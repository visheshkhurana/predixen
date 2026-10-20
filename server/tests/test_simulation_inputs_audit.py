"""Audit 2026-10-16: the enhanced Monte Carlo simulated inputs nobody entered.

AlphaKids (TEST-REPORT-2026-09-16): $815,430 cash, $3,600 MRR, -56% gross
margin, burn $64,980 -> runway 12.55 months. The founder asked about two hires
at $235K/yr combined ($110K + $125K).

1. The scenario hiring plan was summed for a log line and never reached the
   engine, so two hires did not move runway.
2. churn_rate defaulted to 5% and no call site passed the company's churn.
3. Costs carried no noise and runway was whole months: P10 = P50 = P90.
4. "Reduce burn X%" skipped payroll.
5. The copilot invented cash/revenue/growth/burn/margin when data was missing
   and split net burn so the engine charged COGS on top of it.
6. Fundraising readiness turned 0.8% MoM growth into 80%.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from server.api.simulations import _build_enhanced_inputs, resolve_baseline_financials
from server.simulate.enhanced_monte_carlo import (
    EnhancedSimulationInputs,
    SimulationConfig,
    run_enhanced_monte_carlo,
)

CASH, MRR, GM = 815_430.0, 3_600.0, -56.0
BURN = 64_980.0
# Engine net cashflow = MRR * GM - costs, so costs = BURN + MRR * GM / 100.
COSTS = BURN + MRR * GM / 100  # 62,964
PAYROLL, OTHER = 40_000.0, 7_964.0
OPEX = COSTS - PAYROLL - OTHER
RUNWAY = CASH / BURN  # 12.55

TWO_HIRES = [
    {"role": "Growth Lead", "count": 1, "start_month": 1, "monthly_cost": 110_000 / 12},
    {"role": "ML Engineer", "count": 1, "start_month": 1, "monthly_cost": 125_000 / 12},
]


def _alphakids(**overrides) -> EnhancedSimulationInputs:
    kw = dict(
        baseline_revenue=MRR, baseline_growth_rate=0, gross_margin=GM,
        opex=OPEX, payroll=PAYROLL, other_costs=OTHER, cash_balance=CASH,
    )
    kw.update(overrides)
    return EnhancedSimulationInputs(**kw)


def _run(inputs, seed=42, iterations=1000):
    return run_enhanced_monte_carlo(
        inputs, SimulationConfig(iterations=iterations, horizon_months=24, seed=seed)
    )["runway"]


def _alphakids_metrics(**extra):
    m = {"cash_balance": CASH, "monthly_revenue": MRR, "gross_margin": GM,
         "opex": OPEX, "payroll": PAYROLL, "other_costs": OTHER}
    m.update(extra)
    return m


# --- 1. hires reach the engine ----------------------------------------------

def test_two_hires_shorten_runway_materially():
    without = _run(_alphakids())
    with_hires = _run(_alphakids(hiring_plan=TWO_HIRES))
    # $19.6K/mo more burn on $65K: 815,430 / 84,563 = 9.6 months.
    assert without["p50"] - with_hires["p50"] > 2.5
    assert with_hires["p50"] == pytest.approx(CASH / (BURN + 235_000 / 12), abs=0.3)


def test_hire_cost_starts_at_its_start_month():
    early = _run(_alphakids(hiring_plan=[{**TWO_HIRES[0], "start_month": 1}]))
    late = _run(_alphakids(hiring_plan=[{**TWO_HIRES[0], "start_month": 10}]))
    assert early["p50"] < late["p50"] < _run(_alphakids())["p50"]


def test_scenario_hiring_plan_is_passed_by_the_api():
    scenario = SimpleNamespace(inputs_json={"hiring_plan": TWO_HIRES})
    inputs = _build_enhanced_inputs(scenario, _alphakids_metrics(), None)
    assert inputs.hiring_plan == TWO_HIRES


# --- 2. churn: the company's, or none ----------------------------------------

def test_engine_default_churn_is_zero():
    assert EnhancedSimulationInputs(
        baseline_revenue=1, baseline_growth_rate=0, gross_margin=50,
        opex=1, payroll=1, other_costs=1, cash_balance=1,
    ).churn_rate == 0


def test_api_uses_no_churn_when_the_company_has_none():
    inputs = _build_enhanced_inputs(SimpleNamespace(inputs_json={}), _alphakids_metrics(), None)
    assert inputs.churn_rate == 0


def test_api_passes_the_companys_churn_when_known():
    resolved = resolve_baseline_financials(_alphakids_metrics(churn_rate=2.5), None)
    assert resolved["churn"] == 2.5
    inputs = _build_enhanced_inputs(
        SimpleNamespace(inputs_json={}), _alphakids_metrics(churn_rate=2.5), None
    )
    assert inputs.churn_rate == 2.5


# --- 3. a real distribution -----------------------------------------------------

def test_alphakids_percentiles_are_distinct_and_centred_on_the_real_runway():
    r = _run(_alphakids())
    assert r["p10"] < r["p50"] < r["p90"], r
    assert r["p50"] == pytest.approx(RUNWAY, abs=0.15)  # was 13.0 (whole months)


def test_seeded_runs_are_still_deterministic():
    assert _run(_alphakids(), seed=7) == _run(_alphakids(), seed=7)


def test_zero_cost_sigma_with_no_revenue_is_a_single_point():
    r = _run(_alphakids(baseline_revenue=0, cost_sigma=0))
    assert r["p10"] == r["p50"] == r["p90"] == pytest.approx(CASH / COSTS, abs=0.05)


# --- 4. burn reduction includes payroll --------------------------------------

def test_burn_reduction_cuts_payroll_too():
    payroll_only = dict(baseline_revenue=0, opex=0, other_costs=0, payroll=50_000,
                        cash_balance=500_000, cost_sigma=0)
    base = _run(_alphakids(**payroll_only))
    cut = _run(_alphakids(**payroll_only, burn_reduction_pct=20))
    assert base["p50"] == pytest.approx(10.0, abs=0.05)
    assert cut["p50"] == pytest.approx(12.5, abs=0.05)  # 500K / 40K


# --- 5. copilot runs on the real baseline, or not at all ---------------------

class _Query:
    def __init__(self, result):
        self._result = result

    def filter(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def first(self):
        return self._result

    def scalar(self):
        # Monthly plan-quota count. This fake has no usage rows.
        return 0


class _NoRow:
    def fetchone(self):
        return None


class _DB:
    def __init__(self, metrics, record=None):
        self.metrics, self.record = metrics, record

    def query(self, model):
        from server.models.truth_scan import TruthScan
        if model is TruthScan:
            return _Query(SimpleNamespace(outputs_json={"metrics": self.metrics}))
        return _Query(self.record)

    def execute(self, *a, **k):
        # Subscription lookup. No row means the Free plan.
        return _NoRow()

    def add(self, *a, **k):
        return None

    def commit(self):
        return None


def _copilot_run(monkeypatch, metrics):
    from server.copilot import simulation_handler as sh
    from server.copilot.intent_parser import CopilotIntent, ParsedIntent, SimulationParameters
    from server.simulate import enhanced_monte_carlo as emc

    captured = {}

    def _capture(inputs, config):
        captured["inputs"] = inputs
        raise RuntimeError("captured")

    monkeypatch.setattr(emc, "run_enhanced_monte_carlo", _capture)
    handler = sh.SimulationHandler(_DB(metrics), company_id=999_001, user_id=999_001)
    parsed = ParsedIntent(
        intent=CopilotIntent.RUN_SIMULATION,
        parameters=SimulationParameters(burn_reduction_pct=10),
        confidence=1.0, original_message="cut burn 10%",
    )
    try:
        result = handler.run_simulation(parsed)
    except RuntimeError as e:
        assert str(e) == "captured"
        result = None
    return result, captured.get("inputs")


def test_copilot_refuses_to_invent_a_baseline(monkeypatch):
    result, inputs = _copilot_run(monkeypatch, {})
    assert inputs is None, "simulated with invented numbers"
    assert result["success"] is False
    assert result["action"] == "insufficient_data"
    assert "cash balance" in result["missing"]


def test_copilot_simulated_burn_equals_real_burn(monkeypatch):
    metrics = {"cash_balance": CASH, "monthly_revenue": MRR, "gross_margin": GM,
               "net_burn": BURN}
    _, inputs = _copilot_run(monkeypatch, metrics)
    assert inputs.cash_balance == CASH
    assert inputs.baseline_revenue == MRR
    assert inputs.gross_margin == GM
    month1_net = inputs.baseline_revenue * inputs.gross_margin / 100 - (
        inputs.opex + inputs.payroll + inputs.other_costs
    )
    assert month1_net == pytest.approx(-BURN)


# --- 6. fundraising readiness growth units -----------------------------------

@pytest.mark.parametrize("growth,score", [(0.8, 20), (8.0, 50), (12.0, 75)])
def test_readiness_growth_is_read_as_a_percentage(growth, score):
    from server.api.fundraising_readiness import _compute_readiness

    g = _compute_readiness({"revenue_growth_mom": growth}, None, None)["breakdown"]["growth"]
    assert g["value"] == growth  # 0.8 used to become 80.0
    assert g["score"] == score   # ...and score 95


def test_readiness_growth_from_financial_record_is_a_percentage():
    from server.api.fundraising_readiness import _compute_readiness

    record = SimpleNamespace(runway_months=12, cash_balance=0, net_burn=0,
                             mom_growth=0.8, ltv_cac_ratio=0)
    g = _compute_readiness({}, record, None)["breakdown"]["growth"]
    assert g["value"] == 0.8 and g["score"] == 20
