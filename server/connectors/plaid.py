"""
Plaid Connector - Banking data aggregation.

Provides:
- Bank account data (checking, savings, credit)
- Account balances (current, available)
- Transaction history with categorization
- Cash position tracking

API Documentation: https://plaid.com/docs/api/
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


PLAID_ENVIRONMENTS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}


@ConnectorRegistry.register
class PlaidConnector(BaseConnector):
    PROVIDER_ID = "plaid"
    PROVIDER_NAME = "Plaid"
    PROVIDER_DESCRIPTION = "Bank account aggregation. Import balances, transactions, and cash position from connected bank accounts."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://plaid.com/docs/api/"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client_id = config.credentials.get("client_id", "")
        self._secret = config.credentials.get("secret", "")
        self._access_token = config.credentials.get("access_token", "")
        env = config.settings.get("environment", "sandbox")
        self._base_url = PLAID_ENVIRONMENTS.get(env, PLAID_ENVIRONMENTS["sandbox"])
        self._client: Optional[httpx.AsyncClient] = None
        self._accounts: List[Dict[str, Any]] = []

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    def _auth_payload(self) -> Dict[str, str]:
        return {
            "client_id": self._client_id,
            "secret": self._secret,
        }

    async def authenticate(self) -> bool:
        if not all([self._client_id, self._secret, self._access_token]):
            logger.warning("Plaid credentials incomplete")
            return False

        try:
            client = await self._get_client()
            payload = {
                **self._auth_payload(),
                "access_token": self._access_token,
            }
            response = await client.post("/accounts/get", json=payload)

            if response.status_code == 200:
                data = response.json()
                self._accounts = data.get("accounts", [])
                self._authenticated = True
                logger.info(f"Plaid authentication successful, {len(self._accounts)} accounts found")
                return True
            else:
                error = response.json().get("error_message", response.text)
                logger.warning(f"Plaid auth failed: {error}")
                return False

        except Exception as e:
            logger.error(f"Plaid authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            payload = {
                **self._auth_payload(),
                "access_token": self._access_token,
            }
            response = await client.post("/accounts/get", json=payload)
            return response.status_code == 200
        except Exception:
            return False

    async def get_accounts(self) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []
        return self._accounts

    async def get_balances(self) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            payload = {
                **self._auth_payload(),
                "access_token": self._access_token,
            }
            response = await client.post("/accounts/balance/get", json=payload)

            if response.status_code == 200:
                data = response.json()
                accounts = data.get("accounts", [])
                return [
                    {
                        "account_id": acc.get("account_id"),
                        "name": acc.get("name", ""),
                        "official_name": acc.get("official_name", ""),
                        "type": acc.get("type", ""),
                        "subtype": acc.get("subtype", ""),
                        "current": acc.get("balances", {}).get("current", 0),
                        "available": acc.get("balances", {}).get("available", 0),
                        "limit": acc.get("balances", {}).get("limit"),
                        "currency": acc.get("balances", {}).get("iso_currency_code", "USD"),
                    }
                    for acc in accounts
                ]
            return []
        except Exception as e:
            logger.error(f"Plaid balance fetch error: {e}")
            return []

    async def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        count: int = 500,
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
            total = None

            while total is None or offset < total:
                payload = {
                    **self._auth_payload(),
                    "access_token": self._access_token,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "options": {
                        "count": min(count, 500),
                        "offset": offset,
                    },
                }
                response = await client.post("/transactions/get", json=payload)

                if response.status_code != 200:
                    error = response.json().get("error_message", response.text)
                    logger.error(f"Plaid transactions error: {error}")
                    break

                data = response.json()
                transactions = data.get("transactions", [])
                total = data.get("total_transactions", 0)
                all_transactions.extend(transactions)
                offset += len(transactions)

                if len(transactions) == 0:
                    break

            return all_transactions

        except Exception as e:
            logger.error(f"Plaid transaction fetch error: {e}")
            return []

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        transactions = await self.get_transactions(start_date, end_date)
        entries = []

        for txn in transactions:
            category = txn.get("category", [])
            category_str = " > ".join(category) if category else "Uncategorized"
            amount = txn.get("amount", 0)

            entries.append(
                LedgerEntry(
                    external_id=txn.get("transaction_id", ""),
                    date=datetime.strptime(txn.get("date", "2025-01-01"), "%Y-%m-%d"),
                    account_code=txn.get("account_id", ""),
                    account_name=txn.get("name", ""),
                    debit=abs(amount) if amount > 0 else 0.0,
                    credit=abs(amount) if amount < 0 else 0.0,
                    description=txn.get("merchant_name") or txn.get("name", ""),
                    category=category_str,
                    metadata={
                        "plaid_category": category,
                        "merchant_name": txn.get("merchant_name"),
                        "pending": txn.get("pending", False),
                        "location": txn.get("location", {}),
                        "payment_channel": txn.get("payment_channel"),
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
            "source_type": "connector_plaid",
            "extraction_summary": f"Synced from Plaid ({len(self._accounts)} accounts)",
        }

        total_cash = sum(
            acc.get("balances", {}).get("current", 0)
            for acc in self._accounts
            if acc.get("type") in ("depository",)
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
                    errors=["Authentication failed - check client_id, secret, and access_token"],
                    sync_started=sync_started,
                )

            balances = await self.get_balances()
            transactions = await self.get_transactions()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(transactions) + len(balances),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "accounts_count": len(self._accounts),
                    "transactions_count": len(transactions),
                    "balances": balances,
                },
            )

        except Exception as e:
            logger.error(f"Plaid sync failed: {e}")
            return SyncResult(
                success=False,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                errors=[str(e)],
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
            )

    async def create_link_token(self, user_id: str) -> Optional[str]:
        try:
            client = await self._get_client()
            payload = {
                **self._auth_payload(),
                "user": {"client_user_id": user_id},
                "client_name": "Predixen Intelligence OS",
                "products": ["transactions"],
                "country_codes": ["US"],
                "language": "en",
            }
            response = await client.post("/link/token/create", json=payload)
            if response.status_code == 200:
                return response.json().get("link_token")
            return None
        except Exception as e:
            logger.error(f"Plaid link token error: {e}")
            return None

    async def exchange_public_token(self, public_token: str) -> Optional[str]:
        try:
            client = await self._get_client()
            payload = {
                **self._auth_payload(),
                "public_token": public_token,
            }
            response = await client.post("/item/public_token/exchange", json=payload)
            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("access_token", "")
                return self._access_token
            return None
        except Exception as e:
            logger.error(f"Plaid token exchange error: {e}")
            return None

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
