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

from api.database import CallLogORM, LoadORM, create_tables, get_db
from api.fmcsa import lookup_carrier
from api.models import (
    CallLog,
    CallLogCreate,
    CarrierVerification,
    DashboardMetrics,
    Load,
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
    """Ensure all DB tables exist when the server starts."""
    create_tables()


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
    return Load.model_validate(row)


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
    response_model=list[Load],
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

    return [_orm_to_load(row) for row in q.all()]


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

# Temporary debug endpoint to test FMCSA integration without auth - remove before production.
@app.get("/debug/verify/{mc_number}", tags=["Debug"])
async def debug_verify(
    mc_number: str,
    mock: bool = Query(False, description="Force mock mode regardless of FMCSA key status"),
):
    """Temporary debug endpoint - no auth - remove before production."""
    try:
        result = await lookup_carrier(mc_number, mock=mock)
        return {"success": True, "mock": mock, "result": result}
    except Exception as e:
        return {"success": False, "mock": mock, "error": str(e)}


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

    # Convert empty strings to None for optional fields
    for field in ["load_id", "final_agreed_rate", "notes"]:
        if field in raw and raw[field] == "":
            raw[field] = None

    # Convert numeric strings to proper types
    for field in ["initial_rate_offered", "final_agreed_rate"]:
        if field in raw and isinstance(raw[field], str) and raw[field]:
            raw[field] = float(raw[field])

    for field in ["num_negotiation_rounds", "call_duration_seconds"]:
        if field in raw and isinstance(raw[field], str) and raw[field]:
            raw[field] = int(raw[field])

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
    )
