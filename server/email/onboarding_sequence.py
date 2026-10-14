"""7-day onboarding email drip for new FounderConsole signups.

Each step is sent the first time a user has been registered for >= `delay_days`
and the step has not already been sent. Background scheduler polls every
~10 minutes; sends are idempotent via the `onboarding_email_log` table.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from server.core.db import SessionLocal
from server.email.lifecycle_guard import (
    evaluate_for_user,
    guard_enabled,
    is_past_max_hold,
    page_unsubscribe_url,
    record_lifecycle_event,
)

logger = logging.getLogger(__name__)

APP_URL = os.getenv("APP_BASE_URL", "https://founderconsole.ai")


def _wrap(title: str, body_html: str, cta_label: str, cta_url: str, unsubscribe_url: str) -> str:
    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#0a0a0a;color:#e4e4e7;font-family:-apple-system,Segoe UI,Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:24px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#111114;border:1px solid #27272a;border-radius:12px;overflow:hidden;">
      <tr><td style="padding:28px 32px 8px;">
        <div style="font-size:12px;letter-spacing:1px;color:#10b981;font-weight:600;">FOUNDERCONSOLE</div>
        <h1 style="margin:8px 0 0;font-size:22px;color:#fafafa;line-height:1.3;">{title}</h1>
      </td></tr>
      <tr><td style="padding:16px 32px 8px;font-size:15px;line-height:1.6;color:#d4d4d8;">{body_html}</td></tr>
      <tr><td style="padding:20px 32px 28px;">
        <a href="{cta_url}" style="display:inline-block;background:#10b981;color:#0a0a0a;text-decoration:none;padding:12px 22px;border-radius:8px;font-weight:600;font-size:14px;">{cta_label}</a>
      </td></tr>
      <tr><td style="padding:16px 32px 24px;border-top:1px solid #27272a;font-size:12px;color:#71717a;">
        FounderConsole &middot; AI financial intelligence for founders<br/>
        <a href="{unsubscribe_url}" style="color:#71717a;">Unsubscribe</a>
        &middot;
        <a href="{APP_URL}/account/notifications" style="color:#71717a;">Manage emails</a>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


def _step_welcome(name: Optional[str], unsubscribe_url: str) -> tuple[str, str]:
    greeting = f"Welcome aboard, {name}." if name else "Welcome aboard."
    body = f"""<p>{greeting}</p>
<p>You joined FounderConsole to answer one question: how long your cash lasts, and what changes it.
That answer takes about five minutes.</p>
<p><strong>The one thing worth doing today:</strong> open the runway calculator and put in your real
burn and balance. It reads straight back to you: your monthly net burn, your months of runway, the date
the cash runs out and your projected cash balance. Five minutes, and you have the number the rest of
this week is about.</p>
<p>Everything else here builds on that runway number: the 1,000-path simulation, the ranked decision
list, the diligence pack for your next round.</p>
<p>Tomorrow I'll show you the single highest-leverage move most founders miss in week one.</p>"""
    return ("Your first five minutes on FounderConsole",
            _wrap("Start with your real runway number", body, "Open the runway calculator",
                  f"{APP_URL}/tools/runway-calculator", unsubscribe_url))


def _step_truth_scan(unsubscribe_url: str) -> tuple[str, str]:
    body = """<p>Most founders we onboard discover at least one number in their model that doesn't match their bank account.</p>
<p>Truth Scan compares what you reported against your raw data and flags discrepancies in three colors: green (clean), amber (worth reviewing), red (action required).</p>
<p>It takes <strong>about 5 minutes</strong>. Founders typically find $5K&ndash;$50K of unaccounted spend on first run.</p>"""
    return ("Run your first Truth Scan today (5 min)",
            _wrap("Find what your numbers are hiding", body, "Run Truth Scan", f"{APP_URL}/truth-scan", unsubscribe_url))


def _step_simulator(unsubscribe_url: str) -> tuple[str, str]:
    body = """<p>You've seen your runway number. The useful question is what changes it.</p>
<p>The Simulation Engine runs 1,000 Monte Carlo paths across your burn, growth and gross margin, and
shows you how many months until you run out of cash &mdash; and which lever moves that date the most.</p>
<p>Try the three scenarios founders actually face:</p>
<ul>
  <li>What if growth slows 30%?</li>
  <li>What if you cut 20% of headcount?</li>
  <li>What if you raise $1M today?</li>
</ul>
<p>Run one and <strong>save it</strong>. Two saved scenarios side by side is the fastest way to see
which decision your next board meeting actually turns on.</p>"""
    return ("What would change your runway date?",
            _wrap("Stress-test the scenarios that scare you", body, "Open Simulation Console",
                  f"{APP_URL}/simulate", unsubscribe_url))


