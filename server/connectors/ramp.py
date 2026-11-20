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
from server.services.software_spend import card_software_months

logger = logging.getLogger(__name__)

RAMP_HOSTS = {
    "production": "https://api.ramp.com",
    "sandbox": "https://demo-api.ramp.com",
}
RAMP_SCOPES = "transactions:read reimbursements:read bills:read"
# Ramp's standard page_size is 2..100 (https://docs.ramp.com/developer-api/v1/pagination).
RAMP_PAGE_SIZE = 100


def ramp_money(value: Any) -> float:
    """
    A Ramp amount as a float in major units.

    Legacy fields (`amount` on a transaction) are plain numbers in dollars.
    Newer ones are objects in the currency's smallest unit: CurrencyAmount
    {amount, currency_code, minor_unit_conversion_rate} on bills, and
    {value, currency, minor_unit_conversion_rate} on reimbursements.
    """
    if value is None:
        return 0.0
    if isinstance(value, dict):
        raw = value.get("amount", value.get("value", 0))
        rate = value.get("minor_unit_conversion_rate") or 100
        try:
            return float(raw or 0) / float(rate)
        except (ValueError, TypeError, ZeroDivisionError):
            return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _ramp_date(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


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
        env = str(config.settings.get("environment") or "production").lower()
        host = RAMP_HOSTS.get(env, RAMP_HOSTS["production"])
        self._host = host
        self._base_url = f"{host}/developer/v1"
        self._client: Optional[httpx.AsyncClient] = None
        self._token_fetched = False

    async def _fetch_token(self) -> bool:
        """
        Client-credentials token from POST /developer/v1/token (HTTP Basic auth).
        Tokens last 10 days and come with no refresh token, so a new one is
        requested when the stored one is missing or rejected.
        """
        if self._token_fetched or not (self._client_id and self._client_secret):
            return False
        self._token_fetched = True
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/token",
                    auth=(self._client_id, self._client_secret),
                    data={"grant_type": "client_credentials", "scope": RAMP_SCOPES},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            if response.status_code != 200:
                logger.warning(f"Ramp token request failed: {response.status_code}")
                return False
            token = response.json().get("access_token")
            if not token:
                return False
            self._access_token = token
            if self._client:
                await self._client.aclose()
                self._client = None
            return True
        except Exception as e:
            logger.error(f"Ramp token request error: {e}")
            return False

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=30.0,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._access_token and not await self._fetch_token():
            logger.warning("Ramp credentials not provided (client_id/client_secret or access_token)")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/transactions", params={"page_size": 2})
            if response.status_code == 401 and await self._fetch_token():
                client = await self._get_client()
                response = await client.get("/transactions", params={"page_size": 2})

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Ramp authentication successful")
                return True
            logger.warning(f"Ramp auth failed: {response.status_code} - {response.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"Ramp authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/transactions", params={"page_size": 2})
            return response.status_code == 200
        except Exception:
            return False

    async def _list(self, path: str, params: Optional[Dict[str, Any]] = None, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Follow Ramp cursor pagination. `page.next` is the complete URL of the
        next page (cursor and filters included), so it is requested as-is.
        """
        if not self._authenticated:
            if not await self.authenticate():
                return []
        items: List[Dict[str, Any]] = []
        try:
            client = await self._get_client()
            query = dict(params or {})
            query["page_size"] = max(2, min(RAMP_PAGE_SIZE, limit))
            response = await client.get(path, params=query)
            seen = set()
            while True:
                if response.status_code != 200:
                    logger.error(f"Ramp {path} error: {response.status_code}")
                    break
                data = response.json()
                items.extend(data.get("data", []) or [])
                next_url = (data.get("page") or {}).get("next")
                if not next_url or len(items) >= limit or next_url in seen:
                    break
                seen.add(next_url)
                if not str(next_url).startswith(self._host + "/"):
                    logger.warning("Ramp page.next points off-host; stopping pagination")
                    break
                response = await client.get(next_url)
        except Exception as e:
            logger.error(f"Ramp {path} fetch error: {e}")
        return items[:limit]

    async def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if start_date:
            params["from_date"] = start_date.strftime("%Y-%m-%dT00:00:00Z")
        if end_date:
            params["to_date"] = end_date.strftime("%Y-%m-%dT23:59:59Z")
        return await self._list("/transactions", params, limit)

    async def get_reimbursements(self, limit: int = 500) -> List[Dict[str, Any]]:
        return await self._list("/reimbursements", None, limit)

    async def get_bills(self, limit: int = 500) -> List[Dict[str, Any]]:
        return await self._list("/bills", None, limit)

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        transactions = await self.get_transactions(start_date, end_date)
        reimbursements = await self.get_reimbursements()
        entries = []

        for txn in transactions:
            amount = ramp_money(txn["amount"]) if txn.get("amount") is not None else ramp_money(txn.get("entity_amount"))
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
                        "card_holder_name": (txn.get("card_holder") or {}).get("full_name"),
                        "state": txn.get("state"),
                        "type": "card_transaction",
                    },
                )
            )

        for reimb in reimbursements:
            amount = ramp_money(reimb["amount"]) if reimb.get("amount") is not None else ramp_money(reimb.get("entity_amount"))
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
                    description=reimb.get("merchant") or reimb.get("merchant_name") or reimb.get("memo") or "Reimbursement",
                    category="Reimbursement",
                    metadata={
                        "type": "reimbursement",
                        "user_name": (reimb.get("user") or {}).get("full_name"),
                        "status": reimb.get("state") or reimb.get("status"),
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
            amount_field = bill.get("amount")
            amount = ramp_money(amount_field)
            currency = (
                amount_field.get("currency_code") if isinstance(amount_field, dict) else None
            ) or bill.get("currency") or "USD"
            bill_date = (
                _ramp_date(bill.get("issued_at"))
                or _ramp_date(bill.get("invoice_date"))
                or _ramp_date(bill.get("created_at"))
                or datetime.now()
            )
            due_date = _ramp_date(bill.get("due_at")) or _ramp_date(bill.get("due_date"))

            if start_date and bill_date < start_date:
                continue
            if end_date and bill_date > end_date:
                continue

            vendor = bill.get("vendor") or {}
            vendor_name = (vendor.get("name") if isinstance(vendor, dict) else None) or bill.get("vendor_name", "")
            raw_status = str(bill.get("status") or bill.get("payment_status") or "").upper()
            status = {"PAID": "paid", "OPEN": "pending"}.get(raw_status, raw_status.lower() or "pending")

            invoices.append(
                InvoiceRecord(
                    external_id=bill.get("id", ""),
                    date=bill_date,
                    due_date=due_date,
                    customer_name=vendor_name,
                    amount=amount,
                    total=amount,
                    currency=currency,
                    status=status,
                    metadata={
                        "vendor_name": vendor_name,
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
                    "software_spend": card_software_months(ledger, default_currency="USD"),
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
