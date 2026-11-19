"""Pipedrive v2 migration, HubSpot closed-won/currency detection, REST API
connector hardening. No network: httpx MockTransport."""

import asyncio

import httpx
import pytest

from server.connectors.base import ConnectorConfig
from server.connectors.hubspot import HubSpotConnector
from server.connectors.pipedrive import PipedriveConnector
from server.connectors.rest_api import RestAPIConnector


def _run(coro):
    return asyncio.run(coro)


def _patch_httpx(monkeypatch, handler):
    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)


# --- Pipedrive -----------------------------------------------------------------

def _pipedrive():
    return PipedriveConnector(ConnectorConfig(provider_id="pipedrive", company_id=1, credentials={
        "api_token": "tok", "company_domain": "acme"}, settings={}))


def test_pipedrive_uses_v2_cursor_pagination_and_header_token(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        assert request.url.host == "acme.pipedrive.com"
        assert request.headers["x-api-token"] == "tok"
        assert "api_token" not in request.url.params  # token never in the URL
        path = request.url.path
        if path == "/api/v1/users/me":
            return httpx.Response(200, json={"success": True, "data": {"id": 1}})
        assert path.startswith("/api/v2/"), path
        if path == "/api/v2/deals":
            if request.url.params.get("cursor") is None:
                return httpx.Response(200, json={"success": True, "data": [{"id": 1}, {"id": 2}],
                                                 "additional_data": {"next_cursor": "c2"}})
            assert request.url.params["cursor"] == "c2"
            return httpx.Response(200, json={"success": True, "data": [{"id": 3}],
                                             "additional_data": {"next_cursor": None}})
        raise AssertionError(path)

    _patch_httpx(monkeypatch, handler)
    deals = _run(_pipedrive().get_deals(limit=500))
    assert [d["id"] for d in deals] == [1, 2, 3]
    deal_calls = [r for r in seen if r.url.path == "/api/v2/deals"]
    assert len(deal_calls) == 2
    assert "start" not in deal_calls[0].url.params
    assert deal_calls[0].url.params["limit"] == "500"


def test_pipedrive_stops_at_limit(monkeypatch):
    def handler(request):
        if request.url.path == "/api/v1/users/me":
            return httpx.Response(200, json={"success": True})
        n = int(request.url.params["limit"])
        return httpx.Response(200, json={"success": True, "data": [{"id": i} for i in range(n)],
                                         "additional_data": {"next_cursor": "more"}})

    _patch_httpx(monkeypatch, handler)
    assert len(_run(_pipedrive().get_persons(limit=7))) == 7


def test_pipedrive_won_deals_resolve_org_name_from_org_id(monkeypatch):
    def handler(request):
        path = request.url.path
        if path == "/api/v1/users/me":
            return httpx.Response(200, json={"success": True})
        if path == "/api/v2/deals":
            assert request.url.params["status"] == "won"
            return httpx.Response(200, json={"success": True, "additional_data": {"next_cursor": None}, "data": [
                {"id": 10, "title": "Big", "value": 1200.0, "currency": "EUR", "org_id": 5,
                 "won_time": "2026-07-01T05:50:19Z", "pipeline_id": 1, "stage_id": 4},
                {"id": 11, "title": "No org", "value": 50, "currency": "USD", "org_id": None,
                 "won_time": "2026-07-02T00:00:00Z"},
            ]})
        if path == "/api/v2/organizations":
            return httpx.Response(200, json={"success": True, "additional_data": {"next_cursor": None},
                                             "data": [{"id": 5, "name": "Acme GmbH"}]})
        raise AssertionError(path)

    _patch_httpx(monkeypatch, handler)
    invoices = _run(_pipedrive().fetch_invoices())
    by_id = {i.external_id: i for i in invoices}
    assert by_id["10"].metadata["org_name"] == "Acme GmbH"
    assert by_id["10"].currency == "EUR" and by_id["10"].total == 1200.0
    assert by_id["11"].metadata["org_name"] == ""


def test_pipedrive_org_ledger_without_people_count(monkeypatch):
    def handler(request):
        if request.url.path == "/api/v1/users/me":
            return httpx.Response(200, json={"success": True})
        return httpx.Response(200, json={"success": True, "additional_data": {"next_cursor": None},
                                         "data": [{"id": 5, "name": "Acme", "add_time": "2026-01-01T00:00:00Z"}]})

    _patch_httpx(monkeypatch, handler)
    entries = _run(_pipedrive().fetch_ledger())
    assert entries[0].account_name == "Acme"
    assert "people_count" not in entries[0].metadata


def test_pipedrive_auth_failure_returns_empty(monkeypatch):
    _patch_httpx(monkeypatch, lambda r: httpx.Response(401, json={"success": False}))
    conn = _pipedrive()
    assert _run(conn.authenticate()) is False
    assert _run(conn.get_deals()) == []


# --- HubSpot -------------------------------------------------------------------

def _hubspot_deals_handler(deals, seen_props):
    def handler(request):
        if request.url.path == "/crm/v3/objects/deals":
            seen_props.append(request.url.params["properties"])
            return httpx.Response(200, json={"results": deals})
        return httpx.Response(200, json={"results": []})
    return handler


def test_hubspot_custom_pipeline_won_stage_counts_via_hs_is_closed_won(monkeypatch):
    deals = [
        {"id": "1", "properties": {"dealname": "Custom won", "amount": "1000", "dealstage": "12345678",
                                   "hs_is_closed_won": "true", "hs_is_closed": "true",
                                   "deal_currency_code": "INR", "closedate": "2026-10-01T00:00:00Z"}},
        {"id": "2", "properties": {"dealname": "Custom lost", "amount": "500", "dealstage": "87654321",
                                   "hs_is_closed_won": "false", "hs_is_closed": "true"}},
        {"id": "3", "properties": {"dealname": "Open", "amount": "300", "dealstage": "appointmentscheduled",
                                   "hs_is_closed_won": "false", "hs_is_closed": "false"}},
        {"id": "4", "properties": {"dealname": "Single-currency won", "amount": "200", "dealstage": "closedwon",
                                   "hs_is_closed_won": "true", "hs_is_closed": "true", "deal_currency_code": None,
                                   "closedate": "2026-10-02T00:00:00Z"}},
    ]
    seen = []
    _patch_httpx(monkeypatch, _hubspot_deals_handler(deals, seen))
    conn = HubSpotConnector(ConnectorConfig(provider_id="hubspot", company_id=1, credentials={
        "access_token": "pat"}, settings={}))

    invoices = _run(conn.fetch_invoices())
    assert {i.external_id: i.currency for i in invoices} == {"1": "INR", "4": "USD"}
    assert all(p in seen[0].split(",") for p in ("hs_is_closed_won", "hs_is_closed", "deal_currency_code"))

    summary = _run(conn.get_deal_pipeline_summary())
    assert summary["closed_won_count"] == 2 and summary["closed_won_value"] == 1200
    assert summary["open_deals_count"] == 1 and summary["open_deals_value"] == 300


def test_hubspot_falls_back_to_dealstage_when_flag_absent(monkeypatch):
    deals = [{"id": "9", "properties": {"dealname": "Old", "amount": "10", "dealstage": "closedwon"}}]
    _patch_httpx(monkeypatch, _hubspot_deals_handler(deals, []))
    conn = HubSpotConnector(ConnectorConfig(provider_id="hubspot", company_id=1, credentials={
        "access_token": "pat"}, settings={}))
    assert [i.external_id for i in _run(conn.fetch_invoices())] == ["9"]


# --- REST API ------------------------------------------------------------------

def _rest(settings, credentials=None):
    return RestAPIConnector(ConnectorConfig(provider_id="rest_api", company_id=1,
                                            credentials=credentials or {"api_key": "k"},
                                            settings={"endpoint_url": "https://api.example.com/data", **settings}))


def test_rest_test_connection_sends_auth_query_param(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=[])

    _patch_httpx(monkeypatch, handler)
    assert _run(_rest({"auth_param": "key"}).test_connection()) is True
    assert seen[0].url.params["key"] == "k"


@pytest.mark.parametrize("method,expected", [
    ("get", "GET"), ("POST", "POST"), ("DELETE", "GET"), ("put", "GET"), (None, "GET"),
])
def test_rest_method_restricted_to_get_post(monkeypatch, method, expected):
    seen = []

    def handler(request):
        seen.append(request.method)
        return httpx.Response(200, json=[])

    _patch_httpx(monkeypatch, handler)
    conn = _rest({"method": method})
    assert conn.method == expected
    _run(conn.test_connection())
    _run(conn.authenticate())
    _run(conn.fetch_data())
    assert seen == [expected] * 3


def test_rest_response_path_happy(monkeypatch):
    _patch_httpx(monkeypatch, lambda r: httpx.Response(200, json={"data": [{"items": [{"a": 1}, {"a": 2}]}]}))
    rows = _run(_rest({"response_path": "data.0.items"}).fetch_data())
    assert [r["payload"] for r in rows] == [{"a": 1}, {"a": 2}]


@pytest.mark.parametrize("body,path", [
    ({"data": []}, "data.0"),           # index out of range
    ({"data": "scalar"}, "data.items"),  # key on a non-container
    ({"data": [1, 2]}, "data.x"),        # non-numeric key on a list
])
def test_rest_bad_response_path_fails_cleanly(monkeypatch, body, path):
    _patch_httpx(monkeypatch, lambda r: httpx.Response(200, json=body))
    with pytest.raises(ValueError, match="response_path"):
        _run(_rest({"response_path": path}).fetch_data())