def _step_copilot(unsubscribe_url: str) -> tuple[str, str]:
    body = """<p>Your Fund Flow Copilot has read your numbers, your simulations, and 200+ benchmark companies in your stage.</p>
<p>Ask it the questions you'd normally pay a consultant for:</p>
<ul>
  <li><em>"Where am I burning money I shouldn't be?"</em></li>
  <li><em>"What's the strongest case for our next round?"</em></li>
  <li><em>"What three moves will most extend our runway?"</em></li>
</ul>
<p>Every answer is sourced and ranked. No hallucinations &mdash; only what your data supports.</p>"""
    return ("Ask your Copilot the question that's keeping you up at night",
            _wrap("Talk to your Copilot", body, "Open Copilot", f"{APP_URL}/copilot", unsubscribe_url))


def _step_fundraising(unsubscribe_url: str) -> tuple[str, str]:
    body = """<p>When investors ask for your model, your cap table, and your story &mdash; you should have them in one tab.</p>
<p>Fundraising OS gives you:</p>
<ul>
  <li>One-click <strong>cap table</strong> with dilution math.</li>
  <li>An AI-generated <strong>investor one-pager</strong> tuned to your stage.</li>
  <li>A live <strong>Investor Room</strong> link you can share &mdash; no PDF email chains.</li>
</ul>
<p>Even if you're not raising right now, set this up once and you'll never scramble again.</p>"""
    return ("Be raise-ready before you need to be",
            _wrap("Fundraising OS, ready in 10 minutes", body, "Open Fundraising OS", f"{APP_URL}/fundraising", unsubscribe_url))


def _step_feedback(unsubscribe_url: str) -> tuple[str, str]:
    body = """<p>You've had FounderConsole for a week. Two things &mdash; the first takes a minute.</p>
<p><strong>If you haven't put your real numbers in yet</strong>, that is the step that makes the rest
of it work. Open the runway calculator and enter your burn and balance; it shows your months of runway
and the date the money runs out, and everything after it reads off that number.</p>
<p><strong>Then tell me the truth.</strong> Three questions:</p>
<ul>
  <li>What got you to your first "aha" moment?</li>
  <li>What confused you?</li>
  <li>What would you pay for that we don't have yet?</li>
</ul>
<p>Reply to this email &mdash; it goes straight to me, and every reply is read.</p>
<p>&mdash; The FounderConsole team</p>"""
    return ("How was your first week?",
            _wrap("What would make this worth paying for?", body, "Reply to this email",
                  "mailto:hello@founderconsole.ai", unsubscribe_url))


@dataclass
class Step:
    key: str
    delay_days: int
    builder: Callable[..., tuple[str, str]]
    needs_name: bool = False


SEQUENCE: List[Step] = [
    Step("welcome", 0, _step_welcome, needs_name=True),
    Step("truth_scan", 1, _step_truth_scan),
    Step("simulator", 2, _step_simulator),
    Step("copilot", 4, _step_copilot),
    Step("fundraising", 5, _step_fundraising),
    Step("feedback", 7, _step_feedback),
]


MAX_ATTEMPTS = 3

# Claim-before-send. A second worker sees success TRUE, a dropped row, or
# attempts >= MAX and gets no RETURNING row, so the step is not sent twice.
# Cap/opt-out skips must release this claim (see _release_unsent_claim) so the
# step is retried later. A dropped row is never reclaimed.
CLAIM_SQL = """
            INSERT INTO onboarding_email_log (user_id, step_key, success, attempts, sent_at)
            VALUES (:uid, :step, NULL, 1, NOW())
            ON CONFLICT (user_id, step_key) DO UPDATE
                SET attempts = onboarding_email_log.attempts + 1,
                    sent_at = NOW()
                WHERE onboarding_email_log.success IS NOT TRUE
                  AND onboarding_email_log.attempts < :maxa
                  AND onboarding_email_log.dropped_at IS NULL
            RETURNING id
        """

