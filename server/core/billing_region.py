"""Resolve which billing currency a user is quoted in (Razorpay path only).

Order:
  1. an explicit currency the client asked for, if it is in SUPPORTED_CURRENCIES
  2. the user's company currency setting, if it is INR / USD / AED
  3. the user's chosen country (company metadata_json "country" / "hq_country")
  4. an IP-country header, if a proxy set one (cf-ipcountry). founderconsole.ai
     is DNS-only on Cloudflare, so this is usually absent; nothing depends on it
  5. DEFAULT_CURRENCY (INR: the primary market is Indian D2C brands)

Countries map to currencies with plans.currency_for_country: IN -> INR,
US -> USD, AE -> AED, any other country -> USD.

This only picks a currency. The amount and the Razorpay plan id always come
from plans.PRICE_TABLE on the server.
"""
from __future__ import annotations

import json
import logging
from typing import Optional, Tuple

from sqlalchemy import text

from server.core.plans import DEFAULT_CURRENCY, currency_for_country, normalize_currency

logger = logging.getLogger(__name__)

COUNTRY_KEYS = ("country", "hq_country", "country_code")
IP_COUNTRY_HEADERS = ("cf-ipcountry",)


def _company_row(db, user_id: int):
    try:
        return db.execute(
            text("SELECT currency, metadata_json FROM companies WHERE user_id = :uid ORDER BY id DESC LIMIT 1"),
            {"uid": user_id},
        ).fetchone()
    except Exception as e:  # no companies table / bad row: just fall through
        logger.debug(f"billing_region: company lookup failed for user {user_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return None


def _meta_country(meta) -> Optional[str]:
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except ValueError:
            return None
    if not isinstance(meta, dict):
        return None
    for key in COUNTRY_KEYS:
        cur = currency_for_country(meta.get(key))
        if cur:
            return cur
    return None


def resolve_currency(db, user_id: int, headers=None, requested: Optional[str] = None) -> Tuple[str, str]:
    """Return (currency, source)."""
    cur = normalize_currency(requested)
    if cur:
        return cur, "requested"

    row = _company_row(db, user_id)
    if row is not None:
        cur = normalize_currency(row[0])
        if cur:
            return cur, "company_currency"
        cur = _meta_country(row[1])
        if cur:
            return cur, "company_country"

    if headers is not None:
        for h in IP_COUNTRY_HEADERS:
            cur = currency_for_country(headers.get(h))
            if cur:
                return cur, "ip_country"

    return DEFAULT_CURRENCY, "default"
