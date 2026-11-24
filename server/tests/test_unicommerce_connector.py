"""Unicommerce: all-channel orders -> D2C month inputs. No network: httpx MockTransport."""

import asyncio
import json
from datetime import date, datetime, timezone

import httpx
import pytest

from server.connectors import unicommerce as uc
from server.connectors.base import ConnectorConfig

_RealAsyncClient = httpx.AsyncClient


def _run(coro):
    return asyncio.run(coro)


def _cfg(creds):
    return ConnectorConfig(provider_id="unicommerce", company_id=1, credentials=creds, settings={})


CREDS = {"tenant": " acme ", "username": " ops@acme.in ", "password": " s3cret ", "facility": " WH1, WH2 ,"}


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


def _token_response(token="tok1", refresh="ref1", expires=43200):
    return httpx.Response(200, json={"access_token": token, "token_type": "bearer",
                                     "refresh_token": refresh, "expires_in": expires, "scope": "read trust write"})


def _item(status, price=1180.0, discount=118.0, igst=18.0, code=None, **extra):
    item = {"code": code or f"I-{status}", "statusCode": status, "sellingPrice": price, "discount": discount,
            "integratedGstPercentage": igst, "shippingCharges": 50.0}
    item.update(extra)
    return item


def _order(code, items, cod=False, channel="CUSTOM", currency="INR", packages=None):
    return {"code": code, "channel": channel, "status": "COMPLETE", "cod": cod, "currencyCode": currency,
            "saleOrderItems": items, "shippingPackages": packages or []}


# --- tenant and credentials ------------------------------------------------------

@pytest.mark.parametrize("raw", [
    "acme", " Acme ", "acme.unicommerce.com", "https://acme.unicommerce.com",
    "https://acme.unicommerce.com/oms/home", "http://ACME.unicommerce.com/", "acme.unicommerce.com.",
])
def test_normalize_tenant(raw):
    assert uc.normalize_tenant(raw) == "https://acme.unicommerce.com"


@pytest.mark.parametrize("raw", ["", "  ", "evil.com", "acme.unicommerce.com.evil.com",
                                 "https://169.254.169.254", "a_b", "-acme"])
def test_normalize_tenant_rejects_other_hosts(raw):
    with pytest.raises(ValueError):
        uc.normalize_tenant(raw)


def test_parse_facilities():
    assert uc.parse_facilities(" WH1, WH2 ,") == ["WH1", "WH2"]
    assert uc.parse_facilities("") == []
    assert uc.parse_facilities(None) == []
    assert uc.parse_facilities(["A ", " ", "B"]) == ["A", "B"]


# --- auth ---------------------------------------------------------------------------

def test_token_call_and_bearer_header(mock_http):
    def handler(req):
        if req.url.path == "/oauth/token":
            return _token_response()
        if req.url.path == uc.SEARCH_PATH:
            return httpx.Response(200, json={"successful": True, "elements": [], "totalRecords": 0})
        return httpx.Response(404)

    mock_http["handler"] = handler
    conn = uc.UnicommerceConnector(_cfg(CREDS))
    assert _run(conn.authenticate()) is True
    tok = mock_http["seen"][0]
    assert tok.method == "GET"
    assert tok.url.host == "acme.unicommerce.com" and tok.url.scheme == "https"
    assert dict(tok.url.params) == {"client_id": "my-trusted-client", "grant_type": "password",
                                    "username": "ops@acme.in", "password": "s3cret"}

    rows, truncated = _run(conn._search_codes("a", "b"))
    assert rows == [] and truncated is False
    search = mock_http["seen"][1]
    assert search.method == "POST" and search.url.path == "/services/rest/v1/oms/saleOrder/search"
    assert search.headers["authorization"] == "bearer tok1"
    assert "facility" not in search.headers  # tenant-level API
    assert json.loads(search.content)["facilityCodes"] == ["WH1", "WH2"]


def test_auth_failure_gives_success_false(mock_http):
    mock_http["handler"] = lambda req: httpx.Response(400, json={"error": "invalid_grant"})
    conn = uc.UnicommerceConnector(_cfg(CREDS))
    assert _run(conn.test_connection()) is False
    result = _run(conn.sync_all())
    assert result.success is False
    assert "Authentication failed" in result.errors[0]


