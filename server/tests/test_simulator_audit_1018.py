"""Simulator math/plumbing audit (2026-10-18).

Canonical: net burn = total costs incl. COGS - revenue (the dashboard burnRate).
AlphaKids demo: MRR 43,949, net burn 24,109, cash ~514K -> ~21.3 months.
"""

import asyncio
import random
from types import SimpleNamespace

import pytest

MRR = 43949.0
NET = 24109.0
CASH = 513746.0
EXPECTED_RUNWAY = CASH / NET  # ~21.3


# --- 1. simulation v2 (LLM agent engine): burn_rate is GROSS spend ---------

def test_v2_runway_uses_net_of_gross_spend():
    from server.services.simulation.types import net_runway_months

    gross = NET + MRR  # what v2Request.ts now sends
    assert net_runway_months(CASH, MRR, gross) == pytest.approx(EXPECTED_RUNWAY)
    assert 21 < net_runway_months(CASH, MRR, gross) < 21.5
    assert net_runway_months(CASH, 100, 50) == 999


def test_v2_monthly_dynamics_burn_net_and_runway():
    from server.services.simulation.engine import SimulationEngine
    from server.services.simulation.types import CompanyState

    state = CompanyState(mrr=MRR, burn_rate=NET + MRR, cash=CASH, customers=0, growth_rate=0.0)
    SimulationEngine(llm_client=None)._apply_monthly_dynamics(state)
    assert state.cash == pytest.approx(CASH - NET)
    assert state.runway_months == pytest.approx((CASH - NET) / NET)


def test_v2_initial_state_runway():
    from server.api.simulation_v2 import SimulationV2Request, build_simulation_v2_state
    from server.services.simulation.input_normalization import inputs_for_simulation_request

    req = SimulationV2Request(monthly_revenue=MRR, monthly_burn=NET + MRR, cash_balance=CASH)
    normalized, _ = inputs_for_simulation_request(req)
    state, _, _ = build_simulation_v2_state(normalized)
    assert state.runway_months == pytest.approx(EXPECTED_RUNWAY)


# --- 2. agent simulation (simulate-v2 page) ---------------------------------

def _demo_financials(**over):
    d = {"cash_balance": CASH, "monthly_burn": NET, "monthly_revenue": MRR, "growth_rate": 0, "gross_margin": 70}
    d.update(over)
    return d


def test_agent_sim_initial_state_treats_monthly_burn_as_net():
    from server.simulation_agents.agent_factory import build_initial_company_state

    st = build_initial_company_state(_demo_financials())
    assert st["runway_months"] == pytest.approx(EXPECTED_RUNWAY)
    assert st["net_burn"] == pytest.approx(NET)
    # Month-one cash flow in the loop: revenue * gm - operating_costs == -net.
    assert MRR * 0.70 - st["monthly_burn"] == pytest.approx(-NET)


def test_agent_sim_founder_not_told_runway_999():
    from server.simulation_agents.agent_factory import create_agents

    founder = create_agents(_demo_financials())[0]
    # runway ~21 -> confidence 0.7 (999 gave 0.85).
    assert founder.state.confidence == pytest.approx(0.7)


def test_agent_sim_month_advances_by_net_burn():
    from server.simulation_agents.agent_factory import build_initial_company_state
    from server.simulation_agents.simulation_orchestrator import _advance_financials

    random.seed(1)
    st = build_initial_company_state(_demo_financials())
    _advance_financials(st, 1, 0.0, 0.70, 0, 0, 1.0, {"market_growth": 0.5})
    assert st["cash_balance"] == pytest.approx(CASH - NET)
    assert st["runway_months"] == pytest.approx((CASH - NET) / NET)


def test_agent_sim_survival_is_relabelled_months_solvent():
    from server.simulation_agents.simulation_orchestrator import _compile_results
    from server.simulation_agents.environment_engine import EnvironmentEngine

    snaps = [
        {"month": m, "cash_balance": 1, "monthly_revenue": 1, "monthly_burn": 1,
         "runway_months": 1, "survival": m <= 3}
        for m in range(1, 5)
    ]
    out = _compile_results({"cash_balance": 0, "runway_months": 0}, snaps, [], [],
                           EnvironmentEngine({}), {}, {})
    assert out["summary"]["monthsSolventPct"] == 75.0
    assert out["summary"]["survivedHorizon"] is False
    assert out["summary"]["survivalProbability"] == 75.0  # deprecated alias


def test_agent_sim_headline_does_not_claim_probability():
    from server.simulation_agents.simulation_report import _generate_headline

    text = _generate_headline({"monthsSolventPct": 75}, "moderate")
    assert "probability" not in text.lower()
    assert "75%" in text


# --- 3. digital twin --------------------------------------------------------

