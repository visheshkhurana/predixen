"""Google signups are tracked and followed up like email signups.

Google is the main converting path, but it reached the client with no signal
that the account was new, carried no campaign attribution to the server event,
never enrolled the user in the welcome sequence, and its Slack ping called
get_event_loop().create_task() from a sync route with no running loop.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api import oauth as oauth_api
from server.core.config import settings
from server.core.db import get_db
from server.models.user import RefreshToken, User


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "csec")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(engine, tables=[User.__table__, RefreshToken.__table__])
    Session = sessionmaker(bind=engine)

    app = FastAPI()
    app.include_router(oauth_api.router, prefix="/api")

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    oauth_api._oauth_states.clear()
    oauth_api._oauth_attribution.clear()
    yield TestClient(app), Session
    oauth_api._oauth_states.clear()
    oauth_api._oauth_attribution.clear()


def _google(email: str):
    token = MagicMock()
    token.json.return_value = {"access_token": "at"}
    profile = MagicMock()
    profile.json.return_value = {"email": email, "verified_email": True, "id": "g-1", "name": "Asha"}
    return patch.object(oauth_api.requests, "post", return_value=token), \
        patch.object(oauth_api.requests, "get", return_value=profile)


def _login(client, email, start_query=""):
    start = client.get(f"/api/auth/google/start{start_query}", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    post, get = _google(email)
    with post, get, \
            patch("server.services.activation.emit_signup_completed") as emit, \
            patch("server.email.onboarding_sequence.enroll_new_signup") as enroll, \
            patch("server.email.service.send_slack_signup_notification") as slack:
        res = client.get(f"/api/auth/google/callback?code=c&state={state}", follow_redirects=False)
    params = parse_qs(urlparse(res.headers["location"]).query)
    return res, params, emit, enroll, slack


def test_new_google_user_is_flagged_attributed_and_enrolled(env):
    client, _ = env
    res, params, emit, enroll, slack = _login(
        client, "new@brand.in",
        "?utm_source=meta&utm_campaign=d2c-launch&gclid=abc&utm_term=me%40x.com",
    )
    assert res.status_code == 302
    assert params.get("new_user") == ["1"]
    attribution = emit.call_args.kwargs["attribution"]
    assert attribution["utm_source"] == "meta"
    assert attribution["utm_campaign"] == "d2c-launch"
    assert attribution["gclid"] == "abc"
    assert "utm_term" not in attribution, "email-shaped values never reach analytics"
    enroll.assert_called_once()
    assert enroll.call_args.args[1] == "new@brand.in"
    slack.assert_called_once()


def test_returning_google_user_is_not_counted_again(env):
    client, Session = env
    db = Session()
    db.add(User(email="back@brand.in", oauth_provider="google", oauth_id="g-1", is_email_verified=True))
    db.commit()
    db.close()

    _, params, emit, enroll, slack = _login(client, "back@brand.in", "?utm_source=meta")
    assert "new_user" not in params
    emit.assert_not_called()
    enroll.assert_not_called()
    slack.assert_not_called()


def test_attribution_never_goes_to_google():
    request = MagicMock()
    request.headers.get.return_value = None
    request.query_params = {"utm_source": "meta-campaign-xyz"}
    with patch.object(settings, "GOOGLE_CLIENT_ID", "cid"), patch.object(settings, "GOOGLE_CLIENT_SECRET", "csec"):
        response = oauth_api.google_start(request)
    assert "meta-campaign-xyz" not in response.headers["location"]
    oauth_api._oauth_states.clear()
    oauth_api._oauth_attribution.clear()


def test_attribution_store_is_bounded(monkeypatch):
    monkeypatch.setattr(oauth_api, "_OAUTH_ATTRIBUTION_MAX", 3)
    oauth_api._oauth_attribution.clear()
    for i in range(5):
        oauth_api._remember_google_attribution(f"s{i}", {"utm_source": "x"})
    assert list(oauth_api._oauth_attribution) == ["s2", "s3", "s4"]
    oauth_api._oauth_attribution.clear()
