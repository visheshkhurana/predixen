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
from .http import http_client
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
WAVE_TOKEN_URL = "https://api.waveapps.com/oauth2/token/"


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
        # Set by "Connect with Wave": Wave access tokens expire (expires_in),
        # so without these a connection stopped working after the first token.
        self._refresh_token = config.credentials.get("refresh_token", "")
        self._client_id = config.credentials.get("client_id", "")
        self._client_secret = config.credentials.get("client_secret", "")
        self._refresh_attempted = False
        self.auth_error: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def _refresh_access_token(self) -> bool:
        """POST /oauth2/token/ with grant_type=refresh_token (form body).
        Wave rotates the refresh token; rotated_credentials() saves it.
        A 403 here means the business has no Pro/Advisor subscription, which
        Wave requires for third-party apps."""
        if self._refresh_attempted or not (self._refresh_token and self._client_id and self._client_secret):
            return False
        self._refresh_attempted = True
        try:
            async with http_client(timeout=30.0) as client:
                res = await client.post(WAVE_TOKEN_URL, data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                })
            if res.status_code == 403:
                self.auth_error = ("Wave only lets outside apps read businesses on a Pro or "
                                   "Wave Advisor subscription. Upgrade the business in Wave, then reconnect.")
                return False
            data = res.json() if res.status_code == 200 else {}
            if not data.get("access_token"):
                logger.warning(f"Wave token refresh failed: {res.status_code}")
                return False
            self._access_token = data["access_token"]
            self._refresh_token = data.get("refresh_token", self._refresh_token)
            if self._client:
                await self._client.aclose()
                self._client = None
            return True
        except Exception as e:
            logger.error(f"Wave token refresh error: {e}")
            return False

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = http_client(
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
        if response.status_code == 401 and await self._refresh_access_token():
            client = await self._get_client()
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

    async def get_invoices_raw(self, page: int = 1, page_size: int = 50, max_pages: int = 100) -> List[Dict[str, Any]]:
        """All invoices, following `pageInfo.totalPages` (offset pagination)."""
        if not self._authenticated:
            if not await self.authenticate():
                return []

        query = """
        query($businessId: ID!, $page: Int!, $pageSize: Int!) {
            business(id: $businessId) {
                invoices(page: $page, pageSize: $pageSize) {
                    pageInfo { currentPage totalPages totalCount }
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
                            amountDue { value currency { code } }
                            amountPaid { value currency { code } }
                            total { value currency { code } }
                            customer { id name email }
                        }
                    }
                }
            }
        }
        """
        nodes: List[Dict[str, Any]] = []
        try:
            current = page
            for _ in range(max_pages):
                data = await self._graphql_query(query, {
                    "businessId": self._business_id,
                    "page": current,
                    "pageSize": page_size,
                })
                conn = (data.get("business") or {}).get("invoices") or {}
                edges = conn.get("edges") or []
                nodes.extend(edge.get("node", {}) for edge in edges)
                total_pages = (conn.get("pageInfo") or {}).get("totalPages") or current
                if not edges or current >= total_pages:
                    break
                current += 1
        except Exception as e:
            logger.error(f"Wave invoices fetch error: {e}")
        return nodes

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
                        "amount_paid": float((inv.get("amountPaid") or {}).get("value", 0) or 0),
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
        """
        Ledger lines derived from invoices: the amount paid on each invoice.

        Wave's public GraphQL schema has no transaction listing (`Business`
        exposes invoices, customers, accounts, vendors and products, but no
        `transactions` field; transactions can only be created), so the old
        `business.transactions` query failed validation on every sync.
        """
        invoices = await self.fetch_invoices(start_date, end_date)
        entries: List[LedgerEntry] = []
        for inv in invoices:
            paid = float(inv.metadata.get("amount_paid", 0) or 0)
            if paid <= 0:
                continue
            entries.append(
                LedgerEntry(
                    external_id=f"{inv.external_id}_paid",
                    date=inv.date,
                    account_code="wave_invoice_payments",
                    account_name="Invoice payments",
                    debit=0.0,
                    credit=paid,
                    description=f"Payments on invoice {inv.metadata.get('invoice_number', '')}".strip(),
                    category="Sales",
                    metadata={"source": "wave_invoice", "customer": inv.customer_name},
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
            accounts = await self.get_accounts()
            invoices = await self.fetch_invoices()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(invoices=invoices, ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(raw_invoices) + len(accounts),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "invoices_count": len(raw_invoices),
                    "transactions_count": len(ledger),
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
