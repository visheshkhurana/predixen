"""Resolve which billing currency a user is charged in (Razorpay path only).

The charge currency comes from ONE place: the user's latest company currency
setting. INR -> INR, AED -> AED, anything else (including USD, the column
default, and no company at all) -> USD.

Nothing the client sends, and no request header, can change it. A client
currency or a geo header (cf-ipcountry is spoofable while founderconsole.ai
is DNS-only on Cloudflare) would let a buyer pick the cheaper currency.

This only picks a currency. The amount and the Razorpay plan id always come
from plans.PRICE_TABLE on the server.
"""
from __future__ import annotations

import logging
from typing import Tuple

from sqlalchemy import text

logger = logging.getLogger(__name__)

COMPANY_CURRENCY_MAP = {"INR": "INR", "AED": "AED"}
FALLBACK_CURRENCY = "USD"


def _company_currency(db, user_id: int):
    try:
        row = db.execute(
            text("SELECT currency FROM companies WHERE user_id = :uid ORDER BY id DESC LIMIT 1"),
            {"uid": user_id},
        ).fetchone()
    except Exception as e:  # no companies table / bad row: fall back to USD
        logger.debug(f"billing_region: company lookup failed for user {user_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return None
    return row[0] if row else None


def resolve_currency(db, user_id: int) -> Tuple[str, str]:
    """Return (currency, source) for a user's charge."""
    raw = _company_currency(db, user_id)
    if isinstance(raw, str) and raw.strip().upper() in COMPANY_CURRENCY_MAP:
        return COMPANY_CURRENCY_MAP[raw.strip().upper()], "company_currency"
    if raw is None:
        return FALLBACK_CURRENCY, "no_company"
    return FALLBACK_CURRENCY, "company_currency_other"
