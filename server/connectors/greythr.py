"""
GreytHR Connector

Integrates with the greytHR API (V2) to fetch:
- Employee data
- Monthly salary statements (payroll)

API documentation (official Postman collection): https://api-docs.greythr.com/
- Auth:      POST https://api.greythr.com/oauth2/v2/client-token
             Basic auth (API user name : API password) + header x-greythr-domain: {company}.greythr.com
             -> {"access_token", "expires_in": 3599, ...}
- Every call then sends ACCESS-TOKEN: <token> and x-greythr-domain.
- Employees: GET /employee/v2/employees?page=&size=  -> {"data": [...], "pages": {"totalPages", ...}}
- Payroll:   GET /payroll/v2/employees/salary/statement/{yyyy-mm-01}
             -> {"data": [{employeeId, itemName, amount, type, itemOrder}, ...], "pages": {...}}
"""

import httpx
import logging
import re
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from urllib.parse import urlparse

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

API_BASE = "https://api.greythr.com"
TOKEN_PATH = "/oauth2/v2/client-token"
PAGE_SIZE = 100
MAX_PAGES = 200
DEFAULT_PAYROLL_MONTHS = 12
TOKEN_REFRESH_MARGIN = 120  # seconds

_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

RECONNECT_MESSAGE = (
    "greytHR needs to be reconnected: enter your greytHR domain (the 'acme' in acme.greythr.com), "
    "and the API user name (Access ID) and password (Secret) from greytHR Admin > Settings > API Details."
)


def normalize_greythr_domain(value: Optional[str]) -> str:
    """Accept 'acme', 'acme.greythr.com' or a URL on it; return 'acme.greythr.com' ('' if unusable)."""
    text = (value or "").strip().lower()
    if not text:
        return ""
    if "://" in text:
        text = urlparse(text).hostname or ""
    text = text.split("/", 1)[0]
    if text.endswith(".greythr.com"):
        text = text[: -len(".greythr.com")]
    if not _LABEL_RE.match(text) or text == "api":
        return ""
    return f"{text}.greythr.com"


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


def _month_starts(start: date, end: date) -> List[date]:
    months = []
    cur = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    while cur <= last:
        months.append(cur)
        cur = date(cur.year + (cur.month == 12), 1 if cur.month == 12 else cur.month + 1, 1)
    return months


def _month_end(month_start: date) -> date:
    nxt = date(month_start.year + (month_start.month == 12), 1 if month_start.month == 12 else month_start.month + 1, 1)
    return date.fromordinal(nxt.toordinal() - 1)


