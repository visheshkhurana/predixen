"""Store and read D2C monthly inputs, and compute unit economics from them."""

from __future__ import annotations

from dataclasses import fields
from datetime import date
from typing import Any, Dict, List, Mapping, Optional

from sqlalchemy.orm import Session

from server.core.d2c import D2CPeriodInputs, compute_unit_economics
from server.models.d2c_month import D2CMonth

INPUT_FIELDS = tuple(f.name for f in fields(D2CPeriodInputs))
MANUAL = "manual"


def month_start(value: date) -> date:
    return value.replace(day=1)


def upsert_month(
    db: Session,
    company_id: int,
    period: date,
    values: Mapping[str, Any],
    source: str,
) -> D2CMonth:
    """Write the given fields for one month.

    A connector never overwrites a field the founder set by hand; a manual
    write always wins. A value of None from a connector is ignored (it does
    not know the field); a None from a manual write clears it.
    """
    period = month_start(period)
    row = (
        db.query(D2CMonth)
        .filter(D2CMonth.company_id == company_id, D2CMonth.period == period)
        .one_or_none()
    )
    if row is None:
        row = D2CMonth(company_id=company_id, period=period, field_sources={})
        db.add(row)

    sources = dict(row.field_sources or {})
    for name, value in values.items():
        if name not in INPUT_FIELDS:
            continue
        if source != MANUAL:
            if value is None or sources.get(name) == MANUAL:
                continue
        setattr(row, name, value)
        if value is None:
            sources.pop(name, None)
        else:
            sources[name] = source
    row.field_sources = sources
    db.flush()
    return row


def inputs_from_row(row: D2CMonth) -> Optional[D2CPeriodInputs]:
    """The engine needs orders and sales; without them there is nothing to compute."""
    if row.orders_shipped is None or row.gross_sales is None:
        return None
    kwargs = {name: getattr(row, name) for name in INPUT_FIELDS}
    for name, default in (("discounts", 0.0), ("rto_orders", 0), ("customer_returns_value", 0.0), ("customer_returns_orders", 0)):
        if kwargs[name] is None:
            kwargs[name] = default
    return D2CPeriodInputs(**kwargs)


def month_view(row: D2CMonth) -> Dict[str, Any]:
    inputs = {name: getattr(row, name) for name in INPUT_FIELDS}
    view: Dict[str, Any] = {
        "period": row.period.isoformat(),
        "inputs": inputs,
        "sources": dict(row.field_sources or {}),
        "unit_economics": None,
        "error": None,
    }
    engine_inputs = inputs_from_row(row)
    if engine_inputs is None:
        view["missing"] = [n for n in ("orders_shipped", "gross_sales") if inputs[n] is None]
        return view
    try:
        view["unit_economics"] = compute_unit_economics(engine_inputs).as_dict()
    except ValueError as exc:
        view["error"] = str(exc)
    return view


def list_months(db: Session, company_id: int, limit: int = 12) -> List[Dict[str, Any]]:
    rows = (
        db.query(D2CMonth)
        .filter(D2CMonth.company_id == company_id)
        .order_by(D2CMonth.period.desc())
        .limit(limit)
        .all()
    )
    return [month_view(r) for r in rows]


def shopify_values(summary: Mapping[str, Any]) -> Dict[str, Any]:
    """Map the Shopify sync summary onto engine inputs.

    Shopify's net_sales_ex_gst is already after discounts, so it becomes
    gross_sales with discounts left to the engine as 0; refunds are returns.
    Orders are placed orders until a shipping partner reports shipped ones.
    """
    return {
        "orders_shipped": summary.get("orders"),
        "gross_sales": summary.get("net_sales_ex_gst"),
        "discounts": 0.0 if summary.get("net_sales_ex_gst") is not None else None,
        "customer_returns_value": summary.get("refunds"),
        "cod_share": summary.get("cod_share"),
        "new_customers": None,
    }
