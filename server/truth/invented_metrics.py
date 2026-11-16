"""Unit-economics values the truth scan invents, and how readers drop them.

When the data behind them is missing, ``truth_scan.run_truth_scan`` still
writes CAC (marketing assumed to be 30% of payroll + 40% of opex), LTV, LTV:CAC
and payback from a 150-customer book, plus NDR 108%, and lists each one on
``metrics["_estimated_metrics"]``. Simulations use them internally, but screens
and exports must not present them as the company's numbers.

Readers that show values to the founder pass truth-scan metrics through
:func:`strip_invented_unit_economics` first. Founder-entered or connected
values on ``FinancialRecord`` are read separately and are unaffected.
"""
from typing import Any, Dict

INVENTED_UNIT_ECONOMICS_KEYS = frozenset({
    "cac",
    "ltv",
    "ltv_cac_ratio",
    "payback_months",
    "arpu",
    "customer_count",
    "net_revenue_retention",
})


def strip_invented_unit_economics(ts_metrics: Any) -> Dict[str, Any]:
    """Copy of truth-scan metrics without the unit-economics values it invented.

    Only keys that are both unit-economics keys and listed on
    ``_estimated_metrics`` are removed; everything else is passed through.
    """
    if not isinstance(ts_metrics, dict):
        return {}
    listed = ts_metrics.get("_estimated_metrics") or []
    if not isinstance(listed, (list, tuple, set)):
        return dict(ts_metrics)
    drop = INVENTED_UNIT_ECONOMICS_KEYS.intersection(str(x) for x in listed)
    return {k: v for k, v in ts_metrics.items() if k not in drop}