def _cs(**over):
    d = dict(revenue_monthly=MRR, monthly_burn=NET, expenses_monthly=NET + MRR,
             cash_balance=CASH, revenue_growth_rate="0", snapshot_id="s1")
    d.update(over)
    return SimpleNamespace(**d)


def test_twin_inputs_month_one_burn_equals_net_burn():
    from server.services.digital_twin import build_twin_engine_inputs

    rec = SimpleNamespace(gross_margin=60.0, revenue=MRR, cogs=None, opex=10, payroll=30, other_costs=10)
    base = build_twin_engine_inputs(_cs(), rec)
    costs = base["opex"] + base["payroll"] + base["other_costs"]
    assert base["gross_margin"] == 60.0
    assert MRR * 0.60 - costs == pytest.approx(-NET)
    assert base["payroll"] == pytest.approx(costs * 0.6)  # real split, not 50%


def test_twin_inputs_unknown_margin_not_hardcoded_70():
    from server.services.digital_twin import build_twin_engine_inputs

    base = build_twin_engine_inputs(_cs(), None)
    assert base["gross_margin_known"] is False
    assert base["churn_rate"] == 0.0  # no invented 5% churn
    assert base["gross_margin"] != 70
    costs = base["opex"] + base["payroll"] + base["other_costs"]
    assert MRR * base["gross_margin"] / 100 - costs == pytest.approx(-NET)


def test_twin_summary_flattens_nested_engine_output():
    from server.services.digital_twin import build_twin_engine_inputs, summarize_twin_results
    from server.simulate.enhanced_monte_carlo import (
        EnhancedSimulationInputs, SimulationConfig, run_enhanced_monte_carlo,
    )

    base = build_twin_engine_inputs(_cs(), None)
    kwargs = {k: base[k] for k in ("baseline_revenue", "baseline_growth_rate", "gross_margin",
                                   "opex", "payroll", "other_costs", "cash_balance", "churn_rate")}
    res = run_enhanced_monte_carlo(EnhancedSimulationInputs(**kwargs),
                                   SimulationConfig(iterations=100, horizon_months=24, seed=1))
    s = summarize_twin_results(res)
    for k in ("p10_runway", "p50_runway", "p90_runway"):
        assert isinstance(s[k], float)
    assert 0 <= s["survival_probability"] <= 1
    assert s["iterations"] == 100
    assert 15 < s["p50_runway"] < 30


