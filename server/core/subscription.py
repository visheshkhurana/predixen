"""Subscription checking and feature gating middleware."""
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

ROUTE_FEATURE_MAP: List[tuple] = [
    (re.compile(r"/api/companies/\d+/copilot"), Feature.COPILOT),
    (re.compile(r"/api/companies/\d+/quick-chat"), Feature.COPILOT),
    (re.compile(r"/api/companies/\d+/simulations"), Feature.SIMULATIONS),
    (re.compile(r"/api/simulation/"), Feature.SIMULATIONS),
    (re.compile(r"/api/simulator/"), Feature.FLIGHT_SIMULATOR),
    (re.compile(r"/api/simulation-copilot/"), Feature.SIMULATIONS),
    (re.compile(r"/api/companies/\d+/truth-scan"), Feature.TRUTH_SCAN),
    (re.compile(r"/api/connectors/"), Feature.DATA_CONNECTORS),
    (re.compile(r"/api/companies/\d+/fundraising"), Feature.FUNDRAISING_OS),
    (re.compile(r"/api/companies/\d+/cap-table"), Feature.CAP_TABLE),
    (re.compile(r"/api/export/board-deck"), Feature.BOARD_DECK),
    (re.compile(r"/api/companies/\d+/hiring"), Feature.HIRING_PLANNER),
    (re.compile(r"/api/companies/\d+/digital-twin"), Feature.DIGITAL_TWIN),
    (re.compile(r"/api/companies/\d+/ai-graphics"), Feature.AI_GRAPHICS),
    (re.compile(r"/api/companies/\d+/investor-room"), Feature.INVESTOR_ROOM),
    (re.compile(r"/api/doc-generator/"), Feature.DOCUMENT_GENERATOR),
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


def get_user_subscription(db: Session, user_id: int) -> dict:
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
        return {
            "plan": PlanTier.FREE,
            "status": "none",
            "is_trial": False,
            "trial_days_remaining": 0,
            "is_active": False,
            "has_payment_method": False,
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
    }


def start_trial(db: Session, user_id: int) -> dict:
    now = datetime.utcnow()
    trial_end = now + timedelta(days=TRIAL_DURATION_DAYS)

    existing = db.execute(
        text("SELECT id, trial_start, trial_end, status FROM subscriptions WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1"),
        {"uid": user_id}
    ).fetchone()

    if existing:
        prev_trial_start = existing[1]
        prev_trial_end = existing[2]
        prev_status = existing[3]

        if prev_trial_start is not None:
            raise ValueError("You have already used your free trial.")

        if prev_status == "active":
            raise ValueError("You already have an active subscription.")

        db.execute(
            text("""
                UPDATE subscriptions 
                SET plan = :plan, status = 'trialing', 
                    trial_start = :start, trial_end = :end,
                    updated_at = :now
                WHERE id = :sid
            """),
            {"plan": TRIAL_PLAN, "start": now, "end": trial_end, "now": now, "sid": existing[0]}
        )
    else:
        db.execute(
            text("""
                INSERT INTO subscriptions (user_id, plan, status, trial_start, trial_end, monthly_price, created_at, updated_at)
                VALUES (:uid, :plan, 'trialing', :start, :end, 0, :now, :now)
            """),
            {"uid": user_id, "plan": TRIAL_PLAN, "start": now, "end": trial_end, "now": now}
        )
    db.commit()

    return {
        "plan": TRIAL_PLAN,
        "status": "trialing",
        "is_trial": True,
        "trial_days_remaining": TRIAL_DURATION_DAYS,
        "trial_end": trial_end.isoformat(),
        "is_active": True,
    }


def check_feature_access(feature: str):
    def dependency(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        if hasattr(current_user, 'is_master') and current_user.is_master:
            return True

        sub = get_user_subscription(db, current_user.id)
        effective_plan = sub["effective_plan"]

        if has_feature(effective_plan, feature):
            return True

        min_plan = minimum_plan_for_feature(feature)
        feature_label = FEATURE_LABELS.get(feature, feature)
        plan_name = PLAN_DETAILS.get(min_plan, {}).get("name", min_plan) if min_plan else "a paid plan"

        raise HTTPException(
            status_code=403,
            detail={
                "error": "feature_locked",
                "feature": feature,
                "feature_label": feature_label,
                "required_plan": min_plan,
                "required_plan_name": plan_name,
                "current_plan": effective_plan,
                "message": f"{feature_label} requires the {plan_name} plan or higher.",
            }
        )
    return dependency


class PaywallMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        if method in EXEMPT_METHODS:
            return await call_next(request)

        required_feature = None
        for pattern, feature in ROUTE_FEATURE_MAP:
            if pattern.search(path):
                required_feature = feature
                break

        if required_feature is None:
            return await call_next(request)

        user_id = None
        try:
            from server.core.security import decode_token, AUTH_COOKIE_NAME
            token = request.cookies.get(AUTH_COOKIE_NAME)
            if token:
                payload = decode_token(token)
                user_id = payload.get("sub") if payload else None
        except Exception:
            pass

        if not user_id:
            return await call_next(request)

        db = SessionLocal()
        try:
            sub = get_user_subscription(db, int(user_id))
            effective_plan = sub.get("effective_plan", PlanTier.FREE)
            plan_features = PLAN_DETAILS.get(effective_plan, PLAN_DETAILS[PlanTier.FREE])["features"]

            if required_feature in plan_features:
                return await call_next(request)

            min_plan = _required_plan_for_feature(required_feature)
            feature_label = FEATURE_LABELS.get(required_feature, required_feature)
            plan_name = PLAN_DETAILS.get(min_plan, {}).get("name", min_plan) if min_plan else "a paid plan"

            return JSONResponse(
                status_code=403,
                content={
                    "detail": {
                        "error": "feature_locked",
                        "feature": required_feature,
                        "feature_label": feature_label,
                        "required_plan": min_plan,
                        "required_plan_name": plan_name,
                        "current_plan": effective_plan,
                        "message": f"{feature_label} requires the {plan_name} plan or higher.",
                    }
                }
            )
        except Exception as e:
            logger.warning(f"Paywall middleware error: {e}")
            return await call_next(request)
        finally:
            db.close()
