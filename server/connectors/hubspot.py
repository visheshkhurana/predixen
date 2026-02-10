"""
HubSpot CRM Connector - Sales and revenue pipeline data.

Provides:
- Deal pipeline data (revenue forecasts)
- Contact and company records
- Revenue metrics from closed deals
- Sales pipeline analytics

API Documentation: https://developers.hubspot.com/docs/api-reference/crm
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

BASE_URL = "https://api.hubapi.com"


@ConnectorRegistry.register
class HubSpotConnector(BaseConnector):
    PROVIDER_ID = "hubspot"
    PROVIDER_NAME = "HubSpot"
    PROVIDER_DESCRIPTION = "CRM platform for sales pipeline, deal tracking, and revenue forecasting. Import deal data, contacts, and revenue metrics."
    PROVIDER_CATEGORY = ProviderCategory.CRM
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developers.hubspot.com/docs/api-reference/crm"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
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
            logger.warning("HubSpot access token not provided")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/crm/v3/objects/contacts?limit=1")

            if response.status_code == 200:
                self._authenticated = True
                logger.info("HubSpot authentication successful")
                return True
            else:
                logger.warning(f"HubSpot auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"HubSpot authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/crm/v3/objects/contacts?limit=1")
            return response.status_code == 200
        except Exception:
            return False

    async def get_deals(
        self,
        limit: int = 100,
        properties: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        if not properties:
            properties = [
                "dealname", "amount", "dealstage", "pipeline",
                "closedate", "createdate", "hs_lastmodifieddate",
                "hs_deal_stage_probability", "hubspot_owner_id",
            ]

        try:
            client = await self._get_client()
            all_deals = []
            after = None

            while True:
                params: Dict[str, Any] = {
                    "limit": min(limit, 100),
                    "properties": ",".join(properties),
                }
                if after:
                    params["after"] = after

                response = await client.get("/crm/v3/objects/deals", params=params)

                if response.status_code != 200:
                    logger.error(f"HubSpot deals error: {response.status_code}")
                    break

                data = response.json()
                results = data.get("results", [])
                all_deals.extend(results)

                paging = data.get("paging", {})
                next_page = paging.get("next", {})
                after = next_page.get("after")

                if not after or len(all_deals) >= limit:
                    break

            return all_deals

        except Exception as e:
            logger.error(f"HubSpot deals fetch error: {e}")
            return []

    async def get_contacts(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params = {
                "limit": min(limit, 100),
                "properties": "email,firstname,lastname,company,createdate,lifecyclestage",
            }
            response = await client.get("/crm/v3/objects/contacts", params=params)

            if response.status_code == 200:
                return response.json().get("results", [])
            return []
        except Exception as e:
            logger.error(f"HubSpot contacts fetch error: {e}")
            return []

    async def get_companies(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params = {
                "limit": min(limit, 100),
                "properties": "name,domain,industry,annualrevenue,numberofemployees,createdate",
            }
            response = await client.get("/crm/v3/objects/companies", params=params)

            if response.status_code == 200:
                return response.json().get("results", [])
            return []
        except Exception as e:
            logger.error(f"HubSpot companies fetch error: {e}")
            return []

    async def get_deal_pipeline_summary(self) -> Dict[str, Any]:
        deals = await self.get_deals(limit=500)

        pipeline: Dict[str, Any] = {
            "total_deals": len(deals),
            "total_pipeline_value": 0,
            "closed_won_value": 0,
            "closed_won_count": 0,
            "open_deals_value": 0,
            "open_deals_count": 0,
            "stages": {},
        }

        for deal in deals:
            props = deal.get("properties", {})
            amount = float(props.get("amount") or 0)
            stage = props.get("dealstage", "unknown")

            if stage not in pipeline["stages"]:
                pipeline["stages"][stage] = {"count": 0, "value": 0}
            pipeline["stages"][stage]["count"] += 1
            pipeline["stages"][stage]["value"] += amount

            pipeline["total_pipeline_value"] += amount

            if stage == "closedwon":
                pipeline["closed_won_value"] += amount
                pipeline["closed_won_count"] += 1
            elif stage != "closedlost":
                pipeline["open_deals_value"] += amount
                pipeline["open_deals_count"] += 1

        return pipeline

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        deals = await self.get_deals(limit=500)
        invoices = []

        for deal in deals:
            props = deal.get("properties", {})
            stage = props.get("dealstage", "")
            amount = float(props.get("amount") or 0)

            if stage != "closedwon" or amount <= 0:
                continue

            close_date_str = props.get("closedate", "")
            try:
                close_date = datetime.fromisoformat(close_date_str.replace("Z", "+00:00")) if close_date_str else datetime.now()
            except (ValueError, TypeError):
                close_date = datetime.now()

            if start_date and close_date < start_date:
                continue
            if end_date and close_date > end_date:
                continue

            invoices.append(
                InvoiceRecord(
                    external_id=deal.get("id", ""),
                    date=close_date,
                    customer_name=props.get("dealname", ""),
                    amount=amount,
                    total=amount,
                    currency="USD",
                    status="paid",
                    metadata={
                        "deal_stage": stage,
                        "pipeline": props.get("pipeline", ""),
                        "source": "hubspot_deal",
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
            "source_type": "connector_hubspot",
            "extraction_summary": "Synced from HubSpot CRM",
        }

        if invoices:
            result["revenue"] = sum(inv.total for inv in invoices)
            result["deals_closed"] = len(invoices)

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

            deals = await self.get_deals(limit=500)
            contacts = await self.get_contacts(limit=100)
            companies = await self.get_companies(limit=100)
            pipeline = await self.get_deal_pipeline_summary()
            invoices = await self.fetch_invoices()
            financials = self.map_to_financials(invoices=invoices)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(deals) + len(contacts) + len(companies),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "pipeline_summary": pipeline,
                    "deals_count": len(deals),
                    "contacts_count": len(contacts),
                    "companies_count": len(companies),
                },
            )

        except Exception as e:
            logger.error(f"HubSpot sync failed: {e}")
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
