"""
Mercury Banking Connector - Business banking data.

Provides:
- Business bank account data
- Transaction history
- Account balances and cash position

API Documentation: https://docs.mercury.com/reference
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

BASE_URL = "https://api.mercury.com/api/v1"


@ConnectorRegistry.register
class MercuryConnector(BaseConnector):
    PROVIDER_ID = "mercury"
    PROVIDER_NAME = "Mercury"
    PROVIDER_DESCRIPTION = "Business banking platform. Import bank accounts, transactions, and cash position data for treasury management."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://docs.mercury.com/reference"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_token = config.credentials.get("api_token", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._accounts: List[Dict[str, Any]] = []

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_token}",
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._api_token:
            logger.warning("Mercury API token not provided")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/accounts")

            if response.status_code == 200:
                data = response.json()
                self._accounts = data.get("accounts", [])
                self._authenticated = True
                logger.info(f"Mercury authentication successful, {len(self._accounts)} accounts found")
                return True
            else:
                logger.warning(f"Mercury auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Mercury authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/accounts")
            return response.status_code == 200
        except Exception:
            return False

    async def get_accounts(self) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        return self._accounts

    async def get_transactions(
        self,
        account_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        if not start_date:
            start_date = datetime.now() - timedelta(days=90)
        if not end_date:
            end_date = datetime.now()

        try:
            client = await self._get_client()
            all_transactions = []
            offset = 0

            while True:
                params: Dict[str, Any] = {
                    "limit": min(limit, 500),
                    "offset": offset,
                    "start": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                    "end": end_date.strftime("%Y-%m-%dT23:59:59Z"),
                }

                response = await client.get(
                    f"/accounts/{account_id}/transactions",
                    params=params,
                )

                if response.status_code != 200:
                    logger.error(f"Mercury transactions error: {response.status_code}")
                    break

                data = response.json()
                transactions = data.get("transactions", [])
                all_transactions.extend(transactions)

                if len(transactions) < min(limit, 500):
                    break

                offset += len(transactions)
                if len(all_transactions) >= limit:
                    break

            return all_transactions

        except Exception as e:
            logger.error(f"Mercury transaction fetch error: {e}")
            return []

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        entries = []
        for account in self._accounts:
            account_id = account.get("id", "")
            account_name = account.get("name", "Mercury Account")
            transactions = await self.get_transactions(account_id, start_date, end_date)

            for txn in transactions:
                amount = float(txn.get("amount", 0))
                txn_date_str = txn.get("createdAt", "")
                try:
                    txn_date = datetime.fromisoformat(txn_date_str.replace("Z", "+00:00")) if txn_date_str else datetime.now()
                except (ValueError, TypeError):
                    txn_date = datetime.now()

                entries.append(
                    LedgerEntry(
                        external_id=txn.get("id", ""),
                        date=txn_date,
                        account_code=account_id,
                        account_name=account_name,
                        debit=abs(amount) if amount < 0 else 0.0,
                        credit=abs(amount) if amount > 0 else 0.0,
                        description=txn.get("counterpartyName") or txn.get("note", ""),
                        category=txn.get("kind", "Uncategorized"),
                        metadata={
                            "status": txn.get("status"),
                            "counterparty_name": txn.get("counterpartyName"),
                            "kind": txn.get("kind"),
                            "bank_description": txn.get("bankDescription"),
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
            "source_type": "connector_mercury",
            "extraction_summary": f"Synced from Mercury ({len(self._accounts)} accounts)",
        }

        total_cash = sum(
            float(acc.get("currentBalance", 0))
            for acc in self._accounts
        )
        result["cash_balance"] = total_cash

        if ledger_entries:
            total_outflow = sum(e.debit for e in ledger_entries)
            total_inflow = sum(e.credit for e in ledger_entries)
            result["total_outflow"] = total_outflow
            result["total_inflow"] = total_inflow
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
                    errors=["Authentication failed - check api_token"],
                    sync_started=sync_started,
                )

            accounts = await self.get_accounts()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(ledger) + len(accounts),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "accounts_count": len(accounts),
                    "transactions_count": len(ledger),
                },
            )

        except Exception as e:
            logger.error(f"Mercury sync failed: {e}")
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
