"""
Rippling HR/Payroll Connector - Employee and payroll data integration.

Provides:
- Employee records and headcount
- Payroll run data (gross, deductions, net)
- Department structure
- Compensation details

API Documentation: https://developer.rippling.com/docs/rippling-api/
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

BASE_URL = "https://api.rippling.com"


@ConnectorRegistry.register
class RipplingConnector(BaseConnector):
    PROVIDER_ID = "rippling"
    PROVIDER_NAME = "Rippling"
    PROVIDER_DESCRIPTION = "HR, payroll, and benefits platform. Import employee data, payroll costs, headcount, departments, and compensation details."
    PROVIDER_CATEGORY = ProviderCategory.PAYROLL
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developer.rippling.com/docs/rippling-api/"

    SUPPORTS_EMPLOYEES = True
    SUPPORTS_PAYROLL = True
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_key = config.credentials.get("api_key", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._api_key:
            logger.warning("Rippling API key not provided")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/platform/api/employees?limit=1")

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Rippling authentication successful")
                return True
            else:
                logger.warning(f"Rippling auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Rippling authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/platform/api/employees?limit=1")
            return response.status_code == 200
        except Exception:
            return False

    async def get_departments(self) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            response = await client.get("/platform/api/departments")

            if response.status_code == 200:
                return response.json().get("results", response.json() if isinstance(response.json(), list) else [])
            return []
        except Exception as e:
            logger.error(f"Rippling departments fetch error: {e}")
            return []

    async def fetch_employees(self) -> List[EmployeeRecord]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        employees = []
        try:
            client = await self._get_client()
            next_url = "/platform/api/employees"

            while next_url:
                response = await client.get(next_url)

                if response.status_code != 200:
                    logger.error(f"Rippling employees error: {response.status_code}")
                    break

                data = response.json()
                results = data.get("results", data if isinstance(data, list) else [])

                for emp in results:
                    salary = None
                    compensation = emp.get("compensation", {})
                    if compensation:
                        rate = compensation.get("amount") or compensation.get("rate")
                        if rate:
                            rate_val = float(rate)
                            period = compensation.get("period", "").lower()
                            if period == "yearly" or period == "annual":
                                salary = rate_val
                            elif period == "monthly":
                                salary = rate_val * 12
                            elif period == "hourly":
                                salary = rate_val * 2080
                            else:
                                salary = rate_val

                    join_date = None
                    start_str = emp.get("start_date") or emp.get("startDate")
                    if start_str:
                        try:
                            join_date = datetime.strptime(start_str[:10], "%Y-%m-%d")
                        except (ValueError, TypeError):
                            pass

                    employees.append(
                        EmployeeRecord(
                            external_id=str(emp.get("id", "")),
                            name=f"{emp.get('first_name', emp.get('firstName', ''))} {emp.get('last_name', emp.get('lastName', ''))}".strip(),
                            email=emp.get("email") or emp.get("work_email"),
                            department=emp.get("department", {}).get("name") if isinstance(emp.get("department"), dict) else emp.get("department"),
                            designation=emp.get("title") or emp.get("job_title"),
                            salary=salary,
                            join_date=join_date,
                            status="active" if emp.get("status", "").lower() in ("active", "") and not emp.get("termination_date") else "terminated",
                            metadata={
                                "rippling_id": emp.get("id"),
                                "employment_type": emp.get("employment_type"),
                                "manager_id": emp.get("manager_id") or emp.get("manager"),
                            },
                        )
                    )

                next_url = data.get("next") if isinstance(data, dict) else None

        except Exception as e:
            logger.error(f"Error fetching Rippling employees: {e}")

        return employees

    async def fetch_payroll_runs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[PayrollRunRecord]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        payroll_runs = []
        try:
            client = await self._get_client()
            params: Dict[str, str] = {}
            if start_date:
                params["start_date"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                params["end_date"] = end_date.strftime("%Y-%m-%d")

            response = await client.get("/platform/api/payroll_runs", params=params)

            if response.status_code != 200:
                logger.error(f"Rippling payroll runs error: {response.status_code}")
                return []

            data = response.json()
            results = data.get("results", data if isinstance(data, list) else [])

            for run in results:
                totals = run.get("totals", run)
                gross = float(totals.get("gross_pay", totals.get("total_gross", 0)))
                deductions = float(totals.get("total_deductions", 0))
                net = float(totals.get("net_pay", totals.get("total_net", 0)))
                employer_taxes = float(totals.get("employer_taxes", 0))
                employee_count = int(run.get("employee_count", 0))

                period_start_str = run.get("pay_period_start") or run.get("period_start", "")
                period_end_str = run.get("pay_period_end") or run.get("period_end", "")

                try:
                    start_dt = datetime.strptime(period_start_str[:10], "%Y-%m-%d") if period_start_str else datetime.now()
                    end_dt = datetime.strptime(period_end_str[:10], "%Y-%m-%d") if period_end_str else datetime.now()
                except (ValueError, TypeError):
                    start_dt = datetime.now()
                    end_dt = datetime.now()

                payroll_runs.append(
                    PayrollRunRecord(
                        external_id=str(run.get("id", "")),
                        period_start=start_dt,
                        period_end=end_dt,
                        total_gross=gross,
                        total_deductions=deductions,
                        total_net=net,
                        employee_count=employee_count,
                        currency="USD",
                        status=run.get("status", "completed"),
                        breakdown={
                            "employer_taxes": employer_taxes,
                            "employee_taxes": float(totals.get("employee_taxes", 0)),
                            "benefits": float(totals.get("benefits", 0)),
                            "net_pay": net,
                        },
                        metadata={
                            "run_type": run.get("run_type"),
                            "check_date": run.get("check_date"),
                            "approval_status": run.get("approval_status"),
                        },
                    )
                )

        except Exception as e:
            logger.error(f"Error fetching Rippling payroll runs: {e}")

        return payroll_runs

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        result = {
            "source_type": "connector_rippling",
            "extraction_summary": "Synced from Rippling HR/Payroll",
        }

        if employees:
            active = [e for e in employees if e.status == "active"]
            result["headcount"] = len(active)
            total_salary = sum(e.salary or 0 for e in active)
            result["annual_payroll"] = total_salary
            result["monthly_payroll"] = total_salary / 12 if total_salary > 0 else 0

        if payroll_runs:
            total_payroll_cost = sum(run.total_gross for run in payroll_runs)
            avg_monthly = total_payroll_cost / max(len(payroll_runs), 1)
            result["payroll"] = avg_monthly
            result["total_payroll_cost"] = total_payroll_cost
            result["payroll_runs_count"] = len(payroll_runs)
            if payroll_runs:
                result["last_payroll_date"] = payroll_runs[-1].period_end.isoformat()

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

            employees = await self.fetch_employees()
            payroll_runs = await self.fetch_payroll_runs()
            departments = await self.get_departments()
            financials = self.map_to_financials(employees=employees, payroll_runs=payroll_runs)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(employees) + len(payroll_runs),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "employees_count": len(employees),
                    "payroll_runs_count": len(payroll_runs),
                    "departments_count": len(departments),
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
