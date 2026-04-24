"""
HappyRobot Carrier Sales Agent — FastAPI backend.

Exposes endpoints for the AI voice agent to:
  - Browse available freight loads
  - Verify carrier eligibility via FMCSA
  - Log completed calls with negotiation details
  - Surface operational metrics on a dashboard
"""

from __future__ import annotations

import os
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import CallLogORM, LoadORM, create_tables, migrate_tables, engine, get_db
from api.fmcsa import lookup_carrier
from api.models import (
    CallEnrichment,
    CallLog,
    CallLogCreate,
    CarrierHistory,
    CarrierVerification,
    DashboardMetrics,
    Load,
    LoadSearchResult,
    OutcomeBreakdown,
    SentimentBreakdown,
    TopLane,
)

load_dotenv()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="HappyRobot Carrier Sales API",
    description="Inbound carrier sales automation backend for freight brokerage.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Ensure all DB tables exist and schema is current when the server starts."""
    create_tables()
    migrate_tables(engine)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

API_KEY: str = os.getenv("API_KEY", "")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def require_api_key(key: str = Security(_api_key_header)) -> str:
    """
    FastAPI dependency that validates the X-API-Key request header.

    Raises 403 if the key is missing or incorrect.
    """
    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY environment variable is not configured.",
        )
    if key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )
    return key


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _orm_to_load(row: LoadORM) -> Load:
    load = Load.model_validate(row)
    if load.rate_usd is not None:
        load.floor_price = round(load.rate_usd * 0.90, 2)
    return load


def _orm_to_call(row: CallLogORM) -> CallLog:
    return CallLog.model_validate(row)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
)
def health_check():
    """
    Returns 200 OK with a simple status payload.
    No authentication required — useful for load-balancer probes.
    """
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get(
    "/loads",
    response_model=LoadSearchResult,
    tags=["Loads"],
    summary="List freight loads",
    dependencies=[Depends(require_api_key)],
)
def list_loads(
    origin: Optional[str] = Query(None, description="Filter by origin city/state substring"),
    equipment_type: Optional[str] = Query(None, description="Filter by equipment type (Dry Van | Reefer | Flatbed)"),
    available_only: bool = Query(True, description="Return only loads that are still available"),
    db: Session = Depends(get_db),
):
    """
    Return freight loads from the loadboard, with optional filtering.

    Query parameters
    ----------------
    origin          : Case-insensitive substring match on the origin field.
    equipment_type  : Exact match on equipment type (``Dry Van``, ``Reefer``, ``Flatbed``).
    available_only  : When ``true`` (default), only loads not yet covered are returned.
    """
    q = db.query(LoadORM)

    if available_only:
        q = q.filter(LoadORM.available == True)  # noqa: E712
    if origin:
        q = q.filter(LoadORM.origin.ilike(f"%{origin}%"))
    if equipment_type:
        q = q.filter(LoadORM.equipment_type == equipment_type)

    loads = [_orm_to_load(row) for row in q.all()]
    return LoadSearchResult(loads=loads, count=len(loads), available=available_only)


@app.get(
    "/loads/{load_id}",
    response_model=Load,
    tags=["Loads"],
    summary="Get a single load by ID",
    dependencies=[Depends(require_api_key)],
)
def get_load(load_id: str, db: Session = Depends(get_db)):
    """
    Retrieve full details for a specific load by its ID (e.g. ``LD-001``).

    Returns 404 if the load does not exist.
    """
    row = db.get(LoadORM, load_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Load '{load_id}' not found.")
    return _orm_to_load(row)


@app.get(
    "/verify-carrier/{mc_number}",
    response_model=CarrierVerification,
    tags=["Carriers"],
    summary="Verify carrier eligibility via FMCSA",
    dependencies=[Depends(require_api_key)],
)
async def verify_carrier(mc_number: str):
    """
    Look up a carrier in the FMCSA database by MC number and return
    eligibility information.

    ``is_eligible`` is ``true`` when the carrier has active operating authority
    **and** insurance on file.

    Returns 404 if the MC number is not found in FMCSA records.
    Forwards 502 on FMCSA upstream errors.
    """
    try:
        result = await lookup_carrier(mc_number)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"FMCSA API returned {exc.response.status_code}.",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Carrier with MC number '{mc_number}' not found in FMCSA records.",
        )
    return result

