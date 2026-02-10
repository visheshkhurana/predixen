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
        self._account_id = config.credentials.get("account_id", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            base_url = f"https://api.freshbooks.com/accounting/account/{self._account_id}"
            self._client = httpx.AsyncClient(
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
        if not self._access_token or not self._account_id:
            logger.warning("FreshBooks credentials incomplete - need access_token and account_id")
            return False

        try:
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
            amount = float(inv.get("amount", {}).get("amount", 0))
            total = float(inv.get("outstanding", {}).get("amount", 0)) or amount

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

            status_map = {"0": "draft", "1": "sent", "2": "viewed", "3": "paid", "4": "partial"}
            fb_status = str(inv.get("v3_status", inv.get("status", "0")))

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
                    status=status_map.get(fb_status, "pending"),
                    metadata={
                        "invoice_number": inv.get("invoice_number", ""),
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
            result["outstanding"] = sum(inv.total for inv in invoices if inv.status != "paid")

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
