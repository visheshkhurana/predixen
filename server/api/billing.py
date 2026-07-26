import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from server.core.db import get_db, SessionLocal
from server.core.security import get_current_user
from server.core.plans import PlanTier, PLAN_DETAILS, Feature, FEATURE_LABELS, TRIAL_DURATION_DAYS, TRIAL_PLAN, minimum_plan_for_feature
from server.core.subscription import get_user_subscription, start_trial
from server.core import stripe_billing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


class SubscribeBody(BaseModel):
    interval: str = "monthly"  # "monthly" | "annual"


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
    return {"plans": plans, "payments_enabled": stripe_billing.stripe_enabled()}


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
        "payments_enabled": stripe_billing.stripe_enabled(),
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
    body: Optional[SubscribeBody] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if plan_id not in [t.value for t in PlanTier]:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan_info = PLAN_DETAILS[plan_id]
    if plan_info["price_monthly"] == 0:
        return {"message": "Free plan activated", "plan": plan_id}

    if not stripe_billing.stripe_enabled():
        raise HTTPException(
            status_code=503,
            detail="Payments are not configured yet. Please try again later.",
        )

    interval = (body.interval if body else "monthly")
    if interval not in ("monthly", "annual"):
        raise HTTPException(status_code=400, detail="interval must be 'monthly' or 'annual'")

    try:
        checkout_url = stripe_billing.create_checkout_session(db, current_user, plan_id, interval)
    except Exception as e:
        logger.error(f"Stripe checkout creation failed for user {current_user.id}: {e}")
        raise HTTPException(status_code=502, detail="Could not start checkout. Please try again.")

    return {
        "checkout_url": checkout_url,
        "plan": plan_id,
        "plan_name": plan_info["name"],
        "stripe_connected": True,
    }


