"""
Stripe connector for payment and revenue data integration.

Provides:
- Revenue and payment transaction data
- Subscription MRR/ARR metrics
- Customer payment data
- Invoice and billing information
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import httpx
import base64

from .base import (
    BaseConnector,
    ConnectorConfig,
    ProviderCategory,
    AuthType,
    SyncResult,
    InvoiceRecord,
    LedgerEntry,
    EmployeeRecord,
    PayrollRunRecord,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)


@ConnectorRegistry.register
class StripeConnector(BaseConnector):
    PROVIDER_ID = "stripe"
    PROVIDER_NAME = "Stripe"
    PROVIDER_DESCRIPTION = "Payment processing and subscription billing platform. Import revenue, MRR/ARR, and customer payment data."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://stripe.com/docs/api"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.api_key = config.credentials.get("api_key") or config.credentials.get("secret_key")
        self.base_url = "https://api.stripe.com/v1"
        self.client: Optional[httpx.AsyncClient] = None

    def _get_auth_header(self) -> Dict[str, str]:
        encoded = base64.b64encode(f"{self.api_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._get_auth_header(),
                timeout=30.0,
            )
        return self.client

    async def authenticate(self) -> bool:
        if not self.api_key:
            logger.warning("Stripe API key not provided")
            return False
        try:
            client = await self._get_client()
            response = await client.get("/balance")
            if response.status_code == 200:
                self._authenticated = True
                logger.info("Stripe authentication successful")
                return True
            else:
                logger.warning(f"Stripe auth failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Stripe auth error: {e}")
            return False

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[InvoiceRecord]:
        client = await self._get_client()
        invoices = []
        params: Dict[str, Any] = {"limit": 100}
        if start_date:
            params["created[gte]"] = int(start_date.timestamp())
        if end_date:
            params["created[lte]"] = int(end_date.timestamp())

        try:
            has_more = True
            while has_more:
                response = await client.get("/invoices", params=params)
                if response.status_code != 200:
                    logger.warning(f"Stripe invoices fetch failed: {response.status_code}")
                    break
                data = response.json()
                for inv in data.get("data", []):
                    amount = (inv.get("amount_paid", 0) or 0) / 100.0
                    tax = (inv.get("tax", 0) or 0) / 100.0
                    total = (inv.get("total", 0) or 0) / 100.0
                    status_map = {"paid": "paid", "open": "pending", "void": "cancelled", "draft": "draft"}
                    invoices.append(InvoiceRecord(
                        external_id=inv.get("id", ""),
                        date=datetime.fromtimestamp(inv.get("created", 0)),
                        due_date=datetime.fromtimestamp(inv["due_date"]) if inv.get("due_date") else None,
                        customer_name=inv.get("customer_name") or inv.get("customer_email", ""),
                        amount=amount,
                        tax=tax,
                        total=total,
                        currency=(inv.get("currency") or "usd").upper(),
                        status=status_map.get(inv.get("status", ""), inv.get("status", "unknown")),
                        metadata={"stripe_id": inv.get("id"), "subscription": inv.get("subscription")},
                    ))
                has_more = data.get("has_more", False)
                if has_more and data.get("data"):
                    params["starting_after"] = data["data"][-1]["id"]
                else:
                    has_more = False
        except Exception as e:
            logger.error(f"Error fetching Stripe invoices: {e}")
        return invoices

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[LedgerEntry]:
        client = await self._get_client()
        entries = []
        params: Dict[str, Any] = {"limit": 100, "type": "charge"}
        if start_date:
            params["created[gte]"] = int(start_date.timestamp())
        if end_date:
            params["created[lte]"] = int(end_date.timestamp())

        try:
            response = await client.get("/balance_transactions", params=params)
            if response.status_code == 200:
                data = response.json()
                for txn in data.get("data", []):
                    amount = (txn.get("amount", 0) or 0) / 100.0
                    fee = (txn.get("fee", 0) or 0) / 100.0
                    net = (txn.get("net", 0) or 0) / 100.0
                    entries.append(LedgerEntry(
                        external_id=txn.get("id", ""),
                        date=datetime.fromtimestamp(txn.get("created", 0)),
                        account_code="STRIPE_REVENUE",
                        account_name="Stripe Revenue",
                        debit=0.0,
                        credit=amount,
                        description=txn.get("description") or f"Stripe {txn.get('type', 'charge')}",
                        category="revenue",
                        metadata={"fee": fee, "net": net, "type": txn.get("type")},
                    ))
        except Exception as e:
            logger.error(f"Error fetching Stripe balance transactions: {e}")
        return entries

    async def get_mrr(self) -> float:
        client = await self._get_client()
        try:
            response = await client.get("/subscriptions", params={"status": "active", "limit": 100})
            if response.status_code == 200:
                data = response.json()
                mrr = 0.0
                for sub in data.get("data", []):
                    for item in sub.get("items", {}).get("data", []):
                        price = item.get("price", {})
                        amount = (price.get("unit_amount", 0) or 0) / 100.0
                        interval = price.get("recurring", {}).get("interval", "month")
                        qty = item.get("quantity", 1) or 1
                        if interval == "year":
                            mrr += (amount * qty) / 12
                        elif interval == "month":
                            mrr += amount * qty
                        elif interval == "week":
                            mrr += amount * qty * 4.33
                return mrr
        except Exception as e:
            logger.error(f"Error calculating Stripe MRR: {e}")
        return 0.0

    async def get_arr(self) -> float:
        return await self.get_mrr() * 12

    async def get_revenue_metrics(self) -> Dict[str, Any]:
        client = await self._get_client()
        metrics = {
            "mrr": 0.0,
            "arr": 0.0,
            "total_revenue": 0.0,
            "active_subscriptions": 0,
            "new_customers": 0,
            "churned_customers": 0,
        }
        try:
            mrr = await self.get_mrr()
            metrics["mrr"] = mrr
            metrics["arr"] = mrr * 12

            bal_resp = await client.get("/balance")
            if bal_resp.status_code == 200:
                bal = bal_resp.json()
                for avail in bal.get("available", []):
                    metrics["total_revenue"] += (avail.get("amount", 0) or 0) / 100.0

            sub_resp = await client.get("/subscriptions", params={"status": "active", "limit": 1})
            if sub_resp.status_code == 200:
                metrics["active_subscriptions"] = sub_resp.json().get("total_count", 0)
        except Exception as e:
            logger.error(f"Error getting Stripe revenue metrics: {e}")
        return metrics

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        errors = []
        total_records = 0

        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check your Stripe API key"],
                    sync_started=sync_started,
                )

            invoices = await self.fetch_invoices()
            total_records += len(invoices)

            ledger = await self.fetch_ledger()
            total_records += len(ledger)

            mrr = await self.get_mrr()

            financials = self.map_to_financials(
                invoices=invoices,
                ledger_entries=ledger,
            )
            financials["mrr"] = mrr
            financials["arr"] = mrr * 12

            self._last_sync = datetime.utcnow()

            return SyncResult(
                success=len(errors) == 0,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=total_records,
                errors=errors,
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={"financials": financials},
            )
        except Exception as e:
            logger.error(f"Stripe sync failed: {e}")
            return SyncResult(
                success=False,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                errors=[str(e)],
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
            )

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()
            self.client = None
