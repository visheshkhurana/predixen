"""
Shiprocket connector - shipping outcomes and freight for Indian D2C brands.

Shopify knows what was ordered; the shipping partner knows what happened to
it. This connector supplies the inputs only a logistics aggregator has:
orders actually shipped, RTO (shipped, came back undelivered), customer
returns, the COD share of shipped orders, and freight per order from the
wallet statement.

API: https://apidocs.shiprocket.in (v1 external). Auth is an API user's
email/password exchanged for a bearer token (POST /auth/login).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import httpx

from .base import AuthType, BaseConnector, ConnectorConfig, ProviderCategory, SyncResult
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

BASE_URL = "https://apiv2.shiprocket.in/v1/external"
PER_PAGE = 100
MAX_PAGES = 500  # 50k rows; a truncated month is reported, never hidden

# Order statuses from the Shiprocket docs, normalised to upper case with
# underscores as spaces. Anything else is counted as "other" and reported.
NOT_SHIPPED = {
    "NEW", "INVOICED", "READY TO SHIP", "PICKUP SCHEDULED", "PICKUP QUEUE", "PICKUP QUEUED",
    "PICKUP RESCHEDULED", "PICKUP ERROR", "PICKUP EXCEPTION", "OUT FOR PICKUP", "AWB ASSIGNED",
    "LABEL GENERATED", "MANIFEST GENERATED", "PICKUP SCHEDULED/GENERATED", "PICKUP BOOKED",
    "UNMAPPED", "UNFULFILLABLE", "EPAYMENT FAILED", "PENDING",
}
IN_TRANSIT = {
    "SHIPPED", "IN TRANSIT", "OUT FOR DELIVERY", "UNDELIVERED", "PICKED UP", "DELAYED",
    "REACHED AT DESTINATION", "REACHED AT DESTINATION HUB", "MISROUTED", "REACHED WAREHOUSE",
}
DELIVERED = {"DELIVERED", "PARTIAL DELIVERED", "FULFILLED"}
LOST = {"LOST", "DAMAGED", "DESTROYED", "DISPOSED OFF"}


def last_complete_month(today: date) -> Tuple[date, date]:
    last_prev = today.replace(day=1) - timedelta(days=1)
    return last_prev.replace(day=1), last_prev


def _status(order: Dict[str, Any]) -> str:
    return " ".join(str(order.get("status") or "").upper().replace("_", " ").split())


def classify(order: Dict[str, Any]) -> str:
    s = _status(order)
    if s.startswith("CANCEL"):
        return "cancelled"
    if s.startswith("RTO"):
        return "rto"
    if s.startswith("RETURN"):
        return "returned"  # delivered, then sent back by the customer
    if s in DELIVERED:
        return "delivered"
    if s in IN_TRANSIT:
        return "in_transit"
    if s in LOST:
        return "lost"
    if s in NOT_SHIPPED:
        return "not_shipped"
    return "other"


def _awbs(order: Dict[str, Any]) -> Set[str]:
    out: Set[str] = set()
    for shipment in order.get("shipments", []) or []:
        for key in ("awb", "return_awb"):
            code = str(shipment.get(key) or "").strip()
            if code:
                out.add(code)
    return out


def _money(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def summarize_shipments(orders: Iterable[Dict[str, Any]], statement: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {k: 0 for k in ("delivered", "returned", "rto", "in_transit", "lost", "cancelled", "not_shipped", "other")}
    shipped_cod = 0
    month_awbs: Set[str] = set()
    other_statuses: Set[str] = set()

    for order in orders:
        kind = classify(order)
        counts[kind] += 1
        if kind == "other":
            other_statuses.add(_status(order))
        if kind in ("delivered", "returned", "rto", "in_transit", "lost"):
            month_awbs |= _awbs(order)
            if str(order.get("payment_method") or "").lower() == "cod":
                shipped_cod += 1

    shipped = counts["delivered"] + counts["returned"] + counts["rto"] + counts["in_transit"] + counts["lost"]

    # Freight: wallet debits against this month's AWBs. Shiprocket bills RTO
    # legs separately; a debit that mentions RTO is the return leg.
    forward_freight = rto_freight = 0.0
    matched = 0
    for row in statement:
        awb = str(row.get("awb_code") or "").strip()
        debit = _money(row.get("debit_amount"))
        if not awb or awb not in month_awbs or debit <= 0:
            continue
        matched += 1
        label = " ".join(str(row.get(k) or "") for k in ("description", "action", "charge")).lower()
        if "rto" in label:
            rto_freight += debit
        else:
            forward_freight += debit

    return {
        "orders_shipped": shipped,
        "delivered": counts["delivered"],
        "rto_orders": counts["rto"],
        "customer_returns_orders": counts["returned"],
        "in_transit": counts["in_transit"],
        "lost": counts["lost"],
        "cancelled": counts["cancelled"],
        "not_shipped": counts["not_shipped"],
        "other": counts["other"],
        "other_statuses": sorted(other_statuses),
        "cod_share": round(shipped_cod / shipped, 4) if shipped else None,
        # RTO rate among orders whose outcome is known; in-transit ones may still RTO.
        "rto_rate_resolved": (
            round(counts["rto"] / (counts["rto"] + counts["delivered"] + counts["returned"]), 4)
            if counts["rto"] + counts["delivered"] + counts["returned"] else None
        ),
        "freight_rows_matched": matched,
        "forward_freight": round(forward_freight, 2),
        "rto_freight": round(rto_freight, 2),
        # None, not 0, when nothing was billed yet: the engine then says
        # "add shipping cost" instead of showing free shipping.
        "forward_shipping_per_order": round(forward_freight / shipped, 2) if shipped and forward_freight > 0 else None,
        "rto_shipping_per_order": round(rto_freight / counts["rto"], 2) if counts["rto"] and rto_freight > 0 else None,
    }


def month_values(summary: Dict[str, Any]) -> Dict[str, Any]:
    """The fields of a d2c_months row this connector owns."""
    return {
        "orders_shipped": summary["orders_shipped"],
        "rto_orders": summary["rto_orders"],
        "customer_returns_orders": summary["customer_returns_orders"],
        "cod_share": summary["cod_share"],
        "forward_shipping_per_order": summary["forward_shipping_per_order"],
        "rto_shipping_per_order": summary["rto_shipping_per_order"],
    }


@ConnectorRegistry.register
class ShiprocketConnector(BaseConnector):
    PROVIDER_ID = "shiprocket"
    PROVIDER_NAME = "Shiprocket"
    PROVIDER_DESCRIPTION = "Shipping aggregator for Indian D2C. Imports shipped orders, RTO, returns, COD share and freight."
    PROVIDER_CATEGORY = ProviderCategory.ERP
    AUTH_TYPE = AuthType.BASIC
    DOCS_URL = "https://apidocs.shiprocket.in"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._email = (config.credentials.get("email") or "").strip()
        self._password = config.credentials.get("password") or ""
        self._token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        return self._client

    async def authenticate(self) -> bool:
        if not self._email or not self._password:
            logger.warning("Shiprocket email or password not provided")
            return False
        try:
            client = await self._get_client()
            res = await client.post("/auth/login", json={"email": self._email, "password": self._password})
            if res.status_code != 200:
                logger.warning(f"Shiprocket auth failed: {res.status_code}")
                return False
            self._token = res.json().get("token")
            self._authenticated = bool(self._token)
            return self._authenticated
        except Exception as e:
            logger.error(f"Shiprocket authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def _paged(self, path: str, params: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool]:
        client = await self._get_client()
        headers = {"Authorization": f"Bearer {self._token}"}
        rows: List[Dict[str, Any]] = []
        page = 1
        while page <= MAX_PAGES:
            res = await client.get(path, params={**params, "page": page, "per_page": PER_PAGE}, headers=headers)
            if res.status_code != 200:
                raise RuntimeError(f"Shiprocket {path} returned {res.status_code}")
            body = res.json()
            rows.extend(body.get("data") or [])
            total_pages = (((body.get("meta") or {}).get("pagination") or {}).get("total_pages")) or 1
            if page >= total_pages:
                return rows, False
            page += 1
        return rows, True

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                    errors=["Authentication failed - check the Shiprocket API user email and password"],
                    sync_started=sync_started,
                )
            period_start, period_end = last_complete_month(sync_started.date())
            window = {"from": period_start.isoformat(), "to": period_end.isoformat()}
            orders, orders_truncated = await self._paged("/orders", window)
            statement, statement_truncated = await self._paged("/account/details/statement", window)
            summary = summarize_shipments(orders, statement)
            truncated = orders_truncated or statement_truncated

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(orders),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                errors=["Row limit reached; the month is incomplete"] if truncated else [],
                metadata={
                    "d2c_month": {"period": period_start.isoformat(), "values": month_values(summary)},
                    "shiprocket": summary,
                },
            )
        except Exception as e:
            logger.error(f"Shiprocket sync failed: {e}")
            return SyncResult(
                success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                errors=[str(e)], sync_started=sync_started, sync_completed=datetime.utcnow(),
            )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
