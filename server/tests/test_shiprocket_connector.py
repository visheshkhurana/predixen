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
