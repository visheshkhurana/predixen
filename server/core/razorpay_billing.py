"""Razorpay subscription billing.

Off by default. Razorpay is the active provider only when ALL of these are set:

    BILLING_PROVIDER=razorpay
    RAZORPAY_KEY_ID
    RAZORPAY_KEY_SECRET
    RAZORPAY_WEBHOOK_SECRET

With any of them missing, billing_provider() returns "stripe" and the existing
Stripe path (itself off unless STRIPE_SECRET_KEY is set) is used unchanged.

Talks to the Razorpay REST API over plain HTTPS with httpx (already a
dependency), using HTTP basic auth (key_id:key_secret). No SDK.

Prices and plan ids come from server.core.plans.PRICE_TABLE: the server picks
the plan id for (tier, currency, interval); the client never sends an amount.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Optional

import httpx

from server.core.plans import get_regional_price

logger = logging.getLogger(__name__)

API_BASE = "https://api.razorpay.com/v1"
CHECKOUT_JS_URL = "https://checkout.razorpay.com/v1/checkout.js"
HTTP_TIMEOUT = 20.0
# Razorpay requires total_count for subscriptions. 10 years of cycles; the
# customer can cancel at any time.
TOTAL_COUNT = {"monthly": 120, "annual": 10}


class RazorpayError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def key_id() -> str:
    return _env("RAZORPAY_KEY_ID")


def _key_secret() -> str:
    return _env("RAZORPAY_KEY_SECRET")


def _webhook_secret() -> str:
    return _env("RAZORPAY_WEBHOOK_SECRET")


def razorpay_enabled() -> bool:
    """True only with an explicit BILLING_PROVIDER=razorpay and all three secrets."""
    return (
        _env("BILLING_PROVIDER").lower() == "razorpay"
        and bool(key_id())
        and bool(_key_secret())
        and bool(_webhook_secret())
    )


def plan_id_for(tier: str, currency: str, interval: str) -> Optional[str]:
    """Razorpay plan id for (tier, currency, interval), from its env var."""
    price = get_regional_price(tier, currency, interval)
    if not price:
        return None
    return _env(price["plan_env"]) or None


def tier_for_plan_id(plan_id: Optional[str]) -> Optional[dict]:
    """Reverse lookup: which (tier, currency, interval) a Razorpay plan id is.

    This is how webhook state is mapped to a tier: from the plan Razorpay
    actually charges, never from anything the client sent.
    """
    if not plan_id:
        return None
    from server.core.plans import PRICE_TABLE

    for (tier, currency, interval), entry in PRICE_TABLE.items():
        if _env(entry["plan_env"]) == plan_id:
            return {
                "tier": tier,
                "currency": currency,
                "interval": interval,
                "amount": entry["amount"],
            }
    return None


# ---------------------------------------------------------------------------
# Signatures
# ---------------------------------------------------------------------------

def _hmac_hex(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_payment_signature(payment_id: str, subscription_id: str, signature: str) -> bool:
    """Checkout handler signature for subscriptions.

    razorpay_signature == HMAC_SHA256(razorpay_payment_id + "|" + subscription_id, key_secret)
    """
    secret = _key_secret()
    if not secret or not payment_id or not subscription_id or not signature:
        return False
    expected = _hmac_hex(secret, f"{payment_id}|{subscription_id}".encode("utf-8"))
    return hmac.compare_digest(expected, str(signature).strip())


def verify_webhook_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    """X-Razorpay-Signature == HMAC_SHA256(raw request body, webhook secret).

    Fails closed: an unset secret or missing header is never valid.
    """
    secret = _webhook_secret()
    if not secret or not signature or raw_body is None:
        return False
    expected = _hmac_hex(secret, raw_body)
    return hmac.compare_digest(expected, str(signature).strip())


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

def _request(method: str, path: str, json: Optional[dict] = None) -> dict:
    if not key_id() or not _key_secret():
        raise RazorpayError("Razorpay keys are not configured")
    try:
        resp = httpx.request(
            method,
            f"{API_BASE}{path}",
            json=json,
            auth=(key_id(), _key_secret()),
            timeout=HTTP_TIMEOUT,
        )
    except httpx.HTTPError as e:
        raise RazorpayError(f"Razorpay request failed: {e}") from e
    if resp.status_code >= 400:
        # Razorpay error bodies carry a description but no secrets.
        try:
            desc = (resp.json().get("error") or {}).get("description")
        except Exception:
            desc = None
        raise RazorpayError(f"Razorpay {method} {path} -> {resp.status_code}: {desc or 'error'}")
    try:
        return resp.json()
    except ValueError as e:
        raise RazorpayError("Razorpay returned a non-JSON response") from e


def create_customer(email: Optional[str], name: Optional[str], user_id: int) -> dict:
    """Create a customer, or return the existing one for this email.

    fail_existing=0 makes Razorpay return the existing customer instead of
    erroring when the email/contact is already on the account.
    """
    body = {
        "fail_existing": "0",
        "notes": {"fc_user_id": str(user_id)},
    }
    if email:
        body["email"] = email
    if name:
        body["name"] = name[:50]
    return _request("POST", "/customers", json=body)


def fetch_customer(customer_id: str) -> dict:
    return _request("GET", f"/customers/{customer_id}")


def get_or_create_customer(email: Optional[str], name: Optional[str], user_id: int,
                           existing_customer_id: Optional[str] = None) -> str:
    """Look up a stored customer id, falling back to create (idempotent by email)."""
    if existing_customer_id:
        try:
            return fetch_customer(existing_customer_id)["id"]
        except RazorpayError as e:
            logger.warning(f"Razorpay customer {existing_customer_id} lookup failed, recreating: {e}")
    return create_customer(email, name, user_id)["id"]


def create_subscription(plan_id: str, interval: str, user_id: int, tier: str,
                        currency: str, customer_id: Optional[str] = None) -> dict:
    body = {
        "plan_id": plan_id,
        "total_count": TOTAL_COUNT.get(interval, 120),
        "quantity": 1,
        "customer_notify": 1,
        "notes": {
            "fc_user_id": str(user_id),
            "fc_plan": tier,
            "fc_interval": interval,
            "fc_currency": currency,
        },
    }
    if customer_id:
        body["customer_id"] = customer_id
    return _request("POST", "/subscriptions", json=body)


def fetch_subscription(subscription_id: str) -> dict:
    return _request("GET", f"/subscriptions/{subscription_id}")


def cancel_subscription(subscription_id: str, at_cycle_end: bool = True) -> dict:
    """Cancel. By default at the end of the current billing cycle."""
    return _request(
        "POST",
        f"/subscriptions/{subscription_id}/cancel",
        json={"cancel_at_cycle_end": 1 if at_cycle_end else 0},
    )
