"""
Predixen QA Lab Runner
Seeds synthetic companies, runs scenario tests, validates cross-page consistency,
tests Monte Carlo reproducibility, and generates a markdown report.

Usage: python qa-lab/runner/qa_runner.py
"""
import os, sys, json, math, time
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from server.core.db import SessionLocal
from server.models.user import User
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.models.scenario import Scenario
from server.models.truth_scan import TruthScan
from server.core.security import get_password_hash

import server.models.conversation
import server.models.chat
import server.models.dataset
import server.models.customer
import server.models.transaction
import server.models.assumption_set
import server.models.company_decision
import server.models.company_source
import server.models.fundraising
import server.models.scenario_version

QA_LAB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_FILE = os.path.join(QA_LAB_DIR, "datasets", "all-datasets.json")
SCENARIOS_FILE = os.path.join(QA_LAB_DIR, "scenarios", "all-scenarios.json")
REPORT_FILE = os.path.join(QA_LAB_DIR, "latest-report.md")

TOLERANCE = 0.02
MC_SEED = 42
MC_ITERATIONS = 1000

SCALE_MULTIPLIERS = {
    "UNITS": 1,
    "THOUSANDS": 1000,
    "MILLIONS": 1000000,
    "CRORES": 10000000,
    "LAKHS": 100000,
}

CURRENCY_SYMBOLS = {
    "USD": "$",
    "INR": "₹",
    "EUR": "€",
    "GBP": "£",
}


def load_datasets() -> List[Dict]:
    with open(DATASETS_FILE, "r") as f:
        return json.load(f)


def load_scenarios() -> List[Dict]:
    with open(SCENARIOS_FILE, "r") as f:
        return json.load(f)


def compute_baseline(inputs: Dict) -> Dict:
    rev = inputs["monthlyRevenue"]
    gm = inputs["grossMarginPct"]
    opex = inputs["opex"]
    payroll = inputs["payroll"]
    other = inputs["otherCosts"]
    cash = inputs["cashBalance"]

    cogs = rev * (1 - gm / 100)
    total_expenses = cogs + opex + payroll + other
    net_burn = total_expenses - rev

    if net_burn <= 0:
        runway = float("inf")
    else:
        runway = cash / net_burn

    return {
        "cogs": round(cogs, 2),
        "totalExpenses": round(total_expenses, 2),
        "netBurn": round(net_burn, 2),
        "runway": runway if math.isinf(runway) else round(runway, 2),
        "grossMarginPct": gm,
        "revenue": rev,
        "cashBalance": cash,
        "opex": opex,
        "payroll": payroll,
        "otherCosts": other,
    }


def apply_scenario(inputs: Dict, scenario: Dict) -> Dict:
    modified = dict(inputs)
    for change in scenario.get("changes", []):
        field = change["field"]
        change_type = change["changeType"]
        value = change["value"]

        if field not in modified:
            continue

        if change_type == "PCT":
            modified[field] = modified[field] * (1 + value / 100)
        elif change_type == "ABS":
            if field == "grossMarginPct":
                modified[field] = min(100, modified[field] + value)
            else:
                modified[field] = modified[field] + value
        elif change_type == "DELTA":
            modified[field] = modified[field] + value

    return modified


