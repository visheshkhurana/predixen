"""
Deel Global Payroll Connector - International payroll and contractor management.

Provides:
- Contract records (employees and contractors)
- Invoice data for contractor payments
- People/team member records
- Global payroll run data

API Documentation: https://developer.deel.com/docs/
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

BASE_URL = "https://api.deel.com/rest/v2"


@ConnectorRegistry.register
class DeelConnector(BaseConnector):
    PROVIDER_ID = "deel"
    PROVIDER_NAME = "Deel"
    PROVIDER_DESCRIPTION = "Global payroll and contractor management platform. Import contracts, invoices, team members, and international payroll data."
    PROVIDER_CATEGORY = ProviderCategory.PAYROLL
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developer.deel.com/docs/"

    SUPPORTS_EMPLOYEES = True
    SUPPORTS_PAYROLL = True
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = True

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
            logger.warning("Deel API key not provided")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/people?limit=1")

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Deel authentication successful")
                return True
            else:
                logger.warning(f"Deel auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Deel authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/people?limit=1")
            return response.status_code == 200
        except Exception:
            return False

    async def get_contracts(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_contracts = []
            page = 1

            while True:
                params = {"limit": min(limit, 100), "page": page}
                response = await client.get("/contracts", params=params)

                if response.status_code != 200:
                    logger.error(f"Deel contracts error: {response.status_code}")
                    break

                data = response.json()
                results = data.get("data", data if isinstance(data, list) else [])
                all_contracts.extend(results)

                total_pages = data.get("page", {}).get("total_pages", 1) if isinstance(data, dict) else 1
                if page >= total_pages or len(all_contracts) >= limit:
                    break
                page += 1

            return all_contracts

        except Exception as e:
            logger.error(f"Deel contracts fetch error: {e}")
            return []

    async def get_people(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            client = await self._get_client()
            all_people = []
            page = 1

            while True:
                params = {"limit": min(limit, 100), "page": page}
                response = await client.get("/people", params=params)

                if response.status_code != 200:
                    logger.error(f"Deel people error: {response.status_code}")
                    break

                data = response.json()
                results = data.get("data", data if isinstance(data, list) else [])
                all_people.extend(results)

                total_pages = data.get("page", {}).get("total_pages", 1) if isinstance(data, dict) else 1
                if page >= total_pages or len(all_people) >= limit:
                    break
                page += 1

            return all_people

        except Exception as e:
            logger.error(f"Deel people fetch error: {e}")
            return []

    async def fetch_employees(self) -> List[EmployeeRecord]:
        people = await self.get_people(limit=500)
        employees = []

        for person in people:
            salary = None
            compensation = person.get("compensation", {})
            if compensation:
                amount = compensation.get("amount") or compensation.get("rate")
                if amount:
                    salary = float(amount)
                    scale = compensation.get("scale", "").lower()
                    if scale == "monthly":
                        salary = salary * 12
                    elif scale == "hourly":
                        salary = salary * 2080

            join_date = None
            start_str = person.get("start_date") or person.get("hiring_date")
            if start_str:
                try:
                    join_date = datetime.strptime(start_str[:10], "%Y-%m-%d")
                except (ValueError, TypeError):
                    pass

            employees.append(
                EmployeeRecord(
                    external_id=str(person.get("id", "")),
                    name=f"{person.get('first_name', '')} {person.get('last_name', '')}".strip() or person.get("full_name", ""),
                    email=person.get("email"),
                    department=person.get("department", {}).get("name") if isinstance(person.get("department"), dict) else person.get("department"),
                    designation=person.get("job_title") or person.get("title"),
                    salary=salary,
                    join_date=join_date,
                    status="active" if person.get("status", "").lower() in ("active", "") else person.get("status", "inactive"),
                    metadata={
                        "deel_id": person.get("id"),
                        "contract_type": person.get("contract_type"),
                        "country": person.get("country"),
                        "worker_type": person.get("worker_type"),
                    },
                )
            )

        return employees

    async def fetch_payroll_runs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[PayrollRunRecord]:
        contracts = await self.get_contracts(limit=500)
        payroll_runs = []

        for contract in contracts:
            compensation = contract.get("compensation", {})
            if not compensation:
                continue

            amount = float(compensation.get("amount", 0))
            currency = compensation.get("currency", "USD")
            scale = compensation.get("scale", "monthly").lower()

            period_start_str = contract.get("start_date", "")
            period_end_str = contract.get("end_date", "")

            try:
                start_dt = datetime.strptime(period_start_str[:10], "%Y-%m-%d") if period_start_str else datetime.now()
            except (ValueError, TypeError):
                start_dt = datetime.now()

            try:
                end_dt = datetime.strptime(period_end_str[:10], "%Y-%m-%d") if period_end_str else datetime.now()
            except (ValueError, TypeError):
                end_dt = datetime.now()

            if start_date and end_dt < start_date:
                continue
            if end_date and start_dt > end_date:
                continue

            payroll_runs.append(
                PayrollRunRecord(
                    external_id=str(contract.get("id", "")),
                    period_start=start_dt,
                    period_end=end_dt,
                    total_gross=amount,
                    total_deductions=0.0,
                    total_net=amount,
                    employee_count=1,
                    currency=currency,
                    status=contract.get("status", "active"),
                    breakdown={
                        "base_pay": amount,
                        "scale": scale,
                    },
                    metadata={
                        "contract_type": contract.get("type"),
                        "contract_status": contract.get("status"),
                        "country": contract.get("country"),
                    },
                )
            )

        return payroll_runs

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        invoices = []
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"limit": 100}
            if start_date:
                params["from_date"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                params["to_date"] = end_date.strftime("%Y-%m-%d")

            response = await client.get("/invoices", params=params)

            if response.status_code != 200:
                logger.error(f"Deel invoices error: {response.status_code}")
                return []

            data = response.json()
            results = data.get("data", data if isinstance(data, list) else [])

            for inv in results:
                inv_date_str = inv.get("date") or inv.get("created_at", "")
                due_date_str = inv.get("due_date", "")

                try:
                    inv_date = datetime.strptime(inv_date_str[:10], "%Y-%m-%d") if inv_date_str else datetime.now()
                except (ValueError, TypeError):
                    inv_date = datetime.now()

                try:
                    due_date = datetime.strptime(due_date_str[:10], "%Y-%m-%d") if due_date_str else None
                except (ValueError, TypeError):
                    due_date = None

                amount = float(inv.get("amount", inv.get("total", 0)))

                invoices.append(
                    InvoiceRecord(
                        external_id=str(inv.get("id", "")),
                        date=inv_date,
                        due_date=due_date,
                        customer_name=inv.get("contractor_name") or inv.get("worker_name", ""),
                        amount=amount,
                        total=amount,
                        currency=inv.get("currency", "USD"),
                        status=inv.get("status", "pending"),
                        metadata={
                            "invoice_number": inv.get("invoice_number"),
                            "contract_id": inv.get("contract_id"),
                            "source": "deel_invoice",
                        },
                    )
                )

        except Exception as e:
            logger.error(f"Error fetching Deel invoices: {e}")

        return invoices

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        result = {
            "source_type": "connector_deel",
            "extraction_summary": "Synced from Deel Global Payroll",
        }

        if employees:
            active = [e for e in employees if e.status == "active"]
            result["headcount"] = len(active)
            total_salary = sum(e.salary or 0 for e in active)
            result["annual_payroll"] = total_salary
            result["monthly_payroll"] = total_salary / 12 if total_salary > 0 else 0

        if payroll_runs:
            total_payroll_cost = sum(run.total_gross for run in payroll_runs)
            result["payroll"] = total_payroll_cost / max(len(payroll_runs), 1)
            result["total_payroll_cost"] = total_payroll_cost
            result["payroll_runs_count"] = len(payroll_runs)

        if invoices:
            result["revenue"] = sum(inv.total for inv in invoices)
            result["invoices_count"] = len(invoices)

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
            invoices = await self.fetch_invoices()
            financials = self.map_to_financials(employees=employees, payroll_runs=payroll_runs, invoices=invoices)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(employees) + len(payroll_runs) + len(invoices),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "employees_count": len(employees),
                    "payroll_runs_count": len(payroll_runs),
                    "invoices_count": len(invoices),
                },
            )

        except Exception as e:
            logger.error(f"Deel sync failed: {e}")
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