def test_missing_or_bad_credentials_make_no_call(mock_http):
    mock_http["handler"] = lambda req: pytest.fail("no request expected")
    assert _run(uc.UnicommerceConnector(_cfg({"tenant": "acme", "username": "u"})).authenticate()) is False
    bad = uc.UnicommerceConnector(_cfg({**CREDS, "tenant": "evil.com"}))
    assert _run(bad.authenticate()) is False
    assert _run(bad.sync_all()).success is False


def test_expired_token_is_renewed_with_refresh_token(mock_http):
    calls = []

    def handler(req):
        if req.url.path == "/oauth/token":
            calls.append(dict(req.url.params))
            if req.url.params["grant_type"] == "password":
                return _token_response("tok1", "ref1", expires=1)  # expires inside the skew
            return _token_response("tok2", "ref2")
        assert req.headers["authorization"] == "bearer tok2"
        return httpx.Response(200, json={"successful": True, "saleOrderDTO": {"code": "SO1"}})

    mock_http["handler"] = handler
    conn = uc.UnicommerceConnector(_cfg(CREDS))
    assert _run(conn.authenticate())
    assert _run(conn._get_order("SO1")) == {"code": "SO1"}
    assert calls[1] == {"client_id": "my-trusted-client", "grant_type": "refresh_token", "refresh_token": "ref1"}


def test_401_triggers_one_renewal(mock_http):
    state = {"n": 0}

    def handler(req):
        if req.url.path == "/oauth/token":
            state["n"] += 1
            return _token_response(f"tok{state['n']}", "ref")
        if req.headers["authorization"] == "bearer tok1":
            return httpx.Response(401)
        return httpx.Response(200, json={"successful": True, "saleOrderDTO": {"code": "SO1"}})

    mock_http["handler"] = handler
    conn = uc.UnicommerceConnector(_cfg(CREDS))
    assert _run(conn.authenticate())
    assert _run(conn._get_order("SO1")) == {"code": "SO1"}


# --- IST month window --------------------------------------------------------------

def test_today_ist_and_month_window():
    # 20:00 UTC on 31 Oct is 01:30 IST on 1 Nov: October is now complete.
    assert uc.today_ist(datetime(2026, 10, 31, 20, 0, tzinfo=timezone.utc)) == date(2026, 11, 1)
    assert uc.today_ist(datetime(2026, 10, 31, 18, 0)) == date(2026, 10, 31)  # naive = UTC
    start, end = uc.last_complete_month(date(2026, 11, 1))
    assert (start, end) == (date(2026, 10, 1), date(2026, 10, 31))
    assert uc.last_complete_month(date(2026, 3, 15)) == (date(2026, 2, 1), date(2026, 2, 28))
    assert uc.last_complete_month(date(2026, 1, 5)) == (date(2025, 12, 1), date(2025, 12, 31))
    assert uc.month_window_utc(start, end) == ("2026-09-30T18:30:00.000Z", "2026-10-31T18:29:59.999Z")


# --- classification ----------------------------------------------------------------

@pytest.mark.parametrize("status,kind", [
    ("DELIVERED", "delivered"),
    ("DISPATCHED", "in_transit"),
    ("SHIPPED", "in_transit"),
    ("COURIER_RETURN", "rto"),
    ("RESHIPPED", "rto"),
    ("RETURN_REQUESTED", "returned"),
    ("RETURNED", "returned"),
    ("REPLACED", "replaced"),
    ("CANCELLED", "cancelled"),
    ("READY_TO_DISPATCH", "not_shipped"),
    ("FULFILLABLE", "not_shipped"),
    ("PACKED", "not_shipped"),
    ("SOMETHING_NEW", "other"),
    ("", "other"),
])
def test_classify_item(status, kind):
    assert uc.classify_item({"statusCode": status}, {}) == (kind, False)


