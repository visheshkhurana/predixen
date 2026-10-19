"""The one way a scenario gets its baseline financials.

Three call sites built ``EnhancedSimulationInputs`` with invented constants --
$100,000 revenue, 5% growth, 70% gross margin, $20,000 opex, $50,000 payroll,
$10,000 other, $500,000 cash, 5% churn. A company with real data could be
simulated on numbers it never had, and a company with no data at all was
simulated on a business that does not exist, with nothing in the result saying
so. The dashboard and ``POST /api/simulations`` already resolve a company's real
baseline through ``resolve_baseline_financials``; this module applies the same
resolution to the job, sensitivity and worker paths.

Precedence is unchanged where a value exists: a baseline key written on the
scenario still wins. Only a *missing* key is resolved from the company's own
data, and when there is no data either, the caller gets ``MissingBaseline``
rather than a plausible-looking fiction.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from server.simulate.enhanced_monte_carlo import EnhancedSimulationInputs

# Scenario input key -> key returned by resolve_baseline_financials.
BASELINE_FIELDS = {
    "baseline_revenue": "revenue",
    "baseline_growth_rate": "growth",
    "gross_margin": "gross_margin",
    "opex": "opex",
    "payroll": "payroll",
    "other_costs": "other_costs",
    "cash_balance": "cash",
    "churn_rate": "churn",
}


class MissingBaseline(ValueError):
    """The scenario has no baseline values and the company has no data to resolve them from."""


def company_baseline(db, company_id: int) -> Dict[str, float]:
    """Resolve a company's real baseline, the way ``POST /api/simulations`` does.

    Latest truth scan by ``created_at`` supplies the computed metrics; the latest
    ``FinancialRecord`` by ``period_end`` supplies the P&L fields. Raises
    ``MissingBaseline`` when neither exists -- simulating a company with no data
    produces a confident answer to a question nobody asked.
    """
    # Imported here, not at module scope: server/api/simulations imports the
    # simulate package, and a module-level import would close that loop.
    from server.api.simulations import resolve_baseline_financials
    from server.models.financial import FinancialRecord
    from server.models.truth_scan import TruthScan

    truth_scan = (
        db.query(TruthScan)
        .filter(TruthScan.company_id == company_id)
        .order_by(TruthScan.created_at.desc())
        .first()
    )
    metrics = ((truth_scan.outputs_json or {}).get("metrics") or {}) if truth_scan else {}

    latest_record = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(FinancialRecord.period_end.desc())
        .first()
    )

    if not metrics and latest_record is None:
        raise MissingBaseline(
            "This scenario has no baseline financials. Enter revenue, costs and cash on the "
            "scenario, or run a truth scan for the company first."
        )

    return resolve_baseline_financials(metrics, latest_record)


def enhanced_inputs_from_scenario(
    db,
    scenario,
    inputs_json: Optional[Mapping[str, Any]] = None,
    events: Optional[List[Any]] = None,
) -> EnhancedSimulationInputs:
    """Build the engine inputs for a scenario.

    A baseline value present in the scenario wins, exactly as before. A missing
    one is resolved from the company's data instead of being invented. The
    scenario knobs -- pricing change, growth uplift, burn reduction, fundraise,
    margin delta -- keep their 0/None defaults, which mean "no change" rather
    than a guess about the company.
    """
    si = inputs_json if inputs_json is not None else (scenario.inputs_json or {})
    if events is None:
        events = si.get("events", [])

    missing = [key for key in BASELINE_FIELDS if key not in si]
    resolved = company_baseline(db, scenario.company_id) if missing else {}

    values = {
        key: si[key] if key in si else resolved[target]
        for key, target in BASELINE_FIELDS.items()
    }

    return EnhancedSimulationInputs(
        **values,
        pricing_change_pct=si.get("pricing_change_pct", 0),
        growth_uplift_pct=si.get("growth_uplift_pct", 0),
        burn_reduction_pct=si.get("burn_reduction_pct", 0),
        fundraise_month=si.get("fundraise_month"),
        fundraise_amount=si.get("fundraise_amount", 0),
        gross_margin_delta_pct=si.get("gross_margin_delta_pct", 0),
        events=events,
    )
