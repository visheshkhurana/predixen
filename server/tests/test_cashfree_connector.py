"""Cashfree Payments connector: PG Reconciliation (POST /pg/recon, x-api-version
2026-01-01). No network: httpx MockTransport."""

import asyncio
import json
from datetime import date, datetime
from unittest.mock import patch

import httpx
import pytest

from server.connectors import cashfree
from server.connectors.base import ConnectorConfig
from server.connectors.registry import ConnectorRegistry

_RealAsyncClient = httpx.AsyncClient


def _run(coro):
    return asyncio.run(coro)


def _cfg(creds):
    return ConnectorConfig(provider_id="cashfree", company_id=1, credentials=creds, settings={})


@pytest.fixture
def mock_http(monkeypatch):
    """Route every httpx.AsyncClient through ``handler``; returns the request log."""
    state = {"handler": None, "seen": []}

    class Patched(_RealAsyncClient):
        def __init__(self, *a, **kw):
            def wrapped(request):
                state["seen"].append(request)
                return state["handler"](request)
            kw["transport"] = httpx.MockTransport(wrapped)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    return state


def _event(etype="PAYMENT", status="SUCCESS", amount=1000, charge=20, tax=3.6,
           currency="INR", group="UPI"):
    return {
        "event_details": {
            "event_type": etype, "event_status": status, "event_amount": amount,
            "event_service_charge": charge, "event_service_tax": tax, "event_currency": currency,
        },
        "payment_details": {"payment_group": group},
    }


CREDS = {"client_id": "  CF_APP  ", "client_secret": " cfsk_secret \n"}


# --- registration / credentials -----------------------------------------------

def test_registered_as_cashfree():
    assert ConnectorRegistry.get_connector_class("cashfree") is cashfree.CashfreeConnector
    assert cashfree.CashfreeConnector.PROVIDER_NAME == "Cashfree Payments"
    assert cashfree.CashfreeConnector.AUTH_TYPE.value == "api_key"


def test_auth_sends_client_headers_and_api_version(mock_http):
    mock_http["handler"] = lambda req: httpx.Response(200, json={"cursor": None, "data": []})
    conn = cashfree.CashfreeConnector(_cfg(CREDS))
    assert _run(conn.authenticate()) is True
    req = mock_http["seen"][0]
    assert req.method == "POST"
    assert str(req.url) == "https://api.cashfree.com/pg/recon"
    assert req.headers["x-client-id"] == "CF_APP"
    assert req.headers["x-client-secret"] == "cfsk_secret"
    assert req.headers["x-api-version"] == "2026-01-01"
    body = json.loads(req.content)
    assert body["pagination"] == {"limit": 1, "cursor": None}
    assert set(body["filters"]) == {"start_date", "end_date"}


def test_sandbox_environment_uses_sandbox_host(mock_http):
    mock_http["handler"] = lambda req: httpx.Response(200, json={"data": []})
    conn = cashfree.CashfreeConnector(_cfg({**CREDS, "environment": " Sandbox "}))
    assert _run(conn.authenticate()) is True
    assert str(mock_http["seen"][0].url) == "https://sandbox.cashfree.com/pg/recon"


def test_missing_credentials_make_no_request(mock_http):
    mock_http["handler"] = lambda req: httpx.Response(200, json={"data": []})
    conn = cashfree.CashfreeConnector(_cfg({"client_id": "x", "client_secret": "  "}))
    assert _run(conn.authenticate()) is False
    assert mock_http["seen"] == []


def test_auth_failure_gives_unsuccessful_sync(mock_http):
    mock_http["handler"] = lambda req: httpx.Response(401, json={"message": "authentication Failed"})
    conn = cashfree.CashfreeConnector(_cfg(CREDS))
    result = _run(conn.sync_all())
    assert result.success is False
    assert "Authentication failed" in result.errors[0]


# --- window / pagination ---------------------------------------------------------

def test_last_complete_month_and_ist_window():
    assert cashfree.last_complete_month(date(2026, 11, 4)) == (date(2026, 10, 1), date(2026, 10, 31))
    assert cashfree.last_complete_month(date(2026, 1, 1)) == (date(2025, 12, 1), date(2025, 12, 31))
    start, end = cashfree.month_window(date(2026, 10, 1), date(2026, 10, 31))
    # 1 Oct 00:00 IST and 31 Oct 23:59:59 IST, in UTC
    assert start == "2026-09-30T18:30:00Z"
    assert end == "2026-10-31T18:29:59Z"


def test_paginates_until_cursor_ends(mock_http):
    pages = {
        None: {"cursor": "c1", "limit": 1000, "data": [_event(amount=100)]},
        "c1": {"cursor": "c2", "limit": 1000, "data": [_event(amount=200)]},
        "c2": {"cursor": None, "limit": 1000, "data": [_event(amount=300)]},
    }

    def handler(req):
        body = json.loads(req.content)
        assert body["pagination"]["limit"] == cashfree.PAGE_LIMIT
        return httpx.Response(200, json=pages[body["pagination"]["cursor"]])

    mock_http["handler"] = handler
    conn = cashfree.CashfreeConnector(_cfg(CREDS))
    rows, truncated = _run(conn._events("s", "e"))
    assert [r["event_details"]["event_amount"] for r in rows] == [100, 200, 300]
    assert truncated is False
    assert len(mock_http["seen"]) == 3


