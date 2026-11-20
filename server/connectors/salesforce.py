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
from .http import http_client
import logging
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta

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
from server.services import crm_pipeline

logger = logging.getLogger(__name__)

API_VERSION = "v58.0"


def salesforce_opportunity_for_snapshot(opp: Dict[str, Any]) -> Dict[str, Any]:
    if opp.get("IsWon"):
        status = "won"
    elif opp.get("IsClosed"):
        status = "lost"
    else:
        status = "open"
    return {
        "amount": float(opp.get("Amount") or 0.0),
        "currency": opp.get("CurrencyIsoCode"),
        "stage": opp.get("StageName"),
        "status": status,
        "close_date": opp.get("CloseDate"),
        # Opportunity.Probability is a percent (0..100).
        "probability": crm_pipeline.probability(opp.get("Probability"), scale="percent"),
    }


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
        # Set by "Connect with Salesforce": lets the connector get a fresh
        # access token (they last ~2 hours) instead of failing.
        self._refresh_token = config.credentials.get("refresh_token", "")
        self._client_id = config.credentials.get("client_id", "")
        self._client_secret = config.credentials.get("client_secret", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _refresh_access_token(self) -> bool:
        if not (self._refresh_token and self._client_id and self._client_secret and self._instance_url):
            return False
        try:
            async with http_client(timeout=30.0) as client:
                res = await client.post(f"{self._instance_url}/services/oauth2/token", data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                })
            if res.status_code != 200 or not res.json().get("access_token"):
                logger.warning(f"Salesforce token refresh failed: {res.status_code}")
                return False
            data = res.json()
            self._access_token = data["access_token"]
            if self._client:
                await self._client.aclose()
                self._client = None
            return True
        except Exception as e:
            logger.error(f"Salesforce token refresh error: {e}")
            return False

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            base_url = f"{self._instance_url}/services/data/{API_VERSION}"
            self._client = http_client(
                base_url=base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                },
            )
        return self._client

    async def _soql_query(self, query: str) -> List[Dict[str, Any]]:
        return await self._soql_query_strict(query) or []

    async def _soql_query_strict(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Like _soql_query, but None when the first page fails (for example
        INVALID_FIELD on CurrencyIsoCode in a single-currency org), so callers
        can retry with another query instead of reading an error as no rows."""
        client = await self._get_client()
        all_records: List[Dict[str, Any]] = []
        params = {"q": query}

        try:
            response = await client.get("/query", params=params)
            if response.status_code != 200:
                logger.error(f"Salesforce SOQL error: {response.status_code} - {response.text[:200]}")
                return None

            data = response.json()
            all_records.extend(data.get("records", []))

            next_url = data.get("nextRecordsUrl")
            # The page link comes from the remote server: follow a path on the
            # same instance only, never an absolute URL.
            while isinstance(next_url, str) and next_url.startswith("/") and not next_url.startswith("//"):
                resp = await client.get(next_url)
                if resp.status_code != 200:
                    break
                page = resp.json()
                all_records.extend(page.get("records", []))
                next_url = page.get("nextRecordsUrl")

        except Exception as e:
            logger.error(f"Salesforce SOQL query error: {e}")
            if not all_records:
                return None

        return all_records

    async def get_org_currency(self) -> Optional[str]:
        """The org's corporate currency. Opportunity.Amount is in this currency
        unless multi-currency is on, in which case each row has CurrencyIsoCode."""
        if getattr(self, "_org_currency_loaded", False):
            return self._org_currency
        self._org_currency_loaded = True
        self._org_currency = None
        rows = await self._soql_query_strict("SELECT DefaultCurrencyIsoCode FROM Organization LIMIT 1")
        if rows:
            cur = rows[0].get("DefaultCurrencyIsoCode")
            if isinstance(cur, str) and len(cur) == 3:
                self._org_currency = cur.upper()
        return self._org_currency

    async def authenticate(self) -> bool:
        if self._refresh_token and not await self._refresh_access_token() and not self._access_token:
            return False
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

        cache_key = (limit, closed_only)
        cache = getattr(self, "_opp_cache", None)
        if cache is None:
            cache = self._opp_cache = {}
        if cache_key in cache:
            return cache[cache_key]
        where_clause = "WHERE IsWon = true" if closed_only else ""
        fields = (
            "Id, Name, Amount, StageName, CloseDate, CreatedDate, Probability, "
            "IsClosed, IsWon, AccountId, OwnerId, Type, ForecastCategory"
        )
        tail = f"FROM Opportunity {where_clause} ORDER BY CloseDate DESC LIMIT {limit}"
        # CurrencyIsoCode exists only in multi-currency orgs; elsewhere the
        # field is invalid, so retry without it and use the org currency.
        rows = await self._soql_query_strict(f"SELECT {fields}, CurrencyIsoCode {tail}")
        if rows is None:
            rows = await self._soql_query(f"SELECT {fields} {tail}")
        cache[cache_key] = rows
        return rows

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
        org_currency = await self.get_org_currency()
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
                    currency=(opp.get("CurrencyIsoCode") or org_currency or "USD").upper(),
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
            # Revenue for this month only: deals won in the current calendar
            # month, in the main currency. Summing every won deal ever (up to
            # 500) and calling it USD overstated revenue for any org with
            # history and mislabelled non-USD orgs.
            today = date.today()
            month = [i for i in invoices if i.date.date() >= today.replace(day=1) and i.date.date() <= today]
            result["period_start"] = today.replace(day=1).isoformat()
            result["period_end"] = today.isoformat()
            result["deals_closed"] = len(month)
            counts: Dict[str, int] = {}
            for inv in invoices:
                counts[inv.currency] = counts.get(inv.currency, 0) + 1
            main = getattr(self, "_org_currency", None) or (max(counts, key=counts.get) if counts else None)
            in_main = [i for i in month if i.currency == main]
            result["revenue"] = round(sum(i.total for i in in_main), 2)
            if main:
                result["revenue_currency"] = main
            other = sorted({i.currency for i in month if i.currency != main})
            if other:
                result["revenue_other_currencies"] = other

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
                    "crm_pipeline": crm_pipeline.build_snapshot(
                        [salesforce_opportunity_for_snapshot(o) for o in opportunities],
                        await self.get_org_currency(),
                        truncated=len(opportunities) >= 500,
                    ),
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
