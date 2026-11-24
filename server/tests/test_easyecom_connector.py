"""EasyEcom: shipped orders, ex-GST sales, RTO vs customer returns, COD share,
per-channel breakdown. Wire format from https://api-docs.easyecom.io (V2.1).
No network: httpx MockTransport."""

import asyncio
import json
from datetime import date, datetime

import httpx
import pytest

from server.connectors import easyecom
from server.connectors.base import ConnectorConfig

_RealAsyncClient = httpx.AsyncClient

CREDS = {"email": " founder@brand.in ", "password": "pw", "api_key": " xkey123 ", "location_key": " ne12345 "}


def _run(coro):
    return asyncio.run(coro)


def _cfg(creds=None):
    return ConnectorConfig(provider_id="easyecom", company_id=1, credentials=creds or dict(CREDS), settings={})


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


def _sub(price, tax, qty=1, returned=0, cancelled=0):
    return {"selling_price": str(price), "tax": tax, "suborder_quantity": qty,
            "returned_quantity": returned, "cancelled_quantity": cancelled}


def _order(inv, status_id, ship_id=None, payment="COD", marketplace="Shopify", subs=None,
           discount=0, order_id=None, awb=None, status=None, **extra):
    names = {1: "Pending", 2: "Open", 7: "Shipped", 9: "Cancelled", 10: "Returned"}
    o = {"invoice_id": inv, "order_id": order_id or inv * 10, "order_status_id": status_id,
         "order_status": status or names.get(status_id, "Weird"), "shipping_status_id": ship_id,
         "shipping_status": None, "payment_mode": payment, "marketplace": marketplace,
         "order_type": "B2C", "order_type_key": "retailorder", "replacement_order": 0,
         "awb_number": awb or f"AWB{inv}", "total_discount": discount,
         "suborders": subs if subs is not None else [_sub(1180, 180)]}
    o.update(extra)
    return o


# --- pure functions ----------------------------------------------------------

@pytest.mark.parametrize("order,kind", [
    (_order(1, 7, 3), "delivered"),
    (_order(1, 7, 2), "in_transit"),
    (_order(1, 7, 20), "in_transit"),
    (_order(1, 7, 24), "rto"),
    (_order(1, 7, 9), "rto"),
    (_order(1, 10, 17), "rto"),
    (_order(1, 10, 26), "returned"),
    (_order(1, 7, 22), "lost"),
    (_order(1, 9), "cancelled"),
    (_order(1, 2), "not_shipped"),
    (_order(1, 6), "not_shipped"),
    (_order(1, 10, 1), "returned_unclassified"),  # "Shipment Created" in the docs' sample
    (_order(1, 30, status="Mystery"), "other"),
])
def test_classify(order, kind):
    assert easyecom.classify(order) == kind


def test_returned_order_uses_credit_note_type_then_awb():
    o = _order(5, 10, 1, awb="FWD1")
    assert easyecom.classify(o, {"return_type": "RTO"}) == "rto"
    assert easyecom.classify(o, {"return_type": "Customer Return"}) == "returned"
    assert easyecom.classify(o, {"return_awb_number": "FWD1"}) == "rto"  # same AWB = RTO per docs FAQ
    assert easyecom.classify(o, {"return_awb_number": "REV9"}) == "returned"
    assert easyecom.classify(o, {}) == "returned_unclassified"
    assert easyecom.classify(_order(5, 10, None, delivery_date="2026-10-03"), None) == "returned"


def test_line_values_are_ex_gst_and_net_of_cancelled_qty():
    # Docs sample: selling_price 1304.73 includes tax 199.03 (18%).
    v = easyecom.line_values({"suborders": [_sub("1304.73", 199.0266, qty=3)], "total_discount": 0})
    assert v["net_ex"] == pytest.approx(1105.70, abs=0.01)
    # 1 of 2 cancelled -> half the line; discount taken ex-GST at the order's ratio.
    v = easyecom.line_values({"suborders": [_sub(2360, 360, qty=2, cancelled=1)], "total_discount": 118})
    assert v["net_ex"] == pytest.approx(1000.0)
    assert v["discount_ex"] == pytest.approx(100.0)


def test_cod_detection():
    assert easyecom.is_cod({"payment_mode": "COD"})
    assert easyecom.is_cod({"payment_mode": "Cash On Delivery"})
    assert not easyecom.is_cod({"payment_mode": "PrePaid"})
    assert easyecom.is_cod({"payment_mode_id": 2})


def _month_orders():
    return (
        [_order(i, 7, 3, payment="COD" if i < 6 else "PrePaid") for i in range(10)]  # 10 delivered, 6 COD
        + [_order(100 + i, 7, 24, marketplace="Amazon.in") for i in range(3)]       # 3 RTO
        + [_order(200, 10, 26, payment="PrePaid", marketplace="Amazon.in")]          # customer return
        + [_order(300, 7, 2, payment="PrePaid")]                                      # in transit
        + [_order(400, 9), _order(401, 2)]                                            # excluded
        + [_order(500, 7, 3, order_type="STN", order_type_key="stocktransfer")]      # not a sale
        + [_order(501, 7, 3, replacement_order=1)]                                    # zero-value reship
    )