class _FakeQuery:
    def __init__(self, row):
        self.row = row

    def filter(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def first(self):
        return self.row


class _FakeDB:
    def __init__(self, cs):
        self.cs = cs

    def query(self, model):
        from server.models import CompanyState
        return _FakeQuery(self.cs if model is CompanyState else None)


def test_twin_engine_failure_returns_error_not_fabricated_percentiles(monkeypatch):
    import server.simulate.enhanced_monte_carlo as emc
    from server.services import digital_twin

    def boom(*a, **k):
        raise RuntimeError("engine down")

    monkeypatch.setattr(emc, "run_enhanced_monte_carlo", boom)
    out = digital_twin.run_twin_simulation(_FakeDB(_cs()), 1, {})
    assert out.get("error_code") == "simulation_failed"
    assert "results" not in out


def test_twin_success_path_returns_summary_and_iterations(monkeypatch):
    from server.services import digital_twin

    monkeypatch.setattr(digital_twin, "emit_twin_event", lambda *a, **k: None)
    monkeypatch.setattr(digital_twin, "TWIN_ITERATIONS", 50)
    out = digital_twin.run_twin_simulation(
        _FakeDB(_cs()), 1,
        {"hiring_plan": [{"count": 2, "start_month": 1, "monthly_cost": 10000}]},
    )
    assert out["summary"]["iterations"] == 50
    assert out["inputs"]["hiring_plan_mode"] in ("by_start_month", "from_month_1")
    # Two $10k hires shorten runway well below the ~21 months without them.
    assert out["summary"]["p50_runway"] < 16


# --- 4. public survival simulator ------------------------------------------

def test_survival_total_cost_equals_entered_expenses():
    from server.api.survival_simulator import survival_cost_lines

    c = survival_cost_lines(43949, 68058)
    fixed = c["opex"] + c["payroll"] + c["other_costs"]
    assert 43949 * c["gross_margin"] / 100 - fixed == pytest.approx(43949 - 68058)


@pytest.mark.parametrize("n,expected", [(0, 0), (1, 1), (2, 2), (3, 3), (5, 5), (8, 8)])
def test_survival_hire_split_keeps_total(n, expected):
    from server.api.survival_simulator import split_hires_by_quarter

    plan = split_hires_by_quarter(n, 8000)
    assert sum(h["count"] for h in plan) == expected
    assert sum(h["monthly_cost"] for h in plan) == expected * 8000


def test_survival_og_card_sentinel():
    from server.api.survival_og_card import og_runway_text

    assert og_runway_text(999)[0] == "36+"
    assert "999" not in "".join(og_runway_text(999))
    assert og_runway_text(14.6) == ("14", "months")


def test_survival_churn_reaches_engine(monkeypatch):
    import server.simulate.simulation_engine as se
    import server.api.survival_simulator as ss

    seen = {}

    def fake_mc(inputs, seed=None, distribution_limit=None):
        seen["growth"] = inputs.baseline_growth_rate
        raise RuntimeError("stop")

    monkeypatch.setattr(se, "run_monte_carlo", fake_mc)
    req = ss.SurvivalSimRequest(cash_on_hand=1, monthly_revenue=1, monthly_expenses=2,
                                growth_rate=5, monthly_churn=3)
    with pytest.raises(RuntimeError):
        ss.run_survival_simulation(req)
    assert seen["growth"] == 2


# --- 5. hiring planner -------------------------------------------------------

def test_hiring_planner_net_burn_canonical():
    from server.api.hiring_planner import canonical_net_burn

    assert canonical_net_burn({"net_burn": NET}, {}) == NET
    assert canonical_net_burn({"net_burn": {"value": NET}}, {}) == NET
    # Rebuilt: costs ex-COGS + COGS - revenue (COGS was dropped before).
    base = {"revenue": 100.0, "gross_margin": 60.0, "opex": 50.0, "payroll": 30.0, "other_costs": 0.0}
    assert canonical_net_burn({}, base) == pytest.approx(80 + 40 - 100)


# --- 7. copilot decision advisor --------------------------------------------

def _advisor():
    from server.copilot.agents.decision_advisor import DecisionAdvisorAgent
    return DecisionAdvisorAgent()


def test_decision_snapshot_reads_truth_scan_metrics():
    from server.copilot.agents.base import CompanyKnowledgeBase

    ckb = CompanyKnowledgeBase(company_id=1, company_name="x")
    ctx = {"truth_scan": {"metrics": {
        "monthly_revenue": MRR, "net_burn": NET, "cash_balance": CASH,
        "runway_p50": 21.3, "gross_margin": 62.0, "revenue_growth_mom": 4.0,
    }}}
    snap = _advisor()._get_financial_snapshot(ckb, ctx)
    assert snap["revenue"] == MRR
    assert snap["monthly_burn"] == NET
    assert snap["cash_balance"] == CASH
    assert snap["runway_months"] == 21.3
    assert snap["gross_margin"] == 62.0
    assert snap["growth_rate"] == 4.0
    assert snap["churn_rate"] is None  # not invented


def test_decision_snapshot_no_invented_defaults():
    from server.copilot.agents.base import CompanyKnowledgeBase

    snap = _advisor()._get_financial_snapshot(CompanyKnowledgeBase(company_id=1, company_name="x"), {})
    assert all(v is None for v in snap.values())


def test_decision_no_data_runs_no_simulation():
    from server.copilot.agents.base import CompanyKnowledgeBase

    ckb = CompanyKnowledgeBase(company_id=1, company_name="x")
    resp = asyncio.run(_advisor().process("how can i extend runway", ckb, {}))
    out = resp.decision_advisor_output
    assert out["simulations"] == []
    assert out["simulation_status"]["ran"] is False
    assert "No simulation was run" in out["recommendation"]["details"]


def test_decision_simulations_come_from_engine():
    adv = _advisor()
    adv.SIMULATION_RUNS = 60
    fin = {"revenue": MRR, "monthly_burn": NET, "cash_balance": CASH, "runway_months": EXPECTED_RUNWAY,
           "gross_margin": 70.0, "growth_rate": 0.0, "payroll": None, "opex": None, "other_costs": None,
           "headcount": None, "arpu": None, "churn_rate": None}
    from server.copilot.agents.decision_advisor import DecisionContext, DecisionType
    decision = DecisionContext(decision_type=DecisionType.COST_OPTIMIZATION, core_decision="x",
                               target_outcome="x", timeframe_months=12,
                               levers_available=["burn_reduction", "margin_improvement"])
    levers = adv.map_decision_to_levers(decision, fin)
    outcomes = asyncio.run(adv._run_decision_simulations(decision, levers, fin, {}))
    assert adv.simulation_status["ran"] is True
    base = outcomes[0]
    assert 15 < base.runway_p50 < 30
    # Not the old 0.7x / 1.3x fabrication.
    assert base.runway_p10 != pytest.approx(base.runway_p50 * 0.7)
    burn_cut = next(o for o in outcomes if o.lever_combination == ["Burn Rate Reduction"])
    assert burn_cut.runway_p50 > base.runway_p50
