"""Payments / e-commerce connector fixes, checked against each provider's
documented wire format. No network: httpx MockTransport."""

import asyncio
import base64
import time
import urllib.parse

import httpx
import pytest

from server.connectors import chargebee, profitwell, recurly, shiprocket, shopify, stripe, woocommerce
from server.connectors.base import ConnectorConfig

_RealAsyncClient = httpx.AsyncClient


def _run(coro):
    return asyncio.run(coro)


def _cfg(provider, creds):
    return ConnectorConfig(provider_id=provider, company_id=1, credentials=creds, settings={})


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


# --- Recurly -----------------------------------------------------------------

def test_recurly_uses_basic_auth_and_follows_next_path(mock_http):
    def handler(req):
        if req.url.path == "/sites":
            return httpx.Response(200, json={"data": []})
        if req.url.path == "/subscriptions" and "cursor" not in req.url.params:
            return httpx.Response(200, json={
                "has_more": True, "next": "/subscriptions?cursor=abc123&limit=200",
                "data": [{"id": "s1"}]})
        if req.url.path == "/subscriptions":
            assert req.url.params["cursor"] == "abc123"
            return httpx.Response(200, json={"has_more": False, "next": None, "data": [{"id": "s2"}]})
        return httpx.Response(404)

    mock_http["handler"] = handler
    conn = recurly.RecurlyConnector(_cfg("recurly", {"api_key": "key123"}))
    subs = _run(conn.get_subscriptions(limit=1000))
    assert [s["id"] for s in subs] == ["s1", "s2"]

    first = mock_http["seen"][0]
    assert first.url.host == "v3.recurly.com"
    expected = "Basic " + base64.b64encode(b"key123:").decode()
    assert all(r.headers["authorization"] == expected for r in mock_http["seen"])
    assert first.headers["accept"] == "application/vnd.recurly.v2021-02-25+json"
    # next path is requested as-is, not turned into cursor=<full path>
    assert str(mock_http["seen"][-1].url).endswith("/subscriptions?cursor=abc123&limit=200")


def test_recurly_eu_region_uses_eu_host(mock_http):
    mock_http["handler"] = lambda req: httpx.Response(200, json={"data": []})
    conn = recurly.RecurlyConnector(_cfg("recurly", {"api_key": "k", "region": "EU"}))
    assert _run(conn.authenticate()) is True
    assert mock_http["seen"][0].url.host == "v3.eu.recurly.com"


# --- ProfitWell --------------------------------------------------------------

def test_profitwell_auth_sends_only_documented_params(mock_http):
    def handler(req):
        assert req.headers["authorization"] == "tok"
        assert set(req.url.params.keys()) <= {"metrics", "plan_id"}
        return httpx.Response(200, json={"data": {"recurring_revenue": []}})

    mock_http["handler"] = handler
    conn = profitwell.ProfitWellConnector(_cfg("profitwell", {"api_token": "tok"}))
    assert _run(conn.authenticate()) is True
    assert mock_http["seen"][0].url.path == "/v2/metrics/monthly/"


def test_profitwell_monthly_parses_trends_in_currency_units(mock_http):
    payload = {"data": {
        "recurring_revenue": [{"date": "2026-08", "value": 1000.5}, {"date": "2026-09", "value": 1500}],
        "new_recurring_revenue": [{"date": "2026-09", "value": 600}],
        "churned_recurring_revenue": [{"date": "2026-09", "value": 100}],
        "growth_rate": [{"date": "2026-09", "value": None}],
    }}
    mock_http["handler"] = lambda req: httpx.Response(200, json=payload)
    conn = profitwell.ProfitWellConnector(_cfg("profitwell", {"api_token": "tok"}))
    from datetime import datetime
    ledger = _run(conn.fetch_ledger(datetime(2026, 1, 1), datetime(2026, 12, 31)))
    by_id = {e.external_id: e for e in ledger}
    assert by_id["pw-mrr-2026-08"].credit == 1000.5  # not divided by 100
    assert by_id["pw-mrr-2026-09"].credit == 1500
    assert by_id["pw-new-2026-09"].credit == 600
    assert by_id["pw-churn-2026-09"].debit == 100
    fin = conn.map_to_financials(ledger_entries=ledger)
    assert fin["mrr"] == 1500 and fin["arr"] == 18000
    monthly_calls = [r for r in mock_http["seen"] if r.url.path == "/v2/metrics/monthly/" and not r.url.params]
    assert len(monthly_calls) == 1, "full history in one call, no per-month month= loop"


