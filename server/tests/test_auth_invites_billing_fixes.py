"""Auth, invite and billing fixes (audit 2026-10-18).

* /auth/login and /auth/admin/login matched User.email exactly, but register
  stores lowercase, so "Founder@X.com" could sign up and then never log in.
* settings posted to /auth/change-password, which did not exist.
* invite links (/auth?invite=…) were never accepted; workspace invites sent no
  email.
* /billing/subscribe/{plan} always opened a new Checkout, so a paying user
  who switched plan ended up with two live subscriptions.

SQLite in memory with just the tables these paths touch; Stripe is mocked.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.core.db import Base, get_db
from server.core.security import get_current_user, get_password_hash, verify_password


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


# ---------------------------------------------------------------- login case


def test_login_ignores_email_case_and_whitespace(db):
    from server.api.auth import router

    _user(db, "founder@example.com")
    r = _client(db, router).post("/auth/login", json={"email": "Founder@Example.COM", "password": "secret123"})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "founder@example.com"


def test_login_finds_legacy_mixed_case_rows(db):
    from server.api.auth import router

    _user(db, "Legacy@Example.com")
    r = _client(db, router).post("/auth/login", json={"email": "legacy@example.com", "password": "secret123"})
    assert r.status_code == 200, r.text


def test_oauth_only_account_gets_401_not_500(db):
    from server.api.auth import router

    _user(db, "google@example.com", password=None)
    r = _client(db, router).post("/auth/login", json={"email": "google@example.com", "password": "whatever1"})
    assert r.status_code == 401


def test_admin_login_ignores_email_case(db):
    from server.api.auth import router
    from server.core.config import settings

    _user(db, "owner@example.com")
    with patch.object(settings, "ADMIN_MASTER_EMAIL", "owner@example.com"), \
         patch.object(settings, "ADMIN_MASTER_PASSWORD_HASH", None):
        r = _client(db, router).post("/auth/admin/login", json={"email": "OWNER@example.com", "password": "secret123"})
    assert r.status_code == 200, r.text


# ----------------------------------------------------------- change password


def test_change_password_requires_the_current_password(db):
    from server.api.auth import router

    u = _user(db, "a@example.com")
    c = _client(db, router, user=u)
    r = c.post("/auth/change-password", json={"current_password": "wrong", "new_password": "newpass99"})
    assert r.status_code == 400
    assert "incorrect" in r.json()["detail"].lower()

    r = c.post("/auth/change-password", json={"current_password": "secret123", "new_password": "newpass99"})
    assert r.status_code == 200, r.text
    db.refresh(u)
    assert verify_password("newpass99", u.password_hash)


def test_change_password_enforces_register_strength(db):
    from server.api.auth import router

    u = _user(db, "b@example.com")
    c = _client(db, router, user=u)
    assert c.post("/auth/change-password", json={"current_password": "secret123", "new_password": "short1"}).status_code == 422
    assert c.post("/auth/change-password", json={"current_password": "secret123", "new_password": "nonumbers"}).status_code == 422


def test_change_password_needs_a_session(db):
    from server.api.auth import router

    r = _client(db, router).post("/auth/change-password", json={"current_password": "x", "new_password": "newpass99"})
    assert r.status_code == 401


def test_change_password_for_google_only_account_explains(db):
    from server.api.auth import router

    u = _user(db, "g@example.com", password=None)
    r = _client(db, router, user=u).post(
        "/auth/change-password", json={"current_password": "", "new_password": "newpass99"}
    )
    assert r.status_code == 400
    assert "google" in r.json()["detail"].lower()


# ------------------------------------------------------------------- invites


def _workspace_invite(db, email, role="editor", **kw):
    from server.models.company import Company
    from server.models.workspace import WorkspaceInvite

    owner = _user(db, f"owner-{email}")
    company = Company(name="Acme", user_id=owner.id)
    db.add(company)
    db.commit()
    inv = WorkspaceInvite(
        company_id=company.id, email=email, role=role, invited_by=owner.id,
        token=f"tok-{email}", expires_at=kw.pop("expires_at", datetime.utcnow() + timedelta(days=7)), **kw
    )
    db.add(inv)
    db.commit()
    return company, inv


def test_login_with_invite_token_joins_the_workspace(db):
    from server.api.auth import router
    from server.models.workspace import WorkspaceMember

    u = _user(db, "invitee@example.com")
    company, inv = _workspace_invite(db, "invitee@example.com")
    r = _client(db, router).post(
        "/auth/login", json={"email": "invitee@example.com", "password": "secret123", "invite": inv.token}
    )
    assert r.status_code == 200, r.text
    db.refresh(inv)
    assert inv.status == "accepted"
    m = db.query(WorkspaceMember).filter_by(company_id=company.id, user_id=u.id).one()
    assert m.role == "editor" and m.status == "active" and m.joined_at is not None


def test_invite_for_another_email_is_not_applied_and_login_still_works(db):
    from server.api.auth import router
    from server.models.workspace import WorkspaceMember

    _user(db, "mallory@example.com")
    _, inv = _workspace_invite(db, "alice@example.com")
    r = _client(db, router).post(
        "/auth/login", json={"email": "mallory@example.com", "password": "secret123", "invite": inv.token}
    )
    assert r.status_code == 200
    db.refresh(inv)
    assert inv.status == "pending"
    assert db.query(WorkspaceMember).count() == 0


def test_expired_invite_is_rejected_by_accept_endpoint(db):
    from server.api.workspace import router

    u = _user(db, "late@example.com")
    _, inv = _workspace_invite(db, "late@example.com", expires_at=datetime.utcnow() - timedelta(days=1))
    r = _client(db, router, user=u).post("/workspace/invites/accept", json={"token": inv.token})
    assert r.status_code == 400
    db.refresh(inv)
    assert inv.status == "expired"


def test_accept_endpoint_for_signed_in_user(db):
    from server.api.workspace import router

    u = _user(db, "Signed@Example.com")
    company, inv = _workspace_invite(db, "signed@example.com", role="viewer")
    c = _client(db, router, user=u)
    r = c.post("/workspace/invites/accept", json={"token": inv.token})
    assert r.status_code == 200, r.text
    assert r.json()["company_id"] == company.id
    # Single use.
    assert c.post("/workspace/invites/accept", json={"token": inv.token}).status_code == 400


def test_register_with_admin_invite_takes_the_invited_role(db):
    from server.api.auth import router
    from server.models.invite import Invite

    admin = _user(db, "admin@example.com")
    inv = Invite.create_invite(email="new@example.com", role="analyst", invited_by_id=admin.id)
    db.add(inv)
    db.commit()
    with patch("server.email.service.send_email_verification", return_value=None), \
         patch("server.email.service.send_slack_signup_notification", side_effect=Exception("off")), \
         patch("server.email.onboarding_sequence.enroll_new_signup", side_effect=Exception("off")):
        r = _client(db, router).post(
            "/auth/register", json={"email": "New@Example.com", "password": "secret123", "invite": inv.token}
        )
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "analyst"
    db.refresh(inv)
    assert inv.accepted is True


def test_workspace_invite_sends_the_join_email(db):
    from server.api.workspace import router
    from server.models.company import Company

    owner = _user(db, "boss@example.com")
    company = Company(name="Acme", user_id=owner.id)
    db.add(company)
    db.commit()

    sent = {}

    async def fake_send(**kw):
        sent.update(kw)
        return {"success": True}

    with patch("server.email.service.is_email_configured", return_value=True), \
         patch("server.email.service.send_invite_email", side_effect=fake_send):
        r = _client(db, router, user=owner).post(
            f"/workspace/companies/{company.id}/invite", json={"email": "Teammate@Example.com", "role": "editor"}
        )
    assert r.status_code == 200, r.text
    assert r.json()["email_sent"] is True
    assert sent["to_email"] == "teammate@example.com"
    assert sent["early_access"] is False
    assert sent["invite_token"]


# ------------------------------------------------------------------- billing


def _billing_client(db, user):
    from server.api.billing import router

    return _client(db, router, user=user)


LIVE_SUB = {
    "id": "sub_1",
    "customer": "cus_1",
    "status": "active",
    "items": {"data": [{"id": "si_1", "price": {"id": "price_starter", "unit_amount": 2900, "recurring": {"interval": "month"}}}]},
}


def test_subscribe_with_a_live_subscription_modifies_it_instead_of_checkout(db):
    u = _user(db, "payer@example.com")
    updated = {**LIVE_SUB, "metadata": {"fc_plan": "growth"}}
    with patch("server.core.stripe_billing.stripe_enabled", return_value=True), \
         patch("server.core.stripe_billing.find_live_subscription", return_value=LIVE_SUB), \
         patch("server.core.stripe_billing.change_subscription_plan", return_value=updated) as change, \
         patch("server.core.stripe_billing.create_checkout_session") as checkout, \
         patch("server.api.billing._upsert_subscription_from_stripe") as upsert:
        r = _billing_client(db, u).post("/billing/subscribe/growth", json={"interval": "monthly"})
    assert r.status_code == 200, r.text
    assert r.json()["changed"] is True
    assert "checkout_url" not in r.json()
    checkout.assert_not_called()
    change.assert_called_once_with(LIVE_SUB, u.id, "growth", "monthly")
    upsert.assert_called_once_with(db, u.id, updated, "growth")


def test_subscribe_without_a_subscription_opens_checkout(db):
    u = _user(db, "newpayer@example.com")
    with patch("server.core.stripe_billing.stripe_enabled", return_value=True), \
         patch("server.core.stripe_billing.find_live_subscription", return_value=None), \
         patch("server.core.stripe_billing.create_checkout_session", return_value="https://checkout/x") as checkout:
        r = _billing_client(db, u).post("/billing/subscribe/starter", json={"interval": "monthly"})
    assert r.status_code == 200, r.text
    assert r.json()["checkout_url"] == "https://checkout/x"
    checkout.assert_called_once()


@pytest.mark.parametrize("plan,status", [("free", "active"), ("growth", "past_due")])
def test_downgrade_to_free_or_past_due_goes_to_the_portal(db, plan, status):
    u = _user(db, f"{plan}-{status}@example.com")
    with patch("server.core.stripe_billing.stripe_enabled", return_value=True), \
         patch("server.core.stripe_billing.find_live_subscription", return_value={**LIVE_SUB, "status": status}), \
         patch("server.core.stripe_billing.create_portal_session", return_value="https://portal/x") as portal, \
         patch("server.core.stripe_billing.change_subscription_plan") as change, \
         patch("server.core.stripe_billing.create_checkout_session") as checkout:
        r = _billing_client(db, u).post(f"/billing/subscribe/{plan}", json={"interval": "monthly"})
    assert r.status_code == 200, r.text
    assert r.json()["portal_url"] == "https://portal/x"
    portal.assert_called_once_with("cus_1")
    change.assert_not_called()
    checkout.assert_not_called()


def test_change_subscription_plan_prorates_and_retags_metadata():
    from server.core import stripe_billing

    with patch.object(stripe_billing, "ensure_price", return_value="price_growth"), \
         patch.object(stripe_billing.stripe.Subscription, "modify", return_value={"id": "sub_1"}) as modify:
        stripe_billing.change_subscription_plan(LIVE_SUB, 7, "growth", "monthly")
    modify.assert_called_once_with(
        "sub_1",
        items=[{"id": "si_1", "price": "price_growth"}],
        proration_behavior="create_prorations",
        cancel_at_period_end=False,
        metadata={"fc_user_id": "7", "fc_plan": "growth"},
    )


def test_change_subscription_plan_is_a_noop_on_the_same_price():
    from server.core import stripe_billing

    with patch.object(stripe_billing, "ensure_price", return_value="price_starter"), \
         patch.object(stripe_billing.stripe.Subscription, "modify") as modify:
        assert stripe_billing.change_subscription_plan(LIVE_SUB, 7, "starter") is LIVE_SUB
    modify.assert_not_called()
