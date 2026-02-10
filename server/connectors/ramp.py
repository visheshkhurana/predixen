"""
Ramp Expense Management Connector - Corporate expense and bill data.

Provides:
- Corporate card transactions
- Reimbursement records
- Bill payment data
- Spend analytics

API Documentation: https://docs.ramp.com/reference
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

BASE_URL = "https://demo-api.ramp.com/developer/v1"


@ConnectorRegistry.register
class RampConnector(BaseConnector):
    PROVIDER_ID = "ramp"
    PROVIDER_NAME = "Ramp"
    PROVIDER_DESCRIPTION = "Corporate expense management platform. Import card transactions, reimbursements, and bills for comprehensive spend tracking."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://docs.ramp.com/reference"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client_id = config.credentials.get("client_id", "")
        self._client_secret = config.credentials.get("client_secret", "")
        self._access_token = config.credentials.get("access_token", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._access_token:
            logger.warning("Ramp access token not provided")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/transactions", params={"page_size": 1})

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Ramp authentication successful")
                return True
            else:
                logger.warning(f"Ramp auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Ramp authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/transactions", params={"page_size": 1})
            return response.status_code == 200
        except Exception:
            return False

    async def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_transactions = []
            start = None

            while True:
                params: Dict[str, Any] = {"page_size": min(limit, 100)}
                if start:
                    params["start"] = start
                if start_date:
                    params["from_date"] = start_date.strftime("%Y-%m-%dT00:00:00Z")
                if end_date:
                    params["to_date"] = end_date.strftime("%Y-%m-%dT23:59:59Z")

                response = await client.get("/transactions", params=params)

                if response.status_code != 200:
                    logger.error(f"Ramp transactions error: {response.status_code}")
                    break

                data = response.json()
                items = data.get("data", [])
                all_transactions.extend(items)

                next_page = data.get("page", {}).get("next")
                if not next_page or len(all_transactions) >= limit:
                    break
                start = next_page

            return all_transactions

        except Exception as e:
            logger.error(f"Ramp transaction fetch error: {e}")
            return []

    async def get_reimbursements(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"page_size": min(limit, 100)}
            response = await client.get("/reimbursements", params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Ramp reimbursements fetch error: {e}")
            return []

    async def get_bills(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"page_size": min(limit, 100)}
            response = await client.get("/bills", params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Ramp bills fetch error: {e}")
            return []

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        transactions = await self.get_transactions(start_date, end_date)
        reimbursements = await self.get_reimbursements()
        entries = []

        for txn in transactions:
            amount = float(txn.get("amount", 0))
            txn_date_str = txn.get("user_transaction_time", "")
            try:
                txn_date = datetime.fromisoformat(txn_date_str.replace("Z", "+00:00")) if txn_date_str else datetime.now()
            except (ValueError, TypeError):
                txn_date = datetime.now()

            entries.append(
                LedgerEntry(
                    external_id=txn.get("id", ""),
                    date=txn_date,
                    account_code=txn.get("card_id", "ramp_card"),
                    account_name="Ramp Card",
                    debit=abs(amount) if amount > 0 else 0.0,
                    credit=abs(amount) if amount < 0 else 0.0,
                    description=txn.get("merchant_name") or txn.get("memo", ""),
                    category=txn.get("sk_category_name", "Uncategorized"),
                    metadata={
                        "merchant_name": txn.get("merchant_name"),
                        "card_holder_name": txn.get("card_holder", {}).get("full_name"),
                        "state": txn.get("state"),
                        "type": "card_transaction",
                    },
                )
            )

        for reimb in reimbursements:
            amount = float(reimb.get("amount", 0))
            reimb_date_str = reimb.get("created_at", "")
            try:
                reimb_date = datetime.fromisoformat(reimb_date_str.replace("Z", "+00:00")) if reimb_date_str else datetime.now()
            except (ValueError, TypeError):
                reimb_date = datetime.now()

            entries.append(
                LedgerEntry(
                    external_id=reimb.get("id", ""),
                    date=reimb_date,
                    account_code="ramp_reimbursement",
                    account_name="Ramp Reimbursement",
                    debit=abs(amount),
                    credit=0.0,
                    description=reimb.get("merchant_name") or reimb.get("memo", "Reimbursement"),
                    category="Reimbursement",
                    metadata={
                        "type": "reimbursement",
                        "user_name": reimb.get("user", {}).get("full_name"),
                        "status": reimb.get("status"),
                    },
                )
            )

        return entries

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        bills = await self.get_bills(limit=500)
        invoices = []

        for bill in bills:
            amount = float(bill.get("amount", 0))
            bill_date_str = bill.get("invoice_date") or bill.get("created_at", "")
            due_date_str = bill.get("due_date", "")

            try:
                bill_date = datetime.fromisoformat(bill_date_str.replace("Z", "+00:00")) if bill_date_str else datetime.now()
            except (ValueError, TypeError):
                bill_date = datetime.now()

            try:
                due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00")) if due_date_str else None
            except (ValueError, TypeError):
                due_date = None

            if start_date and bill_date < start_date:
                continue
            if end_date and bill_date > end_date:
                continue

            invoices.append(
                InvoiceRecord(
                    external_id=bill.get("id", ""),
                    date=bill_date,
                    due_date=due_date,
                    customer_name=bill.get("vendor_name", ""),
                    amount=amount,
                    total=amount,
                    currency=bill.get("currency", "USD"),
                    status=bill.get("payment_status", "pending"),
                    metadata={
                        "vendor_name": bill.get("vendor_name"),
                        "invoice_number": bill.get("invoice_number"),
                        "source": "ramp_bill",
                    },
                )
            )

        return invoices

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        result = {
            "source_type": "connector_ramp",
            "extraction_summary": "Synced from Ramp expense management",
        }

        if ledger_entries:
            total_spend = sum(e.debit for e in ledger_entries)
            total_credits = sum(e.credit for e in ledger_entries)
            result["total_spend"] = total_spend
            result["total_credits"] = total_credits
            result["transactions_count"] = len(ledger_entries)

            categories: Dict[str, float] = {}
            for entry in ledger_entries:
                if entry.category and entry.debit > 0:
                    categories[entry.category] = categories.get(entry.category, 0) + entry.debit
            result["expense_breakdown"] = categories

        if invoices:
            result["bills_total"] = sum(inv.total for inv in invoices)
            result["bills_count"] = len(invoices)

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

            transactions = await self.get_transactions()
            reimbursements = await self.get_reimbursements()
            bills = await self.get_bills()
            ledger = await self.fetch_ledger()
            invoices = await self.fetch_invoices()
            financials = self.map_to_financials(ledger_entries=ledger, invoices=invoices)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(transactions) + len(reimbursements) + len(bills),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "transactions_count": len(transactions),
                    "reimbursements_count": len(reimbursements),
                    "bills_count": len(bills),
                },
            )

        except Exception as e:
            logger.error(f"Ramp sync failed: {e}")
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
