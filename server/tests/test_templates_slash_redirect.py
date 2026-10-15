"""GET /templates must not 307 to the internal bind.

FastAPI redirect_slashes turns a missing trailing slash into a 307 whose
Location is built from the request host. Behind the Express proxy that host
is localhost:8001 and /api has already been stripped. Both paths are
registered so the list is served in place.
"""

from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import templates as templates_api
from server.core.security import get_current_user

OWNER = SimpleNamespace(id=1, email="owner@example.com", is_platform_admin=False, role="user")


def _client(user=None) -> TestClient:
    app = FastAPI()
    # No extra /api prefix: this is the app the proxy talks to after stripping /api.
    app.include_router(templates_api.router)
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_templates_list_without_slash_is_401_not_an_internal_redirect():
    resp = _client().get(
        "/templates",
        follow_redirects=False,
        headers={"host": "localhost:8001"},
    )
    assert resp.status_code == 401, (resp.status_code, resp.headers.get("location"), resp.text)
    location = resp.headers.get("location", "")
    assert "localhost" not in location
    assert "8001" not in location


def test_templates_list_serves_both_slash_forms_without_redirect():
    client = _client(user=OWNER)
    bare = client.get("/templates", follow_redirects=False)
    slashed = client.get("/templates/", follow_redirects=False)
    assert bare.status_code == 200, bare.text
    assert slashed.status_code == 200, slashed.text
    assert bare.headers.get("location") is None
    assert slashed.headers.get("location") is None
    assert bare.json() == slashed.json()
    assert "templates" in bare.json()
