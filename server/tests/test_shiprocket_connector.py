"""Shiprocket: shipped orders, RTO, returns, COD share and freight per order."""

import asyncio
from datetime import date, datetime
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.connectors import shiprocket
from server.connectors.base import ConnectorConfig
from server.models.company import Company
from server.models.d2c_month import D2CMonth
from server.models.user import User
from server.services import d2c_months


def _order(oid, status, payment="cod", awb=None):
    return {"id": oid, "status": status, "payment_method": payment,
            "shipments": [{"awb": awb or f"AWB{oid}", "return_awb": ""}]}


@pytest.mark.parametrize("status,kind", [
    ("DELIVERED", "delivered"),
    ("RTO DELIVERED", "rto"),
    ("RTO_IN_TRANSIT", "rto"),
    ("RTO INITIATED", "rto"),
    ("Return Delivered", "returned"),
    ("CANCELED", "cancelled"),
    ("CANCELLED_BEFORE_DISPATCHED", "cancelled"),
    ("IN TRANSIT", "in_transit"),
    ("OUT FOR DELIVERY", "in_transit"),
    ("READY TO SHIP", "not_shipped"),
    ("LOST", "lost"),
    ("SOMETHING NEW", "other"),
])
def test_classify(status, kind):
    assert shiprocket.classify({"status": status}) == kind


def _month():
    orders = (
        [_order(i, "DELIVERED", "cod" if i < 50 else "prepaid") for i in range(80)]
        + [_order(100 + i, "RTO DELIVERED", "cod") for i in range(15)]
        + [_order(200 + i, "IN TRANSIT", "prepaid") for i in range(5)]
        + [_order(300, "CANCELED"), _order(301, "READY TO SHIP")]
    )
    statement = (
        [{"awb_code": f"AWB{i}", "debit_amount": "65.00", "description": "Freight Charges"} for i in range(80)]
        + [{"awb_code": f"AWB{100 + i}", "debit_amount": "65.00", "description": "Freight Charges"} for i in range(15)]
        + [{"awb_code": f"AWB{100 + i}", "debit_amount": "55.00", "description": "RTO Freight Charges"} for i in range(15)]
        + [{"awb_code": f"AWB{200 + i}", "debit_amount": "65.00", "description": "Freight Charges"} for i in range(5)]
        + [{"awb_code": "OTHER-MONTH", "debit_amount": "999", "description": "Freight Charges"},
           {"awb_code": "", "debit_amount": "", "description": "Wallet Balance"}]
    )
    return orders, statement


def test_summary():
    s = shiprocket.summarize_shipments(*_month())
    assert s["orders_shipped"] == 100  # 80 delivered + 15 RTO + 5 in transit
    assert s["rto_orders"] == 15
    assert s["cancelled"] == 1 and s["not_shipped"] == 1
    assert s["cod_share"] == pytest.approx(65 / 100)
    assert s["rto_rate_resolved"] == pytest.approx(15 / 95, abs=1e-4)
    assert s["forward_shipping_per_order"] == pytest.approx(65.0)
    assert s["rto_shipping_per_order"] == pytest.approx(55.0)
    assert s["freight_rows_matched"] == 115, "other months' AWBs and balance rows are ignored"


def test_unbilled_freight_is_missing_not_free():
    orders, _ = _month()
    s = shiprocket.summarize_shipments(orders, [])
    assert s["forward_shipping_per_order"] is None
    assert s["rto_shipping_per_order"] is None


