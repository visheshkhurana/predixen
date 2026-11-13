"""
Meta Ads connector - monthly ad spend from Facebook and Instagram ads.

For a D2C brand the Meta ad account is usually the biggest marketing line.
This connector reads, per ad account and per full calendar month: spend,
impressions, clicks, and the purchases and purchase value Meta attributes to
its own ads. Spend feeds marketing_spend on the Profit screen (CM3, MER).

Meta's purchase value is NOT revenue. It is what Meta's attribution claims it
drove, measured by the pixel/CAPI, and it overlaps with every other channel's
claim. It is kept beside the store's numbers as "platform-reported ROAS" and
never used for MER, which divides the store's net revenue by total spend.

API: Marketing API (Graph API), GET /act_<id>/insights with
time_increment=monthly. Auth is an access token with ads_read on the ad
accounts: a system-user token from Business Settings (does not expire) or a
long-lived user token (~60 days). See docs/connectors/meta-ads.md.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import httpx

from .base import AuthType, BaseConnector, ConnectorConfig, ProviderCategory, SyncResult
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

# One place to bump when Meta deprecates a version (each lives ~2 years).
GRAPH_API_VERSION = "v24.0"
GRAPH_HOST = "graph.facebook.com"
BASE_URL = f"https://{GRAPH_HOST}/{GRAPH_API_VERSION}"

DEFAULT_LOOKBACK_MONTHS = 3  # Meta keeps revising recent attribution; re-read the last few months
MAX_LOOKBACK_MONTHS = 24
MAX_PAGES = 200
MAX_RETRIES = 4
BACKOFF_BASE_SECONDS = 2.0
BACKOFF_CAP_SECONDS = 60.0

INSIGHT_FIELDS = "spend,impressions,clicks,actions,action_values,account_currency"

# Purchase action types, most complete first. They overlap (omni_purchase
# already includes pixel purchases), so the first one present is used, never a sum.
PURCHASE_ACTION_TYPES = (
    "omni_purchase",
    "purchase",
    "offsite_conversion.fb_pixel_purchase",
)

# Graph API error codes (developers.facebook.com/docs/graph-api/guides/error-handling,
# .../marketing-api/insights/best-practices#ratelimits).
TOKEN_ERROR_CODES = {190, 102}
RATE_LIMIT_CODES = {4, 17, 32, 613, 80000, 80003, 80004, 80014}
PERMISSION_CODES = {10, 200, 294}  # 200-299 are permission errors too

_ACCOUNT_RE = re.compile(r"^(?:act_)?(\d{1,20})$")


class MetaAPIError(Exception):
    def __init__(self, message: str, code: Optional[int] = None, subcode: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.subcode = subcode


class MetaAuthError(MetaAPIError):
    """The token is expired, revoked or invalid: the founder must reconnect."""


class MetaPermissionError(MetaAPIError):
    """The token works but cannot read this ad account (missing ads_read or access)."""


class MetaRateLimitError(MetaAPIError):
    """Still throttled after the retries."""


def parse_account_ids(raw: Any) -> List[str]:
    """'act_123, 456' or ['act_123', '456'] -> ['act_123', 'act_456'], deduplicated, in order."""
    if isinstance(raw, str):
        parts = re.split(r"[\s,;]+", raw)
    elif isinstance(raw, (list, tuple)):
        parts = [str(p) for p in raw]
    else:
        parts = []
    out: List[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        match = _ACCOUNT_RE.fullmatch(part)
        if not match:
            raise ValueError(f"'{part}' is not an ad account id (expected act_<digits> or digits)")
        acct = f"act_{match.group(1)}"
        if acct not in out:
            out.append(acct)
    return out


def full_months(today: date, count: int) -> List[Tuple[date, date]]:
    """The last `count` complete calendar months before `today`, oldest first."""
    months: List[Tuple[date, date]] = []
    end = today.replace(day=1) - timedelta(days=1)
    for _ in range(max(1, count)):
        start = end.replace(day=1)
        months.append((start, end))
        end = start - timedelta(days=1)
    return list(reversed(months))


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _action_value(entries: Optional[Iterable[Dict[str, Any]]]) -> Optional[float]:
    """The value for the first purchase action type present, or None if none is."""
    by_type: Dict[str, float] = {}
    for entry in entries or []:
        kind = str(entry.get("action_type") or "")
        if kind in PURCHASE_ACTION_TYPES and kind not in by_type:
            by_type[kind] = _num(entry.get("value"))
    for kind in PURCHASE_ACTION_TYPES:
        if kind in by_type:
            return by_type[kind]
    return None


def parse_purchases(row: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """(purchase count, purchase value) from an insights row's actions / action_values."""
    return _action_value(row.get("actions")), _action_value(row.get("action_values"))