@app.get("/debug/verify/{mc_number}", tags=["Debug"],
         dependencies=[Depends(require_api_key)])
async def debug_verify(
    mc_number: str,
    mock: bool = Query(False, description="Force mock mode regardless of FMCSA key status"),
):
    """
    FMCSA diagnostic endpoint. Calls FMCSA directly and returns the
    full response including mock fallback status and any FMCSA errors.
    Useful for verifying FMCSA connectivity and API key status.
    Requires API key authentication via X-API-Key header.
    """
    try:
        result = await lookup_carrier(mc_number, mock=mock)
        return {
            "success": result is not None,
            "mock": result.is_mock if result else False,
            "fmcsa_error": result.fmcsa_error if result else None,
            "result": result,
        }
    except Exception as e:
        return {"success": False, "mock": mock, "error": str(e)}


@app.get(
    "/carriers/{mc_number}/history",
    response_model=CarrierHistory,
    tags=["Carriers"],
    summary="Get call history for a carrier by MC number",
    dependencies=[Depends(require_api_key)],
)
def get_carrier_history(
    mc_number: str,
    db: Session = Depends(get_db),
):
    """
    Returns aggregated call history for a given MC number,
    computed from existing call logs.

    Used by the Orchestrator Agent to detect returning carriers
    and personalize the greeting.

    Returns returning_carrier=False with zero counts if no
    prior calls exist for this MC number.
    """
    rows = (
        db.query(CallLogORM)
        .filter(CallLogORM.mc_number == mc_number)
        .order_by(CallLogORM.timestamp.desc())
        .all()
    )

    if not rows:
        return CarrierHistory(
            mc_number=mc_number,
            returning_carrier=False,
        )

    last = rows[0]

    # Resolve last load's origin and destination from the loads table
    last_origin: Optional[str] = None
    last_destination: Optional[str] = None
    if last.load_id:
        load_row = db.get(LoadORM, last.load_id)
        if load_row:
            last_origin = load_row.origin
            last_destination = load_row.destination

    total_booked = sum(1 for r in rows if r.outcome == "booked")

    return CarrierHistory(
        mc_number=mc_number,
        returning_carrier=True,
        last_call_date=last.timestamp,
        last_load_id=last.load_id,
        last_origin=last_origin,
        last_destination=last_destination,
        total_calls=len(rows),
        total_booked=total_booked,
    )


