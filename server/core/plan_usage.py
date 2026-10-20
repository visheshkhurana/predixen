"""Monthly plan quotas for simulations and Copilot.

The Free plan (and Starter) already publish max_simulations_per_month and
max_copilot_messages_per_month. Nothing counted usage, so the numbers were
copy only. This reserves one unit of the current calendar month (UTC) when a
request is accepted.

A negative limit means unlimited (Growth, Scale, and the Scale trial). No
Truth Scan quota exists in plans.py; do not invent one.

There was no prior limit response. The refusal is 402 plan_limit_reached,
which is neither 403 feature_locked nor an outage.
"""
from datetime import datetime
from typing import Optional, Union

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from server.core.plans import PLAN_DETAILS, PlanTier, get_plan_limit
from server.core.subscription import get_user_subscription
from server.models.analytics_event import AnalyticsEvent

PLAN_QUOTA_SIMULATION = "plan_quota_simulation"
PLAN_QUOTA_COPILOT = "plan_quota_copilot"

_LIMIT_KEYS = {
    PLAN_QUOTA_SIMULATION: "max_simulations_per_month",
    PLAN_QUOTA_COPILOT: "max_copilot_messages_per_month",
}
_NOUNS = {
    PLAN_QUOTA_SIMULATION: "simulations",
    PLAN_QUOTA_COPILOT: "Copilot messages",
}


def month_start_utc(now: Optional[datetime] = None) -> datetime:
    now = now or datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def monthly_usage(db: Session, user_id: int, kind: str, now: Optional[datetime] = None) -> int:
    start = month_start_utc(now)
    used = (
        db.query(func.count(AnalyticsEvent.id))
        .filter(
            AnalyticsEvent.user_id == user_id,
            AnalyticsEvent.event_name == kind,
            AnalyticsEvent.created_at >= start,
        )
        .scalar()
    )
    return int(used or 0)


def reserve_monthly_quota(
    db: Session,
    user: Union[int, object],
    kind: str,
    company_id: Optional[int] = None,
) -> None:
    """Count this accepted use, or raise 402 plan_limit_reached.

    Call only once the request is actually going to run (after auth and any
    precondition such as "run a truth scan first"), so a 400 does not spend
    the month's allowance. Commits the reservation on its own so a later
    handler error cannot roll the count back.
    """
    if kind not in _LIMIT_KEYS:
        raise ValueError(f"unknown plan quota {kind}")

    if user is None:
        return

    if isinstance(user, int):
        user_id = user
    else:
        from server.core.security import is_master_user
        if is_master_user(user):
            return
        user_id = getattr(user, "id", None)

    if not user_id or int(user_id) < 0:
        return
    user_id = int(user_id)

    sub = get_user_subscription(db, user_id)
    plan = sub.get("effective_plan") or PlanTier.FREE
    limit_key = _LIMIT_KEYS[kind]
    limit = get_plan_limit(plan, limit_key)
    if limit is None or int(limit) < 0:
        return

    used = monthly_usage(db, user_id, kind)
    if used >= int(limit):
        plan_name = PLAN_DETAILS.get(plan, {}).get("name", str(plan))
        noun = _NOUNS[kind]
        raise HTTPException(
            status_code=402,
            detail={
                "error": "plan_limit_reached",
                "limit": limit_key,
                "used": used,
                "max": int(limit),
                "current_plan": plan.value if hasattr(plan, "value") else plan,
                "message": (
                    f"You've used all {int(limit)} {noun} for this month "
                    f"on the {plan_name} plan."
                ),
            },
        )

    db.add(AnalyticsEvent(
        event_name=kind,
        user_id=user_id,
        company_id=company_id,
        meta_json={"plan": plan.value if hasattr(plan, "value") else plan, "limit": limit_key},
        created_at=datetime.utcnow(),
    ))
    db.commit()
