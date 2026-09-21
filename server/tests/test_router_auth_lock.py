"""P0 auth lock: templates / integrations / notifications must reject strangers.

Each router is mounted on a bare app with the DB mocked, so an unauthenticated
request must fail in the auth dependency before any query or write happens.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import integrations as integrations_api
from server.api import notifications as notifications_api
from server.api import templates as templates_api
from server.api.admin import require_platform_admin
from server.core.db import get_db
from server.core.security import get_current_user

OWNER = SimpleNamespace(id=1, email="owner@example.com", is_platform_admin=False, role="user")
STRANGER = SimpleNamespace(id=2, email="stranger@example.com", is_platform_admin=False, role="user")


def _db_with_company(owner_id: int = OWNER.id) -> MagicMock:
    db = MagicMock()
    company = SimpleNamespace(id=1, user_id=owner_id)
    # get_user_company: company lookup, then WorkspaceMember lookup (none).
    db.query.return_value.filter.return_value.first.side_effect = [company, None, None, None]
    return db


def _client(router, db=None, user=None) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    db = db if db is not None else MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


UNAUTH_CASES = [
    (templates_api.router, "GET", "/api/templates/"),
    (templates_api.router, "GET", "/api/templates/baseline"),
    (templates_api.router, "GET", "/api/templates/category/conservative"),
    (templates_api.router, "POST", "/api/templates/companies/1/apply/baseline"),
    (templates_api.router, "POST", "/api/templates/companies/1/bulk-apply"),
    (integrations_api.router, "GET", "/api/integrations/available"),
    (integrations_api.router, "GET", "/api/integrations/companies/1/status"),
    (integrations_api.router, "POST", "/api/integrations/companies/1/accounting/sync"),
    (integrations_api.router, "POST", "/api/integrations/companies/1/payments/connect"),
    (integrations_api.router, "GET", "/api/integrations/companies/1/crm/pipeline"),
    (notifications_api.router, "GET", "/api/notifications/email-stats"),
    (notifications_api.router, "GET", "/api/notifications/email-stats/abc"),
    (notifications_api.router, "GET", "/api/notifications/recipients"),
    (notifications_api.router, "GET", "/api/notifications/changelog"),
    (notifications_api.router, "POST", "/api/notifications/feature"),
    (notifications_api.router, "POST", "/api/notifications/publish"),
    (notifications_api.router, "POST", "/api/notifications/early-member-invite"),
    (notifications_api.router, "POST", "/api/notifications/digest/send"),
    (notifications_api.router, "POST", "/api/notifications/digest/test"),
]


@pytest.mark.parametrize("router,method,path", UNAUTH_CASES)
def test_no_session_is_401_and_touches_no_db(router, method, path):
    db = MagicMock()
    resp = _client(router, db=db).request(method, path, json={})
    assert resp.status_code == 401, (path, resp.status_code, resp.text)
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_stranger_cannot_apply_template_to_someone_elses_company():
    db = _db_with_company(owner_id=OWNER.id)
    resp = _client(templates_api.router, db=db, user=STRANGER).post(
        "/api/templates/companies/1/apply/baseline"
    )
    assert resp.status_code == 403
    db.add.assert_not_called()


def test_stranger_cannot_bulk_apply_templates():
    db = _db_with_company(owner_id=OWNER.id)
    resp = _client(templates_api.router, db=db, user=STRANGER).post(
        "/api/templates/companies/1/bulk-apply", json=["baseline"]
    )
    assert resp.status_code == 403
    db.add.assert_not_called()


def test_stranger_cannot_read_integration_status():
    db = _db_with_company(owner_id=OWNER.id)
    resp = _client(integrations_api.router, db=db, user=STRANGER).get(
        "/api/integrations/companies/1/status"
    )
    assert resp.status_code == 403


def test_owner_can_apply_template():
    db = _db_with_company(owner_id=OWNER.id)
    template_id = templates_api.get_all_templates()
    template_id = next(iter(template_id)) if isinstance(template_id, dict) else template_id[0]["id"]
    resp = _client(templates_api.router, db=db, user=OWNER).post(
        f"/api/templates/companies/1/apply/{template_id}"
    )
    assert resp.status_code == 200, resp.text
    db.add.assert_called_once()


def test_logged_in_user_can_list_templates_and_integrations():
    assert _client(templates_api.router, user=OWNER).get("/api/templates/").status_code == 200
    assert _client(integrations_api.router, user=OWNER).get("/api/integrations/available").status_code == 200


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/notifications/email-stats"),
    ("POST", "/api/notifications/publish"),
    ("POST", "/api/notifications/digest/test"),
])
def test_non_admin_user_is_403_on_admin_notification_routes(monkeypatch, method, path):
    monkeypatch.setattr("server.api.admin.settings.ADMIN_MASTER_EMAIL", OWNER.email)
    resp = _client(notifications_api.router, user=STRANGER).request(
        method, path, json={"email": "x@example.com"}
    )
    assert resp.status_code == 403


def test_admin_can_read_email_stats():
    app = FastAPI()
    app.include_router(notifications_api.router, prefix="/api")
    db = MagicMock()
    db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_platform_admin] = lambda: OWNER
    resp = TestClient(app).get("/api/notifications/email-stats")
    assert resp.status_code == 200
    assert resp.json()["total_emails"] == 0


def test_webhook_and_tracking_pixel_stay_public():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    client = _client(notifications_api.router, db=db)
    assert client.get("/api/notifications/track/abc").status_code == 200
    assert client.post("/api/notifications/resend-webhook", json={"type": "email.delivered", "data": {}}).status_code == 200
