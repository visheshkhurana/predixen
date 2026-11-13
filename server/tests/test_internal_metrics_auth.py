"""GET /metrics/internal is an internal timing summary.

It used to answer unauthenticated, and on failure it returned str(e).
"""

from unittest.mock import patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from server.core.db import get_db
from server.core.security import get_current_user
from server.main import app, internal_metrics


def _production_route():
    matches = [r for r in app.routes if getattr(r, "path", None) == "/metrics/internal"]
    assert len(matches) == 1
    return matches[0]


def test_the_live_route_requires_auth():
    route = _production_route()
    assert route.endpoint is internal_metrics
    dependency_calls = [dep.call for dep in route.dependant.dependencies]
    assert get_current_user in dependency_calls


def _isolated_client(overrides: dict | None = None) -> TestClient:
    mini = FastAPI()
    mini.add_api_route(
        "/metrics/internal",
        internal_metrics,
        methods=["GET"],
        dependencies=[Depends(get_current_user)],
    )
    if overrides:
        mini.dependency_overrides.update(overrides)
    return TestClient(mini)


def test_unauthenticated_request_is_401():
    def _db():
        yield None

    response = _isolated_client({get_db: _db}).get("/metrics/internal")
    assert response.status_code == 401
    assert "hunter2" not in response.text
    assert "Internal metrics unavailable" not in response.text


def test_failure_does_not_return_the_exception_text():
    secret = "driver password=hunter2-should-not-leak"
    client = _isolated_client({get_current_user: lambda: object()})
    with patch(
        "server.core.observability.get_metrics_summary",
        side_effect=RuntimeError(secret),
    ):
        response = client.get("/metrics/internal")
    assert response.status_code == 200
    body = response.json()
    assert body["metrics"] == {}
    assert body["error"] == "Internal metrics unavailable"
    assert secret not in response.text
    assert "RuntimeError" not in response.text


def test_authenticated_success_returns_the_summary():
    client = _isolated_client({get_current_user: lambda: object()})
    with patch(
        "server.core.observability.get_metrics_summary",
        return_value={"simulation.run": {"count": 2}},
    ):
        response = client.get("/metrics/internal")
    assert response.status_code == 200
    assert response.json() == {"metrics": {"simulation.run": {"count": 2}}}
