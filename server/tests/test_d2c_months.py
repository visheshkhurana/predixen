"""Monthly D2C inputs: storage, source precedence, and the company API."""

from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api import d2c as d2c_api
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.company import Company
from server.models.d2c_month import D2CMonth
from server.models.user import User
from server.services import d2c_months


@pytest.fixture
def Session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(engine, tables=[User.__table__, Company.__table__, D2CMonth.__table__])
    S = sessionmaker(bind=engine)
    db = S()
    owner = User(email="owner@brand.in", is_active=True)
    other = User(email="other@brand.in", is_active=True)
    db.add_all([owner, other])
    db.flush()
    db.add(Company(id=1, name="Brand", user_id=owner.id, currency="INR"))
    db.commit()
    db.close()
    return S


def test_manual_entry_survives_the_next_sync(Session):
    db = Session()
    d2c_months.upsert_month(db, 1, date(2026, 10, 15), {"cogs": 300_000}, source="manual")
    d2c_months.upsert_month(db, 1, date(2026, 10, 1), {"cogs": 1, "orders_shipped": 1000}, source="shopify")
    row = db.query(D2CMonth).one()
    assert row.period == date(2026, 10, 1)
    assert row.cogs == 300_000, "a sync never overwrites a founder's number"
    assert row.orders_shipped == 1000
    assert row.field_sources == {"cogs": "manual", "orders_shipped": "shopify"}


def test_connector_none_does_not_erase_but_manual_none_clears(Session):
    db = Session()
    d2c_months.upsert_month(db, 1, date(2026, 10, 1), {"orders_shipped": 1000}, source="shopify")
    d2c_months.upsert_month(db, 1, date(2026, 10, 1), {"orders_shipped": None}, source="shopify")
    assert db.query(D2CMonth).one().orders_shipped == 1000
    d2c_months.upsert_month(db, 1, date(2026, 10, 1), {"orders_shipped": None}, source="manual")
    row = db.query(D2CMonth).one()
    assert row.orders_shipped is None and "orders_shipped" not in row.field_sources


def test_shopify_mapping():
    values = d2c_months.shopify_values({"orders": 601, "net_sales_ex_gst": 601_000.0, "refunds": 2_000.0, "cod_share": 0.6})
    assert values == {
        "orders_shipped": 601, "gross_sales": 601_000.0, "discounts": 0.0,
        "customer_returns_value": 2_000.0, "cod_share": 0.6, "new_customers": None,
    }


def _client(Session, email):
    app = FastAPI()
    app.include_router(d2c_api.company_router)

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    def _user():
        s = Session()
        return s.query(User).filter(User.email == email).one()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    return TestClient(app)


def test_api_round_trip_computes_cm(Session):
    client = _client(Session, "owner@brand.in")
    body = {
        "orders_shipped": 1000, "gross_sales": 1_500_000, "discounts": 150_000, "rto_orders": 200,
        "customer_returns_value": 30_000, "customer_returns_orders": 20, "cogs": 300_000,
        "forward_shipping_per_order": 60, "rto_shipping_per_order": 50, "packaging_per_order": 15,
        "return_shipping_per_order": 80, "cod_share": 0.6, "payment_gateway_pct": 0.02,
        "cod_fee_per_order": 30, "marketing_spend": 400_000,
    }
    res = client.put("/companies/1/d2c/months/2026-10", json=body)
    assert res.status_code == 200, res.text
    assert res.json()["unit_economics"]["cm3"] == pytest.approx(240_360)

    listed = client.get("/companies/1/d2c/months").json()["months"]
    assert listed[0]["period"] == "2026-10-01"
    assert listed[0]["sources"]["cogs"] == "manual"


def test_partial_month_says_what_is_missing(Session):
    client = _client(Session, "owner@brand.in")
    res = client.put("/companies/1/d2c/months/2026-09", json={"cogs": 100})
    assert res.status_code == 200
    assert res.json()["unit_economics"] is None
    assert set(res.json()["missing"]) == {"orders_shipped", "gross_sales"}


def test_impossible_month_is_rejected_and_not_saved(Session):
    client = _client(Session, "owner@brand.in")
    res = client.put("/companies/1/d2c/months/2026-08", json={"orders_shipped": 10, "gross_sales": 100, "rto_orders": 11})
    assert res.status_code == 422
    assert client.get("/companies/1/d2c/months").json()["months"] == []


@pytest.mark.parametrize("period", ["2026-13", "26-10", "2026-1", "x"])
def test_bad_period(Session, period):
    res = _client(Session, "owner@brand.in").put(f"/companies/1/d2c/months/{period}", json={})
    assert res.status_code == 422


def test_other_users_cannot_read_or_write(Session):
    client = _client(Session, "other@brand.in")
    assert client.get("/companies/1/d2c/months").status_code == 403
    assert client.put("/companies/1/d2c/months/2026-10", json={"cogs": 1}).status_code == 403
