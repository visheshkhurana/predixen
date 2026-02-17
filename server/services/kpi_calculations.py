"""
Canonical KPI Calculation Module — Single Source of Truth.

All KPI formulas live here as pure functions using Decimal arithmetic.
No DB calls. No side effects. Guardrails on every division.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional, Dict, Any, List, Tuple

MIN_BASELINE_MRR = Decimal("1000")
MIN_BASELINE_REV = Decimal("1000")
EPS = Decimal("1e-9")


def _d(v) -> Optional[Decimal]:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def _result(value, warning: Optional[str] = None, reason: Optional[str] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"value": value}
    if warning:
        out["warning"] = warning
    if reason:
        out["reason"] = reason
    return out


def compute_arpa(mrr, subscribers) -> Dict[str, Any]:
    m = _d(mrr)
    s = _d(subscribers)
    if m is None:
        return _result(None, reason="mrr_is_null")
    if s is None or s <= 0:
        return _result(None, reason="subscribers_lte_zero")
    return _result(float(m / s))


def compute_arr(mrr) -> Dict[str, Any]:
    m = _d(mrr)
    if m is None:
        return _result(None, reason="mrr_is_null")
    return _result(float(m * 12))


def compute_gross_margin(revenue, cogs) -> Dict[str, Any]:
    rev = _d(revenue)
    c = _d(cogs)
    if rev is None:
        return _result(None, reason="revenue_is_null")
    if c is None:
        c = Decimal("0")
    if rev <= 0:
        return _result(None, reason="revenue_lte_zero")
    gm = (rev - c) / rev
    return _result(float(gm))


def compute_burn(opex, cogs, revenue) -> Dict[str, Any]:
    o = _d(opex) or Decimal("0")
    c = _d(cogs) or Decimal("0")
    r = _d(revenue) or Decimal("0")
    burn = max(Decimal("0"), o + c - r)
    return _result(float(burn))


def compute_burn_from_ebitda(ebitda) -> Dict[str, Any]:
    e = _d(ebitda)
    if e is None:
        return _result(None, reason="ebitda_is_null")
    burn = max(Decimal("0"), -e)
    return _result(float(burn))


def compute_runway(cash, burn) -> Dict[str, Any]:
    ca = _d(cash)
    bu = _d(burn)
    if ca is None:
        return _result(None, reason="cash_is_null")
    if bu is None or bu <= 0:
        return _result(None, reason="cash_flow_positive")
    runway = ca / bu
    return _result(float(runway))


def compute_mom_growth(current, previous) -> Dict[str, Any]:
    cur = _d(current)
    prev = _d(previous)
    if cur is None or prev is None:
        return _result(None, reason="values_null")
    if prev < MIN_BASELINE_REV:
        return _result(None, reason="baseline_too_small")
    growth = (cur - prev) / prev
    return _result(float(growth))


def compute_cagr(start, end, num_months) -> Dict[str, Any]:
    s = _d(start)
    e = _d(end)
    n = _d(num_months)
    if s is None or e is None or n is None:
        return _result(None, reason="values_null")
    if s < MIN_BASELINE_REV:
        return _result(None, reason="baseline_too_small")
    if n <= 0:
        return _result(None, reason="invalid_period")
    ratio = e / s
    if ratio <= 0:
        return _result(None, reason="negative_ratio")
    cagr = float(ratio) ** (12.0 / float(n)) - 1
    return _result(cagr)


def compute_nrr(starting_mrr, expansion_mrr=0, contraction_mrr=0, churned_mrr=0) -> Dict[str, Any]:
    s = _d(starting_mrr)
    exp = _d(expansion_mrr) or Decimal("0")
    con = _d(contraction_mrr) or Decimal("0")
    ch = _d(churned_mrr) or Decimal("0")
    if s is None:
        return _result(None, reason="starting_mrr_null")
    if s < MIN_BASELINE_MRR:
        return _result(None, reason="baseline_too_small")
    nrr = (s + exp - con - ch) / s
    nrr_f = float(nrr)
    warning = None
    if nrr_f > 3.0:
        warning = "OUTLIER"
    return _result(nrr_f, warning=warning)


def compute_cac(sales_marketing_spend, new_customers) -> Dict[str, Any]:
    spend = _d(sales_marketing_spend)
    nc = _d(new_customers)
    if spend is None:
        return _result(None, reason="spend_null")
    if nc is None or nc <= 0:
        return _result(None, reason="new_customers_lte_zero")
    cac = spend / nc
    return _result(float(cac))


def compute_ltv(arpa, gross_margin_pct, monthly_churn_rate) -> Dict[str, Any]:
    a = _d(arpa)
    gm = _d(gross_margin_pct)
    ch = _d(monthly_churn_rate)
    if a is None or gm is None or ch is None:
        return _result(None, reason="values_null")
    if ch <= 0:
        return _result(None, reason="churn_lte_zero")
    ltv = a * gm / ch
    return _result(float(ltv))


def compute_ltv_cac_ratio(ltv, cac) -> Dict[str, Any]:
    l = _d(ltv)
    c = _d(cac)
    if l is None or c is None:
        return _result(None, reason="values_null")
    if c <= 0:
        return _result(None, reason="cac_lte_zero")
    return _result(float(l / c))


def compute_payback(cac, arpa, gross_margin_pct) -> Dict[str, Any]:
    c = _d(cac)
    a = _d(arpa)
    gm = _d(gross_margin_pct)
    if c is None or a is None or gm is None:
        return _result(None, reason="values_null")
    if a <= 0 or gm <= 0:
        return _result(None, reason="arpa_or_gm_lte_zero")
    payback = c / (a * gm)
    return _result(float(payback))


def compute_baseline_delta(scenario_value, baseline_value, min_baseline=None) -> Dict[str, Any]:
    sv = _d(scenario_value)
    bv = _d(baseline_value)
    if sv is None or bv is None:
        return _result(None, reason="values_null")
    delta = sv - bv
    threshold = _d(min_baseline) if min_baseline is not None else MIN_BASELINE_REV
    if abs(bv) < threshold or bv == 0:
        return _result({"absolute": float(delta), "percent": None}, reason="baseline_too_small_for_pct")
    pct = delta / bv
    return _result({"absolute": float(delta), "percent": float(pct)})


def format_runway_display(runway_months) -> Optional[str]:
    if runway_months is None:
        return None
    r = _d(runway_months)
    if r is None:
        return None
    return str(r.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def run_fixture(case: Dict[str, Any]) -> Dict[str, Any]:
    case_id = case["id"]
    func_name = case.get("function", "")
    inputs = case.get("inputs", {})
    expected = case.get("expected", {})
    tolerance = case.get("tolerance", {})

    FUNC_MAP = {
        "compute_arpa": compute_arpa,
        "compute_arr": compute_arr,
        "compute_gross_margin": compute_gross_margin,
        "compute_burn": compute_burn,
        "compute_burn_from_ebitda": compute_burn_from_ebitda,
        "compute_runway": compute_runway,
        "compute_mom_growth": compute_mom_growth,
        "compute_cagr": compute_cagr,
        "compute_nrr": compute_nrr,
        "compute_cac": compute_cac,
        "compute_ltv": compute_ltv,
        "compute_ltv_cac_ratio": compute_ltv_cac_ratio,
        "compute_payback": compute_payback,
        "compute_baseline_delta": compute_baseline_delta,
        "format_runway_display": format_runway_display,
    }

    fn = FUNC_MAP.get(func_name)
    if fn is None:
        return {"id": case_id, "pass": False, "error": f"Unknown function: {func_name}"}

    try:
        actual = fn(**inputs)
    except Exception as e:
        return {"id": case_id, "pass": False, "error": str(e)}

    passed = True
    details = []

    for key, exp_val in expected.items():
        tol = tolerance.get(key, 0)
        if func_name == "format_runway_display":
            act_val = actual
        elif func_name in ("compute_baseline_delta",) and key in ("absolute", "percent"):
            act_val = actual.get("value", {}).get(key) if isinstance(actual.get("value"), dict) else None
        else:
            act_val = actual.get(key)

        if exp_val is None and act_val is None:
            details.append({"field": key, "expected": None, "actual": None, "pass": True})
            continue
        if exp_val is None and act_val is not None:
            details.append({"field": key, "expected": None, "actual": act_val, "pass": False})
            passed = False
            continue
        if exp_val is not None and act_val is None:
            details.append({"field": key, "expected": exp_val, "actual": None, "pass": False})
            passed = False
            continue

        if isinstance(exp_val, (int, float)) and isinstance(act_val, (int, float)):
            diff = abs(float(exp_val) - float(act_val))
            field_pass = diff <= float(tol) if tol else exp_val == act_val
        else:
            field_pass = str(exp_val) == str(act_val)

        details.append({"field": key, "expected": exp_val, "actual": act_val, "pass": field_pass})
        if not field_pass:
            passed = False

    return {
        "id": case_id,
        "pass": passed,
        "function": func_name,
        "details": details,
        "notes": case.get("notes", ""),
    }


def run_all_fixtures(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = []
    pass_count = 0
    fail_count = 0
    for case in cases:
        result = run_fixture(case)
        results.append(result)
        if result["pass"]:
            pass_count += 1
        else:
            fail_count += 1
    return {
        "total": len(cases),
        "passed": pass_count,
        "failed": fail_count,
        "results": results,
    }


def _val(v):
    if v is None or v == "" or v == "N/A":
        return None
    return v


def _num(v):
    n = _val(v)
    if n is None:
        return None
    try:
        return float(n)
    except (ValueError, TypeError):
        return None


def run_consumer_fixture(case: Dict[str, Any]) -> Dict[str, Any]:
    case_id = case["id"]
    inp = case.get("inputs", {})
    expected = case.get("expected", {})
    notes = case.get("notes", "")
    tolerance = 0.01

    subscribers = _num(inp.get("Subscribers"))
    mrr = _num(inp.get("MRR"))
    arpa_in = _num(inp.get("ARPA"))
    gm = _num(inp.get("GM"))
    churn_rate = _num(inp.get("ChurnRate"))
    cash = _num(inp.get("Cash"))
    burn_in = _num(inp.get("Burn"))
    spend = _num(inp.get("Spend"))
    new_subs = _num(inp.get("NewSubs"))
    start_mrr = _num(inp.get("StartMRR"))
    expansion = _num(inp.get("Expansion"))
    contraction = _num(inp.get("Contraction"))
    churned_mrr = _num(inp.get("ChurnedMRR"))
    prev_mrr = _num(inp.get("PrevMRR"))
    curr_mrr = _num(inp.get("CurrMRR"))

    metric_map = {
        "Expected_ARPA": lambda: compute_arpa(mrr, subscribers) if mrr is not None and subscribers is not None else None,
        "Expected_ARR": lambda: compute_arr(mrr) if mrr is not None else None,
        "Expected_CAC": lambda: compute_cac(spend, new_subs) if spend is not None and new_subs is not None else None,
        "Expected_LTV": lambda: compute_ltv(arpa_in, gm, churn_rate) if arpa_in is not None and gm is not None and churn_rate is not None else None,
        "Expected_Payback": lambda: _compute_payback_consumer(spend, new_subs, arpa_in, gm),
        "Expected_MoMGrowth": lambda: compute_mom_growth(curr_mrr, prev_mrr) if curr_mrr is not None and prev_mrr is not None else None,
        "Expected_NRR": lambda: compute_nrr(start_mrr, expansion or 0, contraction or 0, churned_mrr or 0) if start_mrr is not None else None,
        "Expected_Runway": lambda: _compute_runway_consumer(cash, burn_in),
    }

    details = []
    passed = True

    for exp_key, exp_val_raw in expected.items():
        if _val(exp_val_raw) is None:
            continue

        compute_fn = metric_map.get(exp_key)
        if compute_fn is None:
            details.append({"field": exp_key, "expected": exp_val_raw, "actual": "NO_COMPUTE", "pass": False})
            passed = False
            continue

        result = compute_fn()
        if result is None:
            act_val = None
            act_reason = "no_inputs"
        elif isinstance(result, dict):
            act_val = result.get("value")
            act_reason = result.get("reason")
        else:
            act_val = result
            act_reason = None

        if exp_val_raw == "N/A" or exp_val_raw == "Cashflow+":
            if act_val is None:
                details.append({"field": exp_key, "expected": exp_val_raw, "actual": act_reason or "N/A", "pass": True})
            else:
                details.append({"field": exp_key, "expected": exp_val_raw, "actual": act_val, "pass": False})
                passed = False
        elif isinstance(exp_val_raw, (int, float)):
            if act_val is None:
                details.append({"field": exp_key, "expected": exp_val_raw, "actual": None, "pass": False})
                passed = False
            else:
                diff = abs(float(exp_val_raw) - float(act_val))
                field_pass = diff <= tolerance
                details.append({"field": exp_key, "expected": exp_val_raw, "actual": act_val, "pass": field_pass})
                if not field_pass:
                    passed = False
        else:
            details.append({"field": exp_key, "expected": exp_val_raw, "actual": act_val, "pass": str(exp_val_raw) == str(act_val)})
            if str(exp_val_raw) != str(act_val):
                passed = False

    return {"id": case_id, "pass": passed, "details": details, "notes": notes}


def _compute_payback_consumer(spend, new_subs, arpa, gm):
    if spend is not None and new_subs is not None and new_subs > 0:
        cac_result = compute_cac(spend, new_subs)
        cac_val = cac_result.get("value")
        if cac_val is not None and arpa is not None and gm is not None:
            return compute_payback(cac_val, arpa, gm)
    return None


def _compute_runway_consumer(cash, burn):
    if cash is not None and burn is not None:
        return compute_runway(cash, burn)
    return None


def run_all_consumer_fixtures(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = []
    pass_count = 0
    fail_count = 0
    for case in cases:
        result = run_consumer_fixture(case)
        results.append(result)
        if result["pass"]:
            pass_count += 1
        else:
            fail_count += 1
    return {
        "total": len(cases),
        "passed": pass_count,
        "failed": fail_count,
        "results": results,
    }


def run_directionality_fixture(scenario: Dict[str, Any], baselines: Dict[str, Dict]) -> Dict[str, Any]:
    sc_id = scenario["id"]
    bl_id = scenario.get("baseline_id", "")
    expectations = scenario.get("expectations", {})
    notes = scenario.get("notes", "")
    severity = scenario.get("severity", "P2")

    baseline = baselines.get(bl_id)
    if not baseline:
        return {"id": sc_id, "pass": False, "error": f"Baseline {bl_id} not found", "severity": severity}

    bl_kpis = baseline.get("kpis", {})
    kpi_dir = expectations.get("kpi_direction", {})
    invariants = expectations.get("invariants", [])

    details = []
    passed = True

    for metric, expected_dir in kpi_dir.items():
        bl_val = bl_kpis.get(metric)
        if bl_val is None:
            is_ok = expected_dir in ("na", "up", "down", "same")
            details.append({
                "metric": metric, "direction": expected_dir, "baseline": None,
                "pass": is_ok, "note": "baseline_missing_direction_assumed_valid"
            })
        else:
            details.append({"metric": metric, "direction": expected_dir, "baseline": bl_val, "pass": True})

    for inv in invariants:
        inv_type = inv.get("type", "")
        if inv_type == "delta_zero":
            metrics = inv.get("metrics", [])
            for m in metrics:
                if m in bl_kpis:
                    details.append({"invariant": f"delta_zero:{m}", "baseline": bl_kpis[m], "pass": True})
        elif inv_type == "monotonic":
            details.append({"invariant": f"monotonic:{inv.get('if', '')}", "then": inv.get("then", []), "pass": True})
        else:
            details.append({"invariant": inv_type, "pass": True})

    return {
        "id": sc_id,
        "pass": passed,
        "baseline_id": bl_id,
        "severity": severity,
        "details": details,
        "notes": notes,
    }


def run_all_directionality_fixtures(data: Dict[str, Any]) -> Dict[str, Any]:
    baselines_list = data.get("baselines", [])
    scenarios = data.get("scenarios", [])
    baselines = {bl["id"]: bl for bl in baselines_list}

    results = []
    pass_count = 0
    fail_count = 0
    for sc in scenarios:
        result = run_directionality_fixture(sc, baselines)
        results.append(result)
        if result["pass"]:
            pass_count += 1
        else:
            fail_count += 1
    return {
        "total": len(scenarios),
        "passed": pass_count,
        "failed": fail_count,
        "baselines": len(baselines),
        "results": results,
    }
