import hashlib
import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from server.core.db import get_db, SessionLocal
from server.core.security import get_current_user
from server.core.plans import (
    PlanTier, PLAN_DETAILS, Feature, FEATURE_LABELS, TRIAL_DURATION_DAYS, TRIAL_PLAN,
    minimum_plan_for_feature, ANNUAL_LABEL, ANNUAL_MULTIPLIER, CURRENCY_SYMBOLS,
    get_regional_price, normalize_currency, regional_tiers,
)
from server.core.subscription import get_user_subscription, start_trial
from server.core import stripe_billing
from server.core import razorpay_billing
from server.core.billing_region import resolve_currency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


class SubscribeBody(BaseModel):
    interval: str = "monthly"  # "monthly" | "annual"
    # No currency or amount field on purpose: the Razorpay charge currency is
    # decided by the server from the company's currency setting.


# ---------------------------------------------------------------------------
# Provider selection
#
# BILLING_PROVIDER=razorpay plus all three RAZORPAY_* secrets -> Razorpay.
# Anything else -> Stripe, exactly as before (itself off unless
# STRIPE_SECRET_KEY is set). With no billing env vars, payments stay off.
# ---------------------------------------------------------------------------

def billing_provider() -> str:
    return "razorpay" if razorpay_billing.razorpay_enabled() else "stripe"


def payments_enabled() -> bool:
    if billing_provider() == "razorpay":
        return True
    return stripe_billing.stripe_enabled()


def _optional_user_id(request: Request) -> Optional[int]:
    """Best-effort user id for a public endpoint. Used only to pick a display currency."""
    try:
        from server.core.security import decode_token, AUTH_COOKIE_NAME
        token = None
        authz = request.headers.get("authorization") or ""
        if authz.lower().startswith("bearer "):
            token = authz[7:].strip()
        token = token or request.cookies.get(AUTH_COOKIE_NAME)
        payload = decode_token(token) if token else None
        return _parse_user_id((payload or {}).get("sub"))
    except Exception:
        return None


def _display_currency(user_id: Optional[int], requested: Optional[str]) -> str:
    """Currency for the plan list. Signed-in users see what they will be
    charged (company currency). Signed-out visitors may pass ?currency= to
    preview a price; it never reaches checkout."""
    if user_id is None:
        return normalize_currency(requested) or "USD"
    db = SessionLocal()
    try:
        return resolve_currency(db, user_id)[0]
    finally:
        db.close()


@router.get("/plans")
def get_plans(request: Request, currency: Optional[str] = None):
    provider = billing_provider()
    display_currency = "USD"
    offered = None
    if provider == "razorpay":
        display_currency = _display_currency(_optional_user_id(request), currency)
        offered = set(regional_tiers(display_currency))

    plans = []
    for tier in [PlanTier.FREE, PlanTier.STARTER, PlanTier.GROWTH, PlanTier.SCALE]:
        info = PLAN_DETAILS[tier]
        price_monthly = info["price_monthly"]
        price_annual = info["price_annual"]
        if offered is not None and tier != PlanTier.FREE:
            # Razorpay: only tiers with a regional price are sold.
            if tier.value not in offered:
                continue
            price_monthly = get_regional_price(tier.value, display_currency, "monthly")["amount"]
            price_annual = get_regional_price(tier.value, display_currency, "annual")["amount"]
        plans.append({
            "id": tier.value,
            "name": info["name"],
            "price_monthly": price_monthly,
            "price_annual": price_annual,
            "tagline": info["tagline"],
            "max_companies": info["max_companies"],
            "max_simulations_per_month": info["max_simulations_per_month"],
            "max_copilot_messages_per_month": info["max_copilot_messages_per_month"],
            "max_connectors": info["max_connectors"],
            "highlights": info["highlights"],
            "features": [f.value for f in info["features"]],
        })
    return {
        "plans": plans,
        "payments_enabled": payments_enabled(),
        "provider": provider,
        "currency": display_currency,
        "currency_symbol": CURRENCY_SYMBOLS.get(display_currency, ""),
        "annual_label": ANNUAL_LABEL,
        "annual_multiplier": ANNUAL_MULTIPLIER,
    }