def test_summarize_counts_values_and_channels():
    s = easyecom.summarize_orders(_month_orders())
    assert s["orders_shipped"] == 15
    assert (s["delivered"], s["rto_orders"], s["customer_returns_orders"], s["in_transit"]) == (10, 3, 1, 1)
    assert (s["cancelled"], s["not_shipped"]) == (1, 1)
    assert (s["excluded_non_retail"], s["excluded_replacements"]) == (1, 1)
    assert s["gross_sales"] == pytest.approx(15 * 1000.0)
    assert s["customer_returns_value"] == pytest.approx(1000.0)
    assert s["cod_share"] == pytest.approx(6 / 11, abs=1e-4)  # of delivered (incl. later returned)
    amazon = s["channels"]["Amazon.in"]
    assert (amazon["orders_shipped"], amazon["rto_orders"], amazon["customer_returns_orders"]) == (4, 3, 1)
    assert s["channels"]["Shopify"]["orders_shipped"] == 11


def test_split_order_counts_once_and_duplicate_rows_once():
    rows = [_order(1, 7, 3, order_id=77), _order(2, 7, 3, order_id=77), _order(2, 7, 3, order_id=77)]
    s = easyecom.summarize_orders(rows)
    assert s["orders_shipped"] == 1
    assert s["gross_sales"] == pytest.approx(2000.0)


def test_credit_note_values_customer_return_and_partial_return():
    rows = [_order(1, 10, 1, awb="A1"), _order(2, 7, 3, subs=[_sub(2360, 360, qty=2, returned=1)])]
    notes = [{"invoice_id": 1, "return_type": "Customer Return",
              "items": [{"credit_note_total_item_excluding_tax": 900}]}]
    s = easyecom.summarize_orders(rows, notes)
    assert s["customer_returns_orders"] == 2
    assert s["customer_returns_value"] == pytest.approx(900 + 1000)
    assert s["credit_notes_matched"] == 1


def test_month_values_none_for_unknowns():
    empty = easyecom.month_values(easyecom.summarize_orders([]))
    assert empty["orders_shipped"] == 0
    assert empty["gross_sales"] is None and empty["cod_share"] is None
    unclear = easyecom.month_values(easyecom.summarize_orders([_order(1, 7, 3), _order(2, 10, 1)]))
    assert unclear["orders_shipped"] == 2
    assert unclear["rto_orders"] is None
    assert unclear["customer_returns_orders"] is None and unclear["customer_returns_value"] is None
    assert unclear["cod_share"] == 1.0


def test_ist_month_window_and_chunks():
    # 1 Nov 00:30 IST is still 31 Oct in UTC: the last complete month is October.
    assert easyecom.ist_today(datetime(2026, 10, 31, 19, 0)) == date(2026, 11, 1)
    assert easyecom.last_complete_month(date(2026, 11, 1)) == (date(2026, 10, 1), date(2026, 10, 31))
    assert easyecom.last_complete_month(date(2026, 3, 15)) == (date(2026, 2, 1), date(2026, 2, 28))
    chunks = easyecom.date_chunks(date(2026, 10, 1), date(2026, 10, 31))
    assert chunks[0] == ("2026-10-01 00:00:00", "2026-10-07 23:59:59")
    assert chunks[-1] == ("2026-10-29 00:00:00", "2026-10-31 23:59:59")
    assert len(chunks) == 5


# --- wire format -------------------------------------------------------------

def _token_ok(req):
    return httpx.Response(200, json={"data": {"time_zone": "Asia/Kolkata",
                                              "token": {"jwt_token": "JWT1", "token_type": "bearer"}},
                                     "message": None})


def test_token_call_and_both_headers(mock_http):
    def handler(req):
        if req.url.path == "/access/token":
            return _token_ok(req)
        return httpx.Response(400, json={"code": 200, "message": "No Data Found"})

    mock_http["handler"] = handler
    conn = easyecom.EasyEcomConnector(_cfg())
    assert _run(conn.authenticate()) is True
    tok = mock_http["seen"][0]
    assert tok.method == "POST" and tok.url.host == "api.easyecom.io"
    assert tok.headers["x-api-key"] == "xkey123"
    assert json.loads(tok.content) == {"email": "founder@brand.in", "password": "pw", "location_key": "ne12345"}

    result = _run(conn.sync_all())
    data_calls = [r for r in mock_http["seen"] if r.url.path != "/access/token"]
    assert data_calls
    for r in data_calls:
        assert r.headers["x-api-key"] == "xkey123"
        assert r.headers["authorization"] == "Bearer JWT1"
    assert result.success is True


