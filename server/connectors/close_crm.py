"""
Close CRM Connector - Lead, opportunity, and activity data.

Provides:
- Lead tracking and management
- Opportunity pipeline data
- Activity logs (calls, emails, meetings)
- Revenue metrics from won opportunities

API Documentation: https://developer.close.com/
"""

import httpx
import logging
import base64
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

BASE_URL = "https://api.close.com/api/v1"


@ConnectorRegistry.register
class CloseCRMConnector(BaseConnector):
    PROVIDER_ID = "close_crm"
    PROVIDER_NAME = "Close CRM"
    PROVIDER_DESCRIPTION = "Inside sales CRM for lead management, opportunity tracking, and activity logging. Import leads, opportunities, and communication activity."
    PROVIDER_CATEGORY = ProviderCategory.CRM
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developer.close.com/"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_key = config.credentials.get("api_key", "")
        self._client: Optional[httpx.AsyncClient] = None

    def _basic_auth_header(self) -> str:
        credentials = base64.b64encode(f"{self._api_key}:".encode()).decode()
        return f"Basic {credentials}"

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": self._basic_auth_header(),
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._api_key:
            logger.warning("Close CRM API key not provided")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/me/")

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Close CRM authentication successful")
                return True
            else:
                logger.warning(f"Close CRM auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Close CRM authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/me/")
            return response.status_code == 200
        except Exception:
            return False

    async def get_leads(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_leads: List[Dict[str, Any]] = []
            skip = 0

            while True:
                params: Dict[str, Any] = {
                    "_skip": skip,
                    "_limit": min(limit - len(all_leads), 100),
                }
                response = await client.get("/lead/", params=params)

                if response.status_code != 200:
                    logger.error(f"Close CRM leads error: {response.status_code}")
                    break

                data = response.json()
                items = data.get("data", [])
                all_leads.extend(items)

                if not data.get("has_more", False) or len(all_leads) >= limit:
                    break
                skip += len(items)

            return all_leads

        except Exception as e:
            logger.error(f"Close CRM leads fetch error: {e}")
            return []

    async def get_opportunities(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_opps: List[Dict[str, Any]] = []
            skip = 0

            while True:
                params: Dict[str, Any] = {
                    "_skip": skip,
                    "_limit": min(limit - len(all_opps), 100),
                }
                response = await client.get("/opportunity/", params=params)

                if response.status_code != 200:
                    logger.error(f"Close CRM opportunities error: {response.status_code}")
                    break

                data = response.json()
                items = data.get("data", [])
                all_opps.extend(items)

                if not data.get("has_more", False) or len(all_opps) >= limit:
                    break
                skip += len(items)

            return all_opps

        except Exception as e:
            logger.error(f"Close CRM opportunities fetch error: {e}")
            return []

    async def get_activities(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_activities: List[Dict[str, Any]] = []
            skip = 0

            while True:
                params: Dict[str, Any] = {
                    "_skip": skip,
                    "_limit": min(limit - len(all_activities), 100),
                }
                response = await client.get("/activity/", params=params)

                if response.status_code != 200:
                    logger.error(f"Close CRM activities error: {response.status_code}")
                    break

                data = response.json()
                items = data.get("data", [])
                all_activities.extend(items)

                if not data.get("has_more", False) or len(all_activities) >= limit:
                    break
                skip += len(items)

            return all_activities

        except Exception as e:
            logger.error(f"Close CRM activities fetch error: {e}")
            return []

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        opportunities = await self.get_opportunities(limit=500)
        invoices = []

        for opp in opportunities:
            status_type = opp.get("status_type", "")
            value = float(opp.get("value") or 0)

            if status_type != "won" or value <= 0:
                continue

            value_in_currency = value / 100.0

            date_won_str = opp.get("date_won", "") or opp.get("date_created", "")
            try:
                opp_date = datetime.fromisoformat(date_won_str.replace("Z", "+00:00")) if date_won_str else datetime.now()
            except (ValueError, TypeError):
                opp_date = datetime.now()

            if start_date and opp_date < start_date:
                continue
            if end_date and opp_date > end_date:
                continue

            currency = opp.get("value_currency", "USD")

            invoices.append(
                InvoiceRecord(
                    external_id=opp.get("id", ""),
                    date=opp_date,
                    customer_name=opp.get("lead_name", "") or opp.get("note", ""),
                    amount=value_in_currency,
                    total=value_in_currency,
                    currency=currency,
                    status="paid",
                    metadata={
                        "status_type": status_type,
                        "confidence": opp.get("confidence", 0),
                        "lead_id": opp.get("lead_id", ""),
                        "source": "close_crm_opportunity",
                    },
                )
            )

        return invoices

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        leads = await self.get_leads(limit=500)
        entries = []

        for lead in leads:
            lead_id = lead.get("id", "")
            display_name = lead.get("display_name", "Unknown Lead")

            created_str = lead.get("date_created", "")
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
                    external_id=f"close_lead_{lead_id}",
                    date=created_date,
                    account_code=lead_id,
                    account_name=display_name,
                    debit=0.0,
                    credit=0.0,
                    description=f"Lead: {display_name} - Status: {lead.get('status_label', 'N/A')}",
                    category="CRM Lead",
                    metadata={
                        "status_id": lead.get("status_id", ""),
                        "status_label": lead.get("status_label", ""),
                        "contacts_count": len(lead.get("contacts", [])),
                        "opportunities_count": len(lead.get("opportunities", [])),
                        "source": "close_crm_lead",
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
            "source_type": "connector_close_crm",
            "extraction_summary": "Synced from Close CRM",
        }

        if invoices:
            result["revenue"] = sum(inv.total for inv in invoices)
            result["opportunities_won"] = len(invoices)

        if ledger_entries:
            result["leads_count"] = len(ledger_entries)

        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check api_key"],
                    sync_started=sync_started,
                )

            leads = await self.get_leads(limit=200)
            opportunities = await self.get_opportunities(limit=200)
            activities = await self.get_activities(limit=200)
            invoices = await self.fetch_invoices()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(invoices=invoices, ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(leads) + len(opportunities) + len(activities),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "leads_count": len(leads),
                    "opportunities_count": len(opportunities),
                    "activities_count": len(activities),
                },
            )

        except Exception as e:
            logger.error(f"Close CRM sync failed: {e}")
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
