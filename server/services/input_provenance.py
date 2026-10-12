"""Where a synced financial input came from.

Modeling & AI reads this when it fills
``input_provenance[field] = {kind: "synced", source, synced_at}``.
This module only supplies ``source`` and ``synced_at``. It does not choose
``kind`` and it does not change simulation responses.

``source`` is a canonical connector id (``tally``, ``razorpayx``, ``stripe``,
``zoho_books``, ``csv_import``, or another registered provider id). It is never
an account number, credential, or ``source_type`` string such as
``connector_stripe``. ``synced_at`` is a UTC ISO-8601 timestamp ending in
``Z`` or ``+00:00``.

A field is returned only when the latest value for that field is a sync whose
connector id and timestamp are both known, and the connector actually supplied
that field. Manual rows, unknown ids, derived numbers, and ties between
different origins are left out.

If the live table has no ``source`` / ``synced_at`` / ``synced_fields`` columns
yet, sync writes still commit and this helper returns an empty map. A single
static warning is logged. Nothing about the company or the amounts is logged.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session, undefer

from server.core.db import SessionLocal
from server.models.financial import FinancialRecord

logger = logging.getLogger(__name__)

# Logged once per process when financial_records has no provenance columns.
# Static text only: no company id, no amounts, no SQL, no exception text.
MISSING_PROVENANCE_COLUMNS_WARNING = (
    "financial_records is missing sync provenance columns "
    "(source, synced_at, synced_fields); connector sync will continue "
    "without recording where values came from"
)

_PROVENANCE_ATTRIBUTES = ("source", "synced_at", "synced_fields")
_provenance_columns_present: Dict[int, bool] = {}
_provenance_columns_absent: Dict[int, bool] = {}
_missing_columns_warned = False

# Columns a connector or csv import can supply directly. Derived totals
# (gross profit, runway, operating income) are not inputs.
FINANCIAL_INPUT_FIELDS = (
    "revenue",
    "cogs",
    "opex",
    "payroll",
    "other_costs",
    "cash_balance",
    "mrr",
    "arr",
    "gross_margin",
    "net_burn",
    "burn_multiple",
    "headcount",
    "customers",
    "mom_growth",
    "yoy_growth",
    "ndr",
    "ltv",
    "cac",
    "ltv_cac_ratio",
    "arpu",
    "marketing_expense",
)

# Catalog id is canonical. The RazorpayX adapter class uses a different
# PROVIDER_ID; the marketplace id is the one stored on the row.
_PROVIDER_ID_ALIASES = {
    "razorpayx_payroll": "razorpayx",
}

# Not a registered connector class, but it is a sync write path.
_EXTRA_CANONICAL_SOURCES = frozenset({"csv_import", "razorpayx"})

_UTC_ISO = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$"
)


def reset_provenance_column_state() -> None:
    """Clear the process-local column cache and the one-time warning flag.

    Tests that drop columns on an engine already seen as migrated call this.
    Production caches a result per engine for the life of the process.
    """
    global _missing_columns_warned
    _missing_columns_warned = False
    _provenance_columns_present.clear()
    _provenance_columns_absent.clear()


def _engine_of(bind: Any) -> Any:
    return getattr(bind, "engine", bind)


def _warn_missing_provenance_columns() -> None:
    global _missing_columns_warned
    if _missing_columns_warned:
        return
    _missing_columns_warned = True
    logger.warning(MISSING_PROVENANCE_COLUMNS_WARNING)


def provenance_columns_available(bind: Any) -> bool:
    """True when ``financial_records`` has source, synced_at, and synced_fields.

    A missing table is not cached: the same engine may create it later.
    A confirmed absence is cached per engine so later syncs skip the catalog
    lookup. The warning is static and is emitted at most once per process.
    """
    engine = _engine_of(bind)
    key = id(engine)
    if _provenance_columns_present.get(key) is True:
        return True
    if _provenance_columns_absent.get(key) is True:
        return False
    try:
        inspector = inspect(bind)
        if not inspector.has_table(FinancialRecord.__tablename__):
            return False
        names = {column["name"] for column in inspector.get_columns(FinancialRecord.__tablename__)}
    except Exception:
        _warn_missing_provenance_columns()
        return False
    present = all(name in names for name in _PROVENANCE_ATTRIBUTES)
    if present:
        _provenance_columns_present[key] = True
        return True
    _provenance_columns_absent[key] = True
    _warn_missing_provenance_columns()
    return False


def omit_provenance_if_columns_missing(mapper, connection, state) -> None:
    """Drop provenance bindings so INSERT/UPDATE does not name missing columns.

    SQLAlchemy otherwise sends explicit NULL for nullable string columns that
    were left unset, which fails when the live table has not been migrated.
    Values already assigned on the instance are removed from this flush only.
    """
    if provenance_columns_available(connection):
        return
    table = FinancialRecord.__table__
    current = mapper._insert_cols_as_none.get(table)
    if current:
        trimmed = current.difference(_PROVENANCE_ATTRIBUTES)
        if trimmed != current:
            mapper._insert_cols_as_none[table] = trimmed
    for key in _PROVENANCE_ATTRIBUTES:
        state.dict.pop(key, None)
        state.committed_state.pop(key, None)


def utc_now_iso() -> str:
    """Current time as UTC ISO-8601 with a Z suffix and second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc_timestamp(value: Any) -> Optional[datetime]:
    """Parse a UTC ISO-8601 timestamp. Anything else is not a sync time."""
    if not isinstance(value, str) or _UTC_ISO.fullmatch(value) is None:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.utcoffset() != timedelta(0):
        return None
    return parsed.astimezone(timezone.utc)


