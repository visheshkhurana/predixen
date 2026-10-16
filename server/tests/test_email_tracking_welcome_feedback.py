"""/email-tracking/welcome only redirects on-site; /feedback escapes its params."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import email_tracking as email_tracking_api
from server.core.db import get_db


def _client(monkeypatch) -> TestClient:
    def fake_get_db():
        yield MagicMock()

    monkeypatch.setattr(email_tracking_api, "get_db", fake_get_db)
    app = FastAPI()
    app.include_router(email_tracking_api.router)
    app.dependency_overrides[get_db] = fake_get_db
    return TestClient(app, follow_redirects=False)


def _welcome_path() -> str:
    prefix = email_tracking_api.router.prefix or ""
    return f"{prefix}/welcome"


def _feedback_path() -> str:
    prefix = email_tracking_api.router.prefix or ""
    return f"{prefix}/feedback"


@pytest.mark.parametrize(
    "dest",
    [
        "https://evil.example.com/login",
        "//evil.example.com",
        "/\\evil.example.com",
        "https://founderconsole.ai.evil.example.com/",
        "https://evil.example.com/?x=founderconsole.ai",
        "javascript:alert(1)",
        "http://founderconsole.ai/",
        "https://user@evil.example.com",
    ],
)
def test_offsite_dest_falls_back_to_home(monkeypatch, dest):
    r = _client(monkeypatch).get(_welcome_path(), params={"dest": dest})
    assert r.status_code == 302
    assert r.headers["location"] == "https://founderconsole.ai"


@pytest.mark.parametrize(
    "dest",
    ["/pricing", "/blog/runway?x=1", "https://founderconsole.ai/auth", "https://app.founderconsole.ai/"],
)
def test_onsite_dest_is_kept(monkeypatch, dest):
    r = _client(monkeypatch).get(_welcome_path(), params={"dest": dest})
    assert r.status_code == 302
    assert r.headers["location"] == dest


def test_feedback_page_escapes_query_params(monkeypatch):
    payload = '"><script>alert(1)</script>'
    r = _client(monkeypatch).get(
        _feedback_path(), params={"email": payload, "campaign": payload, "email_id": payload}
    )
    assert r.status_code == 200
    assert "<script>alert(1)</script>" not in r.text
    import re

    hrefs = re.findall(r'href="([^"]*)"', r.text)
    assert len(hrefs) == 3
    assert all(h.endswith(("rating=helpful", "rating=somewhat", "rating=not_helpful")) for h in hrefs)
