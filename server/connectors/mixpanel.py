"""
Mixpanel Analytics Connector - Event analytics, funnels, and retention data.

Provides:
- Event tracking and insights
- Funnel analysis
- Retention cohort data
- User engagement metrics

API Documentation: https://developer.mixpanel.com/reference/overview
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

BASE_URL = "https://mixpanel.com/api/2.0"


@ConnectorRegistry.register
class MixpanelConnector(BaseConnector):
    PROVIDER_ID = "mixpanel"
    PROVIDER_NAME = "Mixpanel"
    PROVIDER_DESCRIPTION = "Product analytics for event tracking, funnel analysis, and user retention. Map analytics data as ledger entries for business intelligence."
    PROVIDER_CATEGORY = ProviderCategory.CRM
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developer.mixpanel.com/reference/overview"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._project_id = config.credentials.get("project_id", "")
        self._api_secret = config.credentials.get("api_secret", "")
        self._service_account_user = config.credentials.get("service_account_user", "")
        self._service_account_secret = config.credentials.get("service_account_secret", "")
        self._client: Optional[httpx.AsyncClient] = None

    def _auth_header(self) -> str:
        if self._service_account_user and self._service_account_secret:
            credentials = base64.b64encode(
                f"{self._service_account_user}:{self._service_account_secret}".encode()
            ).decode()
        else:
            credentials = base64.b64encode(f"{self._api_secret}:".encode()).decode()
        return f"Basic {credentials}"

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": self._auth_header(),
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        has_secret = bool(self._api_secret)
        has_service_account = bool(self._service_account_user and self._service_account_secret)

        if not self._project_id or (not has_secret and not has_service_account):
            logger.warning("Mixpanel credentials incomplete (need project_id and api_secret or service account)")
            return False

        try:
            client = await self._get_client()
            today = datetime.now().strftime("%Y-%m-%d")
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            params = {
                "project_id": self._project_id,
                "from_date": week_ago,
                "to_date": today,
            }
            response = await client.get("/insights", params=params)

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Mixpanel authentication successful")
                return True
            elif response.status_code == 401:
                logger.warning("Mixpanel auth failed: invalid credentials")
                return False
            else:
                logger.warning(f"Mixpanel auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Mixpanel authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            today = datetime.now().strftime("%Y-%m-%d")
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            params = {
                "project_id": self._project_id,
                "from_date": week_ago,
                "to_date": today,
            }
            response = await client.get("/insights", params=params)
            return response.status_code == 200
        except Exception:
            return False

    async def get_insights(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self._authenticated:
            if not await self.authenticate():
                return {}

        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        try:
            client = await self._get_client()
            params = {
                "project_id": self._project_id,
                "from_date": from_date,
                "to_date": to_date,
            }
            response = await client.get("/insights", params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Mixpanel insights error: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Mixpanel insights fetch error: {e}")
            return {}

    async def get_funnels(self, funnel_id: Optional[str] = None) -> Dict[str, Any]:
        if not self._authenticated:
            if not await self.authenticate():
                return {}

        try:
            client = await self._get_client()
            today = datetime.now().strftime("%Y-%m-%d")
            month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            params: Dict[str, Any] = {
                "project_id": self._project_id,
                "from_date": month_ago,
                "to_date": today,
            }
            if funnel_id:
                params["funnel_id"] = funnel_id

            response = await client.get("/funnels", params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Mixpanel funnels error: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Mixpanel funnels fetch error: {e}")
            return {}

    async def get_retention(self, days: int = 30) -> Dict[str, Any]:
        if not self._authenticated:
            if not await self.authenticate():
                return {}

        try:
            client = await self._get_client()
            today = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            params = {
                "project_id": self._project_id,
                "from_date": start,
                "to_date": today,
            }
            response = await client.get("/retention", params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Mixpanel retention error: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Mixpanel retention fetch error: {e}")
            return {}

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        from_date = start_date.strftime("%Y-%m-%d")
        to_date = end_date.strftime("%Y-%m-%d")

        insights_data = await self.get_insights(from_date=from_date, to_date=to_date)
        entries = []

        series = insights_data.get("series", {})
        for event_name, date_data in series.items():
            if not isinstance(date_data, dict):
                continue

            for date_str, value in date_data.items():
                try:
                    entry_date = datetime.strptime(date_str, "%Y-%m-%d")
                except (ValueError, TypeError):
                    continue

                event_count = float(value) if isinstance(value, (int, float)) else 0

                entries.append(
                    LedgerEntry(
                        external_id=f"mixpanel_{self._project_id}_{event_name}_{date_str}",
                        date=entry_date,
                        account_code=f"mixpanel_{self._project_id}",
                        account_name="Mixpanel Analytics",
                        debit=0.0,
                        credit=0.0,
                        description=f"Event: {event_name} - Count: {int(event_count)}",
                        category="Analytics Event",
                        metadata={
                            "event_name": event_name,
                            "event_count": event_count,
                            "project_id": self._project_id,
                            "source": "mixpanel_insights",
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
            "source_type": "connector_mixpanel",
            "extraction_summary": f"Synced from Mixpanel (project {self._project_id})",
        }

        if ledger_entries:
            total_events = sum(e.metadata.get("event_count", 0) for e in ledger_entries)
            unique_events = len(set(e.metadata.get("event_name", "") for e in ledger_entries))
            result["total_events"] = total_events
            result["unique_event_types"] = unique_events
            result["days_tracked"] = len(set(e.date.strftime("%Y-%m-%d") for e in ledger_entries))

        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check project_id and api_secret"],
                    sync_started=sync_started,
                )

            insights = await self.get_insights()
            funnels = await self.get_funnels()
            retention = await self.get_retention(days=30)
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(ledger),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "insights_available": bool(insights),
                    "funnels_available": bool(funnels),
                    "retention_available": bool(retention),
                    "ledger_entries_count": len(ledger),
                },
            )

        except Exception as e:
            logger.error(f"Mixpanel sync failed: {e}")
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
