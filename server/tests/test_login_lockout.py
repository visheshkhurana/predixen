"""Per-account failed sign-in guard (auth._refuse_if_too_many_failed_logins)."""
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api import auth


@pytest.fixture
def db():
    import server.models  # noqa: F401
    from server.models.login_history import LoginHistory
    from server.models.user import User
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(engine, tables=[User.__table__, LoginHistory.__table__])
    s = sessionmaker(bind=engine)()
    yield s, LoginHistory
    s.close()
    engine.dispose()


def _fail(s, Model, email, n, minutes_ago=1, success=False):
    for _ in range(n):
        s.add(Model(email=email, success=success, created_at=datetime.utcnow() - timedelta(minutes=minutes_ago)))
    s.commit()


def test_under_limit_is_allowed(db):
    s, M = db
    _fail(s, M, "a@example.com", auth.FAILED_LOGIN_LIMIT - 1)
    auth._refuse_if_too_many_failed_logins(s, "a@example.com")


def test_at_limit_is_429_case_insensitive(db):
    s, M = db
    _fail(s, M, "A@Example.com", auth.FAILED_LOGIN_LIMIT)
    with pytest.raises(HTTPException) as e:
        auth._refuse_if_too_many_failed_logins(s, " a@example.COM ")
    assert e.value.status_code == 429
    assert e.value.headers["Retry-After"] == "900"


def test_old_failures_and_successes_do_not_count(db):
    s, M = db
    _fail(s, M, "b@example.com", auth.FAILED_LOGIN_LIMIT, minutes_ago=20)
    _fail(s, M, "b@example.com", auth.FAILED_LOGIN_LIMIT, success=True)
    auth._refuse_if_too_many_failed_logins(s, "b@example.com")


def test_other_accounts_unaffected(db):
    s, M = db
    _fail(s, M, "victim@example.com", auth.FAILED_LOGIN_LIMIT)
    auth._refuse_if_too_many_failed_logins(s, "someone-else@example.com")
