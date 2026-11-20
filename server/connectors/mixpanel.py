"""
Mixpanel Analytics Connector - Event analytics, funnels, and retention data.

Provides:
- Event tracking and insights
- Funnel analysis
- Retention cohort data
- User engagement metrics

API Documentation: https://docs.mixpanel.com/reference/query-api

Credentials: project_id + api_secret (or service_account_user/secret); optional
region (us/eu/in), bookmark_id (saved Insights report) and funnel_id.
"""

import httpx
from .http import http_client
import json
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

# Query API servers: https://{regionAndDomain}.com/api/query (docs.mixpanel.com/reference/query-api)
REGION_HOSTS = {
    "us": "mixpanel.com",
    "eu": "eu.mixpanel.com",
    "in": "in.mixpanel.com",
}
BASE_URL = "https://mixpanel.com/api/query"


def base_url_for_region(region: Optional[str]) -> str:
    host = REGION_HOSTS.get(str(region or "us").strip().lower(), REGION_HOSTS["us"])
    return f"https://{host}/api/query"


def _parse_series_date(value: Any) -> Optional[datetime]:
    """Insights returns ISO timestamps (2020-08-31T00:00:00-07:00); /events returns 2020-08-31."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Keep the report's local calendar date; ledger dates are naive.
    return parsed.replace(tzinfo=None)


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
        creds = config.credentials or {}
        settings = config.settings or {}
        self._region = creds.get("region") or settings.get("region") or "us"
        self._base_url = base_url_for_region(self._region)
        # Insights needs a saved report (bookmark_id); funnels need a saved funnel_id.
        self._bookmark_id = str(creds.get("bookmark_id") or settings.get("bookmark_id") or "")
        self._funnel_id = str(creds.get("funnel_id") or settings.get("funnel_id") or "")
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
            self._client = http_client(
                base_url=self._base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": self._auth_header(),
                },
            )
        return self._client

    async def _probe(self) -> httpx.Response:
        """Cheapest Query API call that needs no saved report: this month's top event names.

        GET /events/names requires project_id and type; works with a service
        account or the project api_secret (docs.mixpanel.com/reference/query-months-top-event-names).
        """
        client = await self._get_client()
        return await client.get(
            "/events/names",
            params={"project_id": self._project_id, "type": "general", "limit": 1},
        )

    async def get_top_event_names(self, limit: int = 10) -> List[str]:
        client = await self._get_client()
        response = await client.get(
            "/events/names",
            params={"project_id": self._project_id, "type": "general", "limit": limit},
        )
        if response.status_code != 200:
            logger.error(f"Mixpanel event names error: {response.status_code}")
            return []
        data = response.json()
        return [str(n) for n in data] if isinstance(data, list) else []

    async def get_event_counts(self, from_date: str, to_date: str, limit: int = 10) -> Dict[str, Any]:
        """Aggregate daily counts for the top events (GET /events). Returns {"series": {event: {date: n}}}."""
        names = await self.get_top_event_names(limit=limit)
        if not names:
            return {}
        client = await self._get_client()
        response = await client.get(
            "/events",
            params={
                "project_id": self._project_id,
                "event": json.dumps(names),
                "type": "general",
                "unit": "day",
                "from_date": from_date,
                "to_date": to_date,
            },
        )
        if response.status_code != 200:
            logger.error(f"Mixpanel event counts error: {response.status_code}")
            return {}
        values = (response.json().get("data") or {}).get("values") or {}
        return {"series": values}

    async def authenticate(self) -> bool:
        has_secret = bool(self._api_secret)
        has_service_account = bool(self._service_account_user and self._service_account_secret)

        if not self._project_id or (not has_secret and not has_service_account):
            logger.warning("Mixpanel credentials incomplete (need project_id and api_secret or service account)")
            return False

        try:
            response = await self._probe()

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
            response = await self._probe()
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

        if not self._bookmark_id:
            # /insights only queries a saved report; without one, use aggregate event counts.
            return await self.get_event_counts(from_date=from_date, to_date=to_date)

        try:
            client = await self._get_client()
            params = {
                "project_id": self._project_id,
                "bookmark_id": self._bookmark_id,
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
        funnel_id = funnel_id or self._funnel_id
        if not funnel_id:
            # /funnels requires funnel_id (docs.mixpanel.com/reference/funnels-query).
            return {}
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
                # Default "birth" retention requires a born_event; compounded
                # (recurring) retention needs none.
                "retention_type": "compounded",
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
                entry_date = _parse_series_date(date_str)
                if entry_date is None:
                    continue
                day = entry_date.strftime("%Y-%m-%d")

                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                event_count = float(value)

                entries.append(
                    LedgerEntry(
                        external_id=f"mixpanel_{self._project_id}_{event_name}_{day}",
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
                            "source": "mixpanel_insights" if self._bookmark_id else "mixpanel_events",
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

            # fetch_ledger already runs the insights/event-count query; the Query API
            # allows 60 queries/hour, so don't issue it twice.
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
                    "insights_available": bool(ledger),
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
