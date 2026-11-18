"""Workspace invites: copyable link, and auto-accept for people who skip the link.

Tester findings (2026-11-18):
* owners could only email an invite; there was no way to copy the join link.
* an invited person who signed up directly (not via /auth?invite=…) was never
  added to the workspace.

Auto-accept matches on email alone, so it only runs for a proven address: an
email-verified account (login / verify-email) or a Google sign-in.

SQLite in memory with just the tables these paths touch; no email is sent.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.core.db import Base, get_db
from server.core.security import get_current_user, get_password_hash


@pytest.fixture()
def db():
    import server.models  # noqa: F401  (registers every mapper)
    from server.models.company import Company
    from server.models.invite import Invite
    from server.models.login_history import LoginHistory
    from server.models.user import EmailVerificationToken, RefreshToken, User
    from server.models.workspace import WorkspaceInvite, WorkspaceMember

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    tables = [
        m.__table__
        for m in (User, Company, Invite, LoginHistory, RefreshToken, EmailVerificationToken,
                  WorkspaceInvite, WorkspaceMember)
    ]
    Base.metadata.create_all(engine, tables=tables)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _client(db, router, user=None):
    app = FastAPI()
    app.include_router(router)

    def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _user(db, email, password="secret123", **kw):
    from server.models.user import User

    u = User(email=email, password_hash=get_password_hash(password) if password else None, **kw)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _company(db, owner_email="owner@acme.test"):
    from server.models.company import Company

    owner = _user(db, owner_email, is_email_verified=True)
    company = Company(name="Acme", user_id=owner.id)
    db.add(company)
    db.commit()
    return owner, company


def _invite(db, company, owner, email, role="editor", status="pending", expires_in_days=7, token=None):
    from server.models.workspace import WorkspaceInvite

    inv = WorkspaceInvite(
        company_id=company.id, email=email, role=role, invited_by=owner.id, status=status,
        token=token or f"tok-{email}-{company.id}-{role}",
        expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
    )
    db.add(inv)
    db.commit()
    return inv


def _member(db, company, user):
    from server.models.workspace import WorkspaceMember

    return db.query(WorkspaceMember).filter_by(company_id=company.id, user_id=user.id).first()


def _login(db, email, password="secret123"):
    from server.api.auth import router

    return _client(db, router).post("/auth/login", json={"email": email, "password": password})


# ---------------------------------------------------------------- auto-accept


def test_verified_login_without_link_joins_with_invited_role(db):
    owner, company = _company(db)
    inv = _invite(db, company, owner, "Invitee@Example.com", role="admin")
    u = _user(db, "invitee@example.com", is_email_verified=True)

    r = _login(db, "INVITEE@example.com")
    assert r.status_code == 200, r.text
    db.refresh(inv)
    assert inv.status == "accepted"
    m = _member(db, company, u)
    assert m is not None and m.role == "admin" and m.status == "active"
    assert m.joined_at is not None


def test_unverified_login_does_not_join(db):
    owner, company = _company(db)
    inv = _invite(db, company, owner, "squatter@example.com")
    u = _user(db, "squatter@example.com", is_email_verified=False)

    assert _login(db, "squatter@example.com").status_code == 200
    db.refresh(inv)
    assert inv.status == "pending"
    assert _member(db, company, u) is None


def test_register_then_verify_email_joins(db):
    from server.api.auth import router
    from server.models.user import EmailVerificationToken, User

    owner, company = _company(db)
    inv = _invite(db, company, owner, "newbie@example.com", role="viewer")

    with patch("server.email.service.send_email_verification", return_value=None), \
         patch("server.email.service.send_slack_signup_notification", side_effect=Exception("off")), \
         patch("server.email.onboarding_sequence.enroll_new_signup", side_effect=Exception("off")):
        r = _client(db, router).post("/auth/register", json={"email": "Newbie@Example.com", "password": "secret123"})
    assert r.status_code == 200, r.text
    u = db.query(User).filter_by(email="newbie@example.com").one()
    # Not verified yet: anyone can register any address, so nothing is granted.
    db.refresh(inv)
    assert inv.status == "pending"
    assert _member(db, company, u) is None

    token = db.query(EmailVerificationToken).filter_by(user_id=u.id).one().token
    r = _client(db, router).get(f"/auth/verify-email?token={token}")
    assert r.status_code == 200, r.text
    db.refresh(inv)
    assert inv.status == "accepted"
    m = _member(db, company, u)
    assert m is not None and m.role == "viewer" and m.status == "active"


def test_expired_and_revoked_invites_are_not_auto_accepted(db):
    owner, company = _company(db)
    expired = _invite(db, company, owner, "late@example.com", expires_in_days=-1)
    _, other = _company(db, "owner2@acme.test")
    owner2 = db.query(type(owner)).filter_by(email="owner2@acme.test").one()
    revoked = _invite(db, other, owner2, "late@example.com", status="revoked")
    u = _user(db, "late@example.com", is_email_verified=True)

    assert _login(db, "late@example.com").status_code == 200
    db.refresh(expired)
    db.refresh(revoked)
    assert expired.status == "expired"
    assert revoked.status == "revoked"
    assert _member(db, company, u) is None
    assert _member(db, other, u) is None


def test_invites_from_several_companies_all_apply(db):
    owner, company = _company(db)
    owner2, company2 = _company(db, "owner2@acme.test")
    _invite(db, company, owner, "multi@example.com", role="editor")
    _invite(db, company2, owner2, "multi@example.com", role="viewer")
    u = _user(db, "multi@example.com", is_email_verified=True)

    assert _login(db, "multi@example.com").status_code == 200
    assert _member(db, company, u).role == "editor"
    assert _member(db, company2, u).role == "viewer"


def test_platform_invites_are_not_auto_applied(db):
    from server.models.invite import Invite

    admin = _user(db, "admin@example.com", is_email_verified=True)
    inv = Invite.create_invite(email="role@example.com", role="admin", invited_by_id=admin.id)
    db.add(inv)
    db.commit()
    u = _user(db, "role@example.com", is_email_verified=True)

    assert _login(db, "role@example.com").status_code == 200
    db.refresh(inv)
    db.refresh(u)
    assert inv.accepted is False
    assert u.role != "admin"


def test_google_signup_joins(db):
    from server.api import oauth
    from server.models.user import User

    owner, company = _company(db)
    inv = _invite(db, company, owner, "gmailer@example.com", role="editor")

    token_resp = MagicMock()
    token_resp.json.return_value = {"access_token": "at"}
    profile_resp = MagicMock()
    profile_resp.json.return_value = {
        "email": "GMailer@example.com", "verified_email": True, "id": "g-1", "name": "G",
    }
    with patch.object(oauth, "_take_google_state", return_value=(True, None)), \
         patch.object(oauth, "_take_google_attribution", return_value={}), \
         patch.object(oauth.requests, "post", return_value=token_resp), \
         patch.object(oauth.requests, "get", return_value=profile_resp), \
         patch("server.email.onboarding_sequence.enroll_new_signup", return_value=None), \
         patch("server.email.service.send_slack_signup_notification", return_value=None), \
         patch("server.services.activation.emit_signup_completed", return_value=None):
        r = _client(db, oauth.router).get(
            "/auth/google/callback?code=c&state=s", follow_redirects=False
        )
    assert r.status_code == 302, r.text
    u = db.query(User).filter_by(email="gmailer@example.com").one()
    db.refresh(inv)
    assert inv.status == "accepted"
    assert _member(db, company, u).role == "editor"


# ---------------------------------------------------------------- invite link


def test_create_invite_returns_the_same_link_the_email_holds(db, monkeypatch):
    from server.api.workspace import router
    from server.email import service

    monkeypatch.setenv("APP_BASE_URL", "https://app.example.test/")
    owner, company = _company(db)
    sent = {}

    async def fake_send(**kw):
        sent.update(kw)
        return {"success": True}

    with patch.object(service, "is_email_configured", return_value=True), \
         patch.object(service, "send_invite_email", side_effect=fake_send):
        r = _client(db, router, user=owner).post(
            f"/workspace/companies/{company.id}/invite", json={"email": "mate@example.com", "role": "viewer"}
        )
    assert r.status_code == 200, r.text
    assert r.json()["invite_url"] == f"https://app.example.test/auth?invite={sent['invite_token']}"


def test_invite_list_never_exposes_the_token(db):
    from server.api.workspace import router

    owner, company = _company(db)
    inv = _invite(db, company, owner, "x@example.com")
    r = _client(db, router, user=owner).get(f"/workspace/companies/{company.id}/invites")
    assert r.status_code == 200
    assert inv.token not in r.text


def test_owner_and_admin_can_get_the_link(db, monkeypatch):
    from server.api.workspace import router
    from server.models.workspace import WorkspaceMember

    monkeypatch.setenv("APP_BASE_URL", "https://app.example.test")
    owner, company = _company(db)
    inv = _invite(db, company, owner, "x@example.com")

    r = _client(db, router, user=owner).get(f"/workspace/invites/{inv.id}/link")
    assert r.status_code == 200, r.text
    assert r.json()["invite_url"] == f"https://app.example.test/auth?invite={inv.token}"

    admin = _user(db, "admin@acme.test", is_email_verified=True)
    db.add(WorkspaceMember(company_id=company.id, user_id=admin.id, role="admin", status="active"))
    db.commit()
    assert _client(db, router, user=admin).get(f"/workspace/invites/{inv.id}/link").status_code == 200


@pytest.mark.parametrize("role", ["editor", "viewer"])
def test_editors_and_viewers_cannot_get_the_link(db, role):
    from server.api.workspace import router
    from server.models.workspace import WorkspaceMember

    owner, company = _company(db)
    inv = _invite(db, company, owner, "x@example.com")
    member = _user(db, f"{role}@acme.test", is_email_verified=True)
    db.add(WorkspaceMember(company_id=company.id, user_id=member.id, role=role, status="active"))
    db.commit()
    r = _client(db, router, user=member).get(f"/workspace/invites/{inv.id}/link")
    assert r.status_code == 403
    assert inv.token not in r.text


def test_outsiders_and_suspended_admins_cannot_get_the_link(db):
    from server.api.workspace import router
    from server.models.workspace import WorkspaceMember

    owner, company = _company(db)
    inv = _invite(db, company, owner, "x@example.com")
    stranger = _user(db, "stranger@example.com", is_email_verified=True)
    assert _client(db, router, user=stranger).get(f"/workspace/invites/{inv.id}/link").status_code == 403

    ex_admin = _user(db, "ex@acme.test", is_email_verified=True)
    db.add(WorkspaceMember(company_id=company.id, user_id=ex_admin.id, role="admin", status="suspended"))
    db.commit()
    assert _client(db, router, user=ex_admin).get(f"/workspace/invites/{inv.id}/link").status_code == 403


def test_link_for_used_expired_or_missing_invite(db):
    from server.api.workspace import router

    owner, company = _company(db)
    c = _client(db, router, user=owner)
    accepted = _invite(db, company, owner, "a@example.com", status="accepted")
    revoked = _invite(db, company, owner, "r@example.com", status="revoked")
    expired = _invite(db, company, owner, "e@example.com", expires_in_days=-1)
    assert c.get(f"/workspace/invites/{accepted.id}/link").status_code == 400
    assert c.get(f"/workspace/invites/{revoked.id}/link").status_code == 400
    assert c.get(f"/workspace/invites/{expired.id}/link").status_code == 400
    assert c.get("/workspace/invites/99999/link").status_code == 404


def test_resend_returns_the_new_link(db, monkeypatch):
    from server.api.workspace import router

    monkeypatch.setenv("APP_BASE_URL", "https://app.example.test")
    owner, company = _company(db)
    inv = _invite(db, company, owner, "x@example.com")
    old = inv.token
    r = _client(db, router, user=owner).post(f"/workspace/invites/{inv.id}/resend")
    assert r.status_code == 200
    db.refresh(inv)
    assert inv.token != old
    assert r.json()["invite_url"] == f"https://app.example.test/auth?invite={inv.token}"
