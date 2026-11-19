"""
Amplitude Analytics Connector - Product analytics and user behavior data.

Provides:
- User activity and search
- Event segmentation data
- Cohort definitions and membership
- Retention analysis

API Documentation: https://amplitude.com/docs/apis/analytics/dashboard-rest
Cohorts: https://amplitude.com/docs/apis/analytics/behavioral-cohorts

Credentials: api_key + secret_key; optional region ("eu" for the EU data centre).
"""

import httpx
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

# REST hosts. EU projects use analytics.eu.amplitude.com (never analytics.amplitude.com, the web app).
US_HOST = "https://amplitude.com"
EU_HOST = "https://analytics.eu.amplitude.com"
BASE_URL = US_HOST

# Amplitude special event types: _active = "Any Active Event", _all = "Any Event".
ACTIVE_EVENT = "_active"
ALL_EVENTS = "_all"
_LEGACY_EVENT_NAMES = {"any active event": ACTIVE_EVENT, "any event": ALL_EVENTS}


def host_for_region(region: Optional[str]) -> str:
    return EU_HOST if str(region or "").strip().lower() == "eu" else US_HOST


def _event_param(event_type: str) -> str:
    event_type = _LEGACY_EVENT_NAMES.get(str(event_type).strip().lower(), event_type)
    return json.dumps({"event_type": event_type})


def _parse_retention_date(label: str, start: datetime, end: datetime) -> Optional[datetime]:
    """Retention cohort labels look like "Aug 14" (no year); some responses use YYYY-MM-DD."""
    if not isinstance(label, str) or not label:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(label, fmt)
        except ValueError:
            pass
    try:
        month_day = datetime.strptime(f"2000 {label.strip()}", "%Y %b %d")
    except ValueError:
        return None
    # Pick the year that places the label inside the requested range (handles Dec->Jan).
    for year in range(end.year, start.year - 2, -1):
        try:
            candidate = month_day.replace(year=year)
        except ValueError:  # Feb 29 in a non-leap year
            continue
        if candidate.date() <= end.date():
            return candidate
    return None


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
        self._region = (config.credentials or {}).get("region") or (config.settings or {}).get("region") or ""
        self._host = host_for_region(self._region)
        self._client: Optional[httpx.AsyncClient] = None

    def _basic_auth_header(self) -> str:
        credentials = f"{self._api_key}:{self._secret_key}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._host,
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
                "e": _event_param(ACTIVE_EVENT),
                "start": start.strftime("%Y%m%d"),
                "end": end.strftime("%Y%m%d"),
            }
            response = await client.get("/api/2/events/segmentation", params=params)

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
                "e": _event_param(ACTIVE_EVENT),
                "start": start.strftime("%Y%m%d"),
                "end": end.strftime("%Y%m%d"),
            }
            response = await client.get("/api/2/events/segmentation", params=params)
            return response.status_code == 200
        except Exception:
            return False

    async def search_users(self, user_query: str) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            response = await client.get("/api/2/usersearch", params={"user": user_query})

            if response.status_code == 200:
                data = response.json()
                return data.get("matches", data if isinstance(data, list) else [])
            return []
        except Exception as e:
            logger.error(f"Amplitude user search error: {e}")
            return []

    async def get_event_segmentation(
        self,
        event_type: str = ACTIVE_EVENT,
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
                "e": _event_param(event_type),
                "start": start_date.strftime("%Y%m%d"),
                "end": end_date.strftime("%Y%m%d"),
                "m": "uniques",
            }
            response = await client.get("/api/2/events/segmentation", params=params)

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
            response = await client.get("/api/3/cohorts")

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
                # se accepts _new/_active; re accepts _all/_active.
                "se": _event_param(ACTIVE_EVENT),
                "re": _event_param(ACTIVE_EVENT),
                "start": start_date.strftime("%Y%m%d"),
                "end": end_date.strftime("%Y%m%d"),
            }
            response = await client.get("/api/2/retention", params=params)

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
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        event_data = await self.get_event_segmentation(
            event_type=ACTIVE_EVENT,
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
                            "event_type": ACTIVE_EVENT,
                            "source": "amplitude",
                        },
                    )
                )

        retention_data = await self.get_retention(start_date, end_date)
        retention_series = (retention_data.get("data") or {}).get("series") or []
        first_series = retention_series[0] if retention_series and isinstance(retention_series[0], dict) else {}
        cohort_values = first_series.get("values") or {}

        retention_entries: List[LedgerEntry] = []
        # values[date][0] = cohort size, [1] = Day 0, [2] = Day 1 (N+1 = N intervals out).
        for label, buckets in cohort_values.items():
            if not isinstance(buckets, list) or len(buckets) < 3:
                continue
            day1 = buckets[2] if isinstance(buckets[2], dict) else {}
            if day1.get("incomplete"):
                continue
            cohort_date = _parse_retention_date(label, start_date, end_date)
            if cohort_date is None:
                continue
            first = buckets[0] if isinstance(buckets[0], dict) else {}
            count = float(first.get("count") or first.get("outof") or 0)
            retained = float(day1.get("count") or 0)
            retention_rate = (retained / count * 100) if count > 0 else 0
            date_str = cohort_date.strftime("%Y-%m-%d")

            retention_entries.append(
                LedgerEntry(
                    external_id=f"amp-ret-{date_str}",
                    date=cohort_date,
                    account_code="5001",
                    account_name="User Retention",
                    debit=0.0,
                    credit=retention_rate,
                    description=f"Day 1 retention for cohort {date_str}: {retention_rate:.1f}%",
                    category="Product Metrics - Retention",
                    metadata={
                        "metric_type": "retention",
                        "cohort_size": count,
                        "retained_count": retained,
                        "source": "amplitude",
                    },
                )
            )

        # Cohorts arrive newest-first; keep oldest-first so [-1] is the latest.
        entries.extend(sorted(retention_entries, key=lambda e: e.date))
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
