"""D2C contribution margin, worked by hand for a ₹15L/month brand.

1000 orders shipped at ₹1500 gross (₹15,00,000), ₹1,50,000 discounts,
200 RTO (20%), 20 delivered orders returned worth ₹30,000, 60% COD.

  net order value      15,00,000 - 1,50,000            = 13,50,000  (₹1350 / shipped)
  RTO value            1350 x 200                      =  2,70,000
  net revenue          13,50,000 - 2,70,000 - 30,000   = 10,50,000
  CM1                  10,50,000 - COGS 3,00,000       =  7,50,000
  fulfilment           60x1000 + 50x200 + 15x1000 + 80x20 = 86,600
  payment              2% x (1350 x 800 x 0.4) + 30 x 480  = 8,640 + 14,400 = 23,040
  CM2                  7,50,000 - 86,600 - 23,040      =  6,40,360
  CM3                  6,40,360 - marketing 4,00,000   =  2,40,360  (₹300.45 / delivered order)
  RTO logistics burnt  (60 + 50 + 15) x 200            =    25,000
"""

import pytest

from server.core.d2c import D2CPeriodInputs, compute_unit_economics


def _brand(**overrides) -> D2CPeriodInputs:
    base = dict(
        orders_shipped=1000,
        gross_sales=1_500_000,
        discounts=150_000,
        rto_orders=200,
        customer_returns_value=30_000,
        customer_returns_orders=20,
        cogs=300_000,
        forward_shipping_per_order=60,
        rto_shipping_per_order=50,
        packaging_per_order=15,
        return_shipping_per_order=80,
        cod_share=0.6,
        payment_gateway_pct=0.02,
        cod_fee_per_order=30,
        marketing_spend=400_000,
        new_customers=500,
    )
    base.update(overrides)
    return D2CPeriodInputs(**base)


def test_worked_example():
    ue = compute_unit_economics(_brand())
    assert ue.delivered_orders == 800
    assert ue.net_revenue == pytest.approx(1_050_000)
    assert ue.cm1 == pytest.approx(750_000)
    assert ue.cm2 == pytest.approx(640_360)
    assert ue.cm3 == pytest.approx(240_360)
    assert ue.cm3_per_order == pytest.approx(300.45)
    assert ue.aov == pytest.approx(1312.5)
    assert ue.rto_rate == pytest.approx(0.2)
    assert ue.rto_cost == pytest.approx(25_000)
    assert ue.mer == pytest.approx(2.625)
    assert ue.cac == pytest.approx(800)
    assert ue.cm1_pct == pytest.approx(750_000 / 1_050_000)
    assert ue.missing == []


def test_rto_is_what_kills_margin():
    clean = compute_unit_economics(_brand(rto_orders=0))
    heavy = compute_unit_economics(_brand(rto_orders=300))
    # No RTO: CM3 ₹5,14,600 on 1000 delivered = ₹514.6/order.
    # 30% RTO: ₹1,03,240 on 700 delivered = ₹147.5/order, under a third.
    assert clean.cm3_per_order == pytest.approx(514.6)
    assert heavy.cm3_per_order == pytest.approx(103_240 / 700)
    assert heavy.cm3_per_order < 0.3 * clean.cm3_per_order


def test_missing_costs_are_reported_not_zeroed():
    ue = compute_unit_economics(_brand(forward_shipping_per_order=None, marketing_spend=None))
    assert ue.cm1 == pytest.approx(750_000), "CM1 does not need shipping"
    assert ue.cm2 is None and ue.cm3 is None
    assert "forward_shipping_per_order" in ue.missing
    assert "marketing_spend" in ue.missing


def test_missing_cogs_leaves_every_layer_unknown():
    ue = compute_unit_economics(_brand(cogs=None))
    assert ue.cm1 is None and ue.cm2 is None and ue.cm3 is None
    assert ue.net_revenue == pytest.approx(1_050_000)
    assert "cogs" in ue.missing


def test_rto_needs_its_reverse_leg_cost():
    ue = compute_unit_economics(_brand(rto_shipping_per_order=None))
    assert ue.cm2 is None
    assert "rto_shipping_per_order" in ue.missing


def test_no_rto_does_not_ask_for_rto_cost():
    ue = compute_unit_economics(_brand(rto_orders=0, rto_shipping_per_order=None))
    assert "rto_shipping_per_order" not in ue.missing
    assert ue.cm2 is not None


@pytest.mark.parametrize("bad", [
    dict(rto_orders=1001),
    dict(orders_shipped=-1),
    dict(cod_share=1.5),
    dict(payment_gateway_pct=2.0),
])
def test_rejects_impossible_inputs(bad):
    with pytest.raises(ValueError):
        compute_unit_economics(_brand(**bad))


def test_zero_orders_does_not_divide_by_zero():
    ue = compute_unit_economics(D2CPeriodInputs(orders_shipped=0, gross_sales=0, cogs=0))
    assert ue.aov is None and ue.rto_rate is None and ue.cm1_per_order is None


# --- API ---------------------------------------------------------------------

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import d2c as d2c_api


def _api() -> TestClient:
    app = FastAPI()
    app.include_router(d2c_api.router)
    return TestClient(app)


def test_api_returns_the_same_numbers():
    body = {k: v for k, v in _brand().__dict__.items()}
    res = _api().post("/d2c/unit-economics", json=body)
    assert res.status_code == 200
    data = res.json()
    assert data["cm3"] == pytest.approx(240_360)
    assert data["missing"] == []


def test_api_rejects_rto_above_shipped():
    res = _api().post("/d2c/unit-economics", json={"orders_shipped": 10, "gross_sales": 1000, "rto_orders": 11})
    assert res.status_code == 422


def test_api_rejects_out_of_range():
    res = _api().post("/d2c/unit-economics", json={"orders_shipped": 10, "gross_sales": 1000, "cod_share": 3})
    assert res.status_code == 422
