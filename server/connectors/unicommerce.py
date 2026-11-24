"""
Unicommerce (Uniware) connector - all-channel orders for Indian D2C brands.

Unicommerce is the order management system most Indian D2C brands run their
website, Amazon, Flipkart, Myntra, Nykaa, Ajio and quick-commerce orders
through. One connection therefore sees every sales channel, which is why its
values outrank Shopify's and Shiprocket's in d2c_months (see OMS_SOURCES).

For the last complete calendar month in India time it emits the D2C inputs the
Profit screen uses (orders shipped, gross sales and discounts ex-GST, RTO,
customer returns, COD share) plus a per-channel breakdown.

API (checked against https://documentation.unicommerce.com, Nov 2026):

- Auth: GET https://{tenant}.unicommerce.com/oauth/token
      ?grant_type=password&client_id=my-trusted-client&username=..&password=..
  -> access_token, token_type "bearer", refresh_token, expires_in (seconds).
  Renew: same URL with grant_type=refresh_token&refresh_token=...
  Every call then sends `Authorization: bearer <access_token>`.
  (docs/oauth.html, docs/oauth-refreshtoken.html)
- Search: POST /services/rest/v1/oms/saleOrder/search. Returns only order
  summaries (code, channel, status, dates) in `elements`, paged with
  searchOptions.displayStart / displayLength, `totalRecords` for the count.
  (docs/saleorder-search.html)
- Detail: POST /services/rest/v1/oms/saleorder/get {"code": ...} returns
  saleOrderDTO with saleOrderItems (prices, GST, item status), `cod`,
  `channel`, `currencyCode` and shippingPackages. One call per order, so the
  number fetched per sync is capped and truncation is reported.
  (docs/saleorder-get.html)

Both sale order APIs are tenant level, so no `Facility` header is sent (the
docs require it only for facility-level APIs, docs/using-the-uniware-apis.html).
Optional facility codes go in the documented `facilityCodes` body field.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from .http import http_client

from .base import AuthType, BaseConnector, ConnectorConfig, ProviderCategory, SyncResult
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
CLIENT_ID = "my-trusted-client"  # the documented public client id
TOKEN_PATH = "/oauth/token"
SEARCH_PATH = "/services/rest/v1/oms/saleOrder/search"
DETAIL_PATH = "/services/rest/v1/oms/saleorder/get"  # lower-case "saleorder", as documented

PAGE_SIZE = 100  # the docs give no maximum; 100 is a gentle page
MAX_SEARCH_PAGES = 200  # per COD pass: 20k order codes
MAX_ORDER_DETAILS = 5000  # per-order GET calls per sync; more is reported as truncated
DETAIL_CONCURRENCY = 4  # be gentle: the docs publish no rate limit
TOKEN_SKEW_SECONDS = 60

_TENANT_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

# Sale order item statusCode values. The Get Sale Order doc lists CANCELLED,
# FULFILLABLE, CREATED, PROCESSING, PACKED, READY_TO_DISPATCH, DISPATCHED,
# DELIVERED, REPLACED, RETURN_REQUESTED, COURIER_RETURN, RETURNED; the OMS
# overview adds UNFULFILLABLE, MANIFESTED, PICKING_*, LOCATION_NOT_SERVICABLE
# and RESHIPPED. Anything else is counted as "other" and reported by name.
NOT_SHIPPED = {
    "CREATED", "FULFILLABLE", "UNFULFILLABLE", "PROCESSING", "PACKED", "READY_TO_DISPATCH",
    "READY_TO_SHIP", "MANIFESTED", "PICKING_FOR_STAGING", "PICKING_FOR_INVOICING", "PICKING",
    "LOCATION_NOT_SERVICABLE", "LOCATION_NOT_SERVICEABLE", "PENDING_VERIFICATION",
    "PENDING_CUSTOMIZATION", "CUSTOMIZATION_COMPLETE", "ALTERNATE_SUGGESTED",
}
IN_TRANSIT = {"DISPATCHED", "SHIPPED", "IN_TRANSIT", "OUT_FOR_DELIVERY"}
DELIVERED = {"DELIVERED"}
REPLACED = {"REPLACED"}  # delivered, then exchanged; the revenue is kept
# Courier returned = RTO: shipped, came back undelivered. RESHIPPED is "a
# courier returned item is reshipped" (OMS overview), so the first shipment
# was an RTO too.
RTO = {"COURIER_RETURN", "COURIER_RETURNED", "RESHIPPED", "RTO"}
# Customer-initiated return (CIR) statuses. RETURNED needs care: see
# classify_item.
CUSTOMER_RETURN = {"RETURN_REQUESTED", "RETURN_EXPECTED", "RETURNED", "RETURN_ACKNOWLEDGED"}
CANCELLED = {"CANCELLED", "CANCELED"}

PACKAGE_REVERSE = {"RETURN_EXPECTED", "RETURNED", "RETURN_ACKNOWLEDGED"}
SHIPPED_ITEM_KINDS = ("delivered", "in_transit", "rto", "returned", "replaced")

GST_AMOUNT_FIELDS = (
    ("totalIntegratedGst", "integratedGst"),
    ("totalCentralGst", "centralGst"),
    ("totalStateGst", "stateGst"),
    ("totalUnionTerritoryGst", "unionTerritoryGst"),
)
GST_RATE_FIELDS = (
    "integratedGstPercentage", "centralGstPercentage", "stateGstPercentage", "unionTerritoryGstPercentage",
)


# --- credentials ---------------------------------------------------------------

def normalize_tenant(value: str) -> str:
    """Base URL for a tenant given as "acme", "acme.unicommerce.com" or a URL.

    Only *.unicommerce.com hosts are accepted, so a stored credential can never
    point the server at an arbitrary host.
    """
    raw = (value or "").strip().lower()
    if not raw:
        raise ValueError("Unicommerce tenant is required")
    host = urlparse(raw if "://" in raw else f"https://{raw}").hostname or ""
    host = host.rstrip(".")
    if host.endswith(".unicommerce.com"):
        tenant = host[: -len(".unicommerce.com")]
    elif "." not in host:
        tenant = host
    else:
        raise ValueError("Unicommerce tenant must be your account name or a <name>.unicommerce.com address")
    if not _TENANT_RE.match(tenant):
        raise ValueError("Unicommerce tenant must be your account name or a <name>.unicommerce.com address")
    return f"https://{tenant}.unicommerce.com"


def parse_facilities(value: Any) -> List[str]:
    if isinstance(value, (list, tuple)):
        parts = value
    else:
        parts = str(value or "").split(",")
    return [p.strip() for p in (str(x) for x in parts) if p.strip()]


# --- month window -----------------------------------------------------------------

def last_complete_month(today: date) -> Tuple[date, date]:
    last_prev = today.replace(day=1) - timedelta(days=1)
    return last_prev.replace(day=1), last_prev


def today_ist(now: Optional[datetime] = None) -> date:
    """Today's date in India; a sync at 02:00 IST on the 1st is already the new month."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(IST).date()