def test_profitwell_daily_uses_month_param(mock_http):
    def handler(req):
        if req.url.path == "/v2/metrics/daily/":
            assert dict(req.url.params) == {"month": "2026-11"}
            return httpx.Response(200, json={"data": {"recurring_revenue": [{"date": "2026-11-01", "value": 10}]}})
        return httpx.Response(200, json={"data": {}})

    mock_http["handler"] = handler
    conn = profitwell.ProfitWellConnector(_cfg("profitwell", {"api_token": "tok"}))
    daily = _run(conn.get_daily_metrics("2026-11"))
    assert daily["recurring_revenue"][0]["value"] == 10


def test_profitwell_customers_endpoint_pages(mock_http):
    def handler(req):
        if req.url.path == "/v2/customers/":
            page = int(req.url.params["page"])
            n = 2 if page == 1 else 1
            return httpx.Response(200, json=[{"customer_id": f"c{page}{i}"} for i in range(n)])
        return httpx.Response(200, json={"data": {}})

    mock_http["handler"] = handler
    conn = profitwell.ProfitWellConnector(_cfg("profitwell", {"api_token": "tok"}))
    customers = _run(conn.get_customers(per_page=2))
    assert len(customers) == 3
    assert not any("subcriptions" in r.url.path for r in mock_http["seen"])


# --- Shopify -----------------------------------------------------------------

def _shop_handler(calls, token_values=("tok-1", "tok-2"), first_shop_status=200):
    tokens = list(token_values)

    def handler(req):
        if req.url.path == "/admin/oauth/access_token":
            form = urllib.parse.parse_qs(req.content.decode())
            calls.append(("token", form))
            return httpx.Response(200, json={"access_token": tokens.pop(0), "scope": "read_orders", "expires_in": 86399})
        calls.append(("api", req.url.path, req.headers.get("x-shopify-access-token")))
        if req.url.path.endswith("/shop.json"):
            status = first_shop_status if len([c for c in calls if c[0] == "api"]) == 1 else 200
            return httpx.Response(status, json={"shop": {"id": 1}})
        if req.url.path.endswith("/products.json"):
            return httpx.Response(200, json={"products": [{"id": 9}]})
        return httpx.Response(404)
    return handler


def test_shopify_client_credentials_exchange_and_rotation(mock_http):
    calls = []
    mock_http["handler"] = _shop_handler(calls)
    conn = shopify.ShopifyConnector(_cfg("shopify", {
        "shop_domain": "brand.myshopify.com", "client_id": "cid", "client_secret": "csec"}))
    assert _run(conn.authenticate()) is True

    kind, form = calls[0]
    assert kind == "token"
    assert form == {"grant_type": ["client_credentials"], "client_id": ["cid"], "client_secret": ["csec"]}
    assert mock_http["seen"][0].url.host == "brand.myshopify.com"
    assert calls[1] == ("api", "/admin/api/2026-10/shop.json", "tok-1")
    rotated = conn.rotated_credentials()
    assert rotated["access_token"] == "tok-1" and rotated["client_id"] == "cid"


def test_shopify_reexchanges_on_401(mock_http):
    calls = []
    mock_http["handler"] = _shop_handler(calls, first_shop_status=401)
    conn = shopify.ShopifyConnector(_cfg("shopify", {
        "shop_domain": "brand", "access_token": "stale", "client_id": "cid", "client_secret": "csec"}))
    assert _run(conn.authenticate()) is True
    assert calls[0] == ("api", "/admin/api/2026-10/shop.json", "stale")
    assert calls[1][0] == "token"
    assert calls[2] == ("api", "/admin/api/2026-10/shop.json", "tok-1")
    assert conn.rotated_credentials()["access_token"] == "tok-1"


