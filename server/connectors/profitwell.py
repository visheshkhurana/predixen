"""
ProfitWell (Paddle) Analytics Connector - Subscription metrics and revenue analytics.

Provides:
- MRR (Monthly Recurring Revenue) metrics
- Churn and retention data
- Subscription plan analytics
- Daily and monthly revenue metrics

API Documentation: https://profitwellapiv2.docs.apiary.io/
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

BASE_URL = "https://api.profitwell.com/v2"


@ConnectorRegistry.register
class ProfitWellConnector(BaseConnector):
    PROVIDER_ID = "profitwell"
    PROVIDER_NAME = "ProfitWell"
    PROVIDER_DESCRIPTION = "Subscription analytics platform (by Paddle). Import MRR, churn, retention metrics, and subscription revenue data."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://profitwellapiv2.docs.apiary.io/"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_token = config.credentials.get("api_token", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": self._api_token,
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._api_token:
            logger.warning("ProfitWell API token not provided")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/metrics/monthly/", params={"metrics": "recurring_revenue"})

            if response.status_code == 200:
                self._authenticated = True
                logger.info("ProfitWell authentication successful")
                return True
            else:
                logger.warning(f"ProfitWell auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"ProfitWell authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/metrics/monthly/", params={"metrics": "recurring_revenue"})
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _trends(payload: Any) -> Dict[str, List[Dict[str, Any]]]:
        """Return ``{trend_name: [{"date", "value"}, ...]}`` from a metrics response."""
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            return {k: v for k, v in payload["data"].items() if isinstance(v, list)}
        return {}

    async def get_daily_metrics(self, month: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Daily trends for one month (``YYYY-MM``; API allows only the
        current or previous month). Dates in the result are ``YYYY-MM-DD``."""
        if not self._authenticated:
            if not await self.authenticate():
                return {}
        month = month or datetime.now().strftime("%Y-%m")
        try:
            client = await self._get_client()
            response = await client.get("/metrics/daily/", params={"month": month})
            if response.status_code != 200:
                logger.error(f"ProfitWell daily metrics error: {response.status_code} - {response.text[:200]}")
                return {}
            return self._trends(response.json())
        except Exception as e:
            logger.error(f"ProfitWell daily metrics fetch error: {e}")
            return {}

    async def get_monthly_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """One row per month: ``{"month": "YYYY-MM", <trend>: value, ...}``.

        The monthly endpoint returns the full history in a single call (it
        accepts only ``metrics``/``plan_id``); we filter to the window here.
        Amount values are already in the account currency (not cents).
        """
        if not self._authenticated:
            if not await self.authenticate():
                return []

        if not start_date:
            start_date = datetime.now() - timedelta(days=365)
        if not end_date:
            end_date = datetime.now()
        lo, hi = start_date.strftime("%Y-%m"), end_date.strftime("%Y-%m")

        try:
            client = await self._get_client()
            response = await client.get("/metrics/monthly/")
            if response.status_code != 200:
                logger.error(f"ProfitWell monthly metrics error: {response.status_code} - {response.text[:200]}")
                return []

            by_month: Dict[str, Dict[str, Any]] = {}
            for trend, points in self._trends(response.json()).items():
                for point in points:
                    if not isinstance(point, dict):
                        continue
                    month = str(point.get("date") or "")[:7]
                    if not month or month < lo or month > hi:
                        continue
                    by_month.setdefault(month, {"month": month})[trend] = point.get("value")
            return [by_month[m] for m in sorted(by_month)]

        except Exception as e:
            logger.error(f"ProfitWell monthly metrics fetch error: {e}")
            return []

    async def get_customers(self, limit: int = 1000, per_page: int = 250) -> List[Dict[str, Any]]:
        """Customers via ``GET /v2/customers/`` (page/per_page paging, max 250)."""
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            customers: List[Dict[str, Any]] = []
            page = 1
            per_page = max(1, min(per_page, 250))
            while len(customers) < limit:
                response = await client.get("/customers/", params={"page": page, "per_page": per_page})
                if response.status_code != 200:
                    logger.error(f"ProfitWell customers error: {response.status_code}")
                    break
                data = response.json()
                rows = data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
                customers.extend(rows)
                if len(rows) < per_page:
                    break
                page += 1
            return customers[:limit]
        except Exception as e:
            logger.error(f"ProfitWell customers fetch error: {e}")
            return []

    # Back-compat alias: there is no list-subscriptions endpoint in API v2.
    async def get_subscriptions(self, limit: int = 1000) -> List[Dict[str, Any]]:
        return await self.get_customers(limit=limit)

    @staticmethod
    def _num(value: Any) -> float:
        try:
            return float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        monthly_metrics = await self.get_monthly_metrics(start_date, end_date)
        entries = []

        for metric in monthly_metrics:
            month_str = metric.get("month", datetime.now().strftime("%Y-%m"))
            try:
                metric_date = datetime.strptime(month_str, "%Y-%m")
            except (ValueError, TypeError):
                metric_date = datetime.now()

            # Values are in account currency units (not cents).
            mrr = self._num(metric.get("recurring_revenue"))
            if mrr > 0:
                entries.append(
                    LedgerEntry(
                        external_id=f"pw-mrr-{month_str}",
                        date=metric_date,
                        account_code="4000",
                        account_name="Monthly Recurring Revenue",
                        debit=0.0,
                        credit=mrr,
                        description=f"MRR for {month_str}",
                        category="Revenue - Recurring",
                        metadata={
                            "metric_type": "mrr",
                            "source": "profitwell",
                        },
                    )
                )

            new_mrr = self._num(metric.get("new_recurring_revenue"))
            if new_mrr > 0:
                entries.append(
                    LedgerEntry(
                        external_id=f"pw-new-{month_str}",
                        date=metric_date,
                        account_code="4001",
                        account_name="New MRR",
                        debit=0.0,
                        credit=new_mrr,
                        description=f"New MRR for {month_str}",
                        category="Revenue - New",
                        metadata={
                            "metric_type": "new_mrr",
                            "source": "profitwell",
                        },
                    )
                )

            churned = abs(self._num(metric.get("churned_recurring_revenue")))
            if churned > 0:
                entries.append(
                    LedgerEntry(
                        external_id=f"pw-churn-{month_str}",
                        date=metric_date,
                        account_code="4002",
                        account_name="Churned MRR",
                        debit=churned,
                        credit=0.0,
                        description=f"Churned MRR for {month_str}",
                        category="Revenue - Churn",
                        metadata={
                            "metric_type": "churned_mrr",
                            "source": "profitwell",
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
            "source_type": "connector_profitwell",
            "extraction_summary": "Synced from ProfitWell (Paddle) Analytics",
        }

        if ledger_entries:
            mrr_entries = [e for e in ledger_entries if e.metadata.get("metric_type") == "mrr"]
            if mrr_entries:
                latest_mrr = mrr_entries[-1].credit
                result["mrr"] = latest_mrr
                result["arr"] = latest_mrr * 12

            churn_entries = [e for e in ledger_entries if e.metadata.get("metric_type") == "churned_mrr"]
            if churn_entries and mrr_entries:
                latest_churn = churn_entries[-1].debit
                latest_mrr_val = mrr_entries[-1].credit
                result["churned_mrr"] = latest_churn
                result["churn_rate"] = (latest_churn / latest_mrr_val * 100) if latest_mrr_val > 0 else 0

            new_entries = [e for e in ledger_entries if e.metadata.get("metric_type") == "new_mrr"]
            if new_entries:
                result["new_mrr"] = new_entries[-1].credit

            result["revenue_entries_count"] = len(ledger_entries)

        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check api_token"],
                    sync_started=sync_started,
                )

            ledger = await self.fetch_ledger()
            subscriptions = await self.get_customers()
            financials = self.map_to_financials(ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(ledger) + len(subscriptions),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "ledger_entries_count": len(ledger),
                    "customers_count": len(subscriptions),
                },
            )

        except Exception as e:
            logger.error(f"ProfitWell sync failed: {e}")
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
