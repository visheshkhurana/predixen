"""Shared "Connect with <provider>" flow, rotated refresh tokens, Zoho data
centres and Salesforce refresh. No network: httpx MockTransport."""

import asyncio
import json
import urllib.parse

import httpx
import pytest

from server.api import connector_oauth as co
from server.connectors.base import ConnectorConfig
from server.connectors.salesforce import SalesforceConnector
from server.connectors.xero import XeroConnector
from server.connectors.zoho_books import ZohoBooksConnector, zoho_dc_from_accounts_server, zoho_urls


def _run(coro):
    return asyncio.run(coro)


# --- rotated credentials ----------------------------------------------------

def test_rotated_refresh_token_is_reported():
    conn = XeroConnector(ConnectorConfig(provider_id="xero", company_id=1, credentials={
        "client_id": "c", "client_secret": "s", "access_token": "old-a", "refresh_token": "old-r"}, settings={}))
    assert conn.rotated_credentials() is None
    conn._access_token, conn._refresh_token = "new-a", "new-r"
    rotated = conn.rotated_credentials()
    assert rotated["access_token"] == "new-a" and rotated["refresh_token"] == "new-r"
    assert rotated["client_id"] == "c"  # everything else kept


def test_persist_writes_new_credentials(monkeypatch):
    from server.api import connectors as api
    saved = {}
    monkeypatch.setattr(api, "save_metadata_value", lambda db, company, path, value, **kw: saved.update(path=path, value=value))
    monkeypatch.setattr(api, "encrypt_credentials", lambda c: json.dumps(c))

    class Fake:
        def rotated_credentials(self):
            return {"refresh_token": "r2"}

    class Co:
        id = 7

    store = {"xero": {"connected": True, "credentials": "old"}}
    api._persist_rotated_credentials(None, Co(), "xero", Fake(), store)
    assert saved["path"] == ("connectors", "xero")
    assert json.loads(saved["value"]["credentials"]) == {"refresh_token": "r2"}
    assert store["xero"]["credentials"] == saved["value"]["credentials"]  # later status write keeps it


# --- Zoho data centres -------------------------------------------------------

def test_zoho_dc_parsing_only_accepts_known_hosts():
    assert zoho_dc_from_accounts_server("https://accounts.zoho.in") == "in"
    assert zoho_dc_from_accounts_server("https://accounts.zoho.com.au") == "com.au"
    assert zoho_dc_from_accounts_server("https://accounts.evil.example") == "com"
    assert zoho_dc_from_accounts_server("https://accounts.zoho.in.evil.example") == "com"
    assert zoho_urls("in") == ("https://accounts.zoho.in/oauth/v2/token", "https://www.zohoapis.in/books/v3")
    assert zoho_dc_from_accounts_server("https://accounts.zoho.ae") == "ae"
    assert zoho_dc_from_accounts_server("https://accounts.zoho.sg") == "sg"
    assert zoho_dc_from_accounts_server("https://accounts.zohocloud.ca") == "ca"
    assert zoho_urls("ca") == ("https://accounts.zohocloud.ca/oauth/v2/token", "https://www.zohoapis.ca/books/v3")


def test_zoho_connector_uses_dc_hosts_and_rejects_200_error():
    conn = ZohoBooksConnector(ConnectorConfig(provider_id="zoho_books", company_id=1, credentials={
        "client_id": "c", "client_secret": "s", "refresh_token": "r", "organization_id": "1", "dc": "in"}, settings={}))
    assert conn._api_base == "https://www.zohoapis.in/books/v3"
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"error": "invalid_code"})

    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    httpx.AsyncClient = Patched
    try:
        assert _run(conn._refresh_access_token()) is False
    finally:
        httpx.AsyncClient = orig
    assert seen == ["https://accounts.zoho.in/oauth/v2/token"]


# --- provider finalizers -----------------------------------------------------

def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


APP = {"client_id": "cid", "client_secret": "csec", "scopes": ""}


