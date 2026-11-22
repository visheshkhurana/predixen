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


def test_zoho_authenticate_hits_real_org_endpoint(monkeypatch):
    conn = ZohoBooksConnector(ConnectorConfig(provider_id="zoho_books", company_id=1, credentials={
        "client_id": "c", "client_secret": "s", "access_token": "a", "organization_id": "947", "dc": "com"}, settings={}))
    seen = []

    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(200, json={"organization": {"organization_id": "947"}})

    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    assert _run(conn.authenticate()) is True
    assert seen == ["/books/v3/organizations/947"]


def test_hubspot_oauth_connection_refreshes_before_auth(monkeypatch):
    from server.connectors.hubspot import HubSpotConnector
    conn = HubSpotConnector(ConnectorConfig(provider_id="hubspot", company_id=1, credentials={
        "access_token": "stale", "refresh_token": "r", "client_id": "c", "client_secret": "s"}, settings={}))

    def handler(request):
        if request.url.path == "/oauth/2026-03/token":
            return httpx.Response(200, json={"access_token": "fresh", "refresh_token": "r"})
        assert request.headers["authorization"] == "Bearer fresh"
        return httpx.Response(200, json={"results": []})

    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    assert _run(conn.authenticate()) is True
    assert conn.rotated_credentials()["access_token"] == "fresh"


def test_hubspot_private_app_token_still_works_without_refresh(monkeypatch):
    from server.connectors.hubspot import HubSpotConnector
    conn = HubSpotConnector(ConnectorConfig(provider_id="hubspot", company_id=1, credentials={
        "access_token": "pat-na1-x"}, settings={}))

    def handler(request):
        assert request.url.path not in ("/oauth/v1/token", "/oauth/2026-03/token")
        return httpx.Response(200, json={"results": []})

    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    assert _run(conn.authenticate()) is True


def _zoho_conn():
    conn = ZohoBooksConnector(ConnectorConfig(provider_id="zoho_books", company_id=1, credentials={
        "client_id": "c", "client_secret": "s", "access_token": "a", "refresh_token": "r",
        "organization_id": "947", "dc": "com"}, settings={}))
    conn._authenticated = True
    return conn


def _patch_httpx(monkeypatch, handler):
    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)


def test_zoho_ledger_reads_lines_from_journal_detail(monkeypatch):
    def handler(request):
        path = request.url.path
        if path.endswith("/chartofaccounts"):
            return httpx.Response(200, json={"chartofaccounts": [{"account_id": "A1", "account_name": "Sales"}],
                                             "page_context": {"has_more_page": False}})
        if path.endswith("/journals"):
            return httpx.Response(200, json={"journals": [{"journal_id": "J1", "journal_date": "2026-11-01"}],
                                             "page_context": {"has_more_page": False}})
        if path.endswith("/journals/J1"):
            return httpx.Response(200, json={"journal": {"line_items": [
                {"line_id": "L1", "account_id": "A1", "amount": 500, "debit_or_credit": "credit"},
                {"line_id": "L2", "account_id": "A2", "amount": 500, "debit_or_credit": "debit"}]}})
        return httpx.Response(404)

    _patch_httpx(monkeypatch, handler)
    entries = _run(_zoho_conn().fetch_ledger())
    assert [(e.account_name, e.debit, e.credit) for e in entries] == [("Sales", 0.0, 500.0), ("", 500.0, 0.0)]


def test_zoho_lists_are_paginated(monkeypatch):
    pages = []

    def handler(request):
        page = int(request.url.params["page"])
        pages.append(page)
        rows = [{"expense_id": f"{page}-{i}"} for i in range(200 if page == 1 else 3)]
        return httpx.Response(200, json={"expenses": rows, "page_context": {"has_more_page": page == 1}})

    _patch_httpx(monkeypatch, handler)
    assert len(_run(_zoho_conn().fetch_expenses())) == 203
    assert pages == [1, 2]


