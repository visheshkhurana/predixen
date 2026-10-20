"""Audit 2026-10-15: logout, password reset and suspension did not end sessions.

revoke_token() was never called and its set lived in one process's memory, so
an access token kept working for its full lifetime after logout or a password
reset, and get_current_user never looked at is_active. These tests run the
real dependency against SQLite.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api import auth as auth_api
from server.api import oauth as oauth_api
from server.core import security
from server.core.config import settings
from server.core.db import get_db
from server.models.session_revocation import RevokedAccessToken, UserSessionCutoff
from server.models.user import PasswordResetToken, RefreshToken, User


@pytest.fixture
def env():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    tables = [User.__table__, RefreshToken.__table__, PasswordResetToken.__table__,
              RevokedAccessToken.__table__, UserSessionCutoff.__table__]
    User.metadata.create_all(engine, tables=tables)
    Session = sessionmaker(bind=engine)
    db = Session()
    user = User(email="founder@example.com", password_hash=security.get_password_hash("old-pass-123"),
                is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    app = FastAPI()
    app.include_router(auth_api.router, prefix="/api")

    @app.get("/api/me")
    def me(current=Depends(security.get_current_user)):
        return {"id": current.id}

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    security._revoked_tokens.clear()
    yield TestClient(app), Session, user.id
    security._revoked_tokens.clear()


def _token(user_id: int, issued_seconds_ago: int = 0) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now - timedelta(seconds=issued_seconds_ago),
            "exp": now + timedelta(hours=1),
            "jti": f"jti-{user_id}-{issued_seconds_ago}",
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def _me(client, token):
    return client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).status_code


def test_logout_revokes_the_access_token_even_after_a_restart(env):
    client, Session, uid = env
    token = _token(uid)
    assert _me(client, token) == 200

    resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert _me(client, token) == 401

    security._revoked_tokens.clear()  # new process / other replica
    assert _me(client, token) == 401, "revocation must survive a restart"


def test_logout_only_ends_that_session(env):
    client, _, uid = env
    phone, laptop = _token(uid, 5), _token(uid, 6)
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {phone}"})
    assert _me(client, phone) == 401
    assert _me(client, laptop) == 200


def test_password_reset_ends_every_existing_session(env):
    client, Session, uid = env
    stolen = _token(uid, issued_seconds_ago=30)
    db = Session()
    db.add(RefreshToken(user_id=uid, token="rt-1", expires_at=datetime.utcnow() + timedelta(days=7)))
    db.add(PasswordResetToken(user_id=uid, token="reset-1", expires_at=datetime.utcnow() + timedelta(hours=1)))
    db.commit()
    db.close()
    assert _me(client, stolen) == 200

    resp = client.post("/api/auth/reset-password", json={"token": "reset-1", "new_password": "N3w-pass-456!"})
    assert resp.status_code == 200, resp.text
    assert _me(client, stolen) == 401

    db = Session()
    assert db.query(RefreshToken).filter(RefreshToken.token == "rt-1").one().revoked is True
    db.close()

    fresh = _token(uid)  # the next login
    assert _me(client, fresh) == 200


def test_oauth_password_clear_rejects_the_old_access_token(env):
    """Linking Google onto an unverified password account is a password change.

    The access token minted from the planted password must fail afterwards.
    Refresh-token revocation alone left that JWT valid until it expired.
    """
    client, Session, uid = env
    stolen = _token(uid, issued_seconds_ago=30)
    assert _me(client, stolen) == 200

    db = Session()
    user = db.query(User).filter(User.id == uid).one()
    user.is_email_verified = False
    user.oauth_provider = None
    user.password_hash = security.get_password_hash("planted-pass-1")
    db.commit()
    email = user.email
    db.close()

    db = Session()
    # example.com is an internal domain; this test is about session revocation.
    with patch("server.services.posthog.urllib.request.urlopen"):
        linked = oauth_api._get_or_create_oauth_user(db, email, "google", "g-reclaim")
    assert linked.password_hash is None
    db.close()

    assert _me(client, stolen) == 401
    fresh = _token(uid)
    assert _me(client, fresh) == 200


def test_suspended_user_is_rejected_immediately(env):
    client, Session, uid = env
    token = _token(uid)
    assert _me(client, token) == 200
    db = Session()
    db.query(User).filter(User.id == uid).update({User.is_active: False})
    security.revoke_all_sessions(db, uid)
    db.commit()
    db.close()
    assert _me(client, token) == 401


def test_admin_suspend_routes_end_sessions():
    src = open("server/api/admin.py").read()
    assert src.count("user.is_active = False\n    revoke_all_sessions(db, user.id)") == 2


def test_a_missing_revocation_table_is_revocation_off_not_a_500(env):
    """HAG-456: the tables are created in _run_deferred_startup, so a deploy serves
    authenticated requests before they exist.

    Before this test's fix, get_current_user queried revoked_access_tokens
    unguarded and every authenticated request 500'd for the length of the deploy
    window. A missing revocation table must mean "revocation is off", never an
    error: the alternative trades a hardening gap measured in seconds for a total
    outage of every authenticated route.
    """
    client, Session, uid = env
    token = _token(uid)

    db = Session()
    engine = db.get_bind()
    db.close()
    with engine.begin() as conn:
        RevokedAccessToken.__table__.drop(conn)
        UserSessionCutoff.__table__.drop(conn)

    security._revoked_tokens.clear()  # nothing cached from this process

    resp = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"id": uid}
