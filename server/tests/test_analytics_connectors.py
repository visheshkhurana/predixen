"""Mixpanel, Amplitude, GA4 and Google Sheets request shapes vs the official
docs. No network: httpx MockTransport."""

import asyncio
import json
import urllib.parse
from datetime import datetime

import httpx
import pytest

from server.connectors.amplitude import AmplitudeConnector
from server.connectors.base import ConnectorConfig
from server.connectors.google_analytics import GoogleAnalyticsConnector
from server.connectors.google_sheets import GoogleSheetsConnector, a1_range
from server.connectors.mixpanel import MixpanelConnector


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def mock_http(monkeypatch):
    """Route every httpx.AsyncClient through a handler; returns the request log."""
    seen = []
    state = {}
    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(lambda r: (seen.append(r), state["handler"](r))[1])
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)

    def install(handler):
        state["handler"] = handler
        return seen

    return install


def _cfg(provider, creds, settings=None):
    return ConnectorConfig(provider_id=provider, company_id=1, credentials=creds, settings=settings or {})


# --- Mixpanel ----------------------------------------------------------------

def test_mixpanel_auth_probe_needs_no_saved_report(mock_http):
    def handler(r):
        assert r.url.path == "/api/query/events/names"
        assert r.url.params["type"] == "general" and r.url.params["project_id"] == "42"
        assert "bookmark_id" not in r.url.params
        return httpx.Response(200, json=["Signed Up"])

    seen = mock_http(handler)
    conn = MixpanelConnector(_cfg("mixpanel", {"project_id": "42", "api_secret": "s"}))
    assert _run(conn.authenticate()) is True
    assert seen[0].url.host == "mixpanel.com"
    assert seen[0].headers["Authorization"].startswith("Basic ")


@pytest.mark.parametrize("region,host", [("us", "mixpanel.com"), ("eu", "eu.mixpanel.com"),
                                         ("in", "in.mixpanel.com"), ("EU", "eu.mixpanel.com")])
def test_mixpanel_region_hosts(mock_http, region, host):
    seen = mock_http(lambda r: httpx.Response(200, json=[]))
    conn = MixpanelConnector(_cfg("mixpanel", {"project_id": "1", "service_account_user": "u",
                                               "service_account_secret": "p", "region": region}))
    assert _run(conn.authenticate()) is True
    assert seen[0].url.host == host


def test_mixpanel_insights_series_iso_timestamps_parse(mock_http):
    def handler(r):
        if r.url.path.endswith("/events/names"):
            return httpx.Response(200, json=["x"])
        assert r.url.path == "/api/query/insights"
        assert r.url.params["bookmark_id"] == "777"
        return httpx.Response(200, json={"series": {"Signed Up": {
            "2020-08-31T00:00:00-07:00": 10, "2020-09-01T00:00:00-07:00": 12, "$overall": 22}}})

    mock_http(handler)
    conn = MixpanelConnector(_cfg("mixpanel", {"project_id": "1", "api_secret": "s", "bookmark_id": "777"}))
    entries = _run(conn.fetch_ledger())
    assert [e.date.strftime("%Y-%m-%d") for e in entries] == ["2020-08-31", "2020-09-01"]
    assert [e.metadata["event_count"] for e in entries] == [10.0, 12.0]
    assert entries[0].external_id == "mixpanel_1_Signed Up_2020-08-31"


def test_mixpanel_without_bookmark_uses_event_counts(mock_http):
    def handler(r):
        if r.url.path.endswith("/events/names"):
            return httpx.Response(200, json=["Signed Up", "Paid"])
        assert r.url.path == "/api/query/events"
        assert json.loads(r.url.params["event"]) == ["Signed Up", "Paid"]
        return httpx.Response(200, json={"data": {"series": ["2024-01-01"], "values": {
            "Signed Up": {"2024-01-01": 5}, "Paid": {"2024-01-01": 2}}}})

    seen = mock_http(handler)
    conn = MixpanelConnector(_cfg("mixpanel", {"project_id": "1", "api_secret": "s"}))
    entries = _run(conn.fetch_ledger())
    assert sorted(e.metadata["event_count"] for e in entries) == [2.0, 5.0]
    assert not any(r.url.path.endswith("/insights") for r in seen)


def test_mixpanel_skips_funnels_without_id(mock_http):
    seen = mock_http(lambda r: httpx.Response(200, json={}))
    conn = MixpanelConnector(_cfg("mixpanel", {"project_id": "1", "api_secret": "s"}))
    assert _run(conn.get_funnels()) == {}
    assert seen == []

    conn = MixpanelConnector(_cfg("mixpanel", {"project_id": "1", "api_secret": "s", "funnel_id": "9"}))
    conn._authenticated = True
    _run(conn.get_funnels())
    assert seen[-1].url.path == "/api/query/funnels" and seen[-1].url.params["funnel_id"] == "9"


