"""
RazorpayX connector (India payroll via documented payouts and contacts).

Payroll cost is the sum of processed RazorpayX payouts whose purpose is
``salary`` (amounts are paise). Headcount is the count of active contacts
with type ``employee``.

RazorpayX Payroll (Opfin) is a different product. Its public API only
addresses one employee at a time, and the partner API needs a partner key
this app does not have. Those endpoints are not called. Callers without a
RazorpayX account number, or with no processed salary payouts, get a
not-available error instead of invented payroll numbers.

Docs:
- https://razorpay.com/docs/api/x/payouts/
- https://razorpay.com/docs/api/x/contacts/
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    AuthType,
    BaseConnector,
    ConnectorConfig,
    EmployeeRecord,
    PayrollRunRecord,
    ProviderCategory,
    SyncResult,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.razorpay.com/v1"
PAGE_SIZE = 100
MAX_PAGES = 10

PAYROLL_API_UNAVAILABLE = (
    "RazorpayX Payroll (Opfin) does not publish a company payroll or headcount API. "
    "Partner access needs a partner key this app does not have, so those endpoints are not called."
)

ACCOUNT_NUMBER_REQUIRED = (
    "RazorpayX payroll sync needs account_number (the Customer Identifier or current "
    "account salary payouts are debited from). "
    + PAYROLL_API_UNAVAILABLE
    + " Payroll is the sum of processed RazorpayX payouts with purpose 'salary'."
)

NO_SALARY_PAYOUTS = (
    "RazorpayX returned no processed payouts with purpose 'salary', so payroll was not written. "
    + PAYROLL_API_UNAVAILABLE
)


class RazorpayXApiError(Exception):
    """A documented RazorpayX call failed or cannot be made."""


def payout_window_start(now: Optional[datetime] = None) -> int:
    """Unix timestamp for the first day of the month two months before ``now`` (UTC)."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    month_index = current.year * 12 + (current.month - 1) - 2
    year, month0 = divmod(month_index, 12)
    start = datetime(year, month0 + 1, 1, tzinfo=timezone.utc)
    return int(start.timestamp())


def _month_key(created_at: Any) -> Optional[str]:
    try:
        timestamp = int(created_at)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m")


def _paise(value: Any) -> int:
    try:
        amount = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return amount if amount > 0 else 0


