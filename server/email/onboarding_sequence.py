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

logger = logging.getLogger(__name__)

APP_URL = os.getenv("APP_BASE_URL", "https://founderconsole.ai")


def _wrap(title: str, body_html: str, cta_label: str, cta_url: str) -> str:
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
        <a href="{APP_URL}/account/notifications" style="color:#71717a;">Manage emails</a>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


def _step_welcome(name: Optional[str]) -> tuple[str, str]:
    greeting = f"Welcome aboard, {name}." if name else "Welcome aboard."
    body = f"""<p>{greeting}</p>
<p>FounderConsole gives you investor-grade financial diligence in minutes, not weeks.
Here's the fastest path to value:</p>
<ol>
  <li><strong>Run Truth Scan</strong> on your numbers (5 min) &mdash; we find every red flag.</li>
  <li><strong>Simulate runway</strong> across 1,000 Monte Carlo paths.</li>
  <li><strong>Get a ranked decision list</strong> from your AI Copilot.</li>
</ol>
<p>Tomorrow we'll show you the single highest-leverage move most founders miss in week one.</p>"""
    return ("Welcome to FounderConsole &mdash; here's your first move",
            _wrap("Welcome to FounderConsole", body, "Open your dashboard", f"{APP_URL}/dashboard"))


def _step_truth_scan() -> tuple[str, str]:
    body = """<p>Most founders we onboard discover at least one number in their model that doesn't match their bank account.</p>
<p>Truth Scan compares what you reported against your raw data and flags discrepancies in three colors: green (clean), amber (worth reviewing), red (action required).</p>
<p>It takes <strong>about 5 minutes</strong>. Founders typically find $5K&ndash;$50K of unaccounted spend on first run.</p>"""
    return ("Run your first Truth Scan today (5 min)",
            _wrap("Find what your numbers are hiding", body, "Run Truth Scan", f"{APP_URL}/truth-scan"))


def _step_simulator() -> tuple[str, str]:
    body = """<p>You've seen your numbers. Now stress them.</p>
<p>The Simulation Engine runs 1,000 Monte Carlo paths across your burn, growth, and gross margin to answer the only question that matters: <strong>how many months until you run out of cash &mdash; and what changes that?</strong></p>
<p>Try one of these scenarios in two clicks:</p>
<ul>
  <li>What if growth slows 30%?</li>
  <li>What if you cut 20% of headcount?</li>
  <li>What if you raise $1M today?</li>
</ul>"""
    return ("Stress-test your runway in 60 seconds",
            _wrap("Simulate the scenarios that scare you", body, "Open Simulation Console", f"{APP_URL}/simulate"))


def _step_copilot() -> tuple[str, str]:
    body = """<p>Your Fund Flow Copilot has read your numbers, your simulations, and 200+ benchmark companies in your stage.</p>
<p>Ask it the questions you'd normally pay a consultant for:</p>
<ul>
  <li><em>"Where am I burning money I shouldn't be?"</em></li>
  <li><em>"What's the strongest case for our next round?"</em></li>
  <li><em>"What three moves will most extend our runway?"</em></li>
</ul>
<p>Every answer is sourced and ranked. No hallucinations &mdash; only what your data supports.</p>"""
    return ("Ask your Copilot the question that's keeping you up at night",
            _wrap("Talk to your Copilot", body, "Open Copilot", f"{APP_URL}/copilot"))


def _step_fundraising() -> tuple[str, str]:
    body = """<p>When investors ask for your model, your cap table, and your story &mdash; you should have them in one tab.</p>
<p>Fundraising OS gives you:</p>
<ul>
  <li>One-click <strong>cap table</strong> with dilution math.</li>
  <li>An AI-generated <strong>investor one-pager</strong> tuned to your stage.</li>
  <li>A live <strong>Investor Room</strong> link you can share &mdash; no PDF email chains.</li>
</ul>
<p>Even if you're not raising right now, set this up once and you'll never scramble again.</p>"""
    return ("Be raise-ready before you need to be",
            _wrap("Fundraising OS, ready in 10 minutes", body, "Open Fundraising OS", f"{APP_URL}/fundraising"))


def _step_feedback() -> tuple[str, str]:
    body = """<p>You've been on FounderConsole for a week. We'd love 90 seconds of your honest reaction.</p>
<p>Specifically:</p>
<ul>
  <li>What got you to your first "aha" moment?</li>
  <li>What confused you?</li>
  <li>What would you pay for that we don't have yet?</li>
</ul>
<p>Reply to this email &mdash; it goes straight to me. Every reply is read.</p>
<p>&mdash; The FounderConsole team</p>"""
    return ("How was your first week?",
            _wrap("Tell us what to build next", body, "Reply to this email", f"mailto:hello@founderconsole.ai"))


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
                "CREATE INDEX IF NOT EXISTS idx_onboarding_log_user ON onboarding_email_log(user_id)"
            ))
            conn.commit()
            logger.info("Onboarding email log table ensured")
        except Exception as e:
            logger.warning(f"onboarding_email_log table create skipped: {e}")


async def _send_step(user_id: int, email: str, name: Optional[str], step: Step, db: Session) -> bool:
    """Claim-before-send. Returns True only if this call actually delivered."""
    from server.email.service import send_email

    # 1. Atomically claim the (user, step) slot. If another worker already
    #    holds it (success TRUE or attempts >= MAX), we skip.
    claim = db.execute(
        text("""
            INSERT INTO onboarding_email_log (user_id, step_key, success, attempts, sent_at)
            VALUES (:uid, :step, NULL, 1, NOW())
            ON CONFLICT (user_id, step_key) DO UPDATE
                SET attempts = onboarding_email_log.attempts + 1,
                    sent_at = NOW()
                WHERE onboarding_email_log.success IS NOT TRUE
                  AND onboarding_email_log.attempts < :maxa
            RETURNING id
        """),
        {"uid": user_id, "step": step.key, "maxa": MAX_ATTEMPTS},
    ).fetchone()
    db.commit()
    if not claim:
        return False  # already sent or attempts exhausted

    # 2. Build + send.
    try:
        if step.needs_name:
            subject, html = step.builder(name)
        else:
            subject, html = step.builder()
        result = await send_email(email, subject, html, campaign=f"onboarding_{step.key}")
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
                        OR (l.success IS NOT TRUE AND l.attempts < :maxa)
                      )
                      AND u.email NOT LIKE '%@example.com'
                      AND u.email NOT LIKE '%+test%'
                    LIMIT 100
                """),
                {"step": step.key, "cutoff": cutoff, "maxa": MAX_ATTEMPTS},
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