def test_returned_without_pickup_on_undelivered_reverse_package_is_rto():
    pkgs = {"P1": {"code": "P1", "status": "RETURNED", "delivered": None}}
    assert uc.classify_item({"statusCode": "RETURNED", "shippingPackageCode": "P1"}, pkgs) == ("rto", True)
    delivered = {"P1": {"code": "P1", "status": "RETURNED", "delivered": "2026-10-03T10:00:00Z"}}
    assert uc.classify_item({"statusCode": "RETURNED", "shippingPackageCode": "P1"}, delivered) == ("returned", False)
    # A reverse pickup only exists for customer-initiated returns.
    assert uc.classify_item({"statusCode": "RETURNED", "shippingPackageCode": "P1", "reversePickupCode": "RP1"},
                            pkgs) == ("returned", False)


# --- ex-GST math -------------------------------------------------------------------

def test_ex_gst_factor():
    assert uc.ex_gst_factor({"sellingPrice": 1180, "integratedGstPercentage": 18}) == (pytest.approx(1 / 1.18), "inclusive")
    assert uc.ex_gst_factor({"sellingPrice": 1050, "centralGstPercentage": 2.5, "stateGstPercentage": 2.5})[0] == \
        pytest.approx(1 / 1.05)
    assert uc.ex_gst_factor({"sellingPrice": 100, "taxPercentage": 12})[0] == pytest.approx(1 / 1.12)
    # GST amount equals price * rate: the price was already ex-GST.
    assert uc.ex_gst_factor({"sellingPrice": 1000, "integratedGstPercentage": 18, "totalIntegratedGst": 180}) == \
        (1.0, "exclusive")
    # GST amount equals the inclusive back-computation.
    assert uc.ex_gst_factor({"sellingPrice": 1180, "integratedGstPercentage": 18, "totalIntegratedGst": 180})[1] == \
        "inclusive"
    # Amount only: taken out of the price.
    assert uc.ex_gst_factor({"sellingPrice": 1180, "totalIntegratedGst": 180})[0] == pytest.approx(1000 / 1180)
    assert uc.ex_gst_factor({"sellingPrice": 500, "taxPercentage": 0}) == (1.0, "zero_rated")
    assert uc.ex_gst_factor({"sellingPrice": 500}) == (None, "unknown")


def _month():
    pkg_rto = [{"code": "PR", "status": "RETURNED", "delivered": None}]
    return [
        # 6 delivered, 4 of them COD, on two channels
        *[_order(f"D{i}", [_item("DELIVERED")], cod=i < 4, channel="AMAZON_IN" if i % 2 else "CUSTOM")
          for i in range(6)],
        # 2 RTO: one courier-return status, one inferred from the package
        _order("R1", [_item("COURIER_RETURN")], cod=True, channel="FLIPKART"),
        _order("R2", [_item("RETURNED", shippingPackageCode="PR")], cod=True, channel="FLIPKART", packages=pkg_rto),
        # 1 customer return with a reverse pickup, prepaid
        _order("C1", [_item("RETURNED", reversePickupCode="RP1")], cod=False, channel="MYNTRA"),
        # 1 in transit, prepaid, with a cancelled second item that must not count
        _order("T1", [_item("DISPATCHED"), _item("CANCELLED")], cod=False),
        # excluded: cancelled, not shipped, unknown status
        _order("X1", [_item("CANCELLED")], cod=True),
        _order("N1", [_item("PACKED")]),
        _order("O1", [_item("WEIRD_NEW_STATUS")]),
    ]


