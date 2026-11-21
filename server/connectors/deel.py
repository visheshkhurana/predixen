"""
Deel Connector - International payroll and contractor management.

Provides:
- People / team member records
- Contracts (with compensation from the per-contract endpoint)
- Paid invoices (what the company paid for its Deel workers), rolled up into
  monthly payroll runs

API reference (https://developer.deel.com/):
- Host:      https://api.letsdeel.com/rest   (Bearer API token)
- People:    GET /people?limit=&offset=          page: {offset, total_rows, items_per_page}
             https://developer.deel.com/api/reference/endpoints/people/get-people
- Contracts: GET /contracts?limit=&after_cursor= page: {cursor, total_rows}; no compensation here
             https://developer.deel.com/api/reference/endpoints/contracts/get-contracts
             GET /contracts/{id} -> data.compensation_details {amount, currency_code, scale, frequency, gross_annual_salary}
             https://developer.deel.com/api/reference/endpoints/contracts/get-contract
- Invoices:  GET /invoices?issued_from_date=&issued_to_date=&limit=&offset= (paid only by default)
             https://developer.deel.com/api/reference/endpoints/accounting/retrieve-invoices-v-2026-01-01
"""

import httpx
from .http import http_client
import logging
from collections import defaultdict
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from .base import (
    BaseConnector,
    ConnectorConfig,
    AuthType,
    ProviderCategory,
    InvoiceRecord,
    EmployeeRecord,
    PayrollRunRecord,
    SyncResult,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.letsdeel.com/rest"
PAGE_SIZE = 100
MAX_PAGES = 100
MAX_CONTRACT_DETAILS = 200
DEFAULT_INVOICE_DAYS = 365
ACTIVE_CONTRACT_STATUSES = {"in_progress", "active", "onboarding", "onboarded"}

_ANNUALIZE = {
    "annual": 1, "annually": 1, "yearly": 1, "year": 1,
    "monthly": 12, "month": 12,
    "semimonthly": 24, "semi_monthly": 24,
    "biweekly": 26, "bi_weekly": 26,
    "weekly": 52, "week": 52,
    "daily": 260, "day": 260,
    "hourly": 2080, "hour": 2080,
}


def _parse_date(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def annual_compensation(details: Optional[Dict[str, Any]]) -> Optional[Tuple[float, str]]:
    """(annual amount, currency) from a contract's compensation_details, or None."""
    if not isinstance(details, dict):
        return None
    currency = details.get("currency_code") or details.get("currency") or "USD"
    if details.get("gross_annual_salary"):
        return _num(details["gross_annual_salary"]), currency
    amount = _num(details.get("amount"))
    if not amount:
        return None
    # `scale` is the unit of the rate (hourly, weekly, monthly...); `frequency`
    # is the invoice cycle. A $50/hour contract invoiced monthly was being
    # annualised as 50 x 12.
    scale = str(details.get("scale") or details.get("frequency") or "monthly").lower()
    return amount * _ANNUALIZE.get(scale, 12), currency


def _primary_email(person: Dict[str, Any]) -> Optional[str]:
    emails = person.get("emails") or []
    values = [e for e in emails if isinstance(e, dict) and e.get("value")]
    work = next((e["value"] for e in values if (e.get("type") or "").lower() == "work"), None)
    return work or (values[0]["value"] if values else None) or person.get("email")


@ConnectorRegistry.register
class DeelConnector(BaseConnector):
    PROVIDER_ID = "deel"
    PROVIDER_NAME = "Deel"
    PROVIDER_DESCRIPTION = "Global payroll and contractor management platform. Import team members, contracts, and what you pay Deel workers each month."
    PROVIDER_CATEGORY = ProviderCategory.PAYROLL
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developer.deel.com/"

    SUPPORTS_EMPLOYEES = True
    SUPPORTS_PAYROLL = True
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_key = (config.credentials.get("api_key") or "").strip()
        self._client: Optional[httpx.AsyncClient] = None
        self._contract_details: Optional[Dict[str, Dict[str, Any]]] = None
        self._invoice_cache: Optional[List[InvoiceRecord]] = None
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
            self.auth_error = "Enter a Deel API token (Deel > More > Developer > Access tokens)."
            return False

        try:
            client = await self._get_client()
            response = await client.get("/people", params={"limit": 1})

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Deel authentication successful")
                return True
            logger.warning(f"Deel auth failed: {response.status_code}")
            if response.status_code in (401, 403):
                self.auth_error = (
                    "Deel rejected the API token. Create an organization token with people:read, "
                    "contracts:read and accounting:read scopes."
                )
            else:
                self.auth_error = f"Deel returned {response.status_code}."
            return False
        except Exception as e:
            logger.error(f"Deel authentication error: {e}")
            self.auth_error = "Could not reach Deel. Try again."
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/people", params={"limit": 1})
            return response.status_code == 200
        except Exception:
            return False

    async def _ensure_auth(self) -> bool:
        return self._authenticated or await self.authenticate()

    async def _get_offset_paged(self, path: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Offset paging: page = {offset, total_rows, items_per_page}."""
        client = await self._get_client()
        items: List[Dict[str, Any]] = []
        offset = 0
        for _ in range(MAX_PAGES):
            response = await client.get(path, params={**(params or {}), "limit": PAGE_SIZE, "offset": offset})
            if response.status_code != 200:
                raise RuntimeError(f"Deel {path} returned {response.status_code}")
            body = response.json() or {}
            batch = body.get("data") or []
            items.extend(b for b in batch if isinstance(b, dict))
            total = int(_num((body.get("page") or {}).get("total_rows")))
            offset += len(batch)
            if not batch or offset >= total:
                return items
        logger.warning(f"Deel {path}: stopped after {MAX_PAGES} pages; results truncated")
        return items

    async def get_contracts(self) -> List[Dict[str, Any]]:
        """Cursor paging: after_cursor -> page.cursor."""
        if not await self._ensure_auth():
            return []
        client = await self._get_client()
        contracts: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        for _ in range(MAX_PAGES):
            params: Dict[str, Any] = {"limit": PAGE_SIZE}
            if cursor:
                params["after_cursor"] = cursor
            response = await client.get("/contracts", params=params)
            if response.status_code != 200:
                logger.error(f"Deel contracts error: {response.status_code}")
                break
            body = response.json() or {}
            batch = body.get("data") or []
            contracts.extend(b for b in batch if isinstance(b, dict))
            page = body.get("page") or {}
            next_cursor = page.get("cursor")
            total = int(_num(page.get("total_rows")))
            if not batch or not next_cursor or next_cursor == cursor or (total and len(contracts) >= total):
                break
            cursor = next_cursor
        return contracts

    async def get_contract_details(self) -> Dict[str, Dict[str, Any]]:
        """GET /contracts/{id} for active contracts (the list endpoint has no compensation)."""
        if self._contract_details is not None:
            return self._contract_details
        details: Dict[str, Dict[str, Any]] = {}
        contracts = [c for c in await self.get_contracts()
                     if str(c.get("status") or "").lower() in ACTIVE_CONTRACT_STATUSES and c.get("id")]
        if len(contracts) > MAX_CONTRACT_DETAILS:
            logger.warning(f"Deel: {len(contracts)} active contracts, reading compensation for the first {MAX_CONTRACT_DETAILS}")
        client = await self._get_client()
        for contract in contracts[:MAX_CONTRACT_DETAILS]:
            try:
                response = await client.get(f"/contracts/{contract['id']}")
            except httpx.HTTPError as e:
                logger.warning(f"Deel contract detail failed: {e}")
                continue
            if response.status_code != 200:
                continue
            body = response.json() or {}
            data = body.get("data") if isinstance(body.get("data"), dict) else body
            details[str(contract["id"])] = {**contract, **data}
        self._contract_details = details
        return details

    async def get_people(self) -> List[Dict[str, Any]]:
        if not await self._ensure_auth():
            return []
        try:
            return await self._get_offset_paged("/people")
        except Exception as e:
            logger.error(f"Deel people fetch error: {e}")
            return []

    async def fetch_employees(self) -> List[EmployeeRecord]:
        people = await self.get_people()
        if not people:
            return []

        # Salary from contract compensation, matched by contract id (people.employments[].id)
        # or by worker email.
        by_contract: Dict[str, Tuple[float, str]] = {}
        by_email: Dict[str, Tuple[float, str]] = {}
        try:
            for cid, detail in (await self.get_contract_details()).items():
                comp = annual_compensation(detail.get("compensation_details"))
                if not comp:
                    continue
                by_contract[cid] = comp
                worker = detail.get("worker") or {}
                email = (worker.get("email") or worker.get("expected_email") or "").lower()
                if email:
                    by_email[email] = comp
        except Exception as e:
            logger.info(f"Deel contract compensation unavailable: {e}")

        employees = []
        for person in people:
            email = _primary_email(person)
            comp = None
            for employment in person.get("employments") or []:
                if isinstance(employment, dict) and str(employment.get("id")) in by_contract:
                    comp = by_contract[str(employment.get("id"))]
                    break
            if comp is None and email:
                comp = by_email.get(email.lower())

            department = person.get("department")
            hiring_status = str(person.get("hiring_status") or "").lower()
            name = person.get("full_name") or " ".join(
                p for p in (person.get("first_name"), person.get("last_name")) if p
            )
            employees.append(
                EmployeeRecord(
                    external_id=str(person.get("id", "")),
                    name=name or "",
                    email=email,
                    department=department.get("name") if isinstance(department, dict) else department,
                    designation=person.get("job_title"),
                    salary=comp[0] if comp else None,
                    join_date=_parse_date(person.get("start_date")),
                    status="active" if hiring_status in ("active", "onboarded", "") else hiring_status,
                    metadata={
                        "deel_id": person.get("id"),
                        "hiring_type": person.get("hiring_type"),
                        "country": person.get("country"),
                        "salary_currency": comp[1] if comp else None,
                    },
                )
            )
        return employees

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        """Paid invoices for Deel workers. These are costs to the company, not revenue."""
        if start_date is None and end_date is None and self._invoice_cache is not None:
            return self._invoice_cache
        if not await self._ensure_auth():
            return []

        start = start_date or (datetime.utcnow() - timedelta(days=DEFAULT_INVOICE_DAYS))
        params: Dict[str, Any] = {"issued_from_date": start.strftime("%Y-%m-%d")}
        if end_date:
            params["issued_to_date"] = end_date.strftime("%Y-%m-%d")

        invoices: List[InvoiceRecord] = []
        try:
            for inv in await self._get_offset_paged("/invoices", params):
                issued = _parse_date(inv.get("issued_at") or inv.get("created_at")) or datetime.utcnow()
                invoices.append(
                    InvoiceRecord(
                        external_id=str(inv.get("id", "")),
                        date=issued,
                        due_date=_parse_date(inv.get("due_date")),
                        customer_name=None,
                        amount=_num(inv.get("amount") if inv.get("amount") is not None else inv.get("total")),
                        tax=_num(inv.get("vat_total")),
                        total=_num(inv.get("total")),
                        currency=inv.get("currency") or "USD",
                        status=inv.get("status") or "paid",
                        metadata={
                            "label": inv.get("label"),
                            "contract_id": inv.get("contract_id"),
                            "deel_fee": _num(inv.get("deel_fee")),
                            "paid_at": inv.get("paid_at"),
                            "source": "deel_invoice",
                        },
                    )
                )
        except Exception as e:
            logger.error(f"Error fetching Deel invoices: {e}")

        if start_date is None and end_date is None:
            self._invoice_cache = invoices
        return invoices

    async def fetch_payroll_runs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[PayrollRunRecord]:
        """Monthly runs from paid worker invoices; falls back to contract compensation."""
        invoices = await self.fetch_invoices(start_date, end_date)
        buckets: Dict[Tuple[str, str], List[InvoiceRecord]] = defaultdict(list)
        for inv in invoices:
            if inv.status not in ("paid", "processing"):
                continue
            paid = _parse_date(inv.metadata.get("paid_at")) or inv.date
            buckets[(paid.strftime("%Y-%m"), inv.currency)].append(inv)

        runs: List[PayrollRunRecord] = []
        for (month, currency), items in sorted(buckets.items()):
            first = datetime.strptime(month + "-01", "%Y-%m-%d")
            last = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            # Invoice `total` includes Deel's fee and VAT, so it isn't worker
            # pay. Gross is the worker amount; the fee is added back as an
            # employment cost in map_to_financials; VAT is kept apart.
            worker_pay = sum(i.amount for i in items)
            runs.append(PayrollRunRecord(
                external_id=f"deel-{month}-{currency}",
                period_start=first,
                period_end=last,
                total_gross=worker_pay,
                total_deductions=0.0,
                total_net=worker_pay,
                employee_count=len({i.metadata.get("contract_id") for i in items if i.metadata.get("contract_id")}),
                currency=currency,
                status="completed",
                breakdown={
                    "worker_pay": worker_pay,
                    "deel_fees": sum(i.metadata.get("deel_fee") or 0 for i in items),
                    "vat": sum(i.tax for i in items),
                },
                metadata={"source": "deel_invoices", "invoice_count": len(items)},
            ))
        if runs:
            return runs

        # No paid invoices visible (new account or token without accounting:read):
        # estimate this month's cost from active contract compensation.
        monthly: Dict[str, float] = defaultdict(float)
        heads: Dict[str, int] = defaultdict(int)
        for detail in (await self.get_contract_details()).values():
            comp = annual_compensation(detail.get("compensation_details"))
            if comp:
                monthly[comp[1]] += comp[0] / 12
                heads[comp[1]] += 1
        now = datetime.utcnow()
        first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for currency, amount in monthly.items():
            runs.append(PayrollRunRecord(
                external_id=f"deel-estimate-{first.strftime('%Y-%m')}-{currency}",
                period_start=first,
                period_end=now,
                total_gross=amount,
                total_deductions=0.0,
                total_net=amount,
                employee_count=heads[currency],
                currency=currency,
                status="estimated",
                breakdown={"base_pay": amount},
                metadata={"source": "deel_contract_compensation"},
            ))
        return runs

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        result = {
            "source_type": "connector_deel",
            "extraction_summary": "Synced from Deel",
        }

        if employees:
            active = [e for e in employees if e.status == "active"]
            result["headcount"] = len(active)
            total_salary = sum(e.salary or 0 for e in active)
            result["annual_payroll"] = total_salary
            result["monthly_payroll"] = total_salary / 12 if total_salary > 0 else 0

        if payroll_runs:
            months = {r.period_start.strftime("%Y-%m") for r in payroll_runs}
            # Worker pay plus Deel's fee (a cost of employing them); VAT excluded.
            total_payroll_cost = sum(run.total_gross + float((run.breakdown or {}).get("deel_fees") or 0) for run in payroll_runs)
            result["payroll"] = total_payroll_cost / max(len(months), 1)
            result["total_payroll_cost"] = total_payroll_cost
            result["payroll_runs_count"] = len(payroll_runs)

        if invoices:
            # Deel invoices are what the company pays for its workers: a cost, never revenue.
            result["contractor_invoices_total"] = sum(inv.total for inv in invoices)
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
                    errors=[self.auth_error or "Authentication failed - check api_key"],
                    sync_started=sync_started,
                )

            employees = await self.fetch_employees()
            invoices = await self.fetch_invoices()
            payroll_runs = await self.fetch_payroll_runs()
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
