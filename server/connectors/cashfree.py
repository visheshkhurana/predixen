"""
Cashfree Payments connector - payment gateway fees for Indian D2C brands.

The Cashfree counterpart of razorpay.py. Shopify knows the order value; the
payment gateway knows what it kept. This connector reads the brand's own
Cashfree payment events for the last complete month (India time) and works out
the gateway fee as a share of captured prepaid value, ex-GST, which is the
`payment_gateway_pct` input of the D2C contribution margin.

API (version 2026-01-01, the latest documented):
- PG Reconciliation, POST /pg/recon
  https://www.cashfree.com/docs/api-reference/payments/latest/pg-reconciliation/pg-reconciliation
  Every event on the payment account in a date range (PAYMENT, REFUND,
  DISPUTE, CHARGEBACK, ...), each with event_amount, event_service_charge and
  event_service_tax, plus payment_details (payment_group = payment method).
  It is keyed on event time, not settlement date, so a month's payments are
  all in even if Cashfree has not settled them yet. Settlement Reconciliation
  (POST /settlement/recon) was rejected for that reason: it groups by
  settlement and would shift month-end payments into the next month.
- Auth: headers x-client-id / x-client-secret plus x-api-version.
  https://www.cashfree.com/docs/api-reference/authentication
- Base URLs: https://api.cashfree.com/pg (production),
  https://sandbox.cashfree.com/pg (sandbox).
  https://www.cashfree.com/docs/api-reference/payments/latest/overview
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx
from .http import http_client

from .base import AuthType, BaseConnector, ConnectorConfig, ProviderCategory, SyncResult
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

BASE_URLS = {
    "production": "https://api.cashfree.com/pg",
    "sandbox": "https://sandbox.cashfree.com/pg",
}
API_VERSION = "2026-01-01"
PAGE_LIMIT = 1000  # documented maximum for /recon (default is 10)
MAX_PAGES = 200  # 200k events; a truncated month is reported, never hidden
IST = timezone(timedelta(hours=5, minutes=30))


def last_complete_month(today: date) -> Tuple[date, date]:
    last_prev = today.replace(day=1) - timedelta(days=1)
    return last_prev.replace(day=1), last_prev


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def month_window(start: date, end: date) -> Tuple[str, str]:
    """The month in India time, as /recon start_date/end_date (inclusive, UTC).

    The docs' example sends ISO-8601 with a trailing Z ('2022-07-20T00:00:00Z'),
    so the IST month boundaries are converted to UTC: 1 Oct 00:00 IST is
    30 Sep 18:30Z. If Cashfree were to ignore the Z and read the times as IST,
    the window would shift by 5h30m at each end; sending explicit UTC is the
    reading that matches the documented format.
    """
    start_dt = datetime(start.year, start.month, start.day, tzinfo=IST)
    end_dt = datetime(end.year, end.month, end.day, tzinfo=IST) + timedelta(days=1) - timedelta(seconds=1)
    return _utc_iso(start_dt), _utc_iso(end_dt)


def _paise(value: Any) -> int:
    """Cashfree reports rupees as decimals (40, 7.2); count in integer paise."""
    try:
        return int(round(float(value) * 100)) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def _first(*values: Any) -> Any:
    for v in values:
        if v is not None:
            return v
    return None


def summarize_events(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Fees, refunds and method mix for one month of /recon events.

    Only successful INR PAYMENT events count towards captured value and fees.
    Mirroring the Razorpay connector: a payment that is later refunded was
    captured first and the gateway keeps its fee, so the payment stays in;
    REFUND events are reported (refunded_value) but do not reduce captured
    value. Any service charge Cashfree books on refund events is reported as
    `refund_service_charge_ex_gst` and kept out of the rate, because Razorpay's
    rate has no equivalent and the docs don't say whether it is a fee or a fee
    reversal.

    `event_service_charge` is the fee and `event_service_tax` the GST on it
    (docs example: amount 4000, charge 40, tax 7.2, settled 3952.8). The fee
    ex-GST is used for the margin, matching the ex-GST sales Shopify reports,
    because a GST-registered brand claims that GST back as input credit.
    """
    captured_paise = charge_paise = tax_paise = refunded_paise = 0
    refund_charge_paise = 0
    captured_count = failed = non_inr = 0
    methods: Counter = Counter()

    for e in events:
        ev = e.get("event_details") or {}
        pay = e.get("payment_details") or {}
        etype = str(ev.get("event_type") or "").upper()
        status = str(ev.get("event_status") or "").upper()
        currency = str(_first(ev.get("event_currency"), pay.get("payment_currency")) or "INR").upper()

        if etype == "PAYMENT":
            if status in ("FAILED", "CANCELLED"):
                failed += 1
                continue
            if status != "SUCCESS":
                continue  # PENDING and anything else: not captured
            if currency != "INR":
                non_inr += 1
                continue
            amount = _paise(_first(ev.get("event_amount"), pay.get("payment_amount")))
            captured_count += 1
            captured_paise += amount
            charge_paise += _paise(_first(ev.get("event_service_charge"), pay.get("payment_service_charge")))
            tax_paise += _paise(_first(ev.get("event_service_tax"), pay.get("payment_service_tax")))
            methods[str(pay.get("payment_group") or "other")] += amount
        elif etype == "REFUND" and status == "SUCCESS" and currency == "INR":
            refunded_paise += abs(_paise(ev.get("event_amount")))
            refund_charge_paise += _paise(ev.get("event_service_charge"))

    return {
        "captured_payments": captured_count,
        "failed_payments": failed,
        "non_inr_payments_skipped": non_inr,
        "captured_value": round(captured_paise / 100, 2),
        "refunded_value": round(refunded_paise / 100, 2),
        "fees_incl_gst": round((charge_paise + tax_paise) / 100, 2),
        "gst_on_fees": round(tax_paise / 100, 2),
        "fees_ex_gst": round(charge_paise / 100, 2),
        "refund_service_charge_ex_gst": round(refund_charge_paise / 100, 2),
        # None, not 0, with no captured value: the engine then asks for the
        # gateway rate instead of assuming payments are free.
        "payment_gateway_pct": (
            round(charge_paise / captured_paise, 5) if captured_paise > 0 and charge_paise >= 0 else None
        ),
        "method_share": (
            {m: round(v / captured_paise, 4) for m, v in methods.most_common()} if captured_paise else {}
        ),
    }