def bucket_monthly(
    rows: Iterable[Dict[str, Any]], months: List[Tuple[date, date]]
) -> Dict[str, Dict[str, Any]]:
    """Sum insights rows into the requested calendar months, keyed 'YYYY-MM-01'.

    With time_increment=monthly Meta returns one row per calendar month, but a
    row is placed by its date_start so a split or daily row still lands in the
    right month. Rows outside the window are dropped. Every month in the window
    gets an entry: no row from Meta for a month means nothing was spent.
    """
    out: Dict[str, Dict[str, Any]] = {
        start.isoformat(): {
            "spend": 0.0, "impressions": 0, "clicks": 0,
            "purchases": None, "purchase_value": None,
        }
        for start, _ in months
    }
    for row in rows:
        try:
            started = date.fromisoformat(str(row.get("date_start"))[:10])
        except ValueError:
            continue
        key = started.replace(day=1).isoformat()
        if key not in out:
            continue
        bucket = out[key]
        bucket["spend"] += _num(row.get("spend"))
        bucket["impressions"] += int(_num(row.get("impressions")))
        bucket["clicks"] += int(_num(row.get("clicks")))
        purchases, value = parse_purchases(row)
        if purchases is not None:
            bucket["purchases"] = (bucket["purchases"] or 0.0) + purchases
        if value is not None:
            bucket["purchase_value"] = (bucket["purchase_value"] or 0.0) + value
    for bucket in out.values():
        bucket["spend"] = round(bucket["spend"], 2)
        if bucket["purchase_value"] is not None:
            bucket["purchase_value"] = round(bucket["purchase_value"], 2)
        bucket["platform_roas"] = (
            round(bucket["purchase_value"] / bucket["spend"], 4)
            if bucket["purchase_value"] is not None and bucket["spend"] > 0 else None
        )
    return out


def _graph_error(res: httpx.Response) -> Tuple[Optional[int], Optional[int], str]:
    try:
        err = (res.json() or {}).get("error") or {}
    except ValueError:
        err = {}
    code = err.get("code")
    sub = err.get("error_subcode")
    msg = err.get("error_user_msg") or err.get("message") or f"HTTP {res.status_code}"
    return (int(code) if isinstance(code, (int, str)) and str(code).isdigit() else None,
            int(sub) if isinstance(sub, (int, str)) and str(sub).isdigit() else None,
            str(msg))


def _retry_after_seconds(res: httpx.Response, attempt: int) -> float:
    """Meta reports the wait in X-Business-Use-Case-Usage (minutes); else exponential backoff."""
    wait = BACKOFF_BASE_SECONDS * (2 ** attempt)
    header = res.headers.get("x-business-use-case-usage")
    if header:
        try:
            usage = json.loads(header)
            minutes = max(
                (_num(entry.get("estimated_time_to_regain_access"))
                 for entries in usage.values() for entry in entries),
                default=0.0,
            )
            if minutes > 0:
                wait = max(wait, minutes * 60)
        except (ValueError, AttributeError, TypeError):
            pass
    return min(wait, BACKOFF_CAP_SECONDS)