def test_repeated_cursor_stops(mock_http):
    mock_http["handler"] = lambda req: httpx.Response(200, json={"cursor": "same", "data": [_event()]})
    conn = cashfree.CashfreeConnector(_cfg(CREDS))
    rows, truncated = _run(conn._events("s", "e"))
    assert len(rows) == 2 and truncated is False


def test_truncation_is_reported(mock_http, monkeypatch):
    monkeypatch.setattr(cashfree, "MAX_PAGES", 2)
    counter = {"n": 0}

    def handler(req):
        counter["n"] += 1
        return httpx.Response(200, json={"cursor": f"c{counter['n']}", "data": [_event()]})

    mock_http["handler"] = handler
    conn = cashfree.CashfreeConnector(_cfg(CREDS))
    with patch.object(cashfree, "datetime", wraps=datetime) as dt:
        dt.utcnow.return_value = datetime(2026, 11, 4, 9, 0)
        result = _run(conn.sync_all())
    assert result.success is True
    assert result.errors == ["Row limit reached; the month is incomplete"]


# --- fee math ----------------------------------------------------------------------

def test_fee_math_ex_gst_skips_failed_non_inr_and_pending():
    summary = cashfree.summarize_events([
        _event(amount=4000, charge=40, tax=7.2, group="CREDIT_CARD"),
        _event(amount=1000, charge=10, tax=1.8, group="UPI"),
        _event(status="FAILED", amount=0, charge=None, tax=None),
        _event(status="PENDING", amount=500, charge=5, tax=0.9),
        _event(amount=999, charge=30, tax=5.4, currency="USD"),
        _event(etype="REFUND", amount=1000, charge=0, tax=0),
    ])
    assert summary["captured_payments"] == 2
    assert summary["failed_payments"] == 1
    assert summary["non_inr_payments_skipped"] == 1
    assert summary["captured_value"] == 5000.0
    assert summary["fees_ex_gst"] == 50.0
    assert summary["gst_on_fees"] == 9.0
    assert summary["fees_incl_gst"] == 59.0
    # the refunded payment stays in captured value (fee is kept), refund reported apart
    assert summary["refunded_value"] == 1000.0
    assert summary["payment_gateway_pct"] == 0.01
    assert summary["method_share"] == {"CREDIT_CARD": 0.8, "UPI": 0.2}


def test_falls_back_to_payment_details_when_event_fields_missing():
    e = {
        "event_details": {"event_type": "PAYMENT", "event_status": "SUCCESS"},
        "payment_details": {"payment_amount": 2000, "payment_service_charge": 36,
                            "payment_service_tax": 6.48, "payment_currency": "INR",
                            "payment_group": "DEBIT_CARD"},
    }
    summary = cashfree.summarize_events([e])
    assert summary["captured_value"] == 2000.0
    assert summary["payment_gateway_pct"] == 0.018


def test_none_not_zero_when_nothing_captured():
    summary = cashfree.summarize_events([_event(status="FAILED")])
    assert summary["payment_gateway_pct"] is None
    assert summary["method_share"] == {}
    assert cashfree.summarize_events([])["payment_gateway_pct"] is None


# --- sync_all ------------------------------------------------------------------------

def test_sync_all_emits_d2c_month_for_previous_month(mock_http):
    windows = []

    def handler(req):
        body = json.loads(req.content)
        if body["pagination"]["limit"] == 1:
            return httpx.Response(200, json={"cursor": None, "data": []})
        windows.append(body["filters"])
        return httpx.Response(200, json={"cursor": None, "data": [
            _event(amount=10000, charge=180, tax=32.4, group="UPI"),
        ]})

    mock_http["handler"] = handler
    conn = cashfree.CashfreeConnector(_cfg(CREDS))
    with patch.object(cashfree, "datetime", wraps=datetime) as dt:
        dt.utcnow.return_value = datetime(2026, 11, 4, 9, 0)
        result = _run(conn.sync_all())
    _run(conn.close())

    assert result.success is True, result.errors
    assert result.errors == []
    assert result.records_synced == 1
    assert windows == [{"start_date": "2026-09-30T18:30:00Z", "end_date": "2026-10-31T18:29:59Z"}]
    assert result.metadata["d2c_month"] == {
        "period": "2026-10-01", "values": {"payment_gateway_pct": 0.018},
    }
    assert result.metadata["cashfree"]["fees_ex_gst"] == 180.0


def test_recon_error_mid_sync_is_unsuccessful(mock_http):
    def handler(req):
        body = json.loads(req.content)
        if body["pagination"]["limit"] == 1:
            return httpx.Response(200, json={"data": []})
        return httpx.Response(400, json={"message": "bad"})

    mock_http["handler"] = handler
    conn = cashfree.CashfreeConnector(_cfg(CREDS))
    result = _run(conn.sync_all())
    assert result.success is False
    assert "400" in result.errors[0]
