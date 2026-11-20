"""
FreshBooks Accounting Connector - Cloud accounting and invoicing.

Provides:
- Invoice management and tracking
- Expense tracking and categorization
- Payment records
- Client management

API Documentation: https://www.freshbooks.com/api/start
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

FRESHBOOKS_TOKEN_URL = "https://api.freshbooks.com/auth/oauth/token"

# Invoice `v3_status` is a string (https://www.freshbooks.com/api/invoices).
V3_STATUS_MAP = {
    "created": "draft",
    "draft": "draft",
    "sent": "sent",
    "viewed": "viewed",
    "overdue": "overdue",
    "failed": "pending",
    "retry": "pending",
    "success": "paid",
    "autopaid": "paid",
    "paid": "paid",
    "partial": "partial",
    "disputed": "disputed",
    "resolved": "pending",
    "deposit-partial": "partial",
    "deposit-paid": "partial",
    "declined": "voided",
    "pending": "pending",
}
# The older numeric `status` field: 0 disputed, 1 draft, 2 sent, 3 viewed,
# 4 paid, 5 auto-paid, 6 retry, 7 failed, 8 partial.
NUMERIC_STATUS_MAP = {
    "0": "disputed", "1": "draft", "2": "sent", "3": "viewed", "4": "paid",
    "5": "paid", "6": "pending", "7": "pending", "8": "partial",
}


def freshbooks_invoice_status(inv: Dict[str, Any]) -> str:
    v3 = inv.get("v3_status")
    if isinstance(v3, str) and v3.strip():
        return V3_STATUS_MAP.get(v3.strip().lower(), "pending")
    status = inv.get("status")
    if status is not None:
        return NUMERIC_STATUS_MAP.get(str(status), "pending")
    return "pending"


def _money(value: Any) -> float:
    if isinstance(value, dict):
        value = value.get("amount", 0)
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


@ConnectorRegistry.register
class FreshBooksConnector(BaseConnector):
    PROVIDER_ID = "freshbooks"
    PROVIDER_NAME = "FreshBooks"
    PROVIDER_DESCRIPTION = "Cloud accounting platform for invoicing, expenses, and payments. Import invoices, expense reports, and payment data."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://www.freshbooks.com/api/start"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._access_token = config.credentials.get("access_token", "")
        self._refresh_token = config.credentials.get("refresh_token", "")
        self._client_id = config.credentials.get("client_id", "")
        self._client_secret = config.credentials.get("client_secret", "")
        self._redirect_uri = config.credentials.get("redirect_uri", "")
        self._account_id = config.credentials.get("account_id", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._refresh_attempted = False

    async def _refresh_access_token(self) -> bool:
        """
        Exchange the refresh token for a new bearer token.

        FreshBooks refresh tokens are one-time-use: a successful refresh
        invalidates the old one, so the new refresh_token is kept on
        `self._refresh_token`, where `BaseConnector.rotated_credentials`
        picks it up to be saved.
        """
        if self._refresh_attempted:
            return False
        if not (self._refresh_token and self._client_id and self._client_secret):
            return False
        self._refresh_attempted = True
        body = {
            "grant_type": "refresh_token",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
        }
        if self._redirect_uri:
            body["redirect_uri"] = self._redirect_uri
        try:
            async with http_client(timeout=30.0) as client:
                response = await client.post(
                    FRESHBOOKS_TOKEN_URL,
                    json=body,
                    headers={"Content-Type": "application/json", "Api-Version": "alpha"},
                )
            if response.status_code != 200:
                logger.warning(f"FreshBooks token refresh failed: {response.status_code}")
                return False
            data = response.json()
            if not data.get("access_token"):
                return False
            self._access_token = data["access_token"]
            if data.get("refresh_token"):
                self._refresh_token = data["refresh_token"]
            if self._client:
                await self._client.aclose()
                self._client = None
            logger.info("FreshBooks token refreshed")
            return True
        except Exception as e:
            logger.error(f"FreshBooks token refresh error: {e}")
            return False

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            base_url = f"https://api.freshbooks.com/accounting/account/{self._account_id}"
            self._client = http_client(
                base_url=base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                    "Api-Version": "alpha",
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._account_id or not (self._access_token or self._refresh_token):
            logger.warning("FreshBooks credentials incomplete - need access_token and account_id")
            return False

        try:
            if not self._access_token and not await self._refresh_access_token():
                return False
            client = await self._get_client()
            response = await client.get("/users/clients?per_page=1")

            if response.status_code == 401 and await self._refresh_access_token():
                client = await self._get_client()
                response = await client.get("/users/clients?per_page=1")

            if response.status_code == 200:
                self._authenticated = True
                logger.info("FreshBooks authentication successful")
                return True
            else:
                logger.warning(f"FreshBooks auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"FreshBooks authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/users/clients?per_page=1")
            return response.status_code == 200
        except Exception:
            return False

    async def get_invoices(
        self,
        page: int = 1,
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_invoices = []
            current_page = page

            while True:
                params = {"page": current_page, "per_page": per_page}
                response = await client.get("/invoices/invoices", params=params)

                if response.status_code != 200:
                    logger.error(f"FreshBooks invoices error: {response.status_code}")
                    break

                data = response.json()
                result = data.get("response", {}).get("result", {})
                invoices = result.get("invoices", [])
                all_invoices.extend(invoices)

                total_pages = result.get("pages", 1)
                if current_page >= total_pages:
                    break
                current_page += 1

            return all_invoices

        except Exception as e:
            logger.error(f"FreshBooks invoices fetch error: {e}")
            return []

    async def get_expenses(
        self,
        page: int = 1,
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_expenses = []
            current_page = page

            while True:
                params = {"page": current_page, "per_page": per_page}
                response = await client.get("/expenses/expenses", params=params)

                if response.status_code != 200:
                    logger.error(f"FreshBooks expenses error: {response.status_code}")
                    break

                data = response.json()
                result = data.get("response", {}).get("result", {})
                expenses = result.get("expenses", [])
                all_expenses.extend(expenses)

                total_pages = result.get("pages", 1)
                if current_page >= total_pages:
                    break
                current_page += 1

            return all_expenses

        except Exception as e:
            logger.error(f"FreshBooks expenses fetch error: {e}")
            return []

    async def get_payments(self, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params = {"page": page, "per_page": per_page}
            response = await client.get("/payments/payments", params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get("response", {}).get("result", {}).get("payments", [])
            return []
        except Exception as e:
            logger.error(f"FreshBooks payments fetch error: {e}")
            return []

    async def get_clients(self, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params = {"page": page, "per_page": per_page}
            response = await client.get("/users/clients", params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get("response", {}).get("result", {}).get("clients", [])
            return []
        except Exception as e:
            logger.error(f"FreshBooks clients fetch error: {e}")
            return []

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        raw_invoices = await self.get_invoices()
        invoices = []

        for inv in raw_invoices:
            amount = _money(inv.get("amount"))
            outstanding = _money(inv.get("outstanding"))
            total = amount

            date_str = inv.get("create_date", "")
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
            except (ValueError, TypeError):
                date = datetime.now()

            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue

            due_date_str = inv.get("due_date", "")
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d") if due_date_str else None
            except (ValueError, TypeError):
                due_date = None


            invoices.append(
                InvoiceRecord(
                    external_id=str(inv.get("invoiceid", inv.get("id", ""))),
                    date=date,
                    due_date=due_date,
                    customer_name=inv.get("current_organization", inv.get("fname", "")),
                    amount=amount,
                    tax=float(inv.get("tax_amount", {}).get("amount", 0) if isinstance(inv.get("tax_amount"), dict) else inv.get("tax_amount", 0)),
                    total=total,
                    currency=inv.get("currency_code", "USD"),
                    status=freshbooks_invoice_status(inv),
                    metadata={
                        "invoice_number": inv.get("invoice_number", ""),
                        "outstanding": outstanding,
                        "v3_status": inv.get("v3_status"),
                        "source": "freshbooks",
                    },
                )
            )

        return invoices

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        expenses = await self.get_expenses()
        entries = []

        for exp in expenses:
            amount = float(exp.get("amount", {}).get("amount", 0) if isinstance(exp.get("amount"), dict) else exp.get("amount", 0))
            date_str = exp.get("date", "")
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
            except (ValueError, TypeError):
                date = datetime.now()

            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue

            entries.append(
                LedgerEntry(
                    external_id=str(exp.get("expenseid", exp.get("id", ""))),
                    date=date,
                    account_code=str(exp.get("categoryid", "")),
                    account_name=exp.get("category_name", exp.get("account_name", "Uncategorized")),
                    debit=amount,
                    credit=0.0,
                    description=exp.get("notes", exp.get("vendor", "")),
                    category=exp.get("category_name", "Expense"),
                    metadata={
                        "vendor": exp.get("vendor", ""),
                        "source": "freshbooks",
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
            "source_type": "connector_freshbooks",
            "extraction_summary": "Synced from FreshBooks Accounting",
        }

        if invoices:
            result["revenue"] = sum(inv.total for inv in invoices if inv.status == "paid")
            result["invoices_count"] = len(invoices)
            result["outstanding"] = sum(
                float(inv.metadata.get("outstanding", inv.total) or 0) for inv in invoices if inv.status != "paid"
            )

        if ledger_entries:
            result["total_expenses"] = sum(e.debit for e in ledger_entries)
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
                    errors=["Authentication failed - check access_token and account_id"],
                    sync_started=sync_started,
                )

            raw_invoices = await self.get_invoices()
            expenses = await self.get_expenses()
            payments = await self.get_payments()
            clients = await self.get_clients()
            invoices = await self.fetch_invoices()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(invoices=invoices, ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(raw_invoices) + len(expenses) + len(payments) + len(clients),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "invoices_count": len(raw_invoices),
                    "expenses_count": len(expenses),
                    "payments_count": len(payments),
                    "clients_count": len(clients),
                },
            )

        except Exception as e:
            logger.error(f"FreshBooks sync failed: {e}")
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
