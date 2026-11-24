"""
EasyEcom connector - orders, RTO, returns and COD share for Indian D2C brands.

EasyEcom is the order/inventory system many Indian D2C brands run their
website, Amazon, Flipkart, Myntra, Nykaa, Meesho and quick-commerce orders
through. For the last complete calendar month (India time) this connector
emits the D2C inputs the Profit screen uses, plus a per-channel breakdown.

API (V2.1): https://api-docs.easyecom.io (Postman documenter; collection
20795951/2s93ecupH6). What the docs say, and what this file relies on:

- Auth: POST /access/token with {email, password, location_key} returns
  data.token.jwt_token. Every call, the token call included, needs the
  `x-api-key` header; data calls also need `Authorization: Bearer <jwt>`.
  The docs text says the token is valid 24 hours (the sample response shows
  expires_in 7884000); we fetch a fresh one per sync, so either is fine.
  Bad credentials can come back as HTTP 200 with only a "message", so a
  missing jwt_token is treated as an auth failure.
- Orders: GET /orders/V2/getAllOrders with start_date/end_date (order date,
  "YYYY-MM-DD HH:MM:SS", account time zone = Asia/Kolkata). The range "should
  not exceed 7 days", so the month is fetched in 7-day chunks. limit max 250.
  Pagination: data.nextUrl is a relative URL to call as-is, "without any
  filters". An empty window may come back as HTTP 400 with "No Data Found".
- Returns: GET /orders/getAllReturns lists credit notes (data.credit_notes,
  same nextUrl paging) filterable by credit_note_start_date/end_date. Each
  credit note carries return_type, return_awb_number and per-item
  credit_note_total_item_excluding_tax. It is location-scoped: it returns
  only the JWT's location, so the founder should use the primary location key.
- Status tables: order_status_id 1 pending, 2 assigned, 3 confirmed, 4 out of
  stock, 5 printed, 6 ready to dispatch, 7 shipped, 9 cancelled, 10 returned,
  11 upcoming. shipping_status_id 3 delivered, 22 lost, 9/17/24/25 RTO
  (delivered back / initiated / in transit / undelivered), 26/7 reverse
  pickup scheduled / picked up (a customer return).
- RTO vs customer return: order_status 10 "Returned" covers both. The docs'
  Returns FAQ: "the reverse AWB will always be the same as the forward for
  RTO cases". We use, in order: an RTO / reverse-pickup shipping status, the
  credit note's return_type, then return AWB == forward AWB. A returned order
  none of these settle is "unclassified" and makes rto_orders and the
  customer-return fields None rather than a guess.

GST: the Get All Orders FAQ says "All easyecom fields are tax inclusive in
general" and "Is the selling price excluding tax? It's inclusive"; the
samples agree (selling_price 1304.73 with tax 199.03 at 18% is
1304.73 * 18/118). The field sheet says selling_price excludes tax; we follow
the FAQ and the arithmetic. So ex-GST line value = selling_price - tax, where
selling_price is the line total after discounts ("the final price at which
the product is sold"). total_discount is an order-level, tax-inclusive
amount; it is taken ex-GST at the order's own ex-GST/inclusive ratio.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx
from .http import http_client

from .base import AuthType, BaseConnector, ConnectorConfig, ProviderCategory, SyncResult
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.easyecom.io"
IST = timezone(timedelta(hours=5, minutes=30))
PAGE_LIMIT = 250  # documented max
CHUNK_DAYS = 7  # documented max range per getAllOrders call
MAX_PAGES = 400  # per endpoint, across all chunks: 100k rows; truncation is reported
RETURNS_LOOKAHEAD_DAYS = 45  # credit notes for a month's orders arrive after it ends

# order_status_id
NOT_SHIPPED_IDS = {1, 2, 3, 4, 5, 6, 11}
SHIPPED_ID = 7
CANCELLED_ID = 9
RETURNED_ID = 10
# shipping_status_id
DELIVERED_SHIP_IDS = {3}
LOST_SHIP_IDS = {22}
RTO_SHIP_IDS = {9, 17, 24, 25}
REVERSE_SHIP_IDS = {7, 26}

SHIPPED_KINDS = ("delivered", "returned", "rto", "in_transit", "lost", "returned_unclassified")


def last_complete_month(today: date) -> Tuple[date, date]:
    last_prev = today.replace(day=1) - timedelta(days=1)
    return last_prev.replace(day=1), last_prev


def ist_today(now_utc: Optional[datetime] = None) -> date:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(IST).date()


def date_chunks(start: date, end: date, days: int = CHUNK_DAYS) -> List[Tuple[str, str]]:
    """Inclusive [start, end] as (start_date, end_date) strings, each under `days` long."""
    out: List[Tuple[str, str]] = []
    cur = start
    while cur <= end:
        last = min(cur + timedelta(days=days - 1), end)
        out.append((f"{cur.isoformat()} 00:00:00", f"{last.isoformat()} 23:59:59"))
        cur = last + timedelta(days=1)
    return out


def _money(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").split())


def is_cod(order: Dict[str, Any]) -> bool:
    mode = _text(order.get("payment_mode"))
    if mode:
        return mode == "cod" or "cash on delivery" in mode
    return _int(order.get("payment_mode_id")) == 2  # COD in the docs' samples


def line_values(order: Dict[str, Any]) -> Dict[str, float]:
    """Ex-GST value of a shipment's items, after discounts, net of cancelled qty."""
    net_incl = net_ex = returned_ex = 0.0
    for sub in order.get("suborders") or []:
        qty = _money(sub.get("suborder_quantity")) or 0.0
        cancelled = _money(sub.get("cancelled_quantity"))
        kept = (qty - cancelled) / qty if qty > 0 else 1.0
        kept = max(0.0, min(1.0, kept))
        incl = _money(sub.get("selling_price")) * kept
        ex = (_money(sub.get("selling_price")) - _money(sub.get("tax"))) * kept
        net_incl += incl
        net_ex += ex
        returned = _money(sub.get("returned_quantity"))
        if qty > 0 and returned > 0:
            returned_ex += (_money(sub.get("selling_price")) - _money(sub.get("tax"))) * min(1.0, returned / qty)
    ratio = net_ex / net_incl if net_incl > 0 else 1.0
    discount_ex = _money(order.get("total_discount")) * ratio
    return {"net_ex": net_ex, "discount_ex": discount_ex, "returned_ex": returned_ex}


