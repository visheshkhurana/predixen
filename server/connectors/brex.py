"""
Brex Corporate Cards Connector - Corporate card and spend data.

Provides:
- Corporate card accounts
- Card transaction history
- Transfer records
- Spend analytics

API Documentation: https://developer.brex.com/openapi/payments_api/
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

# Server listed in Brex's published OpenAPI specs (Transactions + Payments APIs).
# Paths carry their own version: /v2/accounts, /v2/transactions, /v1/transfers.
BASE_URL = "https://api.brex.com"


@ConnectorRegistry.register
class BrexConnector(BaseConnector):
    PROVIDER_ID = "brex"
    PROVIDER_NAME = "Brex"
    PROVIDER_DESCRIPTION = "Corporate card and spend management platform. Import card transactions, accounts, and transfers for expense tracking."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developer.brex.com/openapi/payments_api/"

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
            logger.warning("Brex API key not provided")
            return False

        try:
            client = await self._get_client()
            # There is no GET /v2/accounts; probe the cash accounts list, and the
            # card accounts list for card-only tokens.
            response = await client.get("/v2/accounts/cash")
            if response.status_code in (401, 403, 404):
                response = await client.get("/v2/accounts/card")

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Brex authentication successful")
                return True
            else:
                logger.warning(f"Brex auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Brex authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/v2/accounts/cash")
            if response.status_code in (401, 403, 404):
                response = await client.get("/v2/accounts/card")
            return response.status_code == 200
        except Exception:
            return False

    async def get_accounts(self) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            accounts: List[Dict[str, Any]] = []
            for path in ("/v2/accounts/cash", "/v2/accounts/card"):
                response = await client.get(path)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", data) if isinstance(data, dict) else data
                    if isinstance(items, list):
                        accounts.extend(items)
            return accounts
        except Exception as e:
            logger.error(f"Brex accounts fetch error: {e}")
            return []

    async def get_card_transactions(
        self,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_transactions = []
            cursor = None

            while True:
                params: Dict[str, Any] = {"limit": min(limit, 100)}
                if cursor:
                    params["cursor"] = cursor

                response = await client.get(
                    "/v2/transactions/card/primary",
                    params=params,
                )

                if response.status_code != 200:
                    logger.error(f"Brex card transactions error: {response.status_code}")
                    break

                data = response.json()
                items = data.get("items", [])
                all_transactions.extend(items)

                cursor = data.get("next_cursor")
                if not cursor or len(all_transactions) >= limit:
                    break

            return all_transactions

        except Exception as e:
            logger.error(f"Brex card transaction fetch error: {e}")
            return []

    async def get_transfers(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"limit": min(limit, 100)}
            response = await client.get("/v1/transfers", params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            return []
        except Exception as e:
            logger.error(f"Brex transfers fetch error: {e}")
            return []

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        transactions = await self.get_card_transactions(limit=500)
        transfers = await self.get_transfers(limit=100)
        entries = []

        for txn in transactions:
            amount_data = txn.get("amount", {})
            amount = float(amount_data.get("amount", 0)) / 100
            txn_date_str = txn.get("posted_at_date") or txn.get("initiated_at_date") or ""
            try:
                txn_date = datetime.fromisoformat(txn_date_str.replace("Z", "+00:00")).replace(tzinfo=None) if txn_date_str else datetime.now()
            except (ValueError, TypeError):
                txn_date = datetime.now()
            merchant = txn.get("merchant") or {}
            merchant_name = merchant.get("raw_descriptor") if isinstance(merchant, dict) else None

            if start_date and txn_date < start_date:
                continue
            if end_date and txn_date > end_date:
                continue

            entries.append(
                LedgerEntry(
                    external_id=txn.get("id", ""),
                    date=txn_date,
                    account_code=txn.get("card_id", ""),
                    account_name="Brex Card",
                    debit=abs(amount) if amount > 0 else 0.0,
                    credit=abs(amount) if amount < 0 else 0.0,
                    description=merchant_name or txn.get("description", ""),
                    category=txn.get("category") or (merchant.get("mcc") if isinstance(merchant, dict) else None) or "Uncategorized",
                    metadata={
                        "merchant_name": merchant_name,
                        "card_id": txn.get("card_id"),
                        "type": "card_transaction",
                        "currency": amount_data.get("currency", "USD"),
                    },
                )
            )

        for transfer in transfers:
            amount_data = transfer.get("amount", {})
            amount = float(amount_data.get("amount", 0)) / 100
            transfer_date_str = transfer.get("process_date") or transfer.get("created_at") or ""
            try:
                transfer_date = datetime.fromisoformat(transfer_date_str.replace("Z", "+00:00")).replace(tzinfo=None) if transfer_date_str else datetime.now()
            except (ValueError, TypeError):
                transfer_date = datetime.now()

            if start_date and transfer_date < start_date:
                continue
            if end_date and transfer_date > end_date:
                continue

            entries.append(
                LedgerEntry(
                    external_id=transfer.get("id", ""),
                    date=transfer_date,
                    account_code="brex_transfer",
                    account_name="Brex Transfer",
                    debit=abs(amount) if amount > 0 else 0.0,
                    credit=abs(amount) if amount < 0 else 0.0,
                    description=transfer.get("description", "Transfer"),
                    category="Transfer",
                    metadata={
                        "type": "transfer",
                        "status": transfer.get("status"),
                        "currency": amount_data.get("currency", "USD"),
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
            "source_type": "connector_brex",
            "extraction_summary": "Synced from Brex corporate cards",
        }

        if ledger_entries:
            total_spend = sum(e.debit for e in ledger_entries)
            total_inflow = sum(e.credit for e in ledger_entries)
            result["total_spend"] = total_spend
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
                    errors=["Authentication failed - check api_key"],
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
            logger.error(f"Brex sync failed: {e}")
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
