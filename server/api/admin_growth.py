"""Growth analytics dashboard for admin."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
from typing import List, Dict, Any

from server.core.db import get_db
from server.models import User, LoginHistory
from server.api.admin import require_platform_admin

router = APIRouter(prefix="/admin/growth", tags=["admin-growth"])


def _safe_count(db: Session, sql: str, params: dict | None = None) -> int:
    try:
        result = db.execute(text(sql), params or {}).scalar()
        return int(result or 0)
    except Exception:
        return 0


def _safe_rows(db: Session, sql: str, params: dict | None = None) -> List[Dict[str, Any]]:
    try:
        result = db.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]
    except Exception:
        return []


@router.get("/funnel")
def growth_funnel(db: Session = Depends(get_db), _admin=Depends(require_platform_admin)):
    """Top-level acquisition funnel + key conversion rates."""
    now = datetime.utcnow()
    last_30 = now - timedelta(days=30)
    last_7 = now - timedelta(days=7)

    sim_runs_30d = _safe_count(
        db,
        "SELECT COUNT(*) FROM survival_simulations WHERE created_at >= :since",
        {"since": last_30},
    )
    sim_runs_7d = _safe_count(
        db,
        "SELECT COUNT(*) FROM survival_simulations WHERE created_at >= :since",
        {"since": last_7},
    )
    sim_runs_total = _safe_count(db, "SELECT COUNT(*) FROM survival_simulations")

    total_users = db.query(func.count(User.id)).scalar() or 0
    signups_30d = (
        db.query(func.count(User.id)).filter(User.created_at >= last_30).scalar() or 0
    )
    signups_7d = (
        db.query(func.count(User.id)).filter(User.created_at >= last_7).scalar() or 0
    )
    activated = (
        db.query(func.count(User.id))
        .filter(User.is_email_verified.is_(True))
        .scalar()
        or 0
    )

    distinct_logins_30d = (
        db.query(func.count(func.distinct(LoginHistory.user_id)))
        .filter(LoginHistory.created_at >= last_30, LoginHistory.success.is_(True))
        .scalar()
        or 0
    )
    distinct_logins_7d = (
        db.query(func.count(func.distinct(LoginHistory.user_id)))
        .filter(LoginHistory.created_at >= last_7, LoginHistory.success.is_(True))
        .scalar()
        or 0
    )

    sim_to_signup = (signups_30d / sim_runs_30d * 100.0) if sim_runs_30d else 0.0
    signup_to_active = (
        distinct_logins_30d / signups_30d * 100.0 if signups_30d else 0.0
    )
    activation_rate = (activated / total_users * 100.0) if total_users else 0.0

    funnel = [
        {"stage": "Survival sims (30d)", "count": sim_runs_30d},
        {"stage": "Signups (30d)", "count": int(signups_30d)},
        {"stage": "Email verified", "count": int(activated)},
        {"stage": "Active 30d (logged in)", "count": int(distinct_logins_30d)},
    ]

    return {
        "summary": {
            "total_users": int(total_users),
            "signups_7d": int(signups_7d),
            "signups_30d": int(signups_30d),
            "active_7d": int(distinct_logins_7d),
            "active_30d": int(distinct_logins_30d),
            "sim_runs_total": sim_runs_total,
            "sim_runs_7d": sim_runs_7d,
            "sim_runs_30d": sim_runs_30d,
        },
        "rates": {
            "sim_to_signup_pct": round(sim_to_signup, 1),
            "signup_to_active_pct": round(signup_to_active, 1),
            "activation_pct": round(activation_rate, 1),
        },
        "funnel": funnel,
        "generated_at": now.isoformat(),
    }


@router.get("/timeseries")
def growth_timeseries(
    days: int = 30, db: Session = Depends(get_db), _admin=Depends(require_platform_admin)
):
    """Daily counts of signups, sim runs, and active users for the last N days."""
    days = max(1, min(days, 180))
    now = datetime.utcnow()
    since = now - timedelta(days=days)

    signups = _safe_rows(
        db,
        """
        SELECT DATE(created_at) AS day, COUNT(*) AS n
        FROM users
        WHERE created_at >= :since
        GROUP BY DATE(created_at)
        ORDER BY day
        """,
        {"since": since},
    )
    sims = _safe_rows(
        db,
        """
        SELECT DATE(created_at) AS day, COUNT(*) AS n
        FROM survival_simulations
        WHERE created_at >= :since
        GROUP BY DATE(created_at)
        ORDER BY day
        """,
        {"since": since},
    )
    logins = _safe_rows(
        db,
        """
        SELECT DATE(created_at) AS day, COUNT(DISTINCT user_id) AS n
        FROM login_history
        WHERE created_at >= :since AND success = TRUE
        GROUP BY DATE(created_at)
        ORDER BY day
        """,
        {"since": since},
    )

    by_day: Dict[str, Dict[str, Any]] = {}
    for d in range(days + 1):
        day = (since + timedelta(days=d)).date().isoformat()
        by_day[day] = {"day": day, "signups": 0, "sims": 0, "active": 0}

    for r in signups:
        key = str(r["day"])
        if key in by_day:
            by_day[key]["signups"] = int(r["n"])
    for r in sims:
        key = str(r["day"])
        if key in by_day:
            by_day[key]["sims"] = int(r["n"])
    for r in logins:
        key = str(r["day"])
        if key in by_day:
            by_day[key]["active"] = int(r["n"])

    return {"days": days, "series": list(by_day.values())}


@router.get("/cohorts")
def signup_cohorts(
    weeks: int = 8, db: Session = Depends(get_db), _admin=Depends(require_platform_admin)
):
    """Weekly signup cohorts with week-N return retention."""
    weeks = max(2, min(weeks, 16))
    now = datetime.utcnow()
    since = now - timedelta(weeks=weeks)

    rows = _safe_rows(
        db,
        """
        SELECT
            DATE_TRUNC('week', u.created_at) AS cohort_week,
            COUNT(DISTINCT u.id) AS cohort_size,
            COUNT(DISTINCT CASE WHEN lh.created_at >= u.created_at + INTERVAL '7 days'
                  AND lh.created_at < u.created_at + INTERVAL '14 days' AND lh.success = TRUE
                  THEN u.id END) AS w1,
            COUNT(DISTINCT CASE WHEN lh.created_at >= u.created_at + INTERVAL '14 days'
                  AND lh.created_at < u.created_at + INTERVAL '21 days' AND lh.success = TRUE
                  THEN u.id END) AS w2,
            COUNT(DISTINCT CASE WHEN lh.created_at >= u.created_at + INTERVAL '21 days'
                  AND lh.created_at < u.created_at + INTERVAL '28 days' AND lh.success = TRUE
                  THEN u.id END) AS w3
        FROM users u
        LEFT JOIN login_history lh ON lh.user_id = u.id
        WHERE u.created_at >= :since
        GROUP BY cohort_week
        ORDER BY cohort_week
        """,
        {"since": since},
    )

    cohorts = []
    for r in rows:
        size = int(r.get("cohort_size") or 0) or 1
        cohorts.append(
            {
                "cohort_week": str(r.get("cohort_week"))[:10],
                "cohort_size": int(r.get("cohort_size") or 0),
                "w1_pct": round(int(r.get("w1") or 0) / size * 100.0, 1),
                "w2_pct": round(int(r.get("w2") or 0) / size * 100.0, 1),
                "w3_pct": round(int(r.get("w3") or 0) / size * 100.0, 1),
            }
        )
    return {"cohorts": cohorts}


@router.get("/top-pages")
def top_pages(db: Session = Depends(get_db), _admin=Depends(require_platform_admin)):
    """Top entry pages from analytics_events (if instrumented). Empty if none."""
    rows = _safe_rows(
        db,
        """
        SELECT
            COALESCE(meta_json->>'path', meta_json->>'page', 'unknown') AS path,
            COUNT(*) AS hits
        FROM analytics_events
        WHERE event_name IN ('page_view', '$pageview')
          AND created_at >= NOW() - INTERVAL '30 days'
        GROUP BY 1
        ORDER BY hits DESC
        LIMIT 20
        """,
    )
    return {"pages": [{"path": r["path"], "hits": int(r["hits"])} for r in rows]}
