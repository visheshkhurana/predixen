"""Audit 2026-10-15: cross-tenant access and OAuth account pre-hijack.

simulation_jobs and suggestions accepted any signed-in caller for any id; the
Google callback linked to any password account with the same email. Routers
are mounted on a bare app with the DB mocked, as in test_router_auth_lock.py.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from server.api import oauth as oauth_api
from server.api import simulation_jobs as sim_api
from server.api import suggestions as suggestions_api
from server.core.db import get_db
from server.core.security import get_current_user

OWNER = SimpleNamespace(id=1, email="owner@example.com", is_platform_admin=False, role="user")
STRANGER = SimpleNamespace(id=2, email="stranger@example.com", is_platform_admin=False, role="user")


def _client(router, db, user) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


# --- simulation_jobs -------------------------------------------------------

def _sim_db() -> MagicMock:
    """Every lookup finds a row belonging to company 1, scenario 1."""
    db = MagicMock()
    row = SimpleNamespace(
        id=1, company_id=1, scenario_id=1, version=1, status="completed",
        inputs_json={}, events_json=[], tags=[], name="s", description=None,
        latest_truth_dataset_id=None, progress=100, config_json={},
        created_at=None, started_at=None, completed_at=None,
        execution_time_ms=0, error_message=None, results_json={},
    )
    db.query.return_value.filter.return_value.first.return_value = row
    return db


@pytest.fixture
def owner_only_access(monkeypatch):
    def fake_get_user_company(db, company_id, user):
        if user.id != OWNER.id:
            raise HTTPException(status_code=403, detail="Access denied to this company")
        return SimpleNamespace(id=company_id, user_id=OWNER.id)

    monkeypatch.setattr(sim_api, "get_user_company", fake_get_user_company, raising=False)


STRANGER_CASES = [
    ("POST", "/api/simulations/run", {"scenario_id": 1}),
    ("GET", "/api/simulations/jobs/job-1", None),
    ("POST", "/api/simulations/sensitivity", {"scenario_id": 1, "parameters": []}),
    ("POST", "/api/simulations/versions", {"scenario_id": 1}),
    ("GET", "/api/simulations/versions/1", None),
    ("GET", "/api/simulations/versions/1/1", None),
    ("POST", "/api/simulations/versions/diff?scenario_id=1", {"version_a": 1, "version_b": 2}),
    ("POST", "/api/simulations/versions/1/1/restore", None),
]


@pytest.mark.parametrize("method,path,body", STRANGER_CASES)
def test_stranger_gets_404_and_nothing_is_written(owner_only_access, method, path, body):
    db = _sim_db()
    resp = _client(sim_api.router, db, STRANGER).request(method, path, json=body)
    assert resp.status_code == 404, (path, resp.status_code, resp.text)
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_owner_can_read_their_scenario_versions(owner_only_access):
    db = _sim_db()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    resp = _client(sim_api.router, db, OWNER).get("/api/simulations/versions/1")
    assert resp.status_code == 200, resp.text


def test_job_listing_is_scoped_to_callers_companies():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [SimpleNamespace(id=7)]
    resp = _client(sim_api.router, db, STRANGER).get("/api/simulations/jobs")
    assert resp.status_code == 200, resp.text
    db.query.return_value.join.assert_called_once()


def test_platform_admin_job_listing_is_unscoped():
    admin = SimpleNamespace(id=9, email="a@example.com", is_platform_admin=True, role="admin")
    db = MagicMock()
    resp = _client(sim_api.router, db, admin).get("/api/simulations/jobs")
    assert resp.status_code == 200, resp.text
    db.query.return_value.join.assert_not_called()


# --- suggestions -----------------------------------------------------------

def _company_db(owner_id: int) -> MagicMock:
    db = MagicMock()
    company = SimpleNamespace(id=1, user_id=owner_id)
    # get_user_company: company lookup, then WorkspaceMember lookup (none).
    db.query.return_value.filter.return_value.first.side_effect = [company, None, None]
    return db


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/suggestions?company_id=1"),
    ("GET", "/api/suggestions/5?company_id=1"),
    ("POST", "/api/suggestions/5/accept?company_id=1"),
    ("POST", "/api/suggestions/5/dismiss?company_id=1"),
    ("GET", "/api/suggestions/5/explain?company_id=1"),
    ("POST", "/api/suggestions/generate?company_id=1"),
    ("GET", "/api/suggestions/capabilities/list?company_id=1"),
])
def test_suggestions_reject_a_stranger(method, path):
    db = _company_db(owner_id=OWNER.id)
    resp = _client(suggestions_api.router, db, STRANGER).request(method, path, json={})
    assert resp.status_code == 403, (path, resp.status_code, resp.text)
    db.add.assert_not_called()
    db.commit.assert_not_called()


# --- Google OAuth linking --------------------------------------------------

def _oauth_db(existing):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing
    return db


def test_unverified_password_account_is_reclaimed_not_shared():
    planted = SimpleNamespace(
        id=3, email="victim@corp.com", password_hash="attacker-hash",
        is_email_verified=False, oauth_provider=None, oauth_id=None,
        display_name=None, avatar_url=None,
    )
    db = _oauth_db(planted)
    user = oauth_api._get_or_create_oauth_user(db, "victim@corp.com", "google", "g-123")
    assert user.password_hash is None, "the planted password must not survive the link"
    assert user.is_email_verified is True
    assert user.oauth_id == "g-123"
    db.query.return_value.filter.return_value.update.assert_called_once()


def test_verified_password_account_keeps_its_password():
    real = SimpleNamespace(
        id=4, email="me@corp.com", password_hash="my-hash",
        is_email_verified=True, oauth_provider=None, oauth_id=None,
        display_name=None, avatar_url=None,
    )
    db = _oauth_db(real)
    user = oauth_api._get_or_create_oauth_user(db, "me@corp.com", "google", "g-456")
    assert user.password_hash == "my-hash"
    assert user.oauth_id == "g-456"
    db.query.return_value.filter.return_value.update.assert_not_called()


def test_different_google_identity_for_linked_email_is_refused():
    linked = SimpleNamespace(
        id=5, email="me@corp.com", password_hash=None, is_email_verified=True,
        oauth_provider="google", oauth_id="g-original",
        display_name=None, avatar_url=None,
    )
    with pytest.raises(oauth_api.OAuthLinkError):
        oauth_api._get_or_create_oauth_user(_oauth_db(linked), "me@corp.com", "google", "g-other")


def test_callback_refuses_an_email_google_has_not_verified(monkeypatch):
    monkeypatch.setattr(oauth_api.settings, "GOOGLE_CLIENT_ID", "cid", raising=False)
    monkeypatch.setattr(oauth_api.settings, "GOOGLE_CLIENT_SECRET", "secret", raising=False)
    oauth_api._oauth_states["st"] = "google"

    token_resp = MagicMock()
    token_resp.json.return_value = {"access_token": "at"}
    profile_resp = MagicMock()
    profile_resp.json.return_value = {"email": "victim@corp.com", "id": "g-1", "verified_email": False}
    monkeypatch.setattr(oauth_api.requests, "post", lambda *a, **k: token_resp)
    monkeypatch.setattr(oauth_api.requests, "get", lambda *a, **k: profile_resp)

    linked = []
    monkeypatch.setattr(oauth_api, "_get_or_create_oauth_user", lambda *a, **k: linked.append(1))

    app = FastAPI()
    app.include_router(oauth_api.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: MagicMock()
    paths = [r.path for r in app.routes if getattr(r, "path", "").endswith("/google/callback")]
    resp = TestClient(app).get(f"{paths[0]}?code=c&state=st", follow_redirects=False)

    assert resp.status_code == 302
    assert "error=google_unverified_email" in resp.headers["location"]
    assert linked == [], "no account may be created or linked for an unverified email"