def test_sync_against_mocked_api():
    orders, statement = _month()
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, dict(request.url.params)))
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(200, json={"token": "t"})
        assert request.headers["authorization"] == "Bearer t"
        page = int(request.url.params["page"])
        data = orders if request.url.path.endswith("/orders") else statement
        chunk = data[(page - 1) * 60: page * 60]
        return httpx.Response(200, json={"data": chunk, "meta": {"pagination": {"total_pages": (len(data) + 59) // 60}}})

    conn = shiprocket.ShiprocketConnector(ConnectorConfig(
        provider_id="shiprocket", company_id=1, credentials={"email": "api@brand.in", "password": "p"}))
    conn._client = httpx.AsyncClient(base_url=shiprocket.BASE_URL, transport=httpx.MockTransport(handler))
    with patch.object(shiprocket, "datetime", wraps=datetime) as dt:
        dt.utcnow.return_value = datetime(2026, 11, 4, 9, 0)
        result = asyncio.run(conn.sync_all())

    assert result.success, result.errors
    month = result.metadata["d2c_month"]
    assert month["period"] == "2026-10-01"
    assert month["values"]["orders_shipped"] == 100
    assert month["values"]["rto_orders"] == 15
    order_calls = [p for m, path, p in seen if path.endswith("/orders")]
    assert order_calls[0]["from"] == "2026-10-01" and order_calls[0]["to"] == "2026-10-31"
    assert len(order_calls) == 2, "follows pagination"


def test_bad_credentials():
    conn = shiprocket.ShiprocketConnector(ConnectorConfig(provider_id="shiprocket", company_id=1, credentials={}))
    result = asyncio.run(conn.sync_all())
    assert not result.success


def test_shiprocket_counts_win_over_a_later_shopify_sync():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(engine, tables=[User.__table__, Company.__table__, D2CMonth.__table__])
    db = sessionmaker(bind=engine)()
    d2c_months.upsert_month(db, 1, date(2026, 10, 1), {"orders_shipped": 100, "cod_share": 0.65}, source="shiprocket")
    d2c_months.upsert_month(db, 1, date(2026, 10, 1), {"orders_shipped": 120, "cod_share": 0.6, "gross_sales": 1e5}, source="shopify")
    row = db.query(D2CMonth).one()
    assert row.orders_shipped == 100 and row.cod_share == 0.65
    assert row.gross_sales == 1e5, "Shopify still owns sales"
    d2c_months.upsert_month(db, 1, date(2026, 10, 1), {"orders_shipped": 90}, source="manual")
    assert db.query(D2CMonth).one().orders_shipped == 90, "the founder beats everyone"


# --- wallet balance -----------------------------------------------------------

@pytest.mark.parametrize("body,expected", [
    ({"data": {"balance_amount": "-291539.83"}}, -291539.83),
    ({"data": {"balance_amount": "1,250.5"}}, 1250.5),
    ({"data": {"balance_amount": 400}}, 400.0),
    ({"data": {"balance_amount": ""}}, None),
    ({"data": {}}, None),
    ({"data": {"balance_amount": "n/a"}}, None),
    ([], None),
])
def test_wallet_from_response(body, expected):
    assert shiprocket.wallet_from_response(body) == expected


def _wallet_conn(wallet_response):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/login"):
            return httpx.Response(200, json={"token": "t"})
        if path.endswith("/wallet-balance"):
            assert request.headers["authorization"] == "Bearer t"
            return wallet_response
        return httpx.Response(200, json={"data": [], "meta": {"pagination": {"total_pages": 1}}})

    conn = shiprocket.ShiprocketConnector(ConnectorConfig(
        provider_id="shiprocket", company_id=1, credentials={"email": "api@brand.in", "password": "p"}))
    conn._client = httpx.AsyncClient(base_url=shiprocket.BASE_URL, transport=httpx.MockTransport(handler))
    return conn


def test_sync_reports_wallet_balance():
    result = asyncio.run(_wallet_conn(httpx.Response(200, json={"data": {"balance_amount": "-1200.00"}})).sync_all())
    assert result.success
    wallet = result.metadata["wallet"]
    assert wallet["balance"] == -1200.0 and wallet["currency"] == "INR" and wallet["as_of"]
    assert result.warnings == []


def test_wallet_failure_does_not_fail_sync():
    result = asyncio.run(_wallet_conn(httpx.Response(500, json={})).sync_all())
    assert result.success
    assert "wallet" not in result.metadata
    assert any("wallet" in w for w in result.warnings)


def test_route_stores_wallet_and_view_reads_it(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from server.api import connectors as connectors_api
    from server.connectors.base import SyncResult
    from server.core.db import get_db
    from server.core.security import get_current_user
    from server.models.financial import FinancialRecord
    from server.models.workspace import WorkspaceMember

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(engine, tables=[User.__table__, Company.__table__, WorkspaceMember.__table__,
                                             D2CMonth.__table__, FinancialRecord.__table__])
    db = sessionmaker(bind=engine)()
    owner = User(email="owner@brand.in", is_active=True)
    db.add(owner)
    db.flush()
    db.add(Company(id=1, name="Brand", user_id=owner.id, currency="INR", metadata_json={"connectors": {
        "shiprocket": {"connected": True, "credentials": {"email": "api@brand.in", "password": "p"}}}}))
    db.commit()

    wallet = {"provider": "shiprocket", "balance": -500.0, "currency": "INR", "as_of": "2026-11-25T08:00:00Z"}

    async def fake_sync(self):
        return SyncResult(success=True, provider_id="shiprocket", sync_type="full", records_synced=0,
                          metadata={"wallet": wallet})

    async def fake_close(self):
        return None

    monkeypatch.setattr(shiprocket.ShiprocketConnector, "sync_all", fake_sync)
    monkeypatch.setattr(shiprocket.ShiprocketConnector, "close", fake_close)
    app = FastAPI()
    app.include_router(connectors_api.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.query(User).one()
    client = TestClient(app)

    assert client.get("/api/connectors/companies/1/shipping-wallet").json() == {"wallets": []}
    res = client.post("/api/connectors/companies/1/sync/shiprocket")
    assert res.status_code == 200, res.text
    view = client.get("/api/connectors/companies/1/shipping-wallet").json()
    assert view["wallets"] == [{**wallet, "provider_id": "shiprocket"}]
    assert client.get("/api/connectors/companies/999/shipping-wallet").status_code == 404
