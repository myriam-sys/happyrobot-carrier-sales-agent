"""
Async FMCSA Query Central API client.

Docs: https://mobile.fmcsa.dot.gov/QCDevsite/docs/qcAPI
Base URL: https://mobile.fmcsa.dot.gov/qc/services/carriers/{mc_number}?webKey={key}

The FMCSA response wraps the carrier record under `{"content": {...}}`.
We normalise it into our CarrierVerification schema.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

from api.models import CarrierVerification

load_dotenv()

FMCSA_BASE_URL = "https://mobile.fmcsa.dot.gov/qc/services/carriers"
FMCSA_API_KEY: str = os.getenv("FMCSA_API_KEY", "")

# Statuses that indicate the carrier is authorised to haul freight
_ACTIVE_STATUSES = {"ACTIVE", "AUTHORIZED FOR PROPERTY"}


def _extract_cargo(content: dict[str, Any]) -> list[str]:
    """Pull the list of cargo types from the nested FMCSA payload."""
    cargo_carried = content.get("cargoCarried", {})
    if not isinstance(cargo_carried, dict):
        return []
    return [k for k, v in cargo_carried.items() if v == "X"]


def _parse_carrier(mc_number: str, content: dict[str, Any]) -> CarrierVerification:
    """Map a raw FMCSA carrier content dict to CarrierVerification."""
    operating_status: Optional[str] = content.get("carrierOperation", {}).get(
        "carrierOperationDesc"
    )
    common_authority = content.get("commonAuthorityStatus", "")
    contract_authority = content.get("contractAuthorityStatus", "")

    # Carrier is eligible if authority is active AND insurance is on file
    has_active_authority = common_authority.upper() in _ACTIVE_STATUSES or \
                           contract_authority.upper() in _ACTIVE_STATUSES
    insurance_on_file: Optional[bool] = content.get("bipdInsuranceOnFile") == "Y"
    is_eligible = has_active_authority and bool(insurance_on_file)

    return CarrierVerification(
        mc_number=mc_number,
        dot_number=str(content.get("dotNumber", "")),
        legal_name=content.get("legalName"),
        dba_name=content.get("dbaName"),
        entity_type=content.get("entityType", {}).get("entityTypeDesc"),
        operating_status=operating_status,
        carrier_operation=content.get("carrierOperation", {}).get("carrierOperationDesc"),
        cargo_carried=_extract_cargo(content),
        insurance_on_file=insurance_on_file,
        safety_rating=content.get("safetyRating"),
        out_of_service_date=content.get("oosDate"),
        is_eligible=is_eligible,
    )


async def lookup_carrier(mc_number: str) -> Optional[CarrierVerification]:
    """
    Query the FMCSA API for a carrier by MC number.

    Parameters
    ----------
    mc_number:
        MC number with or without the ``MC-`` prefix (e.g. ``"123456"`` or
        ``"MC-123456"``).

    Returns
    -------
    CarrierVerification | None
        Parsed carrier record, or ``None`` if the carrier was not found or the
        API key is not configured.

    Raises
    ------
    httpx.HTTPStatusError
        Re-raised for non-404 HTTP errors so callers can decide how to handle.
    """
    if not FMCSA_API_KEY:
        # Graceful degradation: return a stub so the rest of the system works
        # without a live FMCSA key (useful during local development/testing).
        return CarrierVerification(
            mc_number=mc_number,
            legal_name="[FMCSA key not configured — stub response]",
            is_eligible=False,
        )

    # Strip common prefixes; FMCSA expects the numeric portion only
    numeric_mc = mc_number.upper().lstrip("MC-").lstrip("MC").strip()

    url = f"{FMCSA_BASE_URL}/{numeric_mc}"
    params = {"webKey": FMCSA_API_KEY}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)

    if response.status_code == 404:
        return None

    response.raise_for_status()

    data = response.json()
    content: Optional[dict] = data.get("content")
    if not content:
        return None

    return _parse_carrier(mc_number, content)
