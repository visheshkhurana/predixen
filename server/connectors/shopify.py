"""
Shopify E-commerce Connector - Online store and revenue data.

Provides:
- Order data (as invoices)
- Product catalog
- Customer records
- Revenue and sales analytics

API Documentation: https://shopify.dev/docs/api/admin-rest
"""

import httpx
import logging
import os
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime, timedelta

from .base import (
    BaseConnector,
    ConnectorConfig,
    AuthType,
    ProviderCategory,
    LedgerEntry,
    InvoiceRecord,
    EmployeeRecord,
    PayrollRunRecord,
    SyncResult,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

# Shopify retires each API version after about a year and then serves the
# oldest supported one instead, so a stale pin silently changes behaviour.
# 2026-10 is the latest stable as of Nov 2026; override with SHOPIFY_API_VERSION.
DEFAULT_API_VERSION = "2026-10"

# Upper bound on orders read for one month, so a runaway pagination loop
# cannot hang a sync. A truncated month is reported, never presented as whole.
MAX_ORDERS_PER_SYNC = 50_000

COD_KEYWORDS = ("cod", "cash on delivery", "cash_on_delivery", "pay on delivery")


def _money(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def is_cod_order(order: Dict[str, Any]) -> bool:
    gateway = (order.get("gateway", "") or "").lower()
    names = [str(p).lower() for p in order.get("payment_gateway_names", []) or []]
    payment_str = " ".join([gateway] + names)
    return any(kw in payment_str for kw in COD_KEYWORDS)


def last_complete_month(today: date) -> Tuple[date, date]:
    first_this_month = today.replace(day=1)
    last_prev = first_this_month - timedelta(days=1)
    return last_prev.replace(day=1), last_prev


def summarize_orders(orders: List[Dict[str, Any]]) -> Dict[str, Any]:
    """One period of Shopify orders as D2C sales figures, ex-GST.

    - Test orders are ignored. Cancelled orders are counted but earn nothing.
    - COD orders count as sales. Shopify keeps them financial_status=pending
      until the courier remits, and in India they are often most of the
      orders; the old connector summed "paid" orders only and dropped them.
    - Indian stores usually show tax-inclusive prices (taxes_included=true),
      so GST is removed from subtotal_price to get net sales.
    - Refunds come from the refund transactions actually issued.
    - RTO is not visible in Shopify; it comes from the shipping partner.
    """
    gross_sales = discounts = net_sales_ex_gst = refunds = tax = 0.0
    orders_count = cancelled = cod_orders = 0
    customers = set()

    for order in orders:
        if order.get("test"):
            continue
        if order.get("cancelled_at"):
            cancelled += 1
            continue
        orders_count += 1
        gross_sales += _money(order.get("total_line_items_price"))
        discounts += _money(order.get("total_discounts"))
        order_tax = _money(order.get("total_tax"))
        tax += order_tax
        subtotal = _money(order.get("subtotal_price"))
        net_sales_ex_gst += subtotal - order_tax if order.get("taxes_included") else subtotal
        for refund in order.get("refunds", []) or []:
            for txn in refund.get("transactions", []) or []:
                if txn.get("kind") == "refund" and txn.get("status") == "success":
                    refunds += _money(txn.get("amount"))
        if is_cod_order(order):
            cod_orders += 1
        customer = order.get("customer") or {}
        if customer.get("id"):
            customers.add(customer["id"])

    revenue = net_sales_ex_gst - refunds
    return {
        "orders": orders_count,
        "cancelled_orders": cancelled,
        "gross_sales": round(gross_sales, 2),
        "discounts": round(discounts, 2),
        "gst_collected": round(tax, 2),
        "net_sales_ex_gst": round(net_sales_ex_gst, 2),
        "refunds": round(refunds, 2),
        "revenue": round(revenue, 2),
        "cod_orders": cod_orders,
        "cod_share": round(cod_orders / orders_count, 4) if orders_count else None,
        "aov": round(net_sales_ex_gst / orders_count, 2) if orders_count else None,
        "customers": len(customers),
    }


@ConnectorRegistry.register
class ShopifyConnector(BaseConnector):
    PROVIDER_ID = "shopify"
    PROVIDER_NAME = "Shopify"
    PROVIDER_DESCRIPTION = "E-commerce platform. Import orders, products, and customers for revenue tracking and sales analytics."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://shopify.dev/docs/api/admin-rest"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._shop_domain = config.credentials.get("shop_domain", "")
        self._access_token = config.credentials.get("access_token", "")
        self._client: Optional[httpx.AsyncClient] = None

    def _get_base_url(self) -> str:
        domain = self._shop_domain.replace(".myshopify.com", "").strip()
        version = (os.getenv("SHOPIFY_API_VERSION") or DEFAULT_API_VERSION).strip()
        return f"https://{domain}.myshopify.com/admin/api/{version}"

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._get_base_url(),
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "X-Shopify-Access-Token": self._access_token,
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._shop_domain or not self._access_token:
            logger.warning("Shopify shop_domain or access_token not provided")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/products.json", params={"limit": 1})

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Shopify authentication successful")
                return True
            else:
                logger.warning(f"Shopify auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Shopify authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/products.json", params={"limit": 1})
            return response.status_code == 200
        except Exception:
            return False

    async def get_orders(
        self,
        start_date: Optional[datetime] = None,
        limit: int = 250,
        status: str = "any",
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_orders = []
            page_info = None

            while True:
                params: Dict[str, Any] = {
                    "limit": min(limit, 250),
                    "status": status,
                }
                if start_date:
                    params["created_at_min"] = start_date.strftime("%Y-%m-%dT00:00:00Z")
                if end_date:
                    params["created_at_max"] = end_date.strftime("%Y-%m-%dT23:59:59Z")
                if page_info:
                    params = {"limit": min(limit, 250), "page_info": page_info}

                response = await client.get("/orders.json", params=params)

                if response.status_code != 200:
                    logger.error(f"Shopify orders error: {response.status_code}")
                    break

                data = response.json()
                orders = data.get("orders", [])
                all_orders.extend(orders)

                link_header = response.headers.get("link", "")
                if 'rel="next"' in link_header:
                    for part in link_header.split(","):
                        if 'rel="next"' in part:
                            url_part = part.split(";")[0].strip().strip("<>")
                            if "page_info=" in url_part:
                                page_info = url_part.split("page_info=")[-1]
                                break
                    else:
                        break
                else:
                    break

                if len(all_orders) >= limit:
                    break

            return all_orders

        except Exception as e:
            logger.error(f"Shopify orders fetch error: {e}")
            return []

    async def get_products(self, limit: int = 250) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"limit": min(limit, 250)}
            response = await client.get("/products.json", params=params)

            if response.status_code == 200:
                return response.json().get("products", [])
            return []
        except Exception as e:
            logger.error(f"Shopify products fetch error: {e}")
            return []

    async def get_customers(self, limit: int = 250) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"limit": min(limit, 250)}
            response = await client.get("/customers.json", params=params)

            if response.status_code == 200:
                return response.json().get("customers", [])
            return []
        except Exception as e:
            logger.error(f"Shopify customers fetch error: {e}")
            return []

    def _detect_payment_type(self, order: Dict[str, Any]) -> str:
        return "cod" if is_cod_order(order) else "prepaid"

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        orders = await self.get_orders(start_date=start_date, limit=500)
        entries = []

        for order in orders:
            total_price = float(order.get("total_price", 0))
            order_date_str = order.get("created_at", "")
            try:
                order_date = datetime.fromisoformat(order_date_str.replace("Z", "+00:00")) if order_date_str else datetime.now()
            except (ValueError, TypeError):
                order_date = datetime.now()

            if end_date and order_date > end_date:
                continue

            payment_type = self._detect_payment_type(order)
            shipping_lines = order.get("shipping_lines", [])
            shipping_total = sum(float(s.get("price", 0)) for s in shipping_lines)

            entries.append(
                LedgerEntry(
                    external_id=str(order.get("id", "")),
                    date=order_date,
                    account_code="shopify_revenue",
                    account_name="Shopify Revenue",
                    debit=0.0,
                    credit=total_price,
                    description=f"Order #{order.get('order_number', '')} - {order.get('email', '')}",
                    category="Sales Revenue",
                    metadata={
                        "order_number": order.get("order_number"),
                        "financial_status": order.get("financial_status"),
                        "fulfillment_status": order.get("fulfillment_status"),
                        "currency": order.get("currency", "USD"),
                        "payment_type": payment_type,
                        "shipping_total": shipping_total,
                        "discount_codes": order.get("discount_codes", []),
                    },
                )
            )

        return entries

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        orders = await self.get_orders(start_date=start_date, limit=500)
        invoices = []

        for order in orders:
            total_price = float(order.get("total_price", 0))
            subtotal = float(order.get("subtotal_price", 0))
            total_tax = float(order.get("total_tax", 0))
            order_date_str = order.get("created_at", "")

            try:
                order_date = datetime.fromisoformat(order_date_str.replace("Z", "+00:00")) if order_date_str else datetime.now()
            except (ValueError, TypeError):
                order_date = datetime.now()

            if end_date and order_date > end_date:
                continue

            customer = order.get("customer", {})
            customer_name = ""
            if customer:
                customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
            if not customer_name:
                customer_name = order.get("email", "Guest")

            financial_status = order.get("financial_status", "pending")
            status_map = {
                "paid": "paid",
                "partially_paid": "partial",
                "refunded": "refunded",
                "partially_refunded": "partial_refund",
                "pending": "pending",
                "authorized": "pending",
                "voided": "cancelled",
            }

            line_items = []
            for item in order.get("line_items", []):
                line_items.append({
                    "name": item.get("name", ""),
                    "quantity": item.get("quantity", 0),
                    "price": float(item.get("price", 0)),
                    "sku": item.get("sku", ""),
                })

            payment_type = self._detect_payment_type(order)
            shipping_lines = order.get("shipping_lines", [])
            shipping_total = sum(float(s.get("price", 0)) for s in shipping_lines)

            invoices.append(
                InvoiceRecord(
                    external_id=str(order.get("id", "")),
                    date=order_date,
                    customer_name=customer_name,
                    amount=subtotal,
                    tax=total_tax,
                    total=total_price,
                    currency=order.get("currency", "USD"),
                    status=status_map.get(financial_status, "pending"),
                    line_items=line_items,
                    metadata={
                        "order_number": order.get("order_number"),
                        "financial_status": financial_status,
                        "fulfillment_status": order.get("fulfillment_status"),
                        "payment_type": payment_type,
                        "shipping_total": shipping_total,
                        "source": "shopify_order",
                    },
                )
            )

        return invoices

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        result = {
            "source_type": "connector_shopify",
            "extraction_summary": f"Synced from Shopify ({self._shop_domain})",
        }

        if invoices:
            paid_invoices = [inv for inv in invoices if inv.status == "paid"]
            result["revenue"] = sum(inv.total for inv in paid_invoices)
            result["total_orders"] = len(invoices)
            result["paid_orders"] = len(paid_invoices)
            result["total_tax_collected"] = sum(inv.tax for inv in invoices)

            cod_orders = [inv for inv in invoices if inv.metadata.get("payment_type") == "cod"]
            prepaid_orders = [inv for inv in invoices if inv.metadata.get("payment_type") == "prepaid"]
            result["cod_orders"] = len(cod_orders)
            result["prepaid_orders"] = len(prepaid_orders)
            result["cod_revenue"] = sum(inv.total for inv in cod_orders)
            result["prepaid_revenue"] = sum(inv.total for inv in prepaid_orders)
            result["cod_percentage"] = round(len(cod_orders) / len(invoices) * 100, 1) if invoices else 0

            shipping_total = sum(float(inv.metadata.get("shipping_total", 0)) for inv in invoices)
            result["total_shipping"] = shipping_total

            refunded = [inv for inv in invoices if inv.status == "refunded"]
            result["refunded_orders"] = len(refunded)
            result["refund_amount"] = sum(inv.total for inv in refunded)
            result["return_rate"] = round(len(refunded) / len(invoices) * 100, 1) if invoices else 0

            if paid_invoices:
                result["aov"] = round(sum(inv.total for inv in paid_invoices) / len(paid_invoices), 2)

        if ledger_entries:
            result["total_revenue"] = sum(e.credit for e in ledger_entries)
            result["transactions_count"] = len(ledger_entries)

        return result

    async def sync_all(self) -> SyncResult:
        """Sync the last complete calendar month, every order in it.

        One record per sync, dated to that month (see _declared_period in
        server/api/connectors.py). The previous sync read the newest 500
        orders of all time, three times over, and dated them to today.
        """
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check shop_domain and access_token"],
                    sync_started=sync_started,
                )

            period_start, period_end = last_complete_month(sync_started.date())
            orders = await self.get_orders(
                start_date=datetime.combine(period_start, datetime.min.time()),
                end_date=datetime.combine(period_end, datetime.min.time()),
                limit=MAX_ORDERS_PER_SYNC,
            )
            truncated = len(orders) >= MAX_ORDERS_PER_SYNC
            summary = summarize_orders(orders)
            products = await self.get_products()

            financials: Dict[str, Any] = {
                "source_type": "connector_shopify",
                "extraction_summary": (
                    f"Synced from Shopify ({self._shop_domain}) for "
                    f"{period_start:%b %Y}: {summary['orders']} orders, net of GST and refunds"
                    + (" (TRUNCATED: order limit reached)" if truncated else "")
                ),
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "revenue": summary["revenue"],
                "d2c": summary,
            }
            if summary["customers"]:
                financials["customers"] = summary["customers"]

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(orders) + len(products),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                errors=["Order limit reached; the month is incomplete"] if truncated else [],
                metadata={
                    "financials": financials,
                    "orders_count": len(orders),
                    "products_count": len(products),
                },
            )

        except Exception as e:
            logger.error(f"Shopify sync failed: {e}")
            return SyncResult(
                success=False,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                errors=[str(e)],
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
            )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
