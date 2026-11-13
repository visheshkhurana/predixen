"""Audit 10-19: tenant checks, share-link lifecycle, announcement unsubscribe.

Covers:
- /connectors/catalog?company_id= requires access to that company
- /simulation/v2/{id} is owner-scoped and the store is bounded
- agent-sim runs get no public link until shared; links can be revoked/expire
- shared scenarios can expire and be revoked by the owner only
- a company-level "admin" role is not cross-company access
- the in-memory /export/share links are gone
- announcement mail carries a per-user unsubscribe token and honours opt-out
"""
from __future__ import annotations

import asyncio
import inspect
import json
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.core.db import Base, get_db
from server.core.security import get_current_user, MasterUser
from server.models.agent_simulation import AgentSimulationRun
from server.models.company import Company
from server.models.shared_scenario import SharedScenario
from server.models.user import User
from server.models.workspace import NotificationPreference, WorkspaceMember


@pytest.fixture()
def db_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            Company.__table__,
            WorkspaceMember.__table__,
            AgentSimulationRun.__table__,
            SharedScenario.__table__,
            NotificationPreference.__table__,
        ],
    )
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def _user(db, uid, email, role="viewer", verified=True):
    u = User(id=uid, email=email, password_hash="x", role=role, is_email_verified=verified)
    db.add(u)
    db.commit()
    u.is_platform_admin = False
    u._is_master_user = False
    return u


def _company(db, cid, owner_id):
    c = Company(id=cid, user_id=owner_id, name=f"Co{cid}", metadata_json={
        "connectors": {"stripe": {"connected": True, "records_synced": 7}}
    })
    db.add(c)
    db.commit()
    return c


def _client(router, db_factory, user_holder):
    app = FastAPI()
    app.include_router(router)

    def _db():
        db = db_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: user_holder["user"]
    return TestClient(app)


# ---------------------------------------------------------------- 4. access


def test_company_admin_role_is_not_cross_company_access(db_factory, monkeypatch):
    from server.core import company_access
    from server.core.config import settings

    monkeypatch.setattr(settings, "ADMIN_MASTER_EMAIL", "owner@platform.test")
    db = db_factory()
    _user(db, 1, "a@x.test")
    _company(db, 10, 1)
    other_admin = _user(db, 2, "b@x.test", role="admin")

    with pytest.raises(HTTPException) as exc:
        company_access.get_user_company(db, 10, other_admin)
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException):
        company_access.get_user_company_role(db, 10, other_admin)

    assert company_access.get_user_company(db, 10, MasterUser()).id == 10

    platform = _user(db, 3, "owner@platform.test", verified=True)
    assert company_access.get_user_company(db, 10, platform).id == 10

    unverified = _user(db, 4, "OWNER@platform.test ", verified=False)
    with pytest.raises(HTTPException):
        company_access.get_user_company(db, 10, unverified)


# ---------------------------------------------------------------- 1. catalog


def test_connector_catalog_requires_company_access(db_factory):
    from server.api.connectors import router

    db = db_factory()
    owner = _user(db, 1, "a@x.test")
    stranger = _user(db, 2, "b@x.test")
    _company(db, 10, 1)
    holder = {"user": stranger}
    client = _client(router, db_factory, holder)

    assert client.get("/connectors/catalog").status_code == 200
    assert client.get("/connectors/catalog?company_id=10").status_code == 403
    assert client.get("/connectors/catalog?company_id=999").status_code == 404

    holder["user"] = owner
    res = client.get("/connectors/catalog?company_id=10")
    assert res.status_code == 200
    stripe = [c for c in res.json() if c["id"] == "stripe"]
    if stripe:
        assert stripe[0]["installStatus"]["record_count"] == 7


# ---------------------------------------------------------------- 2. sim v2


def test_simulation_v2_store_is_owner_scoped_and_bounded():
    from server.api import simulation_v2

    store = simulation_v2._ResultStore(max_items=3, ttl_seconds=3600)
    for i in range(5):
        store.put(f"s{i}", 1, {"i": i})
    assert len(store) == 3
    assert store.get("s0", 1) is None
    assert store.get("s4", 1) == {"i": 4}
    assert store.get("s4", 2) is None

    expiring = simulation_v2._ResultStore(max_items=10, ttl_seconds=0)
    expiring.put("x", 1, {})
    assert expiring.get("x", 1) is None


def test_simulation_v2_get_hides_other_users_results(monkeypatch):
    from server.api import simulation_v2

    store = simulation_v2._ResultStore()
    store.put("abc", 1, {"ok": True})
    monkeypatch.setattr(simulation_v2, "_results_store", store)

    class U:
        def __init__(self, uid):
            self.id = uid

    assert asyncio.run(simulation_v2.get_simulation_v2_result("abc", U(1))) == {"ok": True}
    with pytest.raises(HTTPException) as exc:
        asyncio.run(simulation_v2.get_simulation_v2_result("abc", U(2)))
    assert exc.value.status_code == 404


# ---------------------------------------------------------------- 3. shares