# --- Amplitude ---------------------------------------------------------------

def test_amplitude_auth_sends_active_event(mock_http):
    def handler(r):
        assert r.url.path == "/api/2/events/segmentation"
        assert json.loads(r.url.params["e"]) == {"event_type": "_active"}
        return httpx.Response(200, json={"data": {}})

    seen = mock_http(handler)
    conn = AmplitudeConnector(_cfg("amplitude", {"api_key": "k", "secret_key": "s"}))
    assert _run(conn.authenticate()) is True
    assert seen[0].url.host == "amplitude.com"


def test_amplitude_eu_region_and_cohorts_v3(mock_http):
    def handler(r):
        if r.url.path == "/api/3/cohorts":
            return httpx.Response(200, json={"cohorts": [{"id": "c1"}, {"id": "c2"}]})
        return httpx.Response(200, json={"data": {}})

    seen = mock_http(handler)
    conn = AmplitudeConnector(_cfg("amplitude", {"api_key": "k", "secret_key": "s", "region": "eu"}))
    assert len(_run(conn.get_cohorts())) == 2
    assert {r.url.host for r in seen} == {"analytics.eu.amplitude.com"}


def test_amplitude_legacy_event_name_is_mapped(mock_http):
    seen = mock_http(lambda r: httpx.Response(200, json={"data": {}}))
    conn = AmplitudeConnector(_cfg("amplitude", {"api_key": "k", "secret_key": "s"}))
    conn._authenticated = True
    _run(conn.get_event_segmentation(event_type="Any Active Event"))
    assert json.loads(seen[-1].url.params["e"]) == {"event_type": "_active"}


def test_amplitude_retention_parses_documented_shape(mock_http):
    def handler(r):
        if r.url.path == "/api/2/retention":
            assert json.loads(r.url.params["se"]) == {"event_type": "_active"}
            assert json.loads(r.url.params["re"]) == {"event_type": "_active"}
            return httpx.Response(200, json={"data": {"series": [{
                "dates": ["Aug 15", "Aug 14"],
                "values": {
                    "Aug 14": [{"count": 100, "outof": 100, "incomplete": False},
                               {"count": 90, "outof": 100, "incomplete": False},
                               {"count": 40, "outof": 100, "incomplete": False}],
                    "Aug 15": [{"count": 50, "outof": 50, "incomplete": False},
                               {"count": 45, "outof": 50, "incomplete": False},
                               {"count": 5, "outof": 50, "incomplete": True}],
                },
                "combined": [],
            }], "seriesMeta": [{"segmentIndex": 0}]}})
        return httpx.Response(200, json={"data": {"series": [[3, 4]], "xValues": ["2025-08-14", "2025-08-15"]}})

    mock_http(handler)
    conn = AmplitudeConnector(_cfg("amplitude", {"api_key": "k", "secret_key": "s"}))
    conn._authenticated = True
    entries = _run(conn.fetch_ledger(datetime(2025, 7, 20), datetime(2025, 8, 20)))
    dau = [e for e in entries if e.metadata["metric_type"] == "dau"]
    ret = [e for e in entries if e.metadata["metric_type"] == "retention"]
    assert [e.credit for e in dau] == [3.0, 4.0]
    assert len(ret) == 1  # Aug 15 Day 1 is incomplete
    assert ret[0].date == datetime(2025, 8, 14) and ret[0].credit == pytest.approx(40.0)


# --- Google Analytics --------------------------------------------------------

def _ga_report():
    return {"dimensionHeaders": [{"name": "date"}],
            "metricHeaders": [{"name": "sessions"}, {"name": "totalUsers"},
                              {"name": "keyEvents"}, {"name": "totalRevenue"}],
            "rows": [{"dimensionValues": [{"value": "20250101"}],
                      "metricValues": [{"value": "10"}, {"value": "8"}, {"value": "3"}, {"value": "99.5"}]}]}


def test_ga4_requests_key_events_not_conversions(mock_http):
    bodies = []

    def handler(r):
        body = json.loads(r.content)
        bodies.append(body)
        return httpx.Response(200, json=_ga_report())

    mock_http(handler)
    conn = GoogleAnalyticsConnector(_cfg("google_analytics", {"property_id": "123", "access_token": "a"}))
    entries = _run(conn.fetch_ledger())
    names = {m["name"] for b in bodies for m in b["metrics"]}
    assert "keyEvents" in names and "conversions" not in names
    assert entries[0].metadata["conversions"] == 3.0 and entries[0].credit == 99.5
    _run(conn.get_conversion_metrics())
    _run(conn.get_traffic_sources())
    assert "conversions" not in {m["name"] for b in bodies for m in b["metrics"]}


