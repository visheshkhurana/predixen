"""Salesforce external client apps force refresh token rotation: each refresh
returns a new refresh_token and retires the old one, so the connector must
hand the new one to rotated_credentials() or the next sync fails."""

import asyncio

import httpx

from server.connectors.base import ConnectorConfig
from server.connectors.salesforce import SalesforceConnector


def _patch(monkeypatch, handler):
    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)


def _conn():
    return SalesforceConnector(ConnectorConfig(provider_id="salesforce", company_id=1, credentials={
        "access_token": "stale", "refresh_token": "r1", "client_id": "i", "client_secret": "s",
        "instance_url": "https://acme.my.salesforce.com/"}))


def test_rotated_refresh_token_is_saved(monkeypatch):
    seen = {}

    def handler(req: httpx.Request):
        seen["body"] = req.content.decode()
        return httpx.Response(200, json={"access_token": "fresh", "refresh_token": "r2",
                                         "instance_url": "https://acme.my.salesforce.com"})

    _patch(monkeypatch, handler)
    conn = _conn()
    assert asyncio.run(conn._refresh_access_token()) is True
    assert "refresh_token=r1" in seen["body"] and "client_secret=s" in seen["body"]
    rotated = conn.rotated_credentials()
    assert rotated["refresh_token"] == "r2"
    assert rotated["access_token"] == "fresh"


def test_refresh_without_rotation_keeps_old_token(monkeypatch):
    _patch(monkeypatch, lambda req: httpx.Response(200, json={"access_token": "fresh"}))
    conn = _conn()
    assert asyncio.run(conn._refresh_access_token()) is True
    assert conn.rotated_credentials()["refresh_token"] == "r1"
