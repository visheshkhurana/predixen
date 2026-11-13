"""Lifecycle unsubscribe, the per-user send cap, and hold expiry.

Opt-out lives on NotificationPreference. The send choke point is
deliver_lifecycle_email, and every call names a category. Onboarding still
claims a row before send. A cap skip releases that claim. A step past its
max delay is marked dropped and is not claimed again.
"""
from __future__ import annotations

import asyncio
import base64
import inspect
import re
from datetime import datetime, timedelta
from urllib.parse import unquote

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
    send_receipt_email,
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
                dropped_at TIMESTAMP,
                UNIQUE(user_id, step_key)
            )
        """))
    return engine


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv("LIFECYCLE_GUARDS", "on")
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
        category="lifecycle",
        template="activity_simulation",
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
        category="digest",
        template="monthly_digest",
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
        category="lifecycle",
        template="activity_simulation",
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
        category="lifecycle",
        template="onboarding_welcome",
        campaign="onboarding_welcome",
        user_id=user.id,
        db=db,
    )
    assert result["reason"] == "capped"


def test_kill_switch_lets_opted_out_mail_through(db, monkeypatch):
    monkeypatch.setenv("LIFECYCLE_GUARDS", "off")
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
        category="digest",
        template="monthly_digest",
        campaign="monthly_digest",
        user_id=user.id,
        db=db,
    )
    assert result["success"] is True
    assert len(calls) == 1
    assert calls[0]["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert calls[0]["headers"]["List-Unsubscribe"].startswith("<https://")


def test_transactional_mail_skips_cap_opt_out_and_unsubscribe_headers(db, monkeypatch):
    user = _user(db, "ada@example.com")
    db.add(NotificationPreference(user_id=user.id, email_enabled=False, monthly_digest=False))
    db.commit()
    _sent(db, user.id, datetime.utcnow(), n=5)
    calls = []

    def fake_send(*args, **kwargs):
        calls.append({"subject": args[1], "headers": kwargs.get("headers"), "html": args[2]})
        return {"success": True, "message_id": "t"}

    monkeypatch.setattr("server.email.service._send_email_sync", fake_send)
    asyncio.run(send_password_reset_email("ada@example.com", "reset-token"))
    asyncio.run(send_email_verification("ada@example.com", "verify-token"))
    asyncio.run(send_receipt_email("ada@example.com", "<p>Paid $20</p>"))
    assert [c["subject"] for c in calls] == [
        "Reset Your FounderConsole Password",
        "Verify Your FounderConsole Email",
        "Your FounderConsole receipt",
    ]
    for call in calls:
        assert not call["headers"]
        assert "List-Unsubscribe" not in call["html"]

    for category, template in (
        ("lifecycle", "activity_simulation"),
        ("digest", "monthly_digest"),
        ("briefing", "weekly_briefing"),
    ):
        blocked = deliver_lifecycle_email(
            "ada@example.com",
            template,
            "<p>covered</p>",
            category=category,
            template=template,
            user_id=user.id,
            db=db,
        )
        assert blocked["skipped"] is True
        assert blocked["reason"] == "opted_out"
    assert len(calls) == 3


def test_unknown_category_is_rejected(db):
    user = _user(db, "ada@example.com")
    with pytest.raises(ValueError, match="unknown email category"):
        deliver_lifecycle_email(
            "ada@example.com",
            "Hi",
            "<p>x</p>",
            category="nurture",
            template="password_reset",
            user_id=user.id,
            db=db,
        )


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


def _token_in(value: str) -> str:
    match = re.search(r"[?&]token=([^&\"'<>]+)", value)
    assert match, value
    return unquote(match.group(1))


def test_covered_sends_use_one_https_token_for_header_and_footer(db, monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "http://founderconsole.ai")
    monkeypatch.setenv("LIFECYCLE_EMAIL_MAX_PER_24H", "10")
    monkeypatch.setenv("LIFECYCLE_EMAIL_MAX_PER_7D", "10")
    user = _user(db, "ada@example.com")
    calls = []

    def fake_send(*args, **kwargs):
        calls.append({"html": args[2], "headers": kwargs.get("headers")})
        return {"success": True, "message_id": "m"}

    monkeypatch.setattr("server.email.service._send_email_sync", fake_send)
    stale = '<html><body><a href="http://founderconsole.ai/unsubscribe?token=someone-else">Unsubscribe</a></body></html>'
    for category, template in (
        ("lifecycle", "onboarding_truth_scan"),
        ("digest", "monthly_digest"),
        ("briefing", "weekly_briefing"),
    ):
        result = deliver_lifecycle_email(
            "ada@example.com",
            template,
            stale,
            category=category,
            template=template,
            user_id=user.id,
            db=db,
            due_at=datetime.utcnow(),
        )
        assert result["success"] is True

    assert len(calls) == 3
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

    for call in calls:
        headers = call["headers"]
        assert headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
        header_url = headers["List-Unsubscribe"]
        assert header_url.startswith("<https://")
        assert header_url.endswith(">")
        assert "http://" not in header_url
        header_token = _token_in(header_url)
        footer_token = _token_in(call["html"])
        assert header_token == footer_token
        assert verify_unsubscribe_token(header_token) == user.id
        assert "someone-else" not in call["html"]

    posted = client.post(
        "/email/unsubscribe",
        params={"token": _token_in(calls[0]["headers"]["List-Unsubscribe"])},
    )
    assert posted.status_code == 200
    assert posted.request.headers.get("authorization") is None

    db.expire_all()
    pref = db.query(NotificationPreference).filter_by(user_id=user.id).one()
    assert not pref.email_enabled
    assert not pref.monthly_digest


def test_day1_onboarding_past_max_hold_is_dropped_and_not_retried(db, monkeypatch):
    user = _user(db, "ada@example.com")
    user.created_at = datetime.utcnow() - timedelta(days=4)
    db.commit()
    step = SEQUENCE[1]
    assert step.key == "truth_scan"
    assert step.delay_days == 1
    calls = []

    async def should_not_send(*args, **kwargs):
        calls.append(kwargs)
        raise AssertionError("expired step was sent")

    monkeypatch.setattr("server.email.service.send_lifecycle_email", should_not_send)
    assert asyncio.run(_send_step(user.id, user.email, None, step, db)) is False
    assert calls == []
    row = db.execute(
        text("""
            SELECT success, attempts, dropped_at
            FROM onboarding_email_log
            WHERE user_id = :u AND step_key = :s
        """),
        {"u": user.id, "s": step.key},
    ).fetchone()
    assert row[0] in (False, 0)
    assert int(row[1]) == 0
    assert row[2] is not None
    drop = db.query(LifecycleEmailLog).filter(LifecycleEmailLog.user_id == user.id).one()
    assert drop.status == "dropped_expired"
    assert drop.reason == "expired"

    assert asyncio.run(_send_step(user.id, user.email, None, step, db)) is False
    assert calls == []
    claimed = db.execute(
        text(CLAIM_SQL),
        {"uid": user.id, "step": step.key, "maxa": 3},
    ).fetchone()
    assert claimed is None
    still = db.execute(
        text("SELECT COUNT(*) FROM onboarding_email_log WHERE dropped_at IS NOT NULL")
    ).scalar()
    assert still == 1


def test_capped_onboarding_inside_max_hold_stays_retryable(db, monkeypatch):
    user = _user(db, "ada@example.com")
    step = SEQUENCE[1]
    _sent(db, user.id, datetime.utcnow(), n=2)

    async def should_not_send(*args, **kwargs):
        raise AssertionError("capped step was sent")

    monkeypatch.setattr("server.email.service.send_lifecycle_email", should_not_send)
    assert asyncio.run(_send_step(user.id, user.email, None, step, db)) is False
    assert db.execute(text("SELECT COUNT(*) FROM onboarding_email_log")).scalar() == 0
    skip = db.query(LifecycleEmailLog).filter(LifecycleEmailLog.status == "skipped_capped").one()
    assert skip.reason == "capped"
    assert db.query(LifecycleEmailLog).filter(LifecycleEmailLog.status == "dropped_expired").count() == 0


def test_activity_past_max_hold_is_dropped(db, monkeypatch):
    user = _user(db, "ada@example.com")

    def should_not_send(*args, **kwargs):
        raise AssertionError("expired activity mail was sent")

    monkeypatch.setattr("server.email.service._send_email_sync", should_not_send)
    result = deliver_lifecycle_email(
        "ada@example.com",
        "Simulation",
        "<p>late</p>",
        category="lifecycle",
        template="activity_simulation",
        user_id=user.id,
        due_at=datetime.utcnow() - timedelta(hours=13),
        db=db,
    )
    assert result["dropped"] is True
    assert result["reason"] == "expired"
    drop = db.query(LifecycleEmailLog).one()
    assert drop.status == "dropped_expired"


def test_weekly_briefing_send_names_briefing_category():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "api" / "smart_alerts.py").read_text()
    assert 'category="briefing"' in source
    assert 'template="weekly_briefing"' in source
    assert "send_lifecycle_email(" in source


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


# --- the ASCII hardening on the token's user part --------------------------
#
# verify_unsubscribe_token guards the user part with
# `user_part.isascii() and user_part.isdigit()` at lifecycle_guard.py:188.
# Measured, the characters that guard is about do not behave alike:
#
#   int("２") == 2 and int("٢") == 2   - fullwidth and Arabic-Indic
#       "2". A non-ASCII SPELLING OF A REAL ID. With a signature computed over
#       that id, the rest of the function accepts it as that user.
#   int("²") and int("①") raise ValueError  - superscript two and
#       circled one. isdigit() is true, int() fails.
#
# There are 798 such characters, and every one is rejected today - but NOT
# because of the isascii() conjunct. Line 184 decodes with .decode("ascii")
# INSIDE the try whose except returns None, so any non-ASCII byte raises
# UnicodeDecodeError and returns None before line 188 is reached. The conjunct
# is inert there, which is measured rather than argued: reverting line 188 to
# `not user_part.isdigit()` changes no outcome in this file's tests.
#
# So there are two different things worth pinning and they need two different
# kinds of test. The behavioural ones below pin that a non-ASCII digit never
# reaches int() - and they FAIL if the ascii decode is ever moved out of the
# try, which is the change that would make line 188 matter. The source-text test
# at the end pins the conjunct itself, because no behavioural test can.

_NON_ASCII_DIGITS = [c for c in map(chr, range(0x110000)) if c.isdigit() and not c.isascii()]


def _raw_token(user_part: str, sig: str) -> str:
    """base64url of "<user_part>.<sig>", which is the wire form of a token."""
    return base64.urlsafe_b64encode(f"{user_part}.{sig}".encode("utf-8")).decode("ascii")


def _sig_of(token: str) -> str:
    return base64.urlsafe_b64decode(token + ("=" * (-len(token) % 4))).decode("ascii").split(".", 1)[1]


def test_every_non_ascii_digit_user_part_is_rejected():
    """All 798 of them, not a chosen few - and none of them raises."""
    # Proves the sweep is not vacuous. Deliberately a floor rather than the
    # exact 798, which is a fact about this Python's Unicode tables.
    assert len(_NON_ASCII_DIGITS) > 100, "the sweep collected nothing - it would pass for free"

    for c in _NON_ASCII_DIGITS:
        assert verify_unsubscribe_token(_raw_token(c, "0" * 64)) is None, (
            f"{c!r} (U+{ord(c):04X}) was not rejected"
        )


def test_fullwidth_digit_cannot_impersonate_the_id_it_spells():
    """The sharp case: a non-ASCII spelling of a real id, with a REAL signature.

    `int("２") == 2`, so the signature for user 2 is a valid signature for
    this user part. Only the ASCII path stops it - everything downstream would
    accept it.
    """
    valid = sign_unsubscribe_token(2)
    sig = _sig_of(valid)

    # The payload really does spell id 2, and the signature really is the one
    # for id 2. Both halves of a working forgery are present.
    assert int("２") == 2
    assert sig == _sig_of(sign_unsubscribe_token(2))

    impostor = _raw_token("２", sig)
    assert impostor != valid, "the impostor must not be the valid token"
    assert verify_unsubscribe_token(valid) == 2, "the valid token must still verify"
    assert verify_unsubscribe_token(impostor) is None


def test_unsubscribe_route_answers_400_for_a_non_ascii_digit_token(db):
    """The route, not just the function: 400, and never a 500."""
    ada = _user(db, "ada@example.com")
    db.commit()
    sig = _sig_of(sign_unsubscribe_token(ada.id))

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

    for c in ("２", "²", "٢"):
        token = _raw_token(c, sig)
        response = client.get("/email/unsubscribe", params={"token": token})
        assert response.status_code == 400, f"{c!r} gave {response.status_code}, not 400"
        db.expire_all()
        assert db.query(NotificationPreference).filter_by(user_id=ada.id).first() is None, (
            f"{c!r} opted the user out"
        )


def test_lifecycle_guard_keeps_the_ascii_conjunct():
    """A SOURCE-TEXT pin, and deliberately so.

    No behavioural test can pin this conjunct: it is unreachable-but-true at
    :188 because :184 already refused every non-ASCII byte. A behavioural
    assertion would keep passing if the conjunct were deleted, which is exactly
    the silent revert this is here to prevent. So it asserts the source.
    """
    source = inspect.getsource(verify_unsubscribe_token)
    assert "user_part.isascii() and user_part.isdigit()" in source, (
        "the ASCII conjunct on the unsubscribe token's user part is gone from "
        "verify_unsubscribe_token; it is inert today only because the ascii "
        "decode in that function is inside a try, so removing it is safe only "
        "while that stays true"
    )
