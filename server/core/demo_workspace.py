"""Per-visitor demo workspaces.

"Try the live demo" used to log every visitor into one shared account
(demo@founderconsole.ai / demo123), so each visitor saw the last visitor's
edits and the account piled up companies. Now each click creates a throwaway
user that owns a fresh copy of the sample company and nothing else:

  * the user's email is ``visitor-<hex>@demo.founderconsole.invalid``. The
    ``.invalid`` TLD is reserved (RFC 2606), so nothing can be delivered to it
    and /auth/register rejects it, which makes the suffix an unforgeable
    demo flag without a schema change;
  * no password, no OAuth identity, role "viewer", never verified, so the
    session cookie is the only way in;
  * creation is rate limited per IP (per minute by the middleware, per hour
    here) and globally per hour;
  * demo users (and the legacy shared account) are refused admin routes and
    every route that sends email, invites or shares (``DemoGuardMiddleware``);
  * demo users older than DEMO_TTL_HOURS are deleted with everything they
    own, at boot and opportunistically on each new demo.

The legacy shared account is left alone unless DEMO_LEGACY_CLEANUP=true, in
which case ``cleanup_legacy_demo_account`` runs once (idempotent) on boot.
"""
from __future__ import annotations

import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Set

from sqlalchemy import MetaData, Table, func, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DEMO_EMAIL_DOMAIN = "demo.founderconsole.invalid"
LEGACY_DEMO_EMAIL = "demo@founderconsole.ai"
LEGACY_CLEANUP_MARKER = "demo_legacy_cleanup_v1"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_true(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in ("1", "true", "yes", "on")


def demo_ttl_hours() -> int:
    return max(1, _env_int("DEMO_TTL_HOURS", 24))


def max_per_ip_per_hour() -> int:
    return _env_int("DEMO_MAX_PER_IP_PER_HOUR", 10)


def max_per_hour() -> int:
    return _env_int("DEMO_MAX_PER_HOUR", 300)


# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

def is_ephemeral_demo_email(email: Optional[str]) -> bool:
    return (email or "").strip().lower().endswith("@" + DEMO_EMAIL_DOMAIN)


def is_demo_email(email: Optional[str]) -> bool:
    """Per-visitor demo users and the legacy shared demo account."""
    e = (email or "").strip().lower()
    return e == LEGACY_DEMO_EMAIL or is_ephemeral_demo_email(e)


def is_demo_user(user) -> bool:
    return is_demo_email(getattr(user, "email", None))


def _ephemeral_filter(User):
    # Belt and braces: a row is only treated as a throwaway demo user if it
    # has the reserved suffix AND no way to sign in other than the cookie.
    return (
        User.email.like("%@" + DEMO_EMAIL_DOMAIN),
        User.password_hash.is_(None),
        User.oauth_id.is_(None),
    )


def client_ip(request) -> str:
    """Same rule as the rate limiter: the trusted edge appends the real client
    IP as the LAST X-Forwarded-For entry."""
    xff = request.headers.get("X-Forwarded-For") if request is not None else None
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-1][:45]
    if request is not None and request.client:
        return request.client.host
    return "unknown"


# --------------------------------------------------------------------------
# Creation
# --------------------------------------------------------------------------

class DemoLimitError(Exception):
    pass


def check_demo_quota(db: Session, ip: str, now: Optional[datetime] = None) -> None:
    from server.models.login_history import LoginHistory
    from server.models.user import User

    now = now or datetime.utcnow()
    since = now - timedelta(hours=1)
    per_ip = (
        db.query(func.count(LoginHistory.id))
        .filter(
            LoginHistory.email.like("%@" + DEMO_EMAIL_DOMAIN),
            LoginHistory.ip_address == ip,
            LoginHistory.created_at >= since,
        )
        .scalar()
        or 0
    )
    if per_ip >= max_per_ip_per_hour():
        raise DemoLimitError("Too many demo sessions from this network. Try again in an hour, or sign up free.")
    total = (
        db.query(func.count(User.id))
        .filter(*_ephemeral_filter(User), User.created_at >= since)
        .scalar()
        or 0
    )
    if total >= max_per_hour():
        raise DemoLimitError("The demo is busy right now. Please try again shortly, or sign up free.")


