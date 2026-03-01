"""
QuickBooks Online connector for accounting and financial data integration.

Uses the Intuit QuickBooks Online Accounting API v3.
Provides:
- Profit & Loss reports (revenue, COGS, expenses, net income)
- Balance Sheet reports (assets, liabilities, equity, cash)
- Cash Flow statements
- Invoice data with line items
- General ledger / journal entries
- Employee list (if QuickBooks Payroll enabled)
- Payroll cost summaries

API Documentation: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/account
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import httpx
import base64

from .base import (
    BaseConnector,
    ConnectorConfig,
    ProviderCategory,
    AuthType,
    SyncResult,
    InvoiceRecord,
    LedgerEntry,
    EmployeeRecord,
    PayrollRunRecord,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

QB_OAUTH_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

QB_ENVIRONMENTS = {
    "sandbox": "https://sandbox-quickbooks.api.intuit.com/v3",
    "production": "https://quickbooks.api.intuit.com/v3",
}

QB_EXPENSE_ACCOUNT_TYPES = {
    "Expense", "Other Expense", "Cost of Goods Sold",
}

QB_REVENUE_ACCOUNT_TYPES = {
    "Income", "Other Income",
}


class QuickBooksConnector(BaseConnector):
    """Connector for QuickBooks Online accounting integration."""

    PROVIDER_ID = "quickbooks"
    PROVIDER_NAME = "QuickBooks Online"
    PROVIDER_DESCRIPTION = "Accounting software for small business. Import P&L, balance sheet, invoices, and expense data."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.OAUTH2
    DOCS_URL = "https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/account"

    SUPPORTS_EMPLOYEES = True
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.client_id = config.credentials.get("client_id", "")
        self.client_secret = config.credentials.get("client_secret", "")
        self.access_token = config.credentials.get("access_token", "")
        self.refresh_token = config.credentials.get("refresh_token", "")
        self.realm_id = config.credentials.get("realm_id", "")
        self.environment = config.settings.get("environment", "production")
        self.base_url = QB_ENVIRONMENTS.get(self.environment, QB_ENVIRONMENTS["production"])
        self.client: Optional[httpx.AsyncClient] = None
        self._token_refreshed = False

    def _company_url(self, path: str) -> str:
        return f"{self.base_url}/company/{self.realm_id}/{path}"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                headers=self._get_headers(),
                timeout=30.0,
            )
        return self.client

    async def _refresh_access_token(self) -> bool:
        if not self.client_id or not self.client_secret or not self.refresh_token:
            logger.warning("QuickBooks OAuth credentials incomplete for token refresh")
            return False

        try:
            basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            async with httpx.AsyncClient(timeout=15.0) as token_client:
                resp = await token_client.post(
                    QB_OAUTH_TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {basic}",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                    },
                )

            if resp.status_code != 200:
                logger.error(f"QuickBooks token refresh failed: {resp.status_code} {resp.text[:200]}")
                return False

            token_data = resp.json()
            self.access_token = token_data["access_token"]
            if "refresh_token" in token_data:
                self.refresh_token = token_data["refresh_token"]
            self._token_refreshed = True

            if self.client and not self.client.is_closed:
                await self.client.aclose()
                self.client = None

            logger.info("QuickBooks access token refreshed successfully")
            return True
        except Exception as e:
            logger.error(f"QuickBooks token refresh error: {e}")
            return False

    async def _api_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        client = await self._get_client()
        url = self._company_url(path)

        try:
            resp = await client.get(url, params=params)

            if resp.status_code == 401:
                logger.info("QuickBooks token expired, attempting refresh")
                if await self._refresh_access_token():
                    client = await self._get_client()
                    resp = await client.get(url, params=params)
                else:
                    return None

            if resp.status_code != 200:
                logger.warning(f"QuickBooks API {path} returned {resp.status_code}: {resp.text[:300]}")
                return None

            return resp.json()
        except Exception as e:
            logger.error(f"QuickBooks API error ({path}): {e}")
            return None

    async def _api_query(self, query: str, max_results: int = 1000) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        start_position = 1

        while True:
            paged_query = f"{query} STARTPOSITION {start_position} MAXRESULTS {max_results}"
            data = await self._api_get("query", params={"query": paged_query})
            if not data:
                break

            query_response = data.get("QueryResponse", {})
            entities = []
            for key, val in query_response.items():
                if isinstance(val, list):
                    entities = val
                    break

            if not entities:
                break

            results.extend(entities)

            if len(entities) < max_results:
                break
            start_position += max_results

        return results

    async def authenticate(self) -> bool:
        if not self.realm_id:
            logger.warning("QuickBooks realm_id (company ID) not provided")
            return False

        if not self.access_token and not self.refresh_token:
            logger.warning("QuickBooks: no access_token or refresh_token provided")
            return False

        if not self.access_token and self.refresh_token:
            if not await self._refresh_access_token():
                return False

        data = await self._api_get("companyinfo/" + self.realm_id)
        if data and "CompanyInfo" in data:
            company_name = data["CompanyInfo"].get("CompanyName", "Unknown")
            logger.info(f"QuickBooks authenticated: {company_name} (realm {self.realm_id})")
            self._authenticated = True
            return True

        if not self._token_refreshed and self.refresh_token:
            if await self._refresh_access_token():
                data = await self._api_get("companyinfo/" + self.realm_id)
                if data and "CompanyInfo" in data:
                    self._authenticated = True
                    return True

        logger.warning("QuickBooks authentication failed")
        return False

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def fetch_employees(self) -> List[EmployeeRecord]:
        employees_data = await self._api_query("SELECT * FROM Employee")
        records = []

        for emp in employees_data:
            name_parts = []
            if emp.get("GivenName"):
                name_parts.append(emp["GivenName"])
            if emp.get("FamilyName"):
                name_parts.append(emp["FamilyName"])
            full_name = " ".join(name_parts) or emp.get("DisplayName", "Unknown")

            email = None
            if emp.get("PrimaryEmailAddr"):
                email = emp["PrimaryEmailAddr"].get("Address")

            hire_date = None
            if emp.get("HiredDate"):
                try:
                    hire_date = datetime.strptime(emp["HiredDate"], "%Y-%m-%d")
                except (ValueError, TypeError):
                    pass

            status = "active" if emp.get("Active", True) else "inactive"

            records.append(EmployeeRecord(
                external_id=str(emp.get("Id", "")),
                name=full_name,
                email=email,
                department=emp.get("Department", {}).get("name") if isinstance(emp.get("Department"), dict) else None,
                designation=emp.get("Title"),
                salary=None,
                join_date=hire_date,
                status=status,
                metadata={
                    "qb_id": emp.get("Id"),
                    "employee_number": emp.get("EmployeeNumber"),
                    "billable_time": emp.get("BillableTime", False),
                },
            ))

        logger.info(f"QuickBooks: fetched {len(records)} employees")
        return records

    async def fetch_payroll_runs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PayrollRunRecord]:
        return []

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[LedgerEntry]:
        if not start_date:
            start_date = datetime.now() - timedelta(days=90)
        if not end_date:
            end_date = datetime.now()

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        query = f"SELECT * FROM JournalEntry WHERE TxnDate >= '{start_str}' AND TxnDate <= '{end_str}'"
        journal_entries = await self._api_query(query)
        records: List[LedgerEntry] = []

        for je in journal_entries:
            txn_date_str = je.get("TxnDate", "")
            try:
                txn_date = datetime.strptime(txn_date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                txn_date = datetime.now()

            for line in je.get("Line", []):
                je_detail = line.get("JournalEntryLineDetail", {})
                posting_type = je_detail.get("PostingType", "")
                account_ref = je_detail.get("AccountRef", {})
                amount = float(line.get("Amount", 0))

                records.append(LedgerEntry(
                    external_id=f"{je.get('Id', '')}-{line.get('Id', '')}",
                    date=txn_date,
                    account_code=str(account_ref.get("value", "")),
                    account_name=account_ref.get("name", "Unknown Account"),
                    debit=amount if posting_type == "Debit" else 0.0,
                    credit=amount if posting_type == "Credit" else 0.0,
                    description=line.get("Description") or je.get("PrivateNote", ""),
                    category=self._categorize_account(account_ref.get("name", "")),
                    metadata={
                        "journal_entry_id": je.get("Id"),
                        "doc_number": je.get("DocNumber"),
                        "posting_type": posting_type,
                    },
                ))

        purchase_query = f"SELECT * FROM Purchase WHERE TxnDate >= '{start_str}' AND TxnDate <= '{end_str}'"
        purchases = await self._api_query(purchase_query)

        for purchase in purchases:
            txn_date_str = purchase.get("TxnDate", "")
            try:
                txn_date = datetime.strptime(txn_date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                txn_date = datetime.now()

            for line in purchase.get("Line", []):
                detail = line.get("AccountBasedExpenseLineDetail", {})
                account_ref = detail.get("AccountRef", {})
                amount = float(line.get("Amount", 0))

                if not account_ref.get("value"):
                    detail = line.get("ItemBasedExpenseLineDetail", {})
                    account_ref = detail.get("ItemRef", {})

                records.append(LedgerEntry(
                    external_id=f"purchase-{purchase.get('Id', '')}-{line.get('Id', '')}",
                    date=txn_date,
                    account_code=str(account_ref.get("value", "")),
                    account_name=account_ref.get("name", "Expense"),
                    debit=amount,
                    credit=0.0,
                    description=line.get("Description", ""),
                    category="expense",
                    metadata={
                        "purchase_id": purchase.get("Id"),
                        "payment_type": purchase.get("PaymentType"),
                        "entity_name": purchase.get("EntityRef", {}).get("name"),
                    },
                ))

        logger.info(f"QuickBooks: fetched {len(records)} ledger entries ({len(journal_entries)} journal entries, {len(purchases)} purchases)")
        return records

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[InvoiceRecord]:
        if not start_date:
            start_date = datetime.now() - timedelta(days=90)
        if not end_date:
            end_date = datetime.now()

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        query = f"SELECT * FROM Invoice WHERE TxnDate >= '{start_str}' AND TxnDate <= '{end_str}'"
        invoices_data = await self._api_query(query)
        records: List[InvoiceRecord] = []

        for inv in invoices_data:
            txn_date_str = inv.get("TxnDate", "")
            try:
                txn_date = datetime.strptime(txn_date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                txn_date = datetime.now()

            due_date = None
            if inv.get("DueDate"):
                try:
                    due_date = datetime.strptime(inv["DueDate"], "%Y-%m-%d")
                except (ValueError, TypeError):
                    pass

            customer_name = inv.get("CustomerRef", {}).get("name", "")
            subtotal = float(inv.get("TotalAmt", 0))
            tax_amount = float(inv.get("TxnTaxDetail", {}).get("TotalTax", 0))
            total = subtotal
            amount_before_tax = subtotal - tax_amount

            balance = float(inv.get("Balance", 0))
            if balance == 0 and total > 0:
                status = "paid"
            elif balance < total:
                status = "partial"
            else:
                status = "pending"

            line_items = []
            for line in inv.get("Line", []):
                if line.get("DetailType") == "SalesItemLineDetail":
                    detail = line.get("SalesItemLineDetail", {})
                    line_items.append({
                        "description": line.get("Description", ""),
                        "amount": float(line.get("Amount", 0)),
                        "quantity": detail.get("Qty", 1),
                        "unit_price": float(detail.get("UnitPrice", 0)),
                        "item": detail.get("ItemRef", {}).get("name", ""),
                    })

            currency_ref = inv.get("CurrencyRef", {})
            currency = (currency_ref.get("value") or "USD").upper()

            records.append(InvoiceRecord(
                external_id=str(inv.get("Id", "")),
                date=txn_date,
                due_date=due_date,
                customer_name=customer_name,
                amount=amount_before_tax,
                tax=tax_amount,
                total=total,
                currency=currency,
                status=status,
                line_items=line_items,
                metadata={
                    "qb_id": inv.get("Id"),
                    "doc_number": inv.get("DocNumber"),
                    "balance": balance,
                    "email_status": inv.get("EmailStatus"),
                    "ship_date": inv.get("ShipDate"),
                },
            ))

        logger.info(f"QuickBooks: fetched {len(records)} invoices")
        return records

    def _categorize_account(self, account_name: str) -> str:
        name_lower = account_name.lower()
        if any(kw in name_lower for kw in ["revenue", "income", "sales", "service"]):
            return "revenue"
        if any(kw in name_lower for kw in ["cost of goods", "cogs", "cost of sales"]):
            return "cogs"
        if any(kw in name_lower for kw in ["salary", "wages", "payroll", "compensation", "benefits"]):
            return "payroll"
        if any(kw in name_lower for kw in ["rent", "lease", "office", "utilities"]):
            return "facilities"
        if any(kw in name_lower for kw in ["marketing", "advertising", "promotion"]):
            return "marketing"
        if any(kw in name_lower for kw in ["software", "subscription", "hosting", "cloud"]):
            return "technology"
        if any(kw in name_lower for kw in ["travel", "meals", "entertainment"]):
            return "travel"
        if any(kw in name_lower for kw in ["legal", "professional", "accounting", "consulting"]):
            return "professional_services"
        if any(kw in name_lower for kw in ["insurance"]):
            return "insurance"
        if any(kw in name_lower for kw in ["depreciation", "amortization"]):
            return "depreciation"
        if any(kw in name_lower for kw in ["interest", "bank", "finance"]):
            return "finance"
        if any(kw in name_lower for kw in ["tax"]):
            return "tax"
        return "other_expense"

    async def get_profit_and_loss(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        if not start_date:
            start_date = datetime.now() - timedelta(days=90)
        if not end_date:
            end_date = datetime.now()

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        data = await self._api_get("reports/ProfitAndLoss", params={
            "start_date": start_str,
            "end_date": end_str,
            "accounting_method": "Accrual",
            "minorversion": "65",
        })

        result = {
            "period_start": start_str,
            "period_end": end_str,
            "total_income": 0.0,
            "total_cogs": 0.0,
            "gross_profit": 0.0,
            "total_expenses": 0.0,
            "net_income": 0.0,
            "income_breakdown": {},
            "expense_breakdown": {},
        }

        if not data:
            return result

        rows = data.get("Rows", {}).get("Row", [])
        for section in rows:
            group = (section.get("group", "") or "").lower().replace(" ", "")
            summary = section.get("Summary", {})
            col_data = summary.get("ColData", [])
            section_total = self._extract_amount(col_data)

            header_label = ""
            if "Header" in section:
                hdr_cols = section["Header"].get("ColData", [])
                if hdr_cols:
                    header_label = (hdr_cols[0].get("value", "") or "").lower().replace(" ", "")

            if group in ("income", "totalincome") or header_label in ("income", "totalincome"):
                result["total_income"] = section_total
                result["income_breakdown"] = self._extract_row_breakdown(section)
            elif group in ("cogs", "costofgoodssold", "costofgoods") or header_label in ("costofgoodssold", "cogs"):
                result["total_cogs"] = section_total
            elif group in ("expenses", "totalexpenses", "expense") or header_label in ("expenses", "totalexpenses"):
                result["total_expenses"] = section_total
                result["expense_breakdown"] = self._extract_row_breakdown(section)
            elif group in ("grossprofit",) or header_label in ("grossprofit",):
                result["gross_profit"] = section_total
            elif group in ("netincome", "netoperatingincome", "netincomeloss") or header_label in ("netincome", "netoperatingincome"):
                result["net_income"] = section_total
            elif group in ("otherincome",) or header_label in ("otherincome",):
                result["total_income"] += section_total
            elif group in ("otherexpenses", "otherexpense") or header_label in ("otherexpenses", "otherexpense"):
                result["total_expenses"] += section_total

        if result["gross_profit"] == 0.0 and result["total_income"] > 0:
            result["gross_profit"] = result["total_income"] - result["total_cogs"]

        logger.info(f"QuickBooks P&L: revenue={result['total_income']}, expenses={result['total_expenses']}, net={result['net_income']}")
        return result

    async def get_balance_sheet(self, as_of_date: Optional[datetime] = None) -> Dict[str, Any]:
        if not as_of_date:
            as_of_date = datetime.now()

        date_str = as_of_date.strftime("%Y-%m-%d")

        data = await self._api_get("reports/BalanceSheet", params={
            "date": date_str,
            "accounting_method": "Accrual",
            "minorversion": "65",
        })

        result = {
            "as_of_date": date_str,
            "total_assets": 0.0,
            "total_liabilities": 0.0,
            "total_equity": 0.0,
            "cash_and_equivalents": 0.0,
            "accounts_receivable": 0.0,
            "accounts_payable": 0.0,
        }

        if not data:
            return result

        rows = data.get("Rows", {}).get("Row", [])
        for section in rows:
            group = (section.get("group", "") or "").lower().replace(" ", "")
            summary = section.get("Summary", {})
            col_data = summary.get("ColData", [])
            section_total = self._extract_amount(col_data)

            header_label = ""
            if "Header" in section:
                hdr_cols = section["Header"].get("ColData", [])
                if hdr_cols:
                    header_label = (hdr_cols[0].get("value", "") or "").lower().replace(" ", "")

            if group in ("asset", "assets", "totalassets", "totalcurrentassets") or header_label in ("assets", "totalassets"):
                result["total_assets"] = section_total
                breakdown = self._extract_row_breakdown(section)
                for label, amount in breakdown.items():
                    label_lower = label.lower()
                    if any(kw in label_lower for kw in ["cash", "bank", "checking", "savings", "money market", "undeposited"]):
                        result["cash_and_equivalents"] += amount
                    elif any(kw in label_lower for kw in ["accounts receivable", "a/r"]):
                        result["accounts_receivable"] += amount
            elif group in ("liability", "liabilities", "totalliabilities", "totalcurrentliabilities") or header_label in ("liabilities", "totalliabilities"):
                result["total_liabilities"] = section_total
                breakdown = self._extract_row_breakdown(section)
                for label, amount in breakdown.items():
                    if any(kw in label.lower() for kw in ["accounts payable", "a/p"]):
                        result["accounts_payable"] += amount
            elif group in ("equity", "totalequity") or header_label in ("equity", "totalequity"):
                result["total_equity"] = section_total

        logger.info(f"QuickBooks balance sheet: assets={result['total_assets']}, liabilities={result['total_liabilities']}, cash={result['cash_and_equivalents']}")
        return result

    async def get_cash_flow(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        if not start_date:
            start_date = datetime.now() - timedelta(days=90)
        if not end_date:
            end_date = datetime.now()

        data = await self._api_get("reports/CashFlow", params={
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "minorversion": "65",
        })

        result = {
            "operating_activities": 0.0,
            "investing_activities": 0.0,
            "financing_activities": 0.0,
            "net_change_in_cash": 0.0,
            "beginning_cash": 0.0,
            "ending_cash": 0.0,
        }

        if not data:
            return result

        rows = data.get("Rows", {}).get("Row", [])
        for section in rows:
            group = (section.get("group", "") or "").lower()
            summary = section.get("Summary", {})
            col_data = summary.get("ColData", [])
            section_total = self._extract_amount(col_data)

            header_label = ""
            if "Header" in section:
                hdr_cols = section["Header"].get("ColData", [])
                if hdr_cols:
                    header_label = (hdr_cols[0].get("value", "") or "").lower()

            combined = group + " " + header_label
            if "operating" in combined:
                result["operating_activities"] = section_total
            elif "investing" in combined:
                result["investing_activities"] = section_total
            elif "financing" in combined:
                result["financing_activities"] = section_total

        result["net_change_in_cash"] = (
            result["operating_activities"]
            + result["investing_activities"]
            + result["financing_activities"]
        )

        logger.info(f"QuickBooks cash flow: operating={result['operating_activities']}, net_change={result['net_change_in_cash']}")
        return result

    def _extract_amount(self, col_data: List[Dict[str, Any]]) -> float:
        if not col_data or len(col_data) < 2:
            return 0.0
        try:
            return float(col_data[-1].get("value", 0) or 0)
        except (ValueError, TypeError):
            return 0.0

    def _extract_row_breakdown(self, section: Dict[str, Any]) -> Dict[str, float]:
        breakdown: Dict[str, float] = {}

        for row in section.get("Rows", {}).get("Row", []):
            if "Header" in row:
                header = row["Header"]
                col_data = header.get("ColData", [])
                if col_data:
                    label = col_data[0].get("value", "Unknown")
                    amount = self._extract_amount(col_data)
                    breakdown[label] = amount
            elif "ColData" in row:
                col_data = row["ColData"]
                if col_data:
                    label = col_data[0].get("value", "Unknown")
                    amount = self._extract_amount(col_data)
                    breakdown[label] = amount

        return breakdown

    async def map_to_financials(
        self,
        employees: List[EmployeeRecord],
        payroll_runs: List[PayrollRunRecord],
        ledger_entries: List[LedgerEntry],
        invoices: List[InvoiceRecord]
    ) -> Dict[str, Any]:
        pnl = await self.get_profit_and_loss()
        balance = await self.get_balance_sheet()

        total_invoice_revenue = sum(inv.total for inv in invoices if inv.status == "paid")
        revenue = pnl["total_income"] if pnl["total_income"] > 0 else total_invoice_revenue

        payroll_cost = 0.0
        for label, amount in pnl.get("expense_breakdown", {}).items():
            if any(kw in label.lower() for kw in ["payroll", "salary", "wages", "compensation"]):
                payroll_cost += amount

        return {
            "source_type": "connector_quickbooks",
            "extraction_summary": f"Synced from QuickBooks Online",
            "revenue": revenue,
            "cogs": pnl.get("total_cogs", 0),
            "opex": pnl.get("total_expenses", 0),
            "payroll": payroll_cost,
            "net_income": pnl.get("net_income", 0),
            "gross_profit": pnl.get("gross_profit", 0),
            "cash_balance": balance.get("cash_and_equivalents", 0),
            "accounts_receivable": balance.get("accounts_receivable", 0),
            "accounts_payable": balance.get("accounts_payable", 0),
            "total_assets": balance.get("total_assets", 0),
            "total_liabilities": balance.get("total_liabilities", 0),
            "headcount": len(employees) if employees else None,
            "invoices_count": len(invoices),
            "transactions_count": len(ledger_entries),
            "income_breakdown": pnl.get("income_breakdown", {}),
            "expense_breakdown": pnl.get("expense_breakdown", {}),
        }

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        errors: List[str] = []
        warnings: List[str] = []
        total_records = 0

        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check your QuickBooks OAuth credentials and realm_id"],
                    sync_started=sync_started,
                )

            employees: List[EmployeeRecord] = []
            ledger: List[LedgerEntry] = []
            invoices: List[InvoiceRecord] = []

            try:
                employees = await self.fetch_employees()
                total_records += len(employees)
            except Exception as e:
                warnings.append(f"Employee fetch failed (non-critical): {str(e)}")
                logger.warning(f"QuickBooks employee fetch error: {e}")

            try:
                ledger = await self.fetch_ledger()
                total_records += len(ledger)
            except Exception as e:
                errors.append(f"Ledger fetch failed: {str(e)}")
                logger.error(f"QuickBooks ledger fetch error: {e}")

            try:
                invoices = await self.fetch_invoices()
                total_records += len(invoices)
            except Exception as e:
                errors.append(f"Invoice fetch failed: {str(e)}")
                logger.error(f"QuickBooks invoice fetch error: {e}")

            financials = await self.map_to_financials(
                employees=employees,
                payroll_runs=[],
                ledger_entries=ledger,
                invoices=invoices,
            )

            if self._token_refreshed:
                financials["_refreshed_tokens"] = {
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                }

            self._last_sync = datetime.utcnow()

            return SyncResult(
                success=len(errors) == 0,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=total_records,
                errors=errors,
                warnings=warnings,
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={"financials": financials},
            )
        except Exception as e:
            logger.error(f"QuickBooks sync failed: {e}")
            return SyncResult(
                success=False,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                errors=[f"QuickBooks sync failed: {str(e)}"],
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
            )

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()
            self.client = None


ConnectorRegistry.register(QuickBooksConnector)
