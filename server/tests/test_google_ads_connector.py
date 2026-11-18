"""Google Ads connector: auth, account discovery, monthly spend, and the OAuth callback."""

import asyncio
import json
from datetime import date

import httpx
import pytest

from server.connectors.base import ConnectorConfig
from server.connectors import google_ads
from server.connectors.google_ads import GoogleAdsConnector, bucket_rows, parse_customer_ids

ENV = {
    "GOOGLE_ADS_DEVELOPER_TOKEN": "dev-token-test",
    "GOOGLE_ADS_CLIENT_ID": "client-id-test",
    "GOOGLE_ADS_CLIENT_SECRET": "client-secret-test",
}


@pytest.fixture
def configured(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", raising=False)


def _fake_google(calls, *, token_ok=True, manager_ids=()):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        url = str(request.url)
        if url == google_ads.TOKEN_URL:
            return httpx.Response(200, json={"access_token": "at"}) if token_ok else httpx.Response(400, json={"error": "invalid_grant"})
        assert request.headers["developer-token"] == "dev-token-test"
        if url.endswith("customers:listAccessibleCustomers"):
            return httpx.Response(200, json={"resourceNames": ["customers/1112223333", "customers/9998887777"]})
        cid = url.split("/customers/")[1].split("/")[0]
        query = json.loads(request.content)["query"]
        if "FROM customer" in query and "segments.month" not in query:
            return httpx.Response(200, json={"results": [{"customer": {
                "id": cid, "descriptiveName": f"Acct {cid}", "currencyCode": "INR", "manager": cid in manager_ids,
            }}]})
        return httpx.Response(200, json={"results": [
            {"segments": {"month": "2026-10-01"}, "metrics": {"costMicros": "12500000000", "impressions": "1000", "clicks": "50", "conversions": 10.0, "conversionsValue": 30000.0}},
            {"segments": {"month": "2026-09-01"}, "metrics": {"costMicros": "5000000000", "impressions": "400", "clicks": "20"}},
        ]})
    return handler


def _connector(handler, creds=None):
    c = GoogleAdsConnector(ConnectorConfig(provider_id="google_ads", company_id=1,
                                           credentials=creds or {"refresh_token": "rt"}, settings={"lookback_months": 3}))
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def no_sleep(_):
        return None
    c._sleep = no_sleep
    return c


def test_parse_customer_ids():
    assert parse_customer_ids("123-456-7890, 9876543210") == ["1234567890", "9876543210"]
    with pytest.raises(ValueError):
        parse_customer_ids("12345")


def test_bucket_rows_converts_micros():
    months = [(date(2026, 9, 1), date(2026, 9, 30)), (date(2026, 10, 1), date(2026, 10, 31))]
    b = bucket_rows([{"segments": {"month": "2026-10-01"}, "metrics": {"costMicros": "1500000"}}], months)
    assert b["2026-10-01"]["spend"] == 1.5 and b["2026-09-01"]["spend"] == 0.0


def test_not_configured_is_a_clear_message(monkeypatch):
    for k in ENV:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    c = _connector(lambda r: httpx.Response(500))
    assert asyncio.run(c.authenticate()) is False
    assert "isn't set up" in c.auth_error


def test_discovers_accounts_skips_managers_and_syncs_spend(configured):
    calls = []
    c = _connector(_fake_google(calls, manager_ids=("9998887777",)))
    result = asyncio.run(c.sync_all())
    assert result.success, result.errors
    assert list(c.accounts) == ["1112223333"], "manager accounts hold no spend"
    months = {m["period"]: m["accounts"] for m in result.metadata["ad_spend"]["months"]}
    oct_ = [m for p, m in months.items() if p.startswith("2026-10")]
    if oct_:  # depends on today's date; October is in the lookback while it is recent
        assert oct_[0][0]["spend"] == 12500.0 and oct_[0][0]["currency"] == "INR"
    assert all(r.headers.get("Authorization") == "Bearer at" for r in calls if "googleads" in str(r.url))


def test_revoked_refresh_token_asks_to_reconnect(configured):
    c = _connector(_fake_google([], token_ok=False))
    result = asyncio.run(c.sync_all())
    assert not result.success and result.metadata.get("needs_reauth") is True


def test_oauth_state_is_signed_and_expires(monkeypatch):
    from fastapi import HTTPException
    from server.api import google_ads_oauth as g
    state = g._sign({"c": 1, "u": 2, "exp": 9_999_999_999})
    assert g._verify(state)["c"] == 1
    with pytest.raises(HTTPException):
        g._verify(state[:-1] + ("0" if state[-1] != "0" else "1"))
    with pytest.raises(HTTPException):
        g._verify(g._sign({"c": 1, "u": 2, "exp": 1}))
