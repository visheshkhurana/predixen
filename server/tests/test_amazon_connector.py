"""Amazon Seller (SP-API) connector and its "Connect with Amazon" sign-in.
No network: httpx MockTransport."""

import asyncio
from datetime import date
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from server.connectors import amazon
from server.connectors.base import ConnectorConfig
from server.connectors.registry import ConnectorRegistry

_RealAsyncClient = httpx.AsyncClient


def _run(coro):
    return asyncio.run(coro)


def _cfg(creds):
    return ConnectorConfig(provider_id="amazon", company_id=1, credentials=creds, settings={})


CREDS = {"client_id": " amzn1.application-oa2-client.x ", "client_secret": "sec", "refresh_token": "Atzr|r"}


@pytest.fixture
def mock_http(monkeypatch):
    state = {"handler": None, "seen": []}

    class Patched(_RealAsyncClient):
        def __init__(self, *a, **kw):
            def wrapped(request):
                state["seen"].append(request)
                return state["handler"](request)
            kw["transport"] = httpx.MockTransport(wrapped)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    monkeypatch.setattr(amazon, "PAGE_INTERVAL", 0)
    return state


def inr(v):
    return {"CurrencyCode": "INR", "CurrencyAmount": v}


def shipment(order="403-1", principal=1000, tax=180, ship=50, ship_tax=9, promo=-100,
             fees=(("Commission", -120), ("FixedClosingFee", -25)), qty=1, market="Amazon.in"):
    return {
        "AmazonOrderId": order, "MarketplaceName": market,
        "ShipmentItemList": [{
            "QuantityShipped": qty,
            "ItemChargeList": [
                {"ChargeType": "Principal", "ChargeAmount": inr(principal)},
                {"ChargeType": "Tax", "ChargeAmount": inr(tax)},
                {"ChargeType": "ShippingCharge", "ChargeAmount": inr(ship)},
                {"ChargeType": "ShippingTax", "ChargeAmount": inr(ship_tax)},
            ],
            "ItemFeeList": [{"FeeType": t, "FeeAmount": inr(a)} for t, a in fees],
            "PromotionList": [{"PromotionType": "PromotionMetaDataDefinitionValue", "PromotionAmount": inr(promo)}],
            "ItemTaxWithheldList": [{"TaxesWithheld": [{"ChargeType": "TCS-IGST", "ChargeAmount": inr(-10)}]}],
        }],
    }


def refund(order="403-1", principal=-1000, tax=-180, fee_back=100):
    return {
        "AmazonOrderId": order, "MarketplaceName": "Amazon.in",
        "ShipmentItemAdjustmentList": [{
            "ItemChargeAdjustmentList": [
                {"ChargeType": "Principal", "ChargeAmount": inr(principal)},
                {"ChargeType": "Tax", "ChargeAmount": inr(tax)},
            ],
            "ItemFeeAdjustmentList": [{"FeeType": "Commission", "FeeAmount": inr(fee_back)},
                                      {"FeeType": "RefundCommission", "FeeAmount": inr(-20)}],
        }],
    }


# --- pure summary --------------------------------------------------------------

def test_summary_sales_ex_gst_fees_and_refunds():
    s = amazon.summarize_events(
        [shipment("A"), shipment("B", qty=2)],
        [refund("A")],
        [{"FeeList": [{"FeeType": "Subscription", "FeeAmount": inr(-499)}]}],
    )
    assert s["orders_shipped"] == 2 and s["units_shipped"] == 3 and s["refunded_orders"] == 1
    assert s["sales_ex_gst"] == 2100.0  # (1000 + 50) x 2, tax lines excluded
    assert s["gst_on_sales"] == 378.0
    assert s["promotions"] == 200.0
    assert s["net_sales_ex_gst"] == 1900.0
    assert s["refunds_ex_gst"] == 1000.0
    # 2 x (120 + 25) + 499 - 100 + 20 = 709
    assert s["amazon_fees"] == 709.0
    assert s["fee_breakdown"]["Subscription"] == 499.0
    assert s["fee_breakdown"]["Commission"] == 140.0  # 240 charged, 100 refunded
    assert s["amazon_fee_pct"] == round(709 / 1900, 5)
    assert s["tax_withheld"] == 20.0  # claimable TCS, not a fee
    assert s["warnings"] == []