def test_summarize_orders_buckets_and_ex_gst_values():
    s = uc.summarize_orders(_month())
    assert s["orders_shipped"] == 10  # 6 delivered + 2 RTO + 1 return + 1 in transit
    assert (s["delivered"], s["rto_orders"], s["customer_returns_orders"], s["in_transit"]) == (6, 2, 1, 1)
    assert (s["cancelled"], s["not_shipped"], s["other"]) == (1, 1, 1)
    assert s["other_statuses"] == ["WEIRD_NEW_STATUS"]
    assert s["inferred_rto_items"] == 1

    # Each shipped item: sellingPrice 1180 incl. 18% GST = 1000 ex-GST; discount 118 -> 100.
    assert s["gross_sales"] == pytest.approx(10 * 1100.0)
    assert s["discounts"] == pytest.approx(10 * 100.0)
    assert s["customer_returns_value"] == pytest.approx(1000.0)
    # Delivered = shipped minus RTO = 8 orders; COD among them: D0-D3 = 4.
    assert s["cod_share"] == 0.5

    ch = s["channels"]
    assert ch["FLIPKART"]["rto_orders"] == 2 and ch["FLIPKART"]["orders_shipped"] == 2
    assert ch["MYNTRA"]["customer_returns_orders"] == 1 and ch["MYNTRA"]["customer_returns_value"] == 1000.0
    assert ch["AMAZON_IN"]["gross_sales"] == 3 * 1100.0
    assert ch["CUSTOM"]["cancelled"] == 1 and ch["CUSTOM"]["orders"] == 6  # 3 delivered, T1, N1, O1

    v = uc.month_values(s)
    assert v == {"orders_shipped": 10, "gross_sales": 11000.0, "discounts": 1000.0, "rto_orders": 2,
                 "customer_returns_value": 1000.0, "customer_returns_orders": 1, "cod_share": 0.5}


def test_unknowns_are_none_not_zero():
    # No tax data on a shipped item: money totals are withheld.
    no_tax = _order("A", [{"statusCode": "DELIVERED", "sellingPrice": 500, "discount": 0}], cod=True)
    s = uc.summarize_orders([no_tax])
    assert s["gross_sales"] is None and s["discounts"] is None and s["customer_returns_value"] is None
    assert s["orders_shipped"] == 1 and s["tax_unknown_items"] == 1
    # No COD field: COD share unknown.
    no_cod = _order("B", [_item("DELIVERED")])
    del no_cod["cod"]
    assert uc.summarize_orders([no_cod])["cod_share"] is None
    # Nothing shipped: no COD share; another currency withholds money.
    assert uc.summarize_orders([_order("C", [_item("CANCELLED")])])["cod_share"] is None
    assert uc.summarize_orders([_order("D", [_item("DELIVERED")], currency="USD")])["gross_sales"] is None
    # An incomplete month keeps only the ratio.
    v = uc.month_values(uc.summarize_orders(_month()), complete=False)
    assert v["cod_share"] == 0.5
    assert all(v[k] is None for k in v if k != "cod_share")


def test_partial_rto_order_counts_as_delivered():
    s = uc.summarize_orders([_order("P", [_item("DELIVERED"), _item("COURIER_RETURN")], cod=True)])
    assert (s["orders_shipped"], s["rto_orders"], s["delivered"], s["partial_rto_orders"]) == (1, 0, 1, 1)
    assert s["gross_sales"] == pytest.approx(2200.0)


# --- search + detail paging, caps, sync_all ----------------------------------------

def _api(orders, page_size=2):
    """A fake tenant: COD/prepaid search filtering and per-order GET."""
    by_code = {o["code"]: o for o in orders}
    log = {"search": [], "get": []}

    def handler(req):
        if req.url.path == "/oauth/token":
            return _token_response()
        body = json.loads(req.content or b"{}")
        if req.url.path == uc.SEARCH_PATH:
            log["search"].append(body)
            rows = [{"code": o["code"], "channel": o["channel"], "status": o["status"]}
                    for o in orders if bool(o.get("cod")) == body["cashOnDelivery"]]
            start = body["searchOptions"]["displayStart"]
            n = body["searchOptions"]["displayLength"]
            return httpx.Response(200, json={"successful": True, "totalRecords": len(rows),
                                             "elements": rows[start:start + n]})
        if req.url.path == uc.DETAIL_PATH:
            log["get"].append(body["code"])
            if body["code"] == "FAIL":
                return httpx.Response(500)
            return httpx.Response(200, json={"successful": True, "saleOrderDTO": by_code[body["code"]]})
        return httpx.Response(404)

    return handler, log


