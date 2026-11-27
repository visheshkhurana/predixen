from __future__ import annotations
"""
1Password Business connector - seat usage and sign-in security signals.

Reads the 1Password Events API v2 with a bearer token from an Events Reporting
integration (1Password > Integrations > Events Reporting). Read-only.

Provides, for the last 30 days:
- distinct active users (unique target_user.uuid with a successful sign-in)
- total sign-ins and failed sign-ins by category
- optional seat cost: seats (or active users) x seat price, as a monthly
  "Software" expense ledger entry, with seat utilisation in its metadata

API reference: https://developer.1password.com/docs/events-api/reference/
(now served from https://www.1password.dev/events-api/reference/)

Credentials:
- bearer_token (required)
- region: us (default, 1password.com) | ent (ent.1password.com) | ca | eu
- seat_price_monthly (optional, e.g. 7.99)
- seats (optional, number of paid seats)

Like Ramp and Brex, the seat cost is reported as an expense_breakdown entry and
no company-wide opex figure is written: 1Password's cost is one line of opex,
not the month's total.
"""

import logging
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from .http import http_client

from .base import (
    AuthType,
    BaseConnector,
    ConnectorConfig,
    LedgerEntry,
    ProviderCategory,
    SyncResult,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

# Events API hosts per account region. Fixed allowlist: the region the user
# types is a key into this table, never part of a URL.
REGION_HOSTS = {
    "us": "https://events.1password.com",
    "ent": "https://events.ent.1password.com",
    "ca": "https://events.1password.ca",
    "eu": "https://events.1password.eu",
}
# Accept the sign-in domain too, since that is what founders see.
_REGION_ALIASES = {
    "": "us",
    "1password.com": "us",
    "com": "us",
    "ent.1password.com": "ent",
    "enterprise": "ent",
    "1password.ca": "ca",
    "1password.eu": "eu",
}

WINDOW_DAYS = 30
PAGE_LIMIT = 1000
MAX_PAGES = 20
# "firewall_reported_success": the sign-in went through; a firewall rule in
# report-only mode flagged it.
SUCCESS_CATEGORIES = {"success", "firewall_reported_success"}

TOKEN_HELP = (
    "In 1Password, open Integrations > Events Reporting, add an integration "
    "with 'Sign-in attempts' ticked, and paste its bearer token."
)


class OnePasswordAPIError(Exception):
    """A readable error from the Events API (bad token, rate limit, outage)."""


def resolve_region(region: Optional[str]) -> Optional[str]:
    """Normalise a region input to a REGION_HOSTS key, or None if unknown."""
    key = str(region or "").strip().lower()
    key = re.sub(r"^https?://", "", key).strip("/")
    if key.startswith("events."):
        key = key[len("events."):]
    key = _REGION_ALIASES.get(key, key)
    return key if key in REGION_HOSTS else None


def base_url_for_region(region: Optional[str]) -> str:
    resolved = resolve_region(region)
    if resolved is None:
        raise ValueError(f"Unknown 1Password region: {region!r}")
    return REGION_HOSTS[resolved]


def _parse_number(value: Any, field: str) -> Optional[float]:
    """Optional numeric credential. Blank -> None; '$7.99' and '1,200' are fine."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = re.sub(r"[\s,$€£₹]", "", str(value))
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            raise ValueError(f"{field} must be a number, got {value!r}")
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a number, got {value!r}")
    if number < 0:
        raise ValueError(f"{field} can't be negative")
    return number


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # Python < 3.11 can't parse more than 6 fractional digits.
    text = re.sub(r"(\.\d{6})\d+", r"\1", text)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _rfc3339(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def summarize_signins(items: List[Dict[str, Any]], since: Optional[datetime] = None) -> Dict[str, Any]:
    """Active users, total sign-ins and failures by category for a list of sign-in attempts."""
    active_users = set()
    successful = 0
    failed_by_category: Dict[str, int] = {}
    total = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        if since is not None:
            stamp = _parse_timestamp(item.get("timestamp"))
            if stamp is not None and stamp < since:
                continue
        total += 1
        category = str(item.get("category") or "unknown")
        if category in SUCCESS_CATEGORIES:
            successful += 1
            user = item.get("target_user") or {}
            user_id = user.get("uuid") if isinstance(user, dict) else None
            if user_id:
                active_users.add(user_id)
        else:
            failed_by_category[category] = failed_by_category.get(category, 0) + 1
    return {
        "active_users": len(active_users),
        "total_signins": total,
        "successful_signins": successful,
        "failed_signins": sum(failed_by_category.values()),
        "failed_by_category": dict(sorted(failed_by_category.items())),
    }


@ConnectorRegistry.register
class OnePasswordConnector(BaseConnector):
    PROVIDER_ID = "onepassword"
    PROVIDER_NAME = "1Password"
    PROVIDER_DESCRIPTION = (
        "1Password Business seat usage and sign-in security signals (active users, "
        "failed sign-ins), with optional seat cost in software spend."
    )
    PROVIDER_CATEGORY = ProviderCategory.SECURITY
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developer.1password.com/docs/events-api/reference/"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        creds = config.credentials or {}
        settings = config.settings or {}
        self._token = str(creds.get("bearer_token") or "").strip()
        if self._token.lower().startswith("bearer "):
            self._token = self._token[7:].strip()
        self._region_input = creds.get("region") or settings.get("region") or ""
        self._region = resolve_region(self._region_input)
        self._seat_price_raw = creds.get("seat_price_monthly", settings.get("seat_price_monthly"))
        self._seats_raw = creds.get("seats", settings.get("seats"))
        self._client: Optional[httpx.AsyncClient] = None
        self.auth_error: Optional[str] = None
        self.features: List[str] = []
        self.account_uuid: Optional[str] = None
        self.truncated = False
        self._signins: Optional[List[Dict[str, Any]]] = None
        self._window_start: Optional[datetime] = None
        self._window_end: Optional[datetime] = None

    # --- HTTP -----------------------------------------------------------------

    @property
    def base_url(self) -> str:
        return REGION_HOSTS[self._region or "us"]

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = http_client(
                base_url=self.base_url,
                timeout=30.0,
                follow_redirects=False,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    def _error_for(self, response: httpx.Response) -> str:
        status = response.status_code
        if status == 401:
            return (
                "1Password rejected the bearer token (401). Check the token and that the "
                f"region matches your account (now: {self._region or 'us'}). " + TOKEN_HELP
            )
        if status == 403:
            return "1Password refused access (403). The token may lack the 'Sign-in attempts' feature. " + TOKEN_HELP
        if status == 429:
            wait = response.headers.get("Retry-After")
            hint = f" in {wait} seconds" if wait and wait.isdigit() else " in a minute"
            return f"1Password rate limit reached (429). Try again{hint}."
        message = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                message = str(body.get("message") or "")
        except ValueError:
            pass
        return f"1Password returned {status}" + (f": {message[:200]}" if message else ".")

    def _validate_inputs(self) -> Optional[str]:
        if not self._token:
            return "Enter a 1Password Events API bearer token. " + TOKEN_HELP
        if self._region is None:
            return (
                f"Unknown 1Password region {self._region_input!r}. Use us (1password.com), "
                "ent (ent.1password.com), ca (1password.ca) or eu (1password.eu)."
            )
        try:
            _parse_number(self._seat_price_raw, "Seat price")
            seats = _parse_number(self._seats_raw, "Seats")
        except ValueError as exc:
            return str(exc) + "."
        if seats is not None and seats != int(seats):
            return "Seats must be a whole number."
        return None

    @property
    def seat_price(self) -> Optional[float]:
        try:
            return _parse_number(self._seat_price_raw, "Seat price")
        except ValueError:
            return None

    @property
    def seats(self) -> Optional[int]:
        try:
            value = _parse_number(self._seats_raw, "Seats")
        except ValueError:
            return None
        return int(value) if value is not None else None

    # --- Auth -----------------------------------------------------------------

    async def authenticate(self) -> bool:
        self.auth_error = self._validate_inputs()
        if self.auth_error:
            return False
        try:
            client = await self._get_client()
            response = await client.get("/api/v2/auth/introspect")
        except httpx.HTTPError as exc:
            logger.warning("1Password introspect failed: %s", exc)
            self.auth_error = f"Could not reach 1Password ({self.base_url}). Try again."
            return False

        if response.status_code != 200:
            self.auth_error = self._error_for(response)
            return False
        try:
            body = response.json()
        except ValueError:
            self.auth_error = "1Password returned an unreadable introspect response."
            return False

        self.features = [str(f) for f in (body.get("features") or [])] if isinstance(body, dict) else []
        self.account_uuid = body.get("account_uuid") if isinstance(body, dict) else None
        if "signinattempts" not in self.features:
            self.auth_error = (
                "This 1Password token can't read sign-in attempts (it has: "
                + (", ".join(self.features) or "no features")
                + "). " + TOKEN_HELP
            )
            return False

        self._authenticated = True
        return True

    async def test_connection(self) -> bool:
        if self._validate_inputs():
            return False
        try:
            client = await self._get_client()
            response = await client.get("/api/v2/auth/introspect")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    # --- Data -----------------------------------------------------------------

    async def fetch_signin_attempts(
        self, start_time: datetime, max_pages: int = MAX_PAGES
    ) -> List[Dict[str, Any]]:
        """All sign-in attempts since start_time, following the cursor up to max_pages."""
        client = await self._get_client()
        items: List[Dict[str, Any]] = []
        body: Dict[str, Any] = {"limit": PAGE_LIMIT, "start_time": _rfc3339(start_time)}
        self.truncated = False
        for page in range(max_pages):
            try:
                response = await client.post("/api/v2/signinattempts", json=body)
            except httpx.HTTPError as exc:
                raise OnePasswordAPIError(f"Could not reach 1Password: {exc}") from exc
            if response.status_code != 200:
                raise OnePasswordAPIError(self._error_for(response))
            data = response.json() or {}
            page_items = data.get("items") or []
            items.extend(i for i in page_items if isinstance(i, dict))
            cursor = data.get("cursor")
            if not data.get("has_more") or not cursor:
                return items
            body = {"cursor": cursor}
        self.truncated = True
        logger.warning("1Password: stopped after %s pages of sign-in attempts", max_pages)
        return items

    async def _load_signins(self) -> List[Dict[str, Any]]:
        if self._signins is None:
            self._window_end = datetime.now(timezone.utc)
            self._window_start = self._window_end - timedelta(days=WINDOW_DAYS)
            self._signins = await self.fetch_signin_attempts(self._window_start)
        return self._signins

    def _summary(self) -> Dict[str, Any]:
        return summarize_signins(self._signins or [], since=self._window_start)

    def seat_cost_entry(self, summary: Dict[str, Any]) -> Optional[LedgerEntry]:
        """Monthly seat cost as a Software expense, or None without a seat price."""
        price = self.seat_price
        if not price:
            return None
        seats = self.seats
        billed = seats if seats is not None else summary["active_users"]
        if not billed:
            return None
        end = self._window_end or datetime.now(timezone.utc)
        utilization = (summary["active_users"] / seats) if seats else None
        return LedgerEntry(
            external_id=f"1password-seats-{end.strftime('%Y-%m')}",
            date=end.replace(tzinfo=None),
            account_code="software",
            account_name="1Password",
            debit=round(billed * price, 2),
            credit=0.0,
            description=(
                f"1Password: {billed} {'paid seats' if seats is not None else 'active users'} "
                f"x {price:g}/month"
            ),
            category="Software",
            metadata={
                "source": "onepassword",
                "metric_type": "seat_cost",
                "vendor": "1Password",
                "billing_basis": "seats" if seats is not None else "active_users",
                "seats": seats,
                "seat_price_monthly": price,
                "active_users": summary["active_users"],
                "seat_utilization": round(utilization, 4) if utilization is not None else None,
                "unused_seats": max(seats - summary["active_users"], 0) if seats else None,
            },
        )

    def software_spend_payload(self, ledger: List[LedgerEntry]) -> Dict[str, Any]:
        """The seat cost as one 1Password line for its month (see services.software_spend)."""
        seat = next((e for e in ledger if e.metadata.get("metric_type") == "seat_cost"), None)
        if seat is None:
            return {"months": []}
        meta = seat.metadata
        return {"months": [{
            "period": seat.date.date().replace(day=1).isoformat(),
            "vendors": [{
                "vendor": "1Password",
                "amount": seat.debit,
                # 1Password bills Business plans in USD on its price list.
                "currency": "USD",
                "basis": "seats",
                "seats": meta.get("seats"),
                "active_users": meta.get("active_users"),
                "details": {
                    "seat_price_monthly": meta.get("seat_price_monthly"),
                    "billing_basis": meta.get("billing_basis"),
                    "unused_seats": meta.get("unused_seats"),
                    "seat_utilization": meta.get("seat_utilization"),
                },
            }],
        }]}

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        await self._load_signins()
        entry = self.seat_cost_entry(self._summary())
        return [entry] if entry else []

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        summary = self._summary()
        seats = self.seats
        result: Dict[str, Any] = {
            "source_type": "connector_onepassword",
            "extraction_summary": "Synced from 1Password Events API",
            "security": {
                **summary,
                "window_days": WINDOW_DAYS,
                "seats": seats,
                "seat_utilization": round(summary["active_users"] / seats, 4) if seats else None,
                "truncated": self.truncated,
            },
        }
        if self._window_start and self._window_end:
            result["period_start"] = self._window_start.date().isoformat()
            result["period_end"] = self._window_end.date().isoformat()
        spend = [e for e in (ledger_entries or []) if e.metadata.get("metric_type") == "seat_cost"]
        if spend:
            result["expense_breakdown"] = {"Software": sum(e.debit for e in spend)}
            result["software_spend"] = {"1Password": sum(e.debit for e in spend)}
        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()

        def failed(message: str) -> SyncResult:
            return SyncResult(
                success=False,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                errors=[message],
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
            )

        if not await self.authenticate():
            return failed(self.auth_error or "Authentication failed")
        try:
            ledger = await self.fetch_ledger()
        except OnePasswordAPIError as exc:
            return failed(str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.error("1Password sync failed: %s", exc)
            return failed(f"1Password sync failed: {exc}")

        warnings: List[str] = []
        if self.truncated:
            warnings.append(
                f"Read the first {MAX_PAGES * PAGE_LIMIT} sign-in attempts only; "
                "counts for the last 30 days may be low."
            )
        if self.seat_price and not ledger:
            warnings.append("Seat price is set but there are no seats or active users to bill.")

        financials = self.map_to_financials(ledger_entries=ledger)
        return SyncResult(
            success=True,
            provider_id=self.PROVIDER_ID,
            sync_type="full",
            records_synced=len(self._signins or []) + len(ledger),
            warnings=warnings,
            sync_started=sync_started,
            sync_completed=datetime.utcnow(),
            metadata={
                "financials": financials,
                "security": financials["security"],
                "software_spend": self.software_spend_payload(ledger),
            },
        )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
