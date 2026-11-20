"""
Recurly Subscription Management Connector - Subscription billing platform.

Provides:
- Subscription lifecycle data
- Invoice and billing records
- Account management
- Transaction history

API Documentation: https://developers.recurly.com/api/v2021-02-25/
"""

import httpx
from .http import http_client
import logging
from typing import List, Optional, Dict, Any
from datetime import date as date_cls, datetime, timedelta

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

BASE_URL = "https://v3.recurly.com"
# Recurly hosts EU-data-center sites on a separate API host. Mirrors the
# official client (recurly-client-python base_client.API_HOSTS).
API_HOSTS = {"us": "https://v3.recurly.com", "eu": "https://v3.eu.recurly.com"}
# Safety cap on pages followed per list call.
MAX_PAGES = 50


@ConnectorRegistry.register
class RecurlyConnector(BaseConnector):
    PROVIDER_ID = "recurly"
    PROVIDER_NAME = "Recurly"
    PROVIDER_DESCRIPTION = "Subscription management platform for recurring billing. Import subscriptions, invoices, accounts, and transaction data."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developers.recurly.com/api/v2021-02-25/"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_key = config.credentials.get("api_key", "")
        region = str(config.credentials.get("region") or "us").strip().lower()
        self._base_url = API_HOSTS.get(region, BASE_URL)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            # Recurly v3 uses HTTP Basic auth: API key as username, empty
            # password (it does not accept Bearer tokens).
            self._client = http_client(
                base_url=self._base_url,
                timeout=30.0,
                auth=httpx.BasicAuth(self._api_key, ""),
                headers={
                    "Accept": "application/vnd.recurly.v2021-02-25+json",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._api_key:
            logger.warning("Recurly API key not provided")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/sites")

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Recurly authentication successful")
                return True
            else:
                logger.warning(f"Recurly auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Recurly authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/sites")
            return response.status_code == 200
        except Exception:
            return False

    async def _list_all(self, path: str, limit: int, label: str) -> List[Dict[str, Any]]:
        """Follow Recurly list pagination.

        ``next`` in a list response is a full path + query string (e.g.
        ``/subscriptions?cursor=...&limit=200``) that must be requested as-is;
        it is not a bare cursor value.
        """
        client = await self._get_client()
        results: List[Dict[str, Any]] = []
        response = await client.get(path, params={"limit": min(limit, 200)})
        pages = 0
        while True:
            pages += 1
            if response.status_code != 200:
                logger.error(f"Recurly {label} error: {response.status_code}")
                break
            data = response.json()
            results.extend(data.get("data", []))
            next_path = data.get("next")
            if not data.get("has_more") or not next_path or len(results) >= limit or pages >= MAX_PAGES:
                break
            response = await client.get(next_path)
        return results[:limit]

    async def get_subscriptions(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            return await self._list_all("/subscriptions", limit, "subscriptions")
        except Exception as e:
            logger.error(f"Recurly subscriptions fetch error: {e}")
            return []

    async def get_invoices_raw(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            return await self._list_all("/invoices", limit, "invoices")
        except Exception as e:
            logger.error(f"Recurly invoices fetch error: {e}")
            return []

    async def get_accounts(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"limit": min(limit, 200)}
            response = await client.get("/accounts", params=params)

            if response.status_code == 200:
                return response.json().get("data", [])
            return []
        except Exception as e:
            logger.error(f"Recurly accounts fetch error: {e}")
            return []

    async def get_transactions(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            return await self._list_all("/transactions", limit, "transactions")
        except Exception as e:
            logger.error(f"Recurly transactions fetch error: {e}")
            return []

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        raw_invoices = await self.get_invoices_raw()
        invoices = []

        for inv in raw_invoices:
            total = float(inv.get("total", 0))
            subtotal = float(inv.get("subtotal", 0))
            tax = float(inv.get("tax", 0))

            created_at = inv.get("created_at", "")
            try:
                date = datetime.fromisoformat(created_at.replace("Z", "+00:00")) if created_at else datetime.now()
            except (ValueError, TypeError):
                date = datetime.now()

            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue

            due_at = inv.get("due_at", inv.get("net_terms_at", ""))
            try:
                due_date = datetime.fromisoformat(due_at.replace("Z", "+00:00")) if due_at else None
            except (ValueError, TypeError):
                due_date = None

            account = inv.get("account", {}) or {}
            status = inv.get("state", inv.get("status", "pending"))
            currency = inv.get("currency", "USD")

            invoices.append(
                InvoiceRecord(
                    external_id=str(inv.get("id", "")),
                    date=date,
                    due_date=due_date,
                    customer_name=account.get("code", account.get("email", "")),
                    amount=subtotal,
                    tax=tax,
                    total=total,
                    currency=currency,
                    status=status,
                    metadata={
                        "number": inv.get("number", ""),
                        "type": inv.get("type", ""),
                        "collection_method": inv.get("collection_method", ""),
                        "source": "recurly",
                    },
                )
            )

        return invoices

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        raw_transactions = await self.get_transactions()
        entries = []

        for txn in raw_transactions:
            amount = float(txn.get("amount", 0))
            created_at = txn.get("created_at", "")
            try:
                date = datetime.fromisoformat(created_at.replace("Z", "+00:00")) if created_at else datetime.now()
            except (ValueError, TypeError):
                date = datetime.now()

            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue

            txn_type = txn.get("type", "")
            status = txn.get("status", "")
            is_successful = status in ("success", "completed")
            is_failed = status in ("declined", "error", "failed")
            is_refund = txn_type == "refund"
            # A successful refund is money going back out; it used to be booked
            # as collected revenue. Pending/processing/void rows move no money
            # yet and were being counted as failed payments.
            if is_successful and is_refund:
                debit, credit, category = abs(amount), 0.0, "Refund"
            elif is_successful and txn_type != "verify":
                debit, credit, category = 0.0, abs(amount), "Subscription Revenue"
            elif is_failed:
                debit, credit, category = 0.0, 0.0, "Failed Payment"
            else:
                debit, credit, category = 0.0, 0.0, "Pending"

            entries.append(
                LedgerEntry(
                    external_id=str(txn.get("id", "")),
                    date=date,
                    account_code=txn.get("account", {}).get("code", "") if isinstance(txn.get("account"), dict) else "",
                    account_name="Subscription Revenue",
                    debit=debit,
                    credit=credit,
                    description=f"Recurly {txn_type} - {txn.get('id', '')}",
                    category=category,
                    metadata={
                        "type": txn_type,
                        "status": status,
                        "amount": abs(amount),
                        "currency": txn.get("currency"),
                        "payment_method": txn.get("payment_method", {}).get("object", "") if isinstance(txn.get("payment_method"), dict) else "",
                        "source": "recurly",
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
            "source_type": "connector_recurly",
            "extraction_summary": "Synced from Recurly Subscription Management",
        }

        if invoices:
            # This month's collected invoices in the main currency, not every
            # paid invoice fetched.
            today = date_cls.today()
            start = today.replace(day=1)
            paid = [i for i in invoices if i.status in ("paid", "collected")]
            counts: Dict[str, int] = {}
            for i in paid:
                counts[i.currency] = counts.get(i.currency, 0) + 1
            main = max(counts, key=counts.get) if counts else None
            month = [i for i in paid if start <= i.date.date() <= today and i.currency == main]
            result["revenue"] = round(sum(i.total for i in month), 2)
            if main:
                result["revenue_currency"] = main
            result["period_start"] = start.isoformat()
            result["period_end"] = today.isoformat()
            result["invoices_count"] = len(invoices)
            result["outstanding"] = sum(inv.total for inv in invoices if inv.status in ("pending", "past_due"))

        if ledger_entries:
            refunded = sum(e.debit for e in ledger_entries if e.category == "Refund")
            result["total_collected"] = sum(e.credit for e in ledger_entries) - refunded
            result["total_refunded"] = refunded
            result["total_failed"] = sum(
                e.metadata.get("amount", 0) for e in ledger_entries if e.category == "Failed Payment"
            )
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
                    errors=["Authentication failed - check api_key"],
                    sync_started=sync_started,
                )

            subscriptions = await self.get_subscriptions()
            raw_invoices = await self.get_invoices_raw()
            accounts = await self.get_accounts()
            transactions = await self.get_transactions()
            invoices = await self.fetch_invoices()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(invoices=invoices, ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(subscriptions) + len(raw_invoices) + len(accounts) + len(transactions),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "subscriptions_count": len(subscriptions),
                    "invoices_count": len(raw_invoices),
                    "accounts_count": len(accounts),
                    "transactions_count": len(transactions),
                },
            )

        except Exception as e:
            logger.error(f"Recurly sync failed: {e}")
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
