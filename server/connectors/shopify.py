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
        return f"https://{domain}.myshopify.com/admin/api/2024-01"

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
                    errors=["Authentication failed - check shop_domain and access_token"],
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
