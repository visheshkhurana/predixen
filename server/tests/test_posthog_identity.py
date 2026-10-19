"""PostHog key selection, alias payload, and OAuth distinct_id handoff."""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

from server.services import posthog as posthog_svc


class _FakeUrlOpen:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"status":"ok"}'


def _clear_posthog_env(monkeypatch):
    monkeypatch.delenv("POSTHOG_KEY", raising=False)
    monkeypatch.delenv("POSTHOG_PROJECT_API_KEY", raising=False)
    posthog_svc._logged_choice = None


def test_user_distinct_id_matches_browser_identify():
    assert posthog_svc.user_distinct_id(7) == "7"
    assert not posthog_svc.user_distinct_id(7).startswith("user:")


def test_default_key_is_used_and_logged_when_env_is_unset(monkeypatch, caplog):
    _clear_posthog_env(monkeypatch)
    with caplog.at_level(logging.INFO):
        assert posthog_svc._api_key() == posthog_svc._DEFAULT_KEY
    assert "using default" in caplog.text
    assert posthog_svc._DEFAULT_KEY not in caplog.text
    assert "phc_C3jj" in caplog.text


def test_matching_env_key_is_used_and_named(monkeypatch, caplog):
    _clear_posthog_env(monkeypatch)
    monkeypatch.setenv("POSTHOG_KEY", posthog_svc._DEFAULT_KEY)
    with caplog.at_level(logging.INFO):
        assert posthog_svc._api_key() == posthog_svc._DEFAULT_KEY
    assert "POSTHOG_KEY" in caplog.text
    assert "matches the browser project token" in caplog.text
    assert posthog_svc._DEFAULT_KEY not in caplog.text


def test_blank_posthog_key_falls_through_to_project_key(monkeypatch, caplog):
    posthog_svc._logged_choice = None
    monkeypatch.setenv("POSTHOG_KEY", "   ")
    monkeypatch.setenv("POSTHOG_PROJECT_API_KEY", posthog_svc._DEFAULT_KEY)
    with caplog.at_level(logging.INFO):
        assert posthog_svc._api_key() == posthog_svc._DEFAULT_KEY
    assert "POSTHOG_PROJECT_API_KEY" in caplog.text
    assert "matches the browser project token" in caplog.text


def test_mismatched_env_key_is_refused(monkeypatch, caplog):
    wrong = "phc_WRONGKEYxxxxxxxxOLD1"
    _clear_posthog_env(monkeypatch)
    monkeypatch.setenv("POSTHOG_KEY", wrong)
    with caplog.at_level(logging.WARNING):
        assert posthog_svc._api_key() == posthog_svc._DEFAULT_KEY
    assert "refusing POSTHOG_KEY" in caplog.text
    assert "does not match the browser project token" in caplog.text
    assert wrong not in caplog.text
    assert posthog_svc._DEFAULT_KEY not in caplog.text


def test_mismatched_project_key_is_refused_when_primary_is_unset(monkeypatch, caplog):
    wrong = "phc_OTHERKEYyyyyyyyyOLD2"
    _clear_posthog_env(monkeypatch)
    monkeypatch.setenv("POSTHOG_PROJECT_API_KEY", wrong)
    with caplog.at_level(logging.WARNING):
        assert posthog_svc._api_key() == posthog_svc._DEFAULT_KEY
    assert "refusing POSTHOG_PROJECT_API_KEY" in caplog.text
    assert wrong not in caplog.text


def test_capture_posts_the_known_good_key_when_env_disagrees(monkeypatch):
    wrong = "phc_staleprojecttokenXXXX"
    _clear_posthog_env(monkeypatch)
    monkeypatch.setenv("POSTHOG_KEY", wrong)
    captured = {}

    def fake_urlopen(req, timeout=5):
        captured["body"] = req.data
        return _FakeUrlOpen(200)

    with patch.object(posthog_svc.urllib.request, "urlopen", side_effect=fake_urlopen):
        assert posthog_svc.capture("signup_completed", "7", {"method": "email"})

    body = json.loads(captured["body"])
    assert body["api_key"] == posthog_svc._DEFAULT_KEY
    assert body["api_key"] != wrong
    assert body["distinct_id"] == "7"
    assert body["properties"]["$process_person_profile"] is False


def test_alias_merges_previous_id_into_the_user_id(monkeypatch):
    _clear_posthog_env(monkeypatch)
    captured = {}

    def fake_urlopen(req, timeout=5):
        captured["body"] = req.data
        captured["url"] = req.full_url
        return _FakeUrlOpen(200)

    with patch.object(posthog_svc.urllib.request, "urlopen", side_effect=fake_urlopen):
        assert posthog_svc.alias(previous_id="anon-browser", distinct_id="7")

    body = json.loads(captured["body"])
    assert captured["url"].endswith("/capture/")
    assert body["event"] == "$create_alias"
    assert body["api_key"] == posthog_svc._DEFAULT_KEY
    #  previous id is merged away; properties.alias becomes the canonical id.
    assert body["distinct_id"] == "anon-browser"
    assert body["properties"]["alias"] == "7"
    assert "$process_person_profile" not in body["properties"]


