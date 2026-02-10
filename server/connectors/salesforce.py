"""
Salesforce CRM Connector - Sales, pipeline, and account data.

Provides:
- Opportunity data (revenue forecasts, closed deals)
- Account records (company/customer ledger)
- Contact and Lead tracking
- SOQL query-based data extraction

API Documentation: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/
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

API_VERSION = "v58.0"


@ConnectorRegistry.register
class SalesforceConnector(BaseConnector):
    PROVIDER_ID = "salesforce"
    PROVIDER_NAME = "Salesforce"
    PROVIDER_DESCRIPTION = "CRM platform for sales pipeline, opportunity tracking, and account management. Import deals, accounts, contacts, and leads via SOQL queries."
    PROVIDER_CATEGORY = ProviderCategory.CRM
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._instance_url = config.credentials.get("instance_url", "").rstrip("/")
        self._access_token = config.credentials.get("access_token", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            base_url = f"{self._instance_url}/services/data/{API_VERSION}"
            self._client = httpx.AsyncClient(
                base_url=base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                },
            )
        return self._client

    async def _soql_query(self, query: str) -> List[Dict[str, Any]]:
        client = await self._get_client()
        all_records: List[Dict[str, Any]] = []
        params = {"q": query}

        try:
            response = await client.get("/query", params=params)
            if response.status_code != 200:
                logger.error(f"Salesforce SOQL error: {response.status_code} - {response.text[:200]}")
                return []

            data = response.json()
            all_records.extend(data.get("records", []))

            next_url = data.get("nextRecordsUrl")
            while next_url:
                resp = await client.get(next_url)
                if resp.status_code != 200:
                    break
                page = resp.json()
                all_records.extend(page.get("records", []))
                next_url = page.get("nextRecordsUrl")

        except Exception as e:
            logger.error(f"Salesforce SOQL query error: {e}")

        return all_records

    async def authenticate(self) -> bool:
        if not self._instance_url or not self._access_token:
            logger.warning("Salesforce credentials incomplete (need instance_url and access_token)")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/sobjects")

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Salesforce authentication successful")
                return True
            else:
                logger.warning(f"Salesforce auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Salesforce authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/sobjects")
            return response.status_code == 200
        except Exception:
            return False

    async def get_opportunities(
        self,
        limit: int = 500,
        closed_only: bool = False,
    ) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        where_clause = "WHERE IsWon = true" if closed_only else ""
        query = (
            f"SELECT Id, Name, Amount, StageName, CloseDate, CreatedDate, "
            f"Probability, AccountId, OwnerId, Type, ForecastCategory "
            f"FROM Opportunity {where_clause} "
            f"ORDER BY CloseDate DESC LIMIT {limit}"
        )
        return await self._soql_query(query)

    async def get_accounts(self, limit: int = 500) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        query = (
            f"SELECT Id, Name, Type, Industry, AnnualRevenue, "
            f"NumberOfEmployees, BillingCity, BillingCountry, CreatedDate "
            f"FROM Account ORDER BY CreatedDate DESC LIMIT {limit}"
        )
        return await self._soql_query(query)

    async def get_contacts(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        query = (
            f"SELECT Id, FirstName, LastName, Email, AccountId, Title, "
            f"Department, CreatedDate "
            f"FROM Contact ORDER BY CreatedDate DESC LIMIT {limit}"
        )
        return await self._soql_query(query)

    async def get_leads(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        query = (
            f"SELECT Id, FirstName, LastName, Email, Company, Status, "
            f"LeadSource, CreatedDate "
            f"FROM Lead ORDER BY CreatedDate DESC LIMIT {limit}"
        )
        return await self._soql_query(query)

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        opportunities = await self.get_opportunities(limit=500, closed_only=True)
        invoices = []

        for opp in opportunities:
            amount = float(opp.get("Amount") or 0)
            if amount <= 0:
                continue

            close_date_str = opp.get("CloseDate", "")
            try:
                close_date = datetime.strptime(close_date_str, "%Y-%m-%d") if close_date_str else datetime.now()
            except (ValueError, TypeError):
                close_date = datetime.now()

            if start_date and close_date < start_date:
                continue
            if end_date and close_date > end_date:
                continue

            invoices.append(
                InvoiceRecord(
                    external_id=opp.get("Id", ""),
                    date=close_date,
                    customer_name=opp.get("Name", ""),
                    amount=amount,
                    total=amount,
                    currency="USD",
                    status="paid",
                    metadata={
                        "stage": opp.get("StageName", ""),
                        "probability": opp.get("Probability", 0),
                        "forecast_category": opp.get("ForecastCategory", ""),
                        "source": "salesforce_opportunity",
                    },
                )
            )

        return invoices

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        accounts = await self.get_accounts(limit=500)
        entries = []

        for acc in accounts:
            annual_revenue = float(acc.get("AnnualRevenue") or 0)
            if annual_revenue <= 0:
                continue

            created_str = acc.get("CreatedDate", "")
            try:
                created_date = datetime.fromisoformat(created_str.replace("Z", "+00:00")) if created_str else datetime.now()
            except (ValueError, TypeError):
                created_date = datetime.now()

            if start_date and created_date < start_date:
                continue
            if end_date and created_date > end_date:
                continue

            entries.append(
                LedgerEntry(
                    external_id=acc.get("Id", ""),
                    date=created_date,
                    account_code=acc.get("Id", ""),
                    account_name=acc.get("Name", ""),
                    debit=0.0,
                    credit=annual_revenue,
                    description=f"{acc.get('Type', 'Account')} - {acc.get('Industry', 'N/A')}",
                    category=acc.get("Industry", "Uncategorized"),
                    metadata={
                        "account_type": acc.get("Type", ""),
                        "employees": acc.get("NumberOfEmployees", 0),
                        "billing_city": acc.get("BillingCity", ""),
                        "billing_country": acc.get("BillingCountry", ""),
                        "source": "salesforce_account",
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
            "source_type": "connector_salesforce",
            "extraction_summary": "Synced from Salesforce CRM",
        }

        if invoices:
            result["revenue"] = sum(inv.total for inv in invoices)
            result["deals_closed"] = len(invoices)

        if ledger_entries:
            result["total_account_revenue"] = sum(e.credit for e in ledger_entries)
            result["accounts_count"] = len(ledger_entries)

        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check instance_url and access_token"],
                    sync_started=sync_started,
                )

            opportunities = await self.get_opportunities(limit=500)
            accounts = await self.get_accounts(limit=500)
            contacts = await self.get_contacts(limit=200)
            leads = await self.get_leads(limit=200)
            invoices = await self.fetch_invoices()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(invoices=invoices, ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(opportunities) + len(accounts) + len(contacts) + len(leads),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "opportunities_count": len(opportunities),
                    "accounts_count": len(accounts),
                    "contacts_count": len(contacts),
                    "leads_count": len(leads),
                },
            )

        except Exception as e:
            logger.error(f"Salesforce sync failed: {e}")
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
