"""Data Trust gate for calculator lead capture.

The visitor address, and any hash of it, stays out of PostHog and out of URLs.
Consent is on the committed row before Resend is called. POST /leads is rate
limited. The address never reaches an LLM prompt.
"""

from __future__ import annotations

import asyncio
import builtins
import json
import re
import sys
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from server.api.leads import (
    LEAD_RATE_LIMIT,
    LeadCreate,
    _email_markers,
    _emit_lead_captured,
    _runway_email_html,
    _send_runway_email,
    consent_is_recorded,
    create_lead,
    lead_client_key,
    lead_rate_limited,
)
from server.middleware.rate_limiter import RateLimiterMiddleware
from server.services import posthog as posthog_svc

REPO = Path(__file__).resolve().parents[2]
LEADS_PY = REPO / "server/api/leads.py"
OPT_IN = REPO / "client/src/components/marketing/CalculatorEmailOptIn.tsx"
EMAIL = "ada@example.com"


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key.lower(), super().get(key, default))


class _Request:
    def __init__(
        self,
        host="founderconsole.ai",
        client_host="203.0.113.40",
        forwarded_for=None,
        real_ip=None,
    ):
        headers = {"host": host}
        if forwarded_for:
            headers["x-forwarded-for"] = forwarded_for
        if real_ip:
            headers["x-real-ip"] = real_ip
        self.headers = _Headers({k.lower(): v for k, v in headers.items()})
        self.url = type("U", (), {"hostname": host.split(":")[0]})()
        self.client = type("C", (), {"host": client_host})()


class _FakeUrlOpen:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"status":"ok"}'


def _consented(**overrides) -> LeadCreate:
    payload = dict(
        email=EMAIL,
        source="runway-calculator",
        source_page="/tools/runway-calculator",
        consent=True,
        plan="runway-calculator",
    )
    payload.update(overrides)
    return LeadCreate(**payload)


def _db():
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None
    return db


def test_posthog_capture_omits_email_and_every_hash_of_it():
    markers = _email_markers(EMAIL)
    short = markers[2]
    data = _consented(
        source=EMAIL,
        plan=f"lead:{short}",
        notes=EMAIL,
        source_page=f"/tools/{markers[1]}",
        distinct_id=f"lead:{short}",
        runway_months="4",
    )
    captured = {}

    def fake_urlopen(req, timeout=5):
        captured["url"] = req.full_url
        captured["body"] = req.data.decode()
        return _FakeUrlOpen()

    with patch.object(posthog_svc.urllib.request, "urlopen", side_effect=fake_urlopen):
        _emit_lead_captured(data, created=True, host=EMAIL)

    assert "url" in captured
    blob = (captured["url"] + "\n" + captured["body"]).lower()
    for marker in markers:
        assert marker not in blob
    assert "?" not in captured["url"]
    body = json.loads(captured["body"])
    assert body["event"] == "lead_captured"
    assert body["distinct_id"].startswith("optin:")
    assert body["properties"]["distinct_id_source"] == "anonymous"
    assert body["properties"]["location"] == "website"
    assert body["properties"]["source_page"] == "other"
    assert markers[1] not in body["properties"]["source_page"]
    assert "plan" not in body["properties"]
    assert "runway_months" not in body["properties"]


def test_client_posts_the_address_in_the_body_not_the_url():
    src = OPT_IN.read_text()
    assert 'fetch("/api/leads"' in src
    assert 'method: "POST"' in src
    assert "?email" not in src
    assert "searchParams" not in src
    assert "URLSearchParams" not in src
    event = src.split('trackFunnel("lead_captured"', 1)[1].split(");", 1)[0]
    assert "email" not in event


def test_result_email_links_do_not_carry_the_address():
    html = _runway_email_html(
        _consented(runway_months="4", runway_date="March 2027", monthly_burn="$10")
    )
    assert EMAIL not in html
    hrefs = re.findall(r'href="([^"]*)"', html)
    assert hrefs
    for href in hrefs:
        assert EMAIL not in href
        assert "email=" not in href.lower()
        assert "?" not in href


def _email_module(send):
    module = types.ModuleType("server.email.service")
    module.send_email = send
    return module


def test_result_email_is_not_sent_until_consent_is_recorded():
    data = _consented(runway_months="4", runway_date="March 2027")
    called = []

    async def send_email(**kwargs):
        called.append(kwargs)

    with patch("server.api.leads.consent_is_recorded", return_value=False) as recorded, patch.dict(
        sys.modules, {"server.email.service": _email_module(send_email)}
    ):
        asyncio.run(_send_runway_email(data))
    recorded.assert_called_once_with(EMAIL)
    assert called == []