def test_zoho_finalize_redeems_at_users_dc_and_picks_default_org():
    def handler(request):
        if request.url.path == "/oauth/v2/token":
            assert request.url.host == "accounts.zoho.in"
            return httpx.Response(200, json={"access_token": "a", "refresh_token": "r"})
        assert request.url.host == "www.zohoapis.in"
        return httpx.Response(200, json={"organizations": [
            {"organization_id": 11, "name": "Other"}, {"organization_id": 22, "name": "Main", "is_default_org": True}]})

    async def go():
        async with _client(handler) as c:
            return await co._finalize_zoho(c, {}, {"code": "x", "accounts-server": "https://accounts.zoho.in",
                                                   "redirect_uri": "https://app/cb"}, APP)
    creds = _run(go())
    assert creds["organization_id"] == "22" and creds["dc"] == "in" and creds["refresh_token"] == "r"


def test_zoho_finalize_without_books_org_explains():
    def handler(request):
        if request.url.path == "/oauth/v2/token":
            return httpx.Response(200, json={"access_token": "a", "refresh_token": "r"})
        return httpx.Response(200, json={"organizations": []})

    async def go():
        async with _client(handler) as c:
            return await co._finalize_zoho(c, {}, {"code": "x", "redirect_uri": "u"}, APP)
    with pytest.raises(co.OAuthConnectError):
        _run(go())


def test_quickbooks_needs_realm():
    async def go(params):
        async with _client(lambda r: httpx.Response(500)) as c:
            return await co._finalize_quickbooks(c, {"access_token": "a", "refresh_token": "r"}, params, APP)
    with pytest.raises(co.OAuthConnectError):
        _run(go({}))
    assert _run(go({"realmId": "123"}))["realm_id"] == "123"


def test_xero_picks_first_organisation_tenant():
    def handler(request):
        return httpx.Response(200, json=[{"tenantId": "p1", "tenantType": "PRACTICEMANAGER"},
                                         {"tenantId": "t1", "tenantType": "ORGANISATION", "tenantName": "Acme"}])

    async def go():
        async with _client(handler) as c:
            return await co._finalize_xero(c, {"access_token": "a", "refresh_token": "r"}, {}, APP)
    creds = _run(go())
    assert creds["tenant_id"] == "t1" and creds["_hint"] == "Acme"


def test_salesforce_requires_https_instance():
    async def go(token):
        async with _client(lambda r: httpx.Response(500)) as c:
            return await co._finalize_salesforce(c, token, {}, APP)
    with pytest.raises(co.OAuthConnectError):
        _run(go({"access_token": "a", "instance_url": "http://x"}))
    assert _run(go({"access_token": "a", "refresh_token": "r", "instance_url": "https://acme.my.salesforce.com/"}))[
        "instance_url"] == "https://acme.my.salesforce.com"


def test_exchange_code_uses_basic_auth_when_required(monkeypatch):
    monkeypatch.setenv("XERO_CLIENT_ID", "xid")
    monkeypatch.setenv("XERO_CLIENT_SECRET", "xsec")
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization", "")
        seen["body"] = dict(urllib.parse.parse_qsl(request.content.decode()))
        return httpx.Response(200, json={"access_token": "a", "refresh_token": "r"})

    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    token = _run(co.exchange_code(co.PROVIDERS["xero"], "code1", "https://app/cb"))
    assert token["access_token"] == "a"
    assert seen["auth"].startswith("Basic ")
    assert "client_secret" not in seen["body"] and seen["body"]["code"] == "code1"


def test_providers_configured_from_env(monkeypatch):
    for p in co.PROVIDERS.values():
        monkeypatch.delenv(f"{p.env_prefix}_CLIENT_ID", raising=False)
    assert not co.PROVIDERS["zoho_books"].configured()
    monkeypatch.setenv("ZOHO_CLIENT_ID", "a")
    monkeypatch.setenv("ZOHO_CLIENT_SECRET", "b")
    assert co.PROVIDERS["zoho_books"].configured()


# --- Salesforce refresh ------------------------------------------------------

def test_salesforce_refreshes_before_auth(monkeypatch):
    conn = SalesforceConnector(ConnectorConfig(provider_id="salesforce", company_id=1, credentials={
        "instance_url": "https://acme.my.salesforce.com", "access_token": "stale",
        "refresh_token": "r", "client_id": "c", "client_secret": "s"}, settings={}))

    def handler(request):
        if request.url.path == "/services/oauth2/token":
            return httpx.Response(200, json={"access_token": "fresh"})
        assert request.headers["authorization"] == "Bearer fresh"
        return httpx.Response(200, json={"sobjects": []})

    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    assert _run(conn.authenticate()) is True
    assert conn.rotated_credentials()["access_token"] == "fresh"
