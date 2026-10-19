"""The settings screen could turn product emails back on but never restored the
monthly digest, because neither the request model nor the client type carried
monthly_digest. An unsubscribe clears both flags, and a user with no company has
no dashboard switch, so the settings page is the only place to put it back.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api import workspace
from server.models.user import User
from server.models.workspace import NotificationPreference


@pytest.fixture
def env():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    User.metadata.create_all(
        engine, tables=[User.__table__, NotificationPreference.__table__]
    )
    db = sessionmaker(bind=engine)()
    user = User(email="founder@example.com", password_hash="x", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    # The state the unsubscribe link leaves behind: both flags cleared.
    db.add(NotificationPreference(user_id=user.id, email_enabled=False, monthly_digest=False))
    db.commit()
    yield db, user
    db.close()


def _pref(db, user_id):
    db.expire_all()
    return db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id
    ).one()


def test_reenabling_product_emails_restores_the_digest(env):
    db, user = env
    workspace.update_notification_preferences(
        workspace.NotificationSettingsRequest(email_enabled=True, monthly_digest=True),
        db,
        user,
    )

    pref = _pref(db, user.id)
    assert pref.email_enabled is True
    assert pref.monthly_digest is True, "the digest must come back with the emails"

    settings = workspace.get_notification_preferences(db=db, current_user=user)
    assert settings.monthly_digest is True


def test_digest_can_be_turned_off_without_turning_off_product_emails(env):
    db, user = env
    pref = _pref(db, user.id)
    pref.email_enabled = True
    pref.monthly_digest = True
    db.commit()

    workspace.update_notification_preferences(
        workspace.NotificationSettingsRequest(email_enabled=True, monthly_digest=False),
        db,
        user,
    )

    pref = _pref(db, user.id)
    assert pref.email_enabled is True
    assert pref.monthly_digest is False


def test_a_request_without_the_field_leaves_the_digest_alone(env):
    db, user = env
    workspace.update_notification_preferences(
        workspace.NotificationSettingsRequest(email_enabled=True),
        db,
        user,
    )

    assert _pref(db, user.id).monthly_digest is False
