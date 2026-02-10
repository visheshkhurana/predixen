"""
Google Analytics GA4 Connector - Web analytics and conversion data.

Provides:
- Session and user metrics
- Conversion tracking
- Traffic source analytics
- Page view and engagement data

API Documentation: https://developers.google.com/analytics/devguides/reporting/data/v1
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

BASE_URL = "https://analyticsdata.googleapis.com/v1beta"


@ConnectorRegistry.register
class GoogleAnalyticsConnector(BaseConnector):
    PROVIDER_ID = "google_analytics"
    PROVIDER_NAME = "Google Analytics"
    PROVIDER_DESCRIPTION = "GA4 web analytics for sessions, users, conversions, and traffic source data. Map analytics metrics as ledger-like entries for financial correlation."
    PROVIDER_CATEGORY = ProviderCategory.CRM
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developers.google.com/analytics/devguides/reporting/data/v1"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._property_id = config.credentials.get("property_id", "")
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
        if not self._property_id or not self._access_token:
            logger.warning("Google Analytics credentials incomplete (need property_id and access_token)")
            return False

        try:
            client = await self._get_client()
            payload = {
                "dateRanges": [{"startDate": "7daysAgo", "endDate": "today"}],
                "metrics": [{"name": "sessions"}],
            }
            response = await client.post(
                f"/properties/{self._property_id}:runReport",
                json=payload,
            )

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Google Analytics authentication successful")
                return True
            else:
                logger.warning(f"Google Analytics auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Google Analytics authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            payload = {
                "dateRanges": [{"startDate": "1daysAgo", "endDate": "today"}],
                "metrics": [{"name": "sessions"}],
            }
            response = await client.post(
                f"/properties/{self._property_id}:runReport",
                json=payload,
            )
            return response.status_code == 200
        except Exception:
            return False

    async def run_report(
        self,
        metrics: List[str],
        dimensions: Optional[List[str]] = None,
        start_date: str = "30daysAgo",
        end_date: str = "today",
    ) -> Dict[str, Any]:
        if not self._authenticated:
            if not await self.authenticate():
                return {}

        try:
            client = await self._get_client()
            payload: Dict[str, Any] = {
                "dateRanges": [{"startDate": start_date, "endDate": end_date}],
                "metrics": [{"name": m} for m in metrics],
            }
            if dimensions:
                payload["dimensions"] = [{"name": d} for d in dimensions]

            response = await client.post(
                f"/properties/{self._property_id}:runReport",
                json=payload,
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"GA4 report error: {response.status_code} - {response.text[:200]}")
                return {}
        except Exception as e:
            logger.error(f"GA4 report fetch error: {e}")
            return {}

    async def get_session_metrics(self, days: int = 30) -> Dict[str, Any]:
        start_date = f"{days}daysAgo"
        return await self.run_report(
            metrics=["sessions", "totalUsers", "newUsers", "bounceRate", "averageSessionDuration"],
            start_date=start_date,
        )

    async def get_conversion_metrics(self, days: int = 30) -> Dict[str, Any]:
        start_date = f"{days}daysAgo"
        return await self.run_report(
            metrics=["conversions", "totalRevenue", "transactions"],
            start_date=start_date,
        )

    async def get_traffic_sources(self, days: int = 30) -> Dict[str, Any]:
        start_date = f"{days}daysAgo"
        return await self.run_report(
            metrics=["sessions", "totalUsers", "conversions"],
            dimensions=["sessionSource", "sessionMedium"],
            start_date=start_date,
        )

    async def get_daily_metrics(self, days: int = 30) -> Dict[str, Any]:
        start_date = f"{days}daysAgo"
        return await self.run_report(
            metrics=["sessions", "totalUsers", "conversions", "totalRevenue"],
            dimensions=["date"],
            start_date=start_date,
        )

    def _parse_report_rows(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows = report.get("rows", [])
        metric_headers = [h.get("name", "") for h in report.get("metricHeaders", [])]
        dimension_headers = [h.get("name", "") for h in report.get("dimensionHeaders", [])]
        parsed = []

        for row in rows:
            entry: Dict[str, Any] = {}
            dim_values = row.get("dimensionValues", [])
            met_values = row.get("metricValues", [])

            for i, header in enumerate(dimension_headers):
                entry[header] = dim_values[i].get("value", "") if i < len(dim_values) else ""
            for i, header in enumerate(metric_headers):
                val = met_values[i].get("value", "0") if i < len(met_values) else "0"
                try:
                    entry[header] = float(val)
                except ValueError:
                    entry[header] = val

            parsed.append(entry)

        return parsed

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        days = 30
        if start_date and end_date:
            days = max((end_date - start_date).days, 1)

        daily_report = await self.get_daily_metrics(days=days)
        rows = self._parse_report_rows(daily_report)
        entries = []

        for row in rows:
            date_str = row.get("date", "")
            try:
                entry_date = datetime.strptime(date_str, "%Y%m%d") if date_str else datetime.now()
            except (ValueError, TypeError):
                entry_date = datetime.now()

            sessions = float(row.get("sessions", 0))
            users = float(row.get("totalUsers", 0))
            conversions = float(row.get("conversions", 0))
            revenue = float(row.get("totalRevenue", 0))

            entries.append(
                LedgerEntry(
                    external_id=f"ga4_{self._property_id}_{date_str}",
                    date=entry_date,
                    account_code=f"ga4_{self._property_id}",
                    account_name="Google Analytics",
                    debit=0.0,
                    credit=revenue,
                    description=f"Sessions: {int(sessions)}, Users: {int(users)}, Conversions: {int(conversions)}",
                    category="Analytics",
                    metadata={
                        "sessions": sessions,
                        "total_users": users,
                        "conversions": conversions,
                        "revenue": revenue,
                        "source": "google_analytics_ga4",
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
            "source_type": "connector_google_analytics",
            "extraction_summary": f"Synced from Google Analytics (property {self._property_id})",
        }

        if ledger_entries:
            result["total_revenue"] = sum(e.credit for e in ledger_entries)
            total_sessions = sum(e.metadata.get("sessions", 0) for e in ledger_entries)
            total_users = sum(e.metadata.get("total_users", 0) for e in ledger_entries)
            total_conversions = sum(e.metadata.get("conversions", 0) for e in ledger_entries)
            result["total_sessions"] = total_sessions
            result["total_users"] = total_users
            result["total_conversions"] = total_conversions
            result["days_tracked"] = len(ledger_entries)

        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check property_id and access_token"],
                    sync_started=sync_started,
                )

            session_data = await self.get_session_metrics(days=30)
            conversion_data = await self.get_conversion_metrics(days=30)
            traffic_data = await self.get_traffic_sources(days=30)
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(ledger_entries=ledger)

            session_rows = self._parse_report_rows(session_data)
            conversion_rows = self._parse_report_rows(conversion_data)
            traffic_rows = self._parse_report_rows(traffic_data)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(ledger) + len(traffic_rows),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "session_summary": session_rows[0] if session_rows else {},
                    "conversion_summary": conversion_rows[0] if conversion_rows else {},
                    "traffic_sources_count": len(traffic_rows),
                    "daily_entries_count": len(ledger),
                },
            )

        except Exception as e:
            logger.error(f"Google Analytics sync failed: {e}")
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
