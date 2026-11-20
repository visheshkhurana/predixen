"""
Rippling HR Connector - employee and compensation data.

Uses Rippling's REST Platform API v2 at https://rest.ripplingapis.com, which is
what customer API tokens (Tools > Developer > API Tokens) are documented for.
The V1 platform API (api.rippling.com/platform/api/...) is legacy.

- Workers: GET /workers?limit=100&expand=user,department,compensation[&cursor=]
           paged via next_link.
           https://developer.rippling.com/documentation/rest-api/reference/list-workers
- Payroll: the v2 API does not document payroll runs, so none are fetched. Monthly
           payroll is estimated from active workers' annual compensation instead.
- Index:   https://developer.rippling.com/llms.txt
"""

import httpx
from .http import http_client
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

from .base import (
    BaseConnector,
    ConnectorConfig,
    AuthType,
    ProviderCategory,
    EmployeeRecord,
    PayrollRunRecord,
    SyncResult,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

BASE_URL = "https://rest.ripplingapis.com"
_API_HOST = urlparse(BASE_URL).hostname
PAGE_SIZE = 100  # documented maximum
MAX_PAGES = 200
WORKER_EXPAND = "user,department,compensation"


def _parse_date(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _money(value: Any) -> Optional[float]:
    if isinstance(value, dict):
        value = value.get("value")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


@ConnectorRegistry.register
class RipplingConnector(BaseConnector):
    PROVIDER_ID = "rippling"
    PROVIDER_NAME = "Rippling"
    PROVIDER_DESCRIPTION = "HR and payroll platform. Import employees, departments, headcount, and compensation."
    PROVIDER_CATEGORY = ProviderCategory.PAYROLL
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developer.rippling.com/documentation/rest-api"

    SUPPORTS_EMPLOYEES = True
    # Payroll runs are not in the documented v2 API; payroll cost is estimated from compensation.
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_key = (config.credentials.get("api_key") or "").strip()
        self._client: Optional[httpx.AsyncClient] = None
        self.auth_error: Optional[str] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = http_client(
                base_url=BASE_URL,
                timeout=30.0,
                follow_redirects=False,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        self.auth_error = None
        if not self._api_key:
            self.auth_error = "Enter a Rippling API token (Rippling > Tools > Developer > API Tokens)."
            return False

        try:
            client = await self._get_client()
            response = await client.get("/workers", params={"limit": 1})

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Rippling authentication successful")
                return True
            logger.warning(f"Rippling auth failed: {response.status_code}")
            if response.status_code in (401, 403):
                self.auth_error = (
                    "Rippling rejected the API token. Create one in Tools > Developer > API Tokens with "
                    "the workers.read scope (older V1 keys no longer work here)."
                )
            else:
                self.auth_error = f"Rippling returned {response.status_code}."
            return False
        except Exception as e:
            logger.error(f"Rippling authentication error: {e}")
            self.auth_error = "Could not reach Rippling. Try again."
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/workers", params={"limit": 1})
            return response.status_code == 200
        except Exception:
            return False

    def _next_request(self, next_link: Optional[str]) -> Optional[str]:
        """Follow next_link only on the Rippling API host."""
        if not next_link:
            return None
        parsed = urlparse(next_link)
        if parsed.scheme or parsed.netloc:
            if parsed.scheme != "https" or parsed.hostname != _API_HOST:
                logger.warning("Rippling next_link pointed off the API host; stopping")
                return None
            return parsed.path + (f"?{parsed.query}" if parsed.query else "")
        return next_link

    async def get_workers(self) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []
        client = await self._get_client()
        workers: List[Dict[str, Any]] = []
        request: Optional[str] = "/workers"
        params: Optional[Dict[str, Any]] = {"limit": PAGE_SIZE, "expand": WORKER_EXPAND}
        for _ in range(MAX_PAGES):
            response = await client.get(request, params=params)
            if response.status_code != 200:
                logger.error(f"Rippling workers error: {response.status_code}")
                break
            body = response.json() or {}
            workers.extend(w for w in body.get("results") or [] if isinstance(w, dict))
            request = self._next_request(body.get("next_link"))
            params = None  # next_link carries cursor, limit and expand
            if not request:
                break
        else:
            logger.warning(f"Rippling workers: stopped after {MAX_PAGES} pages; results truncated")
        return workers

    async def fetch_employees(self) -> List[EmployeeRecord]:
        employees = []
        for worker in await self.get_workers():
            user = worker.get("user") if isinstance(worker.get("user"), dict) else {}
            name_obj = user.get("name") if isinstance(user.get("name"), dict) else {}
            name = (
                user.get("display_name")
                or name_obj.get("formatted")
                or " ".join(p for p in (name_obj.get("given_name"), name_obj.get("family_name")) if p)
            )
            compensation = worker.get("compensation") if isinstance(worker.get("compensation"), dict) else {}
            annual = _money(compensation.get("annual_compensation"))
            if annual is None:
                monthly = _money(compensation.get("monthly_compensation"))
                annual = monthly * 12 if monthly is not None else None
            currency = (compensation.get("annual_compensation") or {}).get("currency_type") if isinstance(
                compensation.get("annual_compensation"), dict) else None
            department = worker.get("department") if isinstance(worker.get("department"), dict) else {}
            status = str(worker.get("status") or "").upper()
            employees.append(
                EmployeeRecord(
                    external_id=str(worker.get("id", "")),
                    name=name or worker.get("work_email") or "",
                    email=worker.get("work_email"),
                    department=department.get("name"),
                    designation=worker.get("title"),
                    salary=annual,
                    join_date=_parse_date(worker.get("start_date")),
                    status="active" if status in ("ACTIVE", "") else "terminated" if status == "TERMINATED" else status.lower(),
                    metadata={
                        "rippling_id": worker.get("id"),
                        "salary_currency": currency,
                        "end_date": worker.get("end_date"),
                        "manager_id": worker.get("manager_id"),
                    },
                )
            )
        return employees

    async def fetch_payroll_runs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[PayrollRunRecord]:
        # Not part of the documented v2 API; do not call the legacy V1 payroll endpoint.
        logger.info("Rippling: payroll runs are not available on the v2 API; using compensation instead")
        return []

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        result = {
            "source_type": "connector_rippling",
            "extraction_summary": "Synced from Rippling",
        }

        if employees:
            active = [e for e in employees if e.status == "active"]
            result["headcount"] = len(active)
            total_salary = sum(e.salary or 0 for e in active)
            result["annual_payroll"] = total_salary
            result["monthly_payroll"] = total_salary / 12 if total_salary > 0 else 0
            if total_salary > 0 and not payroll_runs:
                result["payroll"] = result["monthly_payroll"]
                result["extraction_summary"] = (
                    "Synced from Rippling (monthly payroll estimated from active workers' compensation)"
                )

        if payroll_runs:
            total_payroll_cost = sum(run.total_gross for run in payroll_runs)
            result["payroll"] = total_payroll_cost / max(len(payroll_runs), 1)
            result["total_payroll_cost"] = total_payroll_cost
            result["payroll_runs_count"] = len(payroll_runs)

        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=[self.auth_error or "Authentication failed - check api_key"],
                    sync_started=sync_started,
                )

            employees = await self.fetch_employees()
            financials = self.map_to_financials(employees=employees)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(employees),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "employees_count": len(employees),
                    "payroll_runs_count": 0,
                },
            )

        except Exception as e:
            logger.error(f"Rippling sync failed: {e}")
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
