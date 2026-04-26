"""
Pydantic models for request/response validation and serialization.
All DB-facing models live in database.py; these are the API layer schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EquipmentType(str, Enum):
    dry_van = "Dry Van"
    reefer = "Reefer"
    flatbed = "Flatbed"


class CallOutcome(str, Enum):
    booked = "booked"
    negotiation_failed = "negotiation_failed"
    carrier_ineligible = "carrier_ineligible"
    no_match = "no_match"
    hung_up = "hung_up"


class CallSentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    frustrated = "frustrated"
    hostile = "hostile"


# ---------------------------------------------------------------------------
# Load schemas
# ---------------------------------------------------------------------------

class LoadBase(BaseModel):
    origin: str = Field(..., examples=["Chicago, IL"])
    destination: str = Field(..., examples=["Dallas, TX"])
    equipment_type: EquipmentType
    weight_lbs: int = Field(..., gt=0, le=48000, examples=[42000])
    miles: int = Field(..., gt=0, examples=[920])
    rate_usd: float = Field(..., gt=0, examples=[2450.00])
    floor_price: Optional[float] = None
    commodity: str = Field(..., examples=["Frozen Foods"])
    pickup_date: datetime
    delivery_date: datetime
    available: bool = True


class LoadCreate(LoadBase):
    pass


class Load(LoadBase):
    load_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoadSearchResult(BaseModel):
    loads: list[Load]
    count: int
    available: bool


# ---------------------------------------------------------------------------
# Call log schemas
# ---------------------------------------------------------------------------

class CallLogCreate(BaseModel):
    mc_number: str = Field(..., examples=["MC-123456"])
    carrier_name: str = Field(..., examples=["Swift Transport LLC"])
    load_id: Optional[str] = Field(None, examples=["LD-001"])
    initial_rate_offered: float = Field(..., gt=0, examples=[2200.00])
    final_agreed_rate: Optional[float] = Field(None, examples=[2350.00])
    num_negotiation_rounds: int = Field(..., ge=0, examples=[2])
    outcome: CallOutcome
    sentiment: CallSentiment
    call_duration_seconds: int = Field(..., ge=0, examples=[187])
    notes: Optional[str] = Field(None, examples=["Carrier requested Friday pickup"])

    @field_validator("mc_number", mode="before")
    @classmethod
    def coerce_mc_number_to_str(cls, v):
        return str(v)

    @field_validator("initial_rate_offered", "final_agreed_rate", mode="before")
    @classmethod
    def coerce_empty_to_none(cls, v):
        if v == "" or v is None:
            return None
        return float(v) if isinstance(v, str) else v


class CallLog(CallLogCreate):
    call_id: str
    timestamp: datetime
    # AI enrichment — None until POST /calls/enrich is called
    negotiation_summary: Optional[str] = None
    ai_sentiment: Optional[str] = None
    ai_confidence: Optional[float] = None

    model_config = {"from_attributes": True}


class CallEnrichment(BaseModel):
    call_id: str = Field(..., description="Matches an existing call log record")
    extracted_mc_number: Optional[str] = None
    extracted_load_id: Optional[str] = None
    extracted_outcome: Optional[str] = None
    negotiation_summary: str = Field(..., description="One-sentence AI Extract summary of the negotiation")
    ai_sentiment: str = Field(..., description="AI Classify output: positive / neutral / frustrated / hostile")
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Classifier confidence score (0–1)")


# ---------------------------------------------------------------------------
# Carrier verification schema (maps FMCSA response to our domain)
# ---------------------------------------------------------------------------

class CarrierVerification(BaseModel):
    mc_number: str
    dot_number: Optional[str] = None
    legal_name: Optional[str] = None
    dba_name: Optional[str] = None
    entity_type: Optional[str] = None
    operating_status: Optional[str] = None
    carrier_operation: Optional[str] = None
    cargo_carried: Optional[list[str]] = None
    insurance_on_file: Optional[bool] = None
    safety_rating: Optional[str] = None
    out_of_service_date: Optional[str] = None
    # Derived eligibility flag: active status + insurance on file
    is_eligible: bool = False
    # True when the response was synthesised locally rather than returned by FMCSA
    is_mock: bool = False
    # Set when the FMCSA API returned an error and a mock was used instead
    fmcsa_error: Optional[str] = None


# ---------------------------------------------------------------------------
# Dashboard metrics schema
# ---------------------------------------------------------------------------

class SentimentBreakdown(BaseModel):
    positive: int = 0
    neutral: int = 0
    frustrated: int = 0
    hostile: int = 0


class OutcomeBreakdown(BaseModel):
    booked: int = 0
    negotiation_failed: int = 0
    carrier_ineligible: int = 0
    no_match: int = 0
    hung_up: int = 0


class TopLane(BaseModel):
    origin: str
    destination: str
    call_count: int
    booked_count: int


class DashboardMetrics(BaseModel):
    total_calls: int
    outcome_breakdown: OutcomeBreakdown
    avg_call_duration_seconds: float
    avg_negotiation_rounds: float
    avg_initial_rate_usd: Optional[float]
    avg_final_rate_usd: Optional[float]
    total_revenue_booked_usd: float
    sentiment_breakdown: SentimentBreakdown
    top_lanes: list[TopLane]
    available_loads: int
    booked_loads: int
    # AI quality layer
    sentiment_agreement_rate: Optional[float] = None  # % where agent sentiment == ai_sentiment
    recent_summaries: list[str] = []                  # last 5 negotiation_summary values


class CarrierHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mc_number: str
    returning_carrier: bool
    last_call_date: Optional[datetime] = None
    last_load_id: Optional[str] = None
    last_origin: Optional[str] = None
    last_destination: Optional[str] = None
    total_calls: int = 0
    total_booked: int = 0


class EvaluateOfferRequest(BaseModel):
    load_id: str
    carrier_offer: float
    round_number: int  # 1, 2, or 3


class EvaluateOfferResponse(BaseModel):
    decision: str        # "accept" | "counter" | "reject"
    suggested_counter: Optional[float] = None
    floor_price: float
    rate_usd: float
    round_number: int
    message: str         # exact phrase for the agent to say
