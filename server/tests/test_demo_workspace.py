"""Per-visitor demo workspaces (server/core/demo_workspace.py).

"Try the live demo" used to sign everyone into one shared account, so each
visitor saw the previous visitor's edits. Each visitor now gets a throwaway
user with a private copy of the sample company.

The pure tests run everywhere. The PostgreSQL tests build the real schema in a
scratch database and are skipped when no local PostgreSQL is reachable.
"""

import os
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from server.core.demo_workspace import (
    DEMO_EMAIL_DOMAIN,
    LEGACY_CLEANUP_MARKER,
    LEGACY_DEMO_EMAIL,
    is_demo_email,
    is_ephemeral_demo_email,
)
from server.middleware.demo_guard import is_blocked_for_demo

PG_ADMIN_URL = os.environ.get("TEST_PG_ADMIN_URL", "postgresql://localhost/postgres")
TEST_DB_NAME = "fc_demo_workspace_test"


def _pg_available() -> bool:
    try:
        engine = create_engine(PG_ADMIN_URL, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


pg_only = pytest.mark.skipif(not _pg_available(), reason="no local PostgreSQL")


# ---------------------------------------------------------------- pure

def test_demo_email_marker():
    assert is_ephemeral_demo_email(f"visitor-abc@{DEMO_EMAIL_DOMAIN}")
    assert is_demo_email(f"VISITOR-abc@{DEMO_EMAIL_DOMAIN.upper()}")
    assert is_demo_email(LEGACY_DEMO_EMAIL)
    assert not is_ephemeral_demo_email(LEGACY_DEMO_EMAIL)
    assert not is_demo_email("founder@example.com")
    assert not is_demo_email(f"x@{DEMO_EMAIL_DOMAIN}.evil.com")
    assert not is_demo_email(None)


@pytest.mark.parametrize("method,path", [
    ("GET", "/admin/users"),
    ("GET", "/api/admin/users"),
    ("POST", "/auth/admin/login"),
    ("POST", "/auth/change-password"),
    ("POST", "/workspace/companies/7/invite"),
    ("POST", "/workspace/invites/3/resend"),
    ("POST", "/api/email-templates/send-test/welcome"),
    ("POST", "/leads"),
    ("POST", "/billing/checkout"),
    ("POST", "/connectors/quickbooks/connect"),
    ("POST", "/companies/7/share-action-item"),
    ("POST", "/companies/7/scenarios/share"),
    ("POST", "/companies/7/digest/send"),
    ("POST", "/auth/send-verification"),
    ("POST", "/messaging/sms"),
])
def test_guard_blocks_admin_and_outbound(method, path):
    assert is_blocked_for_demo(method, path)


@pytest.mark.parametrize("method,path", [
    ("GET", "/companies"),
    ("GET", "/billing/plans"),
    ("POST", "/companies/7/scenarios"),
    ("POST", "/companies/7/simulate"),
    ("PATCH", "/companies/7/shareholders/2"),
    ("POST", "/companies/7/shareholders"),
    ("PUT", "/companies/7/financials/3"),
    ("POST", "/auth/logout"),
])
def test_guard_leaves_the_product_usable(method, path):
    assert not is_blocked_for_demo(method, path)


# ---------------------------------------------------------------- postgres

@pytest.fixture(scope="module")
def pg_engine():
    admin = create_engine(PG_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    admin.dispose()

    from server.core.company_purge import _load_all_models
    from server.core.db import Base

    _load_all_models()
    url = PG_ADMIN_URL.rsplit("/", 1)[0] + "/" + TEST_DB_NAME
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

    admin = create_engine(PG_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    admin.dispose()


@pytest.fixture()
def db(pg_engine):
    session = sessionmaker(bind=pg_engine)()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(autouse=True)
def _demo_env(monkeypatch):
    for k in ("DEMO_LEGACY_CLEANUP", "DEMO_LEGACY_DISABLE_LOGIN", "DEMO_LEGACY_KEEP_COMPANY_IDS"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DEMO_MAX_PER_IP_PER_HOUR", "1000")
    monkeypatch.setenv("DEMO_MAX_PER_HOUR", "1000")


def _company_ids(db, user_id):
    from server.models.company import Company
    return {c.id for c in db.query(Company).filter(Company.user_id == user_id).all()}


def _real_user(db, email=None, created_at=None, **kw):
    from server.models.user import User
    u = User(email=email or f"founder-{uuid.uuid4().hex[:8]}@example.com", password_hash="x", **kw)
    if created_at:
        u.created_at = created_at
    db.add(u)
    db.commit()
    return u


@pg_only
def test_two_demo_sessions_are_isolated(db):
    from server.core.demo_workspace import create_demo_user
    from server.models.financial import FinancialRecord

    a, ca = create_demo_user(db, ip="10.0.0.1")
    b, cb = create_demo_user(db, ip="10.0.0.2")

    assert a.id != b.id and ca.id != cb.id
    assert _company_ids(db, a.id) == {ca.id}
    assert _company_ids(db, b.id) == {cb.id}
    assert ca.name == cb.name == "TechFlow Analytics"
    # Each copy is complete on its own.
    assert db.query(FinancialRecord).filter(FinancialRecord.company_id == ca.id).count() >= 12
    assert db.query(FinancialRecord).filter(FinancialRecord.company_id == cb.id).count() >= 12

    # A visitor's edit is not visible in the other workspace.
    ca.name = "Visitor A renamed this"
    db.commit()
    db.refresh(cb)
    assert cb.name == "TechFlow Analytics"


@pg_only
def test_demo_user_has_no_privileges(db):
    from server.core.demo_workspace import create_demo_user

    u, _ = create_demo_user(db, ip="10.0.0.3")
    assert u.email.endswith("@" + DEMO_EMAIL_DOMAIN)
    assert u.role == "viewer"
    assert u.password_hash is None
    assert u.oauth_id is None
    assert u.is_email_verified is False


@pg_only
def test_per_ip_hourly_cap(db, monkeypatch):
    from server.core.demo_workspace import DemoLimitError, create_demo_user

    monkeypatch.setenv("DEMO_MAX_PER_IP_PER_HOUR", "2")
    ip = f"10.9.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"
    create_demo_user(db, ip=ip)
    create_demo_user(db, ip=ip)
    with pytest.raises(DemoLimitError):
        create_demo_user(db, ip=ip)
    create_demo_user(db, ip=ip + "0")  # another network is unaffected


@pg_only
def test_cleanup_only_removes_expired_demo_users(db):
    from server.core.demo_workspace import cleanup_expired_demo_users, create_demo_user
    from server.models.company import Company
    from server.models.user import User

    old = datetime.utcnow() - timedelta(hours=48)

    expired, expired_co = create_demo_user(db, ip="10.1.0.1")
    expired.created_at = old
    fresh, fresh_co = create_demo_user(db, ip="10.1.0.2")
    # Old real founder with a company: never touched.
    founder = _real_user(db, created_at=old)
    founder_co = Company(name="Founder Co", user_id=founder.id)
    db.add(founder_co)
    # Has the demo suffix but a password: not a throwaway, never touched.
    lookalike = _real_user(db, email=f"x-{uuid.uuid4().hex[:6]}@{DEMO_EMAIL_DOMAIN}", created_at=old)
    db.commit()
    expired_id, expired_co_id = expired.id, expired_co.id
    keep_users = [fresh.id, founder.id, lookalike.id]
    keep_cos = [fresh_co.id, founder_co.id]

    db.expunge_all()
    assert cleanup_expired_demo_users(db, older_than_hours=24) >= 1

    assert db.query(User).filter(User.id == expired_id).count() == 0
    assert db.query(Company).filter(Company.id == expired_co_id).count() == 0
    for uid in keep_users:
        assert db.query(User).filter(User.id == uid).count() == 1
    for cid in keep_cos:
        assert db.query(Company).filter(Company.id == cid).count() == 1


@pg_only
def test_legacy_cleanup_is_opt_in_scoped_and_idempotent(db, monkeypatch):
    from server.core.demo_workspace import cleanup_legacy_demo_account
    from server.models.company import Company
    from server.models.financial import FinancialRecord
    from server.models.user import User
    from server.seed.seed_demo import seed_demo_company

    legacy = db.query(User).filter(User.email == LEGACY_DEMO_EMAIL).first() or _real_user(db, email=LEGACY_DEMO_EMAIL)
    primary = seed_demo_company(db, legacy)
    dups = [Company(name="TechFlow Analytics", user_id=legacy.id) for _ in range(3)]
    visitor_made = Company(name="AlphaKids", user_id=legacy.id)
    kept = Company(name="Keep me", user_id=legacy.id)
    peer = Company(name="StackBridge", user_id=legacy.id)
    db.add_all(dups + [visitor_made, kept, peer])
    other = _real_user(db)
    other_co = Company(name="TechFlow Analytics", user_id=other.id)  # same name, other owner
    db.add(other_co)
    db.commit()
    # A visitor overwrote the baseline.
    db.query(FinancialRecord).filter(FinancialRecord.company_id == primary.id).update({"mrr": 195000})
    db.commit()
    doomed = {primary.id, visitor_made.id} | {d.id for d in dups}

    # Off by default.
    assert cleanup_legacy_demo_account(db, legacy) is False
    assert doomed <= _company_ids(db, legacy.id)

    monkeypatch.setenv("DEMO_LEGACY_CLEANUP", "true")
    monkeypatch.setenv("DEMO_LEGACY_KEEP_COMPANY_IDS", str(kept.id))
    assert cleanup_legacy_demo_account(db, legacy) is True
    db.expire_all()

    remaining = db.query(Company).filter(Company.user_id == legacy.id).all()
    ids = {c.id for c in remaining}
    assert not (doomed & ids)
    assert kept.id in ids and peer.id in ids
    rebuilt = [c for c in remaining if (c.metadata_json or {}).get(LEGACY_CLEANUP_MARKER)]
    assert len(rebuilt) == 1 and rebuilt[0].name == "TechFlow Analytics"
    mrrs = [r.mrr for r in db.query(FinancialRecord).filter(FinancialRecord.company_id == rebuilt[0].id)]
    assert mrrs and 195000 not in mrrs
    # Another user's company is untouched.
    assert db.query(Company).filter(Company.id == other_co.id).count() == 1

    # Second run: nothing to do.
    assert cleanup_legacy_demo_account(db, legacy) is False
    assert {c.id for c in db.query(Company).filter(Company.user_id == legacy.id)} == ids


@pg_only
def test_guard_middleware_rejects_demo_sessions(pg_engine, db, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import server.core.db as core_db
    from server.core.demo_workspace import create_demo_user
    from server.core.security import create_access_token
    from server.middleware.demo_guard import DemoGuardMiddleware

    monkeypatch.setattr(core_db, "SessionLocal", sessionmaker(bind=pg_engine))
    demo, _ = create_demo_user(db, ip="10.2.0.1")
    founder = _real_user(db)

    app = FastAPI()
    app.add_middleware(DemoGuardMiddleware)

    @app.post("/workspace/companies/{cid}/invite")
    def invite(cid: int):
        return {"ok": True}

    @app.post("/companies/{cid}/scenarios")
    def scenario(cid: int):
        return {"ok": True}

    client = TestClient(app)

    def hdr(u):
        return {"Authorization": "Bearer " + create_access_token({"sub": str(u.id)})}

    assert client.post("/workspace/companies/1/invite", headers=hdr(demo)).status_code == 403
    assert client.post("/companies/1/scenarios", headers=hdr(demo)).status_code == 200
    assert client.post("/workspace/companies/1/invite", headers=hdr(founder)).status_code == 200


@pg_only
def test_boot_seed_does_not_multiply_techflow(db):
    """The boot seed used to pick an arbitrary company of the legacy account,
    sometimes an Intelligence Graph peer, rename it to TechFlow, and recreate
    the peer on the next boot."""
    from server.models.company import Company
    from server.models.user import User
    from server.seed.seed_demo import seed_demo_data

    for _ in range(3):
        seed_demo_data(db)
    legacy = db.query(User).filter(User.email == LEGACY_DEMO_EMAIL).one()
    assert legacy.role == "viewer"
    names = [c.name for c in db.query(Company).filter(Company.user_id == legacy.id)]
    assert names.count("TechFlow Analytics") == 1
    assert "StackBridge" in names


@pg_only
def test_demo_endpoint_opens_separate_workspaces(pg_engine, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from server.api import auth as auth_api
    from server.core.db import get_db
    from server.models.company import Company

    Session = sessionmaker(bind=pg_engine)

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app = FastAPI()
    app.include_router(auth_api.router)
    app.dependency_overrides[get_db] = _db

    r1 = TestClient(app).post("/auth/demo", headers={"X-Forwarded-For": "10.3.0.1"})
    r2 = TestClient(app).post("/auth/demo", headers={"X-Forwarded-For": "10.3.0.2"})
    assert r1.status_code == r2.status_code == 200, (r1.text, r2.text)
    a, b = r1.json(), r2.json()
    assert a["is_demo"] and b["is_demo"] and not a["is_platform_admin"]
    assert a["user_id"] != b["user_id"]
    assert a["email"].endswith("@" + DEMO_EMAIL_DOMAIN)
    assert "auth_token" in r1.cookies

    s = Session()
    try:
        ca = {c.id for c in s.query(Company).filter(Company.user_id == a["user_id"])}
        cb = {c.id for c in s.query(Company).filter(Company.user_id == b["user_id"])}
        assert len(ca) == len(cb) == 1 and not (ca & cb)
    finally:
        s.close()

    monkeypatch.setenv("DEMO_MAX_PER_IP_PER_HOUR", "1")
    r3 = TestClient(app).post("/auth/demo", headers={"X-Forwarded-For": "10.3.0.1"})
    assert r3.status_code == 429