def classify_return(order: Dict[str, Any], credit_note: Optional[Dict[str, Any]]) -> str:
    """'rto', 'returned' (customer return) or 'returned_unclassified'."""
    ship_id = _int(order.get("shipping_status_id"))
    ship_text = _text(order.get("shipping_status"))
    if ship_id in RTO_SHIP_IDS or ship_text.startswith("rto"):
        return "rto"
    if ship_id in REVERSE_SHIP_IDS or ship_text.startswith("reverse"):
        return "returned"
    if credit_note:
        rtype = _text(credit_note.get("return_type"))
        if "rto" in rtype.split() or "return to origin" in rtype or "courier return" in rtype:
            return "rto"
        if "customer" in rtype:
            return "returned"
        fwd = str(order.get("awb_number") or "").strip()
        rev = str(credit_note.get("return_awb_number") or "").strip()
        if fwd and rev:
            return "rto" if fwd == rev else "returned"
    if ship_id in DELIVERED_SHIP_IDS or order.get("delivery_date"):
        return "returned"  # it reached the customer, then came back
    return "returned_unclassified"


def classify(order: Dict[str, Any], credit_note: Optional[Dict[str, Any]] = None) -> str:
    status_id = _int(order.get("order_status_id"))
    status = _text(order.get("order_status"))
    ship_id = _int(order.get("shipping_status_id"))
    ship_text = _text(order.get("shipping_status"))

    if status_id == CANCELLED_ID or status.startswith("cancel"):
        return "cancelled"
    if status_id == RETURNED_ID or status.startswith("return"):
        return classify_return(order, credit_note)
    if status_id == SHIPPED_ID or status in ("shipped", "delivered"):
        if ship_id in RTO_SHIP_IDS or ship_text.startswith("rto"):
            return "rto"
        if ship_id in REVERSE_SHIP_IDS or ship_text.startswith("reverse"):
            return "returned"
        if ship_id in LOST_SHIP_IDS or "lost" in ship_text:
            return "lost"
        if ship_id in DELIVERED_SHIP_IDS or ship_text == "delivered":
            return "delivered"
        return "in_transit"
    if status_id in NOT_SHIPPED_IDS or status in ("open", "pending", "assigned", "confirmed", "printed",
                                                  "ready to dispatch", "out of stock", "upcoming", "hold", "on hold"):
        return "not_shipped"
    return "other"