def month_values(summary: Dict[str, Any]) -> Dict[str, Any]:
    """The fields of a d2c_months row this connector owns."""
    return {"payment_gateway_pct": summary["payment_gateway_pct"]}


@ConnectorRegistry.register
class CashfreeConnector(BaseConnector):
    PROVIDER_ID = "cashfree"
    PROVIDER_NAME = "Cashfree Payments"
    PROVIDER_DESCRIPTION = "Payment gateway for Indian D2C. Imports successful payments, refunds and gateway fees."
    PROVIDER_CATEGORY = ProviderCategory.ERP
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://www.cashfree.com/docs/api-reference/payments/latest/pg-reconciliation/pg-reconciliation"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        creds = config.credentials or {}
        self._client_id = (creds.get("client_id") or "").strip()
        self._client_secret = (creds.get("client_secret") or "").strip()
        env = (creds.get("environment") or "production").strip().lower()
        self._environment = "sandbox" if env in ("sandbox", "test") else "production"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def base_url(self) -> str:
        return BASE_URLS[self._environment]

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = http_client(
                base_url=self.base_url,
                timeout=30.0,
                headers={
                    "x-client-id": self._client_id,
                    "x-client-secret": self._client_secret,
                    "x-api-version": API_VERSION,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def _recon_page(self, start: str, end: str, limit: int, cursor: Optional[str]) -> httpx.Response:
        client = await self._get_client()
        return await client.post("/recon", json={
            "pagination": {"limit": limit, "cursor": cursor},
            "filters": {"start_date": start, "end_date": end},
        })

    async def authenticate(self) -> bool:
        if not self._client_id or not self._client_secret:
            logger.warning("Cashfree client id or client secret not provided")
            return False
        try:
            # Read-only: one event from yesterday's recon. Cashfree has no
            # dedicated whoami endpoint for PG keys.
            y = datetime.now(IST).date() - timedelta(days=1)
            res = await self._recon_page(*month_window(y, y), limit=1, cursor=None)
            if res.status_code != 200:
                logger.warning(f"Cashfree auth failed: {res.status_code}")
                return False
            self._authenticated = True
            return True
        except Exception as e:
            logger.error(f"Cashfree authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def _events(self, start: str, end: str) -> Tuple[List[Dict[str, Any]], bool]:
        """All /recon events in the window. Returns (events, truncated).

        Paging follows the documented cursor: pass null first, then the cursor
        each response returns. The docs don't say how the last page is marked,
        so stop on any of: no cursor, an empty page, or a cursor repeated
        (which would otherwise loop forever).
        """
        rows: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        seen = set()
        for _ in range(MAX_PAGES):
            res = await self._recon_page(start, end, PAGE_LIMIT, cursor)
            if res.status_code != 200:
                raise RuntimeError(f"Cashfree /recon returned {res.status_code}")
            body = res.json() or {}
            data = body.get("data") or []
            rows.extend(data)
            cursor = body.get("cursor")
            if not data or not cursor or cursor in seen:
                return rows, False
            seen.add(cursor)
        return rows, True

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                    errors=["Authentication failed - check the Cashfree client id, client secret and environment"],
                    sync_started=sync_started,
                )
            period_start, period_end = last_complete_month(sync_started.date())
            events, truncated = await self._events(*month_window(period_start, period_end))
            summary = summarize_events(events)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(events),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                errors=["Row limit reached; the month is incomplete"] if truncated else [],
                metadata={
                    "d2c_month": {"period": period_start.isoformat(), "values": month_values(summary)},
                    "cashfree": summary,
                },
            )
        except Exception as e:
            logger.error(f"Cashfree sync failed: {e}")
            return SyncResult(
                success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                errors=[str(e)], sync_started=sync_started, sync_completed=datetime.utcnow(),
            )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