def financials_from_razorpayx(
    contacts: List[Dict[str, Any]],
    payouts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Map RazorpayX contacts and payouts onto payroll and headcount.

    Only the latest calendar month that has processed salary payouts is used,
    so an earlier month in the fetch window is not added into this month's cost.
    Amounts are converted from paise to INR. Fees and tax are not payroll.
    """
    headcount = 0
    for contact in contacts:
        if contact.get("type") != "employee":
            continue
        if contact.get("active") is False:
            continue
        headcount += 1

    by_month: Dict[str, int] = {}
    counts: Dict[str, int] = {}
    for payout in payouts:
        if payout.get("purpose") != "salary" or payout.get("status") != "processed":
            continue
        month = _month_key(payout.get("created_at"))
        amount = _paise(payout.get("amount"))
        if not month or amount <= 0:
            continue
        by_month[month] = by_month.get(month, 0) + amount
        counts[month] = counts.get(month, 0) + 1

    if not by_month:
        return {
            "headcount": headcount,
            "unavailable": NO_SALARY_PAYOUTS,
        }

    month = max(by_month)
    payroll = by_month[month] / 100
    return {
        "payroll": payroll,
        "headcount": headcount,
        "month": month,
        "salary_payout_count": counts[month],
        "extraction_summary": (
            f"RazorpayX processed salary payouts for {month}: {payroll:.2f} INR "
            f"across {headcount} active employee contacts. "
            "Fees are excluded. RazorpayX Payroll (Opfin) company payroll runs are not available on this API."
        ),
    }


def _describe_failure(response: httpx.Response) -> str:
    description = ""
    try:
        body = response.json()
    except Exception:
        body = None
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("description"):
            description = str(error["description"])
    if response.status_code in (401, 403):
        return "RazorpayX rejected the API key or secret."
    if description:
        return f"RazorpayX request failed ({response.status_code}): {description}"
    return f"RazorpayX request failed ({response.status_code})."


@ConnectorRegistry.register
class RazorpayXConnector(BaseConnector):
    """RazorpayX salary payouts and employee contacts."""

    PROVIDER_ID = "razorpayx"
    PROVIDER_ALIASES = ("razorpayx_payroll",)
    PROVIDER_NAME = "RazorpayX"
    PROVIDER_DESCRIPTION = (
        "Sync processed salary payouts and employee contacts from RazorpayX"
    )
    PROVIDER_CATEGORY = ProviderCategory.PAYROLL
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://razorpay.com/docs/api/x/payouts/"

    SUPPORTS_EMPLOYEES = True
    SUPPORTS_PAYROLL = True
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        credentials = config.credentials or {}
        settings = config.settings or {}
        self._api_key = str(credentials.get("api_key") or "").strip()
        self._api_secret = str(credentials.get("api_secret") or "").strip()
        account = credentials.get("account_number") or settings.get("account_number") or ""
        self._account_number = str(account).strip()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                auth=(self._api_key, self._api_secret),
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def _collect(self, path: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        client = await self._get_client()
        items: List[Dict[str, Any]] = []
        skip = 0
        for _ in range(MAX_PAGES):
            page_params = {**params, "count": PAGE_SIZE, "skip": skip}
            response = await client.get(path, params=page_params)
            if response.status_code != 200:
                raise RazorpayXApiError(_describe_failure(response))
            body = response.json()
            batch = body.get("items") if isinstance(body, dict) else None
            if not isinstance(batch, list):
                raise RazorpayXApiError(f"RazorpayX {path} response did not include an items list.")
            items.extend(item for item in batch if isinstance(item, dict))
            if len(batch) < PAGE_SIZE:
                return items
            skip += PAGE_SIZE
        return items

    def _fail(self, sync_started: datetime, message: str) -> SyncResult:
        return SyncResult(
            success=False,
            provider_id=self.PROVIDER_ID,
            sync_type="full",
            errors=[message],
            sync_started=sync_started,
            sync_completed=datetime.utcnow(),
        )

    async def authenticate(self) -> bool:
        """Verify the key pair with the documented contacts list."""
        if not self._api_key or not self._api_secret:
            return False
        try:
            client = await self._get_client()
            response = await client.get("/contacts", params={"count": 1})
        except Exception as exc:
            logger.error("RazorpayX authentication error: %s", exc)
            return False
        if response.status_code == 200:
            self._authenticated = True
            logger.info("RazorpayX authentication successful")
            return True
        logger.warning("RazorpayX auth failed: %s", response.status_code)
        return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/contacts", params={"count": 1})
            return response.status_code in (200, 401, 403)
        except Exception:
            return False

    async def fetch_employees(self) -> List[EmployeeRecord]:
        contacts = await self._collect("/contacts", {"type": "employee"})
        employees: List[EmployeeRecord] = []
        for contact in contacts:
            if contact.get("type") != "employee":
                continue
            employees.append(
                EmployeeRecord(
                    external_id=str(contact.get("id") or ""),
                    name=str(contact.get("name") or ""),
                    email=contact.get("email"),
                    status="active" if contact.get("active") is not False else "inactive",
                )
            )
        return employees

    async def fetch_payroll_runs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[PayrollRunRecord]:
        if not self._account_number:
            raise RazorpayXApiError(ACCOUNT_NUMBER_REQUIRED)
        params: Dict[str, Any] = {"account_number": self._account_number}
        if start_date is not None:
            params["from"] = int(start_date.timestamp())
        else:
            params["from"] = payout_window_start()
        if end_date is not None:
            params["to"] = int(end_date.timestamp())
        payouts = await self._collect("/payouts", params)
        mapped = financials_from_razorpayx([], payouts)
        if mapped.get("unavailable"):
            return []
        year, month = (int(part) for part in mapped["month"].split("-"))
        period = datetime(year, month, 1)
        return [
            PayrollRunRecord(
                external_id=f"razorpayx-salary-{mapped['month']}",
                period_start=period,
                period_end=period,
                total_gross=mapped["payroll"],
                total_deductions=0,
                total_net=mapped["payroll"],
                employee_count=mapped["salary_payout_count"],
                currency="INR",
                status="processed",
            )
        ]

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        if not self._api_key or not self._api_secret:
            return self._fail(sync_started, "RazorpayX API key and secret are required.")
        if not self._account_number:
            return self._fail(sync_started, ACCOUNT_NUMBER_REQUIRED)
        if not await self.authenticate():
            return self._fail(
                sync_started,
                "Authentication failed. Check the RazorpayX API key and secret.",
            )
        try:
            contacts = await self._collect("/contacts", {"type": "employee"})
            payouts = await self._collect(
                "/payouts",
                {
                    "account_number": self._account_number,
                    "from": payout_window_start(),
                },
            )
        except RazorpayXApiError as exc:
            return self._fail(sync_started, str(exc))
        except Exception as exc:
            logger.error("RazorpayX sync failed: %s", exc)
            return self._fail(
                sync_started,
                "RazorpayX sync failed before payroll numbers could be read.",
            )

        mapped = financials_from_razorpayx(contacts, payouts)
        if mapped.get("unavailable"):
            return self._fail(sync_started, mapped["unavailable"])

        return SyncResult(
            success=True,
            provider_id=self.PROVIDER_ID,
            sync_type="full",
            records_synced=mapped["headcount"] + mapped["salary_payout_count"],
            sync_started=sync_started,
            sync_completed=datetime.utcnow(),
            metadata={
                "financials": {
                    "payroll": mapped["payroll"],
                    "headcount": mapped["headcount"],
                    "extraction_summary": mapped["extraction_summary"],
                }
            },
        )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
