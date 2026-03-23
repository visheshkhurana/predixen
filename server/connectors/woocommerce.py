"""
WooCommerce E-commerce Connector - WordPress store and revenue data.

Provides:
- Order data (as invoices and ledger entries)
- Product catalog
- Customer records
- Revenue and sales analytics
- COD/Prepaid split tracking
- Refund and return tracking

API Documentation: https://woocommerce.github.io/woocommerce-rest-api-docs/
"""

import httpx
import logging
import base64
from urllib.parse import urlparse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

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


@ConnectorRegistry.register
class WooCommerceConnector(BaseConnector):
    PROVIDER_ID = "woocommerce"
    PROVIDER_NAME = "WooCommerce"
    PROVIDER_DESCRIPTION = "WordPress e-commerce platform. Import orders, products, and customers for revenue tracking, COD/prepaid split analysis, and sales analytics."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://woocommerce.github.io/woocommerce-rest-api-docs/"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._store_url = config.credentials.get("store_url", "").rstrip("/")
        self._consumer_key = config.credentials.get("consumer_key", "")
        self._consumer_secret = config.credentials.get("consumer_secret", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._validate_store_url()

    def _validate_store_url(self):
        if not self._store_url:
            return
        parsed = urlparse(self._store_url)
        if parsed.scheme not in ("https", "http"):
            raise ValueError("WooCommerce store URL must use https:// or http://")
        hostname = parsed.hostname or ""
        blocked = ["localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254", "metadata.google.internal"]
        if hostname in blocked or hostname.startswith("10.") or hostname.startswith("192.168.") or hostname.startswith("172."):
            raise ValueError("WooCommerce store URL must be a public domain")

    def _get_base_url(self) -> str:
        return f"{self._store_url}/wp-json/wc/v3"

    def _is_https(self) -> bool:
        return self._store_url.startswith("https://")

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            params = {}

            if self._is_https():
                auth_string = base64.b64encode(
                    f"{self._consumer_key}:{self._consumer_secret}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {auth_string}"
            else:
                params["consumer_key"] = self._consumer_key
                params["consumer_secret"] = self._consumer_secret

            self._client = httpx.AsyncClient(
                base_url=self._get_base_url(),
                timeout=30.0,
                params=params,
                headers=headers,
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._store_url or not self._consumer_key or not self._consumer_secret:
            logger.warning("WooCommerce store_url, consumer_key, or consumer_secret not provided")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/products", params={"per_page": 1})

            if response.status_code == 200:
                self._authenticated = True
                logger.info("WooCommerce authentication successful")
                return True
            else:
                logger.warning(f"WooCommerce auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"WooCommerce authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/products", params={"per_page": 1})
            return response.status_code == 200
        except Exception:
            return False

    async def get_orders(
        self,
        start_date: Optional[datetime] = None,
        limit: int = 500,
        status: str = "any",
    ) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_orders = []
            page = 1
            per_page = min(limit, 100)

            while True:
                params: Dict[str, Any] = {
                    "per_page": per_page,
                    "page": page,
                    "orderby": "date",
                    "order": "desc",
                }
                if start_date:
                    params["after"] = start_date.strftime("%Y-%m-%dT00:00:00")
                if status != "any":
                    params["status"] = status

                response = await client.get("/orders", params=params)

                if response.status_code != 200:
                    logger.error(f"WooCommerce orders error: {response.status_code}")
                    break

                orders = response.json()
                if not orders:
                    break

                all_orders.extend(orders)

                total_pages = int(response.headers.get("X-WP-TotalPages", 1))
                if page >= total_pages or len(all_orders) >= limit:
                    break

                page += 1

            return all_orders[:limit]

        except Exception as e:
            logger.error(f"WooCommerce orders fetch error: {e}")
            return []

    async def get_products(self, limit: int = 250) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_products = []
            page = 1
            per_page = min(limit, 100)

            while True:
                params: Dict[str, Any] = {"per_page": per_page, "page": page}
                response = await client.get("/products", params=params)

                if response.status_code != 200:
                    break

                products = response.json()
                if not products:
                    break

                all_products.extend(products)

                total_pages = int(response.headers.get("X-WP-TotalPages", 1))
                if page >= total_pages or len(all_products) >= limit:
                    break

                page += 1

            return all_products[:limit]
        except Exception as e:
            logger.error(f"WooCommerce products fetch error: {e}")
            return []

    async def get_customers(self, limit: int = 250) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_customers = []
            page = 1
            per_page = min(limit, 100)

            while True:
                params: Dict[str, Any] = {"per_page": per_page, "page": page}
                response = await client.get("/customers", params=params)

                if response.status_code != 200:
                    break

                customers = response.json()
                if not customers:
                    break

                all_customers.extend(customers)

                total_pages = int(response.headers.get("X-WP-TotalPages", 1))
                if page >= total_pages or len(all_customers) >= limit:
                    break

                page += 1

            return all_customers[:limit]
        except Exception as e:
            logger.error(f"WooCommerce customers fetch error: {e}")
            return []

    async def get_refunds(self, order_id: int) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            response = await client.get(f"/orders/{order_id}/refunds")

            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"WooCommerce refunds fetch error for order {order_id}: {e}")
            return []

    def _parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.now()
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return datetime.now()

    def _detect_payment_type(self, order: Dict[str, Any]) -> str:
        method = order.get("payment_method", "").lower()
        method_title = order.get("payment_method_title", "").lower()

        cod_keywords = ["cod", "cash on delivery", "cash_on_delivery", "pay on delivery"]
        for kw in cod_keywords:
            if kw in method or kw in method_title:
                return "cod"
        return "prepaid"

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        orders = await self.get_orders(start_date=start_date, limit=500)
        entries = []

        for order in orders:
            total_price = float(order.get("total", 0))
            order_date = self._parse_date(order.get("date_created", ""))

            if end_date and order_date > end_date:
                continue

            payment_type = self._detect_payment_type(order)
            shipping_total = float(order.get("shipping_total", 0))

            entries.append(
                LedgerEntry(
                    external_id=str(order.get("id", "")),
                    date=order_date,
                    account_code="woocommerce_revenue",
                    account_name="WooCommerce Revenue",
                    debit=0.0,
                    credit=total_price,
                    description=f"Order #{order.get('number', '')} - {order.get('billing', {}).get('email', '')}",
                    category="Sales Revenue",
                    metadata={
                        "order_number": order.get("number"),
                        "status": order.get("status"),
                        "payment_method": order.get("payment_method"),
                        "payment_type": payment_type,
                        "currency": order.get("currency", "USD"),
                        "shipping_total": shipping_total,
                        "discount_total": float(order.get("discount_total", 0)),
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
            total_price = float(order.get("total", 0))
            subtotal = sum(float(item.get("subtotal", 0)) for item in order.get("line_items", []))
            total_tax = float(order.get("total_tax", 0))
            order_date = self._parse_date(order.get("date_created", ""))

            if end_date and order_date > end_date:
                continue

            billing = order.get("billing", {})
            customer_name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
            if not customer_name:
                customer_name = billing.get("email", "Guest")

            wc_status = order.get("status", "pending")
            status_map = {
                "completed": "paid",
                "processing": "paid",
                "on-hold": "pending",
                "pending": "pending",
                "cancelled": "cancelled",
                "refunded": "refunded",
                "failed": "cancelled",
            }

            payment_type = self._detect_payment_type(order)

            line_items = []
            for item in order.get("line_items", []):
                line_items.append({
                    "name": item.get("name", ""),
                    "quantity": item.get("quantity", 0),
                    "price": float(item.get("price", 0)),
                    "sku": item.get("sku", ""),
                    "product_id": item.get("product_id"),
                })

            invoices.append(
                InvoiceRecord(
                    external_id=str(order.get("id", "")),
                    date=order_date,
                    customer_name=customer_name,
                    amount=subtotal,
                    tax=total_tax,
                    total=total_price,
                    currency=order.get("currency", "USD"),
                    status=status_map.get(wc_status, "pending"),
                    line_items=line_items,
                    metadata={
                        "order_number": order.get("number"),
                        "wc_status": wc_status,
                        "payment_method": order.get("payment_method"),
                        "payment_method_title": order.get("payment_method_title"),
                        "payment_type": payment_type,
                        "shipping_total": float(order.get("shipping_total", 0)),
                        "shipping_tax": float(order.get("shipping_tax", 0)),
                        "discount_total": float(order.get("discount_total", 0)),
                        "source": "woocommerce_order",
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
            "source_type": "connector_woocommerce",
            "extraction_summary": f"Synced from WooCommerce ({self._store_url})",
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
            discount_total = sum(float(inv.metadata.get("discount_total", 0)) for inv in invoices)
            result["total_shipping"] = shipping_total
            result["total_discounts"] = discount_total

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
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check store_url, consumer_key, and consumer_secret"],
                    sync_started=sync_started,
                )

            orders = await self.get_orders(limit=500)
            products = await self.get_products()
            customers = await self.get_customers()
            invoices = await self.fetch_invoices()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(ledger_entries=ledger, invoices=invoices)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(orders) + len(products) + len(customers),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "orders_count": len(orders),
                    "products_count": len(products),
                    "customers_count": len(customers),
                },
            )

        except Exception as e:
            logger.error(f"WooCommerce sync failed: {e}")
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