def test_no_gst_lines_means_ex_gst_unknown_not_guessed():
    s = amazon.summarize_events([shipment(tax=0, ship_tax=0)], [])
    assert s["sales_ex_gst"] is None and s["net_sales_ex_gst"] is None
    assert s["amazon_fee_pct"] is None
    assert s["warnings"]


def test_empty_month_has_no_rate():
    s = amazon.summarize_events([], [])
    assert s["orders_shipped"] == 0
    assert s["amazon_fee_pct"] is None
    assert s["warnings"] == []


def test_other_marketplaces_and_currencies_skipped():
    usd = shipment("U")
    for c in usd["ShipmentItemList"][0]["ItemChargeList"]:
        c["ChargeAmount"]["CurrencyCode"] = "USD"
    s = amazon.summarize_events([shipment("A"), shipment("X", market="Amazon.ae"), usd], [])
    assert s["other_marketplace_events_skipped"] == 1
    assert s["non_inr_lines_skipped"] == 4
    assert s["sales_ex_gst"] == 1050.0


def test_ads_payments_use_base_value_and_refunds_reverse():
    ads = [{"transactionType": "charge", "baseValue": inr(1000), "transactionValue": inr(1180)},
           {"transactionType": "refund", "baseValue": inr(-200)}]
    s = amazon.summarize_events([], [], [], ads)
    assert s["sponsored_ads_billed_ex_gst"] == 800.0


def test_month_window_is_india_time():
    after, before = amazon.month_window(date(2026, 10, 1), date(2026, 10, 31))
    assert after == "2026-09-30T18:30:00Z"
    assert before == "2026-10-31T18:30:00Z"


def test_marketplaces_from_participations():
    body = {"payload": [
        {"marketplace": {"id": "A21TJRUUN4KGV"}, "participation": {"isParticipating": True}},
        {"marketplace": {"id": "A2VIGQ35RCS4UG"}, "participation": {"isParticipating": False}},
    ]}
    assert amazon.marketplaces_from_participations(body) == ["A21TJRUUN4KGV"]


# --- connector over HTTP ---------------------------------------------------------

def test_registered():
    assert ConnectorRegistry.get_connector_class("amazon") is amazon.AmazonSellerConnector


def test_missing_credentials_fail_without_network(mock_http):
    mock_http["handler"] = lambda r: pytest.fail("no request expected")
    assert _run(amazon.AmazonSellerConnector(_cfg({})).authenticate()) is False


def _api(pages):
    """LWA token, participations, then the given financialEvents pages."""
    def handler(req):
        if req.url.host == "api.amazon.com":
            return httpx.Response(200, json={"access_token": "Atza|t", "expires_in": 3600})
        if req.url.path == "/sellers/v1/marketplaceParticipations":
            return httpx.Response(200, json={"payload": []})
        if req.url.path == "/finances/v0/financialEvents":
            return httpx.Response(200, json={"payload": pages.pop(0)})
        return httpx.Response(404)
    return handler


def test_auth_refreshes_token_and_uses_eu_host(mock_http):
    mock_http["handler"] = _api([])
    conn = amazon.AmazonSellerConnector(_cfg(CREDS))
    assert _run(conn.authenticate()) is True
    tok, check = mock_http["seen"][:2]
    form = parse_qs(tok.content.decode())
    assert form["grant_type"] == ["refresh_token"] and form["refresh_token"] == ["Atzr|r"]
    assert form["client_id"] == ["amzn1.application-oa2-client.x"]
    assert str(check.url).startswith("https://sellingpartnerapi-eu.amazon.com/")
    assert check.headers["x-amz-access-token"] == "Atza|t"


