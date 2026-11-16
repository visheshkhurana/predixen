"""
Razorpay connector - payment gateway fees for Indian D2C brands.

Shopify knows the order value; the payment gateway knows what it kept. This
connector reads the brand's own Razorpay payments for the last complete month
and works out the gateway fee as a share of captured prepaid value, which is
the `payment_gateway_pct` input of the D2C contribution margin.

Not to be confused with RazorpayX (razorpayx.py), which is the banking product.

API: https://razorpay.com/docs/api/payments/ (GET /v1/payments). Auth is HTTP
Basic with the account's key id and key secret.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx

from .base import AuthType, BaseConnector, ConnectorConfig, ProviderCategory, SyncResult
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.razorpay.com/v1"
PER_PAGE = 100  # Razorpay's maximum
MAX_PAGES = 500  # 50k payments; a truncated month is reported, never hidden
IST = timezone(timedelta(hours=5, minutes=30))


def last_complete_month(today: date) -> Tuple[date, date]:
    last_prev = today.replace(day=1) - timedelta(days=1)
    return last_prev.replace(day=1), last_prev


def month_window_unix(start: date, end: date) -> Tuple[int, int]:
    """The month in India time, as Razorpay's from/to unix seconds (inclusive)."""
    start_dt = datetime(start.year, start.month, start.day, tzinfo=IST)
    end_dt = datetime(end.year, end.month, end.day, tzinfo=IST) + timedelta(days=1)
    return int(start_dt.timestamp()), int(end_dt.timestamp()) - 1


def _paise(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def summarize_payments(payments: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Fees, refunds and method mix for one month of payments.

    Only captured INR payments count. A refunded payment was captured first,
    and Razorpay keeps its fee on refunds, so it stays in. Razorpay's `fee`
    includes GST on the fee (`tax`); the ex-GST fee is used for the margin,
    matching the ex-GST sales Shopify reports, because a GST-registered brand
    claims that GST back as input credit.
    """
    captured_paise = fee_paise = tax_paise = refunded_paise = 0
    captured_count = failed = 0
    non_inr = 0
    methods: Counter = Counter()

    for p in payments:
        if p.get("status") == "failed":
            failed += 1
            continue
        if not p.get("captured"):
            continue
        if str(p.get("currency") or "INR").upper() != "INR":
            non_inr += 1
            continue
        captured_count += 1
        amount = _paise(p.get("amount"))
        captured_paise += amount
        fee_paise += _paise(p.get("fee"))
        tax_paise += _paise(p.get("tax"))
        refunded_paise += _paise(p.get("amount_refunded"))
        methods[str(p.get("method") or "other")] += amount

    fee_ex_gst = fee_paise - tax_paise
    return {
        "captured_payments": captured_count,
        "failed_payments": failed,
        "non_inr_payments_skipped": non_inr,
        "captured_value": round(captured_paise / 100, 2),
        "refunded_value": round(refunded_paise / 100, 2),
        "fees_incl_gst": round(fee_paise / 100, 2),
        "gst_on_fees": round(tax_paise / 100, 2),
        "fees_ex_gst": round(fee_ex_gst / 100, 2),
        # None, not 0, with no captured value: the engine then asks for the
        # gateway rate instead of assuming payments are free.
        "payment_gateway_pct": round(fee_ex_gst / captured_paise, 5) if captured_paise > 0 and fee_ex_gst >= 0 else None,
        "method_share": (
            {m: round(v / captured_paise, 4) for m, v in methods.most_common()} if captured_paise else {}
        ),
    }


def month_values(summary: Dict[str, Any]) -> Dict[str, Any]:
    """The fields of a d2c_months row this connector owns."""
    return {"payment_gateway_pct": summary["payment_gateway_pct"]}


@ConnectorRegistry.register
class RazorpayConnector(BaseConnector):
    PROVIDER_ID = "razorpay"
    PROVIDER_NAME = "Razorpay"
    PROVIDER_DESCRIPTION = "Payment gateway for Indian D2C. Imports captured payments, refunds and gateway fees."
    PROVIDER_CATEGORY = ProviderCategory.ERP
    AUTH_TYPE = AuthType.BASIC
    DOCS_URL = "https://razorpay.com/docs/api/payments/"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._key_id = (config.credentials.get("key_id") or "").strip()
        self._key_secret = (config.credentials.get("key_secret") or "").strip()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL, timeout=30.0, auth=(self._key_id, self._key_secret),
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._key_id or not self._key_secret:
            logger.warning("Razorpay key id or key secret not provided")
            return False
        try:
            client = await self._get_client()
            res = await client.get("/payments", params={"count": 1})
            if res.status_code != 200:
                logger.warning(f"Razorpay auth failed: {res.status_code}")
                return False
            self._authenticated = True
            return True
        except Exception as e:
            logger.error(f"Razorpay authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def _payments(self, start: int, end: int) -> Tuple[List[Dict[str, Any]], bool]:
        client = await self._get_client()
        rows: List[Dict[str, Any]] = []
        for page in range(MAX_PAGES):
            res = await client.get("/payments", params={
                "from": start, "to": end, "count": PER_PAGE, "skip": page * PER_PAGE,
            })
            if res.status_code != 200:
                raise RuntimeError(f"Razorpay /payments returned {res.status_code}")
            items = res.json().get("items") or []
            rows.extend(items)
            if len(items) < PER_PAGE:
                return rows, False
        return rows, True

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                    errors=["Authentication failed - check the Razorpay key id and key secret"],
                    sync_started=sync_started,
                )
            period_start, period_end = last_complete_month(sync_started.date())
            payments, truncated = await self._payments(*month_window_unix(period_start, period_end))
            summary = summarize_payments(payments)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(payments),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                errors=["Row limit reached; the month is incomplete"] if truncated else [],
                metadata={
                    "d2c_month": {"period": period_start.isoformat(), "values": month_values(summary)},
                    "razorpay": summary,
                },
            )
        except Exception as e:
            logger.error(f"Razorpay sync failed: {e}")
            return SyncResult(
                success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                errors=[str(e)], sync_started=sync_started, sync_completed=datetime.utcnow(),
            )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
