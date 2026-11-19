"""
Xero Connector - Accounting and financial reporting.

Provides:
- Invoice data (accounts receivable/payable)
- Profit & Loss reports
- Balance Sheet reports
- Contact (customer/supplier) records
- Bank transactions and reconciliation

API Documentation: https://developer.xero.com/documentation/api/accounting/overview
"""

import httpx
import logging
import re
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

XERO_API_URL = "https://api.xero.com/api.xro/2.0"
XERO_IDENTITY_URL = "https://identity.xero.com"
XERO_TOKEN_URL = "https://identity.xero.com/connect/token"
XERO_MAX_PAGES = 50  # 100 rows a page


def parse_xero_date(value: Any) -> Optional[datetime]:
    """Parse a Xero date: ISO ("2024-05-01T00:00:00") or MS-JSON ("/Date(1714521600000+0000)/")."""
    if not value or not isinstance(value, str):
        return None
    m = re.match(r"^/Date\((-?\d+)([+-]\d{4})?\)/$", value.strip())
    if m:
        return datetime.utcfromtimestamp(int(m.group(1)) / 1000)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _xero_cell_number(value: Any) -> Any:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return value


def parse_xero_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten a Xero report (ProfitAndLoss / BalanceSheet) into sections and totals.

    Xero nests every total as a `SummaryRow` *inside* a `Section` row, and the
    headline figures ("Gross Profit", "Net Profit") sit in Sections with an empty
    Title. Account lines are `Row`s, and a Section can contain nested Sections.
    The first value column is read (the current period).
    """
    result: Dict[str, Any] = {
        "report_name": report.get("ReportName", ""),
        "report_date": report.get("ReportDate", ""),
        "sections": {},
        "totals": {},
    }

    def walk(rows: List[Dict[str, Any]], section_data: Optional[Dict[str, Any]]) -> None:
        for row in rows or []:
            row_type = row.get("RowType")
            if row_type == "Section":
                title = row.get("Title") or ""
                if title:
                    target = result["sections"].setdefault(title, {})
                else:
                    target = section_data
                walk(row.get("Rows", []), target)
                continue
            cells = row.get("Cells", [])
            if len(cells) < 2:
                continue
            label = cells[0].get("Value", "")
            value = _xero_cell_number(cells[1].get("Value", "0"))
            if row_type == "SummaryRow":
                if label:
                    result["totals"][label] = value
                    # Kept at the top level too, where callers already read it.
                    result[label] = value
                if section_data is not None:
                    section_data["Total"] = value
            elif row_type == "Row" and section_data is not None and label:
                section_data[label] = value

    walk(report.get("Rows", []), None)
    return result


@ConnectorRegistry.register
class XeroConnector(BaseConnector):
    PROVIDER_ID = "xero"
    PROVIDER_NAME = "Xero"
    PROVIDER_DESCRIPTION = "Cloud accounting platform. Import invoices, P&L, balance sheet, contacts, and bank transactions."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developer.xero.com/documentation/api/accounting/overview"

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
        self._tenant_id = config.credentials.get("tenant_id", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            headers: Dict[str, str] = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self._access_token}",
            }
            if self._tenant_id:
                headers["Xero-Tenant-Id"] = self._tenant_id

            self._client = httpx.AsyncClient(
                base_url=XERO_API_URL,
                timeout=30.0,
                headers=headers,
            )
        return self._client

    async def _refresh_access_token(self) -> bool:
        if not all([self._client_id, self._client_secret, self._refresh_token]):
            return False

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    XERO_TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self._refresh_token,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if response.status_code == 200:
                    data = response.json()
                    self._access_token = data.get("access_token", "")
                    self._refresh_token = data.get("refresh_token", self._refresh_token)
                    if self._client:
                        self._client.headers["Authorization"] = f"Bearer {self._access_token}"
                    logger.info("Xero token refreshed successfully")
                    return True
                return False
        except Exception as e:
            logger.error(f"Xero token refresh error: {e}")
            return False

    async def _get_tenant_id(self) -> bool:
        if self._tenant_id:
            return True

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.xero.com/connections",
                    headers={"Authorization": f"Bearer {self._access_token}"},
                )
                if response.status_code == 200:
                    connections = response.json()
                    if connections:
                        self._tenant_id = connections[0].get("tenantId", "")
                        if self._client:
                            self._client.headers["Xero-Tenant-Id"] = self._tenant_id
                        return True
                return False
        except Exception as e:
            logger.error(f"Xero tenant ID fetch error: {e}")
            return False

    async def authenticate(self) -> bool:
        if not self._access_token:
            logger.warning("Xero access token not provided")
            return False

        try:
            if not self._tenant_id:
                if not await self._get_tenant_id():
                    logger.warning("Could not determine Xero tenant ID")
                    return False

            client = await self._get_client()
            response = await client.get("/Organisation")

            if response.status_code == 200:
                self._authenticated = True
                data = response.json()
                orgs = data.get("Organisations", [])
                if orgs:
                    org_name = orgs[0].get("Name", "Unknown")
                    logger.info(f"Xero authentication successful, org: {org_name}")
                return True
            elif response.status_code == 401:
                logger.info("Xero token expired, attempting refresh")
                if await self._refresh_access_token():
                    if self._client:
                        await self._client.aclose()
                        self._client = None
                    return await self.authenticate()
                return False
            else:
                logger.warning(f"Xero auth failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Xero authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            if not self._tenant_id:
                await self._get_tenant_id()
            client = await self._get_client()
            response = await client.get("/Organisation")
            return response.status_code == 200
        except Exception:
            return False

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        invoices = []
        try:
            client = await self._get_client()
            page = 1

            while True:
                params: Dict[str, Any] = {"page": page}
                where_clauses = []

                if start_date:
                    where_clauses.append(f'Date >= DateTime({start_date.year},{start_date.month},{start_date.day})')
                if end_date:
                    where_clauses.append(f'Date <= DateTime({end_date.year},{end_date.month},{end_date.day})')

                if where_clauses:
                    params["where"] = " AND ".join(where_clauses)

                response = await client.get("/Invoices", params=params)

                if response.status_code != 200:
                    logger.error(f"Xero invoices error: {response.status_code}")
                    break

                data = response.json()
                inv_list = data.get("Invoices", [])

                if not inv_list:
                    break

                for inv in inv_list:
                    inv_date_str = inv.get("DateString", "")
                    due_date_str = inv.get("DueDateString", "")

                    try:
                        inv_date = datetime.fromisoformat(inv_date_str) if inv_date_str else datetime.now()
                    except (ValueError, TypeError):
                        inv_date = datetime.now()

                    try:
                        due_date = datetime.fromisoformat(due_date_str) if due_date_str else None
                    except (ValueError, TypeError):
                        due_date = None

                    contact = inv.get("Contact", {})
                    status_map = {
                        "DRAFT": "draft",
                        "SUBMITTED": "pending",
                        "AUTHORISED": "pending",
                        "PAID": "paid",
                        "VOIDED": "voided",
                        "DELETED": "deleted",
                    }

                    invoices.append(
                        InvoiceRecord(
                            external_id=inv.get("InvoiceID", ""),
                            date=inv_date,
                            due_date=due_date,
                            customer_name=contact.get("Name", ""),
                            amount=float(inv.get("SubTotal", 0)),
                            tax=float(inv.get("TotalTax", 0)),
                            total=float(inv.get("Total", 0)),
                            currency=inv.get("CurrencyCode", "USD"),
                            status=status_map.get(inv.get("Status", ""), "unknown"),
                            line_items=[
                                {
                                    "description": li.get("Description", ""),
                                    "quantity": li.get("Quantity", 0),
                                    "unit_amount": li.get("UnitAmount", 0),
                                    "amount": li.get("LineAmount", 0),
                                    "account_code": li.get("AccountCode", ""),
                                }
                                for li in inv.get("LineItems", [])
                            ],
                            metadata={
                                "xero_invoice_number": inv.get("InvoiceNumber", ""),
                                "xero_type": inv.get("Type", ""),
                                "xero_status": inv.get("Status", ""),
                                "amount_due": float(inv.get("AmountDue", 0)),
                                "amount_paid": float(inv.get("AmountPaid", 0)),
                            },
                        )
                    )

                if len(inv_list) < 100:
                    break
                page += 1

        except Exception as e:
            logger.error(f"Error fetching Xero invoices: {e}")

        return invoices

    async def _account_map(self, client: httpx.AsyncClient) -> Dict[str, Dict[str, str]]:
        """AccountCode -> {name, type}, from GET /Accounts (accounting.settings.read)."""
        try:
            response = await client.get("/Accounts")
            if response.status_code != 200:
                return {}
            return {
                a.get("Code", ""): {"name": a.get("Name", ""), "type": a.get("Type", "")}
                for a in response.json().get("Accounts", [])
                if a.get("Code")
            }
        except Exception as e:
            logger.warning(f"Xero accounts fetch error: {e}")
            return {}

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        """
        Ledger lines from /BankTransactions.

        /Journals is not used: it needs the restricted `accounting.journals.read`
        scope and accepts no `where` filter (only offset / If-Modified-Since), so
        a date-filtered call to it was ignored or refused. BankTransactions is
        covered by the standard transactions/banktransactions scopes, takes a
        `where` filter and pages 100 at a time.
        """
        if not self._authenticated:
            if not await self.authenticate():
                return []

        entries: List[LedgerEntry] = []
        try:
            client = await self._get_client()
            accounts = await self._account_map(client)
            where_clauses = []
            if start_date:
                where_clauses.append(f'Date >= DateTime({start_date.year},{start_date.month},{start_date.day})')
            if end_date:
                where_clauses.append(f'Date <= DateTime({end_date.year},{end_date.month},{end_date.day})')

            page = 1
            while True:
                params: Dict[str, Any] = {"page": page}
                if where_clauses:
                    params["where"] = " AND ".join(where_clauses)
                response = await client.get("/BankTransactions", params=params)
                if response.status_code != 200:
                    logger.error(f"Xero bank transactions error: {response.status_code}")
                    break

                txns = response.json().get("BankTransactions", [])
                if not txns:
                    break

                for txn in txns:
                    if txn.get("Status") == "DELETED":
                        continue
                    txn_date = (
                        parse_xero_date(txn.get("DateString"))
                        or parse_xero_date(txn.get("Date"))
                        or datetime.now()
                    )
                    is_spend = str(txn.get("Type", "")).startswith("SPEND")
                    for idx, line in enumerate(txn.get("LineItems", []) or []):
                        try:
                            amount = abs(float(line.get("LineAmount", 0) or 0))
                        except (ValueError, TypeError):
                            amount = 0.0
                        code = line.get("AccountCode", "") or ""
                        acct = accounts.get(code, {})
                        entries.append(
                            LedgerEntry(
                                external_id=f"{txn.get('BankTransactionID', '')}_{line.get('LineItemID') or idx}",
                                date=txn_date,
                                account_code=code,
                                account_name=acct.get("name", ""),
                                debit=amount if is_spend else 0.0,
                                credit=0.0 if is_spend else amount,
                                description=line.get("Description") or (txn.get("Contact") or {}).get("Name", ""),
                                category=acct.get("type") or None,
                                metadata={
                                    "xero_bank_transaction_type": txn.get("Type"),
                                    "xero_reference": txn.get("Reference"),
                                    "contact": (txn.get("Contact") or {}).get("Name"),
                                    "bank_account": (txn.get("BankAccount") or {}).get("Name"),
                                    "tax_type": line.get("TaxType", ""),
                                },
                            )
                        )

                if len(txns) < 100 or page >= XERO_MAX_PAGES:
                    break
                page += 1

        except Exception as e:
            logger.error(f"Error fetching Xero bank transactions: {e}")

        return entries

    async def get_profit_and_loss(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        periods: int = 1,
    ) -> Dict[str, Any]:
        if not self._authenticated:
            if not await self.authenticate():
                return {}

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"periods": periods, "timeframe": "MONTH"}

            if from_date:
                params["fromDate"] = from_date.strftime("%Y-%m-%d")
            if to_date:
                params["toDate"] = to_date.strftime("%Y-%m-%d")

            response = await client.get("/Reports/ProfitAndLoss", params=params)

            if response.status_code != 200:
                logger.error(f"Xero P&L error: {response.status_code}")
                return {}

            data = response.json()
            reports = data.get("Reports", [])
            if not reports:
                return {}

            return parse_xero_report(reports[0])

        except Exception as e:
            logger.error(f"Xero P&L fetch error: {e}")
            return {}

    async def get_balance_sheet(
        self,
        date: Optional[datetime] = None,
        periods: int = 1,
    ) -> Dict[str, Any]:
        if not self._authenticated:
            if not await self.authenticate():
                return {}

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"periods": periods, "timeframe": "MONTH"}

            if date:
                params["date"] = date.strftime("%Y-%m-%d")

            response = await client.get("/Reports/BalanceSheet", params=params)

            if response.status_code != 200:
                logger.error(f"Xero Balance Sheet error: {response.status_code}")
                return {}

            data = response.json()
            reports = data.get("Reports", [])
            if not reports:
                return {}

            return parse_xero_report(reports[0])

        except Exception as e:
            logger.error(f"Xero Balance Sheet fetch error: {e}")
            return {}

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        result = {
            "source_type": "connector_xero",
            "extraction_summary": "Synced from Xero",
        }

        if invoices:
            receivable = [i for i in invoices if i.metadata.get("xero_type") == "ACCREC"]
            payable = [i for i in invoices if i.metadata.get("xero_type") == "ACCPAY"]

            result["revenue"] = sum(i.total for i in receivable if i.status == "paid")
            result["accounts_receivable"] = sum(
                float(i.metadata.get("amount_due", 0)) for i in receivable
            )
            result["accounts_payable"] = sum(
                float(i.metadata.get("amount_due", 0)) for i in payable
            )
            result["invoices_count"] = len(invoices)

        if ledger_entries:
            result["journal_entries_count"] = len(ledger_entries)
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
                    errors=["Authentication failed - check OAuth credentials and tenant_id"],
                    sync_started=sync_started,
                )

            invoices = await self.fetch_invoices()
            ledger = await self.fetch_ledger()
            pnl = await self.get_profit_and_loss()
            balance_sheet = await self.get_balance_sheet()
            financials = self.map_to_financials(invoices=invoices, ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(invoices) + len(ledger),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "invoices_count": len(invoices),
                    "journal_entries_count": len(ledger),
                    "profit_and_loss": pnl,
                    "balance_sheet": balance_sheet,
                },
            )

        except Exception as e:
            logger.error(f"Xero sync failed: {e}")
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