def _order_kind(kinds: List[str]) -> str:
    """One order can be split into several shipments (invoices). Pick the order's outcome."""
    shipped = [k for k in kinds if k in SHIPPED_KINDS]
    if not shipped:
        for k in ("not_shipped", "other", "cancelled"):
            if k in kinds:
                return k
        return "other"
    for k in ("returned_unclassified", "returned", "delivered", "rto", "in_transit", "lost"):
        if k in shipped:
            if k == "rto" and any(x in shipped for x in ("delivered", "returned")):
                continue
            return k
    return shipped[0]


def _include(order: Dict[str, Any]) -> Tuple[bool, str]:
    """D2C retail orders only: no stock transfers, B2B or zero-value replacements."""
    key = _text(order.get("order_type_key"))
    otype = _text(order.get("order_type"))
    if key and key != "retailorder":
        return False, "non_retail"
    if not key and otype and otype != "b2c":
        return False, "non_retail"
    if _int(order.get("replacement_order")) == 1:
        return False, "replacement"
    return True, ""


def _credit_note_value(cn: Dict[str, Any]) -> float:
    total = 0.0
    for item in cn.get("items") or []:
        if item.get("credit_note_total_item_excluding_tax") is not None:
            total += _money(item.get("credit_note_total_item_excluding_tax"))
        else:
            total += _money(item.get("total_item_selling_price")) - _money(item.get("credit_note_total_item_tax"))
    return total


def _empty_bucket() -> Dict[str, Any]:
    return {"orders_shipped": 0, "delivered": 0, "rto_orders": 0, "customer_returns_orders": 0,
            "in_transit": 0, "lost": 0, "returned_unclassified": 0, "cod_delivered": 0,
            "gross_sales": 0.0, "discounts": 0.0, "net_sales": 0.0, "customer_returns_value": 0.0}


