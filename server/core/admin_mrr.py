"""Platform MRR for the admin dashboard, across Stripe and Razorpay.

Two sources:

- subscriptions.monthly_price: USD, written by the Stripe webhook (annual
  already divided by 12) and by manual/admin grants.
- razorpay_subscriptions: amount (major units, per interval) + currency +
  interval. The Razorpay sync also writes a row in `subscriptions`, but only
  USD subscriptions get a non-zero monthly_price there, and it is the monthly
  list price even on an annual plan.

So, to count each paying subscription exactly once:

- every ACTIVE razorpay_subscriptions row is counted from that table
  (annual = amount / 12), converted to USD with the approximate rates in
  server.core.config.usd_per_currency();
- `subscriptions` rows owned by a Razorpay subscription (no Stripe id, and the
  user has an active Razorpay subscription) are left out of the USD sum.

Only active subscriptions count. A currency with no FX rate is reported in the
breakdown but left out of the USD total, rather than guessed.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from server.core.config import usd_per_currency

logger = logging.getLogger(__name__)

_ACTIVE_RZ_USERS = "SELECT user_id FROM razorpay_subscriptions WHERE status = 'active'"


def _razorpay_rows(db: Session) -> list:
    # Checked up front rather than try/rollback, so a missing table (Razorpay
    # never booted on this database) cannot roll back the caller's session.
    if not inspect(db.connection()).has_table("razorpay_subscriptions"):
        return []
    return db.execute(
        text("""SELECT currency, interval, amount FROM razorpay_subscriptions
                WHERE status = 'active'""")
    ).fetchall()


def _subscriptions_usd(db: Session, exclude_razorpay: bool) -> float:
    sql = "SELECT COALESCE(SUM(monthly_price), 0) FROM subscriptions WHERE status = 'active'"
    if exclude_razorpay:
        sql += (
            " AND NOT (stripe_subscription_id IS NULL AND user_id IS NOT NULL"
            f" AND user_id IN ({_ACTIVE_RZ_USERS}))"
        )
    return float(db.execute(text(sql)).scalar() or 0.0)


def compute_platform_mrr(db: Session) -> Dict[str, Any]:
    """Returns {"mrr_usd", "breakdown"}; see the module docstring for the rules."""
    rates = usd_per_currency()
    rz_rows = _razorpay_rows(db)
    stripe_usd = _subscriptions_usd(db, exclude_razorpay=bool(rz_rows))

    by_currency: Dict[str, Dict[str, Any]] = {}

    def bucket(code: str) -> Dict[str, Any]:
        return by_currency.setdefault(code, {"native": 0.0, "usd": 0.0, "razorpay_subscriptions": 0})

    if stripe_usd:
        bucket("USD")["native"] += stripe_usd
        bucket("USD")["usd"] += stripe_usd

    razorpay_usd = 0.0
    unconverted = []
    for currency, interval, amount in rz_rows:
        code = (currency or "").upper()
        monthly = float(amount or 0) / 12.0 if interval == "annual" else float(amount or 0)
        b = bucket(code)
        b["native"] += monthly
        b["razorpay_subscriptions"] += 1
        rate = rates.get(code)
        if rate is None:
            b["usd"] = None
            if code not in unconverted:
                unconverted.append(code)
            continue
        usd = monthly * rate
        razorpay_usd += usd
        if b["usd"] is not None:
            b["usd"] += usd

    for b in by_currency.values():
        b["native"] = round(b["native"], 2)
        if b["usd"] is not None:
            b["usd"] = round(b["usd"], 2)

    if unconverted:
        logger.warning(f"admin MRR: no FX rate for {unconverted}; left out of the USD total")

    total = round(stripe_usd + razorpay_usd, 2)
    return {
        "mrr_usd": total,
        "breakdown": {
            "by_currency": by_currency,
            "sources_usd": {
                "subscriptions": round(stripe_usd, 2),
                "razorpay": round(razorpay_usd, 2),
            },
            "fx_usd_per_unit": {k: v for k, v in rates.items() if k != "USD"},
            "fx_approximate": True,
            "fx_note": "Static approximate rates for reporting; override with USD_PER_<CODE> env vars.",
            "unconverted_currencies": unconverted,
        },
    }
