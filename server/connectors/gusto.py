"""
Gusto Connector - Payroll and HR data integration.

Provides:
- Employee records and headcount
- Payroll run data (gross, deductions, net)
- Compensation details
- Pay period scheduling

API Documentation: https://docs.gusto.com/app-integrations/
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

GUSTO_ENVIRONMENTS = {
    "demo": "https://api.gusto-demo.com",
    "production": "https://api.gusto.com",
}


@ConnectorRegistry.register
class GustoConnector(BaseConnector):
    PROVIDER_ID = "gusto"
    PROVIDER_NAME = "Gusto"
    PROVIDER_DESCRIPTION = "Payroll, benefits, and HR platform. Import employee data, payroll costs, headcount, and compensation details."
    PROVIDER_CATEGORY = ProviderCategory.PAYROLL
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://docs.gusto.com/app-integrations/"

    SUPPORTS_EMPLOYEES = True
    SUPPORTS_PAYROLL = True
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._access_token = config.credentials.get("access_token", "")
        self._refresh_token = config.credentials.get("refresh_token", "")
        self._client_id = config.credentials.get("client_id", "")
        self._client_secret = config.credentials.get("client_secret", "")
        self._company_uuid = config.credentials.get("company_uuid", "")
        env = config.settings.get("environment", "production")
        self._base_url = GUSTO_ENVIRONMENTS.get(env, GUSTO_ENVIRONMENTS["production"])
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                },
            )
        return self._client

    async def _refresh_access_token(self) -> bool:
        if not all([self._client_id, self._client_secret, self._refresh_token]):
            return False

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/oauth/token",
                    json={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "grant_type": "refresh_token",
                        "refresh_token": self._refresh_token,
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    self._access_token = data.get("access_token", "")
                    self._refresh_token = data.get("refresh_token", self._refresh_token)
                    if self._client:
                        self._client.headers["Authorization"] = f"Bearer {self._access_token}"
                    logger.info("Gusto token refreshed successfully")
                    return True
                return False
        except Exception as e:
            logger.error(f"Gusto token refresh error: {e}")
            return False

    async def authenticate(self) -> bool:
        if not self._access_token:
            logger.warning("Gusto access token not provided")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/v1/me")

            if response.status_code == 200:
                self._authenticated = True
                data = response.json()
                roles = data.get("roles", {})
                payroll_admin = roles.get("payroll_admin", {})
                companies = payroll_admin.get("companies", [])
                if companies and not self._company_uuid:
                    self._company_uuid = companies[0].get("uuid", "")
                logger.info(f"Gusto authentication successful, company: {self._company_uuid}")
                return True
            elif response.status_code == 401:
                logger.info("Gusto token expired, attempting refresh")
                if await self._refresh_access_token():
                    return await self.authenticate()
                return False
            else:
                logger.warning(f"Gusto auth failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Gusto authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/v1/me")
            return response.status_code == 200
        except Exception:
            return False

    async def fetch_employees(self) -> List[EmployeeRecord]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        if not self._company_uuid:
            logger.warning("Gusto company UUID not set")
            return []

        employees = []
        try:
            client = await self._get_client()
            page = 1

            while True:
                response = await client.get(
                    f"/v1/companies/{self._company_uuid}/employees",
                    params={"page": page, "per": 100},
                )

                if response.status_code != 200:
                    logger.error(f"Gusto employees error: {response.status_code}")
                    break

                data = response.json()
                if not data:
                    break

                for emp in data:
                    jobs = emp.get("jobs", [])
                    current_job = jobs[0] if jobs else {}
                    compensations = current_job.get("compensations", [])
                    current_comp = compensations[0] if compensations else {}

                    salary = None
                    rate = current_comp.get("rate")
                    if rate:
                        payment_unit = current_comp.get("payment_unit", "")
                        rate_val = float(rate)
                        if payment_unit == "Year":
                            salary = rate_val
                        elif payment_unit == "Month":
                            salary = rate_val * 12
                        elif payment_unit == "Hour":
                            salary = rate_val * 2080

                    employees.append(
                        EmployeeRecord(
                            external_id=str(emp.get("uuid", emp.get("id", ""))),
                            name=f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
                            email=emp.get("email"),
                            department=current_job.get("title", ""),
                            designation=current_job.get("title", ""),
                            salary=salary,
                            join_date=(
                                datetime.strptime(emp.get("date_of_birth", ""), "%Y-%m-%d")
                                if emp.get("date_of_birth")
                                else None
                            ),
                            status="active" if not emp.get("terminated", False) else "terminated",
                            metadata={
                                "gusto_uuid": emp.get("uuid"),
                                "payment_method": current_comp.get("payment_unit", ""),
                                "flsa_status": current_comp.get("flsa_status", ""),
                            },
                        )
                    )

                if len(data) < 100:
                    break
                page += 1

        except Exception as e:
            logger.error(f"Error fetching Gusto employees: {e}")

        return employees

    async def fetch_payroll_runs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[PayrollRunRecord]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        if not self._company_uuid:
            logger.warning("Gusto company UUID not set")
            return []

        payroll_runs = []
        try:
            client = await self._get_client()
            params: Dict[str, str] = {}
            if start_date:
                params["start_date"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                params["end_date"] = end_date.strftime("%Y-%m-%d")

            response = await client.get(
                f"/v1/companies/{self._company_uuid}/payrolls",
                params=params,
            )

            if response.status_code != 200:
                logger.error(f"Gusto payrolls error: {response.status_code}")
                return []

            data = response.json()

            for payroll in data:
                if not payroll.get("processed", False):
                    continue

                totals = payroll.get("totals", {})
                employee_compensations = payroll.get("employee_compensations", [])

                gross = float(totals.get("company_debit", 0))
                deductions = float(totals.get("employee_taxes", 0)) + float(totals.get("employee_benefits_deductions", 0))
                net = float(totals.get("net_pay", 0))
                employer_taxes = float(totals.get("employer_taxes", 0))

                period_start = payroll.get("pay_period", {}).get("start_date", "")
                period_end = payroll.get("pay_period", {}).get("end_date", "")

                try:
                    start_dt = datetime.strptime(period_start, "%Y-%m-%d") if period_start else datetime.now()
                    end_dt = datetime.strptime(period_end, "%Y-%m-%d") if period_end else datetime.now()
                except ValueError:
                    start_dt = datetime.now()
                    end_dt = datetime.now()

                payroll_runs.append(
                    PayrollRunRecord(
                        external_id=str(payroll.get("payroll_uuid", payroll.get("id", ""))),
                        period_start=start_dt,
                        period_end=end_dt,
                        total_gross=gross,
                        total_deductions=deductions,
                        total_net=net,
                        employee_count=len(employee_compensations),
                        currency="USD",
                        status="completed" if payroll.get("processed") else "pending",
                        breakdown={
                            "employer_taxes": employer_taxes,
                            "employee_taxes": float(totals.get("employee_taxes", 0)),
                            "benefits": float(totals.get("benefits", 0)),
                            "employee_benefits_deductions": float(totals.get("employee_benefits_deductions", 0)),
                            "net_pay": net,
                            "check_amount": float(totals.get("check_amount", 0)),
                        },
                        metadata={
                            "payroll_deadline": payroll.get("payroll_deadline"),
                            "check_date": payroll.get("check_date"),
                            "processed_date": payroll.get("processed_date"),
                        },
                    )
                )

        except Exception as e:
            logger.error(f"Error fetching Gusto payrolls: {e}")

        return payroll_runs

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        result = {
            "source_type": "connector_gusto",
            "extraction_summary": "Synced from Gusto Payroll",
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
                    errors=["Authentication failed - check access_token or OAuth credentials"],
                    sync_started=sync_started,
                )

            employees = await self.fetch_employees()
            payroll_runs = await self.fetch_payroll_runs()
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
                },
            )

        except Exception as e:
            logger.error(f"Gusto sync failed: {e}")
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
