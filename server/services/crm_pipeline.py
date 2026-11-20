"""CRM pipeline snapshots: building them from deals and storing them.

Each CRM connector normalises its deals to dicts:

    {"amount": 1200.0, "currency": "USD", "stage": "Proposal",
     "status": "open" | "won" | "lost", "close_date": date | None,
     "probability": 0.4 | None}

and hands `build_snapshot(deals, currency)` over as
`result.metadata["crm_pipeline"]`. The sync route calls `store_snapshot`.
Deals in a currency other than the CRM's main one are counted apart in
`other_currencies` instead of being added to totals in the wrong unit.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Optional

from sqlalchemy.orm import Session

from server.models.crm_pipeline import CRMPipelineSnapshot


def parse_day(value: Any) -> Optional[date]:
    """Date from a date, datetime, ISO string or epoch milliseconds; None if unreadable."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.utcfromtimestamp(value / 1000).date()
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if text.isdigit():
        return parse_day(int(text))
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def probability(value: Any, scale: str = "auto") -> Optional[float]:
    """0..1 from a CRM probability.

    scale="percent" for CRMs that send 0..100 (Zoho CRM, Pipedrive, Salesforce),
    scale="fraction" for 0..1 (HubSpot's hs_deal_stage_probability). "auto"
    guesses from the value, which reads a 1% deal as 100%: connectors should
    pass their scale.
    """
    if value in (None, ""):
        return None
    try:
        p = float(value)
    except (TypeError, ValueError):
        return None
    if scale == "percent" or (scale == "auto" and p > 1):
        p = p / 100
    return max(0.0, min(1.0, p))


def build_snapshot(
    deals: Iterable[Mapping[str, Any]],
    currency: Optional[str],
    today: Optional[date] = None,
    truncated: bool = False,
) -> Dict[str, Any]:
    today = today or datetime.utcnow().date()
    main = (currency or "").upper() or None
    d30, d90 = today - timedelta(days=30), today - timedelta(days=90)

    open_count = won30 = lost30 = won90 = lost90 = read = 0
    open_value = won_value30 = won_value90 = 0.0
    weighted = 0.0
    weighted_known = False
    stages: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    other: Dict[str, Dict[str, Any]] = {}

    for deal in deals:
        read += 1
        amount = float(deal.get("amount") or 0.0)
        status = deal.get("status")
        cur = (deal.get("currency") or main or "").upper() or None
        if main and cur and cur != main:
            bucket = other.setdefault(cur, {"count": 0, "value": 0.0})
            bucket["count"] += 1
            bucket["value"] = round(bucket["value"] + amount, 2)
            continue

        closed = parse_day(deal.get("close_date"))
        if status == "open":
            open_count += 1
            open_value += amount
            p = deal.get("probability")
            if p is not None:
                weighted += amount * float(p)
                weighted_known = True
            stage = str(deal.get("stage") or "Unknown stage")
            row = stages.setdefault(stage, {"stage": stage, "count": 0, "value": 0.0})
            row["count"] += 1
            row["value"] += amount
        elif status == "won" and closed:
            if closed >= d30:
                won30 += 1
                won_value30 += amount
            if closed >= d90:
                won90 += 1
                won_value90 += amount
        elif status == "lost" and closed:
            if closed >= d30:
                lost30 += 1
            if closed >= d90:
                lost90 += 1

    decided = won90 + lost90
    return {
        "snapshot_date": today.isoformat(),
        "currency": main,
        "open_count": open_count,
        "open_value": round(open_value, 2),
        "weighted_value": round(weighted, 2) if weighted_known else None,
        "won_count_30d": won30,
        "won_value_30d": round(won_value30, 2),
        "lost_count_30d": lost30,
        "win_rate_90d": round(won90 / decided, 4) if decided else None,
        "avg_won_deal_90d": round(won_value90 / won90, 2) if won90 else None,
        "deals_read": read,
        "truncated": bool(truncated),
        "stages": [
            {**s, "value": round(s["value"], 2)}
            for s in sorted(stages.values(), key=lambda s: -s["value"])
        ],
        "other_currencies": other,
    }


_FIELDS = (
    "open_count", "open_value", "weighted_value", "won_count_30d", "won_value_30d",
    "lost_count_30d", "win_rate_90d", "avg_won_deal_90d", "deals_read",
)


def store_snapshot(db: Session, company_id: int, source: str, snapshot: Any) -> bool:
    """Write a connector's snapshot, replacing that CRM's row for the same day."""
    if not isinstance(snapshot, Mapping):
        return False
    day = parse_day(snapshot.get("snapshot_date")) or datetime.utcnow().date()
    row = (
        db.query(CRMPipelineSnapshot)
        .filter(
            CRMPipelineSnapshot.company_id == company_id,
            CRMPipelineSnapshot.source == source,
            CRMPipelineSnapshot.snapshot_date == day,
        )
        .one_or_none()
    )
    if row is None:
        row = CRMPipelineSnapshot(company_id=company_id, source=source, snapshot_date=day)
        db.add(row)
    for name in _FIELDS:
        value = snapshot.get(name)
        if value is None and name in ("open_count", "open_value", "won_count_30d", "won_value_30d", "lost_count_30d", "deals_read"):
            value = 0
        setattr(row, name, value)
    row.currency = (snapshot.get("currency") or "")[:3].upper() or None
    row.truncated = 1 if snapshot.get("truncated") else 0
    row.stages = list(snapshot.get("stages") or [])[:50]
    row.other_currencies = dict(snapshot.get("other_currencies") or {})
    return True


def _row(r: CRMPipelineSnapshot) -> Dict[str, Any]:
    return {
        "source": r.source,
        "snapshot_date": r.snapshot_date.isoformat(),
        "currency": r.currency,
        **{name: getattr(r, name) for name in _FIELDS},
        "truncated": bool(r.truncated),
        "stages": r.stages or [],
        "other_currencies": r.other_currencies or {},
    }


def summary(db: Session, company_id: int, history_days: int = 90) -> Dict[str, Any]:
    """Latest snapshot per CRM plus a trend of open pipeline per CRM."""
    since = datetime.utcnow().date() - timedelta(days=history_days)
    rows: List[CRMPipelineSnapshot] = (
        db.query(CRMPipelineSnapshot)
        .filter(CRMPipelineSnapshot.company_id == company_id, CRMPipelineSnapshot.snapshot_date >= since)
        .order_by(CRMPipelineSnapshot.snapshot_date.asc())
        .all()
    )
    latest: Dict[str, CRMPipelineSnapshot] = {}
    trend: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        latest[r.source] = r
        trend.setdefault(r.source, []).append(
            {"date": r.snapshot_date.isoformat(), "open_value": r.open_value, "open_count": r.open_count}
        )
    return {
        "company_id": company_id,
        "crms": [
            {**_row(r), "trend": trend.get(source, [])}
            for source, r in sorted(latest.items(), key=lambda kv: -kv[1].open_value)
        ],
    }
