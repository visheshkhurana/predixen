"""
Chargebee Subscription Billing Connector - Subscription management and billing.

Provides:
- Subscription lifecycle management
- Invoice and billing data
- Customer records
- Plan/pricing catalog

API Documentation: https://apidocs.chargebee.com/docs/api
"""

import httpx
import logging
import base64
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
class ChargebeeConnector(BaseConnector):
    PROVIDER_ID = "chargebee"
    PROVIDER_NAME = "Chargebee"
    PROVIDER_DESCRIPTION = "Subscription billing platform for recurring revenue management. Import subscriptions, invoices, customers, and plan data."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://apidocs.chargebee.com/docs/api"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._site = config.credentials.get("site", "")
        self._api_key = config.credentials.get("api_key", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            base_url = f"https://{self._site}.chargebee.com/api/v2"
            auth_string = base64.b64encode(f"{self._api_key}:".encode()).decode()
            self._client = httpx.AsyncClient(
                base_url=base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {auth_string}",
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._site or not self._api_key:
            logger.warning("Chargebee credentials incomplete - need site and api_key")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/subscriptions?limit=1")

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Chargebee authentication successful")
                return True
            else:
                logger.warning(f"Chargebee auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Chargebee authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/subscriptions?limit=1")
            return response.status_code == 200
        except Exception:
            return False

    async def get_subscriptions(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_subscriptions = []
            offset = None

            while True:
                params: Dict[str, Any] = {"limit": min(limit, 100)}
                if offset:
                    params["offset"] = offset

                response = await client.get("/subscriptions", params=params)

                if response.status_code != 200:
                    logger.error(f"Chargebee subscriptions error: {response.status_code}")
                    break

                data = response.json()
                entries = data.get("list", [])
                all_subscriptions.extend([e.get("subscription", {}) for e in entries])

                offset = data.get("next_offset")
                if not offset or len(all_subscriptions) >= limit:
                    break

            return all_subscriptions

        except Exception as e:
            logger.error(f"Chargebee subscriptions fetch error: {e}")
            return []

    async def get_invoices_raw(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_invoices = []
            offset = None

            while True:
                params: Dict[str, Any] = {"limit": min(limit, 100)}
                if offset:
                    params["offset"] = offset

                response = await client.get("/invoices", params=params)

                if response.status_code != 200:
                    logger.error(f"Chargebee invoices error: {response.status_code}")
                    break

                data = response.json()
                entries = data.get("list", [])
                all_invoices.extend([e.get("invoice", {}) for e in entries])

                offset = data.get("next_offset")
                if not offset or len(all_invoices) >= limit:
                    break

            return all_invoices

        except Exception as e:
            logger.error(f"Chargebee invoices fetch error: {e}")
            return []

    async def get_customers(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"limit": min(limit, 100)}
            response = await client.get("/customers", params=params)

            if response.status_code == 200:
                data = response.json()
                return [e.get("customer", {}) for e in data.get("list", [])]
            return []
        except Exception as e:
            logger.error(f"Chargebee customers fetch error: {e}")
            return []

    async def get_plans(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"limit": min(limit, 100)}
            response = await client.get("/plans", params=params)

            if response.status_code == 200:
                data = response.json()
                return [e.get("plan", {}) for e in data.get("list", [])]
            return []
        except Exception as e:
            logger.error(f"Chargebee plans fetch error: {e}")
            return []

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        raw_invoices = await self.get_invoices_raw()
        invoices = []

        for inv in raw_invoices:
            amount = float(inv.get("total", 0)) / 100.0
            sub_total = float(inv.get("sub_total", 0)) / 100.0
            tax = float(inv.get("tax", 0)) / 100.0

            date_ts = inv.get("date")
            try:
                date = datetime.utcfromtimestamp(date_ts) if date_ts else datetime.now()
            except (ValueError, TypeError, OSError):
                date = datetime.now()

            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue

            due_date_ts = inv.get("due_date")
            try:
                due_date = datetime.utcfromtimestamp(due_date_ts) if due_date_ts else None
            except (ValueError, TypeError, OSError):
                due_date = None

            status = inv.get("status", "pending")
            currency = inv.get("currency_code", "USD")
            customer_id = inv.get("customer_id", "")

            invoices.append(
                InvoiceRecord(
                    external_id=str(inv.get("id", "")),
                    date=date,
                    due_date=due_date,
                    customer_name=customer_id,
                    amount=sub_total,
                    tax=tax,
                    total=amount,
                    currency=currency,
                    status=status,
                    metadata={
                        "subscription_id": inv.get("subscription_id", ""),
                        "recurring": inv.get("recurring", False),
                        "source": "chargebee",
                    },
                )
            )

        return invoices

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        raw_invoices = await self.get_invoices_raw()
        entries = []

        for inv in raw_invoices:
            amount = float(inv.get("total", 0)) / 100.0
            date_ts = inv.get("date")
            try:
                date = datetime.utcfromtimestamp(date_ts) if date_ts else datetime.now()
            except (ValueError, TypeError, OSError):
                date = datetime.now()

            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue

            status = inv.get("status", "")

            entries.append(
                LedgerEntry(
                    external_id=str(inv.get("id", "")),
                    date=date,
                    account_code="subscription_revenue",
                    account_name="Subscription Revenue",
                    debit=0.0,
                    credit=amount if status == "paid" else 0.0,
                    description=f"Chargebee invoice {inv.get('id', '')} - {inv.get('subscription_id', '')}",
                    category="Subscription Revenue",
                    metadata={
                        "subscription_id": inv.get("subscription_id", ""),
                        "status": status,
                        "source": "chargebee",
                    },
                )
            )

        return entries

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        result = {
            "source_type": "connector_chargebee",
            "extraction_summary": "Synced from Chargebee Subscription Billing",
        }

        if invoices:
            result["revenue"] = sum(inv.total for inv in invoices if inv.status == "paid")
            result["invoices_count"] = len(invoices)
            result["mrr"] = sum(
                inv.total for inv in invoices
                if inv.status == "paid" and inv.metadata.get("recurring")
            )

        if ledger_entries:
            result["total_subscription_revenue"] = sum(e.credit for e in ledger_entries)

        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check site and api_key"],
                    sync_started=sync_started,
                )

            subscriptions = await self.get_subscriptions()
            raw_invoices = await self.get_invoices_raw()
            customers = await self.get_customers()
            plans = await self.get_plans()
            invoices = await self.fetch_invoices()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(invoices=invoices, ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(subscriptions) + len(raw_invoices) + len(customers) + len(plans),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "subscriptions_count": len(subscriptions),
                    "invoices_count": len(raw_invoices),
                    "customers_count": len(customers),
                    "plans_count": len(plans),
                },
            )

        except Exception as e:
            logger.error(f"Chargebee sync failed: {e}")
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
