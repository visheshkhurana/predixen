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

    - ``_estimated_metrics`` present (a list): only unit-economics keys listed
      on it are removed; everything else is passed through.
    - ``_estimated_metrics`` ABSENT (a scan saved before the flag existed, or a
      null): every unit-economics key is removed. Every version of the truth
      scan has computed CAC from assumed marketing spend (30% of payroll + 40%
      of opex), LTV from an assumed churn floor, LTV:CAC and payback from those,
      and NRR as a 100/108 placeholder, so none of them can be real in an old
      scan. ARPU / customer count are real only when customer rows existed, but
      an old scan cannot be told apart from the 150-customer default (a real
      150 is possible), and real counts are read from FinancialRecord anyway.
      Re-running the scan restores a real customer count.
    - ``_estimated_metrics`` present but malformed: passed through unchanged.
    """
    if not isinstance(ts_metrics, dict):
        return {}
    listed = ts_metrics.get("_estimated_metrics")
    if listed is None:
        drop = INVENTED_UNIT_ECONOMICS_KEYS
    elif not isinstance(listed, (list, tuple, set)):
        return dict(ts_metrics)
    else:
        drop = INVENTED_UNIT_ECONOMICS_KEYS.intersection(str(x) for x in listed)
    return {k: v for k, v in ts_metrics.items() if k not in drop}


def strip_invented_from_outputs(outputs: Any) -> Dict[str, Any]:
    """Copy of a truth scan's whole ``outputs_json`` without invented unit economics.

    Strips ``metrics`` (see :func:`strip_invented_unit_economics`; a list kept
    at the top level of ``outputs`` is honoured too) and drops the flags and
    benchmark comparisons computed from the removed values (e.g. "Low LTV:CAC
    Ratio" from an invented ratio). Everything else is passed through.
    """
    if not isinstance(outputs, dict):
        return {}
    out = dict(outputs)
    raw_metrics = outputs.get("metrics")
    if not isinstance(raw_metrics, dict):
        return out
    metrics = dict(raw_metrics)
    if "_estimated_metrics" not in metrics and isinstance(outputs.get("_estimated_metrics"), list):
        metrics["_estimated_metrics"] = outputs["_estimated_metrics"]
    kept = strip_invented_unit_economics(metrics)
    if "_estimated_metrics" not in raw_metrics:
        kept.pop("_estimated_metrics", None)
    removed = {k for k in raw_metrics if k not in kept}
    out["metrics"] = kept
    if not removed:
        return out

    flags = outputs.get("flags")
    if isinstance(flags, list):
        out["flags"] = [
            f for f in flags
            if not (isinstance(f, dict) and removed.intersection(
                str(m) for m in (f.get("metrics_involved") or [])
            ))
        ]
    comparisons = outputs.get("benchmark_comparisons")
    if isinstance(comparisons, list):
        out["benchmark_comparisons"] = [
            c for c in comparisons
            if not (isinstance(c, dict) and str(c.get("metric")) in removed)
        ]
    return out


def _num(value: Any) -> float:
    """A truth-scan / record value as a float; 0.0 when absent or not numeric."""
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, bool) or value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def resolve_unit_economics(
    ts_metrics: Any,
    record: Any = None,
    d2c_cac: Any = None,
) -> Dict[str, Any]:
    """CAC / LTV / LTV:CAC from real inputs only, in one order for every reader.

    - ``ts_metrics``: raw truth-scan metrics; invented values are stripped here.
    - ``record``: a ``FinancialRecord`` (or anything with ``cac``/``ltv``/
      ``ltv_cac_ratio`` attributes); founder-entered or connected values win.
    - ``d2c_cac``: the result of ``server.services.d2c_months.latest_d2c_cac``
      (marketing spend / new customers from a D2C month), or None.

    CAC order: record > D2C month > real truth-scan value. LTV only comes from
    the record or a real truth-scan value (one month of D2C data is not enough
    to model lifetime value). The ratio is reported, or LTV / CAC when both are
    known. Unknown values are 0.0 (readers already treat 0 as "not available")
    and their source is None.
    """
    ts = strip_invented_unit_economics(ts_metrics)

    def rec(attr: str) -> float:
        return _num(getattr(record, attr, None)) if record is not None else 0.0

    cac, cac_source, cac_period = rec("cac"), None, None
    if cac > 0:
        cac_source = "reported"
    elif isinstance(d2c_cac, dict) and _num(d2c_cac.get("cac")) > 0:
        cac, cac_source = _num(d2c_cac.get("cac")), "d2c_month"
        cac_period = d2c_cac.get("period")
    elif _num(ts.get("cac")) > 0:
        cac, cac_source = _num(ts.get("cac")), "truth_scan"
    else:
        cac = 0.0

    ltv, ltv_source = rec("ltv"), None
    if ltv > 0:
        ltv_source = "reported"
    elif _num(ts.get("ltv")) > 0:
        ltv, ltv_source = _num(ts.get("ltv")), "truth_scan"
    else:
        ltv = 0.0

    ratio = rec("ltv_cac_ratio") or _num(ts.get("ltv_cac_ratio"))
    if ratio <= 0 and ltv > 0 and cac > 0:
        ratio = ltv / cac
    if ratio <= 0:
        ratio = 0.0

    return {
        "cac": cac,
        "ltv": ltv,
        "ltv_cac_ratio": ratio,
        "cac_source": cac_source,
        "cac_period": cac_period,
        "ltv_source": ltv_source,
    }
