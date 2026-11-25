"""
Amazon Seller connector (Selling Partner API) - the brand's Amazon.in channel.

For Indian D2C brands, Amazon is usually the biggest channel next to the
website. Shopify can't see it, and an OMS (Unicommerce/EasyEcom) sees the
orders but not what Amazon kept. This connector reads the seller's own
financial events for the last complete month (India time) and reports the
channel's sales, refunds and Amazon fees.

The figures are kept as an Amazon channel summary on the connection
(metadata "channel_sales"). They are NOT written into the D2C month: that
row is one blended set of inputs, and Amazon's sales would overwrite the
website's (or double count what an OMS already reports for every channel).

API:
- Login with Amazon (LWA) refresh-token grant, POST https://api.amazon.com/auth/o2/token.
  The access token goes in the x-amz-access-token header; SigV4 signing is no
  longer required (dropped Oct 2023).
  https://developer-docs.amazon.com/sp-api/docs/connecting-to-the-selling-partner-api
- Sellers getMarketplaceParticipations, GET /sellers/v1/marketplaceParticipations
  (used to verify the connection and find the seller's marketplaces).
- Finances v0 listFinancialEvents, GET /finances/v0/financialEvents
  https://developer-docs.amazon.com/sp-api/docs/finances-api-reference
  Events are keyed on PostedDate (when Amazon charged/refunded), which for
  a shipment is the day it shipped, so a month's events are that month's
  shipped orders. Rate limit 0.5 req/s (burst 30); events from the last 48h
  may be missing, which doesn't affect a complete past month.
- India is served from the EU endpoint; marketplace Amazon.in = A21TJRUUN4KGV.
  https://developer-docs.amazon.com/sp-api/docs/marketplace-ids

GST: ItemChargeList splits each item into Principal, ShippingCharge, GiftWrap
and their Tax / ShippingTax / GiftwrapTax. The charges are additive (the sum
is what the buyer paid, which is how settlement adds them up), so sales ex-GST
are the non-tax charges. If a month has sales but no GST charges at all we
can't tell whether prices already include GST, so the ex-GST figures are None
with a warning rather than a guess. Verify against a live seller account.
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx

from .base import AuthType, BaseConnector, ConnectorConfig, ProviderCategory, SyncResult
from .http import http_client
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
SP_API_HOSTS = {
    "na": "https://sellingpartnerapi-na.amazon.com",
    "eu": "https://sellingpartnerapi-eu.amazon.com",
    "fe": "https://sellingpartnerapi-fe.amazon.com",
}
INDIA_MARKETPLACE_ID = "A21TJRUUN4KGV"
INDIA_MARKETPLACE_NAME = "amazon.in"
PAGE_SIZE = 100  # documented maximum MaxResultsPerPage
MAX_PAGES = 150  # ~15k events; a truncated month is reported, never hidden
PAGE_INTERVAL = 2.1  # seconds between pages: 0.5 req/s documented rate
IST = timezone(timedelta(hours=5, minutes=30))

TAX_CHARGES = {"Tax", "ShippingTax", "GiftwrapTax"}
SALE_CHARGES = {"Principal", "ShippingCharge", "GiftWrap"}


def last_complete_month(today: date) -> Tuple[date, date]:
    last_prev = today.replace(day=1) - timedelta(days=1)
    return last_prev.replace(day=1), last_prev


def month_window(start: date, end: date) -> Tuple[str, str]:
    """The month in India time as PostedAfter / PostedBefore (UTC ISO-8601)."""
    after = datetime(start.year, start.month, start.day, tzinfo=IST)
    before = datetime(end.year, end.month, end.day, tzinfo=IST) + timedelta(days=1)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return after.astimezone(timezone.utc).strftime(fmt), before.astimezone(timezone.utc).strftime(fmt)


def _paise(money: Any) -> Tuple[int, str]:
    """(amount in paise, currency) from an SP-API Currency object."""
    if not isinstance(money, dict):
        return 0, ""
    raw = money.get("CurrencyAmount")
    try:
        amount = int(round(float(raw) * 100)) if raw is not None else 0
    except (TypeError, ValueError):
        amount = 0
    return amount, str(money.get("CurrencyCode") or "").upper()


def _is_india(event: Dict[str, Any]) -> bool:
    # The docs name the field MarketplaceName ("Amazon.in"); treat a missing
    # name as India because the connection is India-scoped.
    name = str(event.get("MarketplaceName") or INDIA_MARKETPLACE_NAME).strip().lower()
    return name == INDIA_MARKETPLACE_NAME


class _Totals:
    def __init__(self) -> None:
        self.sales = 0  # non-tax charges, paise
        self.tax = 0
        self.promotions = 0  # as reported (negative = discount)
        self.fees = 0  # as reported (negative = Amazon kept it)
        self.withheld = 0  # TCS/TDS withheld, claimable, not a fee
        self.other_charges = 0
        self.fee_types: Counter = Counter()
        self.non_inr = 0

    def add_charges(self, charges: Iterable[Dict[str, Any]]) -> None:
        for c in charges or []:
            amount, cur = _paise(c.get("ChargeAmount"))
            if cur and cur != "INR":
                self.non_inr += 1
                continue
            ctype = str(c.get("ChargeType") or "")
            if ctype in TAX_CHARGES:
                self.tax += amount
            elif ctype in SALE_CHARGES:
                self.sales += amount
            else:
                self.other_charges += amount

    def add_fees(self, fees: Iterable[Dict[str, Any]]) -> None:
        for f in fees or []:
            amount, cur = _paise(f.get("FeeAmount"))
            if cur and cur != "INR":
                self.non_inr += 1
                continue
            self.fees += amount
            self.fee_types[str(f.get("FeeType") or "Other")] += amount

    def add_promotions(self, promos: Iterable[Dict[str, Any]]) -> None:
        for p in promos or []:
            amount, cur = _paise(p.get("PromotionAmount"))
            if cur and cur != "INR":
                self.non_inr += 1
                continue
            self.promotions += amount

    def add_withheld(self, groups: Iterable[Dict[str, Any]]) -> None:
        for g in groups or []:
            for c in g.get("TaxesWithheld") or []:
                amount, cur = _paise(c.get("ChargeAmount"))
                if cur and cur != "INR":
                    continue
                self.withheld += amount


def summarize_events(
    shipments: Iterable[Dict[str, Any]],
    refunds: Iterable[Dict[str, Any]],
    service_fees: Iterable[Dict[str, Any]] = (),
    ad_payments: Iterable[Dict[str, Any]] = (),
) -> Dict[str, Any]:
    """Amazon.in sales, refunds and fees for one month of financial events."""
    sold, back = _Totals(), _Totals()
    orders, refund_orders = set(), set()
    units = 0
    other_marketplace = 0

    for ev in shipments:
        if not _is_india(ev):
            other_marketplace += 1
            continue
        if ev.get("AmazonOrderId"):
            orders.add(ev["AmazonOrderId"])
        for item in ev.get("ShipmentItemList") or []:
            try:
                units += int(item.get("QuantityShipped") or 0)
            except (TypeError, ValueError):
                pass
            sold.add_charges(item.get("ItemChargeList"))
            sold.add_fees(item.get("ItemFeeList"))
            sold.add_promotions(item.get("PromotionList"))
            sold.add_withheld(item.get("ItemTaxWithheldList"))
        sold.add_fees(ev.get("ShipmentFeeList"))
        sold.add_fees(ev.get("OrderFeeList"))

    for ev in refunds:
        if not _is_india(ev):
            other_marketplace += 1
            continue
        if ev.get("AmazonOrderId"):
            refund_orders.add(ev["AmazonOrderId"])
        for item in ev.get("ShipmentItemAdjustmentList") or []:
            back.add_charges(item.get("ItemChargeAdjustmentList"))
            back.add_fees(item.get("ItemFeeAdjustmentList"))
            back.add_promotions(item.get("PromotionAdjustmentList"))
            back.add_withheld(item.get("ItemTaxWithheldList"))

    # Account-level fees (subscription, storage, etc.) are charged to the
    # seller, not to an order: they count towards Amazon's take.
    service = _Totals()
    for ev in service_fees:
        service.add_fees(ev.get("FeeList"))

    # Sponsored Products invoices paid from the seller's Amazon balance.
    # baseValue is before GST; a "refund" transaction reverses a charge.
    ads_paise = 0
    for ev in ad_payments:
        amount, cur = _paise(ev.get("baseValue"))
        if cur and cur != "INR":
            continue
        sign = -1 if str(ev.get("transactionType") or "").lower() == "refund" else 1
        ads_paise += sign * abs(amount)

    def rupees(p: Optional[int]) -> Optional[float]:
        return None if p is None else round(p / 100, 2)

    gst_known = sold.tax != 0 or sold.sales == 0
    warnings: List[str] = []
    if not gst_known:
        warnings.append("Amazon reported sales with no GST charges, so we can't tell whether "
                        "its prices include GST. Sales ex-GST are left blank.")

    # Refund adjustments are negative for the money going back to the buyer.
    refunds_ex_gst = -back.sales if gst_known else None
    net_sales = (sold.sales + sold.promotions) if gst_known else None
    fees_total = -(sold.fees + back.fees + service.fees)  # positive = Amazon kept it
    fee_types = Counter()
    for t in (sold, back, service):
        fee_types.update(t.fee_types)

    return {
        "marketplace": "Amazon.in",
        "orders_shipped": len(orders),
        "units_shipped": units,
        "refunded_orders": len(refund_orders),
        "sales_ex_gst": rupees(sold.sales) if gst_known else None,
        "gst_on_sales": rupees(sold.tax),
        "promotions": rupees(-sold.promotions),
        "net_sales_ex_gst": rupees(net_sales),
        "refunds_ex_gst": rupees(refunds_ex_gst),
        "amazon_fees": rupees(fees_total),
        "fee_breakdown": {k: rupees(-v) for k, v in fee_types.most_common() if v},
        # None, not 0, when there are no sales: a rate can't be worked out.
        "amazon_fee_pct": (
            round(fees_total / net_sales, 5) if net_sales and net_sales > 0 else None
        ),
        "tax_withheld": rupees(-(sold.withheld + back.withheld)),
        # Billed when an invoice threshold is hit, not daily spend: shown for
        # reference, not fed into marketing spend.
        "sponsored_ads_billed_ex_gst": rupees(ads_paise),
        "other_marketplace_events_skipped": other_marketplace,
        "non_inr_lines_skipped": sold.non_inr + back.non_inr + service.non_inr,
        "warnings": warnings,
    }


def marketplaces_from_participations(body: Dict[str, Any]) -> List[str]:
    """Marketplace ids the seller actively sells in."""
    ids = []
    for row in (body or {}).get("payload") or []:
        mp = row.get("marketplace") or {}
        part = row.get("participation") or {}
        if mp.get("id") and part.get("isParticipating", True):
            ids.append(str(mp["id"]))
    return ids


@ConnectorRegistry.register
class AmazonSellerConnector(BaseConnector):
    PROVIDER_ID = "amazon"
    PROVIDER_NAME = "Amazon Seller Central"
    PROVIDER_DESCRIPTION = "Amazon.in channel: shipped orders, refunds and Amazon fees from your Seller Central account."
    PROVIDER_CATEGORY = ProviderCategory.ERP
    AUTH_TYPE = AuthType.OAUTH2
    DOCS_URL = "https://developer-docs.amazon.com/sp-api/docs/finances-api-reference"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        creds = config.credentials or {}
        self._client_id = (creds.get("client_id") or "").strip()
        self._client_secret = (creds.get("client_secret") or "").strip()
        self._refresh_token = (creds.get("refresh_token") or "").strip()
        region = (creds.get("region") or "eu").strip().lower()
        self._region = region if region in SP_API_HOSTS else "eu"
        self._access_token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def base_url(self) -> str:
        return SP_API_HOSTS[self._region]

    async def _token(self) -> Optional[str]:
        if self._access_token:
            return self._access_token
        async with http_client(timeout=30.0) as client:
            res = await client.post(LWA_TOKEN_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            })
        if res.status_code != 200:
            logger.warning("Amazon LWA token refresh failed: %s", res.status_code)
            return None
        self._access_token = (res.json() or {}).get("access_token")
        return self._access_token

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = http_client(
                base_url=self.base_url, timeout=60.0,
                headers={"x-amz-access-token": self._access_token or "", "Accept": "application/json"},
            )
        return self._client

    async def authenticate(self) -> bool:
        if not (self._client_id and self._client_secret and self._refresh_token):
            logger.warning("Amazon client id, client secret or refresh token not provided")
            return False
        try:
            if not await self._token():
                return False
            client = await self._get_client()
            res = await client.get("/sellers/v1/marketplaceParticipations")
            if res.status_code != 200:
                logger.warning("Amazon auth check failed: %s", res.status_code)
                return False
            self._authenticated = True
            return True
        except Exception as e:
            logger.error(f"Amazon authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def _financial_events(self, after: str, before: str) -> Tuple[Dict[str, List[Dict[str, Any]]], bool]:
        """Every financial event in the window, by list name. Returns (lists, truncated)."""
        client = await self._get_client()
        lists: Dict[str, List[Dict[str, Any]]] = {}
        next_token: Optional[str] = None
        seen = set()
        for page in range(MAX_PAGES):
            if page:
                await asyncio.sleep(PAGE_INTERVAL)
            params: Dict[str, Any] = {"PostedAfter": after, "PostedBefore": before,
                                      "MaxResultsPerPage": PAGE_SIZE}
            if next_token:
                params["NextToken"] = next_token
            res = await client.get("/finances/v0/financialEvents", params=params)
            if res.status_code != 200:
                raise RuntimeError(f"Amazon listFinancialEvents returned {res.status_code}")
            payload = (res.json() or {}).get("payload") or {}
            for name, rows in (payload.get("FinancialEvents") or {}).items():
                if isinstance(rows, list):
                    lists.setdefault(name, []).extend(rows)
            next_token = payload.get("NextToken")
            if not next_token or next_token in seen:
                return lists, False
            seen.add(next_token)
        return lists, True

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                    errors=["Authentication failed - reconnect Amazon Seller Central"],
                    sync_started=sync_started, metadata={"needs_reauth": True},
                )
            period_start, period_end = last_complete_month(datetime.now(IST).date())
            lists, truncated = await self._financial_events(*month_window(period_start, period_end))
            summary = summarize_events(
                lists.get("ShipmentEventList", []),
                lists.get("RefundEventList", []),
                lists.get("ServiceFeeEventList", []),
                lists.get("ProductAdsPaymentEventList", []),
            )
            errors = []
            if truncated:
                errors.append("Row limit reached; the month is incomplete")
                for key in ("orders_shipped", "units_shipped", "refunded_orders"):
                    summary[key] = None
                for key in ("sales_ex_gst", "gst_on_sales", "promotions", "net_sales_ex_gst",
                            "refunds_ex_gst", "amazon_fees", "amazon_fee_pct"):
                    summary[key] = None
            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=sum(len(v) for v in lists.values()),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                errors=errors,
                warnings=list(summary.get("warnings") or []),
                metadata={
                    "amazon": summary,
                    "channel_sales": {
                        "channel": "amazon",
                        "months": [{"period": period_start.isoformat(), **summary}],
                    },
                },
            )
        except Exception as e:
            logger.error(f"Amazon sync failed: {e}")
            return SyncResult(
                success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                errors=[str(e)], sync_started=sync_started, sync_completed=datetime.utcnow(),
            )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