MARK_DROPPED_SQL = """
            INSERT INTO onboarding_email_log
                (user_id, step_key, success, attempts, sent_at, dropped_at, error)
            VALUES (:uid, :step, FALSE, 0, NOW(), NOW(), 'expired')
            ON CONFLICT (user_id, step_key) DO UPDATE
                SET dropped_at = NOW(),
                    success = FALSE,
                    error = 'expired'
                WHERE onboarding_email_log.success IS NOT TRUE
                  AND onboarding_email_log.dropped_at IS NULL
        """


def _release_unsent_claim(db: Session, user_id: int, step_key: str) -> None:
    """Undo a claim that never delivered. success=TRUE rows are left alone."""
    row = db.execute(
        text("""
            UPDATE onboarding_email_log
               SET attempts = attempts - 1,
                   success = NULL,
                   error = NULL
             WHERE user_id = :uid AND step_key = :step
               AND success IS NULL
             RETURNING attempts
        """),
        {"uid": user_id, "step": step_key},
    ).fetchone()
    if row is not None and int(row[0]) <= 0:
        db.execute(
            text("""
                DELETE FROM onboarding_email_log
                 WHERE user_id = :uid AND step_key = :step
                   AND success IS NULL
            """),
            {"uid": user_id, "step": step_key},
        )
    db.commit()


