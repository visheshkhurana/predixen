"""Subscription lookup and (now inert) feature gating.

FounderConsole is free for everyone (see ``server.core.plans.FREE_FOR_ALL``):
``check_feature_access`` always allows and ``PaywallMiddleware`` passes every
request through. ``get_user_subscription`` still reports any legacy paid Stripe
subscription so the billing portal stays reachable for those customers.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from server.core.db import get_db, SessionLocal
from server.core.security import get_current_user
from server.core.plans import (
    PlanTier, Feature, PLAN_DETAILS, TRIAL_DURATION_DAYS, TRIAL_PLAN,
    has_feature, get_plan_limit, minimum_plan_for_feature, FEATURE_LABELS,
)

logger = logging.getLogger(__name__)

# NOTE: FastAPI sees paths WITHOUT the /api prefix (Express strips it when
# proxying), but keep the prefix optional so this works in both contexts.
#
# HAG-265: six of these patterns matched NO live route, and one of them was the
# only pattern naming a feature at all. They are listed in the order the old
# map had them, with the dead six replaced by the routes that actually exist:
#
#   companies/\d+/copilot        -> companies/\d+/chat
#   companies/\d+/simulations    -> companies/\d+/simulate + /simulation/
#   companies/\d+/truth-scan     -> companies/\d+/truth/ + /truth-scan/
#   export/board-deck            -> companies/\d+/board-export/
#   companies/\d+/digital-twin   -> companies/\d+/twin/
#   doc-generator/               -> companies/\d+/doc-generator/
#
# The two that mattered most: `POST /companies/{company_id}/chat` is the main
# Copilot call and was named by no pattern, and `POST /scenarios/{scenario_id}/simulate`
# is what the product's own scenario page calls -- the `/simulation/` patterns
# cover the v2 family, which `/scenarios` does not use.
#
# Scenario ids are matched as `[^/]+` rather than `\d+`: `/scenarios/shared/{share_uuid}`
# is a live route, so an id is not always numeric.
ROUTE_FEATURE_MAP: List[tuple] = [
    (re.compile(r"^(?:/api)?/companies/\d+/chat"), Feature.COPILOT),
    (re.compile(r"^(?:/api)?/companies/\d+/quick-chat"), Feature.COPILOT),
    (re.compile(r"^(?:/api)?/companies/\d+/simulate"), Feature.SIMULATIONS),
    (re.compile(r"^(?:/api)?/companies/\d+/simulation/"), Feature.SIMULATIONS),
    (re.compile(r"^(?:/api)?/scenarios/[^/]+/simulate"), Feature.SIMULATIONS),
    (re.compile(r"^(?:/api)?/scenarios/[^/]+/simulation/latest"), Feature.SIMULATIONS),
    (re.compile(r"^(?:/api)?/simulation/"), Feature.SIMULATIONS),
    (re.compile(r"^(?:/api)?/simulations/"), Feature.SIMULATIONS),
    (re.compile(r"^(?:/api)?/simulator/"), Feature.FLIGHT_SIMULATOR),
    (re.compile(r"^(?:/api)?/simulation-copilot/"), Feature.SIMULATIONS),
    (re.compile(r"^(?:/api)?/companies/\d+/truth/"), Feature.TRUTH_SCAN),
    (re.compile(r"^(?:/api)?/truth-scan/"), Feature.TRUTH_SCAN),
    (re.compile(r"^(?:/api)?/connectors/"), Feature.DATA_CONNECTORS),
    (re.compile(r"^(?:/api)?/companies/\d+/fundraising"), Feature.FUNDRAISING_OS),
    (re.compile(r"^(?:/api)?/companies/\d+/cap-table"), Feature.CAP_TABLE),
    (re.compile(r"^(?:/api)?/companies/\d+/board-export/"), Feature.BOARD_DECK),
    (re.compile(r"^(?:/api)?/companies/\d+/hiring"), Feature.HIRING_PLANNER),
    (re.compile(r"^(?:/api)?/companies/\d+/twin/"), Feature.DIGITAL_TWIN),
    (re.compile(r"^(?:/api)?/companies/\d+/ai-graphics"), Feature.AI_GRAPHICS),
    (re.compile(r"^(?:/api)?/companies/\d+/investor-room"), Feature.INVESTOR_ROOM),
    (re.compile(r"^(?:/api)?/companies/\d+/doc-generator/"), Feature.DOCUMENT_GENERATOR),
]

EXEMPT_METHODS = {"GET", "HEAD", "OPTIONS"}
PLAN_HIERARCHY = [PlanTier.FREE, PlanTier.STARTER, PlanTier.GROWTH, PlanTier.SCALE]


def _plan_rank(plan: str) -> int:
    try:
        idx = PLAN_HIERARCHY.index(plan)
    except ValueError:
        idx = 0
    return idx


def _required_plan_for_feature(feature: str) -> Optional[str]:
    return minimum_plan_for_feature(feature)


def _grandfather_cutoff() -> Optional[datetime]:
    """Users created before this date keep full free access (paywall launch)."""
    import os
    raw = os.getenv("PAYWALL_GRANDFATHER_BEFORE", "")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", ""))
    except ValueError:
        logger.warning(f"Invalid PAYWALL_GRANDFATHER_BEFORE value: {raw}")
        return None


def _is_grandfathered(db: Session, user_id: int) -> bool:
    cutoff = _grandfather_cutoff()
    if cutoff is None:
        return False
    try:
        row = db.execute(
            text("SELECT created_at FROM users WHERE id = :uid"),
            {"uid": user_id},
        ).fetchone()
        return bool(row and row[0] and row[0] < cutoff)
    except Exception as e:
        logger.warning(f"Grandfather check failed for user {user_id}: {e}")
        return False


def get_user_subscription(db: Session, user_id: int) -> dict:
    # Founding members: accounts created before the paywall launch keep
    # full (Scale-level) access for free, forever — unless they later buy
    # a paid plan, which takes precedence below.
    grandfathered = _is_grandfathered(db, user_id)

    row = db.execute(
        text("""
            SELECT plan, status, current_period_end, 
                   trial_start, trial_end, stripe_subscription_id
            FROM subscriptions 
            WHERE user_id = :uid 
            ORDER BY created_at DESC LIMIT 1
        """),
        {"uid": user_id}
    ).fetchone()

    if not row:
        if grandfathered:
            return {
                "plan": PlanTier.SCALE,
                "effective_plan": PlanTier.SCALE,
                "status": "grandfathered",
                "is_trial": False,
                "trial_days_remaining": 0,
                "is_active": True,
                "has_payment_method": False,
                "grandfathered": True,
            }
        return {
            "plan": PlanTier.FREE,
            "effective_plan": PlanTier.FREE,
            "status": "free",
            "is_trial": False,
            "trial_days_remaining": 0,
            "is_active": True,
            "has_payment_method": False,
            "grandfathered": False,
        }

    plan = row[0] or PlanTier.FREE
    status = row[1] or "active"
    period_end = row[2]
    trial_start = row[3]
    trial_end = row[4]
    stripe_sub_id = row[5]
    now = datetime.utcnow()

    is_trial = status == "trialing" and trial_end and now < trial_end
    trial_days_remaining = 0
    if is_trial and trial_end:
        trial_days_remaining = max(0, (trial_end - now).days)

    is_active = status in ("active", "trialing")
    if status == "trialing" and trial_end and now >= trial_end:
        is_active = False

    if status == "active" and period_end and now > period_end:
        is_active = False

    # Grandfathered users fall back to full access whenever they don't have
    # an active paid subscription (e.g. expired trial, canceled plan).
    if grandfathered and not is_active:
        return {
            "plan": PlanTier.SCALE,
            "effective_plan": PlanTier.SCALE,
            "status": "grandfathered",
            "is_trial": False,
            "trial_days_remaining": 0,
            "trial_end": None,
            "is_active": True,
            "has_payment_method": bool(stripe_sub_id),
            "current_period_end": None,
            "grandfathered": True,
        }

    return {
        "plan": plan if is_active else PlanTier.FREE,
        "effective_plan": plan if is_active else PlanTier.FREE,
        "status": status,
        "is_trial": is_trial,
        "trial_days_remaining": trial_days_remaining,
        "trial_end": trial_end.isoformat() if trial_end else None,
        "is_active": is_active,
        "has_payment_method": bool(stripe_sub_id),
        "current_period_end": period_end.isoformat() if period_end else None,
        "grandfathered": grandfathered,
    }


def start_trial(db: Session, user_id: int) -> dict:
    """Trials are gone: FounderConsole is free, so there is nothing to trial."""
    raise ValueError("FounderConsole is free — there is no trial to start.")


def check_feature_access(feature: str):
    """FastAPI dependency kept for compatibility. Every user has every feature."""
    def dependency(current_user=Depends(get_current_user)):
        return True
    return dependency


class PaywallMiddleware(BaseHTTPMiddleware):
    """Inert: FounderConsole is free, so no route is gated by plan.

    ``PAYWALL_ENABLED`` is deliberately ignored — flipping it must not lock
    users out of a product that is advertised as free. ``ROUTE_FEATURE_MAP``
    is kept as documentation of what used to be gated.
    """

    async def dispatch(self, request: Request, call_next):
        return await call_next(request)