def test_sync_chunks_paginates_and_emits_d2c_month(mock_http, monkeypatch):
    monkeypatch.setattr(easyecom, "ist_today", lambda now=None: date(2026, 11, 24))
    order_windows = []

    def handler(req):
        p = req.url.path
        if p == "/access/token":
            return _token_ok(req)
        if p == "/orders/V2/getAllOrders":
            if "cursor" in req.url.params:
                assert "start_date" not in req.url.params  # nextUrl is called as-is
                return httpx.Response(200, json={"code": 200, "data": {
                    "orders": [_order(2, 7, 24, marketplace="Flipkart")], "nextUrl": None}})
            order_windows.append((req.url.params["start_date"], req.url.params["end_date"]))
            assert req.url.params["limit"] == "250"
            if req.url.params["start_date"].startswith("2026-10-01"):
                return httpx.Response(200, json={"code": 200, "data": {
                    "orders": [_order(1, 7, 3)], "nextUrl": "/orders/V2/getAllOrders?cursor=abc/def="}})
            return httpx.Response(400, json={"code": 200, "message": "No Data Found"})
        if p == "/orders/getAllReturns":
            assert "credit_note_start_date" in req.url.params
            return httpx.Response(200, json={"code": 200, "data": {"credit_notes": [], "nextUrl": None}})
        return httpx.Response(404)

    mock_http["handler"] = handler
    result = _run(easyecom.EasyEcomConnector(_cfg()).sync_all())
    assert result.success is True, result.errors
    assert len(order_windows) == 5
    assert order_windows[0] == ("2026-10-01 00:00:00", "2026-10-07 23:59:59")
    assert order_windows[-1][1] == "2026-10-31 23:59:59"
    cursor_call = [r for r in mock_http["seen"] if "cursor" in r.url.params][0]
    assert cursor_call.url.params["cursor"] == "abc/def="

    month = result.metadata["d2c_month"]
    assert month["period"] == "2026-10-01"
    v = month["values"]
    assert (v["orders_shipped"], v["rto_orders"], v["customer_returns_orders"]) == (2, 1, 0)
    assert v["gross_sales"] == pytest.approx(2000.0)
    assert v["cod_share"] == 1.0
    assert set(result.metadata["d2c_channels"]) == {"Shopify", "Flipkart"}
    assert result.errors == []


def test_page_cap_reports_truncation(mock_http, monkeypatch):
    monkeypatch.setattr(easyecom, "MAX_PAGES", 3)

    def handler(req):
        if req.url.path == "/access/token":
            return _token_ok(req)
        if req.url.path == "/orders/V2/getAllOrders":
            n = int(req.url.params.get("cursor", "0"))
            return httpx.Response(200, json={"code": 200, "data": {
                "orders": [_order(1000 + n, 7, 3)], "nextUrl": f"/orders/V2/getAllOrders?cursor={n + 1}"}})
        return httpx.Response(200, json={"code": 200, "data": {"credit_notes": [], "nextUrl": None}})

    mock_http["handler"] = handler
    result = _run(easyecom.EasyEcomConnector(_cfg()).sync_all())
    assert result.success is True
    order_calls = [r for r in mock_http["seen"] if r.url.path == "/orders/V2/getAllOrders"]
    assert len(order_calls) == 3
    assert any("incomplete" in e for e in result.errors)


def test_returns_failure_is_a_warning_not_a_failed_sync(mock_http):
    def handler(req):
        if req.url.path == "/access/token":
            return _token_ok(req)
        if req.url.path == "/orders/V2/getAllOrders":
            return httpx.Response(200, json={"code": 200, "data": {"orders": [_order(1, 10, 1)], "nextUrl": None}})
        return httpx.Response(400, json={"code": 400, "message": "Unable to find the company"})

    mock_http["handler"] = handler
    result = _run(easyecom.EasyEcomConnector(_cfg()).sync_all())
    assert result.success is True
    assert result.metadata["d2c_month"]["values"]["rto_orders"] is None
    assert any("Returns could not be read" in w for w in result.warnings)


@pytest.mark.parametrize("response", [
    httpx.Response(200, json={"message": "Invalid user credentials provided"}),  # HTTP 200, no token
    httpx.Response(400, json={"message": "Invalid location key provided"}),
    httpx.Response(401, json={"message": "Unauthorized"}),
])
def test_auth_failure_gives_success_false(mock_http, response):
    mock_http["handler"] = lambda req: response
    result = _run(easyecom.EasyEcomConnector(_cfg()).sync_all())
    assert result.success is False
    assert "Authentication failed" in result.errors[0]
    assert all(r.url.path == "/access/token" for r in mock_http["seen"])


def test_missing_credentials_never_call_out(mock_http):
    mock_http["handler"] = lambda req: pytest.fail("no request expected")
    conn = easyecom.EasyEcomConnector(_cfg({"email": "a@b.in", "password": "x", "api_key": "k"}))
    assert _run(conn.authenticate()) is False


def test_registered():
    from server.connectors.registry import ConnectorRegistry
    assert easyecom.EasyEcomConnector.PROVIDER_ID == "easyecom"
    assert ConnectorRegistry.get_connector_class("easyecom") is easyecom.EasyEcomConnector
