"""$internal_or_test_user is decided on the server. The address is not sent.

PostHog can exclude internal and test people with that boolean. Smoke
accounts, @example.com, the demo account, and the existing platform-admin
flag qualify. A normal founder sends nothing.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from server.core.config import settings
from server.services import posthog as posthog_svc
from server.services.activation import emit_signup_completed
from server.services.posthog import sync_internal_or_test_person


class _FakeUrlOpen:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture(autouse=True)
def _no_configured_admin_email(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_MASTER_EMAIL", "")
    monkeypatch.delenv("POSTHOG_KEY", raising=False)
    monkeypatch.delenv("POSTHOG_PROJECT_API_KEY", raising=False)
    posthog_svc._logged_choice = None


@contextmanager
def _capture_posts():
    sent: list[tuple[str, str]] = []

    def fake_urlopen(req, timeout=5):
        sent.append((req.full_url, req.data.decode()))
        return _FakeUrlOpen()

    with patch.object(posthog_svc.urllib.request, "urlopen", side_effect=fake_urlopen):
        yield sent


def _bodies(sent: list[tuple[str, str]]) -> list[dict]:
    return [json.loads(raw) for _url, raw in sent]


def _blob(sent: list[tuple[str, str]]) -> str:
    return "\n".join(f"{url}\n{raw}" for url, raw in sent).lower()


def _assert_no_address(sent: list[tuple[str, str]], email: str) -> None:
    """The address, its domain, and its local part are absent from every payload."""
    blob = _blob(sent)
    assert "@" not in blob
    normalized = email.strip().lower()
    local, _, domain = normalized.rpartition("@")
    assert normalized not in blob
    assert domain not in blob
    # "founder" is a substring of the static lib name founderconsole-server.
    static = "founderconsole-server"
    if len(local) >= 3 and local not in static:
        assert local not in blob


def _flag_events(sent: list[tuple[str, str]]) -> list[dict]:
    return [
        body
        for body in _bodies(sent)
        if body.get("properties", {}).get("$set", {}).get("$internal_or_test_user") is True
    ]


def _assert_flagged(sent: list[tuple[str, str]], email: str, distinct_id: str) -> None:
    flagged = _flag_events(sent)
    assert len(flagged) == 1
    body = flagged[0]
    assert body["event"] == "$set"
    assert body["distinct_id"] == distinct_id
    assert body["properties"]["$process_person_profile"] is True
    assert body["properties"]["$set"] == {"$internal_or_test_user": True}
    assert set(body["properties"]) == {"$lib", "$process_person_profile", "$set"}
    _assert_no_address(sent, email)


def _login(email: str):
    from server.api.auth import LoginRequest, login

    user = SimpleNamespace(
        id=9,
        email=email,
        password_hash="hashed",
        is_active=True,
        role="viewer",
        is_email_verified=True,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    request = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers.get.return_value = ""
    with patch("server.api.auth.verify_password", return_value=True):
        return login(
            LoginRequest(email=email, password="password1"),
            request,
            MagicMock(),
            db,
        )


@pytest.mark.parametrize(
    "email",
    ["apply-smoke+x@mail.test", "x@example.com", "Apply-Smoke+X@Mail.Test", "X@Example.COM"],
)
def test_signup_sets_internal_flag_without_the_address(email):
    with _capture_posts() as sent:
        assert emit_signup_completed(user_id=7, method="email", email=email) is True
    _assert_flagged(sent, email, "7")
    signup = [body for body in _bodies(sent) if body["event"] == "signup_completed"]
    assert len(signup) == 1
    assert "$internal_or_test_user" not in json.dumps(signup[0]["properties"])


@pytest.mark.parametrize("email", ["apply-smoke+x@acme.io", "x@example.com"])
def test_login_sets_internal_flag_without_the_address(email):
    with _capture_posts() as sent:
        result = _login(email)
    assert result.user_id == 9
    _assert_flagged(sent, email, "9")


def test_signup_capture_failure_still_flags_an_internal_account():
    with patch("server.services.activation.posthog_capture", side_effect=RuntimeError("down")):
        with _capture_posts() as sent:
            assert emit_signup_completed(user_id=7, method="email", email="x@example.com") is False
    _assert_flagged(sent, "x@example.com", "7")


def test_normal_founder_signup_and_login_do_not_set_the_flag():
    email = "founder@acme.io"
    with _capture_posts() as sent:
        assert emit_signup_completed(user_id=4, method="email", email=email) is True
    assert _flag_events(sent) == []
    assert "$internal_or_test_user" not in _blob(sent)
    _assert_no_address(sent, email)

    with _capture_posts() as sent:
        result = _login(email)
    assert result.email == email
    assert sent == []


def test_near_miss_addresses_are_normal_founders():
    """The smoke prefix and example.com domain are exact, not substrings."""
    for email in (
        "apply-smoke@acme.io",
        "not-apply-smoke+x@acme.io",
        "founder@sub.example.com",
        "founder@example.org",
    ):
        with _capture_posts() as sent:
            assert sync_internal_or_test_person(4, email) is False
        assert sent == []


def test_demo_account_and_platform_admin_are_internal_without_the_address():
    with _capture_posts() as sent:
        assert sync_internal_or_test_person(3, "demo@founderconsole.ai") is True
    _assert_flagged(sent, "demo@founderconsole.ai", "3")

    with _capture_posts() as sent:
        assert sync_internal_or_test_person(
            11, "owner@acme.io", is_platform_admin=True
        ) is True
    _assert_flagged(sent, "owner@acme.io", "11")

    with _capture_posts() as sent:
        assert sync_internal_or_test_person(12, "owner@acme.io", is_master=True) is True
    _assert_flagged(sent, "owner@acme.io", "12")


def test_admin_master_email_is_internal_without_sending_it(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_MASTER_EMAIL", "Owner@Acme.io")
    with _capture_posts() as sent:
        assert sync_internal_or_test_person(11, "owner@acme.io") is True
    _assert_flagged(sent, "owner@acme.io", "11")
    _assert_no_address(sent, "Owner@Acme.io")


def test_company_admin_role_is_not_an_internal_user():
    """role=admin is a company role. It does not set the PostHog flag."""
    with _capture_posts() as sent:
        assert sync_internal_or_test_person(6, "ops@acme.io", is_platform_admin=False) is False
    assert sent == []


def test_returning_google_example_user_is_flagged_without_the_address():
    from server.api.oauth import _get_or_create_oauth_user

    user = SimpleNamespace(
        id=8,
        email="x@example.com",
        password_hash="hashed",
        is_email_verified=True,
        oauth_provider="google",
        oauth_id="g-1",
        display_name="X",
        avatar_url=None,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    with _capture_posts() as sent:
        linked = _get_or_create_oauth_user(db, "x@example.com", "google", "g-1")
    assert linked.id == 8
    _assert_flagged(sent, "x@example.com", "8")


def test_email_shaped_distinct_id_is_not_sent():
    with _capture_posts() as sent:
        assert posthog_svc.set_internal_or_test_person("x@example.com") is False
    assert sent == []
