"""
Razorpay billing API for FounderConsole.
Handles plan listing, order creation, payment verification, webhooks, and subscription management.
"""

import hashlib
import hmac
import logging
import math
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.core.config import settings
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.subscription import Subscription, SubscriptionStatus
from server.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

# ---------------------------------------------------------------------------
# Plan definitions
# ---------------------------------------------------------------------------

PLANS = {
    "free": {
        "id": "free",
        "name": "Free Beta",
        "price_usd": 0,
        "price_monthly_usd": 0,
        "price_annual_usd": 0,
        "features": [
            "Connect key integrations",
            "Baseline forecast",
            "One scenario simulation",
            "AI explanation summary",
            "Unlimited scenarios during beta",
            "Data connectors & integrations",
            "Team collaboration",
            "Priority support",
        ],
    },
    "startup": {
        "id": "startup",
        "name": "Startup",
        "price_usd": 49,
        "price_monthly_usd": 49,
        "price_annual_usd": 468,  # 49 * 12 * ~0.8 discount
        "features": [
            "All free beta features",
            "Unlimited scenarios",
            "Investor report templates",
            "Priority support",
            "Email briefings",
            "Saved scenarios & exports",
        ],
    },
    "growth": {
        "id": "growth",
        "name": "Growth",
        "price_usd": 129,
        "price_monthly_usd": 129,
        "price_annual_usd": 1236,  # 129 * 12 * ~0.8 discount
        "features": [
            "All startup features",
            "Advanced scenario compare",
            "Team access controls",
            "Custom reporting",
            "Dedicated support",
            "API access",
        ],
    },
}


def _usd_to_paise(usd_amount: float) -> int:
    """Convert USD to Razorpay paise (INR * 100)."""
    inr = usd_amount * settings.USD_TO_INR_RATE
    return int(math.ceil(inr * 100))


def _get_razorpay_client():
    """Lazily initialize and return the Razorpay client."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway not configured. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.",
        )
    try:
        import razorpay
        return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Razorpay SDK not installed.",
        )


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CreateOrderRequest(BaseModel):
    plan_id: str
    billing_period: str = "monthly"  # monthly or annual


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan_id: str
    billing_period: str = "monthly"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/plans")
def get_plans():
    """Return available subscription plans with INR pricing."""
    plans_with_inr = []
    for plan in PLANS.values():
        p = dict(plan)
        p["price_monthly_inr"] = round(plan["price_monthly_usd"] * settings.USD_TO_INR_RATE)
        p["price_annual_inr"] = round(plan["price_annual_usd"] * settings.USD_TO_INR_RATE)
        p["price_monthly_paise"] = _usd_to_paise(plan["price_monthly_usd"])
        p["price_annual_paise"] = _usd_to_paise(plan["price_annual_usd"])
        plans_with_inr.append(p)
    return {"plans": plans_with_inr}


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str):
    """Return a single plan by ID."""
    plan = PLANS.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    p = dict(plan)
    p["price_monthly_inr"] = round(plan["price_monthly_usd"] * settings.USD_TO_INR_RATE)
    p["price_annual_inr"] = round(plan["price_annual_usd"] * settings.USD_TO_INR_RATE)
    return p


@router.post("/create-order")
def create_order(
    body: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Razorpay order for the given plan."""
    plan = PLANS.get(body.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan["price_monthly_usd"] == 0:
        raise HTTPException(status_code=400, detail="Free plan does not require payment")

    # Determine amount
    if body.billing_period == "annual":
        amount_paise = _usd_to_paise(plan["price_annual_usd"])
        description = f"{plan['name']} Plan — Annual"
    else:
        amount_paise = _usd_to_paise(plan["price_monthly_usd"])
        description = f"{plan['name']} Plan — Monthly"

    client = _get_razorpay_client()

    try:
        order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"fc_{current_user.id}_{body.plan_id}_{body.billing_period}",
            "notes": {
                "plan_id": body.plan_id,
                "billing_period": body.billing_period,
                "user_id": str(current_user.id),
                "user_email": current_user.email,
            },
        })
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to create payment order. Please try again.")

    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key_id": settings.RAZORPAY_KEY_ID,
        "plan": plan,
        "description": description,
    }


