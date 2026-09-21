"""Sample-data first-run snapshot: labelled inputs must match calculated insight."""
import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "services" / "sample_data.py"
_spec = importlib.util.spec_from_file_location("fc_sample_data", _PATH)
assert _spec and _spec.loader
sample_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sample_data)

SAMPLE_FINANCIALS = sample_data.SAMPLE_FINANCIALS
build_sample_months = sample_data.build_sample_months
derive_sample_insight = sample_data.derive_sample_insight
sample_monthly_expenses = sample_data.sample_monthly_expenses


def test_canonical_insight_is_27k_burn_and_27_8_runway():
    insight = derive_sample_insight()
    expenses = sample_monthly_expenses()
    assert expenses == 72000.0
    assert insight["inputs"]["monthly_revenue"] == 45000.0
    assert insight["inputs"]["monthly_expenses"] == 72000.0
    assert insight["inputs"]["cash_balance"] == 750000.0
    assert insight["outputs"]["monthly_burn"] == 27000.0
    assert insight["outputs"]["runway_months"] == 27.8


def test_latest_seeded_month_matches_canonical_snapshot():
    months = build_sample_months(12)
    assert len(months) == 12
    latest = months[-1]
    assert latest["monthly_revenue"] == SAMPLE_FINANCIALS["monthly_revenue"]
    assert latest["opex"] == SAMPLE_FINANCIALS["opex"]
    assert latest["payroll"] == SAMPLE_FINANCIALS["payroll"]
    assert latest["other_costs"] == SAMPLE_FINANCIALS["other_costs"]
    assert latest["cash_balance"] == SAMPLE_FINANCIALS["cash_balance"]
    insight = derive_sample_insight(
        latest["monthly_revenue"],
        sample_monthly_expenses(latest),
        latest["cash_balance"],
    )
    assert insight["outputs"]["monthly_burn"] == 27000.0
    assert insight["outputs"]["runway_months"] == 27.8


def test_computed_metrics_formula_includes_breakdown_not_cogs_double_count():
    """cogs and marketing are zero in the snapshot so the onboarding card
    (opex+payroll+other) matches GET /metrics/computed (those plus cogs + marketing)."""
    snap = SAMPLE_FINANCIALS
    card_expenses = snap["opex"] + snap["payroll"] + snap["other_costs"]
    computed_expenses = card_expenses + snap["cogs"] + snap["marketing_expense"]
    assert card_expenses == computed_expenses == 72000.0