def test_agent_run_has_no_public_link_until_shared(db_factory):
    from server.api import agent_simulation

    src = inspect.getsource(agent_simulation.run_simulation)
    assert "token_urlsafe" not in src

    db = db_factory()
    owner = _user(db, 1, "a@x.test")
    viewer = _user(db, 2, "v@x.test")
    stranger = _user(db, 3, "s@x.test")
    _company(db, 10, 1)
    db.add(WorkspaceMember(company_id=10, user_id=2, role="viewer", status="active"))
    run = AgentSimulationRun(company_id=10, results_json=json.dumps({"summary": {"x": 1}}))
    db.add(run)
    db.commit()
    run_id = run.id
    db.close()

    holder = {"user": owner}
    client = _client(agent_simulation.router, db_factory, holder)
    share_url = f"/companies/10/simulation/agent-run/{run_id}/share"

    holder["user"] = viewer
    assert client.post(share_url, json={}).status_code == 403
    holder["user"] = stranger
    assert client.post(share_url, json={}).status_code == 403

    holder["user"] = owner
    res = client.post(share_url, json={})
    assert res.status_code == 200
    token = res.json()["shareToken"]
    assert res.json()["expiresAt"] is None
    assert client.get(f"/simulation/shared/{token}").status_code == 200

    assert client.delete(share_url).status_code == 200
    assert client.get(f"/simulation/shared/{token}").status_code == 404

    res = client.post(share_url, json={"expires_in_days": 7})
    token = res.json()["shareToken"]
    assert res.json()["expiresAt"]
    assert client.get(f"/simulation/shared/{token}").status_code == 200

    db = db_factory()
    row = db.query(AgentSimulationRun).get(run_id)
    data = json.loads(row.results_json)
    data["shareExpiresAt"] = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
    row.results_json = json.dumps(data)
    db.commit()
    db.close()
    assert client.get(f"/simulation/shared/{token}").status_code == 404


def test_shared_scenario_expiry_and_owner_revoke(db_factory):
    from server.api import shared_scenarios

    db = db_factory()
    owner = _user(db, 1, "a@x.test")
    stranger = _user(db, 2, "b@x.test")
    _company(db, 10, 1)
    db.close()

    holder = {"user": owner}
    client = _client(shared_scenarios.router, db_factory, holder)
    body = {"scenario_name": "Base", "simulation_data": {"runway": 12}}

    res = client.post("/companies/10/scenarios/share", json=body)
    assert res.status_code == 200
    uuid = res.json()["uuid"]
    got = client.get(f"/scenarios/shared/{uuid}").json()
    assert got["simulation_data"] == {"runway": 12}
    assert got["expires_at"] is None

    holder["user"] = stranger
    assert client.delete(f"/companies/10/scenarios/shared/{uuid}").status_code == 404
    holder["user"] = owner
    assert client.delete(f"/companies/10/scenarios/shared/{uuid}").status_code == 200
    assert client.get(f"/scenarios/shared/{uuid}").status_code == 404

    res = client.post("/companies/10/scenarios/share", json={**body, "expires_in_days": 3})
    uuid = res.json()["uuid"]
    got = client.get(f"/scenarios/shared/{uuid}").json()
    assert "__share" not in got["simulation_data"]
    assert got["expires_at"]

    db = db_factory()
    row = db.query(SharedScenario).filter(SharedScenario.uuid == uuid).first()
    row.simulation_data = {
        **row.simulation_data,
        "__share": {"expiresAt": (datetime.utcnow() - timedelta(seconds=1)).isoformat()},
    }
    db.commit()
    db.close()
    assert client.get(f"/scenarios/shared/{uuid}").status_code == 404


# ---------------------------------------------------------------- 5. export


def test_in_memory_export_share_links_removed():
    from server.api import export

    paths = {getattr(r, "path", "") for r in export.router.routes}
    assert not any("/share" in p for p in paths)
    assert "replit.app" not in inspect.getsource(export)


# ---------------------------------------------------------------- 6. email


def test_footer_default_has_no_tokenless_unsubscribe_link():
    from server.email.templates import get_footer_html, render_platform_update_template

    assert "/unsubscribe\"" not in get_footer_html()
    html = render_platform_update_template(updates=[{"title": "T", "description": "D"}], app_url="https://x")
    assert "/unsubscribe\"" not in html


def test_prepare_bulk_send_stamps_token_and_honours_opt_out(db_factory):
    from server.email.lifecycle_guard import prepare_bulk_send, verify_unsubscribe_token
    from server.email.templates import render_platform_update_template

    db = db_factory()
    _user(db, 1, "a@x.test")
    _user(db, 2, "out@x.test")
    db.add(NotificationPreference(user_id=2, email_enabled=False))
    db.commit()

    html = render_platform_update_template(updates=[{"title": "T", "description": "D"}], app_url="https://x")

    prepared = prepare_bulk_send(db, "A@x.test", html, "hello")
    assert prepared is not None
    assert "#unsubscribe" not in prepared.html
    assert "/unsubscribe?token=" in prepared.html
    token = prepared.html.split("/unsubscribe?token=")[1].split('"')[0]
    assert verify_unsubscribe_token(token) == 1
    assert prepared.headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert "/unsubscribe?token=" in prepared.text

    assert prepare_bulk_send(db, "out@x.test", html) is None

    unknown = prepare_bulk_send(db, "nobody@x.test", html)
    assert unknown is not None and unknown.html == html and unknown.headers == {}


def test_platform_update_senders_use_per_recipient_prep():
    from server.services import notifications
    from server.email import service

    for fn in (notifications.send_platform_update, notifications.send_hybrid_feature_announcement):
        src = inspect.getsource(fn)
        assert "_personalize_announcement" in src
        assert '"html": html_content' not in src
    assert "prepare_bulk_send" in inspect.getsource(service.send_platform_update_email)
