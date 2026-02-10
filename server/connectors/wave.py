"""
Wave Accounting Connector - Free cloud accounting via GraphQL API.

Provides:
- Invoice management
- Transaction tracking
- Chart of accounts
- Financial reporting

API Documentation: https://developer.waveapps.com/hc/en-us/articles/360019968212
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

WAVE_GRAPHQL_URL = "https://gql.waveapps.com/graphql/public"


@ConnectorRegistry.register
class WaveConnector(BaseConnector):
    PROVIDER_ID = "wave"
    PROVIDER_NAME = "Wave"
    PROVIDER_DESCRIPTION = "Free cloud accounting platform with invoicing, transaction tracking, and financial reporting via GraphQL API."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developer.waveapps.com/hc/en-us/articles/360019968212"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._access_token = config.credentials.get("access_token", "")
        self._business_id = config.credentials.get("business_id", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=WAVE_GRAPHQL_URL,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                },
            )
        return self._client

    async def _graphql_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        client = await self._get_client()
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        response = await client.post("", json=payload)

        if response.status_code != 200:
            logger.error(f"Wave GraphQL error: {response.status_code} - {response.text[:200]}")
            return {}

        data = response.json()
        if "errors" in data:
            logger.error(f"Wave GraphQL errors: {data['errors']}")
        return data.get("data", {})

    async def authenticate(self) -> bool:
        if not self._access_token:
            logger.warning("Wave access token not provided")
            return False

        try:
            query = """
            query {
                businesses(page: 1, pageSize: 1) {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
            """
            data = await self._graphql_query(query)

            if data and "businesses" in data:
                businesses = data["businesses"].get("edges", [])
                if businesses and not self._business_id:
                    self._business_id = businesses[0].get("node", {}).get("id", "")
                self._authenticated = True
                logger.info("Wave authentication successful")
                return True
            else:
                logger.warning("Wave auth failed: could not fetch businesses")
                return False
        except Exception as e:
            logger.error(f"Wave authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            query = """
            query {
                businesses(page: 1, pageSize: 1) {
                    edges {
                        node {
                            id
                        }
                    }
                }
            }
            """
            data = await self._graphql_query(query)
            return bool(data and "businesses" in data)
        except Exception:
            return False

    async def get_invoices_raw(self, page: int = 1, page_size: int = 50) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            query = """
            query($businessId: ID!, $page: Int!, $pageSize: Int!) {
                business(id: $businessId) {
                    invoices(page: $page, pageSize: $pageSize) {
                        edges {
                            node {
                                id
                                createdAt
                                modifiedAt
                                pdfUrl
                                viewUrl
                                status
                                title
                                subhead
                                invoiceNumber
                                invoiceDate
                                poNumber
                                dueDate
                                amountDue {
                                    value
                                    currency { code }
                                }
                                amountPaid {
                                    value
                                    currency { code }
                                }
                                total {
                                    value
                                    currency { code }
                                }
                                customer {
                                    id
                                    name
                                    email
                                }
                            }
                        }
                    }
                }
            }
            """
            variables = {
                "businessId": self._business_id,
                "page": page,
                "pageSize": page_size,
            }
            data = await self._graphql_query(query, variables)
            business = data.get("business", {})
            invoices = business.get("invoices", {}).get("edges", [])
            return [edge.get("node", {}) for edge in invoices]

        except Exception as e:
            logger.error(f"Wave invoices fetch error: {e}")
            return []

    async def get_transactions_raw(self, page: int = 1, page_size: int = 50) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            query = """
            query($businessId: ID!, $page: Int!, $pageSize: Int!) {
                business(id: $businessId) {
                    transactions(page: $page, pageSize: $pageSize) {
                        edges {
                            node {
                                id
                                date
                                description
                                account {
                                    id
                                    name
                                    type { name value }
                                }
                                amount {
                                    value
                                    currency { code }
                                }
                                direction
                            }
                        }
                    }
                }
            }
            """
            variables = {
                "businessId": self._business_id,
                "page": page,
                "pageSize": page_size,
            }
            data = await self._graphql_query(query, variables)
            business = data.get("business", {})
            transactions = business.get("transactions", {}).get("edges", [])
            return [edge.get("node", {}) for edge in transactions]

        except Exception as e:
            logger.error(f"Wave transactions fetch error: {e}")
            return []

    async def get_accounts(self) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            query = """
            query($businessId: ID!) {
                business(id: $businessId) {
                    accounts(page: 1, pageSize: 100) {
                        edges {
                            node {
                                id
                                name
                                description
                                displayId
                                type { name value }
                                subtype { name value }
                                normalBalanceType
                                isArchived
                            }
                        }
                    }
                }
            }
            """
            variables = {"businessId": self._business_id}
            data = await self._graphql_query(query, variables)
            business = data.get("business", {})
            accounts = business.get("accounts", {}).get("edges", [])
            return [edge.get("node", {}) for edge in accounts]

        except Exception as e:
            logger.error(f"Wave accounts fetch error: {e}")
            return []

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        raw_invoices = await self.get_invoices_raw()
        invoices = []

        for inv in raw_invoices:
            total_obj = inv.get("total", {})
            total = float(total_obj.get("value", 0)) if total_obj else 0.0
            amount_due_obj = inv.get("amountDue", {})
            amount_due = float(amount_due_obj.get("value", 0)) if amount_due_obj else 0.0

            date_str = inv.get("invoiceDate", inv.get("createdAt", ""))
            try:
                if "T" in str(date_str):
                    date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                else:
                    date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
            except (ValueError, TypeError):
                date = datetime.now()

            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue

            due_date_str = inv.get("dueDate", "")
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d") if due_date_str else None
            except (ValueError, TypeError):
                due_date = None

            currency = "USD"
            if total_obj and "currency" in total_obj:
                currency = total_obj["currency"].get("code", "USD")

            customer = inv.get("customer", {}) or {}
            status_val = str(inv.get("status", "DRAFT")).lower()

            invoices.append(
                InvoiceRecord(
                    external_id=str(inv.get("id", "")),
                    date=date,
                    due_date=due_date,
                    customer_name=customer.get("name", ""),
                    amount=amount_due,
                    total=total,
                    currency=currency,
                    status=status_val,
                    metadata={
                        "invoice_number": inv.get("invoiceNumber", ""),
                        "source": "wave",
                    },
                )
            )

        return invoices

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        raw_transactions = await self.get_transactions_raw()
        entries = []

        for txn in raw_transactions:
            amount_obj = txn.get("amount", {})
            amount = float(amount_obj.get("value", 0)) if amount_obj else 0.0
            direction = txn.get("direction", "")

            date_str = txn.get("date", "")
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
            except (ValueError, TypeError):
                date = datetime.now()

            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue

            account = txn.get("account", {}) or {}
            account_type = account.get("type", {}) or {}

            entries.append(
                LedgerEntry(
                    external_id=str(txn.get("id", "")),
                    date=date,
                    account_code=str(account.get("id", "")),
                    account_name=account.get("name", "Unknown"),
                    debit=abs(amount) if direction == "DEBIT" else 0.0,
                    credit=abs(amount) if direction == "CREDIT" else 0.0,
                    description=txn.get("description", ""),
                    category=account_type.get("name", ""),
                    metadata={
                        "direction": direction,
                        "account_type": account_type.get("value", ""),
                        "source": "wave",
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
            "source_type": "connector_wave",
            "extraction_summary": "Synced from Wave Accounting",
        }

        if invoices:
            result["revenue"] = sum(inv.total for inv in invoices if inv.status == "paid")
            result["invoices_count"] = len(invoices)
            result["outstanding"] = sum(inv.amount for inv in invoices if inv.status != "paid")

        if ledger_entries:
            result["total_debits"] = sum(e.debit for e in ledger_entries)
            result["total_credits"] = sum(e.credit for e in ledger_entries)
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
                    errors=["Authentication failed - check access_token"],
                    sync_started=sync_started,
                )

            raw_invoices = await self.get_invoices_raw()
            raw_transactions = await self.get_transactions_raw()
            accounts = await self.get_accounts()
            invoices = await self.fetch_invoices()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(invoices=invoices, ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(raw_invoices) + len(raw_transactions) + len(accounts),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "invoices_count": len(raw_invoices),
                    "transactions_count": len(raw_transactions),
                    "accounts_count": len(accounts),
                },
            )

        except Exception as e:
            logger.error(f"Wave sync failed: {e}")
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
