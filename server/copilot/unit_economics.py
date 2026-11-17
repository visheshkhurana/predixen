"""Unit economics for copilot prompts: real values only, unknowns spelled out.

The truth scan invents CAC / LTV / LTV:CAC / payback / ARPU / customer count /
NRR when the inputs are missing (see ``server/truth/invented_metrics.py``).
Copilot context builders used to hand those to the model as plain numbers, so
it could tell a founder "your CAC is 20K, LTV 2.9L, 150 customers" as fact.

Every copilot context builder reads unit economics through
:func:`company_unit_economics` (same rule as /metrics/computed, realtime and
board export) and renders them with :func:`format_unit_economics_lines`, which
writes "not available (no data)" for anything unknown so the model does not
fill the gap in.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from server.truth.invented_metrics import (
    resolve_unit_economics,
    strip_invented_unit_economics,
)

logger = logging.getLogger(__name__)

NOT_AVAILABLE = "not available (no data)"


def _pos(value: Any) -> Optional[float]:
    """A positive number (unwrapping ``{"value": x}``), else None."""
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, bool) or value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if num > 0 else None


def company_unit_economics(
    db: Any,
    company_id: int,
    ts_metrics: Any = None,
    record: Any = None,
) -> Dict[str, Any]:
    """Real unit economics for one company; None = unknown (never 0, never invented).

    ``ts_metrics`` is the raw truth-scan ``metrics`` dict (invented values are
    stripped here); ``record`` the latest ``FinancialRecord`` of the same
    company. The D2C CAC is read here, scoped to ``company_id`` -- callers pass
    the company they already authorized.
    """
    d2c = None
    if db is not None and company_id is not None:
        try:
            from server.services.d2c_months import latest_d2c_cac
            d2c = latest_d2c_cac(db, company_id)
        except Exception as exc:  # a missing table must not break the copilot
            logger.warning("D2C CAC lookup failed for company %s: %s", company_id, exc)
            d2c = None

    resolved = resolve_unit_economics(ts_metrics, record, d2c)
    ts = strip_invented_unit_economics(ts_metrics)

    def rec(attr: str) -> Optional[float]:
        return _pos(getattr(record, attr, None)) if record is not None else None

    customers = rec("customers") or _pos(ts.get("customer_count"))
    arpu = rec("arpu") or _pos(ts.get("arpu"))
    nrr = rec("ndr") or _pos(ts.get("net_revenue_retention"))
    payback = _pos(ts.get("payback_months"))

    return {
        "cac": _pos(resolved["cac"]),
        "cac_source": resolved["cac_source"],
        "cac_period": resolved["cac_period"],
        "d2c_marketing_spend": (d2c or {}).get("marketing_spend") if resolved["cac_source"] == "d2c_month" else None,
        "d2c_new_customers": (d2c or {}).get("new_customers") if resolved["cac_source"] == "d2c_month" else None,
        "ltv": _pos(resolved["ltv"]),
        "ltv_source": resolved["ltv_source"],
        "ltv_cac_ratio": _pos(resolved["ltv_cac_ratio"]),
        "customers": int(customers) if customers else None,
        "arpu": arpu,
        "net_revenue_retention": nrr,
        "payback_months": payback,
    }


def _period_label(period: Any) -> str:
    if not period:
        return ""
    try:
        return date.fromisoformat(str(period)[:10]).strftime("%b %Y")
    except ValueError:
        return str(period)


def _money(value: float, currency: str) -> str:
    return f"{currency} {value:,.2f}" if value < 1000 else f"{currency} {value:,.0f}"


_SOURCE_LABELS = {
    "reported": "founder-reported",
    "truth_scan": "truth scan",
}


def format_unit_economics_lines(ue: Optional[Dict[str, Any]], currency: str = "USD") -> List[str]:
    """Prompt lines for unit economics; unknown values say NOT_AVAILABLE."""
    ue = ue or {}
    currency = currency or "USD"
    lines: List[str] = []

    cac = ue.get("cac")
    if cac:
        if ue.get("cac_source") == "d2c_month":
            detail = f"{_period_label(ue.get('cac_period'))} D2C month: marketing spend / new customers"
            spend, new = ue.get("d2c_marketing_spend"), ue.get("d2c_new_customers")
            if spend and new:
                detail += f" = {_money(spend, currency)} / {int(new):,}"
            lines.append(f"CAC: {_money(cac, currency)} ({detail})")
        else:
            label = _SOURCE_LABELS.get(ue.get("cac_source") or "", "reported")
            lines.append(f"CAC: {_money(cac, currency)} ({label})")
    else:
        lines.append(f"CAC: {NOT_AVAILABLE}")

    ltv = ue.get("ltv")
    if ltv:
        label = _SOURCE_LABELS.get(ue.get("ltv_source") or "", "reported")
        lines.append(f"LTV: {_money(ltv, currency)} ({label})")
    else:
        lines.append(f"LTV: {NOT_AVAILABLE}")

    ratio = ue.get("ltv_cac_ratio")
    lines.append(f"LTV:CAC: {ratio:.1f}x" if ratio else f"LTV:CAC: {NOT_AVAILABLE}")

    customers = ue.get("customers")
    lines.append(f"Customers: {customers:,}" if customers else f"Customers: {NOT_AVAILABLE}")

    arpu = ue.get("arpu")
    lines.append(f"ARPU: {_money(arpu, currency)}" if arpu else f"ARPU: {NOT_AVAILABLE}")

    nrr = ue.get("net_revenue_retention")
    lines.append(f"NRR: {nrr:.1f}%" if nrr else f"NRR: {NOT_AVAILABLE}")

    payback = ue.get("payback_months")
    lines.append(f"CAC payback: {payback:.1f} months" if payback else f"CAC payback: {NOT_AVAILABLE}")
    return lines