def test_shopify_reexchanges_when_token_near_expiry(mock_http):
    calls = []
    mock_http["handler"] = _shop_handler(calls)
    conn = shopify.ShopifyConnector(_cfg("shopify", {
        "shop_domain": "brand", "client_id": "cid", "client_secret": "csec"}))
    assert _run(conn.authenticate()) is True
    conn._token_expires_at = time.time() + 10  # inside the refresh margin
    assert _run(conn.get_products()) == [{"id": 9}]
    assert [c[0] for c in calls] == ["token", "api", "token", "api"]
    assert calls[-1][2] == "tok-2"


def test_shopify_static_token_still_works_and_probes_shop_json(mock_http):
    calls = []
    mock_http["handler"] = _shop_handler(calls)
    conn = shopify.ShopifyConnector(_cfg("shopify", {"shop_domain": "brand", "access_token": "shpat_x"}))
    assert _run(conn.authenticate()) is True
    assert calls == [("api", "/admin/api/2026-10/shop.json", "shpat_x")]
    assert conn.rotated_credentials() is None


def test_shopify_rejected_client_credentials_explain_why(mock_http):
    mock_http["handler"] = lambda req: httpx.Response(400, json={"error": "invalid_client"})
    conn = shopify.ShopifyConnector(_cfg("shopify", {
        "shop_domain": "brand", "client_id": "cid", "client_secret": "bad"}))
    assert _run(conn.authenticate()) is False
    assert "same Shopify organization" in conn.auth_error


def test_shopify_needs_some_credential():
    conn = shopify.ShopifyConnector(_cfg("shopify", {"shop_domain": "brand", "client_id": "cid"}))
    assert _run(conn.authenticate()) is False
    assert "client ID and secret" in conn.auth_error


# --- Stripe ------------------------------------------------------------------

def test_stripe_invoice_tax_uses_total_taxes_with_fallback():
    assert stripe._invoice_tax_cents({"total_taxes": [{"amount": 150}, {"amount": 50}], "tax": 999}) == 200
    assert stripe._invoice_tax_cents({"tax": 120}) == 120
    assert stripe._invoice_tax_cents({"total_taxes": [], "tax": None}) == 0
    assert stripe._invoice_subscription({"parent": {"subscription_details": {"subscription": "sub_1"}}}) == "sub_1"
    assert stripe._invoice_subscription({"subscription": "sub_0"}) == "sub_0"


def test_stripe_fetch_invoices_basil_tax(mock_http):
    mock_http["handler"] = lambda req: httpx.Response(200, json={"has_more": False, "data": [{
        "id": "in_1", "created": 1700000000, "amount_paid": 1200, "total": 1200,
        "total_taxes": [{"amount": 200, "type": "tax_rate_details"}], "status": "paid", "currency": "usd"}]})
    conn = stripe.StripeConnector(_cfg("stripe", {"api_key": "sk_test_x"}))
    inv = _run(conn.fetch_invoices())
    assert inv[0].tax == 2.0


def test_stripe_ledger_paginates_balance_transactions(mock_http):
    def handler(req):
        after = req.url.params.get("starting_after")
        if after is None:
            return httpx.Response(200, json={"has_more": True, "data": [
                {"id": f"txn_{i}", "amount": 100, "created": 1700000000} for i in range(100)]})
        assert after == "txn_99"
        return httpx.Response(200, json={"has_more": False, "data": [{"id": "txn_100", "amount": 100, "created": 1700000000}]})

    mock_http["handler"] = handler
    conn = stripe.StripeConnector(_cfg("stripe", {"api_key": "sk_test_x"}))
    ledger = _run(conn.fetch_ledger())
    assert len(ledger) == 101


