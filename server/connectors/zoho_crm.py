"""
Zoho CRM Connector - deal pipeline, won deals, accounts and contacts.

Uses the same Zoho OAuth client as Zoho Books ("Connect with Zoho"), with
Zoho CRM read scopes. Calls go to the data centre the founder signed in on
(zoho.com, zoho.in, zoho.eu, ...), recorded as `dc` at connect time.

API: https://www.zoho.com/crm/developer/docs/api/v8/
- GET /crm/v8/org                       org name and main currency
- GET /crm/v8/Deals?fields=...          deals, 200 a page
- GET /crm/v8/{Accounts,Contacts}/actions/count

Reports:
- pipeline snapshot (open value and count by stage, weighted value, won/lost
  in 30 days, 90-day win rate) -> services.crm_pipeline
- won deals closed this calendar month as revenue for this month, declared
  as the record's period (not lifetime won deals)
"""

import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from server.services import crm_pipeline

from .base import (
    AuthType,
    BaseConnector,
    ConnectorConfig,
    InvoiceRecord,
    ProviderCategory,
    SyncResult,
)
from .registry import ConnectorRegistry
from .zoho_books import ZOHO_DCS

logger = logging.getLogger(__name__)

PER_PAGE = 200
# Zoho CRM serves page/per_page up to 2,000 records; past that it needs a
# page_token. 2,000 deals covers the pipelines this is for; more is flagged.
MAX_PAGES = 10
DEAL_FIELDS = "Deal_Name,Amount,Stage,Closing_Date,Probability,Pipeline,Currency,Account_Name,Created_Time"


def zoho_crm_urls(dc: str) -> tuple:
    """(token_url, crm_api_base) for a data centre."""
    accounts, api = ZOHO_DCS.get(dc, ZOHO_DCS["com"])
    return f"https://{accounts}/oauth/v2/token", f"https://{api}/crm/v8"


def deal_status(deal: Dict[str, Any]) -> str:
    """open / won / lost. Zoho's default stages are "Closed Won" (100%) and
    "Closed Lost" / "Closed-Lost to Competition" (0%); custom stages keep the
    probability, so 100% counts as won and a closed 0% stage as lost."""
    stage = str(deal.get("Stage") or "").lower()
    prob = crm_pipeline.probability(deal.get("Probability"))
    if "won" in stage and "closed" in stage:
        return "won"
    if "lost" in stage:
        return "lost"
    if prob == 1.0:
        return "won"
    if prob == 0.0 and "closed" in stage:
        return "lost"
    return "open"


class ZohoCRMError(Exception):
    pass


