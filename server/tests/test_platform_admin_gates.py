"""Platform-admin gates, lead email escaping, and owner-only LLM routes.

Routers are mounted on bare apps with the DB mocked; no network or database.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from server.api import admin as admin_api
from server.api import email_templates as email_templates_api
from server.api import email_tracking as email_tracking_api
from server.api import leads as leads_api
from server.api import llm as llm_api
from server.core.config import settings
from server.core.db import get_db
from server.core.security import MasterUser, get_current_user

ADMIN_EMAIL = "owner@example.com"


def _user(email=ADMIN_EMAIL, verified=True, role="viewer", uid=7):
    return SimpleNamespace(
        id=uid, email=email, is_email_verified=verified, role=role,
        _is_master_user=False, is_platform_admin=False,
    )


@pytest.fixture(autouse=True)
def _admin_email(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_MASTER_EMAIL", ADMIN_EMAIL)


def _client(router, user):
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: MagicMock()
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


# --- is_platform_admin / require_platform_admin -------------------------------

def test_verified_matching_email_is_admin():
    assert admin_api.is_platform_admin(_user()) is True


def test_unverified_matching_email_is_not_admin():
    assert admin_api.is_platform_admin(_user(verified=False)) is False


def test_email_match_is_case_insensitive_but_still_needs_verification():
    assert admin_api.is_platform_admin(_user(email=" Owner@Example.com ")) is True
    assert admin_api.is_platform_admin(_user(email="Owner@Example.com", verified=None)) is False


def test_other_email_is_not_admin_even_with_owner_role():
    assert admin_api.is_platform_admin(_user(email="someone@example.com", role="owner")) is False


def test_master_session_is_admin():
    assert admin_api.is_platform_admin(MasterUser()) is True


def test_require_platform_admin_rejects_unverified_match():
    with pytest.raises(HTTPException) as exc:
        admin_api.require_platform_admin(_user(verified=False), MagicMock())
    assert exc.value.status_code == 403


def test_require_platform_admin_accepts_master():
    master = MasterUser()
    with patch.object(admin_api, "log_audit"):
        assert admin_api.require_platform_admin(master, MagicMock()) is master


# --- email templates / email analytics: role never grants admin ---------------

def test_email_templates_reject_company_owner_role():
    client = _client(email_templates_api.router, _user(email="founder@startup.io", role="owner"))
    assert client.get("/api/email-templates/templates").status_code == 403


def test_email_templates_allow_platform_admin():
    client = _client(email_templates_api.router, _user())
    assert client.get("/api/email-templates/templates").status_code == 200


def _verify_with_user(monkeypatch, user):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user

    def fake_get_db():
        yield db

    monkeypatch.setattr(email_tracking_api, "get_db", fake_get_db)
    monkeypatch.setattr("server.core.security.decode_token", lambda t: {"sub": str(user.id)})
    return email_tracking_api._verify_admin_jwt("token")


def test_email_analytics_rejects_owner_role(monkeypatch):
    assert _verify_with_user(monkeypatch, _user(email="founder@startup.io", role="owner")) is False


def test_email_analytics_rejects_unverified_admin_email(monkeypatch):
    assert _verify_with_user(monkeypatch, _user(verified=False)) is False


def test_email_analytics_accepts_verified_admin(monkeypatch):
    assert _verify_with_user(monkeypatch, _user()) is True


# --- lead runway email ---------------------------------------------------------

def _lead(**kw):
    base = dict(email="v@example.com", runway_months="4", runway_date="May 2027", monthly_burn="$10k")
    base.update(kw)
    return leads_api.LeadCreate(**base)


def test_runway_email_escapes_visitor_input():
    html = leads_api._runway_email_html(
        _lead(runway_months="<img src=x>", runway_date='"><a href=//e.test>', monthly_burn="&<b>")
    )
    assert "<img" not in html
    assert "<a href=//e.test>" not in html
    assert "&lt;img src=x&gt;" in html
    assert "&amp;&lt;b&gt;" in html


# --- raw LLM routes ------------------------------------------------------------

LLM_PATHS = [
    ("/api/llm/chat", {"json": {"messages": [{"role": "user", "content": "hi"}]}}),
    ("/api/llm/quick-chat?prompt=hi", {}),
    ("/api/llm/smart-chat", {"json": {"message": "hi"}}),
    ("/api/llm/web-search", {"json": {"query": "hi"}}),
]


@pytest.mark.parametrize("path,kwargs", LLM_PATHS)
def test_llm_routes_reject_ordinary_user(path, kwargs):
    client = _client(llm_api.router, _user(email="founder@startup.io", role="owner"))
    with patch.object(llm_api, "get_llm_router") as router:
        res = client.post(path, **kwargs)
    assert res.status_code == 403
    router.assert_not_called()
