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
