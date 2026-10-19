"""One definition of burn and runway for every reader.

    net_burn = payroll + marketing_expense + opex + cogs + other_costs - revenue

Net burn keeps its sign: negative means the company is cash-flow positive
("profitable"), and runway is then not a number of months at all. It must never
be reported as a capped figure (36, 60, 120) or sign-flipped into a positive
burn. Runway is also unknown, not zero or twelve, when cash was never provided.

Before this module, several pages summed the cost columns themselves and most
of them left out ``marketing_expense``, so the same record showed a different
burn on the dashboard, alerts, KPI board and copilot. Route every reader
through these helpers instead.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

# Cost columns on FinancialRecord that make up gross burn. marketing_expense is
# stored separately from other_costs (other_costs must NOT include marketing).
COST_FIELDS = ("payroll", "marketing_expense", "opex", "cogs", "other_costs")

RUNWAY_PROFITABLE = "profitable"
RUNWAY_FINITE = "finite"
RUNWAY_UNKNOWN = "unknown"


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return v


def _get(record: Any, field: str) -> Optional[float]:
    if record is None:
        return None
    if isinstance(record, Mapping):
        return _num(record.get(field))
    return _num(getattr(record, field, None))


def gross_burn(record: Any) -> float:
    """Total monthly costs (COGS and marketing included) for a record or dict."""
    return sum((_get(record, f) or 0.0) for f in COST_FIELDS)


def net_burn(record: Any, revenue: Optional[float] = None) -> Optional[float]:
    """Signed net burn for a record. ``revenue`` overrides the record's own.

    Falls back to the stored ``net_burn`` scalar only when there is no cost
    breakdown to compute from. Returns None when nothing is known.
    """
    if record is None:
        return None
    rev = _num(revenue)
    if rev is None:
        rev = _get(record, "revenue") or 0.0
    costs = gross_burn(record)
    if costs > 0:
        return costs - rev
    stored = _get(record, "net_burn")
    if stored is not None:
        return stored
    if rev > 0:
        # Revenue with zero recorded costs: cash-flow positive by the record.
        return -rev
    return None


def runway_months(cash: Any, burn: Optional[float]) -> Optional[float]:
    """Months of runway, or None when profitable/break-even or cash unknown."""
    c = _num(cash)
    b = _num(burn)
    if b is None or b <= 0 or c is None:
        return None
    if c <= 0:
        return 0.0
    return c / b


def runway_status(cash: Any, burn: Optional[float]) -> str:
    b = _num(burn)
    if b is not None and b <= 0:
        return RUNWAY_PROFITABLE
    if b is None or _num(cash) is None:
        return RUNWAY_UNKNOWN
    return RUNWAY_FINITE


def burn_summary(record: Any, revenue: Optional[float] = None, cash: Any = "__record__") -> Dict[str, Any]:
    """Everything a reader needs about burn/runway for one record.

    ``cash`` defaults to the record's cash_balance; None there means unknown.
    """
    nb = net_burn(record, revenue)
    cash_val = _get(record, "cash_balance") if cash == "__record__" else _num(cash)
    status = runway_status(cash_val, nb)
    return {
        "gross_burn": gross_burn(record) if record is not None else None,
        "net_burn": nb,
        "is_profitable": status == RUNWAY_PROFITABLE,
        "cash_balance": cash_val,
        "runway_months": runway_months(cash_val, nb),
        "runway_status": status,
    }