def test_search_pages_both_cod_passes_and_fetches_each_order(mock_http, monkeypatch):
    monkeypatch.setattr(uc, "PAGE_SIZE", 2)
    monkeypatch.setattr(uc, "today_ist", lambda: date(2026, 11, 24))
    orders = _month()
    handler, log = _api(orders)
    mock_http["handler"] = handler
    result = _run(uc.UnicommerceConnector(_cfg(CREDS)).sync_all())

    assert result.success is True and result.errors == []
    first = log["search"][0]
    assert first["fromDate"] == "2026-09-30T18:30:00.000Z" and first["toDate"] == "2026-10-31T18:29:59.999Z"
    assert first["dateType"] == "CREATED"
    assert {b["cashOnDelivery"] for b in log["search"]} == {True, False}
    assert [b["searchOptions"]["displayStart"] for b in log["search"] if b["cashOnDelivery"]] == [0, 2, 4, 6]  # 7 COD orders
    assert sorted(log["get"]) == sorted(o["code"] for o in orders)
    assert result.records_synced == len(orders)

    month = result.metadata["d2c_month"]
    assert month["period"] == "2026-10-01"
    assert month["values"]["orders_shipped"] == 10
    assert month["values"]["gross_sales"] == 11000.0
    assert month["values"]["cod_share"] == 0.5
    meta = result.metadata["unicommerce"]
    assert meta["complete"] is True and meta["truncated"] is False
    assert set(meta["channels"]) == {"CUSTOM", "AMAZON_IN", "FLIPKART", "MYNTRA"}


def test_detail_cap_reports_truncation_and_withholds_totals(mock_http, monkeypatch):
    monkeypatch.setattr(uc, "MAX_ORDER_DETAILS", 3)
    monkeypatch.setattr(uc, "today_ist", lambda: date(2026, 11, 24))
    handler, log = _api(_month())
    mock_http["handler"] = handler
    result = _run(uc.UnicommerceConnector(_cfg(CREDS)).sync_all())

    assert result.success is True
    assert len(log["get"]) == 3
    assert "incomplete" in result.errors[0]
    meta = result.metadata["unicommerce"]
    assert meta["truncated"] is True and meta["orders_found"] == 13 and meta["orders_fetched"] == 3
    values = result.metadata["d2c_month"]["values"]
    assert values["orders_shipped"] is None and values["gross_sales"] is None


def test_search_page_cap_is_truncation(mock_http, monkeypatch):
    monkeypatch.setattr(uc, "PAGE_SIZE", 1)
    monkeypatch.setattr(uc, "MAX_SEARCH_PAGES", 2)
    handler, _ = _api(_month())
    mock_http["handler"] = handler
    conn = uc.UnicommerceConnector(_cfg(CREDS))
    assert _run(conn.authenticate())
    rows, truncated = _run(conn._search_codes("a", "b"))
    assert truncated is True and len(rows) == 4  # 2 pages x 2 COD passes


def test_failed_detail_is_retried_once_then_reported(mock_http, monkeypatch):
    monkeypatch.setattr(uc, "today_ist", lambda: date(2026, 11, 24))
    orders = [_order("D1", [_item("DELIVERED")], cod=True), _order("FAIL", [_item("DELIVERED")], cod=True)]
    handler, log = _api(orders)
    mock_http["handler"] = handler
    result = _run(uc.UnicommerceConnector(_cfg(CREDS)).sync_all())
    assert log["get"].count("FAIL") == 2
    assert result.success is True and result.records_failed == 1
    assert result.metadata["unicommerce"]["complete"] is False
    assert result.metadata["d2c_month"]["values"]["orders_shipped"] is None
    assert result.metadata["d2c_month"]["values"]["cod_share"] == 1.0


def test_search_error_fails_the_sync(mock_http):
    def handler(req):
        if req.url.path == "/oauth/token":
            return _token_response()
        return httpx.Response(200, json={"successful": False, "message": "Invalid facility"})

    mock_http["handler"] = handler
    result = _run(uc.UnicommerceConnector(_cfg(CREDS)).sync_all())
    assert result.success is False and "Invalid facility" in result.errors[0]


def test_registered():
    from server.connectors.registry import ConnectorRegistry
    assert ConnectorRegistry.get_connector_class("unicommerce") is uc.UnicommerceConnector