def test_result_email_sends_only_after_the_consent_check():
    data = _consented(runway_months="4", runway_date="March 2027", monthly_burn="$10")
    called = []

    async def send_email(**kwargs):
        called.append(kwargs)

    with patch("server.api.leads.consent_is_recorded", return_value=True) as recorded, patch.dict(
        sys.modules, {"server.email.service": _email_module(send_email)}
    ):
        asyncio.run(_send_runway_email(data))
    recorded.assert_called_once_with(EMAIL)
    assert len(called) == 1
    assert called[0]["to"] == EMAIL
    assert EMAIL not in called[0]["html_content"]


def test_consent_row_commits_before_the_email_task_is_queued(monkeypatch):
    monkeypatch.setenv("LEAD_RUNWAY_EMAIL_ENABLED", "true")
    order = []
    db = _db()
    db.commit.side_effect = lambda: order.append("commit")
    background = MagicMock()

    def add_task(fn, *args, **kwargs):
        order.append(fn.__name__)

    background.add_task.side_effect = add_task
    create_lead(
        _consented(runway_months="6", runway_date="2027-04-01"),
        background,
        _Request(client_host="203.0.113.41"),
        db,
    )
    assert "commit" in order
    assert order.index("commit") < order.index("_send_runway_email")


def test_consent_is_recorded_requires_a_committed_flag_and_timestamp():
    lead = MagicMock(consent=True, consent_at=datetime.utcnow())
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = lead
    session = MagicMock(return_value=db)

    with patch("server.core.db.SessionLocal", session):
        assert consent_is_recorded(EMAIL) is True

    lead.consent = False
    with patch("server.core.db.SessionLocal", session):
        assert consent_is_recorded(EMAIL) is False

    lead.consent = True
    lead.consent_at = None
    with patch("server.core.db.SessionLocal", session):
        assert consent_is_recorded(EMAIL) is False

    db.query.return_value.filter.return_value.one_or_none.return_value = None
    with patch("server.core.db.SessionLocal", session):
        assert consent_is_recorded(EMAIL) is False

    db.query.side_effect = RuntimeError("down")
    with patch("server.core.db.SessionLocal", session):
        assert consent_is_recorded(EMAIL) is False


def test_rate_limit_window_blocks_without_counting_the_rejected_call():
    store: dict[str, list[float]] = {}
    key = "203.0.113.42"
    assert lead_rate_limited(key, now=0, limit=2, window=10, store=store) is False
    assert lead_rate_limited(key, now=1, limit=2, window=10, store=store) is False
    assert lead_rate_limited(key, now=2, limit=2, window=10, store=store) is True
    assert len(store[key]) == 2
    assert lead_rate_limited(key, now=11, limit=2, window=10, store=store) is False


def test_rate_limit_key_is_the_client_not_the_email():
    # One forwarded address plus the socket is shorter than two trusted hops
    # plus a client, so the key is the socket, never the address.
    emailed = _Request(client_host="203.0.113.43", forwarded_for=f"10.1.1.1, {EMAIL}")
    assert lead_client_key(emailed) == "203.0.113.43"
    assert EMAIL not in lead_client_key(emailed)
    only_email = _Request(client_host="203.0.113.44", forwarded_for=EMAIL)
    assert lead_client_key(only_email) == "203.0.113.44"
    assert "@" not in lead_client_key(only_email)
    # spoof, real client, shared edge, Express socket. Not the last hop.
    proxied = _Request(client_host="127.0.0.1", forwarded_for="1.2.3.4, 203.0.113.45, 100.64.0.8")
    assert lead_client_key(proxied) == "203.0.113.45"


def test_create_lead_returns_429_before_saving_or_queueing_email():
    host = "203.0.113.60"
    for n in range(LEAD_RATE_LIMIT):
        db = _db()
        create_lead(
            _consented(email=f"visitor{n}@example.com"),
            MagicMock(),
            _Request(client_host=host),
            db,
        )
        db.commit.assert_called_once()

    db = _db()
    background = MagicMock()
    with pytest.raises(HTTPException) as exc:
        create_lead(_consented(), background, _Request(client_host=host), db)
    assert exc.value.status_code == 429
    assert exc.value.detail == "Too many requests"
    db.query.assert_not_called()
    db.commit.assert_not_called()
    background.add_task.assert_not_called()