def test_zoho_repeated_401_stops_after_one_refresh(monkeypatch):
    calls = {"refresh": 0, "org": 0}

    def handler(request):
        if request.url.path == "/oauth/v2/token":
            calls["refresh"] += 1
            return httpx.Response(200, json={"access_token": f"t{calls['refresh']}"})
        calls["org"] += 1
        return httpx.Response(401)

    _patch_httpx(monkeypatch, handler)
    conn = _zoho_conn()
    conn._authenticated = False
    assert _run(conn.authenticate()) is False
    assert calls == {"refresh": 1, "org": 2}


def test_ga4_finalize_picks_first_property():
    def handler(request):
        assert request.url.host == "analyticsadmin.googleapis.com"
        return httpx.Response(200, json={"accountSummaries": [
            {"propertySummaries": [{"property": "properties/987654", "displayName": "Acme Web"}]}]})

    async def go(token):
        async with _client(handler) as c:
            return await co._finalize_google_analytics(c, token, {}, APP)
    creds = _run(go({"access_token": "a", "refresh_token": "r"}))
    assert creds["property_id"] == "987654" and creds["_hint"] == "Acme Web" and creds["refresh_token"] == "r"
    with pytest.raises(co.OAuthConnectError):
        _run(go({"access_token": "a"}))  # no offline access


def test_ga4_finalize_picks_busiest_property_not_first():
    probed = []

    def handler(request):
        if request.url.host == "analyticsadmin.googleapis.com":
            return httpx.Response(200, json={"accountSummaries": [
                {"propertySummaries": [{"property": "properties/111", "displayName": "Old test site"}]},
                {"propertySummaries": [{"property": "properties/222", "displayName": "Live site"},
                                       {"property": "properties/333", "displayName": "Broken"}]}]})
        assert request.url.host == "analyticsdata.googleapis.com"
        pid = request.url.path.split("/")[-1].split(":")[0]
        probed.append(pid)
        if pid == "111":
            return httpx.Response(200, json={})  # no rows: no traffic
        if pid == "333":
            return httpx.Response(403, json={"error": {"code": 403}})
        return httpx.Response(200, json={"rows": [{"metricValues": [{"value": "1520"}]}]})

    async def go():
        async with _client(handler) as c:
            return await co._finalize_google_analytics(c, {"access_token": "a", "refresh_token": "r"}, {}, APP)
    creds = _run(go())
    assert creds["property_id"] == "222" and creds["_hint"] == "Live site"
    assert probed == ["111", "222", "333"]


def test_ga4_finalize_falls_back_to_first_when_probes_fail():
    def handler(request):
        if request.url.host == "analyticsadmin.googleapis.com":
            return httpx.Response(200, json={"accountSummaries": [{"propertySummaries": [
                {"property": "properties/1", "displayName": "A"}, {"property": "properties/2", "displayName": "B"}]}]})
        return httpx.Response(500)

    async def go():
        async with _client(handler) as c:
            return await co._finalize_google_analytics(c, {"access_token": "a", "refresh_token": "r"}, {}, APP)
    assert _run(go())["property_id"] == "1"


# --- Salesforce sandbox ------------------------------------------------------

def test_salesforce_sandbox_uses_test_host_only_when_asked():
    sf = co.PROVIDERS["salesforce"]
    assert sf.urls() == (sf.authorize_url, sf.token_url)
    assert sf.urls(sandbox=True) == ("https://test.salesforce.com/services/oauth2/authorize",
                                     "https://test.salesforce.com/services/oauth2/token")
    # Providers without a test environment ignore the flag.
    xero = co.PROVIDERS["xero"]
    assert xero.urls(sandbox=True) == (xero.authorize_url, xero.token_url)


def test_exchange_code_honours_token_url_override(monkeypatch):
    monkeypatch.setenv("SALESFORCE_CLIENT_ID", "sid")
    monkeypatch.setenv("SALESFORCE_CLIENT_SECRET", "ssec")
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"access_token": "a", "refresh_token": "r",
                                         "instance_url": "https://acme--dev.sandbox.my.salesforce.com"})

    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    sf = co.PROVIDERS["salesforce"]
    _run(co.exchange_code(sf, "c", "https://app/cb", "v", sf.urls(sandbox=True)[1]))
    assert seen["url"] == "https://test.salesforce.com/services/oauth2/token"
