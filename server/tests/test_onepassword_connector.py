"""1Password Events API connector. No network: httpx MockTransport."""

import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

import server.connectors as connectors_pkg
from server.connectors.base import ConnectorConfig, ProviderCategory
from server.connectors.onepassword import (
    MAX_PAGES,
    OnePasswordConnector,
    base_url_for_region,
    resolve_region,
    summarize_signins,
)
from server.connectors.registry import ConnectorRegistry


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def mock_http(monkeypatch):
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


def _conn(**creds):
    creds.setdefault("bearer_token", "tok")
    return OnePasswordConnector(
        ConnectorConfig(provider_id="onepassword", company_id=1, credentials=creds)
    )


INTROSPECT_OK = {
    "uuid": "INTEG",
    "issued_at": "2026-11-01T00:00:00Z",
    "features": ["auditevents", "itemusages", "signinattempts"],
    "account_uuid": "ACCT",
}


def _ts(days_ago=1):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%S.123456789Z")


def _attempt(user, category="success", days_ago=1):
    return {
        "uuid": f"e-{user}-{category}-{days_ago}",
        "session_uuid": "s",
        "timestamp": _ts(days_ago),
        "category": category,
        "type": "credentials_ok" if category == "success" else "password_secret_bad",
        "country": "US",
        "target_user": {"uuid": user, "name": user.title(), "email": f"{user}@acme.test"},
        "client": {"app_name": "1Password Browser Extension"},
        "location": {"country": "US", "city": "Austin"},
    }


SIGNINS = [
    _attempt("alice"),
    _attempt("alice", days_ago=3),
    _attempt("bob"),
    _attempt("carol", "credentials_failed"),
    _attempt("bob", "mfa_failed"),
    _attempt("dave", "firewall_failed"),
    _attempt("dave", "credentials_failed"),
    _attempt("erin", "firewall_reported_success"),
]


def _handler(pages, introspect=INTROSPECT_OK, bodies=None):
    """pages: list of item lists; each page links to the next with a cursor."""
    def handler(r):
        if r.url.path == "/api/v2/auth/introspect":
            return httpx.Response(200, json=introspect)
        assert r.url.path == "/api/v2/signinattempts" and r.method == "POST"
        body = json.loads(r.content)
        if bodies is not None:
            bodies.append(body)
        index = 0 if "start_time" in body else int(body["cursor"].split("-")[1])
        has_more = index + 1 < len(pages)
        return httpx.Response(200, json={
            "cursor": f"c-{index + 1}", "has_more": has_more, "items": pages[index],
        })
    return handler


# --- Auth --------------------------------------------------------------------

def test_introspect_success_sends_bearer(mock_http):
    seen = mock_http(_handler([[]]))
    conn = _conn(bearer_token="Bearer abc123")
    assert _run(conn.authenticate()) is True
    assert seen[0].url.host == "events.1password.com"
    assert seen[0].url.path == "/api/v2/auth/introspect"
    assert seen[0].headers["Authorization"] == "Bearer abc123"
    assert conn.account_uuid == "ACCT"


def test_introspect_without_signinattempts_feature_fails_clearly(mock_http):
    mock_http(_handler([[]], introspect={**INTROSPECT_OK, "features": ["auditevents", "itemusages"]}))
    conn = _conn()
    assert _run(conn.authenticate()) is False
    assert "sign-in attempts" in conn.auth_error
    assert "auditevents, itemusages" in conn.auth_error


def test_401_gives_readable_error_and_sync_fails(mock_http):
    mock_http(lambda r: httpx.Response(401, json={"status": 401, "message": "Unauthorized"}))
    conn = _conn(region="eu")
    assert _run(conn.authenticate()) is False
    assert "401" in conn.auth_error and "eu" in conn.auth_error
    result = _run(conn.sync_all())
    assert result.success is False
    assert result.errors == [conn.auth_error]


def test_429_during_pagination_is_reported(mock_http):
    def handler(r):
        if r.url.path == "/api/v2/auth/introspect":
            return httpx.Response(200, json=INTROSPECT_OK)
        return httpx.Response(429, headers={"Retry-After": "30"})
    mock_http(handler)
    result = _run(_conn().sync_all())
    assert result.success is False
    assert "rate limit" in result.errors[0] and "30 seconds" in result.errors[0]


def test_missing_token_and_bad_inputs_fail_without_network(mock_http):
    seen = mock_http(lambda r: httpx.Response(500))
    conn = _conn(bearer_token="")
    assert _run(conn.authenticate()) is False and "bearer token" in conn.auth_error
    conn = _conn(region="mars")
    assert _run(conn.authenticate()) is False and "region" in conn.auth_error
    conn = _conn(seat_price_monthly="seven")
    assert _run(conn.authenticate()) is False and "Seat price" in conn.auth_error
    conn = _conn(seats="2.5")
    assert _run(conn.authenticate()) is False and "whole number" in conn.auth_error
    assert seen == []


# --- Region ------------------------------------------------------------------

