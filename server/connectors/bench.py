"""
Bench Bookkeeping Connector - Automated bookkeeping service.

Provides:
- Financial statements (income statement, balance sheet)
- Transaction history with categorization
- Monthly financial summaries

API Documentation: https://bench.co/api
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

BASE_URL = "https://api.bench.co/v2"


@ConnectorRegistry.register
class BenchConnector(BaseConnector):
    PROVIDER_ID = "bench"
    PROVIDER_NAME = "Bench"
    PROVIDER_DESCRIPTION = "Automated bookkeeping service providing financial statements, transaction categorization, and monthly reporting."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://bench.co/api"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_key = config.credentials.get("api_key", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._api_key:
            logger.warning("Bench API key not provided")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/transactions?limit=1")

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Bench authentication successful")
                return True
            else:
                logger.warning(f"Bench auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Bench authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/transactions?limit=1")
            return response.status_code == 200
        except Exception:
            return False

    async def get_financial_statements(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not self._authenticated:
            if not await self.authenticate():
                return {}

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {}
            if year:
                params["year"] = year
            if month:
                params["month"] = month

            response = await client.get("/financial-statements", params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Bench financial statements error: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Bench financial statements fetch error: {e}")
            return {}

    async def get_transactions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_transactions = []
            current_page = page

            while True:
                params: Dict[str, Any] = {"page": current_page, "limit": limit}
                if start_date:
                    params["start_date"] = start_date
                if end_date:
                    params["end_date"] = end_date

                response = await client.get("/transactions", params=params)

                if response.status_code != 200:
                    logger.error(f"Bench transactions error: {response.status_code}")
                    break

                data = response.json()
                transactions = data.get("transactions", data.get("data", []))
                all_transactions.extend(transactions)

                total_pages = data.get("total_pages", data.get("pages", 1))
                if current_page >= total_pages or not transactions:
                    break
                current_page += 1

            return all_transactions

        except Exception as e:
            logger.error(f"Bench transactions fetch error: {e}")
            return []

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        start_str = start_date.strftime("%Y-%m-%d") if start_date else None
        end_str = end_date.strftime("%Y-%m-%d") if end_date else None

        transactions = await self.get_transactions(start_date=start_str, end_date=end_str)
        entries = []

        for txn in transactions:
            amount = float(txn.get("amount", 0))
            date_str = txn.get("date", txn.get("transaction_date", ""))
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
            except (ValueError, TypeError):
                date = datetime.now()

            category = txn.get("category", txn.get("account_name", "Uncategorized"))
            is_debit = amount >= 0

            entries.append(
                LedgerEntry(
                    external_id=str(txn.get("id", txn.get("transaction_id", ""))),
                    date=date,
                    account_code=str(txn.get("account_id", txn.get("account_code", ""))),
                    account_name=txn.get("account_name", category),
                    debit=abs(amount) if is_debit else 0.0,
                    credit=abs(amount) if not is_debit else 0.0,
                    description=txn.get("description", txn.get("memo", "")),
                    category=category,
                    metadata={
                        "vendor": txn.get("vendor", ""),
                        "reconciled": txn.get("reconciled", False),
                        "source": "bench",
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
            "source_type": "connector_bench",
            "extraction_summary": "Synced from Bench Bookkeeping",
        }

        if ledger_entries:
            result["total_debits"] = sum(e.debit for e in ledger_entries)
            result["total_credits"] = sum(e.credit for e in ledger_entries)
            result["transactions_count"] = len(ledger_entries)
            categories: Dict[str, float] = {}
            for entry in ledger_entries:
                if entry.category and entry.debit > 0:
                    categories[entry.category] = categories.get(entry.category, 0) + entry.debit
            result["expense_breakdown"] = categories

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

            transactions = await self.get_transactions()
            statements = await self.get_financial_statements()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(transactions),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "transactions_count": len(transactions),
                    "has_statements": bool(statements),
                },
            )

        except Exception as e:
            logger.error(f"Bench sync failed: {e}")
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
