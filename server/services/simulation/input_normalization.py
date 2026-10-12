"""Shared input normalisation for simulation_v2.

Resolves each simulation input to the same number the endpoint has always
used, and records where that number came from. Provenance is additive:
callers that only pass founder-supplied fields get the historical canned
baselines for everything else.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping, Optional

# Defaults on SimulationV2Request. Do not change these numbers; a test locks
# them to the pydantic field defaults.
CANNED_BASELINE: dict[str, Any] = {
    "total_rounds": 24,
    "monthly_revenue": 50000,
    "monthly_burn": 80000,
    "cash_balance": 500000,
    "customers": 50,
    "team_size": 10,
    "growth_rate": 0.05,
    "churn_rate": 0.03,
    "funding_climate": 0.6,
    "market_growth": 0.5,
    "market_volatility": 0.1,
}

# Hardcoded on the v2 CompanyState. They are not request fields. Their origin
# is unknown to the caller, so they are assumed.
IMPLIED_ASSUMPTIONS: dict[str, Any] = {
    "team_morale": 0.7,
    "product_quality": 0.5,
    "market_fit": 0.5,
    "brand_reputation": 0.5,
    "investor_confidence": 0.5,
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _iso8601(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        return value if text else None
    return None


def _synced_provenance(meta: Optional[Mapping[str, Any]]) -> dict[str, str]:
    entry: dict[str, str] = {"kind": "synced"}
    if not meta:
        return entry
    source = meta.get("source")
    if isinstance(source, str) and source.strip():
        entry["source"] = source
    synced_at = _iso8601(meta.get("synced_at"))
    if synced_at is not None:
        entry["synced_at"] = synced_at
    return entry


def _sync_parts(field: str, record: Any) -> tuple[Any, Optional[Mapping[str, Any]]]:
    """Return (value, metadata) when a connector record actually carries a number."""
    if _is_number(record):
        return record, None
    if isinstance(record, Mapping):
        raw = record.get("value")
        if not _is_number(raw):
            raw = record.get(field)
        if _is_number(raw):
            return raw, record
    return None, None


def _company_value(record: Any) -> Any:
    if _is_number(record):
        return record
    if isinstance(record, Mapping) and _is_number(record.get("value")):
        return record["value"]
    return None


def normalize_simulation_inputs(
    request_fields: Optional[Mapping[str, Any]] = None,
    *,
    company_entered: Optional[Mapping[str, Any]] = None,
    sync_records: Optional[Mapping[str, Any]] = None,
    origins: Optional[Mapping[str, Any]] = None,
) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    """Resolve simulation_v2 inputs and where each one came from.

    Value precedence, first usable value wins:
      1. founder request field
      2. connector sync record
      3. stored company data the founder entered
      4. canned baseline (or the implied CompanyState constant)

    Kind:
      - founder request or stored company data → "entered"
      - a connector sync record that supplied the number → "synced"
      - canned baseline, or any unknown / unrecognised origin → "assumed"

    ``source`` and ``synced_at`` are copied only when the sync record already
    carries them. They are omitted otherwise.
    """
    request_fields = request_fields or {}
    company_entered = company_entered or {}
    sync_records = sync_records or {}
    origins = origins or {}

    defaults = {**CANNED_BASELINE, **IMPLIED_ASSUMPTIONS}
    names = list(CANNED_BASELINE)
    names.extend(name for name in IMPLIED_ASSUMPTIONS if name not in CANNED_BASELINE)
    names.extend(sorted(name for name in origins if name not in defaults))

    values: dict[str, Any] = {}
    provenance: dict[str, dict[str, str]] = {}

    for name in names:
        if name in request_fields and request_fields[name] is not None:
            values[name] = request_fields[name]
            provenance[name] = {"kind": "entered"}
            continue

        if name in sync_records:
            synced_value, meta = _sync_parts(name, sync_records[name])
            if synced_value is not None:
                values[name] = synced_value
                provenance[name] = _synced_provenance(meta)
                continue

        if name in company_entered:
            stored = _company_value(company_entered[name])
            if stored is not None:
                values[name] = stored
                provenance[name] = {"kind": "entered"}
                continue

        if name in defaults:
            values[name] = defaults[name]
        else:
            origin = origins.get(name)
            if isinstance(origin, Mapping) and _is_number(origin.get("value")):
                values[name] = origin["value"]
        # Canned fill, missing origin, or an unrecognised origin label.
        # Never promote that to entered or synced.
        provenance[name] = {"kind": "assumed"}

    return values, provenance


def inputs_for_simulation_request(request: Any) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    """Normalise a SimulationV2Request.

    Only fields the client actually sent are treated as entered. Fields filled
    by the pydantic defaults are assumed. An object with no field-set metadata
    has unknown origin, so every field is assumed.
    """
    fields_set = getattr(request, "model_fields_set", None)
    if fields_set is None:
        return normalize_simulation_inputs()

    explicit: dict[str, Any] = {}
    for name in CANNED_BASELINE:
        if name in fields_set:
            explicit[name] = getattr(request, name)
    return normalize_simulation_inputs(request_fields=explicit)