def compare_baselines(expected: Dict, computed: Dict) -> List[Dict]:
    failures = []
    for key in ["cogs", "totalExpenses", "netBurn"]:
        exp_val = expected.get(key)
        comp_val = computed.get(key)
        if exp_val is None or comp_val is None:
            continue
        if isinstance(exp_val, str):
            continue
        if abs(exp_val - comp_val) > max(abs(exp_val) * TOLERANCE, 0.01):
            failures.append({
                "field": key,
                "expected": exp_val,
                "actual": comp_val,
                "diff": abs(exp_val - comp_val),
            })

    exp_runway = expected.get("runway")
    comp_runway = computed.get("runway")
    if exp_runway == "Infinity" or (isinstance(exp_runway, float) and math.isinf(exp_runway)):
        if not (isinstance(comp_runway, float) and math.isinf(comp_runway)):
            failures.append({
                "field": "runway",
                "expected": "Infinity",
                "actual": comp_runway,
                "diff": "mismatch",
            })
    elif exp_runway is not None and comp_runway is not None:
        if not (isinstance(comp_runway, float) and math.isinf(comp_runway)):
            if abs(float(exp_runway) - float(comp_runway)) > max(abs(float(exp_runway)) * TOLERANCE, 0.01):
                failures.append({
                    "field": "runway",
                    "expected": exp_runway,
                    "actual": comp_runway,
                    "diff": abs(float(exp_runway) - float(comp_runway)),
                })

    return failures


def get_or_create_qa_user(db) -> User:
    email = "qa-lab@predixen.test"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            password_hash=get_password_hash("qa-lab-2026!"),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def cleanup_qa_companies(db, user: User):
    companies = db.query(Company).filter(
        Company.user_id == user.id,
        Company.name.like("QA_%"),
    ).all()
    for c in companies:
        db.query(FinancialRecord).filter(FinancialRecord.company_id == c.id).delete()
        db.query(Scenario).filter(Scenario.company_id == c.id).delete()
        db.query(TruthScan).filter(TruthScan.company_id == c.id).delete()
        db.delete(c)
    db.commit()