def test_ga4_refreshes_on_401_and_reports_rotation(mock_http):
    def handler(r):
        if r.url.host == "oauth2.googleapis.com":
            form = urllib.parse.parse_qs(r.content.decode())
            assert form["grant_type"] == ["refresh_token"] and form["refresh_token"] == ["r"]
            return httpx.Response(200, json={"access_token": "fresh", "expires_in": 3599})
        if r.headers["Authorization"] == "Bearer stale":
            return httpx.Response(401, json={"error": {"code": 401}})
        assert r.headers["Authorization"] == "Bearer fresh"
        return httpx.Response(200, json=_ga_report())

    seen = mock_http(handler)
    conn = GoogleAnalyticsConnector(_cfg("google_analytics", {
        "property_id": "123", "access_token": "stale", "refresh_token": "r",
        "client_id": "cid", "client_secret": "cs"}))
    assert _run(conn.authenticate()) is True
    assert conn._access_token == "fresh"
    assert conn.rotated_credentials()["access_token"] == "fresh"
    assert [r.url.host for r in seen].count("oauth2.googleapis.com") == 1


def test_ga4_refreshes_up_front_when_no_access_token(mock_http):
    def handler(r):
        if r.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "fresh"})
        assert r.headers["Authorization"] == "Bearer fresh"
        return httpx.Response(200, json=_ga_report())

    mock_http(handler)
    conn = GoogleAnalyticsConnector(_cfg("google_analytics", {
        "property_id": "123", "refresh_token": "r", "client_id": "cid", "client_secret": "cs"}))
    assert _run(conn.authenticate()) is True


def test_ga4_401_without_refresh_creds_fails(mock_http):
    seen = mock_http(lambda r: httpx.Response(401))
    conn = GoogleAnalyticsConnector(_cfg("google_analytics", {"property_id": "123", "access_token": "a"}))
    assert _run(conn.authenticate()) is False
    assert len(seen) == 1


# --- Google Sheets -----------------------------------------------------------

def test_a1_range_quotes_and_encodes():
    assert a1_range("Sheet1") == urllib.parse.quote("'Sheet1'!A:ZZ", safe="")
    assert a1_range("Q1 Budget") == "%27Q1%20Budget%27%21A%3AZZ"
    assert urllib.parse.unquote(a1_range("Jon's Data")) == "'Jon''s Data'!A:ZZ"
    assert "/" not in a1_range("a/b") and "#" not in a1_range("a#b")


def test_sheets_fetch_quotes_range_and_refreshes_on_401(mock_http):
    def handler(r):
        if r.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "fresh", "refresh_token": "r2"})
        assert r.url.raw_path.decode().endswith("/values/%27Q1%20Budget%27%21A%3AZZ")
        if r.headers["Authorization"] == "Bearer stale":
            return httpx.Response(401)
        return httpx.Response(200, json={"values": [["Month", "Revenue"], ["Jan", "10"]]})

    seen = mock_http(handler)
    conn = GoogleSheetsConnector(_cfg(
        "google_sheets",
        {"access_token": "stale", "refresh_token": "r", "client_id": "cid", "client_secret": "cs"},
        {"spreadsheet_id": "abc", "sheet_name": "Q1 Budget"}))
    data = _run(conn.fetch_data())
    assert data[0]["payload"] == {"month": "Jan", "revenue": "10"}
    rotated = conn.rotated_credentials()
    assert rotated["access_token"] == "fresh" and rotated["refresh_token"] == "r2"
    assert len(seen) == 3


def test_sheets_auth_refreshes_on_401(mock_http):
    def handler(r):
        if r.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "fresh"})
        return httpx.Response(200 if r.headers["Authorization"] == "Bearer fresh" else 401, json={})

    mock_http(handler)
    conn = GoogleSheetsConnector(_cfg(
        "google_sheets",
        {"access_token": "stale", "refresh_token": "r", "client_id": "cid", "client_secret": "cs"},
        {"spreadsheet_id": "abc"}))
    assert _run(conn.authenticate()) is True


def test_sheets_401_without_client_creds_does_not_refresh(mock_http):
    seen = mock_http(lambda r: httpx.Response(401))
    conn = GoogleSheetsConnector(_cfg("google_sheets", {"access_token": "a", "refresh_token": "r"},
                                      {"spreadsheet_id": "abc"}))
    assert _run(conn.authenticate()) is False
    assert len(seen) == 1