@ConnectorRegistry.register
class MetaAdsConnector(BaseConnector):
    PROVIDER_ID = "meta_ads"
    PROVIDER_NAME = "Meta Ads"
    PROVIDER_DESCRIPTION = (
        "Facebook and Instagram ad spend per month, for CM3 and MER. "
        "Meta-attributed purchases are shown as platform-reported, not revenue."
    )
    PROVIDER_CATEGORY = ProviderCategory.ERP
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developers.facebook.com/docs/marketing-api/insights"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._token = (config.credentials.get("access_token") or "").strip()
        self._raw_accounts = config.credentials.get("ad_account_ids") or config.credentials.get("ad_account_id") or ""
        settings = config.settings or {}
        try:
            lookback = int(settings.get("lookback_months") or DEFAULT_LOOKBACK_MONTHS)
        except (TypeError, ValueError):
            lookback = DEFAULT_LOOKBACK_MONTHS
        self._lookback = max(1, min(lookback, MAX_LOOKBACK_MONTHS))
        self._app_secret = os.getenv("META_APP_SECRET", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._sleep = asyncio.sleep  # replaced in tests
        self.auth_error: Optional[str] = None
        self.accounts: Dict[str, Dict[str, Any]] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=60.0)
        return self._client

    def _auth_params(self) -> Dict[str, str]:
        params = {"access_token": self._token}
        if self._app_secret:
            # Meta's recommended hardening: proves the call comes from our app's server.
            params["appsecret_proof"] = hmac.new(
                self._app_secret.encode(), self._token.encode(), hashlib.sha256
            ).hexdigest()
        return params

    async def _get(self, path_or_url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET with Graph error mapping and rate-limit backoff.

        `path_or_url` is a path under BASE_URL or a paging.next URL, which must
        point at graph.facebook.com (the token is never sent anywhere else).
        """
        client = await self._get_client()
        if path_or_url.startswith("http"):
            parts = urlsplit(path_or_url)
            if parts.scheme != "https" or parts.hostname != GRAPH_HOST:
                raise MetaAPIError(f"Refusing to follow a paging link to {parts.hostname}")
            # httpx replaces a URL's query when params are passed, so carry the
            # cursor over explicitly and re-apply our own auth params.
            url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
            query = {**dict(parse_qsl(parts.query)), **self._auth_params()}
        else:
            url, query = path_or_url, {**(params or {}), **self._auth_params()}

        for attempt in range(MAX_RETRIES + 1):
            res = await client.get(url, params=query)
            if res.status_code == 200:
                return res.json()
            code, subcode, message = _graph_error(res)
            if code in TOKEN_ERROR_CODES:
                raise MetaAuthError(
                    f"Meta access token is expired or no longer valid ({message}). Reconnect Meta Ads.",
                    code, subcode,
                )
            if code in PERMISSION_CODES or (code is not None and 200 <= code <= 299):
                raise MetaPermissionError(
                    f"The token cannot read this ad account ({message}). It needs the ads_read "
                    "permission and access to the account in Business Settings.",
                    code, subcode,
                )
            retryable = code in RATE_LIMIT_CODES or res.status_code == 429 or res.status_code >= 500
            if not retryable:
                raise MetaAPIError(f"Meta API error: {message}", code, subcode)
            if attempt == MAX_RETRIES:
                if code in RATE_LIMIT_CODES or res.status_code == 429:
                    raise MetaRateLimitError(
                        f"Meta is rate-limiting this ad account ({message}). Try the sync again later.",
                        code, subcode,
                    )
                raise MetaAPIError(f"Meta API unavailable: {message}", code, subcode)
            await self._sleep(_retry_after_seconds(res, attempt))
        raise MetaAPIError("unreachable")  # pragma: no cover

    async def _paged(self, path: str, params: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool]:
        rows: List[Dict[str, Any]] = []
        body = await self._get(path, params)
        for _ in range(MAX_PAGES):
            rows.extend(body.get("data") or [])
            next_url = (body.get("paging") or {}).get("next")
            if not next_url:
                return rows, False
            body = await self._get(next_url)
        return rows, True

    async def authenticate(self) -> bool:
        self.auth_error = None
        if not self._token:
            self.auth_error = "Enter a Meta access token with the ads_read permission."
            return False
        try:
            account_ids = parse_account_ids(self._raw_accounts)
        except ValueError as exc:
            self.auth_error = str(exc)
            return False
        if not account_ids:
            self.auth_error = "Enter at least one ad account id (act_<digits>)."
            return False
        try:
            for acct in account_ids:
                info = await self._get(f"/{acct}", {"fields": "name,currency,account_status,timezone_name"})
                self.accounts[acct] = {
                    "account_id": acct,
                    "name": info.get("name") or acct,
                    "currency": (info.get("currency") or "").upper() or None,
                    "account_status": info.get("account_status"),
                    "timezone": info.get("timezone_name"),
                }
        except MetaAPIError as exc:
            self.auth_error = f"{acct}: {exc}"
            logger.warning(f"Meta Ads auth failed: {exc}")
            return False
        except httpx.HTTPError as exc:
            self.auth_error = f"Could not reach Meta: {exc}"
            return False
        self._authenticated = True
        return True

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def fetch_account_months(self, acct: str, months: List[Tuple[date, date]]) -> Tuple[Dict[str, Dict[str, Any]], bool]:
        params = {
            "level": "account",
            "fields": INSIGHT_FIELDS,
            "time_increment": "monthly",
            "time_range": json.dumps({"since": months[0][0].isoformat(), "until": months[-1][1].isoformat()}),
            "limit": 100,
        }
        rows, truncated = await self._paged(f"/{acct}/insights", params)
        currency = self.accounts.get(acct, {}).get("currency")
        for row in rows:
            row_currency = (row.get("account_currency") or "").upper()
            if row_currency and not currency:
                currency = row_currency
                self.accounts.setdefault(acct, {"account_id": acct, "name": acct})["currency"] = currency
        return bucket_monthly(rows, months), truncated

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()

        def failed(message: str, **meta: Any) -> SyncResult:
            return SyncResult(
                success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                errors=[message], sync_started=sync_started,
                sync_completed=datetime.utcnow(), metadata=meta,
            )

        if not await self.authenticate():
            needs_reauth = bool(self.auth_error and "Reconnect Meta Ads" in self.auth_error)
            return failed(self.auth_error or "Authentication failed", needs_reauth=needs_reauth)

        months = full_months(sync_started.date(), self._lookback)
        per_month: Dict[str, List[Dict[str, Any]]] = {start.isoformat(): [] for start, _ in months}
        truncated = False
        try:
            for acct, info in self.accounts.items():
                buckets, cut = await self.fetch_account_months(acct, months)
                truncated = truncated or cut
                for period, bucket in buckets.items():
                    per_month[period].append({
                        "account_id": acct,
                        "account_name": info.get("name") or acct,
                        "currency": info.get("currency"),
                        **bucket,
                    })
        except MetaAuthError as exc:
            return failed(str(exc), needs_reauth=True)
        except MetaAPIError as exc:
            return failed(str(exc))
        except httpx.HTTPError as exc:
            return failed(f"Could not reach Meta: {exc}")

        return SyncResult(
            success=True,
            provider_id=self.PROVIDER_ID,
            sync_type="full",
            records_synced=sum(len(v) for v in per_month.values()),
            errors=["Page limit reached; some months may be incomplete"] if truncated else [],
            sync_started=sync_started,
            sync_completed=datetime.utcnow(),
            metadata={
                "ad_spend": {
                    "source": self.PROVIDER_ID,
                    "months": [{"period": p, "accounts": accts} for p, accts in per_month.items()],
                },
            },
        )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
