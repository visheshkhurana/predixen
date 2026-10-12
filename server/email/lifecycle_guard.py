"""Opt-out, frequency cap, and hold expiry for covered product email.

Every send names an explicit category. Password reset, email verification,
and receipts are transactional: they skip the cap, the unsubscribe check,
hold expiry, and List-Unsubscribe headers. Lifecycle (onboarding and activity),
digest, and briefing are covered by both the cap and RFC 8058 unsubscribe.

Opt-out is stored on NotificationPreference.email_enabled (and monthly_digest
is cleared at the same time so the digest toggle matches). EmailEvent stays a
delivery log; it has no preference column.

The send choke point is deliver_lifecycle_email in server.email.service.
LIFECYCLE_GUARDS=off skips opt-out, the cap, and hold expiry so a bad deploy
can be undone without a revert. Covered mail still carries List-Unsubscribe.
Unsubscribe links keep working either way.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

from sqlalchemy import func
from sqlalchemy.orm import Session

from server.core.config import settings
from server.core.db import SessionLocal
from server.models.email_event import LifecycleEmailLog
from server.models.user import User
from server.models.workspace import NotificationPreference

logger = logging.getLogger(__name__)

# One shared rolling counter per user for covered mail (lifecycle, digest,
# briefing). Transactional mail is not counted.
# 2 per rolling 24h: activity mail can fire several times in one sitting.
# Two leaves room for two distinct product notices the same day; a third waits.
# 5 per rolling 7 days is a ceiling, not a quota. It stops a week of activity
# reports stacking on other product mail. Sends older than 7 days drop out of
# the window. Held mail waits and is retried until its template max delay.
DEFAULT_MAX_PER_24H = 2
DEFAULT_MAX_PER_7D = 5

CATEGORY_TRANSACTIONAL = "transactional"
CATEGORY_LIFECYCLE = "lifecycle"
CATEGORY_DIGEST = "digest"
CATEGORY_BRIEFING = "briefing"
COVERED_CATEGORIES = frozenset({CATEGORY_LIFECYCLE, CATEGORY_DIGEST, CATEGORY_BRIEFING})
TRANSACTIONAL_TEMPLATES = frozenset({"password_reset", "email_verification", "receipt"})

# How long a covered template may sit after it became due. Past this, drop it.
# The day-1 onboarding step (truth_scan) is due one day after signup and may
# wait one more day — it does not go out days late.
TEMPLATE_MAX_HOLD = {
    "onboarding_welcome": timedelta(days=1),
    "onboarding_truth_scan": timedelta(days=1),
    "onboarding_simulator": timedelta(days=1),
    "onboarding_copilot": timedelta(days=2),
    "onboarding_fundraising": timedelta(days=2),
    "onboarding_feedback": timedelta(days=2),
    "activity_simulation": timedelta(hours=12),
    "activity_document": timedelta(hours=12),
    "activity_decision": timedelta(hours=12),
    "monthly_digest": timedelta(days=3),
    "weekly_briefing": timedelta(days=2),
}

TOKEN_PURPOSE = "lifecycle-unsub-v1"
_SKIP_DEDUPE = timedelta(hours=1)
_UNSUB_HREF = re.compile(
    r"""href=(['"])[^'"]*/unsubscribe(?:\?[^'"]*)?\1""",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GuardDecision:
    allow: bool
    reason: str
    sends_24h: int
    sends_7d: int


def guard_enabled() -> bool:
    """LIFECYCLE_GUARDS is the kill switch. The previous name still works if unset."""
    if "LIFECYCLE_GUARDS" in os.environ:
        raw = os.environ["LIFECYCLE_GUARDS"]
    else:
        raw = os.getenv("LIFECYCLE_EMAIL_GUARD", "on")
    return raw.strip().lower() not in {"0", "off", "false", "no"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Ignoring non-integer %s=%r; using %s", name, raw, default)
        return default
    if value < 0:
        logger.warning("Ignoring negative %s=%s; using %s", name, value, default)
        return default
    return value


def cap_limits() -> tuple[int, int]:
    return (
        _int_env("LIFECYCLE_EMAIL_MAX_PER_24H", DEFAULT_MAX_PER_24H),
        _int_env("LIFECYCLE_EMAIL_MAX_PER_7D", DEFAULT_MAX_PER_7D),
    )


def decide(
    *,
    opted_out: bool,
    sends_24h: int,
    sends_7d: int,
    enabled: bool,
    max_24h: int,
    max_7d: int,
) -> GuardDecision:
    if not enabled:
        return GuardDecision(True, "guard_disabled", sends_24h, sends_7d)
    if opted_out:
        return GuardDecision(False, "opted_out", sends_24h, sends_7d)
    if sends_24h >= max_24h or sends_7d >= max_7d:
        return GuardDecision(False, "capped", sends_24h, sends_7d)
    return GuardDecision(True, "ok", sends_24h, sends_7d)


def assert_category(category: str) -> None:
    if category == CATEGORY_TRANSACTIONAL or category in COVERED_CATEGORIES:
        return
    raise ValueError(f"unknown email category: {category}")


def assert_template(category: str, template: str) -> None:
    assert_category(category)
    if category == CATEGORY_TRANSACTIONAL:
        if template not in TRANSACTIONAL_TEMPLATES:
            raise ValueError(f"unknown transactional template: {template}")
        return
    if template not in TEMPLATE_MAX_HOLD:
        raise ValueError(f"unknown covered template: {template}")


def is_past_max_hold(template: str, due_at: datetime, now: Optional[datetime] = None) -> bool:
    """True when now is after due_at plus that template's maximum delay."""
    if template not in TEMPLATE_MAX_HOLD:
        raise ValueError(f"unknown covered template: {template}")
    now = now or datetime.utcnow()
    return now > due_at + TEMPLATE_MAX_HOLD[template]


