from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.plans import PlanTier, PLAN_DETAILS, Feature, FEATURE_LABELS, TRIAL_DURATION_DAYS, TRIAL_PLAN, minimum_plan_for_feature
from server.core.subscription import get_user_subscription, start_trial

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans")
def get_plans():
    plans = []
    for tier in [PlanTier.FREE, PlanTier.STARTER, PlanTier.GROWTH, PlanTier.SCALE]:
        info = PLAN_DETAILS[tier]
        plans.append({
            "id": tier.value,
            "name": info["name"],
            "price_monthly": info["price_monthly"],
            "price_annual": info["price_annual"],
            "tagline": info["tagline"],
            "max_companies": info["max_companies"],
            "max_simulations_per_month": info["max_simulations_per_month"],
            "max_copilot_messages_per_month": info["max_copilot_messages_per_month"],
            "max_connectors": info["max_connectors"],
            "highlights": info["highlights"],
            "features": [f.value for f in info["features"]],
        })
    return {"plans": plans}


@router.get("/subscription")
def get_subscription(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = get_user_subscription(db, current_user.id)
    plan_info = PLAN_DETAILS.get(sub["plan"], PLAN_DETAILS[PlanTier.FREE])
    return {
        **sub,
        "plan_name": plan_info["name"],
        "plan_price": plan_info["price_monthly"],
        "plan_highlights": plan_info["highlights"],
        "trial_duration_days": TRIAL_DURATION_DAYS,
    }


@router.post("/start-trial")
def api_start_trial(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = start_trial(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": f"Your {TRIAL_DURATION_DAYS}-day free trial has started!",
        **result,
    }


@router.post("/subscribe/{plan_id}")
def subscribe(
    plan_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if plan_id not in [t.value for t in PlanTier]:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan_info = PLAN_DETAILS[plan_id]

    if plan_info["price_monthly"] == 0:
        return {"message": "Free plan activated", "plan": plan_id}

    return {
        "message": "Stripe checkout required — connect Stripe to enable payments.",
        "checkout_url": None,
        "plan": plan_id,
        "plan_name": plan_info["name"],
        "price_monthly": plan_info["price_monthly"],
        "stripe_connected": False,
    }


@router.post("/cancel")
def cancel_subscription(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "message": "Subscription will cancel at end of billing period",
        "cancel_at_period_end": True,
    }


@router.get("/feature-access/{feature}")
def check_feature(
    feature: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = get_user_subscription(db, current_user.id)
    plan_features = PLAN_DETAILS.get(sub["plan"], PLAN_DETAILS[PlanTier.FREE])["features"]
    has_access = feature in [f.value if hasattr(f, 'value') else f for f in plan_features]

    min_plan = minimum_plan_for_feature(feature)
    feature_label = FEATURE_LABELS.get(feature, feature)

    return {
        "feature": feature,
        "has_access": has_access,
        "current_plan": sub["plan"],
        "required_plan": min_plan,
        "feature_label": feature_label,
        "is_trial": sub["is_trial"],
        "trial_days_remaining": sub["trial_days_remaining"],
    }
