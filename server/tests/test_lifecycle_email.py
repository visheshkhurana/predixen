"""Lifecycle unsubscribe and the per-user send cap.

Opt-out lives on NotificationPreference. The send choke point is
deliver_lifecycle_email. Onboarding still claims a row before send, and a
cap or opt-out skip releases that claim instead of burning the step.
"""
from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api.email_unsubscribe import router as unsubscribe_router
from server.core.db import Base, get_db
from server.email.lifecycle_guard import (
    apply_unsubscribe,
    decide,
    one_click_unsubscribe_url,
    sign_unsubscribe_token,
    verify_unsubscribe_token,
)
from server.email.onboarding_sequence import CLAIM_SQL, SEQUENCE, _send_step
from server.email.service import (
    deliver_lifecycle_email,
    send_email_verification,
    send_password_reset_email,
)
from server.email.templates import render_simulation_report_template
from server.models.email_event import LifecycleEmailLog
from server.models.user import User
from server.models.workspace import NotificationPreference


def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _now(dbapi_conn, _rec):
        dbapi_conn.create_function(
            "now", 0, lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        )

    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            NotificationPreference.__table__,
            LifecycleEmailLog.__table__,
        ],
    )
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS onboarding_email_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                step_key VARCHAR(50) NOT NULL,
                sent_at TIMESTAMP,
                success BOOLEAN,
                error TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, step_key)
            )
        """))
    return engine


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv("LIFECYCLE_EMAIL_GUARD", "on")
    monkeypatch.setenv("LIFECYCLE_EMAIL_MAX_PER_24H", "2")
    monkeypatch.setenv("LIFECYCLE_EMAIL_MAX_PER_7D", "5")
    engine = _engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _user(db, email: str) -> User:
    user = User(email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _sent(db, user_id: int, when: datetime, n: int = 1) -> None:
    for _ in range(n):
        db.add(
            LifecycleEmailLog(
                user_id=user_id,
                kind="activity",
                campaign="activity_simulation",
                status="sent",
                created_at=when,
            )
        )
    db.commit()


def test_decide_opt_out_and_cap_boundaries():
    blocked = decide(opted_out=True, sends_24h=0, sends_7d=0, enabled=True, max_24h=2, max_7d=5)
    assert blocked.allow is False and blocked.reason == "opted_out"

    at_day = decide(opted_out=False, sends_24h=2, sends_7d=2, enabled=True, max_24h=2, max_7d=5)
    assert at_day.allow is False and at_day.reason == "capped"

    at_week = decide(opted_out=False, sends_24h=0, sends_7d=5, enabled=True, max_24h=2, max_7d=5)
    assert at_week.allow is False and at_week.reason == "capped"

    under = decide(opted_out=False, sends_24h=1, sends_7d=4, enabled=True, max_24h=2, max_7d=5)
    assert under.allow is True and under.reason == "ok"

    killed = decide(opted_out=True, sends_24h=9, sends_7d=9, enabled=False, max_24h=2, max_7d=5)
    assert killed.allow is True and killed.reason == "guard_disabled"


def test_forged_or_retargeted_token_does_not_verify():
    token = sign_unsubscribe_token(7)
    assert verify_unsubscribe_token(token) == 7
    assert verify_unsubscribe_token("") is None
    assert verify_unsubscribe_token("not-a-token") is None

    forged = token[:-1] + ("A" if token[-1] != "A" else "B")
    assert verify_unsubscribe_token(forged) is None

    padded = token + ("=" * (-len(token) % 4))
    user_part, sig = base64.urlsafe_b64decode(padded).decode("ascii").split(".", 1)
    assert user_part == "7"
    swapped = base64.urlsafe_b64encode(f"8.{sig}".encode("ascii")).decode("ascii").rstrip("=")
    assert verify_unsubscribe_token(swapped) is None
    assert verify_unsubscribe_token(token) == 7


def test_opted_out_lifecycle_does_not_send(db, monkeypatch):
    user = _user(db, "ada@example.com")
    db.add(NotificationPreference(user_id=user.id, email_enabled=False, monthly_digest=False))
    db.commit()
    calls = []

    def fake_send(*args, **kwargs):
        calls.append(kwargs)
        return {"success": True, "message_id": "should-not-send"}

    monkeypatch.setattr("server.email.service._send_email_sync", fake_send)
    result = deliver_lifecycle_email(
        "ada@example.com",
        "Your simulation",
        "<p>hi</p>",
        kind="activity",
        campaign="activity_simulation",
        user_id=user.id,
        db=db,
    )
    assert result["skipped"] is True
    assert result["reason"] == "opted_out"
    assert calls == []
    skip = db.query(LifecycleEmailLog).filter(LifecycleEmailLog.user_id == user.id).one()
    assert skip.status == "skipped_opted_out"


def test_cap_blocks_the_next_lifecycle_send_and_ignores_old_mail(db, monkeypatch):
    user = _user(db, "ada@example.com")
    _sent(db, user.id, datetime.utcnow() - timedelta(days=8), n=5)
    calls = []

    def fake_send(*args, **kwargs):
        calls.append(kwargs)
        return {"success": True, "message_id": "m"}

    monkeypatch.setattr("server.email.service._send_email_sync", fake_send)
    allowed = deliver_lifecycle_email(
        "ada@example.com",
        "Digest",
        "<p>old window</p>",
        kind="digest",
        campaign="monthly_digest",
        user_id=user.id,
        db=db,
    )
    assert allowed["success"] is True
    assert len(calls) == 1
    headers = calls[0]["headers"]
    assert headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert headers["List-Unsubscribe"] == f"<{one_click_unsubscribe_url(user.id)}>"
    assert "/api/email/unsubscribe?token=" in headers["List-Unsubscribe"]

    _sent(db, user.id, datetime.utcnow() - timedelta(hours=1), n=1)
    blocked = deliver_lifecycle_email(
        "ada@example.com",
        "Another",
        "<p>cap</p>",
        kind="activity",
        campaign="activity_simulation",
        user_id=user.id,
        db=db,
    )
    assert blocked["skipped"] is True
    assert blocked["reason"] == "capped"
    assert len(calls) == 1


def test_week_cap_blocks_even_when_the_day_window_is_clear(db, monkeypatch):
    user = _user(db, "bea@example.com")
    _sent(db, user.id, datetime.utcnow() - timedelta(days=3), n=5)

    def fake_send(*args, **kwargs):
        raise AssertionError("resend")

    monkeypatch.setattr("server.email.service._send_email_sync", fake_send)
    result = deliver_lifecycle_email(
        "bea@example.com",
        "Step",
        "<p>x</p>",
        kind="onboarding",
        campaign="onboarding_welcome",
        user_id=user.id,
        db=db,
    )
    assert result["reason"] == "capped"


def test_kill_switch_lets_opted_out_mail_through(db, monkeypatch):
    monkeypatch.setenv("LIFECYCLE_EMAIL_GUARD", "off")
    user = _user(db, "cy@example.com")
    db.add(NotificationPreference(user_id=user.id, email_enabled=False))
    db.commit()
    calls = []
    monkeypatch.setattr(
        "server.email.service._send_email_sync",
        lambda *a, **k: calls.append(k) or {"success": True, "message_id": "m"},
    )
    result = deliver_lifecycle_email(
        "cy@example.com",
        "Hi",
        "<p>x</p>",
        kind="digest",
        campaign="monthly_digest",
        user_id=user.id,
        db=db,
    )
    assert result["success"] is True
    assert len(calls) == 1


def test_transactional_mail_stays_outside_the_choke_point(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("transactional mail entered the lifecycle choke point")

    monkeypatch.setattr("server.email.service.deliver_lifecycle_email", boom)
    sent = []
    monkeypatch.setattr(
        "server.email.service._send_email_sync",
        lambda *a, **k: sent.append(a[1]) or {"success": True, "message_id": "t"},
    )
    asyncio.run(send_password_reset_email("ada@example.com", "reset-token"))
    asyncio.run(send_email_verification("ada@example.com", "verify-token"))
    assert sent == ["Reset Your FounderConsole Password", "Verify Your FounderConsole Email"]


def test_unsubscribe_post_is_scoped_to_the_token_user(db):
    ada = _user(db, "ada@example.com")
    bea = _user(db, "bea@example.com")
    db.add(NotificationPreference(user_id=bea.id, email_enabled=True, monthly_digest=True))
    db.commit()

    app = FastAPI()
    app.include_router(unsubscribe_router)
    Session = sessionmaker(bind=db.get_bind())

    def override():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    token = sign_unsubscribe_token(ada.id)

    preview = client.get("/email/unsubscribe", params={"token": token})
    assert preview.status_code == 200
    assert preview.json()["unsubscribed"] is False
    db.expire_all()
    assert db.query(NotificationPreference).filter_by(user_id=ada.id).first() is None

    forged = client.post("/email/unsubscribe", params={"token": token[:-1] + ("A" if token[-1] != "A" else "B")})
    assert forged.status_code == 400
    db.expire_all()
    assert db.query(NotificationPreference).filter_by(user_id=ada.id).first() is None
    assert db.query(NotificationPreference).filter_by(user_id=bea.id).one().email_enabled

    swapped = _retarget(token, bea.id)
    assert client.post("/email/unsubscribe", params={"token": swapped}).status_code == 400
    db.expire_all()
    assert db.query(NotificationPreference).filter_by(user_id=bea.id).one().email_enabled

    ok = client.post(
        "/email/unsubscribe",
        params={"token": token},
        data={"List-Unsubscribe": "One-Click", "user_id": str(bea.id)},
    )
    assert ok.status_code == 200
    assert ok.json()["unsubscribed"] is True
    db.expire_all()
    ada_pref = db.query(NotificationPreference).filter_by(user_id=ada.id).one()
    assert not ada_pref.email_enabled
    assert not ada_pref.monthly_digest
    assert db.query(NotificationPreference).filter_by(user_id=bea.id).one().email_enabled

    again = client.post("/email/unsubscribe", params={"token": token})
    assert again.status_code == 200
    assert again.json()["already"] is True


def test_apply_unsubscribe_does_not_touch_a_different_user(db):
    ada = _user(db, "ada@example.com")
    bea = _user(db, "bea@example.com")
    assert apply_unsubscribe(db, ada.id) == "ok"
    db.expire_all()
    assert db.query(NotificationPreference).filter_by(user_id=bea.id).first() is None
    assert apply_unsubscribe(db, 999999) == "missing"


def _retarget(token: str, user_id: int) -> str:
    padded = token + ("=" * (-len(token) % 4))
    _user_part, sig = base64.urlsafe_b64decode(padded).decode("ascii").split(".", 1)
    raw = f"{user_id}.{sig}".encode("ascii")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def test_onboarding_cap_does_not_claim_and_success_is_idempotent(db, monkeypatch):
    user = _user(db, "ada@example.com")
    step = SEQUENCE[1]
    _sent(db, user.id, datetime.utcnow(), n=2)

    async def should_not_send(*args, **kwargs):
        raise AssertionError("capped step was sent")

    monkeypatch.setattr("server.email.service.send_lifecycle_email", should_not_send)
    assert asyncio.run(_send_step(user.id, user.email, None, step, db)) is False
    left = db.execute(text("SELECT COUNT(*) FROM onboarding_email_log")).scalar()
    assert left == 0

    db.query(LifecycleEmailLog).delete()
    db.commit()
    calls = []

    async def fake_send(*args, **kwargs):
        calls.append(kwargs.get("html_content") or args[2])
        return {"success": True, "message_id": "m"}

    monkeypatch.setattr("server.email.service.send_lifecycle_email", fake_send)
    assert asyncio.run(_send_step(user.id, user.email, "Ada", step, db)) is True
    assert asyncio.run(_send_step(user.id, user.email, "Ada", step, db)) is False
    assert len(calls) == 1
    assert "/unsubscribe?token=" in calls[0]
    row = db.execute(
        text("SELECT success, attempts FROM onboarding_email_log WHERE user_id = :u AND step_key = :s"),
        {"u": user.id, "s": step.key},
    ).fetchone()
    assert row[0] in (True, 1)
    assert int(row[1]) == 1

    claimed = db.execute(
        text(CLAIM_SQL),
        {"uid": user.id, "step": step.key, "maxa": 3},
    ).fetchone()
    assert claimed is None


def test_onboarding_cap_after_claim_releases_and_can_send_later(db, monkeypatch):
    user = _user(db, "ada@example.com")
    step = SEQUENCE[2]
    calls = []

    async def fake_send(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return {"success": False, "skipped": True, "reason": "capped"}
        return {"success": True, "message_id": "m"}

    monkeypatch.setattr("server.email.service.send_lifecycle_email", fake_send)
    assert asyncio.run(_send_step(user.id, user.email, None, step, db)) is False
    assert db.execute(text("SELECT COUNT(*) FROM onboarding_email_log")).scalar() == 0

    assert asyncio.run(_send_step(user.id, user.email, None, step, db)) is True
    assert asyncio.run(_send_step(user.id, user.email, None, step, db)) is False
    assert len(calls) == 2
    row = db.execute(
        text("SELECT success FROM onboarding_email_log WHERE user_id = :u"),
        {"u": user.id},
    ).fetchone()
    assert row[0] in (True, 1)


def test_activity_template_footer_uses_the_signed_link():
    url = "https://founderconsole.ai/unsubscribe?token=abc"
    html = render_simulation_report_template(
        company_name="Northwind",
        scenario_name="Base",
        runway={"p10": 6, "p50": 12, "p90": 18},
        survival={"12m": 0.8, "18m": 0.5, "24m": 0.2},
        unsubscribe_url=url,
    )
    assert url in html
