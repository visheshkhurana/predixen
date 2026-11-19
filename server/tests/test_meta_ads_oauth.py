"""Meta Ads "Connect with Facebook": config gating, the dialog URL, the token
exchange (short -> long-lived) and ad account discovery. No network: Graph is
an httpx MockTransport."""

import asyncio
import urllib.parse

import httpx
import pytest

from server.api import meta_ads_oauth
from server.connectors import meta_ads
from server.connectors.base import ConnectorConfig


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "4490979524476696")
    monkeypatch.setenv("META_APP_SECRET", "app-secret-test")
    monkeypatch.setenv("META_LOGIN_CONFIG_ID", "1638788421309978")


def test_needs_all_three_settings(monkeypatch):
    for name in ("META_APP_ID", "META_APP_SECRET", "META_LOGIN_CONFIG_ID"):
        monkeypatch.delenv(name, raising=False)
    assert not meta_ads_oauth.is_configured()
    monkeypatch.setenv("META_APP_ID", "1")
    monkeypatch.setenv("META_APP_SECRET", "s")
    assert not meta_ads_oauth.is_configured()  # no login configuration yet
    monkeypatch.setenv("META_LOGIN_CONFIG_ID", "2")
    assert meta_ads_oauth.is_configured()


def test_code_is_swapped_for_a_long_lived_token(configured):
    seen = []

    def handler(request):
        q = dict(urllib.parse.parse_qsl(request.url.query.decode()))
        seen.append(q)
        assert request.url.path.endswith("/oauth/access_token")
        assert q["client_secret"] == "app-secret-test"
        if q.get("grant_type") == "fb_exchange_token":
            assert q["fb_exchange_token"] == "short"
            return httpx.Response(200, json={"access_token": "long", "expires_in": 5183944})
        assert q["code"] == "the-code" and q["redirect_uri"] == "https://x/cb"
        return httpx.Response(200, json={"access_token": "short", "expires_in": 3600})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await meta_ads_oauth.exchange_code(client, "the-code", "https://x/cb")

    assert asyncio.run(run()) == {"access_token": "long", "expires_in": 5183944}
    assert len(seen) == 2


def test_bad_code_raises(configured):
    async def run():
        transport = httpx.MockTransport(lambda r: httpx.Response(400, json={"error": {"code": 100}}))
        async with httpx.AsyncClient(transport=transport) as client:
            await meta_ads_oauth.exchange_code(client, "bad", "https://x/cb")

    with pytest.raises(ValueError):
        asyncio.run(run())


def test_disabled_and_closed_ad_accounts_are_skipped():
    def handler(request):
        assert request.url.path.endswith("/me/adaccounts")
        return httpx.Response(200, json={"data": [
            {"account_id": "111", "name": "Live", "account_status": 1},
            {"account_id": "222", "name": "Disabled", "account_status": 2},
            {"account_id": "333", "name": "Closed", "account_status": 101},
            {"account_id": "444", "name": "Unsettled", "account_status": 3},
        ]})

    conn = meta_ads.MetaAdsConnector(ConnectorConfig(
        provider_id="meta_ads", company_id=1, credentials={"access_token": "EAA"}, settings={}))
    conn._client = httpx.AsyncClient(base_url=meta_ads.BASE_URL, transport=httpx.MockTransport(handler))
    accounts = asyncio.run(meta_ads_oauth.list_ad_accounts(conn))
    assert [a["account_id"] for a in accounts] == ["111", "444"]
