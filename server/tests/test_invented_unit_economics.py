"""/metrics/computed must not pass on unit economics the truth scan invented.

A D2C founder typed revenue, margin, costs, cash and headcount -- no marketing
spend, no customers. The truth scan still wrote CAC 20,000 (30% of payroll as
"marketing"), LTV 2.9L and LTV:CAC 14.3x from a 150-customer book, flagged
them on `_estimated_metrics`, and /metrics/computed handed them to every
screen as plain numbers. Values on the founder's own FinancialRecord are
unaffected.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from server.api.ingest import get_computed_metrics
from server.truth.invented_metrics import strip_invented_unit_economics

TS_METRICS = {
    "monthly_revenue": 2_500_000.0,
    "cash_balance": 30_000_000.0,
    "gross_margin": 55.0,
    "net_burn": -575_000.0,
    "net_revenue_retention": 108,
    "arpu": 16_666.67,
    "customer_count": 150,
    "cac": 20_000.0,
    "ltv": 286_458.33,
    "ltv_cac_ratio": 14.32,
    "payback_months": 3,
    "headcount": 14,
    "_estimated_metrics": [
        "arpu", "customer_count", "churn_rate", "cac", "ltv",
        "ltv_cac_ratio", "payback_months", "net_revenue_retention",
    ],
}


def _record(**overrides):
    base = dict(
        revenue=2_500_000.0, mrr=2_500_000.0, arr=30_000_000.0, cash_balance=30_000_000.0,
        payroll=800_000.0, marketing_expense=None, opex=0.0, cogs=1_125_000.0,
        other_costs=0.0, gross_margin=55.0, net_burn=-575_000.0, runway_months=None,
        ltv=None, cac=None, ltv_cac_ratio=None, customers=None, headcount=14, arpu=None,
        ndr=None, mom_growth=None, burn_multiple=None, period_end=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _computed(record, ts_metrics):
    db = MagicMock()
    company = SimpleNamespace(id=1, user_id=1, currency="INR")
    q = db.query.return_value.filter.return_value
    q.first.return_value = company
    scan = SimpleNamespace(outputs_json={"metrics": ts_metrics})
    q.order_by.return_value.first.side_effect = [record, scan]
    return asyncio.run(get_computed_metrics(1, db=db, current_user=SimpleNamespace(id=1)))


def test_strip_drops_only_flagged_unit_economics():
    out = strip_invented_unit_economics(TS_METRICS)
    for key in ("cac", "ltv", "ltv_cac_ratio", "payback_months", "arpu",
                "customer_count", "net_revenue_retention"):
        assert key not in out, key
    # Real figures and the flag list itself pass through.
    assert out["monthly_revenue"] == 2_500_000.0
    assert out["gross_margin"] == 55.0
    assert out["net_burn"] == -575_000.0
    assert out["headcount"] == 14
    assert out["_estimated_metrics"] == TS_METRICS["_estimated_metrics"]


def test_strip_keeps_unflagged_unit_economics():
    ts = {"cac": 900.0, "ltv": 5_400.0, "_estimated_metrics": []}
    assert strip_invented_unit_economics(ts) == ts


def test_strip_tolerates_bad_input():
    assert strip_invented_unit_economics(None) == {}
    assert strip_invented_unit_economics({"cac": 1, "_estimated_metrics": "cac"}) == {
        "cac": 1, "_estimated_metrics": "cac",
    }


def test_computed_does_not_return_invented_cac_ltv():
    out = _computed(_record(), TS_METRICS)
    assert out["cac"] == 0
    assert out["ltv"] == 0
    assert out["ltvCacRatio"] == 0
    assert out["paybackPeriod"] == 0
    assert out["totalCustomers"] == 0
    assert out["arpu"] == 0
    assert out["ndr"] == 0


def test_computed_burn_and_margin_unchanged():
    out = _computed(_record(), TS_METRICS)
    assert out["netBurn"] == -575_000.0
    assert out["runway"] == 999
    assert out["grossMarginPct"] == 55.0
    assert out["headcount"] == 14


def test_computed_keeps_founder_reported_unit_economics():
    rec = _record(cac=4_000.0, ltv=24_000.0, ltv_cac_ratio=6.0, customers=500)
    out = _computed(rec, TS_METRICS)
    assert out["cac"] == 4_000.0
    assert out["ltv"] == 24_000.0
    assert out["ltvCacRatio"] == 6.0
    assert out["totalCustomers"] == 500
    assert out["arpu"] == 5_000.0
