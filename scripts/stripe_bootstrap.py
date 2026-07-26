"""One-time Stripe bootstrap for FounderConsole.

Creates (idempotently):
  1. Products + prices for Starter/Growth/Scale, monthly + annual,
     with stable lookup keys (fc_<plan>_<interval>).
  2. The webhook endpoint pointing at APP_BASE_URL/api/billing/webhook,
     printing its signing secret (set this as STRIPE_WEBHOOK_SECRET).

Usage:
    STRIPE_SECRET_KEY=sk_... APP_BASE_URL=https://founderconsole.ai \
        python scripts/stripe_bootstrap.py
or on Railway (pulls env vars from the linked service):
    railway run python scripts/stripe_bootstrap.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stripe

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://founderconsole.ai").rstrip("/")

WEBHOOK_EVENTS = [
    "checkout.session.completed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_failed",
]


def main():
    if not STRIPE_SECRET_KEY:
        print("ERROR: STRIPE_SECRET_KEY is not set", file=sys.stderr)
        sys.exit(1)
    stripe.api_key = STRIPE_SECRET_KEY

    mode = "LIVE" if STRIPE_SECRET_KEY.startswith("sk_live") else "TEST"
    print(f"Stripe mode: {mode}")

    # --- Products & prices ---------------------------------------------------
    from server.core.plans import PLAN_DETAILS, PlanTier

    for plan in [PlanTier.STARTER, PlanTier.GROWTH, PlanTier.SCALE]:
        info = PLAN_DETAILS[plan]
        for interval, stripe_interval, amount in [
            ("monthly", "month", info["price_monthly"]),
            ("annual", "year", info["price_annual"]),
        ]:
            key = f"fc_{plan.value}_{interval}"
            existing = stripe.Price.list(lookup_keys=[key], active=True, limit=1)
            if existing.data:
                print(f"  price {key}: exists ({existing.data[0].id})")
                continue

            # find or create product
            product_id = None
            try:
                found = stripe.Product.search(query=f"metadata['fc_plan']:'{plan.value}'", limit=1)
                if found.data:
                    product_id = found.data[0].id
            except Exception:
                pass
            if not product_id:
                for p in stripe.Product.list(active=True, limit=100).auto_paging_iter():
                    if p.get("metadata", {}).get("fc_plan") == plan.value:
                        product_id = p.id
                        break
            if not product_id:
                product = stripe.Product.create(
                    name=f"FounderConsole {info['name']}",
                    description=info["tagline"],
                    metadata={"fc_plan": plan.value},
                )
                product_id = product.id
                print(f"  product created: {product_id} ({info['name']})")

            price = stripe.Price.create(
                product=product_id,
                unit_amount=int(amount * 100),
                currency="usd",
                recurring={"interval": stripe_interval},
                lookup_key=key,
                transfer_lookup_key=True,
                metadata={"fc_plan": plan.value, "fc_interval": interval},
            )
            print(f"  price {key}: created ({price.id}, ${amount}/{stripe_interval})")

    # --- Webhook endpoint ----------------------------------------------------
    url = f"{APP_BASE_URL}/api/billing/webhook"
    endpoints = stripe.WebhookEndpoint.list(limit=100)
    existing_ep = next((e for e in endpoints.data if e.url == url), None)
    if existing_ep:
        print(f"\nWebhook endpoint already exists: {existing_ep.id} → {url}")
        print("NOTE: its signing secret is only shown at creation time.")
        print("If STRIPE_WEBHOOK_SECRET is lost, delete the endpoint in the Stripe")
        print("dashboard and re-run this script to get a fresh secret.")
    else:
        ep = stripe.WebhookEndpoint.create(
            url=url,
            enabled_events=WEBHOOK_EVENTS,
            description="FounderConsole billing webhook",
        )
        print(f"\nWebhook endpoint created: {ep.id} → {url}")
        print(f"\n  STRIPE_WEBHOOK_SECRET={ep.secret}\n")
        print("Set this as the STRIPE_WEBHOOK_SECRET environment variable now —")
        print("it cannot be retrieved again later.")

    print("\nBootstrap complete.")
    print("Reminder: enable PayPal / Apple Pay / Google Pay under")
    print("Stripe Dashboard → Settings → Payments → Payment methods.")


if __name__ == "__main__":
    main()