def create_demo_user(db: Session, ip: str = "unknown", user_agent: Optional[str] = None):
    """A throwaway user with its own fresh copy of the sample company.

    Raises DemoLimitError when the per-IP or global hourly cap is reached.
    Returns (user, company).
    """
    from server.models.login_history import LoginHistory
    from server.models.user import User
    from server.seed.seed_demo import seed_demo_company

    check_demo_quota(db, ip)
    user = User(
        email=f"visitor-{uuid.uuid4().hex[:16]}@{DEMO_EMAIL_DOMAIN}",
        password_hash=None,
        role="viewer",
        display_name="Demo visitor",
        is_active=True,
        is_email_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # Recorded before seeding so a failing seed still counts toward the cap.
    db.add(LoginHistory(user_id=user.id, email=user.email, ip_address=ip,
                        user_agent=(user_agent or "")[:1000] or None, success=True))
    db.commit()
    try:
        company = seed_demo_company(db, user)
    except Exception:
        db.rollback()
        try:
            purge_user(db, user.id)
            db.commit()
        except Exception:
            db.rollback()
        raise
    return user, company


# --------------------------------------------------------------------------
# Deletion
# --------------------------------------------------------------------------

_REFLECT_CACHE: dict = {}
_REFLECT_TTL = timedelta(hours=1)


def _reflect(db: Session) -> MetaData:
    """The live schema, including tables created by raw SQL in migrations.py
    that the ORM metadata does not know about. Cached per database for an hour:
    reflection is the expensive part of a cleanup."""
    bind = db.get_bind()
    key = str(bind.url)
    hit = _REFLECT_CACHE.get(key)
    if hit and datetime.utcnow() - hit[0] < _REFLECT_TTL:
        return hit[1]
    meta = MetaData()
    meta.reflect(bind=bind)
    _REFLECT_CACHE[key] = (datetime.utcnow(), meta)
    return meta


def _purge_rows(db: Session, meta: MetaData, table: Table, row_select, skip: Set[str]) -> None:
    """Delete rows of `table` matching `row_select` and everything that
    references them: NOT NULL children are deleted first (recursively),
    nullable references are detached."""
    steps: List[tuple] = []

    def visit(tbl: Table, sel, depth: int, path: tuple) -> None:
        if depth > 8:
            raise RuntimeError(f"demo purge: FK chain too deep at {tbl.name}")
        for child in meta.sorted_tables:
            if child.name in skip or child.name in path:
                continue
            for fk in child.foreign_keys:
                if fk.column.table is not tbl:
                    continue
                parent_vals = sel.with_only_columns(fk.column)
                if fk.parent.nullable:
                    steps.append(("nullify", child, fk.parent, parent_vals))
                else:
                    child_sel = select(child).where(fk.parent.in_(parent_vals))
                    visit(child, child_sel, depth + 1, path + (child.name,))
                    steps.append(("delete", child, fk.parent, parent_vals))

    visit(table, row_select, 0, (table.name,))
    for action, child, col, parent_vals in steps:
        if action == "nullify":
            db.execute(child.update().where(col.in_(parent_vals)).values({col.name: None}))
        else:
            db.execute(child.delete().where(col.in_(parent_vals)))
    db.execute(table.delete().where(table.c.id.in_(row_select.with_only_columns(table.c.id))))


def purge_user(db: Session, user_id: int, meta: Optional[MetaData] = None) -> None:
    """Delete a user, every company they own, and every row hanging off
    either. Caller commits. Only ever called for demo users."""
    from server.core.company_purge import purge_company
    from server.models.company import Company

    company_ids = [r[0] for r in db.query(Company.id).filter(Company.user_id == user_id).all()]
    for cid in company_ids:
        purge_company(db, cid)
    meta = meta or _reflect(db)
    users = meta.tables["users"]
    # Companies are already gone; skipping the table keeps the walk short.
    _purge_rows(db, meta, users, select(users).where(users.c.id == user_id), skip={"companies"})


def cleanup_expired_demo_users(db: Session, older_than_hours: Optional[int] = None,
                               limit: int = 200, now: Optional[datetime] = None) -> int:
    """Delete throwaway demo users (and their data) older than the TTL.
    Never touches a user without the reserved demo suffix. Returns the count."""
    from server.models.user import User

    now = now or datetime.utcnow()
    hours = older_than_hours if older_than_hours is not None else demo_ttl_hours()
    cutoff = now - timedelta(hours=hours)
    ids = [
        r[0] for r in db.query(User.id)
        .filter(*_ephemeral_filter(User), User.created_at < cutoff)
        .order_by(User.id)
        .limit(limit)
        .all()
    ]
    if not ids:
        return 0
    meta = _reflect(db)
    done = 0
    for uid in ids:
        try:
            purge_user(db, uid, meta)
            db.commit()
            done += 1
        except Exception as e:
            db.rollback()
            logger.warning("demo cleanup: could not purge demo user %s: %s", uid, e)
    if done:
        logger.info("demo cleanup: purged %d expired demo users", done)
    return done


# --------------------------------------------------------------------------
# Legacy shared account (one-time, opt-in)
# --------------------------------------------------------------------------

def _peer_company_names() -> Set[str]:
    try:
        from server.seed.seed_twin_intelligence import PEER_COMPANIES
        return {p["name"] for p in PEER_COMPANIES}
    except Exception:
        return set()


def _keep_ids() -> Set[int]:
    raw = os.getenv("DEMO_LEGACY_KEEP_COMPANY_IDS", "")
    out = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def legacy_cleanup_plan(db: Session, legacy_user) -> List[int]:
    """Company ids the legacy cleanup would delete: every company owned by the
    legacy demo account except the Intelligence Graph peers, ids listed in
    DEMO_LEGACY_KEEP_COMPANY_IDS, and a sample company already rebuilt by a
    previous cleanup run."""
    from server.models.company import Company

    peers = _peer_company_names()
    keep = _keep_ids()
    doomed = []
    for c in db.query(Company).filter(Company.user_id == legacy_user.id).order_by(Company.id).all():
        if c.name in peers or c.id in keep:
            continue
        if (c.metadata_json or {}).get(LEGACY_CLEANUP_MARKER):
            continue
        doomed.append(c.id)
    return doomed


def cleanup_legacy_demo_account(db: Session, legacy_user=None) -> bool:
    """One-time reset of the legacy shared demo account, gated by
    DEMO_LEGACY_CLEANUP=true. Deletes the account's duplicate and visitor-made
    companies (see legacy_cleanup_plan) and rebuilds one fresh sample company.
    Only ever touches companies whose owner is demo@founderconsole.ai.
    Idempotent: once the rebuilt company exists and nothing else is left to
    delete, it does nothing. Returns True when it changed anything.

    With DEMO_LEGACY_DISABLE_LOGIN=true it also replaces the public demo123
    password with a random one, so the shared login stops working.
    """
    if not _env_true("DEMO_LEGACY_CLEANUP"):
        return False
    from server.core.company_metadata import save_metadata_value
    from server.core.company_purge import purge_company
    from server.core.security import get_password_hash
    from server.models.company import Company
    from server.models.user import User
    from server.seed.seed_demo import DEMO_COMPANY_NAME, seed_demo_company

    if legacy_user is None:
        legacy_user = db.query(User).filter(func.lower(User.email) == LEGACY_DEMO_EMAIL).first()
    if legacy_user is None or (legacy_user.email or "").lower() != LEGACY_DEMO_EMAIL:
        return False

    changed = False
    if _env_true("DEMO_LEGACY_DISABLE_LOGIN") and legacy_user.password_hash:
        legacy_user.password_hash = get_password_hash(secrets.token_urlsafe(32))
        db.commit()
        changed = True
        logger.info("legacy demo cleanup: shared demo password rotated")

    doomed = legacy_cleanup_plan(db, legacy_user)
    for cid in doomed:
        try:
            name = db.query(Company.name).filter(Company.id == cid).scalar()
            purge_company(db, cid)
            db.commit()
            changed = True
            logger.info("legacy demo cleanup: deleted company id=%s name=%s", cid, name)
        except Exception as e:
            db.rollback()
            logger.warning("legacy demo cleanup: could not delete company id=%s: %s", cid, e)

    rebuilt = [
        c for c in db.query(Company).filter(Company.user_id == legacy_user.id).all()
        if (c.metadata_json or {}).get(LEGACY_CLEANUP_MARKER)
    ]
    if not rebuilt:
        company = seed_demo_company(db, legacy_user)
        save_metadata_value(db, company, LEGACY_CLEANUP_MARKER, True)
        db.commit()
        changed = True
        logger.info("legacy demo cleanup: rebuilt %s as company id=%s", DEMO_COMPANY_NAME, company.id)
    return changed
