"""Razorpay (payment gateway): gateway fee share of captured prepaid value."""

import asyncio
import base64
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.connectors import razorpay
from server.connectors.base import ConnectorConfig
from server.models.company import Company
from server.models.d2c_month import D2CMonth
from server.models.user import User
from server.services import d2c_months


def _pay(i, amount=100_000, fee=2_360, tax=360, status="captured", method="upi", currency="INR", refunded=0):
    return {"id": f"pay_{i}", "amount": amount, "currency": currency, "status": status,
            "captured": status in ("captured", "refunded"), "method": method,
            "fee": fee, "tax": tax, "amount_refunded": refunded}


def _month():
    return (
        [_pay(i) for i in range(60)]                                  # ₹1,000 UPI, ₹20 fee + ₹3.60 GST
        + [_pay(100 + i, method="card") for i in range(30)]
        + [_pay(200 + i, status="refunded", refunded=100_000) for i in range(10)]  # fee kept on refunds
        + [_pay(300 + i, status="failed", fee=None, tax=None) for i in range(7)]
        + [_pay(400, status="authorized", fee=None, tax=None)]        # never captured
        + [_pay(500, currency="USD", amount=5_000, fee=300, tax=0)]   # international, skipped
    )


def test_summary():
    s = razorpay.summarize_payments(_month())
    assert s["captured_payments"] == 100
    assert s["failed_payments"] == 7
    assert s["non_inr_payments_skipped"] == 1
    assert s["captured_value"] == pytest.approx(100_000.0)
    assert s["refunded_value"] == pytest.approx(10_000.0)
    assert s["fees_incl_gst"] == pytest.approx(2_360.0)
    assert s["fees_ex_gst"] == pytest.approx(2_000.0)
    assert s["payment_gateway_pct"] == pytest.approx(0.02), "ex-GST fee / captured value"
    assert s["method_share"]["upi"] == pytest.approx(0.7)
    assert s["method_share"]["card"] == pytest.approx(0.3)


def test_no_captured_payments_is_missing_not_free():
    s = razorpay.summarize_payments([_pay(1, status="failed")])
    assert s["payment_gateway_pct"] is None
    assert razorpay.month_values(s) == {"payment_gateway_pct": None}


def test_month_window_is_india_time():
    start, end = razorpay.month_window_unix(date(2026, 10, 1), date(2026, 10, 31))
    ist = timezone(timedelta(hours=5, minutes=30))
    assert datetime.fromtimestamp(start, ist) == datetime(2026, 10, 1, 0, 0, tzinfo=ist)
    assert datetime.fromtimestamp(end, ist) == datetime(2026, 10, 31, 23, 59, 59, tzinfo=ist)


def test_sync_against_mocked_api():
    payments = _month()
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        expected = "Basic " + base64.b64encode(b"rzp_live_x:secret").decode()
        assert request.headers["authorization"] == expected
        params = dict(request.url.params)
        seen.append(params)
        if params.get("count") == "1":
            return httpx.Response(200, json={"entity": "collection", "count": 1, "items": payments[:1]})
        skip, count = int(params["skip"]), int(params["count"])
        chunk = payments[skip: skip + count]
        return httpx.Response(200, json={"entity": "collection", "count": len(chunk), "items": chunk})

    conn = razorpay.RazorpayConnector(ConnectorConfig(
        provider_id="razorpay", company_id=1, credentials={"key_id": "rzp_live_x", "key_secret": "secret"}))
    conn._client = httpx.AsyncClient(base_url=razorpay.BASE_URL, auth=("rzp_live_x", "secret"),
                                     transport=httpx.MockTransport(handler))
    with patch.object(razorpay, "datetime", wraps=datetime) as dt:
        dt.utcnow.return_value = datetime(2026, 11, 4, 9, 0)
        result = asyncio.run(conn.sync_all())

    assert result.success, result.errors
    month = result.metadata["d2c_month"]
    assert month["period"] == "2026-10-01"
    assert month["values"]["payment_gateway_pct"] == pytest.approx(0.02)
    page_calls = [p for p in seen if "skip" in p]
    assert [p["skip"] for p in page_calls] == ["0", "100"], "follows pagination until a short page"
    assert page_calls[0]["from"] == str(razorpay.month_window_unix(date(2026, 10, 1), date(2026, 10, 31))[0])


def test_bad_credentials():
    conn = razorpay.RazorpayConnector(ConnectorConfig(provider_id="razorpay", company_id=1, credentials={}))
    assert not asyncio.run(conn.sync_all()).success


def test_rejected_key_fails_cleanly():
    conn = razorpay.RazorpayConnector(ConnectorConfig(
        provider_id="razorpay", company_id=1, credentials={"key_id": "k", "key_secret": "bad"}))
    conn._client = httpx.AsyncClient(base_url=razorpay.BASE_URL,
                                     transport=httpx.MockTransport(lambda r: httpx.Response(401, json={})))
    result = asyncio.run(conn.sync_all())
    assert not result.success and "key id" in result.errors[0]


def test_gateway_fee_feeds_cm2_and_manual_still_wins():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(engine, tables=[User.__table__, Company.__table__, D2CMonth.__table__])
    db = sessionmaker(bind=engine)()
    d2c_months.upsert_month(db, 1, date(2026, 10, 1), {"payment_gateway_pct": 0.02}, source="razorpay")
    row = db.query(D2CMonth).one()
    assert row.payment_gateway_pct == 0.02 and row.field_sources["payment_gateway_pct"] == "razorpay"
    d2c_months.upsert_month(db, 1, date(2026, 10, 1), {"payment_gateway_pct": 0.018}, source="manual")
    d2c_months.upsert_month(db, 1, date(2026, 10, 1), {"payment_gateway_pct": 0.025}, source="razorpay")
    assert db.query(D2CMonth).one().payment_gateway_pct == 0.018, "a typed rate is never overwritten"


def test_registered():
    from server.connectors.registry import ConnectorRegistry
    import server.connectors as pkg
    pkg.load_all_connectors()
    assert "razorpay" in ConnectorRegistry.get_available_providers()
    assert "razorpayx" in ConnectorRegistry.get_available_providers(), "banking connector is separate"
