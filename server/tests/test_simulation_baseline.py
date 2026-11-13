"""HAG-459: a scenario simulation must not invent the company's baseline.

Three call sites built ``EnhancedSimulationInputs`` with hard-coded constants --
$100,000 revenue, 5% growth, 70% gross margin, $20,000 opex, $50,000 payroll,
$10,000 other, $500,000 cash, 5% churn. Any scenario that did not carry a
baseline key was simulated on that fictional business, and the result was
indistinguishable from a real one: no warning, no label, a runway number for
numbers nobody entered.

The fix resolves a missing baseline the way ``POST /api/simulations`` and the
dashboard already do -- latest truth scan, then the latest P&L record -- and
fails loudly when there is no data at all. Values written on the scenario still
win, so nothing that worked before changes.
"""


import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.core.db import Base
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.models.scenario import Scenario
from server.models.truth_scan import TruthScan
from server.simulate.baseline import MissingBaseline, enhanced_inputs_from_scenario

REVENUE, CASH, GM, BURN = 3_600.0, 815_430.0, -56.0, 64_980.0
INVENTED = {
    "baseline_revenue": 100_000,
    "baseline_growth_rate": 5,
    "gross_margin": 70,
    "cash_balance": 500_000,
}


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__,
            FinancialRecord.__table__,
            Scenario.__table__,
            TruthScan.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _company(db) -> int:
    company = Company(name="AlphaKids", user_id=1)
    db.add(company)
    db.flush()
    return company.id


def _scenario(db, company_id: int, inputs: dict) -> Scenario:
    scenario = Scenario(company_id=company_id, name="Base", inputs_json=inputs)
    db.add(scenario)
    db.flush()
    return scenario


def _truth_scan(db, company_id: int, metrics: dict) -> None:
    db.add(TruthScan(company_id=company_id, outputs_json={"metrics": metrics}))
    db.flush()


def test_a_scenario_without_baselines_uses_the_companys_numbers(db):
    company_id = _company(db)
    _truth_scan(db, company_id, {
        "monthly_revenue": REVENUE,
        "cash_balance": CASH,
        "gross_margin": GM,
        "net_burn": BURN,
    })
    scenario = _scenario(db, company_id, {"burn_reduction_pct": 10})

    inputs = enhanced_inputs_from_scenario(db, scenario)

    assert inputs.baseline_revenue == REVENUE
    assert inputs.cash_balance == CASH
    assert inputs.gross_margin == GM
    assert inputs.churn_rate == 0, "churn must be the company's, never an invented 5%"
    assert inputs.burn_reduction_pct == 10, "scenario knobs still apply"


def test_the_simulated_burn_is_the_companys_real_burn(db):
    company_id = _company(db)
    _truth_scan(db, company_id, {
        "monthly_revenue": REVENUE,
        "cash_balance": CASH,
        "gross_margin": GM,
        "net_burn": BURN,
    })
    scenario = _scenario(db, company_id, {})

    inputs = enhanced_inputs_from_scenario(db, scenario)
    month_one = (
        inputs.baseline_revenue * inputs.gross_margin / 100
        - (inputs.opex + inputs.payroll + inputs.other_costs)
    )
    assert month_one == pytest.approx(-BURN)


def test_with_no_baseline_and_no_data_it_refuses_instead_of_inventing(db):
    scenario = _scenario(db, _company(db), {"pricing_change_pct": 5})

    with pytest.raises(MissingBaseline) as excinfo:
        enhanced_inputs_from_scenario(db, scenario)

    message = str(excinfo.value)
    assert "no baseline financials" in message
    assert "truth scan" in message


def test_baselines_entered_on_the_scenario_still_win(db):
    scenario = _scenario(db, _company(db), {
        "baseline_revenue": 1_234,
        "baseline_growth_rate": 2,
        "gross_margin": 40,
        "opex": 10,
        "payroll": 20,
        "other_costs": 30,
        "cash_balance": 456,
        "churn_rate": 1,
    })

    inputs = enhanced_inputs_from_scenario(db, scenario)

    assert inputs.baseline_revenue == 1_234
    assert inputs.cash_balance == 456
    assert inputs.churn_rate == 1


def test_hiring_and_churn_knobs_reach_the_engine(db):
    scenario = _scenario(db, _company(db), {
        "baseline_revenue": 1_234,
        "baseline_growth_rate": 2,
        "gross_margin": 40,
        "opex": 10,
        "payroll": 20,
        "other_costs": 30,
        "cash_balance": 456,
        "churn_rate": 1,
        "churn_change_pct": 1.5,
        "cac_change_pct": -10,
        "hiring_plan": [{"count": 2, "start_month": 3, "monthly_cost": 8000}],
    })

    inputs = enhanced_inputs_from_scenario(db, scenario)

    assert inputs.churn_change_pct == 1.5
    assert inputs.cac_change_pct == -10
    assert inputs.hiring_plan == [{"count": 2, "start_month": 3, "monthly_cost": 8000}]


def test_no_call_site_can_reintroduce_the_invented_baseline():
    """A source guard, so another copy of the old constructor fails here rather
    than shipping. The job route, the handler, and the worker Node starts
    are the sites that used to carry the constants."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    sites = [
        root / "server/api/simulation_jobs.py",
        root / "server/workers/handlers/simulation_handler.py",
        root / "server/workers/simulation_worker.py",
    ]
    for path in sites:
        source = path.read_text()
        assert "enhanced_inputs_from_scenario" in source, f"{path.name}: not using the shared builder"
        assert 'inputs_json.get("baseline_revenue", 100000)' not in source, f"{path.name}: invented baseline is back"
        assert 'inputs_json.get("cash_balance", 500000)' not in source, f"{path.name}: invented baseline is back"
        assert 'inputs_json.get("churn_rate", 5)' not in source, f"{path.name}: invented churn is back"