@router.get("/subscription")
def get_subscription(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = get_user_subscription(db, current_user.id)
    plan_info = PLAN_DETAILS.get(sub["plan"], PLAN_DETAILS[PlanTier.FREE])
    provider = billing_provider()
    result = {
        **sub,
        "plan_name": plan_info["name"],
        "plan_price": plan_info["price_monthly"],
        "plan_highlights": plan_info["highlights"],
        "trial_duration_days": TRIAL_DURATION_DAYS,
        "payments_enabled": payments_enabled(),
        "provider": provider,
        "currency": "USD",
    }
    if provider == "razorpay":
        rz = _active_razorpay_subscription(db, current_user.id)
        if rz:
            monthly = get_regional_price(rz["plan"], rz["currency"], "monthly")
            result["currency"] = rz["currency"]
            result["plan_price"] = monthly["amount"] if monthly else rz["amount"]
            result["has_payment_method"] = True
            result["razorpay_subscription_id"] = rz["razorpay_subscription_id"]
        else:
            result["currency"] = resolve_currency(db, current_user.id)[0]
    return result


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

    if billing_provider() == "razorpay":
        return _razorpay_subscribe(plan_id, body, current_user, db)

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
    """Stripe: cancellation goes through the customer portal.
    Razorpay: cancel the active subscription at the end of the current cycle."""
    if billing_provider() == "razorpay":
        return _razorpay_cancel(current_user, db)
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
    # Stripe API 2025+ moved billing periods onto subscription items.
    if not period_end:
        _items = (sub_obj.get("items") or {}).get("data") or []
        if _items:
            period_start = period_start or _items[0].get("current_period_start")
            period_end = _items[0].get("current_period_end")
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


def _parse_user_id(value) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    try:
        user_id = int(value)
    except (TypeError, ValueError):
        return None
    if user_id <= 0:
        return None
    return user_id


def _metadata_user_id(meta) -> Optional[int]:
    if not isinstance(meta, dict):
        return None
    return _parse_user_id(meta.get("fc_user_id"))


def _stripe_id(value) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        return _stripe_id(value.get("id"))
    return None


def _user_exists(db: Session, user_id: int) -> bool:
    row = db.execute(
        text("SELECT 1 FROM users WHERE id = :uid"),
        {"uid": user_id},
    ).fetchone()
    return row is not None


def _accept_user_id(db: Session, user_id: Optional[int]) -> Optional[int]:
    if user_id is None or not _user_exists(db, user_id):
        return None
    return user_id


def _user_id_from_email(db: Session, email: Optional[str]) -> Optional[int]:
    if not isinstance(email, str) or not email.strip():
        return None
    row = db.execute(
        text("SELECT id FROM users WHERE lower(email) = lower(:email) LIMIT 1"),
        {"email": email.strip()},
    ).fetchone()
    return row[0] if row else None


def _candidate_emails(obj: dict, customer: dict) -> list:
    found = []
    seen = set()
    details = obj.get("customer_details") if isinstance(obj.get("customer_details"), dict) else {}
    for raw in (
        (customer or {}).get("email"),
        details.get("email"),
        obj.get("customer_email"),
    ):
        if not isinstance(raw, str):
            continue
        email = raw.strip()
        if not email:
            continue
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append(email)
    return found


def _retrieve_customer(customer_id: str) -> dict:
    try:
        import stripe as _stripe
        customer = stripe_billing.to_plain(_stripe.Customer.retrieve(customer_id)) or {}
    except Exception as e:
        logger.warning(f"Stripe customer retrieve failed for {customer_id}: {e}")
        return {}
    return customer if isinstance(customer, dict) else {}


def _resolve_checkout_user(db: Session, obj: dict, sub_obj: dict) -> dict:
    """Match a verified checkout to a local user.

    Order: subscription metadata, client_reference_id, checkout session
    metadata, an existing stripe_customer_id row, then the Stripe customer's
    metadata and email, then the email collected on the checkout session.
    A metadata id that does not match a users row falls through so a stale
    id cannot block the email fallback.
    """
    customer_id = _stripe_id(obj.get("customer")) or _stripe_id(sub_obj.get("customer"))
    customer: dict = {}
    context = {"user_id": None, "customer_id": customer_id, "email": None, "customer": customer}

    for candidate in (
        _metadata_user_id(sub_obj.get("metadata")),
        _parse_user_id(obj.get("client_reference_id")),
        _metadata_user_id(obj.get("metadata")),
    ):
        user_id = _accept_user_id(db, candidate)
        if user_id:
            context["user_id"] = user_id
            return context

    if customer_id:
        user_id = _accept_user_id(db, _user_id_from_customer(db, customer_id))
        if user_id:
            context["user_id"] = user_id
            return context
        customer = _retrieve_customer(customer_id)
        context["customer"] = customer
        user_id = _accept_user_id(db, _metadata_user_id(customer.get("metadata")))
        if user_id:
            context["user_id"] = user_id
            return context

    emails = _candidate_emails(obj, customer)
    if emails:
        context["email"] = emails[0]
    for email in emails:
        user_id = _user_id_from_email(db, email)
        if user_id:
            context["user_id"] = user_id
            context["email"] = email
            return context
    return context


def _persist_unresolved_checkout(db: Session, event: dict, obj: dict, sub_obj: dict, context: dict) -> None:
    """Store a verified checkout we could not attach, so it can be reconciled.

    The table is created on first use. Stripe retries this event while we
    return non-2xx; the stripe_event_id unique key keeps those retries to one row.
    """
    from server.models.stripe_reconciliation import StripeReconciliationEvent

    StripeReconciliationEvent.__table__.create(bind=db.get_bind(), checkfirst=True)
    event_id = event.get("id") or (f"checkout:{obj.get('id')}" if obj.get("id") else None)
    if not event_id:
        raise RuntimeError("checkout event has no id to persist")

    subscription_id = _stripe_id(obj.get("subscription")) or sub_obj.get("id")
    payload = {
        "event_id": event.get("id"),
        "event_type": event.get("type"),
        "checkout_session_id": obj.get("id"),
        "subscription_id": subscription_id,
        "customer_id": context.get("customer_id"),
        "customer_email": context.get("email"),
        "client_reference_id": obj.get("client_reference_id"),
        "session_metadata": obj.get("metadata") or {},
        "subscription_metadata": sub_obj.get("metadata") or {},
        "customer_metadata": (context.get("customer") or {}).get("metadata") or {},
    }
    now = datetime.utcnow()
    params = {
        "eid": str(event_id),
        "etype": event.get("type") or "checkout.session.completed",
        "oid": obj.get("id"),
        "cid": context.get("customer_id"),
        "email": context.get("email"),
        "payload": json.dumps(payload, default=str),
        "reason": "unresolved_user",
        "now": now,
    }
    db.execute(
        text("""
            INSERT INTO stripe_reconciliation_events
                (stripe_event_id, event_type, stripe_object_id, customer_id, customer_email,
                 payload_json, reason, status, created_at, updated_at)
            VALUES
                (:eid, :etype, :oid, :cid, :email, :payload, :reason, 'open', :now, :now)
            ON CONFLICT (stripe_event_id) DO UPDATE SET
                event_type = excluded.event_type,
                stripe_object_id = excluded.stripe_object_id,
                customer_id = excluded.customer_id,
                customer_email = excluded.customer_email,
                payload_json = excluded.payload_json,
                reason = excluded.reason,
                status = 'open',
                updated_at = excluded.updated_at
        """),
        params,
    )
    db.commit()


def _mark_checkout_reconciled(db: Session, event_id: Optional[str]) -> None:
    """Close an open reconciliation row once a retry finally resolves the user."""
    if not event_id:
        return
    try:
        db.execute(
            text("""
                UPDATE stripe_reconciliation_events
                SET status = 'resolved', updated_at = :now
                WHERE stripe_event_id = :eid
            """),
            {"eid": str(event_id), "now": datetime.utcnow()},
        )
        db.commit()
    except Exception:
        db.rollback()


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook endpoint. CSRF-exempt; authenticated by signature.

    checkout.session.completed is matched to a user via subscription metadata
    (fc_user_id), client_reference_id, checkout session metadata, a stored
    stripe customer id, the Stripe customer's metadata, then the customer or
    session email. If none of those resolve to a local user, the event is
    stored in stripe_reconciliation_events and this handler returns 500.

    Stripe retries any non-2xx response. Returning {"received": true} would
    acknowledge the paid checkout and the subscription would never be written.
    """
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
    # StripeObject (SDK v15+) is not a dict — normalize to plain dicts up front.
    obj = stripe_billing.to_plain(event["data"]["object"])
    db = SessionLocal()
    unresolved_checkout = False
    try:
        if etype == "checkout.session.completed" and obj.get("mode") == "subscription":
            import stripe as _stripe
            sub_obj = stripe_billing.to_plain(_stripe.Subscription.retrieve(obj["subscription"]))
            if not isinstance(sub_obj, dict):
                sub_obj = {}
            resolved = _resolve_checkout_user(db, obj, sub_obj)
            user_id = resolved.get("user_id")
            plan = (sub_obj.get("metadata") or {}).get("fc_plan")
            if not plan:
                items = (sub_obj.get("items") or {}).get("data") or []
                if items:
                    plan = stripe_billing.plan_from_price(items[0].get("price") or {})
            if user_id:
                _upsert_subscription_from_stripe(db, user_id, sub_obj, plan)
                _mark_checkout_reconciled(db, event.get("id"))
            else:
                try:
                    _persist_unresolved_checkout(db, event, obj, sub_obj, resolved)
                except Exception:
                    logger.exception(
                        f"Webhook: failed to persist unresolved checkout session {obj.get('id')}"
                    )
                logger.error(
                    "Webhook: checkout.session.completed "
                    f"{obj.get('id')} (event {event.get('id')}) could not be matched to a user "
                    f"(customer={resolved.get('customer_id')} email={resolved.get('email')}). "
                    "Persisted for reconciliation; returning 500 so Stripe retries."
                )
                unresolved_checkout = True

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

    if unresolved_checkout:
        # Non-2xx on purpose. Stripe will not retry a 2xx, and the subscription
        # row is still missing until a later delivery can be matched.
        raise HTTPException(
            status_code=500,
            detail="Checkout could not be matched to a user and was saved for reconciliation. Stripe should retry.",
        )

    return {"received": True}


# ---------------------------------------------------------------------------
# Razorpay
#
# Flow: POST /billing/subscribe/{plan} creates a Razorpay subscription for the
# server-chosen (tier, currency, interval) plan id and returns
# {subscription_id, key_id} for Razorpay Checkout. After payment the client
# posts the handler response to /billing/razorpay/verify; the signature is
# checked and the subscription is re-fetched from Razorpay. Access changes
# only from that fetched state or from a signature-verified webhook at
# /billing/razorpay/webhook. Amounts and plans from the client are ignored.
# ---------------------------------------------------------------------------

class RazorpayVerifyBody(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


# Razorpay subscription status -> local subscriptions.status. None = no change
# (created/authenticated: no money has moved yet, so no access is granted).
RAZORPAY_STATUS_MAP = {
    "created": None,
    "authenticated": None,
    "active": "active",
    "pending": "past_due",
    "halted": "past_due",
    "cancelled": "canceled",
    "completed": "canceled",
    "expired": "canceled",
}

# Fallback when the payload carries no subscription status.
RAZORPAY_EVENT_STATUS = {
    "subscription.activated": "active",
    "subscription.charged": "active",
    "subscription.resumed": "active",
    "subscription.pending": "past_due",
    "subscription.halted": "past_due",
    "subscription.cancelled": "canceled",
    "subscription.completed": "canceled",
}

RZ_SUB_COLUMNS = (
    "id, user_id, razorpay_subscription_id, razorpay_customer_id, razorpay_plan_id, "
    "plan, interval, currency, amount, status, last_event_at"
)


def _rz_row_to_dict(row) -> Optional[dict]:
    if not row:
        return None
    keys = [k.strip() for k in RZ_SUB_COLUMNS.split(",")]
    return dict(zip(keys, row))


def _rz_by_subscription_id(db: Session, subscription_id: Optional[str]) -> Optional[dict]:
    if not subscription_id:
        return None
    row = db.execute(
        text(f"SELECT {RZ_SUB_COLUMNS} FROM razorpay_subscriptions WHERE razorpay_subscription_id = :sid"),
        {"sid": subscription_id},
    ).fetchone()
    return _rz_row_to_dict(row)


def _active_razorpay_subscription(db: Session, user_id: int) -> Optional[dict]:
    try:
        row = db.execute(
            text(f"""SELECT {RZ_SUB_COLUMNS} FROM razorpay_subscriptions
                     WHERE user_id = :uid AND status = 'active'
                     ORDER BY id DESC LIMIT 1"""),
            {"uid": user_id},
        ).fetchone()
    except Exception:
        db.rollback()
        return None
    return _rz_row_to_dict(row)


def _latest_razorpay_customer_id(db: Session, user_id: int) -> Optional[str]:
    row = db.execute(
        text("""SELECT razorpay_customer_id FROM razorpay_subscriptions
                WHERE user_id = :uid AND razorpay_customer_id IS NOT NULL
                ORDER BY id DESC LIMIT 1"""),
        {"uid": user_id},
    ).fetchone()
    return row[0] if row else None


def _ts(value) -> Optional[datetime]:
    if value in (None, "", 0):
        return None
    try:
        return datetime.utcfromtimestamp(int(value))
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _apply_razorpay_state(db: Session, rz: dict, local_status: Optional[str], entity: dict,
                          event_at: Optional[int] = None) -> bool:
    """Write verified Razorpay state to razorpay_subscriptions and subscriptions.

    Does not commit; the caller owns the transaction. Returns True if applied.
    """
    entity = entity if isinstance(entity, dict) else {}
    if event_at is not None and rz.get("last_event_at") and int(event_at) < int(rz["last_event_at"]):
        logger.info(
            f"Razorpay: ignoring out-of-order event for {rz['razorpay_subscription_id']} "
            f"({event_at} < {rz['last_event_at']})"
        )
        return False

    # Tier comes from the plan Razorpay is charging, else from the row the
    # server wrote at checkout. Never from the client.
    plan = rz["plan"]
    currency = rz["currency"]
    interval = rz["interval"]
    mapped = razorpay_billing.tier_for_plan_id(entity.get("plan_id"))
    if mapped:
        if mapped["tier"] != plan:
            logger.warning(
                f"Razorpay: subscription {rz['razorpay_subscription_id']} plan_id maps to "
                f"{mapped['tier']}, row says {plan}; using the plan_id"
            )
        plan, currency, interval = mapped["tier"], mapped["currency"], mapped["interval"]

    now = datetime.utcnow()
    rz_status = entity.get("status") or {
        "active": "active", "past_due": "halted", "canceled": "cancelled",
    }.get(local_status or "")
    db.execute(
        text("""UPDATE razorpay_subscriptions
                SET status = COALESCE(:status, status), plan = :plan, currency = :currency,
                    interval = :interval,
                    razorpay_customer_id = COALESCE(:cid, razorpay_customer_id),
                    razorpay_plan_id = COALESCE(:pid, razorpay_plan_id),
                    last_event_at = COALESCE(:eat, last_event_at), updated_at = :now
                WHERE id = :id"""),
        {
            "status": rz_status, "plan": plan, "currency": currency, "interval": interval,
            "cid": entity.get("customer_id"), "pid": entity.get("plan_id"),
            "eat": event_at, "now": now, "id": rz["id"],
        },
    )

    if local_status is None:
        return True

    monthly = get_regional_price(plan, currency, "monthly")
    # subscriptions.monthly_price is USD. Only USD subscriptions get a price
    # here; INR/AED amounts live in razorpay_subscriptions (amount + currency).
    # Admin MRR (server/core/admin_mrr.py) counts every active Razorpay
    # subscription from razorpay_subscriptions, FX-converted, and skips this
    # row, so nothing is counted twice.
    monthly_price = float(monthly["amount"]) if (monthly and currency == "USD") else 0.0

    params = {
        "uid": rz["user_id"],
        "plan": plan,
        "status": local_status,
        "pstart": _ts(entity.get("current_start")),
        "pend": _ts(entity.get("current_end")),
        "price": monthly_price,
        "now": now,
    }
    existing = db.execute(
        text("SELECT id FROM subscriptions WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1"),
        {"uid": rz["user_id"]},
    ).fetchone()
    if existing:
        db.execute(
            text("""UPDATE subscriptions
                    SET plan = :plan, status = :status,
                        current_period_start = COALESCE(:pstart, current_period_start),
                        current_period_end = COALESCE(:pend, current_period_end),
                        monthly_price = :price, updated_at = :now
                    WHERE id = :sid"""),
            {**params, "sid": existing[0]},
        )
    else:
        db.execute(
            text("""INSERT INTO subscriptions
                        (user_id, plan, status, current_period_start, current_period_end,
                         monthly_price, created_at, updated_at)
                    VALUES (:uid, :plan, :status, :pstart, :pend, :price, :now, :now)"""),
            params,
        )
    logger.info(f"Billing (razorpay): user {rz['user_id']} -> plan={plan} status={local_status}")
    return True


def _razorpay_subscribe(plan_id: str, body: Optional[SubscribeBody], current_user, db: Session):
    interval = body.interval if body else "monthly"
    if interval not in ("monthly", "annual"):
        raise HTTPException(status_code=400, detail="interval must be 'monthly' or 'annual'")
    # Server-decided from the company currency setting; never from the client.
    currency, _source = resolve_currency(db, current_user.id)
    price = get_regional_price(plan_id, currency, interval)
    if not price:
        raise HTTPException(status_code=404, detail="This plan is not available in your region yet.")
    rz_plan_id = razorpay_billing.plan_id_for(plan_id, currency, interval)
    if not rz_plan_id:
        logger.error(f"Razorpay: {price['plan_env']} is not set")
        raise HTTPException(status_code=503, detail="Payments are not configured yet. Please try again later.")

    if _active_razorpay_subscription(db, current_user.id):
        raise HTTPException(status_code=400, detail="You already have an active subscription.")

    email = getattr(current_user, "email", None)
    name = getattr(current_user, "display_name", None)
    try:
        customer_id = razorpay_billing.get_or_create_customer(
            email, name, current_user.id, _latest_razorpay_customer_id(db, current_user.id)
        )
        sub = razorpay_billing.create_subscription(
            rz_plan_id, interval, current_user.id, plan_id, currency, customer_id
        )
    except razorpay_billing.RazorpayError as e:
        logger.error(f"Razorpay checkout creation failed for user {current_user.id}: {e}")
        raise HTTPException(status_code=502, detail="Could not start checkout. Please try again.")

    now = datetime.utcnow()
    db.execute(
        text("""INSERT INTO razorpay_subscriptions
                    (user_id, razorpay_subscription_id, razorpay_customer_id, razorpay_plan_id,
                     plan, interval, currency, amount, status, created_at, updated_at)
                VALUES (:uid, :sid, :cid, :pid, :plan, :interval, :currency, :amount,
                        :status, :now, :now)"""),
        {
            "uid": current_user.id, "sid": sub["id"], "cid": customer_id, "pid": rz_plan_id,
            "plan": plan_id, "interval": interval, "currency": currency,
            "amount": price["amount"], "status": sub.get("status") or "created", "now": now,
        },
    )
    db.commit()

    return {
        "provider": "razorpay",
        "subscription_id": sub["id"],
        "key_id": razorpay_billing.key_id(),
        "plan": plan_id,
        "plan_name": PLAN_DETAILS[plan_id]["name"],
        "interval": interval,
        "currency": currency,
        "amount": price["amount"],
        "prefill": {"email": email or "", "name": name or ""},
    }


@router.post("/razorpay/verify")
def razorpay_verify(
    body: RazorpayVerifyBody,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify the Checkout handler signature, then re-fetch the subscription.

    The signature proves the payment belongs to this subscription. Access is
    granted from the subscription state Razorpay returns, not from the client.
    """
    if billing_provider() != "razorpay":
        raise HTTPException(status_code=503, detail="Payments are not configured yet.")

    rz = _rz_by_subscription_id(db, body.razorpay_subscription_id)
    if not rz or rz["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not razorpay_billing.verify_payment_signature(
        body.razorpay_payment_id, rz["razorpay_subscription_id"], body.razorpay_signature
    ):
        logger.warning(f"Razorpay: bad payment signature for user {current_user.id}")
        raise HTTPException(status_code=400, detail="Payment verification failed")

    try:
        entity = razorpay_billing.fetch_subscription(rz["razorpay_subscription_id"])
    except razorpay_billing.RazorpayError as e:
        logger.warning(f"Razorpay: fetch after verify failed, waiting for webhook: {e}")
        return {"verified": True, "status": "pending"}

    local_status = RAZORPAY_STATUS_MAP.get(entity.get("status"))
    _apply_razorpay_state(db, rz, local_status, entity)
    db.commit()
    return {"verified": True, "status": local_status or "pending"}


def _razorpay_cancel(current_user, db: Session):
    rz = _active_razorpay_subscription(db, current_user.id)
    if not rz:
        raise HTTPException(status_code=400, detail="No active subscription to cancel.")
    try:
        entity = razorpay_billing.cancel_subscription(rz["razorpay_subscription_id"], at_cycle_end=True)
    except razorpay_billing.RazorpayError as e:
        logger.error(f"Razorpay cancel failed for user {current_user.id}: {e}")
        raise HTTPException(status_code=502, detail="Could not cancel. Please try again.")
    # Access continues until the cycle ends; the subscription.cancelled
    # webhook downgrades the row then.
    end = _ts((entity or {}).get("current_end"))
    return {
        "cancelled_at_cycle_end": True,
        "current_period_end": end.isoformat() if end else None,
        "message": "Your subscription will end at the close of the current billing period.",
    }


def _webhook_event_id(request: Request, raw: bytes) -> str:
    header_id = (request.headers.get("x-razorpay-event-id") or "").strip()
    return header_id or ("sha256:" + hashlib.sha256(raw).hexdigest())


def _process_razorpay_event(db: Session, etype: str, event: dict) -> Optional[str]:
    """Apply one verified event. Returns the subscription id it touched, if any."""
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    sub_entity = ((payload.get("subscription") or {}).get("entity")) or {}
    pay_entity = ((payload.get("payment") or {}).get("entity")) or {}
    event_at = event.get("created_at")
    try:
        event_at = int(event_at) if event_at is not None else None
    except (TypeError, ValueError):
        event_at = None

    if etype.startswith("subscription."):
        sub_id = sub_entity.get("id")
        rz = _rz_by_subscription_id(db, sub_id)
        if not rz:
            rz = _adopt_unknown_subscription(db, sub_entity)
        if not rz:
            # Expected on a shared Razorpay account: events for other products' plans.
            logger.info(f"Razorpay webhook {etype}: ignoring subscription {sub_id} (not ours)")
            return sub_id
        if sub_entity.get("status"):
            local_status = RAZORPAY_STATUS_MAP.get(sub_entity["status"])
        else:
            local_status = RAZORPAY_EVENT_STATUS.get(etype)
        _apply_razorpay_state(db, rz, local_status, sub_entity, event_at)
        return sub_id

    if etype == "payment.failed":
        sub_id = pay_entity.get("subscription_id") or sub_entity.get("id")
        # Match on the subscription id only. The Razorpay account is shared with
        # other products, so a customer id can belong to someone's payment for a
        # different product; renewal failures also arrive as subscription.halted.
        rz = _rz_by_subscription_id(db, sub_id) if sub_id else None
        # Only a failed renewal of a live subscription downgrades. A declined
        # first attempt in Checkout must not end an in-app trial.
        if rz and rz["status"] == "active":
            _apply_razorpay_state(db, rz, "past_due", {"status": "pending"}, event_at)
        return rz["razorpay_subscription_id"] if rz else sub_id

    return sub_entity.get("id")


def _adopt_unknown_subscription(db: Session, sub_entity: dict) -> Optional[dict]:
    """A signed event for a subscription with no local row (e.g. the insert at
    checkout failed). Adopt it only if the server-set notes name a real user
    and the plan id is one of ours."""
    notes = sub_entity.get("notes") if isinstance(sub_entity.get("notes"), dict) else {}
    user_id = _accept_user_id(db, _parse_user_id(notes.get("fc_user_id")))
    mapped = razorpay_billing.tier_for_plan_id(sub_entity.get("plan_id"))
    if not user_id or not mapped or not sub_entity.get("id"):
        return None
    now = datetime.utcnow()
    db.execute(
        text("""INSERT INTO razorpay_subscriptions
                    (user_id, razorpay_subscription_id, razorpay_customer_id, razorpay_plan_id,
                     plan, interval, currency, amount, status, created_at, updated_at)
                VALUES (:uid, :sid, :cid, :pid, :plan, :interval, :currency, :amount,
                        'created', :now, :now)"""),
        {
            "uid": user_id, "sid": sub_entity["id"], "cid": sub_entity.get("customer_id"),
            "pid": sub_entity.get("plan_id"), "plan": mapped["tier"], "interval": mapped["interval"],
            "currency": mapped["currency"], "amount": mapped["amount"], "now": now,
        },
    )
    return _rz_by_subscription_id(db, sub_entity["id"])


@router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):
    """Razorpay webhook. CSRF-exempt; authenticated by X-Razorpay-Signature.

    Fails closed: with RAZORPAY_WEBHOOK_SECRET unset every delivery is refused.
    Idempotent on X-Razorpay-Event-Id (falls back to a hash of the raw body).
    Any processing error returns 500 so Razorpay redelivers.
    """
    raw = await request.body()
    if not razorpay_billing._webhook_secret():
        raise HTTPException(status_code=503, detail="Payments not configured")
    if not razorpay_billing.verify_webhook_signature(raw, request.headers.get("x-razorpay-signature")):
        logger.warning("Razorpay webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        event = json.loads(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")

    etype = str(event.get("event") or "")
    event_id = _webhook_event_id(request, raw)

    db = SessionLocal()
    try:
        seen = db.execute(
            text("SELECT 1 FROM razorpay_webhook_events WHERE event_id = :eid"),
            {"eid": event_id},
        ).fetchone()
        if seen:
            return {"received": True, "duplicate": True}

        sub_id = _process_razorpay_event(db, etype, event)
        db.execute(
            text("""INSERT INTO razorpay_webhook_events
                        (event_id, event_type, razorpay_subscription_id, processed_at)
                    VALUES (:eid, :etype, :sid, :now)"""),
            {"eid": event_id, "etype": etype or "unknown", "sid": sub_id, "now": datetime.utcnow()},
        )
        db.commit()
    except IntegrityError:
        # A concurrent delivery of the same event committed first.
        db.rollback()
        return {"received": True, "duplicate": True}
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(f"Razorpay webhook {etype} ({event_id}) failed; returning 500 for redelivery")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
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