def _signing_key() -> bytes:
    return settings.SECRET_KEY.encode("utf-8")


def sign_unsubscribe_token(user_id: int) -> str:
    """HMAC token bound to one user id. It cannot be retargeted."""
    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        raise ValueError("user_id must be a positive int")
    msg = f"{TOKEN_PURPOSE}:{user_id}".encode("utf-8")
    sig = hmac.new(_signing_key(), msg, hashlib.sha256).hexdigest()
    raw = f"{user_id}.{sig}".encode("ascii")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def verify_unsubscribe_token(token: str) -> Optional[int]:
    """Return the user id, or None when the token is missing, forged, or swapped."""
    if not token or not isinstance(token, str) or len(token) > 512:
        return None
    padded = token + ("=" * (-len(token) % 4))
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")
    except Exception:
        return None
    user_part, sep, sig = raw.partition(".")
    if not sep or not user_part.isdigit() or not sig:
        return None
    user_id = int(user_part)
    if user_id <= 0:
        return None
    msg = f"{TOKEN_PURPOSE}:{user_id}".encode("utf-8")
    expected = hmac.new(_signing_key(), msg, hashlib.sha256).hexdigest()
    if len(sig) != len(expected) or not hmac.compare_digest(expected, sig):
        return None
    return user_id


def app_base_url() -> str:
    return os.getenv("APP_BASE_URL", "https://founderconsole.ai").rstrip("/")


def https_base_url() -> str:
    """List-Unsubscribe must be HTTPS. An http base is rewritten, not left as-is."""
    base = app_base_url()
    lowered = base.lower()
    if lowered.startswith("https://"):
        return base
    if lowered.startswith("http://"):
        return "https://" + base[len("http://"):]
    return "https://" + base.lstrip("/")


@dataclass(frozen=True)
class UnsubscribeLinks:
    """One signing. The footer page and the one-click header share this token."""
    token: str
    page_url: str
    one_click_url: str


def unsubscribe_links(user_id: int) -> UnsubscribeLinks:
    token = sign_unsubscribe_token(user_id)
    quoted = quote(token, safe="")
    base = https_base_url()
    return UnsubscribeLinks(
        token=token,
        page_url=f"{base}/unsubscribe?token={quoted}",
        one_click_url=f"{base}/api/email/unsubscribe?token={quoted}",
    )


def page_unsubscribe_url(user_id: int) -> str:
    return unsubscribe_links(user_id).page_url


def one_click_unsubscribe_url(user_id: int) -> str:
    """Public URL mail clients POST to. Express strips the /api prefix."""
    return unsubscribe_links(user_id).one_click_url


