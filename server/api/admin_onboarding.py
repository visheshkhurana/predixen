"""Admin visibility + manual trigger for the onboarding email drip."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from server.core.db import get_db
from server.api.admin import require_platform_admin
from server.email.onboarding_sequence import SEQUENCE, process_pending, _send_step
from server.core.db import SessionLocal

router = APIRouter(prefix="/admin/onboarding", tags=["admin-onboarding"])


@router.get("/status")
def status(db: Session = Depends(get_db), _admin=Depends(require_platform_admin)):
    sent_counts = {}
    for step in SEQUENCE:
        n = db.execute(
            text("SELECT COUNT(*) FROM onboarding_email_log WHERE step_key = :s AND success = TRUE"),
            {"s": step.key},
        ).scalar() or 0
        sent_counts[step.key] = int(n)

    pending_per_step = {}
    now = datetime.utcnow()
    for step in SEQUENCE:
        cutoff = now - timedelta(days=step.delay_days)
        n = db.execute(
            text("""
                SELECT COUNT(*)
                FROM users u
                LEFT JOIN onboarding_email_log l
                  ON l.user_id = u.id AND l.step_key = :s
                WHERE u.created_at <= :cutoff
                  AND COALESCE(u.is_active, TRUE) = TRUE
                  AND l.id IS NULL
            """),
            {"s": step.key, "cutoff": cutoff},
        ).scalar() or 0
        pending_per_step[step.key] = int(n)

    recent = db.execute(
        text("""
            SELECT l.step_key, l.sent_at, l.success, u.email
            FROM onboarding_email_log l
            JOIN users u ON u.id = l.user_id
            ORDER BY l.sent_at DESC
            LIMIT 25
        """)
    ).fetchall()

    return {
        "steps": [
            {"key": s.key, "delay_days": s.delay_days, "sent": sent_counts.get(s.key, 0),
             "pending": pending_per_step.get(s.key, 0)}
            for s in SEQUENCE
        ],
        "recent": [
            {"step": r.step_key, "email": r.email, "sent_at": r.sent_at.isoformat() if r.sent_at else None,
             "success": bool(r.success)}
            for r in recent
        ],
    }


@router.post("/process-now")
async def process_now(_admin=Depends(require_platform_admin)):
    """Manually run a scheduler tick (useful for testing)."""
    stats = await process_pending()
    return stats


@router.post("/send-test/{step_key}")
async def send_test(step_key: str, to_email: str, _admin=Depends(require_platform_admin)):
    """Send a single step to an arbitrary address for visual QA."""
    step = next((s for s in SEQUENCE if s.key == step_key), None)
    if not step:
        raise HTTPException(404, f"Unknown step: {step_key}")

    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id, email, display_name FROM users WHERE email = :e"),
            {"e": to_email},
        ).fetchone()
        if not user:
            raise HTTPException(404, f"No user with email {to_email}. Test sends require an existing user (FK constraint).")
        ok = await _send_step(user.id, user.email, user.display_name, step, db)
        return {"sent": ok, "step": step_key, "to": to_email}
    finally:
        db.close()