def test_sync_pages_and_reports_channel_sales(mock_http):
    pages = [
        {"NextToken": "n1", "FinancialEvents": {"ShipmentEventList": [shipment("A")], "RefundEventList": []}},
        {"FinancialEvents": {"ShipmentEventList": [shipment("B")], "RefundEventList": [refund("A")]}},
    ]
    mock_http["handler"] = _api(pages)
    result = _run(amazon.AmazonSellerConnector(_cfg(CREDS)).sync_all())
    assert result.success, result.errors
    assert result.records_synced == 3
    fin = [r for r in mock_http["seen"] if r.url.path == "/finances/v0/financialEvents"]
    assert len(fin) == 2
    q2 = parse_qs(urlparse(str(fin[1].url)).query)
    assert q2["NextToken"] == ["n1"] and q2["MaxResultsPerPage"] == ["100"]
    assert "d2c_month" not in result.metadata  # never overwrites the website's month
    month = result.metadata["channel_sales"]["months"][0]
    assert result.metadata["channel_sales"]["channel"] == "amazon"
    assert month["orders_shipped"] == 2 and month["sales_ex_gst"] == 2100.0


def test_truncated_month_blanks_totals(mock_http, monkeypatch):
    monkeypatch.setattr(amazon, "MAX_PAGES", 2)
    pages = [{"NextToken": f"n{i}", "FinancialEvents": {"ShipmentEventList": [shipment(str(i))]}} for i in range(2)]
    mock_http["handler"] = _api(pages)
    result = _run(amazon.AmazonSellerConnector(_cfg(CREDS)).sync_all())
    assert result.success and result.errors
    assert result.metadata["amazon"]["orders_shipped"] is None
    assert result.metadata["amazon"]["net_sales_ex_gst"] is None


def test_failed_token_asks_to_reconnect(mock_http):
    mock_http["handler"] = lambda r: httpx.Response(400, json={"error": "invalid_grant"})
    result = _run(amazon.AmazonSellerConnector(_cfg(CREDS)).sync_all())
    assert not result.success and result.metadata.get("needs_reauth")


# --- "Connect with Amazon" -----------------------------------------------------------

def test_oauth_provider_needs_app_id(monkeypatch):
    from server.api import connector_oauth as co
    p = co.PROVIDERS["amazon"]
    monkeypatch.setenv("AMAZON_SP_CLIENT_ID", "cid")
    monkeypatch.setenv("AMAZON_SP_CLIENT_SECRET", "cs")
    monkeypatch.delenv("AMAZON_SP_APP_ID", raising=False)
    assert p.configured() is False
    monkeypatch.setenv("AMAZON_SP_APP_ID", "amzn1.sp.solution.abc")
    assert p.configured() is True
    assert p.code_param == "spapi_oauth_code"


def test_amazon_consent_params_draft_and_published(monkeypatch):
    from server.api import connector_oauth as co
    monkeypatch.setenv("AMAZON_SP_APP_ID", "amzn1.sp.solution.abc")
    monkeypatch.delenv("AMAZON_SP_PUBLISHED", raising=False)
    assert co._amazon_authorize_params({}) == {"application_id": "amzn1.sp.solution.abc", "version": "beta"}
    monkeypatch.setenv("AMAZON_SP_PUBLISHED", "1")
    assert co._amazon_authorize_params({}) == {"application_id": "amzn1.sp.solution.abc"}


def test_finalize_amazon_finds_region_and_marketplaces(mock_http):
    from server.api import connector_oauth as co

    def handler(req):
        if req.url.host == "sellingpartnerapi-eu.amazon.com":
            return httpx.Response(200, json={"payload": [
                {"marketplace": {"id": "A21TJRUUN4KGV"}, "participation": {"isParticipating": True}}]})
        return httpx.Response(403)
    mock_http["handler"] = handler

    async def go():
        async with httpx.AsyncClient() as client:
            return await co._finalize_amazon(
                client, {"access_token": "Atza|t", "refresh_token": "Atzr|r"},
                {"selling_partner_id": "A1SELLER"}, {"client_id": "cid", "client_secret": "cs"})
    creds = _run(go())
    assert creds["region"] == "eu" and creds["marketplace_ids"] == ["A21TJRUUN4KGV"]
    assert creds["refresh_token"] == "Atzr|r" and creds["selling_partner_id"] == "A1SELLER"


def test_finalize_amazon_without_refresh_token_errors():
    from server.api import connector_oauth as co
    with pytest.raises(co.OAuthConnectError):
        _run(co._finalize_amazon(None, {"access_token": "t"}, {}, {}))