def canonical_connector_source(provider_id: Any) -> Optional[str]:
    """Return the canonical connector id, or None when it is not one of ours.

    Unknown strings are rejected. This does not strip prefixes or pull an id
    out of ``source_type``, an email, or an account number.
    """
    if not isinstance(provider_id, str) or not provider_id or provider_id != provider_id.strip():
        return None
    if any(char in provider_id for char in "@/ \t"):
        return None
    mapped = _PROVIDER_ID_ALIASES.get(provider_id, provider_id)
    if mapped not in _known_canonical_ids():
        return None
    return mapped


def provided_input_fields(payload: Mapping[str, Any]) -> List[str]:
    """Input fields present in a connector payload. Nulls are not supplied."""
    return [
        name
        for name in FINANCIAL_INPUT_FIELDS
        if name in payload and payload[name] is not None
    ]


def stamp_sync_provenance(
    provider_id: Any,
    provided_fields: Iterable[str],
    synced_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Columns to persist for one connector or csv sync write.

    Returns null provenance when the provider id is not canonical, so a manual
    or unknown write cannot be labeled as a sync. ``synced_fields`` lists only
    known input columns; credential keys in the payload are ignored.
    """
    source = canonical_connector_source(provider_id)
    if source is None:
        return {"source": None, "synced_at": None, "synced_fields": None}
    when = synced_at if synced_at is not None else utc_now_iso()
    if parse_utc_timestamp(when) is None:
        return {"source": None, "synced_at": None, "synced_fields": None}
    fields: List[str] = []
    for name in provided_fields:
        if name in FINANCIAL_INPUT_FIELDS and name not in fields:
            fields.append(name)
    return {"source": source, "synced_at": when, "synced_fields": fields}


def get_input_provenance_sources(
    company_id: int,
    db: Optional[Session] = None,
) -> Dict[str, Dict[str, str]]:
    """Latest synced ``{source, synced_at}`` for each financial input field.

    Manual entries and values whose origin is unclear are omitted. The result
    never includes ``kind``; Modeling adds that when it builds
    ``input_provenance``.
    """
    owns_session = db is None
    session = db if db is not None else SessionLocal()
    try:
        if not provenance_columns_available(session.get_bind()):
            return {}
        records = (
            session.query(FinancialRecord)
            .options(
                undefer(FinancialRecord.source),
                undefer(FinancialRecord.synced_at),
                undefer(FinancialRecord.synced_fields),
            )
            .filter(FinancialRecord.company_id == company_id)
            .all()
        )
        return _provenance_from_records(records)
    except (OperationalError, ProgrammingError):
        session.rollback()
        _warn_missing_provenance_columns()
        return {}
    finally:
        if owns_session:
            session.close()


@dataclass(frozen=True)
class _Claim:
    at: Optional[datetime]
    provenance: Optional[Dict[str, str]]


def _known_canonical_ids() -> set[str]:
    from server.connectors import load_all_connectors
    from server.connectors.registry import ConnectorRegistry

    load_all_connectors()
    ids = set(_EXTRA_CANONICAL_SOURCES)
    for provider_id in ConnectorRegistry.get_available_providers():
        ids.add(_PROVIDER_ID_ALIASES.get(provider_id, provider_id))
    return ids


def _as_utc(value: Any) -> Optional[datetime]:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _non_null_inputs(record: FinancialRecord) -> List[str]:
    return [
        name
        for name in FINANCIAL_INPUT_FIELDS
        if getattr(record, name, None) is not None
    ]


def _clean_provenance(record: FinancialRecord) -> Optional[Dict[str, str]]:
    source = getattr(record, "source", None)
    synced_at = getattr(record, "synced_at", None)
    if canonical_connector_source(source) != source or not isinstance(synced_at, str):
        return None
    if parse_utc_timestamp(synced_at) is None:
        return None
    return {"source": source, "synced_at": synced_at}


def _listed_synced_fields(record: FinancialRecord) -> Optional[List[str]]:
    """Field names the sync claimed, or None when that list is unusable."""
    raw = getattr(record, "synced_fields", None)
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        return None
    present = set(_non_null_inputs(record))
    fields: List[str] = []
    for name in raw:
        if name in present and name in FINANCIAL_INPUT_FIELDS and name not in fields:
            fields.append(name)
    return fields


def _claims_for_record(record: FinancialRecord) -> Dict[str, List[_Claim]]:
    claims: Dict[str, List[_Claim]] = defaultdict(list)
    provenance = _clean_provenance(record)
    synced_at = parse_utc_timestamp(getattr(record, "synced_at", None))
    listed = _listed_synced_fields(record) if provenance is not None else None

    if provenance is not None and synced_at is not None and listed is not None:
        for name in listed:
            claims[name].append(_Claim(synced_at, provenance))
        return claims

    # Manual, unknown id, or a sync that did not say which fields it wrote.
    at = synced_at or _as_utc(getattr(record, "created_at", None))
    for name in _non_null_inputs(record):
        claims[name].append(_Claim(at, None))
    return claims


def _resolve_field(claims: List[_Claim]) -> Optional[Dict[str, str]]:
    if not claims or any(claim.at is None for claim in claims):
        return None
    latest_at = max(claim.at for claim in claims if claim.at is not None)
    latest = [claim for claim in claims if claim.at == latest_at]
    winners = []
    for claim in latest:
        if claim.provenance is None:
            return None
        winners.append((claim.provenance["source"], claim.provenance["synced_at"]))
    if len(set(winners)) != 1:
        return None
    source, synced_at = winners[0]
    return {"source": source, "synced_at": synced_at}


def _provenance_from_records(records: Iterable[FinancialRecord]) -> Dict[str, Dict[str, str]]:
    grouped: Dict[str, List[_Claim]] = defaultdict(list)
    for record in records:
        for field, claims in _claims_for_record(record).items():
            grouped[field].extend(claims)

    resolved: Dict[str, Dict[str, str]] = {}
    for field in FINANCIAL_INPUT_FIELDS:
        provenance = _resolve_field(grouped.get(field, []))
        if provenance is not None:
            resolved[field] = provenance
    return resolved