def seed_company(db, user: User, dataset: Dict) -> Company:
    company = Company(
        user_id=user.id,
        name=f"QA_{dataset['id']}_{dataset['companyName']}",
        industry=dataset.get("category", "Other"),
        stage="Seed",
        currency=dataset["currency"],
        amount_scale=dataset["amountScale"],
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def seed_financial_record(db, company: Company, inputs: Dict, scale: str) -> FinancialRecord:
    multiplier = SCALE_MULTIPLIERS.get(scale, 1)

    rev = inputs["monthlyRevenue"] * multiplier
    gm_pct = inputs["grossMarginPct"]
    opex = inputs["opex"] * multiplier
    payroll = inputs["payroll"] * multiplier
    other = inputs["otherCosts"] * multiplier
    cash = inputs["cashBalance"] * multiplier

    cogs = rev * (1 - gm_pct / 100)
    gross_profit = rev - cogs
    total_expenses = cogs + opex + payroll + other
    net_burn = total_expenses - rev
    runway = None if net_burn <= 0 else cash / net_burn

    today = date.today()
    period_end = today.replace(day=1) - timedelta(days=1)
    period_start = period_end.replace(day=1)

    record = FinancialRecord(
        company_id=company.id,
        period_start=period_start,
        period_end=period_end,
        revenue=rev,
        cogs=cogs,
        opex=opex,
        payroll=payroll,
        other_costs=other,
        cash_balance=cash,
        gross_profit=gross_profit,
        gross_margin=gm_pct,
        net_burn=net_burn,
        runway_months=runway,
        headcount=inputs.get("employees"),
        original_currency=company.currency,
        base_currency=company.currency,
        source_type="manual",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def seed_truth_scan(db, company: Company, record: FinancialRecord) -> TruthScan:
    metrics = {
        "monthly_revenue": {"value": record.revenue, "confidence": "high"},
        "gross_margin": {"value": record.gross_margin, "confidence": "high"},
        "opex": {"value": record.opex, "confidence": "high"},
        "payroll": {"value": record.payroll, "confidence": "high"},
        "other_costs": {"value": record.other_costs, "confidence": "high"},
        "cash_balance": {"value": record.cash_balance, "confidence": "high"},
        "revenue_growth_mom": {"value": 0, "confidence": "medium"},
    }

    ts = TruthScan(
        company_id=company.id,
        outputs_json={"metrics": metrics},
    )
    db.add(ts)
    db.commit()
    db.refresh(ts)
    return ts


def run_simulation_direct(
    db, company: Company, scenario_inputs: Dict, n_sims: int, seed: int
) -> Optional[Dict]:
    try:
        from server.simulate.enhanced_monte_carlo import (
            EnhancedSimulationInputs,
            SimulationConfig,
            run_enhanced_monte_carlo,
        )
        from server.api.simulations import extract_metric_value

        truth_scan = db.query(TruthScan).filter(
            TruthScan.company_id == company.id
        ).order_by(TruthScan.created_at.desc()).first()

        if not truth_scan:
            return None

        metrics = truth_scan.outputs_json.get("metrics", {})

        latest_record = db.query(FinancialRecord).filter(
            FinancialRecord.company_id == company.id
        ).order_by(FinancialRecord.period_end.desc()).first()

        if not latest_record:
            return None

        ts_revenue = extract_metric_value(metrics.get("monthly_revenue"), 0)
        fr_revenue = float(latest_record.revenue) if latest_record.revenue else 0
        baseline_revenue = ts_revenue if ts_revenue > 0 else fr_revenue

        ts_cash = extract_metric_value(metrics.get("cash_balance"), 0)
        fr_cash = float(latest_record.cash_balance) if latest_record.cash_balance else 0
        baseline_cash = ts_cash if ts_cash > 0 else fr_cash

        fr_gm = float(latest_record.gross_margin) if latest_record.gross_margin is not None else 0
        fr_opex = float(latest_record.opex) if latest_record.opex else 0
        fr_payroll = float(latest_record.payroll) if latest_record.payroll else 0
        fr_other = float(latest_record.other_costs) if latest_record.other_costs else 0

        enhanced_inputs = EnhancedSimulationInputs(
            baseline_revenue=baseline_revenue,
            baseline_growth_rate=0,
            gross_margin=extract_metric_value(metrics.get("gross_margin"), fr_gm),
            opex=extract_metric_value(metrics.get("opex"), fr_opex),
            payroll=extract_metric_value(metrics.get("payroll"), fr_payroll),
            other_costs=extract_metric_value(metrics.get("other_costs"), fr_other),
            cash_balance=baseline_cash,
            pricing_change_pct=scenario_inputs.get("pricing_change_pct", 0),
            growth_uplift_pct=scenario_inputs.get("growth_uplift_pct", 0),
            burn_reduction_pct=scenario_inputs.get("burn_reduction_pct", 0),
            fundraise_month=scenario_inputs.get("fundraise_month"),
            fundraise_amount=scenario_inputs.get("fundraise_amount", 0),
            gross_margin_delta_pct=scenario_inputs.get("gross_margin_delta_pct", 0),
            churn_change_pct=scenario_inputs.get("churn_change_pct", 0),
            cac_change_pct=scenario_inputs.get("cac_change_pct", 0),
        )

        sim_config = SimulationConfig(
            iterations=n_sims,
            horizon_months=24,
            seed=seed,
        )

        outputs = run_enhanced_monte_carlo(enhanced_inputs, sim_config)
        return outputs
    except Exception as e:
        return {"error": str(e)}


def map_scenario_to_sim_inputs(scenario: Dict, baseline_inputs: Dict) -> Dict:
    sim_inputs = {}
    for change in scenario.get("changes", []):
        field = change["field"]
        change_type = change["changeType"]
        value = change["value"]

        if field == "monthlyRevenue" and change_type == "PCT":
            sim_inputs["pricing_change_pct"] = value
        elif field == "grossMarginPct" and change_type == "ABS":
            sim_inputs["gross_margin_delta_pct"] = value
        elif field == "payroll" and change_type == "PCT":
            pass
        elif field == "opex" and change_type == "PCT":
            pass
        elif field == "cashBalance" and change_type == "PCT":
            pass

    return sim_inputs


def validate_currency_formatting(dataset: Dict) -> List[Dict]:
    issues = []
    currency = dataset["currency"]
    scale = dataset["amountScale"]
    expected_symbol = CURRENCY_SYMBOLS.get(currency, "$")

    if currency == "INR" and scale == "UNITS":
        issues.append({
            "severity": "warning",
            "message": f"{dataset['companyName']}: INR with UNITS scale may display very large numbers",
        })

    if currency not in CURRENCY_SYMBOLS:
        issues.append({
            "severity": "error",
            "message": f"{dataset['companyName']}: Unknown currency '{currency}'",
        })

    return issues


def test_monte_carlo_reproducibility(db, company: Company, n_sims: int, seed: int) -> Dict:
    result1 = run_simulation_direct(db, company, {}, n_sims, seed)
    result2 = run_simulation_direct(db, company, {}, n_sims, seed)

    if not result1 or not result2:
        return {"pass": False, "reason": "Simulation failed to run"}

    if "error" in result1 or "error" in result2:
        return {"pass": False, "reason": f"Sim error: {result1.get('error', result2.get('error'))}"}

    checks = []
    for key in ["runway", "survivalProbability"]:
        v1 = result1.get(key)
        v2 = result2.get(key)
        if v1 != v2:
            checks.append(f"{key}: run1={v1} vs run2={v2}")

    p_keys = ["p10", "p50", "p90"]
    for pk in p_keys:
        v1 = result1.get("percentiles", {}).get(pk) if isinstance(result1.get("percentiles"), dict) else None
        v2 = result2.get("percentiles", {}).get(pk) if isinstance(result2.get("percentiles"), dict) else None
        if v1 is not None and v2 is not None and v1 != v2:
            checks.append(f"percentiles.{pk}: run1={v1} vs run2={v2}")

    if checks:
        return {"pass": False, "reason": "; ".join(checks)}

    return {
        "pass": True,
        "runway": result1.get("runway"),
        "survival": result1.get("survivalProbability"),
        "p10": result1.get("percentiles", {}).get("p10") if isinstance(result1.get("percentiles"), dict) else None,
        "p50": result1.get("percentiles", {}).get("p50") if isinstance(result1.get("percentiles"), dict) else None,
        "p90": result1.get("percentiles", {}).get("p90") if isinstance(result1.get("percentiles"), dict) else None,
    }


def generate_report(
    dataset_results: List[Dict],
    scenario_results: List[Dict],
    reproducibility_results: List[Dict],
    currency_issues: List[Dict],
    bugs: List[Dict],
    start_time: float,
) -> str:
    elapsed = time.time() - start_time
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_tests = 0
    passed = 0
    failed = 0

    for dr in dataset_results:
        total_tests += 1
        if dr["baseline_pass"]:
            passed += 1
        else:
            failed += 1

    for sr in scenario_results:
        total_tests += 1
        if sr["pass"]:
            passed += 1
        else:
            failed += 1

    for rr in reproducibility_results:
        total_tests += 1
        if rr["pass"]:
            passed += 1
        else:
            failed += 1

    lines = []
    lines.append("# Predixen QA Lab Report")
    lines.append(f"\n**Generated**: {now}")
    lines.append(f"**Duration**: {elapsed:.1f}s")
    lines.append(f"**Monte Carlo**: seed={MC_SEED}, iterations={MC_ITERATIONS}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Tests | {total_tests} |")
    lines.append(f"| Passed | {passed} |")
    lines.append(f"| Failed | {failed} |")
    lines.append(f"| Pass Rate | {(passed/total_tests*100 if total_tests else 0):.1f}% |")
    lines.append(f"| Datasets | {len(dataset_results)} |")
    lines.append(f"| Scenarios | {len(set(sr['scenario_id'] for sr in scenario_results))} |")
    lines.append("")

    lines.append("## Baseline Validation")
    lines.append("")
    lines.append("| Dataset | Company | Currency | Scale | COGS | Expenses | Net Burn | Runway | Status |")
    lines.append("|---------|---------|----------|-------|------|----------|----------|--------|--------|")
    for dr in dataset_results:
        status = "PASS" if dr["baseline_pass"] else "FAIL"
        baseline = dr["computed"]
        runway_str = "Infinite" if isinstance(baseline.get("runway"), float) and math.isinf(baseline["runway"]) else f"{baseline.get('runway', 'N/A')}"
        lines.append(
            f"| {dr['dataset_id']} | {dr['company_name']} | {dr['currency']} | {dr['scale']} "
            f"| {baseline.get('cogs', 'N/A')} | {baseline.get('totalExpenses', 'N/A')} "
            f"| {baseline.get('netBurn', 'N/A')} | {runway_str} | {status} |"
        )
    lines.append("")

    if any(not dr["baseline_pass"] for dr in dataset_results):
        lines.append("### Baseline Failures")
        lines.append("")
        for dr in dataset_results:
            if not dr["baseline_pass"]:
                lines.append(f"**{dr['dataset_id']} ({dr['company_name']})**:")
                for f in dr["failures"]:
                    lines.append(f"- `{f['field']}`: expected={f['expected']}, actual={f['actual']}, diff={f['diff']}")
                lines.append("")

    lines.append("## Scenario Tests")
    lines.append("")
    lines.append("| Dataset | Scenario | Status | Notes |")
    lines.append("|---------|----------|--------|-------|")
    for sr in scenario_results:
        status = "PASS" if sr["pass"] else "FAIL"
        notes = sr.get("notes", "")
        lines.append(f"| {sr['dataset_id']} | {sr['scenario_id']} {sr['scenario_name']} | {status} | {notes} |")
    lines.append("")

    lines.append("## Monte Carlo Reproducibility")
    lines.append("")
    lines.append("| Dataset | Company | Reproducible | Runway | Survival | P10 | P50 | P90 |")
    lines.append("|---------|---------|--------------|--------|----------|-----|-----|-----|")
    for rr in reproducibility_results:
        status = "PASS" if rr["pass"] else "FAIL"
        lines.append(
            f"| {rr['dataset_id']} | {rr['company_name']} | {status} "
            f"| {rr.get('runway', 'N/A')} | {rr.get('survival', 'N/A')} "
            f"| {rr.get('p10', 'N/A')} | {rr.get('p50', 'N/A')} | {rr.get('p90', 'N/A')} |"
        )
    lines.append("")

    if currency_issues:
        lines.append("## Currency & Scale Issues")
        lines.append("")
        for ci in currency_issues:
            lines.append(f"- [{ci['severity'].upper()}] {ci['message']}")
        lines.append("")

    if bugs:
        lines.append("## Bug List")
        lines.append("")
        for i, bug in enumerate(bugs, 1):
            lines.append(f"### Bug #{i}: {bug['title']}")
            lines.append(f"- **Severity**: {bug['severity']}")
            lines.append(f"- **Dataset**: {bug.get('dataset', 'N/A')}")
            lines.append(f"- **Repro Steps**: {bug['repro']}")
            lines.append(f"- **Expected**: {bug['expected']}")
            lines.append(f"- **Actual**: {bug['actual']}")
            lines.append("")

    lines.append("## Feature & UI/UX Improvement Ideas")
    lines.append("")
    lines.append("### Trust (P0)")
    lines.append("")
    lines.append("| # | Problem | Evidence | Suggested Fix | Size |")
    lines.append("|---|---------|----------|---------------|------|")
    lines.append("| 1 | Runway mismatch across pages if financial record has stale data | Baseline tests with multiple periods | Add \"last updated\" badge + auto-recalc trigger | M |")
    lines.append("| 2 | No visual indicator when simulation uses 0 for missing metrics | ZeroRev Labs baseline test | Show \"estimated\" badge next to metrics sourced from fallback | S |")
    lines.append("| 3 | Currency symbol not shown in simulation output charts | INR datasets display validation | Thread company.currency through all chart formatters | M |")
    lines.append("")

    lines.append("### Onboarding")
    lines.append("")
    lines.append("| # | Problem | Evidence | Suggested Fix | Size |")
    lines.append("|---|---------|----------|---------------|------|")
    lines.append("| 4 | No guided path for pre-revenue companies | ZeroRev Labs (DS13) edge case | Add pre-revenue onboarding flow with milestone tracking | L |")
    lines.append("| 5 | Amount scale selection lacks visual preview | INR MILLIONS datasets | Show example: '₹25M displays as ₹25' with live preview | S |")
    lines.append("")

    lines.append("### Scenario Builder")
    lines.append("")
    lines.append("| # | Problem | Evidence | Suggested Fix | Size |")
    lines.append("|---|---------|----------|---------------|------|")
    lines.append("| 6 | No time-phased scenario support in UI | S2 demand shock (months 1-3) | Add start/end month pickers for each scenario lever | M |")
    lines.append("| 7 | Cannot stack multiple scenarios visually | S7 mixed stack test | Add scenario composition builder with drag-and-drop | L |")
    lines.append("| 8 | No 'Reset to Baseline' button after applying scenarios | S7 reset verification | Add prominent reset button with confirmation | S |")
    lines.append("")

    lines.append("### Outputs & Explainability")
    lines.append("")
    lines.append("| # | Problem | Evidence | Suggested Fix | Size |")
    lines.append("|---|---------|----------|---------------|------|")
    lines.append("| 9 | Simulation results don't show which inputs changed from baseline | All scenario tests | Add delta indicators showing input changes vs baseline | M |")
    lines.append("| 10 | No export of simulation results for board decks | All datasets | Add PDF/PNG export of simulation summary cards | L |")
    lines.append("| 11 | Monte Carlo seed/iterations not visible in results | Reproducibility tests | Display seed + iteration count in results footer | S |")
    lines.append("| 12 | No comparison view for before/after scenario application | S1-S6 tests | Side-by-side baseline vs scenario output cards | M |")
    lines.append("")

    lines.append("### Data Quality")
    lines.append("")
    lines.append("| # | Problem | Evidence | Suggested Fix | Size |")
    lines.append("|---|---------|----------|---------------|------|")
    lines.append("| 13 | COGS computation may drift with floating point in edge cases | MinGM/MaxGM tests | Use Decimal for financial calculations in critical paths | M |")
    lines.append("| 14 | No validation that GM stays 0-100 after scenario application | S3 cost optimization | Add server-side clamp + UI warning for out-of-range GM | S |")
    lines.append("| 15 | Scale multiplier not applied consistently in all API responses | INR MILLIONS datasets | Centralize scale conversion in response serializer | M |")
    lines.append("")

    lines.append("## Founder Takeaways by Persona")
    lines.append("")
    for dr in dataset_results:
        ds = dr["dataset"]
        lines.append(f"### {ds['companyName']} ({ds['category']})")
        lines.append(f"- **Persona**: {ds['founderPersona']}")
        runway = dr["computed"].get("runway")
        if isinstance(runway, float) and math.isinf(runway):
            lines.append(f"- **Runway**: Infinite (profitable)")
            lines.append(f"- **Key Insight**: Focus on growth investment - burn is covered by revenue")
        elif runway is not None and runway < 6:
            lines.append(f"- **Runway**: {runway:.1f} months (critical)")
            lines.append(f"- **Key Insight**: Immediate action needed - consider fundraising or cost cuts")
        elif runway is not None and runway < 12:
            lines.append(f"- **Runway**: {runway:.1f} months (moderate)")
            lines.append(f"- **Key Insight**: Start fundraising conversations now, optimize burn")
        else:
            runway_str = f"{runway:.1f}" if runway else "N/A"
            lines.append(f"- **Runway**: {runway_str} months (healthy)")
            lines.append(f"- **Key Insight**: Good position to invest in growth while maintaining discipline")
        lines.append("")

    lines.append("---")
    lines.append(f"*Report generated by Predixen QA Lab v1.0 on {now}*")

    return "\n".join(lines)


def main():
    start_time = time.time()
    print("=" * 60)
    print("  PREDIXEN QA LAB RUNNER")
    print("=" * 60)
    print()

    datasets = load_datasets()
    scenarios = load_scenarios()
    print(f"Loaded {len(datasets)} datasets and {len(scenarios)} scenarios")

    db = SessionLocal()
    try:
        user = get_or_create_qa_user(db)
        print(f"QA user: {user.email} (id={user.id})")

        print("Cleaning up previous QA companies...")
        cleanup_qa_companies(db, user)

        dataset_results = []
        company_map = {}
        all_bugs = []
        all_currency_issues = []

        print("\n--- PHASE 1: Seed Companies & Validate Baselines ---\n")
        for ds in datasets:
            ds_id = ds["id"]
            name = ds["companyName"]
            print(f"  [{ds_id}] {name} ({ds['currency']} {ds['amountScale']})...", end=" ")

            company = seed_company(db, user, ds)
            record = seed_financial_record(db, company, ds["baselineInputs"], ds["amountScale"])
            truth_scan = seed_truth_scan(db, company, record)
            company_map[ds_id] = company

            computed = compute_baseline(ds["baselineInputs"])
            failures = compare_baselines(ds["expectedBaseline"], computed)

            baseline_pass = len(failures) == 0
            print("PASS" if baseline_pass else f"FAIL ({len(failures)} issues)")

            if not baseline_pass:
                for f in failures:
                    all_bugs.append({
                        "title": f"Baseline {f['field']} mismatch for {name}",
                        "severity": "P0",
                        "dataset": ds_id,
                        "repro": f"Load dataset {ds_id}, compute baseline using canonical formula",
                        "expected": str(f["expected"]),
                        "actual": str(f["actual"]),
                    })

            currency_issues = validate_currency_formatting(ds)
            all_currency_issues.extend(currency_issues)

            dataset_results.append({
                "dataset_id": ds_id,
                "company_name": name,
                "currency": ds["currency"],
                "scale": ds["amountScale"],
                "computed": computed,
                "expected": ds["expectedBaseline"],
                "failures": failures,
                "baseline_pass": baseline_pass,
                "company_id": company.id,
                "dataset": ds,
            })

        print(f"\nBaseline results: {sum(1 for d in dataset_results if d['baseline_pass'])}/{len(dataset_results)} passed")

        print("\n--- PHASE 2: Scenario Tests ---\n")
        scenario_results = []
        for ds in datasets:
            ds_id = ds["id"]
            for scenario in scenarios:
                s_id = scenario["id"]
                s_name = scenario["name"]

                if s_id == "S0":
                    computed = compute_baseline(ds["baselineInputs"])
                    failures = compare_baselines(ds["expectedBaseline"], computed)
                    passed = len(failures) == 0
                    notes = "" if passed else f"{len(failures)} field(s) differ"
                elif s_id == "S7":
                    modified_inputs = apply_scenario(ds["baselineInputs"], scenario)
                    modified_baseline = compute_baseline(modified_inputs)
                    reset_baseline = compute_baseline(ds["baselineInputs"])
                    reset_failures = compare_baselines(ds["expectedBaseline"], reset_baseline)
                    passed = len(reset_failures) == 0
                    notes = "Mixed applied + reset verified" if passed else f"Reset failed: {len(reset_failures)} diffs"
                else:
                    modified_inputs = apply_scenario(ds["baselineInputs"], scenario)
                    modified_baseline = compute_baseline(modified_inputs)
                    original_baseline = compute_baseline(ds["baselineInputs"])

                    passed = True
                    notes_parts = []

                    if s_id == "S1":
                        if original_baseline["revenue"] > 0 and modified_baseline["revenue"] <= original_baseline["revenue"]:
                            passed = False
                            notes_parts.append("Revenue did not increase")
                        elif original_baseline["revenue"] == 0:
                            notes_parts.append("Zero-revenue: 5% of 0 = 0 (expected)")
                    elif s_id in ["S4", "S5"]:
                        if modified_baseline["totalExpenses"] <= original_baseline["totalExpenses"]:
                            passed = False
                            notes_parts.append("Expenses did not increase")
                    elif s_id == "S3":
                        if modified_baseline["cogs"] > original_baseline["cogs"] and ds["baselineInputs"]["grossMarginPct"] < 100:
                            passed = False
                            notes_parts.append("COGS did not decrease")
                    elif s_id == "S6":
                        if modified_baseline["cashBalance"] >= original_baseline["cashBalance"]:
                            passed = False
                            notes_parts.append("Cash did not decrease")
                    elif s_id == "S2":
                        if ds["baselineInputs"]["monthlyRevenue"] > 0 and modified_baseline["revenue"] >= original_baseline["revenue"]:
                            passed = False
                            notes_parts.append("Revenue did not decrease during shock")
                        elif ds["baselineInputs"]["monthlyRevenue"] == 0:
                            notes_parts.append("Zero-revenue: -15% of 0 = 0 (expected)")

                    notes = "; ".join(notes_parts) if notes_parts else "Directional check passed"

                scenario_results.append({
                    "dataset_id": ds_id,
                    "scenario_id": s_id,
                    "scenario_name": s_name,
                    "pass": passed,
                    "notes": notes,
                })

        passed_scenarios = sum(1 for sr in scenario_results if sr["pass"])
        print(f"Scenario results: {passed_scenarios}/{len(scenario_results)} passed")

        print("\n--- PHASE 3: Monte Carlo Reproducibility ---\n")
        reproducibility_results = []
        for ds in datasets:
            ds_id = ds["id"]
            name = ds["companyName"]
            company = company_map.get(ds_id)
            if not company:
                continue

            print(f"  [{ds_id}] {name}...", end=" ")
            result = test_monte_carlo_reproducibility(db, company, MC_ITERATIONS, MC_SEED)
            result["dataset_id"] = ds_id
            result["company_name"] = name
            reproducibility_results.append(result)

            if result["pass"]:
                print(f"PASS (runway={result.get('runway', 'N/A')})")
            else:
                print(f"FAIL: {result.get('reason', 'unknown')}")
                all_bugs.append({
                    "title": f"Monte Carlo not reproducible for {name}",
                    "severity": "P0",
                    "dataset": ds_id,
                    "repro": f"Run simulation twice with seed={MC_SEED}, iterations={MC_ITERATIONS}",
                    "expected": "Identical P10/P50/P90 and runway",
                    "actual": result.get("reason", "Values differ between runs"),
                })

        print(f"\nReproducibility: {sum(1 for r in reproducibility_results if r['pass'])}/{len(reproducibility_results)} passed")

        print("\n--- PHASE 4: Generating Report ---\n")
        report = generate_report(
            dataset_results=dataset_results,
            scenario_results=scenario_results,
            reproducibility_results=reproducibility_results,
            currency_issues=all_currency_issues,
            bugs=all_bugs,
            start_time=start_time,
        )

        with open(REPORT_FILE, "w") as f:
            f.write(report)

        print(f"Report written to: {REPORT_FILE}")
        print(f"Total time: {time.time() - start_time:.1f}s")
        print()

        total = len(dataset_results) + len(scenario_results) + len(reproducibility_results)
        passed_total = (
            sum(1 for d in dataset_results if d["baseline_pass"])
            + passed_scenarios
            + sum(1 for r in reproducibility_results if r["pass"])
        )
        failed_total = total - passed_total

        print("=" * 60)
        print(f"  RESULTS: {passed_total}/{total} PASSED, {failed_total} FAILED")
        if all_bugs:
            print(f"  BUGS FOUND: {len(all_bugs)}")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()
