"""Plaid picks its host from the access token; Brex asks from a start date."""

import asyncio

import httpx

from server.connectors.base import ConnectorConfig
from server.connectors.brex import BrexConnector
from server.connectors.plaid import PlaidConnector


def _cfg(provider, **creds):
    return ConnectorConfig(provider_id=provider, company_id=1, credentials=creds)


def test_plaid_sandbox_token_uses_sandbox_host():
    assert PlaidConnector(_cfg("plaid", client_id="c", secret="s", access_token="access-sandbox-1"))._base_url == "https://sandbox.plaid.com"
    assert PlaidConnector(_cfg("plaid", client_id="c", secret="s", access_token="access-production-1"))._base_url == "https://production.plaid.com"


def test_brex_card_transactions_send_posted_at_start(monkeypatch):
    seen = []

    def handler(req):
        seen.append(dict(req.url.params))
        return httpx.Response(200, json={"items": [], "next_cursor": None})

    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    conn = BrexConnector(_cfg("brex", api_key="k"))
    conn._authenticated = True
    asyncio.run(conn.fetch_ledger())
    card = [p for p in seen if "posted_at_start" in p]
    assert card and card[0]["posted_at_start"].endswith("T00:00:00Z")


def _plaid(token, **creds):
    return PlaidConnector(ConnectorConfig(provider_id="plaid", company_id=1, credentials={
        "client_id": "c", "secret": "s", "access_token": token, **creds}, settings={}))


def test_plaid_token_prefix_beats_form_environment():
    assert _plaid("access-sandbox-1", environment="production")._base_url == "https://sandbox.plaid.com"
    assert _plaid("access-production-1", environment="sandbox")._base_url == "https://production.plaid.com"


def test_plaid_form_environment_used_when_token_has_no_prefix():
    assert _plaid("legacy-token", environment=" Sandbox ")._base_url == "https://sandbox.plaid.com"
    assert _plaid("legacy-token")._base_url == "https://production.plaid.com"
    assert _plaid("legacy-token", environment="bogus")._base_url == "https://production.plaid.com"


def test_gusto_requests_pin_api_version():
    from server.connectors.gusto import GUSTO_API_VERSION, GustoConnector
    conn = GustoConnector(ConnectorConfig(provider_id="gusto", company_id=1, credentials={
        "access_token": "a"}, settings={}))
    client = asyncio.run(conn._get_client())
    assert client.headers["X-Gusto-API-Version"] == GUSTO_API_VERSION == "2026-06-15"
    asyncio.run(client.aclose())