def list_unsubscribe_headers(links: UnsubscribeLinks) -> dict:
    return {
        "List-Unsubscribe": f"<{links.one_click_url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


def lifecycle_list_unsubscribe_headers(user_id: int) -> dict:
    return list_unsubscribe_headers(unsubscribe_links(user_id))


def stamp_unsubscribe_footer(html: str, page_url: str) -> str:
    """Point every unsubscribe href at this send's page URL, or append one."""
    replaced = False

    def _sub(match: re.Match) -> str:
        nonlocal replaced
        replaced = True
        quote_char = match.group(1)
        return f"href={quote_char}{page_url}{quote_char}"

    updated = _UNSUB_HREF.sub(_sub, html or "")
    if replaced:
        return updated
    link = f'<p><a href="{page_url}">Unsubscribe</a></p>'
    idx = updated.lower().rfind("</body>")
    if idx >= 0:
        return updated[:idx] + link + updated[idx:]
    return updated + link


def mask_email(email: str) -> str:
    local, _, domain = (email or "").partition("@")
    if not domain:
        return "***"
    shown = local[:1] if local else ""
    return f"{shown}***@{domain}"


def user_id_for_email(db: Session, email: str) -> Optional[int]:
    if not email:
        return None
    user = (
        db.query(User)
        .filter(func.lower(User.email) == email.strip().lower())
        .first()
    )
    return int(user.id) if user else None


def page_unsubscribe_url_for_email(email: str) -> Optional[str]:
    db = SessionLocal()
    try:
        user_id = user_id_for_email(db, email)
        if user_id is None:
            return None
        return page_unsubscribe_url(user_id)
    finally:
        db.close()


def _explicitly_disabled(value) -> bool:
    """True only for a real off switch. NULL stays subscribed (column default is on)."""
    return value is not None and not bool(value)


def user_opted_out(db: Session, user_id: int) -> bool:
    pref = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id)
        .first()
    )
    return pref is not None and _explicitly_disabled(pref.email_enabled)


def count_sent_since(db: Session, user_id: int, since: datetime) -> int:
    return (
        db.query(LifecycleEmailLog)
        .filter(
            LifecycleEmailLog.user_id == user_id,
            LifecycleEmailLog.status == "sent",
            LifecycleEmailLog.created_at >= since,
        )
        .count()
    )


def evaluate_for_user(db: Session, user_id: int, now: Optional[datetime] = None) -> GuardDecision:
    max_24h, max_7d = cap_limits()
    if not guard_enabled():
        return decide(
            opted_out=False,
            sends_24h=0,
            sends_7d=0,
            enabled=False,
            max_24h=max_24h,
            max_7d=max_7d,
        )
    now = now or datetime.utcnow()
    opted_out = user_opted_out(db, user_id)
    sends_24h = count_sent_since(db, user_id, now - timedelta(hours=24))
    sends_7d = count_sent_since(db, user_id, now - timedelta(days=7))
    return decide(
        opted_out=opted_out,
        sends_24h=sends_24h,
        sends_7d=sends_7d,
        enabled=True,
        max_24h=max_24h,
        max_7d=max_7d,
    )


def record_lifecycle_event(
    db: Session,
    user_id: int,
    kind: str,
    campaign: Optional[str],
    status: str,
    reason: Optional[str] = None,
) -> None:
    """Persist a send or a skip. Repeat skips inside an hour only hit the log line."""
    campaign_s = (campaign or "")[:120] or None
    reason_s = (reason or "")[:120] or None
    status_s = status[:32]
    kind_s = kind[:32]
    verb = "dropped" if status_s == "dropped_expired" else status_s
    logger.info(
        "lifecycle email %s user_id=%s kind=%s campaign=%s reason=%s",
        verb,
        user_id,
        kind_s,
        campaign_s,
        reason_s,
    )
    try:
        if status_s.startswith("skipped") or status_s == "dropped_expired":
            recent = (
                db.query(LifecycleEmailLog)
                .filter(
                    LifecycleEmailLog.user_id == user_id,
                    LifecycleEmailLog.kind == kind_s,
                    LifecycleEmailLog.campaign == campaign_s,
                    LifecycleEmailLog.status == status_s,
                    LifecycleEmailLog.created_at >= datetime.utcnow() - _SKIP_DEDUPE,
                )
                .first()
            )
            if recent is not None:
                return
        db.add(
            LifecycleEmailLog(
                user_id=user_id,
                kind=kind_s,
                campaign=campaign_s,
                status=status_s,
                reason=reason_s,
                created_at=datetime.utcnow(),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("lifecycle email log write failed user_id=%s status=%s", user_id, status_s)


def apply_unsubscribe(db: Session, user_id: int) -> str:
    """Record opt-out for this user only. Returns 'ok', 'already', or 'missing'."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return "missing"
    pref = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id)
        .first()
    )
    already = pref is not None and _explicitly_disabled(pref.email_enabled)
    if pref is None:
        pref = NotificationPreference(
            user_id=user_id,
            email_enabled=False,
            monthly_digest=False,
            email_address=user.email,
        )
        db.add(pref)
    else:
        pref.email_enabled = False
        pref.monthly_digest = False
        pref.updated_at = datetime.utcnow()
    db.commit()
    logger.info("lifecycle unsubscribe recorded user_id=%s already=%s", user_id, already)
    return "already" if already else "ok"
