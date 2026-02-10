"""
Pipedrive CRM Connector - Deal pipeline, contacts, and organization data.

Provides:
- Deal tracking and pipeline management
- Contact (person) records
- Organization records
- Revenue metrics from won deals

API Documentation: https://developers.pipedrive.com/docs/api/v1
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
class PipedriveConnector(BaseConnector):
    PROVIDER_ID = "pipedrive"
    PROVIDER_NAME = "Pipedrive"
    PROVIDER_DESCRIPTION = "CRM for sales pipeline management. Import deals, contacts, and organizations. Track deal values and revenue metrics."
    PROVIDER_CATEGORY = ProviderCategory.CRM
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developers.pipedrive.com/docs/api/v1"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_token = config.credentials.get("api_token", "")
        self._company_domain = config.credentials.get("company_domain", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            base_url = f"https://{self._company_domain}.pipedrive.com/api/v1"
            self._client = httpx.AsyncClient(
                base_url=base_url,
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    def _auth_params(self) -> Dict[str, str]:
        return {"api_token": self._api_token}

    async def authenticate(self) -> bool:
        if not self._api_token or not self._company_domain:
            logger.warning("Pipedrive credentials incomplete (need api_token and company_domain)")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/users/me", params=self._auth_params())

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self._authenticated = True
                    logger.info("Pipedrive authentication successful")
                    return True

            logger.warning(f"Pipedrive auth failed: {response.status_code} - {response.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"Pipedrive authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/users/me", params=self._auth_params())
            return response.status_code == 200 and response.json().get("success", False)
        except Exception:
            return False

    async def get_deals(
        self,
        limit: int = 500,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_deals: List[Dict[str, Any]] = []
            start = 0

            while True:
                params: Dict[str, Any] = {
                    **self._auth_params(),
                    "start": start,
                    "limit": min(limit - len(all_deals), 100),
                }
                if status:
                    params["status"] = status

                response = await client.get("/deals", params=params)
                if response.status_code != 200:
                    logger.error(f"Pipedrive deals error: {response.status_code}")
                    break

                data = response.json()
                if not data.get("success"):
                    break

                items = data.get("data") or []
                all_deals.extend(items)

                pagination = data.get("additional_data", {}).get("pagination", {})
                if not pagination.get("more_items_in_collection") or len(all_deals) >= limit:
                    break
                start = pagination.get("next_start", start + len(items))

            return all_deals

        except Exception as e:
            logger.error(f"Pipedrive deals fetch error: {e}")
            return []

    async def get_persons(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {
                **self._auth_params(),
                "start": 0,
                "limit": min(limit, 100),
            }
            response = await client.get("/persons", params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("data") or []
            return []
        except Exception as e:
            logger.error(f"Pipedrive persons fetch error: {e}")
            return []

    async def get_organizations(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            params: Dict[str, Any] = {
                **self._auth_params(),
                "start": 0,
                "limit": min(limit, 100),
            }
            response = await client.get("/organizations", params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("data") or []
            return []
        except Exception as e:
            logger.error(f"Pipedrive organizations fetch error: {e}")
            return []

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        deals = await self.get_deals(limit=500, status="won")
        invoices = []

        for deal in deals:
            value = float(deal.get("value") or 0)
            if value <= 0:
                continue

            won_time_str = deal.get("won_time", "") or deal.get("close_time", "")
            try:
                won_date = datetime.fromisoformat(won_time_str.replace("Z", "+00:00")) if won_time_str else datetime.now()
            except (ValueError, TypeError):
                won_date = datetime.now()

            if start_date and won_date < start_date:
                continue
            if end_date and won_date > end_date:
                continue

            currency = deal.get("currency", "USD")

            invoices.append(
                InvoiceRecord(
                    external_id=str(deal.get("id", "")),
                    date=won_date,
                    customer_name=deal.get("title", ""),
                    amount=value,
                    total=value,
                    currency=currency,
                    status="paid",
                    metadata={
                        "pipeline_id": deal.get("pipeline_id", ""),
                        "stage_id": deal.get("stage_id", ""),
                        "org_name": (deal.get("org_name") or {}).get("name", "") if isinstance(deal.get("org_name"), dict) else str(deal.get("org_name", "")),
                        "source": "pipedrive_deal",
                    },
                )
            )

        return invoices

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        organizations = await self.get_organizations(limit=500)
        entries = []

        for org in organizations:
            org_id = str(org.get("id", ""))
            org_name = org.get("name", "Unknown")

            add_time_str = org.get("add_time", "")
            try:
                add_date = datetime.fromisoformat(add_time_str.replace("Z", "+00:00")) if add_time_str else datetime.now()
            except (ValueError, TypeError):
                add_date = datetime.now()

            if start_date and add_date < start_date:
                continue
            if end_date and add_date > end_date:
                continue

            entries.append(
                LedgerEntry(
                    external_id=f"pipedrive_org_{org_id}",
                    date=add_date,
                    account_code=org_id,
                    account_name=org_name,
                    debit=0.0,
                    credit=0.0,
                    description=f"Organization: {org_name}",
                    category="CRM Organization",
                    metadata={
                        "people_count": org.get("people_count", 0),
                        "open_deals_count": org.get("open_deals_count", 0),
                        "won_deals_count": org.get("won_deals_count", 0),
                        "address": org.get("address", ""),
                        "source": "pipedrive_organization",
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
            "source_type": "connector_pipedrive",
            "extraction_summary": "Synced from Pipedrive CRM",
        }

        if invoices:
            result["revenue"] = sum(inv.total for inv in invoices)
            result["deals_won"] = len(invoices)

        if ledger_entries:
            result["organizations_count"] = len(ledger_entries)

        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check api_token and company_domain"],
                    sync_started=sync_started,
                )

            deals = await self.get_deals(limit=500)
            persons = await self.get_persons(limit=200)
            organizations = await self.get_organizations(limit=200)
            invoices = await self.fetch_invoices()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(invoices=invoices, ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(deals) + len(persons) + len(organizations),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "deals_count": len(deals),
                    "persons_count": len(persons),
                    "organizations_count": len(organizations),
                },
            )

        except Exception as e:
            logger.error(f"Pipedrive sync failed: {e}")
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
