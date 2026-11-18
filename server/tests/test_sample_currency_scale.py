"""Sample data loaded into a company is sized for that company's currency."""

from server.services.sample_data import build_sample_months, derive_sample_insight, sample_monthly_expenses, sample_scale


def test_inr_sample_is_rupee_sized_with_same_runway():
    usd = build_sample_months(12, sample_scale("USD"))[-1]
    inr = build_sample_months(12, sample_scale("INR"))[-1]
    assert inr["monthly_revenue"] == usd["monthly_revenue"] * 20
    assert inr["cash_balance"] == usd["cash_balance"] * 20
    run = lambda m: derive_sample_insight(m["monthly_revenue"], sample_monthly_expenses(m), m["cash_balance"])["outputs"]["runway_months"]
    assert run(inr) == run(usd) == 27.8


def test_unknown_currency_keeps_dollar_size():
    assert sample_scale(None) == 1.0
    assert sample_scale("JPY") == 1.0
    assert sample_scale("inr") == 20.0