def test_stripe_ledger_page_cap(mock_http, monkeypatch):
    monkeypatch.setattr(stripe, "MAX_LEDGER_PAGES", 3)
    counter = {"n": 0}

    def handler(req):
        counter["n"] += 1
        return httpx.Response(200, json={"has_more": True, "data": [{"id": f"t{counter['n']}", "amount": 1, "created": 1}]})

    mock_http["handler"] = handler
    conn = stripe.StripeConnector(_cfg("stripe", {"api_key": "sk_test_x"}))
    assert len(_run(conn.fetch_ledger())) == 3


# --- Chargebee ---------------------------------------------------------------

def test_chargebee_plans_fall_back_to_item_prices(mock_http):
    def handler(req):
        if req.url.path.endswith("/plans"):
            return httpx.Response(400, json={"api_error_code": "configuration_incompatible",
                                             "message": "The API endpoint is incompatible with the product catalog version."})
        if req.url.path.endswith("/item_prices"):
            return httpx.Response(200, json={"list": [{"item_price": {"id": "pro-USD-monthly"}}]})
        return httpx.Response(200, json={"list": []})

    mock_http["handler"] = handler
    conn = chargebee.ChargebeeConnector(_cfg("chargebee", {"site": "acme", "api_key": "k"}))
    assert _run(conn.get_plans()) == [{"id": "pro-USD-monthly"}]


def test_chargebee_invoices_page_past_100(mock_http):
    def handler(req):
        if req.url.path.endswith("/invoices"):
            offset = req.url.params.get("offset")
            if offset is None:
                return httpx.Response(200, json={
                    "list": [{"invoice": {"id": f"i{i}"}} for i in range(100)], "next_offset": "[\"x\",\"1\"]"})
            assert offset == "[\"x\",\"1\"]"
            return httpx.Response(200, json={"list": [{"invoice": {"id": "i100"}}]})
        return httpx.Response(200, json={"list": []})

    mock_http["handler"] = handler
    conn = chargebee.ChargebeeConnector(_cfg("chargebee", {"site": "acme", "api_key": "k"}))
    invoices = _run(conn.get_invoices_raw())
    assert len(invoices) == 101
    # the cached list is reused by fetch_invoices/fetch_ledger
    _run(conn.fetch_invoices())
    _run(conn.fetch_ledger())
    assert len([r for r in mock_http["seen"] if r.url.path.endswith("/invoices")]) == 4  # 2 direct + 2 to fill the cache, then reused


# --- WooCommerce -------------------------------------------------------------

def test_woocommerce_rejects_plain_http_without_sending_keys(mock_http):
    mock_http["handler"] = lambda req: pytest.fail("no request may be sent")
    conn = woocommerce.WooCommerceConnector(_cfg("woocommerce", {
        "store_url": "http://shop.example.com", "consumer_key": "ck", "consumer_secret": "cs"}))
    assert _run(conn.authenticate()) is False
    assert "https://" in conn.auth_error
    assert mock_http["seen"] == []


# --- Shiprocket --------------------------------------------------------------

def test_shiprocket_pages_until_short_page_without_meta(mock_http):
    def handler(req):
        page = int(req.url.params["page"])
        n = shiprocket.PER_PAGE if page < 3 else 7
        return httpx.Response(200, json={"data": [{"id": f"{page}-{i}"} for i in range(n)]})

    mock_http["handler"] = handler
    conn = shiprocket.ShiprocketConnector(_cfg("shiprocket", {"email": "a@b.in", "password": "p"}))
    conn._token = "t"
    rows, truncated = _run(conn._paged("/account/details/statement", {}))
    assert len(rows) == 2 * shiprocket.PER_PAGE + 7 and truncated is False
    assert len(mock_http["seen"]) == 3


def test_shiprocket_still_honours_meta_pagination(mock_http):
    def handler(req):
        return httpx.Response(200, json={"data": [{"id": 1}], "meta": {"pagination": {"total_pages": 2}}})

    mock_http["handler"] = handler
    conn = shiprocket.ShiprocketConnector(_cfg("shiprocket", {"email": "a@b.in", "password": "p"}))
    conn._token = "t"
    rows, truncated = _run(conn._paged("/orders", {}))
    assert len(rows) == 2 and truncated is False