@pytest.mark.parametrize("region,host", [
    ("us", "events.1password.com"),
    ("", "events.1password.com"),
    ("ent", "events.ent.1password.com"),
    ("CA", "events.1password.ca"),
    ("eu", "events.1password.eu"),
    ("1password.eu", "events.1password.eu"),
    ("https://events.ent.1password.com/", "events.ent.1password.com"),
])
def test_region_to_base_url(mock_http, region, host):
    seen = mock_http(_handler([[]]))
    assert _run(_conn(region=region).authenticate()) is True
    assert seen[0].url.host == host
    assert base_url_for_region(region) == f"https://{host}"


def test_unknown_region_is_rejected():
    assert resolve_region("evil.example.com") is None
    with pytest.raises(ValueError):
        base_url_for_region("internal")


# --- Pagination and counts -----------------------------------------------------

def test_pagination_follows_cursor(mock_http):
    bodies = []
    mock_http(_handler([SIGNINS[:3], SIGNINS[3:6], SIGNINS[6:]], bodies=bodies))
    conn = _conn()
    result = _run(conn.sync_all())
    assert result.success is True
    assert bodies[0]["limit"] == 1000
    start = datetime.fromisoformat(bodies[0]["start_time"].replace("Z", "+00:00"))
    assert abs((datetime.now(timezone.utc) - start) - timedelta(days=30)) < timedelta(minutes=5)
    assert bodies[1:] == [{"cursor": "c-1"}, {"cursor": "c-2"}]
    assert result.records_synced == len(SIGNINS)
    assert conn.truncated is False


def test_pagination_is_capped(mock_http):
    calls = []

    def handler(r):
        if r.url.path == "/api/v2/auth/introspect":
            return httpx.Response(200, json=INTROSPECT_OK)
        calls.append(r)
        return httpx.Response(200, json={"cursor": "again", "has_more": True, "items": [_attempt("x")]})

    mock_http(handler)
    conn = _conn()
    result = _run(conn.sync_all())
    assert len(calls) == MAX_PAGES
    assert conn.truncated is True
    assert result.success is True and result.warnings


def test_active_user_and_failed_counts(mock_http):
    mock_http(_handler([SIGNINS]))
    result = _run(_conn().sync_all())
    security = result.metadata["financials"]["security"]
    assert security["active_users"] == 3  # alice, bob, erin
    assert security["total_signins"] == 8
    assert security["successful_signins"] == 4
    assert security["failed_signins"] == 4
    assert security["failed_by_category"] == {
        "credentials_failed": 2, "firewall_failed": 1, "mfa_failed": 1,
    }


def test_summary_ignores_attempts_before_window():
    since = datetime.now(timezone.utc) - timedelta(days=30)
    summary = summarize_signins([_attempt("old", days_ago=45), _attempt("new")], since=since)
    assert summary["active_users"] == 1 and summary["total_signins"] == 1


# --- Seat cost -------------------------------------------------------------------

def test_seat_cost_ledger_entry_uses_seats(mock_http):
    mock_http(_handler([SIGNINS]))
    conn = _conn(seat_price_monthly="7.99", seats="10")
    result = _run(conn.sync_all())
    assert result.success is True
    ledger = _run(conn.fetch_ledger())  # cached sign-ins, no extra requests needed
    assert len(ledger) == 1
    entry = ledger[0]
    assert entry.account_name == "1Password" and entry.category == "Software"
    assert entry.debit == pytest.approx(79.9)
    assert entry.metadata["seat_utilization"] == pytest.approx(0.3)
    assert entry.metadata["unused_seats"] == 7
    financials = result.metadata["financials"]
    assert financials["expense_breakdown"] == {"Software": pytest.approx(79.9)}
    assert financials["security"]["seat_utilization"] == pytest.approx(0.3)
    # One line of opex, not the month's total: no company-wide figure.
    assert "opex" not in financials


def test_seat_cost_falls_back_to_active_users(mock_http):
    mock_http(_handler([SIGNINS]))
    conn = _conn(seat_price_monthly="$7.99")
    _run(conn.sync_all())
    entry = _run(conn.fetch_ledger())[0]
    assert entry.debit == pytest.approx(3 * 7.99)
    assert entry.metadata["billing_basis"] == "active_users"
    assert entry.metadata["seat_utilization"] is None


def test_no_seat_price_means_no_expense_entry(mock_http):
    mock_http(_handler([SIGNINS]))
    conn = _conn(seats="10")
    result = _run(conn.sync_all())
    assert result.success is True
    assert _run(conn.fetch_ledger()) == []
    financials = result.metadata["financials"]
    assert "expense_breakdown" not in financials
    assert financials["security"]["seat_utilization"] == pytest.approx(0.3)


# --- Registry ----------------------------------------------------------------------

def test_registered_in_security_category():
    connectors_pkg.load_all_connectors()
    cls = ConnectorRegistry.get_connector_class("onepassword")
    assert cls is OnePasswordConnector
    assert cls.PROVIDER_CATEGORY is ProviderCategory.SECURITY
    listed = ConnectorRegistry.list_connectors(category=ProviderCategory.SECURITY)
    assert [p["id"] for p in listed] == ["onepassword"]
