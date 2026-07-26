"""Stripe billing integration: checkout, customer portal, price management.

Prices are self-bootstrapping: each plan/interval gets a Stripe Price with a
stable lookup_key (fc_<plan>_<interval>). If the price doesn't exist in the
connected Stripe account it is created on first use from PLAN_DETAILS, so no
manual dashboard setup is required beyond enabling payment methods (card,
PayPal, Apple/Google Pay) in Stripe settings.
"""
import json
import logging
from typing import Optional

import stripe

from server.core.config import settings
from server.core.plans import PlanTier, PLAN_DETAILS

logger = logging.getLogger(__name__)

CURRENCY = "usd"
PAID_PLANS = [PlanTier.STARTER, PlanTier.GROWTH, PlanTier.SCALE]
INTERVALS = {"monthly": "month", "annual": "year"}

_price_cache: dict = {}


def stripe_enabled() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


def to_plain(obj):
    """Convert a StripeObject (not a dict subclass in SDK v15+) to plain dicts."""
    if isinstance(obj, (dict, list)) or obj is None:
        return obj
    try:
        return json.loads(str(obj))
    except Exception:
        return obj


def _init():
    stripe.api_key = settings.STRIPE_SECRET_KEY


def _lookup_key(plan: str, interval: str) -> str:
    return f"fc_{plan}_{interval}"


def _ensure_product(plan: str) -> str:
    """Find or create the Stripe Product for a plan. Returns product id."""
    info = PLAN_DETAILS[plan]
    try:
        found = stripe.Product.search(query=f"metadata['fc_plan']:'{plan}'", limit=1)
        if found.data:
            return found.data[0].id
    except Exception as e:  # Product.search unavailable on some accounts
        logger.warning(f"Stripe product search failed, falling back to list: {e}")

    # Search results can lag behind newly-created objects, so always
    # double-check the full list before creating a duplicate product.
    for p in stripe.Product.list(active=True, limit=100).auto_paging_iter():
        if (to_plain(p).get("metadata") or {}).get("fc_plan") == plan:
            return p.id

    product = stripe.Product.create(
        name=f"FounderConsole {info['name']}",
        description=info["tagline"],
        metadata={"fc_plan": plan},
    )
    logger.info(f"Created Stripe product {product.id} for plan {plan}")
    return product.id


def ensure_price(plan: str, interval: str = "monthly") -> str:
    """Return the Stripe Price id for plan+interval, creating it if needed."""
    _init()
    key = _lookup_key(plan, interval)
    if key in _price_cache:
        return _price_cache[key]

    existing = stripe.Price.list(lookup_keys=[key], active=True, limit=1)
    if existing.data:
        _price_cache[key] = existing.data[0].id
        return existing.data[0].id

    info = PLAN_DETAILS[plan]
    amount = info["price_monthly"] if interval == "monthly" else info["price_annual"]
    product_id = _ensure_product(plan)
    price = stripe.Price.create(
        product=product_id,
        unit_amount=int(amount * 100),
        currency=CURRENCY,
        recurring={"interval": INTERVALS[interval]},
        lookup_key=key,
        transfer_lookup_key=True,
        metadata={"fc_plan": plan, "fc_interval": interval},
    )
    logger.info(f"Created Stripe price {price.id} ({key}: ${amount}/{INTERVALS[interval]})")
    _price_cache[key] = price.id
    return price.id


def plan_from_price(price) -> Optional[str]:
    """Map a Stripe Price object (or id) back to a plan tier."""
    _init()
    if isinstance(price, str):
        price = stripe.Price.retrieve(price)
    price = to_plain(price) or {}
    plan = (price.get("metadata") or {}).get("fc_plan")
    if plan:
        return plan
    lk = price.get("lookup_key") or ""
    if lk.startswith("fc_"):
        parts = lk.split("_")
        if len(parts) >= 3:
            return parts[1]
    return None


def get_or_create_customer(db, user) -> str:
    """Return the Stripe customer id for a user, creating one if needed."""
    from sqlalchemy import text

    _init()
    row = db.execute(
        text("SELECT stripe_customer_id FROM subscriptions WHERE user_id = :uid AND stripe_customer_id IS NOT NULL ORDER BY created_at DESC LIMIT 1"),
        {"uid": user.id},
    ).fetchone()
    if row and row[0]:
        return row[0]

    customer = stripe.Customer.create(
        email=getattr(user, "email", None),
        name=getattr(user, "full_name", None) or getattr(user, "name", None),
        metadata={"fc_user_id": str(user.id)},
    )
    return customer.id


def create_checkout_session(db, user, plan: str, interval: str = "monthly") -> str:
    """Create a Stripe Checkout session for a subscription. Returns the URL."""
    _init()
    price_id = ensure_price(plan, interval)
    customer_id = get_or_create_customer(db, user)
    base = settings.APP_BASE_URL.rstrip("/")

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        client_reference_id=str(user.id),
        allow_promotion_codes=True,
        billing_address_collection="auto",
        subscription_data={"metadata": {"fc_user_id": str(user.id), "fc_plan": plan}},
        success_url=f"{base}/billing?checkout=success",
        cancel_url=f"{base}/billing?checkout=cancelled",
    )
    return session.url


def create_portal_session(customer_id: str) -> str:
    """Create a Stripe customer portal session. Returns the URL."""
    _init()
    base = settings.APP_BASE_URL.rstrip("/")
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{base}/billing",
    )
    return session.url


def verify_webhook(payload: bytes, sig_header: str):
    """Verify webhook signature and return the event. Raises on failure."""
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