def ensure_table(engine) -> None:
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS onboarding_email_log (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    step_key VARCHAR(50) NOT NULL,
                    sent_at TIMESTAMP DEFAULT NOW(),
                    success BOOLEAN,
                    error TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(user_id, step_key)
                )
            """))
            # Backfill columns if table pre-existed
            conn.execute(text(
                "ALTER TABLE onboarding_email_log ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0"
            ))
            conn.execute(text(
                "ALTER TABLE onboarding_email_log ADD COLUMN IF NOT EXISTS dropped_at TIMESTAMP"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_onboarding_log_user ON onboarding_email_log(user_id)"
            ))
            conn.commit()
            logger.info("Onboarding email log table ensured")
        except Exception as e:
            logger.warning(f"onboarding_email_log table create skipped: {e}")


def _mark_onboarding_dropped(db: Session, user_id: int, step_key: str) -> None:
    """Permanent drop. success stays false so this is not counted as delivered."""
    db.execute(text(MARK_DROPPED_SQL), {"uid": user_id, "step": step_key})
    db.commit()


def _step_due_at(db: Session, user_id: int, step: Step) -> datetime:
    from server.models.user import User

    user = db.query(User).filter(User.id == user_id).first()
    created = user.created_at if user is not None and user.created_at else datetime.utcnow()
    return created + timedelta(days=step.delay_days)


async def _send_step(user_id: int, email: str, name: Optional[str], step: Step, db: Session) -> bool:
    """Claim-before-send. Returns True only if this call actually delivered.

    Opt-out, the frequency cap, and hold expiry are checked before the claim
    so a skip does not burn an attempt. A step past its max delay is marked
    dropped and is not retried. If the choke point still refuses after the
    claim (a concurrent send filled the cap), the claim is released and the
    step stays eligible for a later tick.
    """
    from server.email.service import send_lifecycle_email

    campaign = f"onboarding_{step.key}"
    due_at = _step_due_at(db, user_id, step)
    try:
        if guard_enabled() and is_past_max_hold(campaign, due_at):
            _mark_onboarding_dropped(db, user_id, step.key)
            record_lifecycle_event(db, user_id, "lifecycle", campaign, "dropped_expired", "expired")
            return False
        decision = evaluate_for_user(db, user_id)
    except Exception:
        logger.exception("onboarding guard failed closed for user %s step %s", user_id, step.key)
        return False
    if not decision.allow:
        record_lifecycle_event(db, user_id, "lifecycle", campaign, f"skipped_{decision.reason}", decision.reason)
        return False

    # 1. Atomically claim the (user, step) slot. If another worker already
    #    holds it (success TRUE or attempts >= MAX), we skip.
    claim = db.execute(
        text(CLAIM_SQL),
        {"uid": user_id, "step": step.key, "maxa": MAX_ATTEMPTS},
    ).fetchone()
    db.commit()
    if not claim:
        return False  # already sent or attempts exhausted

    # 2. Build + send through the lifecycle choke point.
    try:
        unsubscribe_url = page_unsubscribe_url(user_id)
        if step.needs_name:
            subject, html = step.builder(name, unsubscribe_url)
        else:
            subject, html = step.builder(unsubscribe_url)
        result = await send_lifecycle_email(
            email,
            subject,
            html,
            category="lifecycle",
            template=campaign,
            campaign=campaign,
            user_id=user_id,
            due_at=due_at,
        )
        if result.get("reason") == "expired":
            _mark_onboarding_dropped(db, user_id, step.key)
            return False
        if result.get("skipped"):
            _release_unsent_claim(db, user_id, step.key)
            return False
        success = bool(result.get("success"))
        db.execute(
            text("""
                UPDATE onboarding_email_log
                   SET success = :ok, error = :err, sent_at = NOW()
                 WHERE user_id = :uid AND step_key = :step
            """),
            {
                "uid": user_id, "step": step.key, "ok": success,
                "err": None if success else str(result.get("error"))[:500],
            },
        )
        db.commit()
        if success:
            logger.info(f"Sent onboarding step '{step.key}' to user {user_id}")
        else:
            logger.warning(f"Onboarding step '{step.key}' to user {user_id} failed: {result.get('error')}")
        return success
    except Exception as e:
        logger.exception(f"Onboarding step '{step.key}' for user {user_id} crashed: {e}")
        try:
            db.execute(
                text("""
                    UPDATE onboarding_email_log
                       SET success = FALSE, error = :err
                     WHERE user_id = :uid AND step_key = :step
                """),
                {"uid": user_id, "step": step.key, "err": str(e)[:500]},
            )
            db.commit()
        except Exception:
            db.rollback()
        return False


async def enroll_new_signup(user_id: int, email: str, name: Optional[str]) -> None:
    """Fire the day-0 welcome email immediately on signup."""
    db = SessionLocal()
    try:
        await _send_step(user_id, email, name, SEQUENCE[0], db)
    finally:
        db.close()


async def process_pending(now: Optional[datetime] = None) -> dict:
    """Send any drip steps that are due. Idempotent."""
    now = now or datetime.utcnow()
    sent = 0
    skipped = 0
    db = SessionLocal()
    try:
        for step in SEQUENCE:
            cutoff = now - timedelta(days=step.delay_days)
            # Recently capped users stay eligible, but they should not fill the
            # LIMIT and block everyone else. The next tick after the hour retries them.
            rows = db.execute(
                text("""
                    SELECT u.id, u.email, COALESCE(u.display_name, '') AS name
                    FROM users u
                    LEFT JOIN onboarding_email_log l
                      ON l.user_id = u.id AND l.step_key = :step
                    WHERE u.created_at <= :cutoff
                      AND COALESCE(u.is_active, TRUE) = TRUE
                      AND (
                        l.id IS NULL
                        OR (
                          l.success IS NOT TRUE
                          AND l.attempts < :maxa
                          AND l.dropped_at IS NULL
                        )
                      )
                      AND u.email NOT LIKE '%@example.com'
                      AND u.email NOT LIKE '%+test%'
                      AND COALESCE((
                        SELECT np.email_enabled
                        FROM notification_preferences np
                        WHERE np.user_id = u.id
                      ), TRUE) = TRUE
                      AND NOT EXISTS (
                        SELECT 1 FROM lifecycle_email_log g
                        WHERE g.user_id = u.id
                          AND g.campaign = :campaign
                          AND g.status = 'skipped_capped'
                          AND g.created_at >= :recent
                      )
                    LIMIT 100
                """),
                {
                    "step": step.key,
                    "cutoff": cutoff,
                    "maxa": MAX_ATTEMPTS,
                    "campaign": f"onboarding_{step.key}",
                    "recent": now - timedelta(hours=1),
                },
            ).fetchall()
            for row in rows:
                ok = await _send_step(row.id, row.email, row.name or None, step, db)
                if ok:
                    sent += 1
                else:
                    skipped += 1
    finally:
        db.close()
    return {"sent": sent, "skipped": skipped, "ran_at": now.isoformat()}


async def run_scheduler_loop(interval_seconds: int = 600) -> None:
    """Background loop: process pending onboarding emails periodically."""
    logger.info(f"Onboarding scheduler started (every {interval_seconds}s)")
    while True:
        try:
            stats = await process_pending()
            if stats["sent"]:
                logger.info(f"Onboarding tick: {stats}")
        except Exception as e:
            logger.exception(f"Onboarding scheduler tick failed: {e}")
        await asyncio.sleep(interval_seconds)