@router.post("/verify-payment")
def verify_payment(
    body: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify Razorpay payment signature and activate subscription."""
    # Verify signature: HMAC SHA256 of order_id|payment_id using key_secret
    message = f"{body.razorpay_order_id}|{body.razorpay_payment_id}"
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, body.razorpay_signature):
        logger.warning(f"Payment signature mismatch for user {current_user.id}, order {body.razorpay_order_id}")
        raise HTTPException(status_code=400, detail="Payment verification failed. Invalid signature.")

    # Look up plan
    plan = PLANS.get(body.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")

    # Determine pricing and period
    if body.billing_period == "annual":
        monthly_price = plan["price_annual_usd"] / 12
        period_end = datetime.utcnow() + timedelta(days=365)
    else:
        monthly_price = plan["price_monthly_usd"]
        period_end = datetime.utcnow() + timedelta(days=30)

    # Upsert subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()

    if subscription:
        subscription.plan = body.plan_id
        subscription.status = SubscriptionStatus.ACTIVE.value
        subscription.monthly_price = monthly_price
        subscription.razorpay_subscription_id = body.razorpay_order_id
        subscription.razorpay_payment_id = body.razorpay_payment_id
        subscription.payment_gateway = "razorpay"
        subscription.current_period_start = datetime.utcnow()
        subscription.current_period_end = period_end
        subscription.updated_at = datetime.utcnow()
    else:
        subscription = Subscription(
            user_id=current_user.id,
            plan=body.plan_id,
            status=SubscriptionStatus.ACTIVE.value,
            monthly_price=monthly_price,
            razorpay_subscription_id=body.razorpay_order_id,
            razorpay_payment_id=body.razorpay_payment_id,
            payment_gateway="razorpay",
            current_period_start=datetime.utcnow(),
            current_period_end=period_end,
        )
        db.add(subscription)

    db.commit()
    db.refresh(subscription)

    logger.info(f"Subscription activated: user={current_user.id} plan={body.plan_id} payment={body.razorpay_payment_id}")

    return {
        "status": "success",
        "subscription": {
            "id": subscription.id,
            "plan": subscription.plan,
            "status": subscription.status,
            "monthly_price": subscription.monthly_price,
            "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "payment_gateway": subscription.payment_gateway,
        },
    }


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Razorpay server-to-server webhook events."""
    body_bytes = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # Verify webhook signature
    if settings.RAZORPAY_WEBHOOK_SECRET:
        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            logger.warning("Webhook signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json
    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event", "")
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

    logger.info(f"Razorpay webhook received: event={event}")

    if event == "payment.captured":
        order_id = entity.get("order_id")
        payment_id = entity.get("id")
        if order_id:
            sub = db.query(Subscription).filter(
                Subscription.razorpay_subscription_id == order_id
            ).first()
            if sub:
                sub.status = SubscriptionStatus.ACTIVE.value
                sub.razorpay_payment_id = payment_id
                sub.updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Webhook: subscription {sub.id} confirmed via payment.captured")

    elif event == "payment.failed":
        order_id = entity.get("order_id")
        if order_id:
            sub = db.query(Subscription).filter(
                Subscription.razorpay_subscription_id == order_id
            ).first()
            if sub:
                sub.status = SubscriptionStatus.PAST_DUE.value
                sub.updated_at = datetime.utcnow()
                db.commit()
                logger.warning(f"Webhook: payment failed for subscription {sub.id}")

    elif event == "subscription.cancelled":
        sub_entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
        sub_id = sub_entity.get("id")
        if sub_id:
            sub = db.query(Subscription).filter(
                Subscription.razorpay_subscription_id == sub_id
            ).first()
            if sub:
                sub.status = SubscriptionStatus.CANCELED.value
                sub.updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Webhook: subscription {sub.id} cancelled")

    return {"status": "ok"}


@router.get("/subscription")
def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's active subscription."""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).order_by(Subscription.created_at.desc()).first()

    if not subscription:
        return {
            "plan_id": "free",
            "plan_name": "Free Beta",
            "status": "active",
            "current_period_start": datetime.utcnow().isoformat(),
            "current_period_end": None,
            "cancel_at_period_end": False,
            "payment_gateway": None,
        }

    return {
        "id": subscription.id,
        "plan_id": subscription.plan,
        "plan_name": PLANS.get(subscription.plan, {}).get("name", subscription.plan),
        "status": subscription.status,
        "monthly_price": subscription.monthly_price,
        "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
        "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        "cancel_at_period_end": False,
        "payment_gateway": subscription.payment_gateway,
    }


@router.post("/cancel")
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel the current user's subscription at end of billing period."""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE.value,
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")

    if subscription.plan == "free":
        raise HTTPException(status_code=400, detail="Cannot cancel free plan")

    subscription.status = SubscriptionStatus.CANCELED.value
    subscription.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Subscription cancelled: user={current_user.id} plan={subscription.plan}")

    return {
        "message": "Subscription cancelled. You will retain access until the end of your billing period.",
        "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
    }