def summarize_orders(orders: Iterable[Dict[str, Any]], credit_notes: Iterable[Dict[str, Any]] = ()) -> Dict[str, Any]:
    """Pure: month orders (+ credit notes) -> D2C counts and ex-GST values, total and per channel."""
    notes_by_invoice: Dict[Any, Dict[str, Any]] = {}
    for cn in credit_notes:
        inv = cn.get("invoice_id")
        if inv is not None and inv not in notes_by_invoice:
            notes_by_invoice[inv] = cn

    excluded = {"non_retail": 0, "replacement": 0}
    seen_invoices = set()
    groups: Dict[Any, List[Dict[str, Any]]] = {}
    for order in orders:
        inv = order.get("invoice_id")
        if inv is not None:
            if inv in seen_invoices:
                continue  # chunk boundaries can repeat a row
            seen_invoices.add(inv)
        ok, why = _include(order)
        if not ok:
            excluded[why] += 1
            continue
        key = order.get("order_id") or ("inv", inv)
        groups.setdefault(key, []).append(order)

    counts = {k: 0 for k in ("delivered", "returned", "rto", "in_transit", "lost", "returned_unclassified",
                             "cancelled", "not_shipped", "other")}
    other_statuses = set()
    total = _empty_bucket()
    channels: Dict[str, Dict[str, Any]] = {}
    notes_used = 0

    for shipments in groups.values():
        kinds = []
        for s in shipments:
            cn = notes_by_invoice.get(s.get("invoice_id"))
            k = classify(s, cn)
            if k == "delivered" and any(_money(x.get("returned_quantity")) > 0 for x in s.get("suborders") or []):
                k = "returned"  # partial customer return on a delivered shipment
            kinds.append(k)
            if k == "other":
                other_statuses.add(f"{s.get('order_status')}/{s.get('order_status_id')}")
        kind = _order_kind(kinds)
        counts[kind] += 1
        if kind not in SHIPPED_KINDS:
            continue

        first = shipments[0]
        channel = str(first.get("marketplace") or "Unknown")
        bucket = channels.setdefault(channel, _empty_bucket())
        shipped_parts = [(s, k) for s, k in zip(shipments, kinds) if k in SHIPPED_KINDS]
        net = disc = ret_value = 0.0
        for s, k in shipped_parts:
            v = line_values(s)
            net += v["net_ex"]
            disc += v["discount_ex"]
            if k == "returned":
                cn = notes_by_invoice.get(s.get("invoice_id"))
                if cn and cn.get("items"):
                    ret_value += _credit_note_value(cn)
                    notes_used += 1
                elif v["returned_ex"] > 0:
                    ret_value += v["returned_ex"]
                else:
                    ret_value += v["net_ex"]  # whole shipment came back
        cod = is_cod(first)
        for b in (total, bucket):
            b["orders_shipped"] += 1
            b["gross_sales"] += net + disc
            b["discounts"] += disc
            b["net_sales"] += net
            if kind == "delivered":
                b["delivered"] += 1
            elif kind == "returned":
                b["customer_returns_orders"] += 1
                b["customer_returns_value"] += ret_value
            elif kind == "rto":
                b["rto_orders"] += 1
            elif kind == "in_transit":
                b["in_transit"] += 1
            elif kind == "lost":
                b["lost"] += 1
            else:
                b["returned_unclassified"] += 1
            if kind in ("delivered", "returned") and cod:
                b["cod_delivered"] += 1

    def finish(b: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(b)
        for k in ("gross_sales", "discounts", "net_sales", "customer_returns_value"):
            out[k] = round(out[k], 2)
        reached = b["delivered"] + b["customer_returns_orders"]
        # COD share of delivered orders (delivered includes later customer
        # returns); in-transit and RTO are excluded. None when nothing delivered.
        out["cod_share"] = round(b["cod_delivered"] / reached, 4) if reached else None
        resolved = b["rto_orders"] + reached
        out["rto_rate_resolved"] = round(b["rto_orders"] / resolved, 4) if resolved else None
        return out

    summary = finish(total)
    summary.update({
        "cancelled": counts["cancelled"],
        "not_shipped": counts["not_shipped"],
        "other": counts["other"],
        "other_statuses": sorted(other_statuses),
        "excluded_non_retail": excluded["non_retail"],
        "excluded_replacements": excluded["replacement"],
        "credit_notes_matched": notes_used,
        "channels": {name: finish(b) for name, b in sorted(channels.items())},
    })
    return summary


def month_values(summary: Dict[str, Any]) -> Dict[str, Any]:
    """The fields of a d2c_months row this connector owns."""
    unclassified = summary["returned_unclassified"] > 0
    shipped = summary["orders_shipped"]
    return {
        "orders_shipped": shipped,
        "gross_sales": summary["gross_sales"] if shipped else None,
        "discounts": summary["discounts"] if shipped else None,
        # A returned order we couldn't call RTO or customer return makes both
        # counts guesses, so they are left unknown rather than understated.
        "rto_orders": None if unclassified else summary["rto_orders"],
        "customer_returns_orders": None if unclassified else summary["customer_returns_orders"],
        "customer_returns_value": None if unclassified else summary["customer_returns_value"],
        "cod_share": summary["cod_share"],
    }


@ConnectorRegistry.register
class EasyEcomConnector(BaseConnector):
    PROVIDER_ID = "easyecom"
    PROVIDER_NAME = "EasyEcom"
    PROVIDER_DESCRIPTION = (
        "Order management for Indian D2C across website and marketplaces. Imports shipped orders, "
        "sales, discounts, RTO, customer returns and COD share, by channel."
    )
    PROVIDER_CATEGORY = ProviderCategory.ERP
    AUTH_TYPE = AuthType.CUSTOM
    DOCS_URL = "https://api-docs.easyecom.io"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        creds = config.credentials or {}
        self._email = str(creds.get("email") or "").strip()
        self._password = str(creds.get("password") or "").strip()
        self._api_key = str(creds.get("api_key") or creds.get("x_api_key") or "").strip()
        self._location_key = str(creds.get("location_key") or "").strip()
        self._token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = http_client(base_url=BASE_URL, timeout=60.0)
        return self._client

    def _headers(self) -> Dict[str, str]:
        h = {"x-api-key": self._api_key, "Accept": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def authenticate(self) -> bool:
        if not (self._email and self._password and self._api_key and self._location_key):
            logger.warning("EasyEcom email, password, API key or location key not provided")
            return False
        try:
            client = await self._get_client()
            res = await client.post(
                "/access/token",
                json={"email": self._email, "password": self._password, "location_key": self._location_key},
                headers={"x-api-key": self._api_key},
            )
            if res.status_code != 200:
                logger.warning(f"EasyEcom auth failed: {res.status_code}")
                return False
            data = (res.json() or {}).get("data") or {}
            token = data.get("token") if isinstance(data, dict) else None
            jwt = token.get("jwt_token") if isinstance(token, dict) else None
            self._token = jwt or None
            self._authenticated = bool(self._token)
            return self._authenticated
        except Exception as e:
            logger.error(f"EasyEcom authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def _paged(self, path: str, windows: List[Dict[str, Any]], key: str) -> Tuple[List[Dict[str, Any]], bool]:
        """Fetch every window, following data.nextUrl; stop at MAX_PAGES total."""
        client = await self._get_client()
        rows: List[Dict[str, Any]] = []
        pages = 0
        for window in windows:
            url: Optional[str] = path
            params: Optional[Dict[str, Any]] = {**window, "limit": PAGE_LIMIT}
            while url:
                if pages >= MAX_PAGES:
                    return rows, True
                res = await client.get(url, params=params, headers=self._headers())
                pages += 1
                try:
                    body = res.json() or {}
                except ValueError:
                    body = {}
                if "no data found" in _text(body.get("message")):
                    break  # empty window; EasyEcom may send this as HTTP 400
                if res.status_code != 200:
                    raise RuntimeError(f"EasyEcom {path} returned {res.status_code}: {body.get('message')}")
                data = body.get("data") or {}
                if not isinstance(data, dict):
                    break
                rows.extend(data.get(key) or [])
                url = data.get("nextUrl") or None
                params = None  # nextUrl is used as-is, without filters
        return rows, False

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                    errors=["Authentication failed - check the EasyEcom email, password, API key and location key"],
                    sync_started=sync_started,
                )
            today = ist_today(sync_started.replace(tzinfo=timezone.utc))
            period_start, period_end = last_complete_month(today)

            order_windows = [{"start_date": s, "end_date": e}
                             for s, e in date_chunks(period_start, period_end)]
            orders, orders_truncated = await self._paged("/orders/V2/getAllOrders", order_windows, "orders")

            # Credit notes raised from the month start until today (capped),
            # to tell RTO from customer returns and value the returns.
            cn_end = min(today - timedelta(days=1), period_end + timedelta(days=RETURNS_LOOKAHEAD_DAYS))
            cn_windows = [{"credit_note_start_date": s, "credit_note_end_date": e}
                          for s, e in date_chunks(period_start, cn_end)]
            errors: List[str] = []
            warnings: List[str] = []
            try:
                notes, notes_truncated = await self._paged("/orders/getAllReturns", cn_windows, "credit_notes")
            except RuntimeError as e:
                # Returns are location-scoped and optional; orders alone still
                # give shipped/RTO-by-tracking/COD. Say so instead of failing.
                notes, notes_truncated = [], False
                warnings.append(f"Returns could not be read ({e}); RTO vs customer return relies on tracking status")

            summary = summarize_orders(orders, notes)
            if orders_truncated or notes_truncated:
                errors.append("Row limit reached; the month is incomplete")
            if summary["returned_unclassified"]:
                warnings.append(
                    f"{summary['returned_unclassified']} returned orders could not be told apart as RTO or customer "
                    "return; those figures are left blank"
                )

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(orders),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                errors=errors,
                warnings=warnings,
                metadata={
                    "d2c_month": {"period": period_start.isoformat(), "values": month_values(summary)},
                    "easyecom": summary,
                    "d2c_channels": summary["channels"],
                },
            )
        except Exception as e:
            logger.error(f"EasyEcom sync failed: {e}")
            return SyncResult(
                success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                errors=[str(e)], sync_started=sync_started, sync_completed=datetime.utcnow(),
            )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