@router.post("/portal")
def billing_portal(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stripe customer portal: manage payment method, invoices, cancel/switch plan."""
    if not stripe_billing.stripe_enabled():
        raise HTTPException(status_code=503, detail="Payments are not configured yet.")

    row = db.execute(
        text("SELECT stripe_customer_id FROM subscriptions WHERE user_id = :uid AND stripe_customer_id IS NOT NULL ORDER BY created_at DESC LIMIT 1"),
        {"uid": current_user.id},
    ).fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=400, detail="No billing account yet — subscribe to a plan first.")

    try:
        url = stripe_billing.create_portal_session(row[0])
    except Exception as e:
        logger.error(f"Stripe portal creation failed for user {current_user.id}: {e}")
        raise HTTPException(status_code=502, detail="Could not open billing portal. Please try again.")
    return {"portal_url": url}


@router.post("/cancel")
def cancel_subscription(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancellation is handled through the Stripe customer portal."""
    return billing_portal(current_user=current_user, db=db)


def _upsert_subscription_from_stripe(db: Session, user_id: int, sub_obj: dict, plan: Optional[str]):
    """Insert or update the local subscriptions row from a Stripe subscription object."""
    status_map = {
        "active": "active",
        "trialing": "active",  # Stripe-side trials count as active (we run our own in-app trial)
        "past_due": "past_due",
        "unpaid": "past_due",
        "canceled": "canceled",
        "incomplete": "past_due",
        "incomplete_expired": "canceled",
        "paused": "canceled",
    }
    status = status_map.get(sub_obj.get("status"), "active")
    period_end = sub_obj.get("current_period_end")
    period_start = sub_obj.get("current_period_start")
    now = datetime.utcnow()

    items = (sub_obj.get("items") or {}).get("data") or []
    monthly_price = 0.0
    if items:
        price = items[0].get("price") or {}
        amount = price.get("unit_amount") or 0
        if (price.get("recurring") or {}).get("interval") == "year":
            monthly_price = round(amount / 100 / 12, 2)
        else:
            monthly_price = amount / 100

    existing = db.execute(
        text("SELECT id FROM subscriptions WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1"),
        {"uid": user_id},
    ).fetchone()

    params = {
        "uid": user_id,
        "plan": plan or PlanTier.STARTER.value,
        "status": status,
        "ssid": sub_obj.get("id"),
        "scid": sub_obj.get("customer"),
        "pstart": datetime.utcfromtimestamp(period_start) if period_start else None,
        "pend": datetime.utcfromtimestamp(period_end) if period_end else None,
        "price": monthly_price,
        "now": now,
    }
    if existing:
        db.execute(
            text("""
                UPDATE subscriptions
                SET plan = :plan, status = :status,
                    stripe_subscription_id = :ssid, stripe_customer_id = :scid,
                    current_period_start = :pstart, current_period_end = :pend,
                    monthly_price = :price, updated_at = :now
                WHERE id = :sid
            """),
            {**params, "sid": existing[0]},
        )
    else:
        db.execute(
            text("""
                INSERT INTO subscriptions
                    (user_id, plan, status, stripe_subscription_id, stripe_customer_id,
                     current_period_start, current_period_end, monthly_price, created_at, updated_at)
                VALUES (:uid, :plan, :status, :ssid, :scid, :pstart, :pend, :price, :now, :now)
            """),
            params,
        )
    db.commit()
    logger.info(f"Billing: user {user_id} → plan={params['plan']} status={status}")


def _user_id_from_subscription(sub_obj: dict) -> Optional[int]:
    meta = sub_obj.get("metadata") or {}
    if meta.get("fc_user_id"):
        try:
            return int(meta["fc_user_id"])
        except (TypeError, ValueError):
            pass
    return None


def _user_id_from_customer(db: Session, customer_id: str) -> Optional[int]:
    row = db.execute(
        text("SELECT user_id FROM subscriptions WHERE stripe_customer_id = :cid ORDER BY created_at DESC LIMIT 1"),
        {"cid": customer_id},
    ).fetchone()
    return row[0] if row else None


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook endpoint. CSRF-exempt; authenticated by signature."""
    if not stripe_billing.stripe_enabled():
        raise HTTPException(status_code=503, detail="Payments not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe_billing.verify_webhook(payload, sig)
    except Exception as e:
        logger.warning(f"Stripe webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    etype = event["type"]
    obj = event["data"]["object"]
    db = SessionLocal()
    try:
        if etype == "checkout.session.completed" and obj.get("mode") == "subscription":
            import stripe as _stripe
            sub_obj = _stripe.Subscription.retrieve(obj["subscription"])
            user_id = _user_id_from_subscription(sub_obj)
            if user_id is None and obj.get("client_reference_id"):
                try:
                    user_id = int(obj["client_reference_id"])
                except (TypeError, ValueError):
                    user_id = None
            plan = (sub_obj.get("metadata") or {}).get("fc_plan")
            if not plan:
                items = (sub_obj.get("items") or {}).get("data") or []
                if items:
                    plan = stripe_billing.plan_from_price(items[0].get("price") or {})
            if user_id:
                _upsert_subscription_from_stripe(db, user_id, sub_obj, plan)
            else:
                logger.error(f"Webhook: could not resolve user for checkout session {obj.get('id')}")

        elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
            user_id = _user_id_from_subscription(obj) or _user_id_from_customer(db, obj.get("customer"))
            plan = (obj.get("metadata") or {}).get("fc_plan")
            if not plan:
                items = (obj.get("items") or {}).get("data") or []
                if items:
                    plan = stripe_billing.plan_from_price(items[0].get("price") or {})
            if user_id:
                if etype == "customer.subscription.deleted":
                    obj = {**obj, "status": "canceled"}
                _upsert_subscription_from_stripe(db, user_id, obj, plan)
            else:
                logger.error(f"Webhook: could not resolve user for subscription {obj.get('id')}")

        elif etype == "invoice.payment_failed":
            customer_id = obj.get("customer")
            user_id = _user_id_from_customer(db, customer_id) if customer_id else None
            if user_id:
                db.execute(
                    text("UPDATE subscriptions SET status = 'past_due', updated_at = :now WHERE user_id = :uid"),
                    {"uid": user_id, "now": datetime.utcnow()},
                )
                db.commit()
                logger.warning(f"Billing: payment failed for user {user_id} — marked past_due")
    finally:
        db.close()

    return {"received": True}


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
