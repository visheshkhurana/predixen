"""Audit 2026-10-15: one company, four runways; gross margin x100 per layer.

AlphaKids from TEST-REPORT-2026-09-16: $815,430 cash, $3,600 MRR, $68,580/mo
of entered costs, -56% gross margin -> burn $64,980, runway 12.55 months.
Onboarding said 12.5; the dashboard said 11.6 (COGS added on top of the
entered costs); -56% rendered as -5600%; the simulations ran it at +10%.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from server.api.datasets import split_cogs_from_entered_costs
from server.api.ingest import get_computed_metrics
from server.api.simulations import resolve_baseline_financials
from server.core.units import clamp_gross_margin_pct, gross_margin_pct
from server.simulate.simulation_engine import SimulationInputs, run_monte_carlo

CASH, MRR, GM = 815_430.0, 3_600.0, -56.0
OPEX, PAYROLL, OTHER = 20_000.0, 40_000.0, 8_580.0  # entered costs: 68,580
BURN = OPEX + PAYROLL + OTHER - MRR                   # 64,980
RUNWAY = CASH / BURN                                   # 12.55


# --- units -------------------------------------------------------------------

@pytest.mark.parametrize("raw,pct", [
    (-56, -56.0), (75, 75.0), (0.65, 65.0), (-0.4, -40.0), (0, 0.0), (100, 100.0),
    (None, None), ("abc", None),
])
def test_gross_margin_pct(raw, pct):
    assert gross_margin_pct(raw) == pct


def test_clamp_keeps_negative_margins_negative():
    assert clamp_gross_margin_pct(-56) == -56
    assert clamp_gross_margin_pct(-900) == -200
    assert clamp_gross_margin_pct(140) == 95


# --- manual baseline storage -------------------------------------------------

def test_split_keeps_the_entered_total():
    s = split_cogs_from_entered_costs(MRR, GM, OPEX, PAYROLL, OTHER)
    assert s["cogs"] == pytest.approx(MRR * 1.56)
    assert s["total_costs"] == pytest.approx(OPEX + PAYROLL + OTHER)
    assert s["opex"] == pytest.approx(OPEX - MRR * 1.56)
    assert s["other_costs"] == OTHER
    assert s["gross_margin_pct"] == -56.0


def test_split_spills_into_other_costs_then_raises_total():
    s = split_cogs_from_entered_costs(10_000, 20, opex=3_000, payroll=5_000, other_costs=4_000)
    assert s["cogs"] == 8_000 and s["opex"] == 0 and s["other_costs"] == 0
    assert s["total_costs"] == 13_000  # inputs imply more cost than opex+other held


def test_split_with_no_revenue_has_no_cogs():
    s = split_cogs_from_entered_costs(0, 70, OPEX, PAYROLL, OTHER)
    assert s["cogs"] == 0 and s["total_costs"] == OPEX + PAYROLL + OTHER


# --- dashboard: /metrics/computed ---------------------------------------------

def _stored_alphakids_record():
    s = split_cogs_from_entered_costs(MRR, GM, OPEX, PAYROLL, OTHER)
    return SimpleNamespace(
        revenue=MRR, mrr=MRR, arr=MRR * 12, cash_balance=CASH, payroll=PAYROLL,
        marketing_expense=None, opex=s["opex"], cogs=s["cogs"], other_costs=s["other_costs"],
        gross_margin=s["gross_margin_pct"], net_burn=BURN, runway_months=round(RUNWAY, 1),
        ltv=None, cac=None, ltv_cac_ratio=None, customers=None, headcount=7, arpu=None,
        ndr=None, mom_growth=None, burn_multiple=None, period_end=None,
    )


def _computed(record):
    db = MagicMock()
    company = SimpleNamespace(id=1, user_id=1, currency="USD")
    q = db.query.return_value.filter.return_value
    q.first.return_value = company
    q.order_by.return_value.first.side_effect = [record, None]
    import asyncio
    return asyncio.run(get_computed_metrics(1, db=db, current_user=SimpleNamespace(id=1)))


def test_dashboard_runway_matches_onboarding():
    out = _computed(_stored_alphakids_record())
    assert out["netBurn"] == pytest.approx(BURN)
    assert out["runway"] == pytest.approx(RUNWAY)
    assert out["totalExpenses"] == pytest.approx(OPEX + PAYROLL + OTHER)


def test_dashboard_negative_margin_is_not_multiplied():
    out = _computed(_stored_alphakids_record())
    assert out["grossMarginPct"] == pytest.approx(-56.0)
    assert out["grossMarginDecimal"] == pytest.approx(-0.56)


def test_dashboard_legacy_fraction_margin_still_reads_as_percent():
    rec = _stored_alphakids_record()
    rec.gross_margin = 0.65
    assert _computed(rec)["grossMarginPct"] == pytest.approx(65.0)


# --- simulation baseline ------------------------------------------------------

def _alphakids_sim():
    resolved = resolve_baseline_financials({}, _stored_alphakids_record())
    inputs = SimulationInputs(
        baseline_revenue=resolved["revenue"], baseline_growth_rate=0.0,
        gross_margin=resolved["gross_margin"], opex=resolved["opex"],
        payroll=resolved["payroll"], other_costs=resolved["other_costs"],
        cash_balance=resolved["cash"], n_simulations=200, growth_sigma=0.0,
        margin_sigma=0.0, cost_sigma=0.0, expense_shock_prob=0.0,
    )
    return resolved, run_monte_carlo(inputs, seed=7)


def test_simulation_baseline_keeps_the_negative_margin():
    resolved, _ = _alphakids_sim()
    assert resolved["gross_margin"] == pytest.approx(-56.0)


def test_simulated_burn_equals_the_dashboard_burn():
    # With every noise term at zero the engine's month-1 burn is exact. Clamped
    # to +10% margin it charged $62,604 instead of $64,980.
    _, out = _alphakids_sim()
    assert out["bands"]["burn"]["p50"][0] == pytest.approx(BURN)


def test_simulated_runway_agrees_with_onboarding():
    _, out = _alphakids_sim()
    assert out["runway"]["p50"] == pytest.approx(12.5, abs=0.11)  # was 13.0


# --- end to end: onboarding save -> dashboard ---------------------------------

def test_onboarding_save_then_dashboard_shows_onboardings_runway(monkeypatch):
    from server.api import datasets as datasets_api
    from server.models.financial import FinancialRecord

    monkeypatch.setattr(
        "server.services.sample_data.on_real_financials_written", lambda *a, **k: None
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=1, user_id=1)
    baseline = datasets_api.ManualBaseline(
        monthly_revenue=MRR, gross_margin_pct=GM, opex=OPEX, payroll=PAYROLL,
        other_costs=OTHER, cash_balance=CASH, headcount=7,
    )
    datasets_api.manual_baseline(1, baseline, db=db, current_user=SimpleNamespace(id=1))
    stored = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], FinancialRecord))

    for attr in ("marketing_expense", "ltv", "cac", "ltv_cac_ratio", "customers", "arpu",
                 "ndr", "mom_growth", "burn_multiple", "period_end"):
        if getattr(stored, attr, None) is None:
            setattr(stored, attr, None)
    out = _computed(stored)
    assert out["runway"] == pytest.approx(RUNWAY)  # was 11.55 with COGS added on top
    assert out["netBurn"] == pytest.approx(BURN)
    assert out["grossMarginPct"] == pytest.approx(-56.0)
    assert stored.runway_months == pytest.approx(round(RUNWAY, 1))
