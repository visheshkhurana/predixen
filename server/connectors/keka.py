"""
Keka Connector

Integrates with the Keka HR public API to fetch:
- Employee data (HRIS)
- Payroll registers (per finalized pay cycle) and current salary structures

API documentation:
- Token:     https://developers.keka.com/reference/token-1
- Employees: https://developers.keka.com/reference/get_hris-employees
- Payroll:   https://developers.keka.com/reference/get_payroll-paygroups-1 ,
             .../get_payroll-paygroups-routepaygroupid-paycycles ,
             .../get_payroll-paygroups-routepaygroupid-paycycles-routepaycycleid-payregister ,
             .../get_payroll-salaries
- Index:     https://developers.keka.com/llms.txt

Base URL is per tenant: https://{company}.keka.com/api/v1
Auth is a token exchange: POST https://login.keka.com/connect/token with
grant_type=kekaapi, scope=kekaapi, client_id, client_secret, api_key, which
returns a Bearer access_token (expires_in ~86400s).
"""

import httpx
import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import (
    BaseConnector,
    ConnectorConfig,
    AuthType,
    ProviderCategory,
    EmployeeRecord,
    PayrollRunRecord,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

TOKEN_URL = "https://login.keka.com/connect/token"
API_HOST_TEMPLATE = "https://{company}.keka.com/api/v1"
# Keka's docs: "if you hit an error calling Keka APIs, add a user-agent header".
USER_AGENT = "Mozilla/5.0 (compatible; FounderConsole/1.0)"
PAGE_SIZE = 200  # documented maximum
MAX_PAGES = 100
MAX_PAY_CYCLES = 24  # last two years of monthly cycles per pay group

# A Keka tenant subdomain: "acme" for acme.keka.com.
_COMPANY_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

RECONNECT_MESSAGE = (
    "Keka needs to be reconnected: enter your Keka company (the 'acme' in acme.keka.com), "
    "Client ID, Client Secret and API Key from Keka > Settings > Integrations > API access."
)

# PayrollRunStatus enum order per the paycycles runStatus filter: Pending, Finalized, Partial.
_RUN_STATUS = {0: "pending", 1: "completed", 2: "partial"}


def normalize_keka_company(value: Optional[str]) -> str:
    """Accept 'acme', 'acme.keka.com' or 'https://acme.keka.com/...' and return 'acme' ('' if unusable)."""
    text = (value or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"^https?://", "", text).split("/", 1)[0]
    if text.endswith(".keka.com"):
        text = text[: -len(".keka.com")]
    return text if _COMPANY_RE.match(text) else ""


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


@ConnectorRegistry.register
class KekaConnector(BaseConnector):
    """
    Keka HR connector for syncing employee and payroll data.

    Credentials: company (tenant subdomain), client_id, client_secret, api_key.
    Requires the API add-on in Keka (Settings > Integrations > API access).
    """

    PROVIDER_ID = "keka"
    PROVIDER_NAME = "Keka HR"
    PROVIDER_DESCRIPTION = "Sync employee data and payroll from Keka"
    PROVIDER_CATEGORY = ProviderCategory.HRIS
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developers.keka.com/"

    SUPPORTS_EMPLOYEES = True
    SUPPORTS_PAYROLL = True
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        creds = config.credentials or {}
        raw_company = str(creds.get("company") or "")
        self._company = normalize_keka_company(raw_company)
        self._company_invalid = bool(raw_company.strip()) and not self._company
        self._client_id = (creds.get("client_id") or "").strip()
        self._client_secret = (creds.get("client_secret") or "").strip()
        self._api_key = (creds.get("api_key") or "").strip()
        self._base_url = API_HOST_TEMPLATE.format(company=self._company) if self._company else ""
        self._token = ""
        self._client: Optional[httpx.AsyncClient] = None
        self.auth_error: Optional[str] = None

    def rotated_credentials(self) -> Optional[Dict[str, Any]]:
        # The Keka access token is minted per run from the api_key; nothing to persist.
        return None

    def _credential_problem(self) -> Optional[str]:
        if self._company_invalid:
            return "Keka company should look like 'acme' (from acme.keka.com)."
        if not all((self._company, self._client_id, self._client_secret, self._api_key)):
            # Also covers connections saved with the old api_key + tenant_id fields.
            return RECONNECT_MESSAGE
        return None

    async def _fetch_token(self) -> bool:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "kekaapi",
                    "scope": "kekaapi",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "api_key": self._api_key,
                },
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
        if response.status_code != 200:
            detail = ""
            try:
                detail = (response.json() or {}).get("error", "")
            except Exception:
                pass
            self.auth_error = (
                f"Keka rejected the Client ID / Client Secret / API Key ({detail or response.status_code}). "
                "Check them in Keka > Settings > Integrations > API access."
            )
            return False
        token = (response.json() or {}).get("access_token") or ""
        if not token:
            self.auth_error = "Keka did not return an access token."
            return False
        self._token = token
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._token}",
                    "User-Agent": USER_AGENT,
                },
                timeout=30.0,
                follow_redirects=False,
            )
        return self._client

    async def authenticate(self) -> bool:
        """Exchange the API key for a token, then probe a real endpoint."""
        self.auth_error = None
        problem = self._credential_problem()
        if problem:
            self.auth_error = problem
            return False
        try:
            if not await self._fetch_token():
                return False
            client = await self._get_client()
            response = await client.get("/hris/employees", params={"pageNumber": 1, "pageSize": 1})
            if response.status_code == 200:
                self._authenticated = True
                logger.info("Keka authentication successful")
                return True
            if response.status_code in (401, 403):
                self.auth_error = (
                    "Keka accepted the API key but refused employee access. Make sure the API key "
                    "has HRIS (and Payroll) read permissions."
                )
            elif response.status_code == 404:
                self.auth_error = f"No Keka account found at {self._company}.keka.com. Check the company name."
            else:
                self.auth_error = f"Keka returned {response.status_code} for the employee list."
            return False
        except httpx.HTTPError as e:
            logger.error(f"Keka authentication error: {e}")
            self.auth_error = "Could not reach Keka. Check the company name and try again."
            return False

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def _get_paged(self, path: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """GET a Keka paged list (pageNumber/pageSize, totalPages) and return every item."""
        client = await self._get_client()
        items: List[Dict[str, Any]] = []
        page = 1
        while page <= MAX_PAGES:
            response = await client.get(path, params={**(params or {}), "pageNumber": page, "pageSize": PAGE_SIZE})
            if response.status_code != 200:
                raise RuntimeError(f"Keka {path} returned {response.status_code}")
            body = response.json() or {}
            batch = body.get("data") or []
            items.extend(b for b in batch if isinstance(b, dict))
            total_pages = int(body.get("totalPages") or 1)
            if page >= total_pages or not batch:
                return items
            page += 1
        logger.warning(f"Keka {path}: stopped after {MAX_PAGES} pages; results truncated")
        return items

    async def fetch_employees(self) -> List[EmployeeRecord]:
        """GET /hris/employees (working and relieved), paged by totalPages; CTC from /payroll/salaries."""
        if not self._authenticated:
            if not await self.authenticate():
                return []

        salaries: Dict[str, float] = {}
        try:
            for row in await self._get_paged("/payroll/salaries"):
                emp_id = (row.get("employee") or {}).get("id")
                if emp_id and row.get("ctc") is not None:
                    salaries[str(emp_id)] = _num(row.get("ctc"))
        except Exception as e:
            # Payroll scope is optional; employees still sync without salaries.
            logger.info(f"Keka salaries unavailable: {e}")

        rows = await self._get_paged("/hris/employees", {"employmentStatus": "Working,Relieved"})
        employees: List[EmployeeRecord] = []
        now = datetime.utcnow()
        for emp in rows:
            emp_id = str(emp.get("id") or "")
            exit_date = _parse_dt(emp.get("exitDate"))
            job_title = emp.get("jobTitle") if isinstance(emp.get("jobTitle"), dict) else {}
            reports_to = emp.get("reportsTo") if isinstance(emp.get("reportsTo"), dict) else {}
            name = emp.get("displayName") or " ".join(p for p in (emp.get("firstName"), emp.get("lastName")) if p)
            manager = " ".join(p for p in (reports_to.get("firstName"), reports_to.get("lastName")) if p)
            employees.append(EmployeeRecord(
                external_id=emp_id,
                name=name or "",
                email=emp.get("email"),
                department=None,  # not part of the Keka employee schema
                designation=job_title.get("title"),
                salary=salaries.get(emp_id),
                join_date=_parse_dt(emp.get("joiningDate")),
                status="inactive" if exit_date is not None and exit_date <= now else "active",
                metadata={
                    "employee_number": emp.get("employeeNumber"),
                    "manager": manager or None,
                    "city": emp.get("city"),
                    "exit_date": exit_date.isoformat() if exit_date else None,
                },
            ))
        logger.info(f"Fetched {len(employees)} employees from Keka")
        return employees

    async def fetch_payroll_runs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PayrollRunRecord]:
        """Pay groups -> finalized pay cycles -> pay register; one run per pay group per cycle."""
        if not self._authenticated:
            if not await self.authenticate():
                return []

        runs: List[PayrollRunRecord] = []
        for group in await self._get_paged("/payroll/paygroups"):
            group_id = group.get("identifier")
            if not group_id:
                continue
            cycles = await self._get_paged(
                f"/payroll/paygroups/{group_id}/paycycles", {"runStatus": "Finalized"}
            )
            cycles.sort(key=lambda c: c.get("startDate") or "", reverse=True)
            for cycle in cycles[:MAX_PAY_CYCLES]:
                cycle_id = cycle.get("identifier")
                cycle_start = _parse_dt(cycle.get("startDate"))
                cycle_end = _parse_dt(cycle.get("endDate"))
                if not cycle_id or not cycle_start or not cycle_end:
                    continue
                if start_date and cycle_end < start_date:
                    continue
                if end_date and cycle_start > end_date:
                    continue
                register = await self._get_paged(
                    f"/payroll/paygroups/{group_id}/paycycles/{cycle_id}/payregister"
                )
                if register:
                    runs.append(self._register_to_run(group, cycle, cycle_start, cycle_end, register))
        runs.sort(key=lambda r: r.period_start)
        logger.info(f"Fetched {len(runs)} payroll runs from Keka")
        return runs

    @staticmethod
    def _register_to_run(group, cycle, cycle_start, cycle_end, register) -> PayrollRunRecord:
        breakdown: Dict[str, float] = {
            "employer_contributions": sum(_num(r.get("totalContributions")) for r in register),
        }
        for r in register:
            for item in (r.get("deductions") or []) + (r.get("contributions") or []):
                title = (item.get("componentTitle") or "").strip().lower()
                if "pf" in title or "provident" in title:
                    key = "pf"
                elif "esi" in title:
                    key = "esi"
                elif "tds" in title or "income tax" in title:
                    key = "tds"
                elif "professional tax" in title:
                    key = "professional_tax"
                else:
                    continue
                breakdown[key] = breakdown.get(key, 0.0) + _num(item.get("amount"))
        currency = next((r.get("currencyCode") for r in register if r.get("currencyCode")), None) or "INR"
        return PayrollRunRecord(
            external_id=f"{group.get('identifier')}:{cycle.get('identifier')}",
            period_start=cycle_start,
            period_end=cycle_end,
            total_gross=sum(_num(r.get("grossAmount")) for r in register),
            total_deductions=sum(_num(r.get("totalDeductions")) for r in register),
            total_net=sum(_num(r.get("netAmount")) for r in register),
            employee_count=len(register),
            currency=currency,
            status=_RUN_STATUS.get(cycle.get("runStatus"), "completed"),
            breakdown=breakdown,
            metadata={"pay_group": group.get("name"), "month": cycle.get("month")},
        )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
