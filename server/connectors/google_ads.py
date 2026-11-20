"""
Google Ads connector - monthly ad spend from Google Search, Shopping,
Performance Max and YouTube campaigns.

Like Meta Ads, this feeds marketing_spend on the Profit screen (CM3, MER) per
account and calendar month. Google's conversion value is what Google's own
attribution claims; it is kept as platform-reported and never used as revenue.

Auth is OAuth 2.0 with the adwords scope. The founder clicks "Connect with
Google"; the callback (server/api/google_ads_oauth.py) stores the refresh
token. The app-level secrets live in the environment, never with a company:

  GOOGLE_ADS_CLIENT_ID         OAuth client from the Cloud project that holds
                               the Google Ads API access level
  GOOGLE_ADS_CLIENT_SECRET     its secret
  GOOGLE_ADS_DEVELOPER_TOKEN   optional, legacy. Google retired developer tokens
                               in Sept 2026: the access level now belongs to the
                               Cloud project that owns the OAuth client, so the
                               header is sent only when this is set.
  GOOGLE_ADS_LOGIN_CUSTOMER_ID optional manager account id, digits only. Leave
                               unset when founders connect their own accounts.

There is deliberately no fallback to the sign-in GOOGLE_CLIENT_ID: that client
lives in a different Cloud project, and calls made with it run at Test level.

API: REST googleAds:search with GAQL, segments.month.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from .http import http_client

from .base import AuthType, BaseConnector, ConnectorConfig, ProviderCategory, SyncResult
from .meta_ads import DEFAULT_LOOKBACK_MONTHS, MAX_LOOKBACK_MONTHS, full_months
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

API_VERSION = "v26"
API_HOST = "https://googleads.googleapis.com"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/adwords"
MAX_RETRIES = 3


def app_config() -> Dict[str, str]:
    return {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "").strip(),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET", "").strip(),
        "login_customer_id": re.sub(r"\D", "", os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")),
    }


def is_configured() -> bool:
    cfg = app_config()
    return bool(cfg["client_id"] and cfg["client_secret"])


def parse_customer_ids(raw: Any) -> List[str]:
    """'123-456-7890, 9876543210' -> ['1234567890', '9876543210']."""
    if isinstance(raw, (list, tuple)):
        parts = [str(p) for p in raw]
    else:
        parts = re.split(r"[,\s]+", str(raw or ""))
    ids: List[str] = []
    for part in parts:
        digits = re.sub(r"\D", "", part)
        if not digits:
            continue
        if len(digits) != 10:
            raise ValueError(f"'{part.strip()}' is not a Google Ads customer id (10 digits, e.g. 123-456-7890).")
        if digits not in ids:
            ids.append(digits)
    return ids


class GoogleAdsError(Exception):
    pass


class GoogleAdsAuthError(GoogleAdsError):
    pass


def bucket_rows(rows: List[Dict[str, Any]], months: List[Tuple[date, date]]) -> Dict[str, Dict[str, Any]]:
    """Sum googleAds:search rows into {month_start_iso: totals}. Spend is in micros."""
    buckets: Dict[str, Dict[str, Any]] = {
        start.isoformat(): {"spend": 0.0, "impressions": 0, "clicks": 0, "purchases": 0.0, "purchase_value": 0.0}
        for start, _ in months
    }
    for row in rows:
        month = str((row.get("segments") or {}).get("month") or "")[:10]
        if month not in buckets:
            continue
        m = row.get("metrics") or {}
        b = buckets[month]
        b["spend"] += int(m.get("costMicros") or 0) / 1_000_000
        b["impressions"] += int(m.get("impressions") or 0)
        b["clicks"] += int(m.get("clicks") or 0)
        b["purchases"] += float(m.get("conversions") or 0)
        b["purchase_value"] += float(m.get("conversionsValue") or 0)
    for b in buckets.values():
        b["spend"] = round(b["spend"], 2)
        b["purchase_value"] = round(b["purchase_value"], 2)
        b["purchases"] = round(b["purchases"], 2)
    return buckets


@ConnectorRegistry.register
class GoogleAdsConnector(BaseConnector):
    PROVIDER_ID = "google_ads"
    PROVIDER_NAME = "Google Ads"
    PROVIDER_DESCRIPTION = (
        "Google Search, Shopping, Performance Max and YouTube ad spend per month, for CM3 and MER. "
        "Google-attributed conversions are shown as platform-reported, not revenue."
    )
    PROVIDER_CATEGORY = ProviderCategory.ERP
    AUTH_TYPE = AuthType.OAUTH2
    DOCS_URL = "https://developers.google.com/google-ads/api/docs/start"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        creds = config.credentials or {}
        self._refresh_token = (creds.get("refresh_token") or "").strip()
        self._raw_customers = creds.get("customer_ids") or ""
        settings = config.settings or {}
        try:
            lookback = int(settings.get("lookback_months") or DEFAULT_LOOKBACK_MONTHS)
        except (TypeError, ValueError):
            lookback = DEFAULT_LOOKBACK_MONTHS
        self._lookback = max(1, min(lookback, MAX_LOOKBACK_MONTHS))
        self._app = app_config()
        self._access_token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._sleep = asyncio.sleep  # replaced in tests
        self.auth_error: Optional[str] = None
        self.accounts: Dict[str, Dict[str, Any]] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = http_client(timeout=60.0)
        return self._client

    async def _refresh_access_token(self) -> None:
        client = await self._get_client()
        res = await client.post(TOKEN_URL, data={
            "client_id": self._app["client_id"],
            "client_secret": self._app["client_secret"],
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        })
        if res.status_code != 200:
            raise GoogleAdsAuthError("Google sign-in for Google Ads has expired or was revoked. Reconnect Google Ads.")
        self._access_token = res.json().get("access_token")

    def _headers(self) -> Dict[str, str]:
        headers = {"Authorization": f"Bearer {self._access_token}"}
        if self._app["developer_token"]:
            headers["developer-token"] = self._app["developer_token"]
        if self._app["login_customer_id"]:
            headers["login-customer-id"] = self._app["login_customer_id"]
        return headers

    async def _request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        client = await self._get_client()
        url = f"{API_HOST}/{API_VERSION}/{path.lstrip('/')}"
        for attempt in range(MAX_RETRIES + 1):
            res = await client.request(method, url, headers=self._headers(), json=json_body)
            if res.status_code == 200:
                return res.json()
            try:
                message = (res.json().get("error") or {}).get("message") or res.text[:200]
            except ValueError:
                message = res.text[:200]
            if res.status_code == 401:
                raise GoogleAdsAuthError("Google sign-in for Google Ads has expired or was revoked. Reconnect Google Ads.")
            if res.status_code == 403:
                raise GoogleAdsError(f"Google Ads refused access ({message}).")
            if res.status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                await self._sleep(min(2 ** attempt * 2, 30))
                continue
            raise GoogleAdsError(f"Google Ads API error: {message}")
        raise GoogleAdsError("unreachable")  # pragma: no cover

    async def _search(self, customer_id: str, query: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        body: Dict[str, Any] = {"query": query}
        for _ in range(50):
            page = await self._request("POST", f"customers/{customer_id}/googleAds:search", body)
            rows.extend(page.get("results") or [])
            token = page.get("nextPageToken")
            if not token:
                break
            body = {"query": query, "pageToken": token}
        return rows

    async def authenticate(self) -> bool:
        self.auth_error = None
        if not is_configured():
            self.auth_error = "Google Ads isn't set up on this FounderConsole server yet."
            return False
        if not self._refresh_token:
            self.auth_error = "Connect with Google to give FounderConsole read access to Google Ads."
            return False
        try:
            await self._refresh_access_token()
            ids = parse_customer_ids(self._raw_customers)
            if not ids:
                listed = await self._request("GET", "customers:listAccessibleCustomers")
                ids = [str(n).split("/")[-1] for n in listed.get("resourceNames") or []]
            skipped: List[str] = []
            for cid in ids:
                try:
                    rows = await self._search(
                        cid,
                        "SELECT customer.id, customer.descriptive_name, customer.currency_code, customer.manager FROM customer",
                    )
                except GoogleAdsAuthError:
                    raise
                except GoogleAdsError as exc:
                    # A login usually sees some accounts it can't read: closed or
                    # cancelled ones, or ones only reachable through a manager.
                    # One of those must not sink the whole connection.
                    logger.warning("Google Ads: skipping customer %s: %s", cid, exc)
                    skipped.append(f"{cid}: {exc}")
                    continue
                info = (rows[0].get("customer") if rows else {}) or {}
                if info.get("manager"):
                    continue  # manager accounts hold no spend of their own
                self.accounts[cid] = {
                    "account_id": cid,
                    "name": info.get("descriptiveName") or cid,
                    "currency": (info.get("currencyCode") or "").upper() or None,
                }
            self.skipped_accounts = skipped
        except ValueError as exc:
            self.auth_error = str(exc)
            return False
        except GoogleAdsError as exc:
            self.auth_error = str(exc)
            return False
        except httpx.HTTPError as exc:
            self.auth_error = f"Could not reach Google Ads: {exc}"
            return False
        if not self.accounts:
            self.auth_error = "This Google login has no Google Ads accounts with spend (only manager accounts or none)."
            if getattr(self, "skipped_accounts", None):
                self.auth_error += " Couldn't read: " + "; ".join(self.skipped_accounts)[:300]
            return False
        self._authenticated = True
        return True

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()

        def failed(message: str, **meta: Any) -> SyncResult:
            return SyncResult(
                success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                errors=[message], sync_started=sync_started,
                sync_completed=datetime.utcnow(), metadata=meta,
            )

        if not await self.authenticate():
            needs_reauth = bool(self.auth_error and "Reconnect Google Ads" in self.auth_error)
            return failed(self.auth_error or "Authentication failed", needs_reauth=needs_reauth)

        months = full_months(sync_started.date(), self._lookback)
        per_month: Dict[str, List[Dict[str, Any]]] = {start.isoformat(): [] for start, _ in months}
        query = (
            "SELECT segments.month, metrics.cost_micros, metrics.impressions, metrics.clicks, "
            "metrics.conversions, metrics.conversions_value FROM customer "
            f"WHERE segments.date BETWEEN '{months[0][0].isoformat()}' AND '{months[-1][1].isoformat()}'"
        )
        try:
            for cid, info in self.accounts.items():
                buckets = bucket_rows(await self._search(cid, query), months)
                for period, bucket in buckets.items():
                    per_month[period].append({
                        "account_id": cid,
                        "account_name": info.get("name") or cid,
                        "currency": info.get("currency"),
                        **bucket,
                    })
        except GoogleAdsAuthError as exc:
            return failed(str(exc), needs_reauth=True)
        except GoogleAdsError as exc:
            return failed(str(exc))
        except httpx.HTTPError as exc:
            return failed(f"Could not reach Google Ads: {exc}")

        return SyncResult(
            success=True,
            provider_id=self.PROVIDER_ID,
            sync_type="full",
            records_synced=sum(len(v) for v in per_month.values()),
            errors=[],
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