@ConnectorRegistry.register
class ZohoCRMConnector(BaseConnector):
    PROVIDER_ID = "zoho_crm"
    PROVIDER_NAME = "Zoho CRM"
    PROVIDER_DESCRIPTION = (
        "Deal pipeline from Zoho CRM: open pipeline by stage, weighted value, "
        "win rate, and deals won this month."
    )
    PROVIDER_CATEGORY = ProviderCategory.CRM
    AUTH_TYPE = AuthType.OAUTH2
    DOCS_URL = "https://www.zoho.com/crm/developer/docs/api/v8/"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        creds = config.credentials
        self._client_id = creds.get("client_id", "")
        self._client_secret = creds.get("client_secret", "")
        self._refresh_token = creds.get("refresh_token", "")
        self._access_token = creds.get("access_token", "")
        self._token_url, self._api_base = zoho_crm_urls((creds.get("dc") or "com").strip())
        self._client: Optional[httpx.AsyncClient] = None
        self.auth_error: Optional[str] = None
        self.org: Dict[str, Any] = {}
        self.truncated = False
        self._deals: Optional[List[Dict[str, Any]]] = None

    # ------------------------------------------------------------- auth/http

    async def _refresh_access_token(self) -> bool:
        if not self._refresh_token:
            return False
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(self._token_url, data={
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "grant_type": "refresh_token",
                })
            data = res.json() if res.status_code == 200 else {}
        except Exception as exc:  # noqa: BLE001
            logger.error("Zoho CRM token refresh error: %s", exc)
            return False
        token = data.get("access_token")
        if not token:
            # Zoho reports some failures as HTTP 200 + {"error": ...}
            logger.error("Zoho CRM token refresh failed: %s", data.get("error") or res.status_code)
            return False
        self._access_token = token
        if self._client:
            self._client.headers["Authorization"] = f"Zoho-oauthtoken {token}"
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._api_base,
                headers={"Authorization": f"Zoho-oauthtoken {self._access_token}"},
                timeout=30.0,
            )
        return self._client

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None, _retried: bool = False) -> httpx.Response:
        client = await self._get_client()
        res = await client.get(path, params=params)
        if res.status_code == 401 and not _retried and await self._refresh_access_token():
            return await self._get(path, params, _retried=True)
        return res

    async def authenticate(self) -> bool:
        try:
            if not self._access_token and not await self._refresh_access_token():
                self.auth_error = "Zoho sign-in has expired. Reconnect Zoho CRM."
                return False
            res = await self._get("/org")
        except Exception as exc:  # noqa: BLE001
            self.auth_error = f"Couldn't reach Zoho CRM: {exc}"
            return False
        if res.status_code == 200:
            orgs = (res.json() or {}).get("org") or []
            self.org = orgs[0] if orgs else {}
            self._authenticated = True
            return True
        if res.status_code == 401:
            self.auth_error = "Zoho sign-in has expired or was revoked. Reconnect Zoho CRM."
        elif res.status_code == 403:
            self.auth_error = "This Zoho login can't read Zoho CRM (no CRM access or missing scope). Reconnect and allow CRM access."
        else:
            self.auth_error = f"Zoho CRM returned HTTP {res.status_code} on sign-in."
        return False

    async def test_connection(self) -> bool:
        return await self.authenticate()

    @property
    def org_currency(self) -> Optional[str]:
        org = self.org or {}
        cur = org.get("iso_code") or org.get("currency")
        if isinstance(cur, dict):
            cur = cur.get("iso_code")
        return str(cur).upper()[:3] if isinstance(cur, str) and cur else None

    # ----------------------------------------------------------------- data

    async def get_deals(self) -> List[Dict[str, Any]]:
        if self._deals is not None:
            return self._deals
        deals: List[Dict[str, Any]] = []
        for page in range(1, MAX_PAGES + 1):
            res = await self._get("/Deals", {"fields": DEAL_FIELDS, "per_page": PER_PAGE, "page": page})
            if res.status_code == 204:
                break
            if res.status_code != 200:
                raise ZohoCRMError(f"Zoho CRM deals request failed (HTTP {res.status_code}).")
            body = res.json() or {}
            deals.extend(body.get("data") or [])
            if not (body.get("info") or {}).get("more_records"):
                break
        else:
            self.truncated = True
        self._deals = deals
        return deals

    async def count(self, module: str) -> Optional[int]:
        try:
            res = await self._get(f"/{module}/actions/count")
        except Exception:  # noqa: BLE001
            return None
        if res.status_code != 200:
            return None
        value = (res.json() or {}).get("count")
        return int(value) if isinstance(value, (int, float)) else None

    def normalised(self, deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "amount": float(d.get("Amount") or 0.0),
                "currency": d.get("Currency") or self.org_currency,
                "stage": d.get("Stage"),
                "status": deal_status(d),
                "close_date": d.get("Closing_Date"),
                "probability": crm_pipeline.probability(d.get("Probability")),
            }
            for d in deals
        ]

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        """Won deals closed in [start_date, end_date] (default: this calendar month)."""
        today = datetime.now(timezone.utc).date()
        start = start_date.date() if start_date else today.replace(day=1)
        end = end_date.date() if end_date else today
        out: List[InvoiceRecord] = []
        for d in await self.get_deals():
            amount = float(d.get("Amount") or 0.0)
            closed = crm_pipeline.parse_day(d.get("Closing_Date"))
            if deal_status(d) != "won" or amount <= 0 or not closed or not (start <= closed <= end):
                continue
            account = d.get("Account_Name")
            out.append(InvoiceRecord(
                external_id=str(d.get("id", "")),
                date=datetime.combine(closed, datetime.min.time()),
                customer_name=(account.get("name") if isinstance(account, dict) else None) or d.get("Deal_Name"),
                amount=amount,
                total=amount,
                currency=d.get("Currency") or self.org_currency or "USD",
                status="paid",
                metadata={"source": "zoho_crm_deal", "stage": d.get("Stage"), "pipeline": d.get("Pipeline")},
            ))
        return out

    def map_to_financials(self, employees=None, payroll_runs=None, ledger_entries=None, invoices=None) -> Dict[str, Any]:
        today = datetime.now(timezone.utc).date()
        result: Dict[str, Any] = {
            "source_type": "connector_zoho_crm",
            "extraction_summary": "Synced from Zoho CRM (deals won this month)",
            "period_start": today.replace(day=1).isoformat(),
            "period_end": today.isoformat(),
        }
        main = self.org_currency
        won = [i for i in (invoices or []) if not main or (i.currency or "").upper() == main]
        if won:
            result["revenue"] = round(sum(i.total for i in won), 2)
            result["deals_won"] = len(won)
        return result

    async def sync_all(self) -> SyncResult:
        started = datetime.utcnow()

        def failed(message: str) -> SyncResult:
            return SyncResult(success=False, provider_id=self.PROVIDER_ID, sync_type="full",
                              errors=[message], sync_started=started, sync_completed=datetime.utcnow(),
                              metadata={"needs_reauth": True} if "Reconnect" in message else {})

        if not await self.authenticate():
            return failed(self.auth_error or "Zoho CRM authentication failed")
        try:
            deals = await self.get_deals()
            invoices = await self.fetch_invoices()
        except ZohoCRMError as exc:
            return failed(str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.error("Zoho CRM sync failed: %s", exc)
            return failed(f"Zoho CRM sync failed: {exc}")

        accounts = await self.count("Accounts")
        contacts = await self.count("Contacts")
        snapshot = crm_pipeline.build_snapshot(self.normalised(deals), self.org_currency, truncated=self.truncated)
        warnings: List[str] = []
        if self.truncated:
            warnings.append(f"Read the first {MAX_PAGES * PER_PAGE} deals only; pipeline totals may be low.")
        if snapshot["other_currencies"]:
            warnings.append(
                "Deals in " + ", ".join(sorted(snapshot["other_currencies"])) +
                f" are counted apart, not added to {self.org_currency} totals."
            )
        if not deals:
            warnings.append("Zoho CRM has no deals yet.")

        return SyncResult(
            success=True,
            provider_id=self.PROVIDER_ID,
            sync_type="full",
            records_synced=len(deals),
            warnings=warnings,
            sync_started=started,
            sync_completed=datetime.utcnow(),
            metadata={
                "financials": self.map_to_financials(invoices=invoices),
                "crm_pipeline": snapshot,
                "deals_count": len(deals),
                "accounts_count": accounts,
                "contacts_count": contacts,
                "org_name": (self.org or {}).get("company_name"),
            },
        )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