def test_alias_skips_same_id_email_and_blank():
    with patch.object(posthog_svc.urllib.request, "urlopen") as urlopen:
        assert posthog_svc.alias(previous_id="7", distinct_id="7") is False
        assert posthog_svc.alias(previous_id="a@b.co", distinct_id="7") is False
        assert posthog_svc.alias(previous_id="  ", distinct_id="7") is False
        urlopen.assert_not_called()


def test_alias_rejects_a_client_supplied_optin_id():
    with patch.object(posthog_svc.urllib.request, "urlopen") as urlopen:
        assert posthog_svc.alias(previous_id="optin:abc123", distinct_id="7") is False
        assert posthog_svc.alias(previous_id="  OPTIN:abc123  ", distinct_id="7") is False
        urlopen.assert_not_called()
    assert posthog_svc.sanitize_distinct_id("optin:abc123") is None
    assert posthog_svc.sanitize_distinct_id("OPTIN:abc123") is None


def test_alias_swallows_network_errors(monkeypatch):
    _clear_posthog_env(monkeypatch)

    def boom(*args, **kwargs):
        raise TimeoutError("slow")

    with patch.object(posthog_svc.urllib.request, "urlopen", side_effect=boom):
        assert posthog_svc.alias(previous_id="anon-browser", distinct_id="7") is False


def test_google_start_keeps_distinct_id_off_the_google_url(monkeypatch):
    from server.api import oauth
    from server.core.config import settings

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "csec")
    oauth._oauth_states.clear()
    request = MagicMock()
    request.headers.get.return_value = None

    response = oauth.google_start(request, distinct_id="  anon-browser  ")

    location = response.headers["location"]
    assert "anon-browser" not in location
    assert location.startswith("https://accounts.google.com/")
    assert len(oauth._oauth_states) == 1
    state, stored = next(iter(oauth._oauth_states.items()))
    assert stored == {"provider": "google", "distinct_id": "anon-browser"}
    ok, anon = oauth._take_google_state(state)
    assert ok is True
    assert anon == "anon-browser"
    oauth._oauth_states.clear()


def test_google_start_drops_an_email_shaped_distinct_id(monkeypatch):
    from server.api import oauth
    from server.core.config import settings

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "csec")
    oauth._oauth_states.clear()
    request = MagicMock()
    request.headers.get.return_value = None

    oauth.google_start(request, distinct_id="founder@example.com")

    stored = next(iter(oauth._oauth_states.values()))
    assert stored["distinct_id"] is None
    oauth._oauth_states.clear()


def test_legacy_google_state_string_still_valid():
    from server.api import oauth

    oauth._oauth_states["legacy"] = "google"
    ok, anon = oauth._take_google_state("legacy")
    assert ok is True
    assert anon is None
    ok, anon = oauth._take_google_state("missing")
    assert ok is False
    assert anon is None


def test_sanitize_distinct_id_rejects_control_characters():
    assert posthog_svc.sanitize_distinct_id("anon\nbrowser") is None
    assert posthog_svc.sanitize_distinct_id(None) is None
    assert posthog_svc.sanitize_distinct_id(7) is None
    assert posthog_svc.sanitize_distinct_id("anon-browser") == "anon-browser"


def test_alias_refuses_when_42_belongs_to_another_user(monkeypatch):
    """A browser id that is some other account must not be merged away.

    "42" and "user:42" are that user's id. All-digit ids are refused even
    when no row exists, because they are account ids, not anonymous ones.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from server.core import db as db_mod
    from server.models.user import User

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    User.metadata.create_all(engine, tables=[User.__table__])
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(User(id=42, email="other@example.com", password_hash="x"))
    db.commit()
    db.close()
    monkeypatch.setattr(db_mod, "SessionLocal", Session)

    checked: list[int] = []
    real_exists = posthog_svc._user_id_exists

    def tracked(user_id: int) -> bool:
        checked.append(user_id)
        return real_exists(user_id)

    monkeypatch.setattr(posthog_svc, "_user_id_exists", tracked)
    _clear_posthog_env(monkeypatch)

    with patch.object(posthog_svc.urllib.request, "urlopen") as urlopen:
        assert posthog_svc.alias(previous_id="42", distinct_id="7") is False
        assert posthog_svc.alias(previous_id="user:42", distinct_id="7") is False
        assert posthog_svc.sanitize_distinct_id("42") is None
        assert posthog_svc.sanitize_distinct_id("user:42") is None
        assert posthog_svc.sanitize_distinct_id("999") is None
        urlopen.assert_not_called()

    assert 42 in checked
    assert real_exists(42) is True
    assert real_exists(999) is False
    assert posthog_svc.sanitize_distinct_id("anon-browser") == "anon-browser"