def month_window_utc(start: date, end: date) -> Tuple[str, str]:
    """The month in India time as the search API's ISO 8601 UTC fromDate/toDate."""
    start_dt = datetime(start.year, start.month, start.day, tzinfo=IST)
    end_dt = datetime(end.year, end.month, end.day, tzinfo=IST) + timedelta(days=1) - timedelta(milliseconds=1)

    def fmt(dt: datetime) -> str:
        utc = dt.astimezone(timezone.utc)
        return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"

    return fmt(start_dt), fmt(end_dt)


# --- pure math ---------------------------------------------------------------------

def _money(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _status(value: Any) -> str:
    return "_".join(str(value or "").upper().replace("-", " ").split())


def tax_rate(item: Dict[str, Any]) -> Optional[float]:
    """The item's GST rate as a fraction, or None when the item carries no tax data."""
    present = [item.get(k) for k in GST_RATE_FIELDS if item.get(k) is not None]
    if present:
        return sum(_money(v) or 0.0 for v in present) / 100.0
    if item.get("taxPercentage") is not None:
        return (_money(item.get("taxPercentage")) or 0.0) / 100.0
    return None


def gst_amount(item: Dict[str, Any]) -> Optional[float]:
    found = False
    total = 0.0
    for names in GST_AMOUNT_FIELDS:
        for name in names:
            if item.get(name) is not None:
                found = True
                total += _money(item.get(name)) or 0.0
                break
    return total if found else None


def ex_gst_factor(item: Dict[str, Any]) -> Tuple[Optional[float], str]:
    """Multiplier from the item's price to its ex-GST price, and how it was decided.

    The Unicommerce docs never say whether sellingPrice includes GST. Indian
    channels quote tax-inclusive prices and Uniware back-computes the GST on
    its invoices, so the safe default is INCLUSIVE: ex-GST = price / (1 + rate).
    When the item also carries the GST amount, the amount settles it: if it is
    closer to price * rate than to price * rate / (1 + rate), the price was
    already ex-GST and is used as is. With neither a rate nor an amount the
    factor is unknown (None) and the money totals are withheld, not guessed.
    """
    price = _money(item.get("sellingPrice")) or 0.0
    rate = tax_rate(item)
    amount = gst_amount(item)
    if rate is None and amount is None:
        return None, "unknown"
    if rate is None:
        # Only the amount: assume it is inside the price (the safe reading).
        if price <= 0:
            return 1.0, "inclusive"
        return max(0.0, price - (amount or 0.0)) / price, "inclusive"
    if rate <= 0:
        return 1.0, "zero_rated"
    if amount and price > 0:
        inclusive_amt = price * rate / (1 + rate)
        exclusive_amt = price * rate
        if abs(amount - exclusive_amt) < abs(amount - inclusive_amt):
            return 1.0, "exclusive"
    return 1.0 / (1.0 + rate), "inclusive"


def _packages(order: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(p.get("code")): p for p in order.get("shippingPackages") or [] if p.get("code")}


def classify_item(item: Dict[str, Any], packages: Dict[str, Dict[str, Any]]) -> Tuple[str, bool]:
    """Bucket for one sale order item, and whether an RTO was inferred.

    COURIER_RETURN is the documented courier-return (RTO) status, and a
    reverse pickup exists only for customer-initiated returns (CIR). RETURNED
    alone is ambiguous: Uniware also marks a courier-returned shipment
    RETURNED. Safest reading: a RETURNED item with no reverse pickup whose
    shipping package is in a reverse status and was never delivered is an
    RTO; every other RETURNED item is a customer return.
    """
    s = _status(item.get("statusCode") or item.get("status"))
    if s in CANCELLED:
        return "cancelled", False
    if s in RTO:
        return "rto", False
    if s in CUSTOMER_RETURN:
        if s == "RETURNED" and not item.get("reversePickupCode"):
            pkg = packages.get(str(item.get("shippingPackageCode") or ""))
            if pkg is not None:
                pkg_status = _status(pkg.get("status"))
                if pkg_status in PACKAGE_REVERSE and not pkg.get("delivered"):
                    return "rto", True
        return "returned", False
    if s in DELIVERED:
        return "delivered", False
    if s in REPLACED:
        return "replaced", False
    if s in IN_TRANSIT:
        return "in_transit", False
    if s in NOT_SHIPPED:
        return "not_shipped", False
    return "other", False


def _is_cod(order: Dict[str, Any]) -> Optional[bool]:
    for key in ("cod", "cashOnDelivery"):
        if order.get(key) is not None:
            value = order.get(key)
            if isinstance(value, str):
                return value.strip().lower() in ("true", "1", "yes")
            return bool(value)
    return None


def _new_channel() -> Dict[str, Any]:
    return {
        "orders": 0, "orders_shipped": 0, "cancelled": 0, "rto_orders": 0,
        "customer_returns_orders": 0, "gross_sales": 0.0, "discounts": 0.0,
        "customer_returns_value": 0.0, "items_tax_unknown": 0,
    }


def summarize_orders(orders: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """One month of saleOrderDTOs -> D2C counts, ex-GST values and channel mix.

    Order counts are per order; money comes from the items. An order counts as
    shipped when any of its items left the warehouse; it is an RTO when every
    shipped item came back undelivered, and a customer return when any shipped
    item was returned after delivery. Values exclude shipping, COD and gift-wrap
    charges (like Shopify's line-item total) and GST.
    """
    counts = {k: 0 for k in ("delivered", "in_transit", "returned", "rto", "cancelled", "not_shipped", "other")}
    item_counts: Dict[str, int] = {}
    other_statuses: set = set()
    tax_basis: Dict[str, int] = {}
    channels: Dict[str, Dict[str, Any]] = {}
    gross = discounts = returns_value = 0.0
    tax_unknown_items = 0
    non_inr_orders = 0
    partial_rto_orders = 0
    inferred_rto_items = 0
    replaced_items = 0
    cod_known = cod_yes = 0
    cod_missing = 0

    for order in orders:
        items = order.get("saleOrderItems") or []
        packages = _packages(order)
        channel = str(order.get("channel") or "UNKNOWN")
        ch = channels.setdefault(channel, _new_channel())
        currency = str(order.get("currencyCode") or "INR").upper()

        kinds: List[Tuple[str, Dict[str, Any]]] = []
        for item in items:
            kind, inferred = classify_item(item, packages)
            inferred_rto_items += int(inferred)
            item_counts[kind] = item_counts.get(kind, 0) + 1
            if kind == "other":
                other_statuses.add(_status(item.get("statusCode") or item.get("status")))
            kinds.append((kind, item))

        live = [k for k, _ in kinds if k != "cancelled"]
        shipped = [(k, it) for k, it in kinds if k in SHIPPED_ITEM_KINDS]

        if items and not live:
            outcome = "cancelled"
        elif not shipped:
            outcome = "other" if (not items or "other" in live) else "not_shipped"
        else:
            shipped_kinds = [k for k, _ in shipped]
            if all(k == "rto" for k in shipped_kinds):
                outcome = "rto"
            else:
                if "rto" in shipped_kinds:
                    partial_rto_orders += 1
                if "returned" in shipped_kinds:
                    outcome = "returned"
                elif "in_transit" in shipped_kinds and not any(k in ("delivered", "replaced") for k in shipped_kinds):
                    outcome = "in_transit"
                else:
                    outcome = "delivered"

        counts[outcome] += 1
        if outcome == "cancelled":
            ch["cancelled"] += 1
            continue
        ch["orders"] += 1
        if outcome not in ("delivered", "in_transit", "returned", "rto"):
            continue

        ch["orders_shipped"] += 1
        if outcome == "rto":
            ch["rto_orders"] += 1
        if outcome == "returned":
            ch["customer_returns_orders"] += 1
        if currency != "INR":
            non_inr_orders += 1

        if outcome != "rto":
            cod = _is_cod(order)
            if cod is None:
                cod_missing += 1
            else:
                cod_known += 1
                cod_yes += int(cod)

        for kind, item in shipped:
            replaced_items += int(kind == "replaced")
            factor, basis = ex_gst_factor(item)
            tax_basis[basis] = tax_basis.get(basis, 0) + 1
            if factor is None:
                tax_unknown_items += 1
                ch["items_tax_unknown"] += 1
                continue
            if currency != "INR":
                continue
            # sellingPrice is the unit price after discount (the docs call
            # totalPrice the "total final price" incl. charges); discount is
            # the item's discount, so gross before discounts = price + discount.
            price = (_money(item.get("sellingPrice")) or 0.0) * factor
            disc = (_money(item.get("discount")) or 0.0) * factor
            gross += price + disc
            discounts += disc
            ch["gross_sales"] += price + disc
            ch["discounts"] += disc
            if kind == "returned":
                returns_value += price
                ch["customer_returns_value"] += price

    shipped_orders = counts["delivered"] + counts["in_transit"] + counts["returned"] + counts["rto"]
    money_known = tax_unknown_items == 0 and non_inr_orders == 0

    for ch in channels.values():
        for key in ("gross_sales", "discounts", "customer_returns_value"):
            ch[key] = round(ch[key], 2)

    return {
        "orders_seen": sum(counts.values()),
        "orders_shipped": shipped_orders,
        "delivered": counts["delivered"],
        "in_transit": counts["in_transit"],
        "rto_orders": counts["rto"],
        "customer_returns_orders": counts["returned"],
        "cancelled": counts["cancelled"],
        "not_shipped": counts["not_shipped"],
        "other": counts["other"],
        "other_statuses": sorted(s for s in other_statuses if s),
        "item_counts": item_counts,
        "partial_rto_orders": partial_rto_orders,
        "inferred_rto_items": inferred_rto_items,
        "replaced_items": replaced_items,
        "tax_basis": tax_basis,
        "tax_unknown_items": tax_unknown_items,
        "non_inr_orders": non_inr_orders,
        # Ex-GST INR values; None when any shipped item had no tax data or was
        # in another currency, because a partial total would understate sales.
        "gross_sales": round(gross, 2) if money_known else None,
        "discounts": round(discounts, 2) if money_known else None,
        "customer_returns_value": round(returns_value, 2) if money_known else None,
        # Share of delivered (shipped minus RTO) orders paid COD, the
        # denominator compute_unit_economics applies it to.
        "cod_share": round(cod_yes / cod_known, 4) if cod_known and not cod_missing else None,
        "channels": channels,
    }


def month_values(summary: Dict[str, Any], complete: bool = True) -> Dict[str, Any]:
    """The fields of a d2c_months row this connector owns.

    When the month is incomplete (too many orders to fetch, or some detail
    calls failed) counts and totals would be understated, so they are None
    (the store ignores None from a connector). The COD share is a ratio and
    stays meaningful on the orders that were fetched.
    """
    if not complete:
        return {
            "orders_shipped": None, "gross_sales": None, "discounts": None, "rto_orders": None,
            "customer_returns_value": None, "customer_returns_orders": None,
            "cod_share": summary["cod_share"],
        }
    return {
        "orders_shipped": summary["orders_shipped"],
        "gross_sales": summary["gross_sales"],
        "discounts": summary["discounts"],
        "rto_orders": summary["rto_orders"],
        "customer_returns_value": summary["customer_returns_value"],
        "customer_returns_orders": summary["customer_returns_orders"],
        "cod_share": summary["cod_share"],
    }


# --- connector ---------------------------------------------------------------------

@ConnectorRegistry.register
class UnicommerceConnector(BaseConnector):
    PROVIDER_ID = "unicommerce"
    PROVIDER_NAME = "Unicommerce"
    PROVIDER_DESCRIPTION = (
        "Order management for Indian D2C across website, Amazon, Flipkart, Myntra, Nykaa and quick commerce. "
        "Imports shipped orders, sales ex-GST, discounts, RTO, returns and COD share by channel."
    )
    PROVIDER_CATEGORY = ProviderCategory.ERP
    AUTH_TYPE = AuthType.BASIC
    DOCS_URL = "https://documentation.unicommerce.com"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        creds = config.credentials or {}
        self._tenant_raw = str(creds.get("tenant") or "").strip()
        self._username = str(creds.get("username") or "").strip()
        self._password = str(creds.get("password") or "").strip()
        self._facilities = parse_facilities(creds.get("facility") or creds.get("facilities"))
        self._base_url: Optional[str] = None
        self._token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at = 0.0
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._base_url = normalize_tenant(self._tenant_raw)
            self._client = http_client(base_url=self._base_url, timeout=30.0)
        return self._client

    def _take_token(self, body: Dict[str, Any]) -> bool:
        token = body.get("access_token")
        if not token:
            return False
        self._token = token
        self._refresh_token = body.get("refresh_token") or self._refresh_token
        try:
            ttl = float(body.get("expires_in") or 0)
        except (TypeError, ValueError):
            ttl = 0.0
        self._expires_at = time.time() + ttl if ttl > 0 else 0.0
        return True

    async def _token_call(self, params: Dict[str, str]) -> bool:
        client = await self._get_client()
        # The password grant puts credentials in the query string, as the
        # docs specify; never log the request URL.
        res = await client.get(TOKEN_PATH, params={"client_id": CLIENT_ID, **params},
                               headers={"Content-Type": "application/json"})
        if res.status_code != 200:
            logger.warning(f"Unicommerce token call failed: {res.status_code}")
            return False
        try:
            return self._take_token(res.json())
        except ValueError:
            return False

    async def authenticate(self) -> bool:
        if not self._tenant_raw or not self._username or not self._password:
            logger.warning("Unicommerce tenant, username or password not provided")
            return False
        try:
            ok = await self._token_call({
                "grant_type": "password", "username": self._username, "password": self._password,
            })
            self._authenticated = ok
            return ok
        except ValueError as e:  # bad tenant
            logger.warning(f"Unicommerce: {e}")
            return False
        except Exception as e:
            logger.error(f"Unicommerce authentication error: {e}")
            return False

    async def _renew(self) -> bool:
        if self._refresh_token:
            try:
                if await self._token_call({"grant_type": "refresh_token", "refresh_token": self._refresh_token}):
                    return True
            except Exception as e:
                logger.info(f"Unicommerce token refresh failed, signing in again: {e}")
        return await self.authenticate()

    async def _ensure_token(self) -> None:
        if not self._token or (self._expires_at and time.time() > self._expires_at - TOKEN_SKEW_SECONDS):
            if not await self._renew():
                raise RuntimeError("Unicommerce sign-in failed")

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def _post(self, path: str, body: Dict[str, Any]) -> httpx.Response:
        await self._ensure_token()
        client = await self._get_client()
        res = await client.post(path, json=body, headers={"Authorization": f"bearer {self._token}"})
        if res.status_code == 401:
            if not await self._renew():
                raise RuntimeError("Unicommerce sign-in failed")
            res = await client.post(path, json=body, headers={"Authorization": f"bearer {self._token}"})
        return res

    async def _search_codes(self, from_date: str, to_date: str) -> Tuple[List[Dict[str, Any]], bool]:
        """Every order created in the window, as search summaries, deduped by code.

        The docs give `cashOnDelivery` a default of true. If the server applied
        that default when the field is omitted, a plain search would return
        only COD orders, so the search is run once for COD and once for
        prepaid and the results merged. Either way every order is seen.
        """
        found: Dict[str, Dict[str, Any]] = {}
        truncated = False
        for cod in (True, False):
            start = 0
            for _ in range(MAX_SEARCH_PAGES):
                body: Dict[str, Any] = {
                    "fromDate": from_date, "toDate": to_date, "dateType": "CREATED", "cashOnDelivery": cod,
                    "searchOptions": {"displayStart": start, "displayLength": PAGE_SIZE, "getCount": True},
                }
                if self._facilities:
                    body["facilityCodes"] = self._facilities
                res = await self._post(SEARCH_PATH, body)
                if res.status_code != 200:
                    raise RuntimeError(f"Unicommerce order search returned {res.status_code}")
                data = res.json()
                if data.get("successful") is False:
                    raise RuntimeError(f"Unicommerce order search failed: {data.get('message') or data.get('errors')}")
                rows = data.get("elements") or []
                for row in rows:
                    code = row.get("code")
                    if code and code not in found:
                        found[code] = row
                start += len(rows)
                total = data.get("totalRecords")
                if not rows or len(rows) < PAGE_SIZE or (isinstance(total, int) and start >= total):
                    break
            else:
                truncated = True
        return list(found.values()), truncated

    async def _get_order(self, code: str) -> Optional[Dict[str, Any]]:
        body: Dict[str, Any] = {"code": code, "paymentDetailRequired": False}
        if self._facilities:
            body["facilityCodes"] = self._facilities
        for attempt in range(2):  # one extra try on a transient failure
            try:
                res = await self._post(DETAIL_PATH, body)
                if res.status_code == 200:
                    data = res.json()
                    dto = data.get("saleOrderDTO")
                    if data.get("successful") is not False and dto:
                        return dto
            except RuntimeError:
                raise
            except Exception as e:
                logger.info(f"Unicommerce order {code} fetch error: {e}")
        return None

    async def _get_orders(self, codes: List[str]) -> Tuple[List[Dict[str, Any]], int]:
        sem = asyncio.Semaphore(DETAIL_CONCURRENCY)

        async def one(code: str) -> Optional[Dict[str, Any]]:
            async with sem:
                return await self._get_order(code)

        results = await asyncio.gather(*(one(c) for c in codes))
        orders = [r for r in results if r]
        return orders, len(codes) - len(orders)

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                    errors=["Authentication failed - check the Unicommerce tenant, username and password"],
                    sync_started=sync_started,
                )
            period_start, period_end = last_complete_month(today_ist())
            from_date, to_date = month_window_utc(period_start, period_end)

            summaries, search_truncated = await self._search_codes(from_date, to_date)
            codes = [s["code"] for s in summaries]
            detail_truncated = len(codes) > MAX_ORDER_DETAILS
            orders, failed = await self._get_orders(codes[:MAX_ORDER_DETAILS])

            # The search summary carries the channel too; fill it if the detail lacks it.
            by_code = {s["code"]: s for s in summaries}
            for o in orders:
                if not o.get("channel") and by_code.get(o.get("code"), {}).get("channel"):
                    o["channel"] = by_code[o["code"]]["channel"]

            summary = summarize_orders(orders)
            complete = not (search_truncated or detail_truncated or failed)
            errors: List[str] = []
            if search_truncated or detail_truncated:
                errors.append(
                    f"Order limit reached ({len(codes)} orders found, {MAX_ORDER_DETAILS} fetched); "
                    "the month is incomplete, so totals were not saved"
                )
            if failed:
                errors.append(f"{failed} order(s) could not be fetched; the month is incomplete, so totals were not saved")

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(orders),
                records_failed=failed,
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                errors=errors,
                metadata={
                    "d2c_month": {"period": period_start.isoformat(), "values": month_values(summary, complete)},
                    "unicommerce": {
                        **summary,
                        "period": period_start.isoformat(),
                        "orders_found": len(codes),
                        "orders_fetched": len(orders),
                        "orders_failed": failed,
                        "truncated": search_truncated or detail_truncated,
                        "complete": complete,
                        "facilities": self._facilities,
                    },
                },
            )
        except Exception as e:
            logger.error(f"Unicommerce sync failed: {e}")
            return SyncResult(
                success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                errors=[str(e)], sync_started=sync_started, sync_completed=datetime.utcnow(),
            )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