def test_middleware_caps_post_leads_and_drops_email_keys():
    middleware = RateLimiterMiddleware(MagicMock())
    middleware_src = (REPO / "server/middleware/rate_limiter.py").read_text()
    assert 'os.getenv("RATE_LIMIT_LEADS"' not in middleware_src
    assert "LEAD_RATE_LIMIT = 8" in middleware_src

    def request(path, method="POST", forwarded_for=None, client_host="10.9.9.9"):
        headers = {}
        if forwarded_for:
            headers["X-Forwarded-For"] = forwarded_for
        return type(
            "R",
            (),
            {
                "url": type("U", (), {"path": path})(),
                "method": method,
                "headers": headers,
                "client": type("C", (), {"host": client_host})(),
            },
        )()

    assert middleware._get_category(request("/leads")) == ("leads", 8)
    assert middleware._get_category(request("/leads/")) == ("leads", 8)
    assert middleware._get_category(request("/api/leads")) == ("leads", 8)
    api_limit = middleware.rate_limit_api
    assert middleware._get_category(request("/leads", method="GET")) == ("api", api_limit)
    # The address is dropped. One remaining hop is not enough to skip two
    # trusted proxies, so the socket is the key and the address is not.
    assert "@" not in middleware._get_identifier(
        request("/leads", forwarded_for=f"10.0.0.8, {EMAIL}")
    )
    assert middleware._get_identifier(
        request("/leads", forwarded_for=f"10.0.0.8, {EMAIL}", client_host="10.9.9.9")
    ) == "10.9.9.9"
    assert middleware._get_identifier(
        request("/leads", forwarded_for=EMAIL, client_host="10.2.2.2")
    ) == "10.2.2.2"


def test_lead_capture_source_has_no_llm_entry_point():
    src = LEADS_PY.read_text()
    for token in (
        "openai",
        "anthropic",
        "get_llm_router",
        "ChatRequest",
        "server.lib.llm",
        "server.api.llm",
        "copilot",
    ):
        assert token not in src


def test_send_and_emit_do_not_import_or_call_an_llm():
    data = _consented(runway_months="4", runway_date="May 2027")
    seen: list[str] = []
    real_import = builtins.__import__

    def tracking_import(name, globals=None, locals=None, fromlist=(), level=0):
        seen.append(name)
        return real_import(name, globals, locals, fromlist, level)

    async def send_email(**kwargs):
        return None

    before = {name for name in sys.modules if "llm" in name.lower() or name in {"openai", "anthropic"}}
    with patch("server.api.leads.consent_is_recorded", return_value=True), patch.dict(
        sys.modules, {"server.email.service": _email_module(send_email)}
    ), patch("server.api.leads.posthog_capture"), patch("builtins.__import__", tracking_import):
        asyncio.run(_send_runway_email(data))
        _emit_lead_captured(data, created=True, host="founderconsole.ai")
    after = {name for name in sys.modules if "llm" in name.lower() or name in {"openai", "anthropic"}}
    assert after == before
    assert not any(
        name == "openai" or name == "anthropic" or "llm" in name.lower() for name in seen
    )


def _proxied(spoof: str, client: str, real_ip: str | None = None, edge: str = "100.64.0.8"):
    """Railway edge plus Express: spoof, client, shared edge, loopback socket."""
    return _Request(
        client_host="127.0.0.1",
        forwarded_for=f"{spoof}, {client}, {edge}",
        real_ip=real_ip,
    )


