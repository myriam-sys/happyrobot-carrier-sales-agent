"""
Async FMCSA Query Central API client.

Docs: https://mobile.fmcsa.dot.gov/QCDevsite/docs/qcAPI
Base URL: https://mobile.fmcsa.dot.gov/qc/services/carriers/{mc_number}?webKey={key}

The FMCSA response wraps the carrier record under `{"content": {...}}`.
We normalise it into our CarrierVerification schema.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

from api.models import CarrierVerification

logger = logging.getLogger(__name__)

load_dotenv()

FMCSA_BASE_URL = "https://mobile.fmcsa.dot.gov/qc/services/carriers"
FMCSA_API_KEY: str = os.getenv("FMCSA_API_KEY", "")
FMCSA_PROXY: str = os.getenv("FMCSA_PROXY", "")

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
    # Handle both response formats — some endpoints wrap fields under a "carrier" key
    if "carrier" in content:
        content = content["carrier"]

    operating_status: Optional[str] = content.get("carrierOperation", {}).get(
        "carrierOperationDesc"
    )
    common_authority = content.get("commonAuthorityStatus") or ""
    contract_authority = content.get("contractAuthorityStatus") or ""

    # Carrier is eligible if they are allowed to operate AND insurance is not explicitly denied
    allowed_to_operate = content.get("allowedToOperate", "N") == "Y"
    has_active_authority = (
        allowed_to_operate
        or common_authority.upper() in _ACTIVE_STATUSES
        or contract_authority.upper() in _ACTIVE_STATUSES
    )

    # Insurance: only fail if the field is explicitly "N" — null/missing means not required
    bipd = content.get("bipdInsuranceOnFile")
    insurance_ok = bipd != "N"
    insurance_on_file: Optional[bool] = None if bipd is None else (bipd == "Y")

    is_eligible = has_active_authority and insurance_ok

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


_FMCSA_403_ERROR = (
    "FMCSA API returned 403 — the API key is invalid or the request was rejected. "
    "Real carrier data unavailable. Using mock response based on MC number parity. "
    "Ensure FMCSA_API_KEY is set to a valid FMCSA Query Central key. "
    "Mock MC numbers available: 11111 (eligible), 33333 (eligible), "
    "55555 (eligible), 22222 (ineligible), 44444 (ineligible)."
)

_FMCSA_404_ERROR = (
    "MC number not found in FMCSA records. This may be a test MC number "
    "or the carrier may not be registered. Using mock response based on "
    "MC number parity. See README for available test MC numbers."
)


def _mock_carrier(mc_number: str, fmcsa_error: Optional[str] = None) -> CarrierVerification:
    """
    Return a deterministic mock CarrierVerification based on the last digit of
    the MC number.  Odd last digit → eligible; even last digit → ineligible.
    Always sets ``is_mock=True`` so callers can distinguish real vs mock data.
    ``fmcsa_error`` is populated when the mock was triggered by an API error.
    """
    numeric_mc = mc_number.upper().lstrip("MC-").lstrip("MC").strip()
    # Fall back to "0" (ineligible) if the number contains no digits
    last_digit = next((c for c in reversed(numeric_mc) if c.isdigit()), "0")
    eligible = int(last_digit) % 2 != 0
    logger.warning(
        "FMCSA mock response generated for MC %s — is_eligible=%s", mc_number, eligible
    )
    return CarrierVerification(
        mc_number=mc_number,
        dot_number="MOCK-001" if eligible else "MOCK-002",
        legal_name="FastFreight Carriers LLC" if eligible else "Suspended Transport Inc",
        operating_status="ACTIVE" if eligible else "INACTIVE",
        insurance_on_file=eligible,
        is_eligible=eligible,
        is_mock=True,
        fmcsa_error=fmcsa_error,
    )


async def lookup_carrier(mc_number: str, mock: bool = False) -> Optional[CarrierVerification]:
    """
    Query the FMCSA API for a carrier by MC number.

    Parameters
    ----------
    mc_number:
        MC number with or without the ``MC-`` prefix (e.g. ``"123456"`` or
        ``"MC-123456"``).
    mock:
        When ``True``, bypass the FMCSA API entirely and return a mock
        response (useful for UI/integration testing).

    Returns
    -------
    CarrierVerification | None
        Parsed carrier record. On 404 (MC not found) or 403 (invalid key /
        rejected), returns a mock record with ``is_mock=True`` and
        ``fmcsa_error`` set to a descriptive message. Returns ``None`` only
        when ``mc_number`` is empty or contains no digits.

    Raises
    ------
    httpx.HTTPStatusError
        Re-raised for non-404/403 HTTP errors (e.g. 500) so callers can decide
        how to handle them.
    """
    if mock:
        logger.warning("FMCSA mock mode active for MC %s (explicit ?mock=true)", mc_number)
        return _mock_carrier(mc_number)

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

    # Return None only for empty or non-numeric MC numbers — no mock makes sense here
    if not numeric_mc or not any(c.isdigit() for c in numeric_mc):
        return None

    url = f"{FMCSA_BASE_URL}/{numeric_mc}"
    params = {"webKey": FMCSA_API_KEY}

    proxy_url = FMCSA_PROXY if FMCSA_PROXY else None
    async with httpx.AsyncClient(
        timeout=10.0,
        proxy=proxy_url,
    ) as client:
        response = await client.get(url, params=params)

    if response.status_code == 404:
        logger.warning("FMCSA returned 404 for MC %s — not found, falling back to mock", mc_number)
        return _mock_carrier(mc_number, fmcsa_error=_FMCSA_404_ERROR)

    if response.status_code == 403:
        logger.warning(
            "FMCSA returned 403 for MC %s — invalid key or request rejected", mc_number
        )
        return _mock_carrier(mc_number, fmcsa_error=_FMCSA_403_ERROR)

    response.raise_for_status()

    data = response.json()
    content: Optional[dict] = data.get("content")
    if not content:
        return None

    return _parse_carrier(mc_number, content)
