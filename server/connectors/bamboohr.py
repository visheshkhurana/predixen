"""
BambooHR Connector - headcount, hires and exits, and salary run-rate.

API: https://documentation.bamboohr.com/reference
- Base: https://{companyDomain}.bamboohr.com/api/v1
- Auth: HTTP Basic, the API key as username and any password ("x").
- GET  /meta/fields                  sign-in check
- POST /reports/custom?format=JSON   one row per employee with the fields asked

Reports:
- headcount (active employees), by department and employment type
- hires and exits in the last 30 / 90 days
- monthly salary run-rate from current pay rates (salaried staff only), in
  the most common pay currency. It is an estimate from pay rates, not a payroll
  register, so it is sent as payroll only when most active staff have a
  salaried pay rate in that currency; otherwise it is reported and left out.
"""

import logging
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from .http import http_client

from .base import (
    AuthType,
    BaseConnector,
    ConnectorConfig,
    EmployeeRecord,
    ProviderCategory,
    SyncResult,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

# BambooHR moved to {domain}.bamboohr.com/api/v1 on 2025-07-03; the old
# api.bamboohr.com/api/gateway.php form still works but is the legacy one.
# https://documentation.bamboohr.com/docs/past-changes-to-the-api
API_TEMPLATE = "https://{domain}.bamboohr.com/api/v1"
REPORT_FIELDS = [
    "id", "displayName", "firstName", "lastName", "workEmail", "department", "division",
    "jobTitle", "location", "employmentHistoryStatus", "status", "hireDate",
    "terminationDate", "payRate", "payType", "payPer",
]
# Share of active employees that must have a salaried pay rate in the main
# currency before the run-rate is used as payroll.
PAYROLL_COVERAGE = 0.8
_PER_MONTH = {"year": 1 / 12, "month": 1.0, "quarter": 1 / 3, "week": 52 / 12, "day": 260 / 12}
_DOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def normalize_bamboo_domain(value: Optional[str]) -> str:
    """'acme', 'acme.bamboohr.com' or 'https://acme.bamboohr.com/home' -> 'acme' ('' if unusable)."""
    text = (value or "").strip().lower()
    text = re.sub(r"^https?://", "", text).split("/", 1)[0]
    if text.endswith(".bamboohr.com"):
        text = text[: -len(".bamboohr.com")]
    return text if _DOMAIN_RE.match(text) else ""


def parse_day(value: Any) -> Optional[date]:
    if not value or not isinstance(value, str) or value.startswith("0000"):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def parse_pay_rate(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """'85000.00 USD' -> (85000.0, 'USD'); unreadable -> (None, None)."""
    if not value or not isinstance(value, str):
        return None, None
    m = re.match(r"^\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([A-Za-z]{3})?\s*$", value)
    if not m:
        return None, None
    return float(m.group(1).replace(",", "")), (m.group(2) or "").upper() or None


def monthly_salary(emp: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
    """Monthly pay from a salaried pay rate; hourly or unknown periods -> None."""
    amount, currency = parse_pay_rate(emp.get("payRate"))
    if amount is None or amount <= 0:
        return None, None
    if str(emp.get("payType") or "").lower() not in ("salary", ""):
        return None, None
    factor = _PER_MONTH.get(str(emp.get("payPer") or "").strip().lower())
    if factor is None:
        return None, None
    return round(amount * factor, 2), currency


class BambooHRError(Exception):
    pass


@ConnectorRegistry.register
class BambooHRConnector(BaseConnector):
    PROVIDER_ID = "bamboohr"
    PROVIDER_NAME = "BambooHR"
    PROVIDER_DESCRIPTION = (
        "Headcount, hires and exits, and salary run-rate from BambooHR. "
        "Paste an API key and your BambooHR subdomain."
    )
    PROVIDER_CATEGORY = ProviderCategory.HRIS
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://documentation.bamboohr.com/reference"

    SUPPORTS_EMPLOYEES = True
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        creds = config.credentials
        self._api_key = (creds.get("api_key") or "").strip()
        self._domain = normalize_bamboo_domain(creds.get("company_domain"))
        self._client: Optional[httpx.AsyncClient] = None
        self.auth_error: Optional[str] = None
        self._rows: Optional[List[Dict[str, Any]]] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = http_client(
                base_url=API_TEMPLATE.format(domain=self._domain),
                auth=(self._api_key, "x"),
                headers={"Accept": "application/json"},
                timeout=30.0,
            )
        return self._client

    def _explain(self, status: int) -> str:
        if status == 401:
            return "BambooHR rejected the API key. Create a new one under your name > API Keys and reconnect."
        if status == 403:
            return "This BambooHR API key's user can't read employee data. Use a key from an admin or a user with employee access."
        if status == 404:
            return f"No BambooHR account at {self._domain}.bamboohr.com. Check the subdomain."
        if status == 429:
            return "BambooHR is rate limiting requests. Try the sync again in a few minutes."
        return f"BambooHR returned HTTP {status}."

    async def authenticate(self) -> bool:
        if not self._api_key:
            self.auth_error = "Enter your BambooHR API key."
            return False
        if not self._domain:
            self.auth_error = "Enter your BambooHR subdomain (the 'acme' in acme.bamboohr.com)."
            return False
        try:
            res = await (await self._get_client()).get("/meta/fields")
        except Exception as exc:  # noqa: BLE001
            self.auth_error = f"Couldn't reach BambooHR: {exc}"
            return False
        if res.status_code == 200:
            self._authenticated = True
            return True
        self.auth_error = self._explain(res.status_code)
        return False

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def _employee_rows(self) -> List[Dict[str, Any]]:
        if self._rows is not None:
            return self._rows
        res = await (await self._get_client()).post(
            "/reports/custom", params={"format": "JSON", "onlyCurrent": "true"},
            json={"title": "FounderConsole headcount", "fields": REPORT_FIELDS},
        )
        if res.status_code != 200:
            raise BambooHRError(self._explain(res.status_code))
        self._rows = list((res.json() or {}).get("employees") or [])
        return self._rows

    @staticmethod
    def _is_active(emp: Dict[str, Any], today: date) -> bool:
        if str(emp.get("status") or "").lower() == "inactive":
            return False
        ended = parse_day(emp.get("terminationDate"))
        return not (ended and ended <= today)

    async def fetch_employees(self) -> List[EmployeeRecord]:
        today = datetime.now(timezone.utc).date()
        out: List[EmployeeRecord] = []
        for emp in await self._employee_rows():
            monthly, currency = monthly_salary(emp)
            name = emp.get("displayName") or " ".join(p for p in (emp.get("firstName"), emp.get("lastName")) if p)
            hired = parse_day(emp.get("hireDate"))
            out.append(EmployeeRecord(
                external_id=str(emp.get("id") or ""),
                name=name or "",
                email=emp.get("workEmail"),
                department=emp.get("department") or None,
                designation=emp.get("jobTitle") or None,
                salary=monthly,
                join_date=datetime.combine(hired, datetime.min.time()) if hired else None,
                status="active" if self._is_active(emp, today) else "inactive",
                metadata={
                    "salary_period": "month" if monthly is not None else None,
                    "currency": currency,
                    "employment_type": emp.get("employmentHistoryStatus") or None,
                    "location": emp.get("location") or None,
                    "termination_date": emp.get("terminationDate") if parse_day(emp.get("terminationDate")) else None,
                },
            ))
        return out

    def hr_summary(self, rows: List[Dict[str, Any]], today: Optional[date] = None) -> Dict[str, Any]:
        today = today or datetime.now(timezone.utc).date()
        active = [e for e in rows if self._is_active(e, today)]
        d30, d90 = today - timedelta(days=30), today - timedelta(days=90)

        def within(field: str, since: date) -> int:
            return sum(1 for e in rows if (d := parse_day(e.get(field))) and since <= d <= today)

        pay = [monthly_salary(e) for e in active]
        currencies = Counter(cur for amt, cur in pay if amt is not None and cur)
        main = currencies.most_common(1)[0][0] if currencies else None
        in_main = [amt for amt, cur in pay if amt is not None and cur == main]
        coverage = (len(in_main) / len(active)) if active else 0.0
        exits_90 = within("terminationDate", d90)
        avg_heads = max(len(active) + exits_90 / 2, 1)
        return {
            "headcount": len(active),
            "by_department": dict(Counter((e.get("department") or "Unassigned") for e in active).most_common()),
            "by_employment_type": dict(Counter((e.get("employmentHistoryStatus") or "Unspecified") for e in active).most_common()),
            "hires_30d": within("hireDate", d30),
            "hires_90d": within("hireDate", d90),
            "exits_30d": within("terminationDate", d30),
            "exits_90d": exits_90,
            "attrition_90d": round(exits_90 / avg_heads, 4) if active else None,
            "salary_run_rate_monthly": round(sum(in_main), 2) if in_main else None,
            "salary_currency": main,
            "salary_coverage": round(coverage, 4),
            "other_pay_currencies": sorted(c for c in currencies if c != main),
        }

    def map_to_financials(self, employees=None, payroll_runs=None, ledger_entries=None, invoices=None) -> Dict[str, Any]:
        today = datetime.now(timezone.utc).date()
        summary = self.hr_summary(self._rows or [], today)
        result: Dict[str, Any] = {
            "source_type": "connector_bamboohr",
            "extraction_summary": f"Synced from BambooHR: {summary['headcount']} active employees",
            "period_start": today.replace(day=1).isoformat(),
            "period_end": today.isoformat(),
            "headcount": summary["headcount"],
            "hr": summary,
        }
        if summary["salary_run_rate_monthly"] and summary["salary_coverage"] >= PAYROLL_COVERAGE:
            result["payroll"] = summary["salary_run_rate_monthly"]
            result["payroll_currency"] = summary["salary_currency"]
            result["payroll_basis"] = "salary_run_rate"
        return result

    async def sync_all(self) -> SyncResult:
        started = datetime.utcnow()

        def failed(message: str) -> SyncResult:
            return SyncResult(success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                              errors=[message], sync_started=started, sync_completed=datetime.utcnow())

        if not await self.authenticate():
            return failed(self.auth_error or "BambooHR authentication failed")
        try:
            employees = await self.fetch_employees()
        except BambooHRError as exc:
            return failed(str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.error("BambooHR sync failed: %s", exc)
            return failed(f"BambooHR sync failed: {exc}")

        financials = self.map_to_financials(employees=employees)
        hr = financials["hr"]
        warnings: List[str] = []
        if hr["salary_run_rate_monthly"] and "payroll" not in financials:
            warnings.append(
                f"Only {round(hr['salary_coverage'] * 100)}% of active employees have a salaried pay rate in "
                f"{hr['salary_currency']}, so the salary run-rate is shown but not used as payroll."
            )
        if hr["other_pay_currencies"]:
            warnings.append(
                "Pay in " + ", ".join(hr["other_pay_currencies"]) +
                f" is left out of the {hr['salary_currency']} salary run-rate."
            )
        if not employees:
            warnings.append("BambooHR returned no employees.")
        return SyncResult(
            success=True,
            provider_id=self.PROVIDER_ID,
            sync_type="full",
            records_synced=len(employees),
            warnings=warnings,
            sync_started=started,
            sync_completed=datetime.utcnow(),
            metadata={"financials": financials, "hr_summary": hr},
        )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