@app.post(
    "/calls/log",
    response_model=CallLog,
    status_code=status.HTTP_201_CREATED,
    tags=["Calls"],
    summary="Log a completed carrier call",
    dependencies=[Depends(require_api_key)],
)
async def log_call(request: Request, db: Session = Depends(get_db)):
    """
    Persist a call record after the AI agent completes a carrier interaction.

    A unique ``call_id`` (UUID4) and ``timestamp`` are auto-generated.
    The ``load_id``, if provided, is not validated against the loads table so
    that calls can be logged even for loads that were removed after the fact.

    Accepts the raw request body so that empty strings sent by HappyRobot for
    optional fields can be coerced to ``None`` before Pydantic validation.
    """
    raw = await request.json()

    try:
        # Robust sanitization — handles None, empty string, wrong types
        def _clean(val, default=None):
            if val is None or val == "" or val == "null":
                return default
            return val

        raw["mc_number"] = str(_clean(raw.get("mc_number"), "UNKNOWN"))
        raw["carrier_name"] = _clean(raw.get("carrier_name"), "Unknown Carrier") or "Unknown Carrier"
        raw["load_id"] = _clean(raw.get("load_id"))
        raw["notes"] = _clean(raw.get("notes"))

        for field in ["initial_rate_offered"]:
            v = _clean(raw.get(field), 0.0)
            raw[field] = float(v) if v is not None else 0.0

        raw["final_agreed_rate"] = None if _clean(raw.get("final_agreed_rate")) is None else float(raw["final_agreed_rate"])

        for field in ["num_negotiation_rounds", "call_duration_seconds"]:
            v = _clean(raw.get(field), 0)
            raw[field] = int(float(str(v))) if v is not None else 0

        payload = CallLogCreate(**raw)
        row = CallLogORM(
            call_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            **payload.model_dump(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _orm_to_call(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(e)} | Raw payload: {raw}",
        )


@app.post(
    "/calls/enrich",
    response_model=CallLog,
    tags=["Calls"],
    summary="Enrich a call log with AI Extract and AI Classify outputs",
    dependencies=[Depends(require_api_key)],
)
def enrich_call(payload: CallEnrichment, db: Session = Depends(get_db)):
    """
    Apply HappyRobot AI Extract and AI Classify results to an existing call record.

    Called after the voice interaction completes. Looks up the call by ``call_id``
    and writes the AI-generated fields (negotiation summary, classified sentiment,
    confidence score) onto the record. Also backfills ``mc_number``, ``load_id``,
    and ``outcome`` from extraction if the original log left them unset.

    Returns 404 if ``call_id`` does not match any call log.
    """
    row = db.get(CallLogORM, payload.call_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call log '{payload.call_id}' not found.",
        )

    row.negotiation_summary = payload.negotiation_summary
    row.ai_sentiment = payload.ai_sentiment
    row.ai_confidence = payload.ai_confidence

    # Backfill extracted fields only when the original record has no value
    if payload.extracted_mc_number and row.mc_number in (None, "UNKNOWN"):
        row.mc_number = payload.extracted_mc_number
    if payload.extracted_load_id and not row.load_id:
        row.load_id = payload.extracted_load_id
    if payload.extracted_outcome and not row.outcome:
        row.outcome = payload.extracted_outcome

    db.commit()
    db.refresh(row)
    return _orm_to_call(row)


@app.get(
    "/calls/log",
    response_model=list[CallLog],
    tags=["Calls"],
    summary="Retrieve recent call logs",
    dependencies=[Depends(require_api_key)],
)
def list_calls(
    limit: int = Query(20, ge=1, le=100, description="Number of records to return (max 100)"),
    db: Session = Depends(get_db),
):
    """
    Return the most recent call logs ordered by timestamp descending.

    Query parameters
    ----------------
    limit : Number of records to return. Defaults to 20, max 100.
    """
    rows = (
        db.query(CallLogORM)
        .order_by(CallLogORM.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [_orm_to_call(row) for row in rows]


@app.get(
    "/dashboard/metrics",
    response_model=DashboardMetrics,
    tags=["Dashboard"],
    summary="Operational metrics for the carrier sales dashboard",
    dependencies=[Depends(require_api_key)],
)
def dashboard_metrics(db: Session = Depends(get_db)):
    """
    Aggregate metrics computed from all call logs and current load board state.

    Includes outcome breakdown, average rates, sentiment distribution,
    and the top 5 lanes by call volume.
    """
    calls = db.query(CallLogORM).all()

    # --- outcome & sentiment counts ---
    outcome_counts: dict[str, int] = defaultdict(int)
    sentiment_counts: dict[str, int] = defaultdict(int)
    for c in calls:
        outcome_counts[c.outcome] += 1
        sentiment_counts[c.sentiment] += 1

    # --- rate / duration / round averages ---
    total = len(calls)
    avg_duration = (
        sum(c.call_duration_seconds for c in calls) / total if total else 0.0
    )
    avg_rounds = sum(c.num_negotiation_rounds for c in calls) / total if total else 0.0
    avg_initial = (
        sum(c.initial_rate_offered for c in calls) / total if total else None
    )

    booked_calls = [c for c in calls if c.outcome == "booked" and c.final_agreed_rate]
    avg_final = (
        sum(c.final_agreed_rate for c in booked_calls) / len(booked_calls)
        if booked_calls
        else None
    )
    total_revenue = sum(c.final_agreed_rate for c in booked_calls if c.final_agreed_rate)

    # --- top lanes (by call volume, joining load data) ---
    lane_calls: dict[tuple[str, str], list[str]] = defaultdict(list)
    for c in calls:
        if c.load_id:
            load_row = db.get(LoadORM, c.load_id)
            if load_row:
                key = (load_row.origin, load_row.destination)
                lane_calls[key].append(c.outcome)

    top_lanes = sorted(
        [
            TopLane(
                origin=origin,
                destination=dest,
                call_count=len(outcomes),
                booked_count=outcomes.count("booked"),
            )
            for (origin, dest), outcomes in lane_calls.items()
        ],
        key=lambda l: l.call_count,
        reverse=True,
    )[:5]

    # --- AI quality layer ---
    enriched_calls = [c for c in calls if c.ai_sentiment]
    if enriched_calls:
        agreed = sum(1 for c in enriched_calls if c.sentiment == c.ai_sentiment)
        sentiment_agreement_rate = round(agreed / len(enriched_calls) * 100, 1)
    else:
        sentiment_agreement_rate = None

    recent_summaries = [
        c.negotiation_summary
        for c in sorted(calls, key=lambda c: c.timestamp, reverse=True)
        if c.negotiation_summary
    ][:5]

    # --- load board state ---
    available_loads = db.query(func.count(LoadORM.load_id)).filter(LoadORM.available == True).scalar() or 0  # noqa: E712
    booked_loads = db.query(func.count(LoadORM.load_id)).filter(LoadORM.available == False).scalar() or 0  # noqa: E712

    return DashboardMetrics(
        total_calls=total,
        outcome_breakdown=OutcomeBreakdown(
            booked=outcome_counts.get("booked", 0),
            negotiation_failed=outcome_counts.get("negotiation_failed", 0),
            carrier_ineligible=outcome_counts.get("carrier_ineligible", 0),
            no_match=outcome_counts.get("no_match", 0),
            hung_up=outcome_counts.get("hung_up", 0),
        ),
        avg_call_duration_seconds=round(avg_duration, 1),
        avg_negotiation_rounds=round(avg_rounds, 2),
        avg_initial_rate_usd=round(avg_initial, 2) if avg_initial is not None else None,
        avg_final_rate_usd=round(avg_final, 2) if avg_final is not None else None,
        total_revenue_booked_usd=round(total_revenue, 2),
        sentiment_breakdown=SentimentBreakdown(
            positive=sentiment_counts.get("positive", 0),
            neutral=sentiment_counts.get("neutral", 0),
            frustrated=sentiment_counts.get("frustrated", 0),
            hostile=sentiment_counts.get("hostile", 0),
        ),
        top_lanes=top_lanes,
        available_loads=available_loads,
        booked_loads=booked_loads,
        sentiment_agreement_rate=sentiment_agreement_rate,
        recent_summaries=recent_summaries,
    )


@app.delete(
    "/admin/clear-calls",
    tags=["Admin"],
    summary="Clear all call logs — demo reset only",
    dependencies=[Depends(require_api_key)],
)
def clear_all_calls(db: Session = Depends(get_db)):
    """
    Delete every call log record from the database.
    Intended for demo resets only — this action is irreversible.
    Requires API key authentication via X-API-Key header.
    """
    deleted = db.query(CallLogORM).delete()
    db.commit()
    return {"deleted": deleted, "message": f"Cleared {deleted} call log(s)."}