def summarize_salary_statement(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Collapse salary statement line items into gross / deductions / net per month.

    Per employee, greytHR returns an "INCOME" summary item (description GROSS) and a
    "DEDUCT" summary item (TOTAL DEDUCTIONS, negative). Components sit beneath them
    by itemOrder (/00001/00001/... income, /00001/00002/... deductions).
    """
    per_emp: Dict[str, Dict[str, float]] = {}
    breakdown: Dict[str, float] = {}
    for row in rows:
        emp = str(row.get("employeeId") or row.get("employeeNo") or "")
        if not emp:
            continue
        acc = per_emp.setdefault(emp, {"gross": None, "deduct": None, "income_items": 0.0, "deduct_items": 0.0})
        name = (row.get("itemName") or "").upper()
        kind = (row.get("type") or "").upper()
        order = row.get("itemOrder") or ""
        amount = _num(row.get("amount"))
        if name == "INCOME":
            acc["gross"] = amount
        elif name == "DEDUCT":
            acc["deduct"] = abs(amount)
        elif kind == "INCOME" and order.startswith("/00001/00001/"):
            acc["income_items"] += amount
        elif kind == "DEDUCT":
            acc["deduct_items"] += amount
            key = {"PF": "pf", "ESI": "esi", "INC_TAX": "tds", "PROF_TAX": "professional_tax"}.get(name)
            if key:
                breakdown[key] = breakdown.get(key, 0.0) + amount
    gross = deductions = 0.0
    paid = 0
    for acc in per_emp.values():
        g = acc["gross"] if acc["gross"] is not None else acc["income_items"]
        d = acc["deduct"] if acc["deduct"] is not None else acc["deduct_items"]
        gross += g
        deductions += d
        if g:
            paid += 1
    return {"gross": gross, "deductions": deductions, "net": gross - deductions,
            "employee_count": paid, "breakdown": breakdown}


@ConnectorRegistry.register
class GreytHRConnector(BaseConnector):
    """
    GreytHR connector for syncing HR and payroll data.

    Credentials: domain (acme or acme.greythr.com), api_access_id (API user name),
    api_secret (API password), generated in greytHR Admin > Settings > API Details.
    """

    PROVIDER_ID = "greythr"
    PROVIDER_NAME = "GreytHR"
    PROVIDER_DESCRIPTION = "Sync employee data and monthly payroll from GreytHR"
    PROVIDER_CATEGORY = ProviderCategory.HRIS
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://api-docs.greythr.com/"

    SUPPORTS_EMPLOYEES = True
    SUPPORTS_PAYROLL = True
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        creds = config.credentials or {}
        raw_domain = str(creds.get("domain") or "")
        # Connections saved before `domain` existed may carry https://acme.greythr.com as base_url.
        self._domain = normalize_greythr_domain(raw_domain or creds.get("base_url") or "")
        self._domain_invalid = bool(raw_domain.strip()) and not self._domain
        self._api_access_id = (creds.get("api_access_id") or "").strip()
        self._api_secret = (creds.get("api_secret") or "").strip()
        self._token = ""
        self._token_expires_at = 0.0
        self._client: Optional[httpx.AsyncClient] = None
        self.auth_error: Optional[str] = None

    def rotated_credentials(self) -> Optional[Dict[str, Any]]:
        return None  # short-lived token minted per run

    def _credential_problem(self) -> Optional[str]:
        if self._domain_invalid:
            return "greytHR domain should look like 'acme' or 'acme.greythr.com'."
        if not all((self._domain, self._api_access_id, self._api_secret)):
            return RECONNECT_MESSAGE
        return None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=API_BASE,
                headers={"Accept": "application/json", "x-greythr-domain": self._domain},
                timeout=30.0,
                follow_redirects=False,
            )
        return self._client

    async def _fetch_token(self) -> bool:
        client = await self._get_client()
        response = await client.post(TOKEN_PATH, auth=(self._api_access_id, self._api_secret))
        if response.status_code != 200:
            if response.status_code in (400, 401, 403):
                self.auth_error = (
                    f"greytHR rejected the API user name / password for {self._domain}. "
                    "Check them in greytHR Admin > Settings > API Details."
                )
            else:
                self.auth_error = f"greytHR token request failed ({response.status_code})."
            return False
        body = response.json() or {}
        token = body.get("access_token") or ""
        if not token:
            self.auth_error = "greytHR did not return an access token."
            return False
        self._token = token
        self._token_expires_at = time.monotonic() + float(body.get("expires_in") or 3599)
        client.headers["ACCESS-TOKEN"] = token
        return True

    async def _ensure_token(self) -> None:
        if not self._token or time.monotonic() > self._token_expires_at - TOKEN_REFRESH_MARGIN:
            if not await self._fetch_token():
                raise RuntimeError(self.auth_error or "greytHR token refresh failed")

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        await self._ensure_token()
        client = await self._get_client()
        response = await client.get(path, params=params)
        if response.status_code == 401:  # token expired early: refresh once
            self._token = ""
            await self._ensure_token()
            response = await client.get(path, params=params)
        return response

    async def authenticate(self) -> bool:
        """Mint a token and probe the employee list."""
        self.auth_error = None
        problem = self._credential_problem()
        if problem:
            self.auth_error = problem
            return False
        try:
            if not await self._fetch_token():
                return False
            response = await self._get("/employee/v2/employees", {"page": 1, "size": 1})
            if response.status_code == 200:
                self._authenticated = True
                logger.info("GreytHR authentication successful")
                return True
            self.auth_error = (
                "greytHR issued a token but refused the employee list "
                f"({response.status_code}). Make sure the API user has Employee read access."
            )
            return False
        except (httpx.HTTPError, RuntimeError) as e:
            logger.error(f"GreytHR authentication error: {e}")
            self.auth_error = self.auth_error or "Could not reach greytHR. Try again."
            return False

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def _get_paged(self, path: str, params: Optional[Dict[str, Any]] = None,
                         allow_missing: bool = False) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        page = 1
        while page <= MAX_PAGES:
            response = await self._get(path, {**(params or {}), "page": page, "size": PAGE_SIZE})
            if response.status_code != 200:
                if allow_missing and response.status_code in (400, 404, 204):
                    return items
                raise RuntimeError(f"greytHR {path} returned {response.status_code}")
            body = response.json() or {}
            batch = body.get("data") or []
            items.extend(b for b in batch if isinstance(b, dict))
            pages = body.get("pages") or {}
            total_pages = int(pages.get("totalPages") or 1)
            if page >= total_pages or not batch:
                return items
            page += 1
        logger.warning(f"greytHR {path}: stopped after {MAX_PAGES} pages; results truncated")
        return items

    async def fetch_employees(self) -> List[EmployeeRecord]:
        """GET /employee/v2/employees (all states) paged by pages.totalPages."""
        if not self._authenticated:
            if not await self.authenticate():
                return []

        employees: List[EmployeeRecord] = []
        for emp in await self._get_paged("/employee/v2/employees", {"state": "ALL"}):
            left = bool(emp.get("leftorg"))
            employees.append(EmployeeRecord(
                external_id=str(emp.get("employeeId") or ""),
                name=emp.get("name") or "",
                email=emp.get("email"),
                department=None,  # lives under /employee/v2/employees/categories
                designation=None,
                salary=None,
                join_date=_parse_date(emp.get("dateOfJoin")),
                status="inactive" if left else "active",
                metadata={
                    "employee_no": emp.get("employeeNo"),
                    "greythr_status": emp.get("status"),
                    "leaving_date": emp.get("leavingDate"),
                },
            ))
        logger.info(f"Fetched {len(employees)} employees from GreytHR")
        return employees

    async def fetch_payroll_runs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PayrollRunRecord]:
        """One run per payroll month from the monthly salary statement."""
        if not self._authenticated:
            if not await self.authenticate():
                return []

        today = date.today()
        end = (end_date.date() if end_date else today)
        if start_date:
            start = start_date.date()
        else:
            m = today.month - DEFAULT_PAYROLL_MONTHS
            start = date(today.year + (m - 1) // 12, (m - 1) % 12 + 1, 1)

        runs: List[PayrollRunRecord] = []
        for month in _month_starts(start, end):
            rows = await self._get_paged(
                f"/payroll/v2/employees/salary/statement/{month.isoformat()}", allow_missing=True
            )
            if not rows:
                continue  # payroll not processed for that month
            summary = summarize_salary_statement(rows)
            if not summary["gross"]:
                continue
            runs.append(PayrollRunRecord(
                external_id=f"greythr-{month.strftime('%Y-%m')}",
                period_start=datetime.combine(month, datetime.min.time()),
                period_end=datetime.combine(_month_end(month), datetime.min.time()),
                total_gross=summary["gross"],
                total_deductions=summary["deductions"],
                total_net=summary["net"],
                employee_count=summary["employee_count"],
                currency="INR",
                status="completed",
                breakdown=summary["breakdown"],
                metadata={"payroll_month": month.strftime("%Y-%m")},
            ))
        logger.info(f"Fetched {len(runs)} payroll months from GreytHR")
        return runs

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
