"""FreshBooks and Wave connect through OAuth and keep working past the first
token: both providers issue short-lived access tokens with rotating refresh
tokens, and the old forms only took a pasted access token."""

import asyncio
import json

import httpx

from server.api import connector_oauth as co
from server.connectors.base import ConnectorConfig
from server.connectors.wave import WaveConnector


def _run(coro):
    return asyncio.run(coro)


def test_providers_registered():
    assert co.PROVIDERS["freshbooks"].authorize_url == "https://auth.freshbooks.com/oauth/authorize"
    assert co.PROVIDERS["freshbooks"].token_url == ""
    assert "user:invoices:read" in co.PROVIDERS["freshbooks"].default_scopes
    assert co.PROVIDERS["wave"].token_url == "https://api.waveapps.com/oauth2/token/"
    assert "business:read" in co.PROVIDERS["wave"].default_scopes


def test_freshbooks_finalize_redeems_code_as_json_and_picks_account():
    seen = {}

    def handler(req: httpx.Request):
        if req.url.path == "/auth/oauth/token":
            seen["body"] = json.loads(req.content)
            return httpx.Response(200, json={"access_token": "at", "refresh_token": "rt"})
        if req.url.path == "/auth/api/v1/users/me":
            assert req.headers["authorization"] == "Bearer at"
            return httpx.Response(200, json={"response": {"business_memberships": [
                {"business": {"name": "Acme Studio", "account_id": "xZ9"}}]}})
        raise AssertionError(req.url)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await co._finalize_freshbooks(
                client, {}, {"code": "c1", "redirect_uri": "https://founderconsole.ai/cb"},
                {"client_id": "id", "client_secret": "sec"})

    creds = _run(go())
    assert seen["body"]["grant_type"] == "authorization_code" and seen["body"]["code"] == "c1"
    assert creds["account_id"] == "xZ9" and creds["refresh_token"] == "rt"
    assert creds["redirect_uri"] == "https://founderconsole.ai/cb" and creds["_hint"] == "Acme Studio"


def test_wave_finalize_keeps_business_and_refresh_token():
    creds = _run(co._finalize_wave(None, {"access_token": "a", "refresh_token": "r", "businessId": "B1",
                                          "businessName": "Shop"}, {}, {"client_id": "i", "client_secret": "s"}))
    assert creds["business_id"] == "B1" and creds["refresh_token"] == "r" and creds["_hint"] == "Shop"


def test_wave_refreshes_on_401_and_rotates(monkeypatch):
    calls = []

    def handler(req: httpx.Request):
        if req.url.path == "/oauth2/token/":
            calls.append("refresh")
            return httpx.Response(200, json={"access_token": "fresh", "refresh_token": "r2"})
        if req.headers.get("authorization") == "Bearer stale":
            return httpx.Response(401, json={})
        calls.append("graphql")
        return httpx.Response(200, json={"data": {"businesses": {"edges": [{"node": {"id": "B1", "name": "x"}}]}}})

    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    conn = WaveConnector(ConnectorConfig(provider_id="wave", company_id=1, credentials={
        "access_token": "stale", "refresh_token": "r1", "client_id": "i", "client_secret": "s"}))
    assert _run(conn.authenticate()) is True
    assert calls == ["refresh", "graphql"]
    assert conn.rotated_credentials()["refresh_token"] == "r2"


def test_wave_refresh_403_explains_subscription(monkeypatch):
    def handler(req):
        if req.url.path == "/oauth2/token/":
            return httpx.Response(403, json={})
        return httpx.Response(401, json={})

    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    conn = WaveConnector(ConnectorConfig(provider_id="wave", company_id=1, credentials={
        "access_token": "stale", "refresh_token": "r1", "client_id": "i", "client_secret": "s"}))
    assert _run(conn.authenticate()) is False
    assert "Pro" in conn.auth_error
