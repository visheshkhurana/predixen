"""
Pipedrive CRM Connector - Deal pipeline, contacts, and organization data.

Provides:
- Deal tracking and pipeline management
- Contact (person) records
- Organization records
- Revenue metrics from won deals

Deals, persons and organizations use API v2 (the v1 list endpoints went out of
support on 2026-08-01):
https://developers.pipedrive.com/changelog/post/deprecated-apiv1-endpoints-become-out-of-support
https://pipedrive.readme.io/docs/pipedrive-api-v2-migration-guide
`/v1/users/me` is not on the deprecated list and has no v2 equivalent, so the
auth check stays on it. The token goes in the `x-api-token` header for both.
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
from server.services import crm_pipeline

logger = logging.getLogger(__name__)


def pipedrive_deal_for_snapshot(
    deal: Dict[str, Any],
    stage_names: Optional[Dict[str, str]] = None,
    stage_probabilities: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    # Deal-level `probability` is usually null; Pipedrive weights a deal by its
    # stage's `deal_probability` (0..100) unless the deal overrides it.
    status = deal.get("status")
    prob = deal.get("probability")
    if prob in (None, ""):
        prob = (stage_probabilities or {}).get(str(deal.get("stage_id")))
    close = deal.get("won_time") if status == "won" else deal.get("lost_time") if status == "lost" else deal.get("expected_close_date")
    return {
        "amount": float(deal.get("value") or 0.0),
        "currency": deal.get("currency"),
        "stage": (stage_names or {}).get(str(deal.get("stage_id"))) or (
            f"Stage {deal.get('stage_id')}" if deal.get("stage_id") is not None else None),
        "status": status if status in ("open", "won", "lost") else "open",
        "close_date": close or deal.get("close_time"),
        "probability": crm_pipeline.probability(prob, scale="percent"),
    }


def _main_currency(deals: List[Dict[str, Any]]) -> Optional[str]:
    counts: Dict[str, int] = {}
    for d in deals:
        cur = (d.get("currency") or "").upper()
        if cur:
            counts[cur] = counts.get(cur, 0) + 1
    return max(counts, key=counts.get) if counts else None


@ConnectorRegistry.register
class PipedriveConnector(BaseConnector):
    PROVIDER_ID = "pipedrive"
    PROVIDER_NAME = "Pipedrive"
    PROVIDER_DESCRIPTION = "CRM for sales pipeline management. Import deals, contacts, and organizations. Track deal values and revenue metrics."
    PROVIDER_CATEGORY = ProviderCategory.CRM
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developers.pipedrive.com/docs/api/v2"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_token = config.credentials.get("api_token", "")
        self._company_domain = config.credentials.get("company_domain", "")
        self._client: Optional[httpx.AsyncClient] = None

    # v2 cursor pagination allows up to 500 items per page.
    PAGE_LIMIT = 500

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            # Host only: paths carry their version (/api/v2/... or /api/v1/users/me).
            self._client = httpx.AsyncClient(
                base_url=f"https://{self._company_domain}.pipedrive.com",
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "x-api-token": self._api_token,
                },
            )
        return self._client

    async def authenticate(self) -> bool:
        if not self._api_token or not self._company_domain:
            logger.warning("Pipedrive credentials incomplete (need api_token and company_domain)")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/api/v1/users/me")

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self._authenticated = True
                    logger.info("Pipedrive authentication successful")
                    return True

            logger.warning(f"Pipedrive auth failed: {response.status_code} - {response.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"Pipedrive authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/api/v1/users/me")
            return response.status_code == 200 and response.json().get("success", False)
        except Exception:
            return False

    async def _list_v2(
        self,
        path: str,
        limit: int,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Walk a v2 collection with `cursor` + `limit` until
        `additional_data.next_cursor` is null or `limit` items are collected."""
        if not self._authenticated:
            if not await self.authenticate():
                return []

        client = await self._get_client()
        items: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        while len(items) < limit:
            params: Dict[str, Any] = {"limit": min(limit - len(items), self.PAGE_LIMIT)}
            if extra_params:
                params.update(extra_params)
            if cursor:
                params["cursor"] = cursor

            response = await client.get(path, params=params)
            if response.status_code != 200:
                logger.error(f"Pipedrive {path} error: {response.status_code}")
                break

            data = response.json()
            if not data.get("success"):
                break

            items.extend(data.get("data") or [])
            cursor = (data.get("additional_data") or {}).get("next_cursor")
            if not cursor:
                break

        return items[:limit]

    async def get_deals(
        self,
        limit: int = 500,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            return await self._list_v2(
                "/api/v2/deals", limit, {"status": status} if status else None
            )
        except Exception as e:
            logger.error(f"Pipedrive deals fetch error: {e}")
            return []

    async def get_persons(self, limit: int = 200) -> List[Dict[str, Any]]:
        try:
            return await self._list_v2("/api/v2/persons", limit)
        except Exception as e:
            logger.error(f"Pipedrive persons fetch error: {e}")
            return []

    async def get_organizations(self, limit: int = 200) -> List[Dict[str, Any]]:
        try:
            return await self._list_v2("/api/v2/organizations", limit)
        except Exception as e:
            logger.error(f"Pipedrive organizations fetch error: {e}")
            return []

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        deals = await self.get_deals(limit=500, status="won")
        invoices = []

        # v2 deals carry only `org_id` (no `org_name`), so resolve names from the
        # organizations list. Best effort: an unresolved id leaves org_name "".
        org_names: Dict[str, str] = {}
        if any(d.get("org_id") for d in deals):
            for org in await self.get_organizations(limit=5000):
                org_names[str(org.get("id"))] = org.get("name") or ""

        for deal in deals:
            value = float(deal.get("value") or 0)
            if value <= 0:
                continue

            won_time_str = deal.get("won_time", "") or deal.get("close_time", "")
            try:
                won_date = datetime.fromisoformat(won_time_str.replace("Z", "+00:00")) if won_time_str else datetime.now()
            except (ValueError, TypeError):
                won_date = datetime.now()

            if start_date and won_date < start_date:
                continue
            if end_date and won_date > end_date:
                continue

            currency = deal.get("currency") or "USD"

            invoices.append(
                InvoiceRecord(
                    external_id=str(deal.get("id", "")),
                    date=won_date,
                    customer_name=deal.get("title", ""),
                    amount=value,
                    total=value,
                    currency=currency,
                    status="paid",
                    metadata={
                        "pipeline_id": deal.get("pipeline_id", ""),
                        "stage_id": deal.get("stage_id", ""),
                        "org_id": deal.get("org_id"),
                        "org_name": org_names.get(str(deal.get("org_id")), "") if deal.get("org_id") else "",
                        "source": "pipedrive_deal",
                    },
                )
            )

        return invoices

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        organizations = await self.get_organizations(limit=500)
        entries = []

        for org in organizations:
            org_id = str(org.get("id", ""))
            org_name = org.get("name", "Unknown")

            add_time_str = org.get("add_time", "")
            try:
                add_date = datetime.fromisoformat(add_time_str.replace("Z", "+00:00")) if add_time_str else datetime.now()
            except (ValueError, TypeError):
                add_date = datetime.now()

            if start_date and add_date < start_date:
                continue
            if end_date and add_date > end_date:
                continue

            entries.append(
                LedgerEntry(
                    external_id=f"pipedrive_org_{org_id}",
                    date=add_date,
                    account_code=org_id,
                    account_name=org_name,
                    debit=0.0,
                    credit=0.0,
                    description=f"Organization: {org_name}",
                    category="CRM Organization",
                    metadata={
                        "open_deals_count": org.get("open_deals_count", 0),
                        "won_deals_count": org.get("won_deals_count", 0),
                        "address": org.get("address", ""),
                        "source": "pipedrive_organization",
                    },
                )
            )

        return entries

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        result = {
            "source_type": "connector_pipedrive",
            "extraction_summary": "Synced from Pipedrive CRM",
        }

        if invoices:
            result["revenue"] = sum(inv.total for inv in invoices)
            result["deals_won"] = len(invoices)

        if ledger_entries:
            result["organizations_count"] = len(ledger_entries)

        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check api_token and company_domain"],
                    sync_started=sync_started,
                )

            deals = await self.get_deals(limit=500)
            persons = await self.get_persons(limit=200)
            organizations = await self.get_organizations(limit=200)
            invoices = await self.fetch_invoices()
            ledger = await self.fetch_ledger()
            financials = self.map_to_financials(invoices=invoices, ledger_entries=ledger)
            stage_names: Dict[str, str] = {}
            stage_probs: Dict[str, Any] = {}
            try:
                for stage in await self._list_v2("/api/v2/stages", 500):
                    stage_names[str(stage.get("id"))] = stage.get("name") or ""
                    stage_probs[str(stage.get("id"))] = stage.get("deal_probability")
            except Exception:  # stage names are cosmetic; ids still group deals
                pass

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(deals) + len(persons) + len(organizations),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "deals_count": len(deals),
                    "persons_count": len(persons),
                    "organizations_count": len(organizations),
                    "crm_pipeline": crm_pipeline.build_snapshot(
                        [pipedrive_deal_for_snapshot(d, stage_names, stage_probs) for d in deals], _main_currency(deals),
                        truncated=len(deals) >= 500,
                    ),
                },
            )

        except Exception as e:
            logger.error(f"Pipedrive sync failed: {e}")
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
