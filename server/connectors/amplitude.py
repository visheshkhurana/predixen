"""
Amplitude Analytics Connector - Product analytics and user behavior data.

Provides:
- User activity and search
- Event segmentation data
- Cohort definitions and membership
- Retention analysis

API Documentation: https://www.docs.developers.amplitude.com/analytics/apis/
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

BASE_URL = "https://amplitude.com/api/2"


@ConnectorRegistry.register
class AmplitudeConnector(BaseConnector):
    PROVIDER_ID = "amplitude"
    PROVIDER_NAME = "Amplitude"
    PROVIDER_DESCRIPTION = "Product analytics platform. Import user activity, event segmentation, cohorts, and retention data for product-led growth metrics."
    PROVIDER_CATEGORY = ProviderCategory.CRM
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://www.docs.developers.amplitude.com/analytics/apis/"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_key = config.credentials.get("api_key", "")
        self._secret_key = config.credentials.get("secret_key", "")
        self._client: Optional[httpx.AsyncClient] = None

    def _basic_auth_header(self) -> str:
        credentials = f"{self._api_key}:{self._secret_key}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

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
        if not self._api_key or not self._secret_key:
            logger.warning("Amplitude API key or secret key not provided")
            return False

        try:
            client = await self._get_client()
            end = datetime.now()
            start = end - timedelta(days=1)
            params = {
                "start": start.strftime("%Y%m%d"),
                "end": end.strftime("%Y%m%d"),
            }
            response = await client.get("/events/segmentation", params=params)

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Amplitude authentication successful")
                return True
            elif response.status_code == 401:
                logger.warning("Amplitude auth failed: invalid credentials")
                return False
            else:
                logger.warning(f"Amplitude auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Amplitude authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            end = datetime.now()
            start = end - timedelta(days=1)
            params = {
                "start": start.strftime("%Y%m%d"),
                "end": end.strftime("%Y%m%d"),
            }
            response = await client.get("/events/segmentation", params=params)
            return response.status_code == 200
        except Exception:
            return False

    async def search_users(self, user_query: str) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            response = await client.get("/usersearch", params={"user": user_query})

            if response.status_code == 200:
                data = response.json()
                return data.get("matches", data if isinstance(data, list) else [])
            return []
        except Exception as e:
            logger.error(f"Amplitude user search error: {e}")
            return []

    async def get_event_segmentation(
        self,
        event_type: str = "Any Active Event",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        if not self._authenticated:
            if not await self.authenticate():
                return {}

        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        try:
            client = await self._get_client()
            params = {
                "e": f'{{"event_type":"{event_type}"}}',
                "start": start_date.strftime("%Y%m%d"),
                "end": end_date.strftime("%Y%m%d"),
                "m": "uniques",
            }
            response = await client.get("/events/segmentation", params=params)

            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Amplitude event segmentation error: {e}")
            return {}

    async def get_cohorts(self) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            response = await client.get("/cohorts")

            if response.status_code == 200:
                data = response.json()
                return data.get("cohorts", data if isinstance(data, list) else [])
            return []
        except Exception as e:
            logger.error(f"Amplitude cohorts fetch error: {e}")
            return []

    async def get_retention(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        if not self._authenticated:
            if not await self.authenticate():
                return {}

        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        try:
            client = await self._get_client()
            params = {
                "se": '{"event_type":"Any Active Event"}',
                "re": '{"event_type":"Any Active Event"}',
                "start": start_date.strftime("%Y%m%d"),
                "end": end_date.strftime("%Y%m%d"),
            }
            response = await client.get("/retention", params=params)

            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Amplitude retention fetch error: {e}")
            return {}

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        event_data = await self.get_event_segmentation(
            event_type="Any Active Event",
            start_date=start_date,
            end_date=end_date,
        )

        entries = []
        series_data = event_data.get("data", {}).get("series", [])
        x_values = event_data.get("data", {}).get("xValues", [])

        if series_data and x_values:
            values = series_data[0] if series_data else []
            for i, date_str in enumerate(x_values):
                if i >= len(values):
                    break

                try:
                    entry_date = datetime.strptime(date_str, "%Y-%m-%d")
                except (ValueError, TypeError):
                    continue

                user_count = float(values[i]) if values[i] else 0

                entries.append(
                    LedgerEntry(
                        external_id=f"amp-dau-{date_str}",
                        date=entry_date,
                        account_code="5000",
                        account_name="Daily Active Users",
                        debit=0.0,
                        credit=user_count,
                        description=f"DAU for {date_str}",
                        category="Product Metrics - Users",
                        metadata={
                            "metric_type": "dau",
                            "event_type": "Any Active Event",
                            "source": "amplitude",
                        },
                    )
                )

        retention_data = await self.get_retention(start_date, end_date)
        retention_counts = retention_data.get("data", {}).get("retentionCounts", [])

        if retention_counts:
            for i, cohort in enumerate(retention_counts):
                date_str = cohort.get("date", "")
                if not date_str:
                    continue

                try:
                    cohort_date = datetime.strptime(date_str, "%Y-%m-%d")
                except (ValueError, TypeError):
                    continue

                count = float(cohort.get("count", 0))
                retained = float(cohort.get("retainedCount", 0))
                retention_rate = (retained / count * 100) if count > 0 else 0

                entries.append(
                    LedgerEntry(
                        external_id=f"amp-ret-{date_str}",
                        date=cohort_date,
                        account_code="5001",
                        account_name="User Retention",
                        debit=0.0,
                        credit=retention_rate,
                        description=f"Retention rate for cohort {date_str}: {retention_rate:.1f}%",
                        category="Product Metrics - Retention",
                        metadata={
                            "metric_type": "retention",
                            "cohort_size": count,
                            "retained_count": retained,
                            "source": "amplitude",
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
            "source_type": "connector_amplitude",
            "extraction_summary": "Synced from Amplitude Analytics",
        }

        if ledger_entries:
            dau_entries = [e for e in ledger_entries if e.metadata.get("metric_type") == "dau"]
            if dau_entries:
                latest_dau = dau_entries[-1].credit
                avg_dau = sum(e.credit for e in dau_entries) / len(dau_entries)
                result["dau"] = latest_dau
                result["avg_dau"] = avg_dau

            retention_entries = [e for e in ledger_entries if e.metadata.get("metric_type") == "retention"]
            if retention_entries:
                latest_retention = retention_entries[-1].credit
                avg_retention = sum(e.credit for e in retention_entries) / len(retention_entries)
                result["retention_rate"] = latest_retention
                result["avg_retention_rate"] = avg_retention

            result["analytics_entries_count"] = len(ledger_entries)

        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check api_key and secret_key"],
                    sync_started=sync_started,
                )

            ledger = await self.fetch_ledger()
            cohorts = await self.get_cohorts()
            financials = self.map_to_financials(ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(ledger) + len(cohorts),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "ledger_entries_count": len(ledger),
                    "cohorts_count": len(cohorts),
                },
            )

        except Exception as e:
            logger.error(f"Amplitude sync failed: {e}")
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