def test_two_clients_get_separate_buckets_and_a_spoof_does_not_bypass():
    store: dict[str, list[float]] = {}
    client_a = lead_client_key(_proxied("198.51.100.1", "203.0.113.70", real_ip="203.0.113.70"))
    client_a_spoofed = lead_client_key(
        _proxied("203.0.113.250", "198.51.100.9", real_ip="203.0.113.70")
    )
    client_b = lead_client_key(_proxied("198.51.100.1", "203.0.113.71", real_ip="203.0.113.71"))
    assert client_a == client_a_spoofed == "203.0.113.70"
    assert client_b == "203.0.113.71"
    assert client_a not in {"100.64.0.8", "127.0.0.1", "198.51.100.1"}

    for n in range(LEAD_RATE_LIMIT):
        assert lead_rate_limited(
            client_a, now=n, limit=LEAD_RATE_LIMIT, window=60, store=store
        ) is False
    assert lead_rate_limited(
        client_a_spoofed, now=LEAD_RATE_LIMIT, limit=LEAD_RATE_LIMIT, window=60, store=store
    ) is True
    assert lead_rate_limited(
        client_b, now=LEAD_RATE_LIMIT, limit=LEAD_RATE_LIMIT, window=60, store=store
    ) is False

    # No X-Real-IP. The client is the address in front of the two trusted hops.
    # Changing the leftmost spoof does not open a bucket, and the shared edge does not either.
    no_real_a = lead_client_key(_proxied("1.1.1.1", "203.0.113.80"))
    no_real_a_spoof = lead_client_key(_proxied("9.9.9.9", "203.0.113.80"))
    no_real_b = lead_client_key(_proxied("1.1.1.1", "203.0.113.81"))
    assert no_real_a == no_real_a_spoof == "203.0.113.80"
    assert no_real_b == "203.0.113.81"
    assert no_real_a != "100.64.0.8"
    assert lead_rate_limited(no_real_a, now=0, limit=1, window=60, store=store) is False
    assert lead_rate_limited(no_real_a_spoof, now=1, limit=1, window=60, store=store) is True
    assert lead_rate_limited(no_real_b, now=1, limit=1, window=60, store=store) is False


def test_middleware_keys_on_the_client_not_the_shared_edge():
    middleware = RateLimiterMiddleware(MagicMock())

    def request(forwarded_for, real_ip=None, client_host="127.0.0.1"):
        headers = {"X-Forwarded-For": forwarded_for}
        if real_ip:
            headers["X-Real-IP"] = real_ip
        return type(
            "R",
            (),
            {
                "url": type("U", (), {"path": "/leads"})(),
                "method": "POST",
                "headers": headers,
                "client": type("C", (), {"host": client_host})(),
            },
        )()

    a = middleware._get_identifier(
        request("1.1.1.1, 203.0.113.70, 100.64.0.8", real_ip="203.0.113.70")
    )
    a_spoof = middleware._get_identifier(
        request("9.9.9.9, 198.51.100.1, 100.64.0.8", real_ip="203.0.113.70")
    )
    b = middleware._get_identifier(
        request("1.1.1.1, 203.0.113.71, 100.64.0.8", real_ip="203.0.113.71")
    )
    assert a == a_spoof == "203.0.113.70"
    assert b == "203.0.113.71"
    forwarded = middleware._get_identifier(request("8.8.8.8, 203.0.113.80, 100.64.0.8"))
    forwarded_spoof = middleware._get_identifier(request("1.2.3.4, 203.0.113.80, 100.64.0.8"))
    assert forwarded == forwarded_spoof == "203.0.113.80"
    assert forwarded != "100.64.0.8"
    assert forwarded != "8.8.8.8"


def test_result_markup_is_rejected_and_the_email_escapes_it():
    background = MagicMock()
    db = _db()
    with pytest.raises(HTTPException) as exc:
        create_lead(
            _consented(
                runway_months="<b>",
                runway_date="2027-03-15",
                monthly_burn="10",
            ),
            background,
            _Request(client_host="203.0.113.90"),
            db,
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid result field"
    db.commit.assert_not_called()
    background.add_task.assert_not_called()

    rejected = [
        dict(runway_months="4", runway_date="March 2027", monthly_burn="10"),
        dict(runway_months="4", runway_date="2027-03-15", monthly_burn="$10"),
        dict(runway_months="36+", runway_date="2027-03-15", monthly_burn="10"),
        dict(runway_months="1e6", runway_date="2027-03-15", monthly_burn="10"),
        dict(runway_months="4", runway_date="2027-13-40", monthly_burn="10"),
    ]
    for overrides in rejected:
        db = _db()
        with pytest.raises(HTTPException) as exc:
            create_lead(
                _consented(**overrides),
                MagicMock(),
                _Request(client_host="203.0.113.91"),
                db,
            )
        assert exc.value.status_code == 400
        db.add.assert_not_called()

    html = _runway_email_html(
        _consented(
            runway_months="<b>",
            runway_date="2027-03-15",
            monthly_burn="1<2",
        )
    )
    assert "<b>" not in html
    assert "&lt;b&gt;" in html
    assert "1&lt;2" in html

    accepted = create_lead(
        _consented(runway_months="4.5", runway_date="2027-03-15T00:00:00Z", monthly_burn="-1200"),
        MagicMock(),
        _Request(client_host="203.0.113.92"),
        _db(),
    )
    assert accepted == {"status": "ok"}
