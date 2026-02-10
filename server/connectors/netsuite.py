"""
NetSuite ERP Connector - Enterprise resource planning data integration.

Provides:
- Invoice records and accounts receivable
- Journal entries and general ledger
- Chart of accounts
- Vendor records

API Documentation: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/chapter_1558708800.html
"""

import httpx
import logging
import hashlib
import hmac
import base64
import time
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import quote

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

logger = logging.getLogger(__name__)


@ConnectorRegistry.register
class NetSuiteConnector(BaseConnector):
    PROVIDER_ID = "netsuite"
    PROVIDER_NAME = "NetSuite"
    PROVIDER_DESCRIPTION = "Oracle NetSuite ERP platform. Import invoices, journal entries, chart of accounts, and vendor data for financial consolidation."
    PROVIDER_CATEGORY = ProviderCategory.ERP
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/chapter_1558708800.html"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._account_id = config.credentials.get("account_id", "")
        self._consumer_key = config.credentials.get("consumer_key", "")
        self._consumer_secret = config.credentials.get("consumer_secret", "")
        self._token_id = config.credentials.get("token_id", "")
        self._token_secret = config.credentials.get("token_secret", "")
        self._base_url = f"https://{self._account_id.replace('_', '-')}.suitetalk.api.netsuite.com/services/rest/record/v1" if self._account_id else ""
        self._client: Optional[httpx.AsyncClient] = None

    def _generate_oauth_header(self, method: str, url: str) -> str:
        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex

        params = {
            "oauth_consumer_key": self._consumer_key,
            "oauth_token": self._token_id,
            "oauth_signature_method": "HMAC-SHA256",
            "oauth_timestamp": timestamp,
            "oauth_nonce": nonce,
            "oauth_version": "1.0",
        }

        sorted_params = "&".join(f"{quote(k, safe='')}={quote(v, safe='')}" for k, v in sorted(params.items()))
        base_string = f"{method.upper()}&{quote(url, safe='')}&{quote(sorted_params, safe='')}"
        signing_key = f"{quote(self._consumer_secret, safe='')}&{quote(self._token_secret, safe='')}"

        signature = base64.b64encode(
            hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha256).digest()
        ).decode()

        auth_header = (
            f'OAuth realm="{self._account_id}",'
            f'oauth_consumer_key="{self._consumer_key}",'
            f'oauth_token="{self._token_id}",'
            f'oauth_signature_method="HMAC-SHA256",'
            f'oauth_timestamp="{timestamp}",'
            f'oauth_nonce="{nonce}",'
            f'oauth_version="1.0",'
            f'oauth_signature="{quote(signature, safe="")}"'
        )

        return auth_header

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "prefer": "transient",
                },
            )
        return self._client

    async def _make_request(self, method: str, path: str, **kwargs) -> httpx.Response:
        client = await self._get_client()
        full_url = f"{self._base_url}{path}"
        auth_header = self._generate_oauth_header(method, full_url)
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = auth_header
        return await getattr(client, method.lower())(path, headers=headers, **kwargs)

    async def authenticate(self) -> bool:
        if not all([self._account_id, self._consumer_key, self._consumer_secret, self._token_id, self._token_secret]):
            logger.warning("NetSuite credentials incomplete")
            return False

        try:
            response = await self._make_request("GET", "/account?limit=1")

            if response.status_code == 200:
                self._authenticated = True
                logger.info("NetSuite authentication successful")
                return True
            else:
                logger.warning(f"NetSuite auth failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"NetSuite authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            response = await self._make_request("GET", "/account?limit=1")
            return response.status_code == 200
        except Exception:
            return False

    async def get_accounts(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            response = await self._make_request("GET", "/account", params={"limit": limit})

            if response.status_code == 200:
                data = response.json()
                return data.get("items", data if isinstance(data, list) else [])
            return []
        except Exception as e:
            logger.error(f"NetSuite accounts fetch error: {e}")
            return []

    async def get_vendors(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        try:
            response = await self._make_request("GET", "/vendor", params={"limit": limit})

            if response.status_code == 200:
                data = response.json()
                return data.get("items", data if isinstance(data, list) else [])
            return []
        except Exception as e:
            logger.error(f"NetSuite vendors fetch error: {e}")
            return []

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        invoices = []
        try:
            params: Dict[str, Any] = {"limit": 100}
            response = await self._make_request("GET", "/invoice", params=params)

            if response.status_code != 200:
                logger.error(f"NetSuite invoices error: {response.status_code}")
                return []

            data = response.json()
            results = data.get("items", data if isinstance(data, list) else [])

            for inv in results:
                inv_date_str = inv.get("tranDate") or inv.get("createdDate", "")
                due_date_str = inv.get("dueDate", "")

                try:
                    inv_date = datetime.strptime(inv_date_str[:10], "%Y-%m-%d") if inv_date_str else datetime.now()
                except (ValueError, TypeError):
                    inv_date = datetime.now()

                if start_date and inv_date < start_date:
                    continue
                if end_date and inv_date > end_date:
                    continue

                try:
                    due_date = datetime.strptime(due_date_str[:10], "%Y-%m-%d") if due_date_str else None
                except (ValueError, TypeError):
                    due_date = None

                amount = float(inv.get("total", inv.get("amount", 0)))
                tax = float(inv.get("taxTotal", inv.get("tax", 0)))

                customer = inv.get("entity", {})
                customer_name = customer.get("refName", "") if isinstance(customer, dict) else str(customer)

                status_ref = inv.get("status", {})
                status = status_ref.get("refName", "pending") if isinstance(status_ref, dict) else str(status_ref)

                invoices.append(
                    InvoiceRecord(
                        external_id=str(inv.get("id", "")),
                        date=inv_date,
                        due_date=due_date,
                        customer_name=customer_name,
                        amount=amount - tax,
                        tax=tax,
                        total=amount,
                        currency=inv.get("currency", {}).get("refName", "USD") if isinstance(inv.get("currency"), dict) else "USD",
                        status=status.lower() if status else "pending",
                        metadata={
                            "tran_id": inv.get("tranId"),
                            "memo": inv.get("memo"),
                            "subsidiary": inv.get("subsidiary", {}).get("refName") if isinstance(inv.get("subsidiary"), dict) else None,
                            "source": "netsuite_invoice",
                        },
                    )
                )

        except Exception as e:
            logger.error(f"Error fetching NetSuite invoices: {e}")

        return invoices

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        entries = []
        try:
            params: Dict[str, Any] = {"limit": 100}
            response = await self._make_request("GET", "/journalEntry", params=params)

            if response.status_code != 200:
                logger.error(f"NetSuite journal entries error: {response.status_code}")
                return []

            data = response.json()
            results = data.get("items", data if isinstance(data, list) else [])

            for je in results:
                je_date_str = je.get("tranDate") or je.get("createdDate", "")
                try:
                    je_date = datetime.strptime(je_date_str[:10], "%Y-%m-%d") if je_date_str else datetime.now()
                except (ValueError, TypeError):
                    je_date = datetime.now()

                if start_date and je_date < start_date:
                    continue
                if end_date and je_date > end_date:
                    continue

                lines = je.get("line", {}).get("items", []) if isinstance(je.get("line"), dict) else []

                for line in lines:
                    account = line.get("account", {})
                    account_code = str(account.get("id", "")) if isinstance(account, dict) else str(account)
                    account_name = account.get("refName", "") if isinstance(account, dict) else ""

                    debit = float(line.get("debit", 0))
                    credit = float(line.get("credit", 0))

                    entries.append(
                        LedgerEntry(
                            external_id=f"{je.get('id', '')}-{line.get('line', '')}",
                            date=je_date,
                            account_code=account_code,
                            account_name=account_name,
                            debit=debit,
                            credit=credit,
                            description=line.get("memo") or je.get("memo", ""),
                            category=account_name,
                            metadata={
                                "journal_id": je.get("id"),
                                "tran_id": je.get("tranId"),
                                "subsidiary": je.get("subsidiary", {}).get("refName") if isinstance(je.get("subsidiary"), dict) else None,
                                "source": "netsuite_journal",
                            },
                        )
                    )

        except Exception as e:
            logger.error(f"Error fetching NetSuite journal entries: {e}")

        return entries

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        result = {
            "source_type": "connector_netsuite",
            "extraction_summary": "Synced from Oracle NetSuite ERP",
        }

        if invoices:
            paid_invoices = [inv for inv in invoices if inv.status in ("paid", "paidinfull", "completed")]
            result["revenue"] = sum(inv.total for inv in paid_invoices)
            result["invoices_count"] = len(invoices)
            result["accounts_receivable"] = sum(inv.total for inv in invoices if inv.status in ("open", "pending"))

        if ledger_entries:
            total_debits = sum(e.debit for e in ledger_entries)
            total_credits = sum(e.credit for e in ledger_entries)
            result["total_debits"] = total_debits
            result["total_credits"] = total_credits
            result["journal_entries_count"] = len(ledger_entries)

            categories: Dict[str, float] = {}
            for entry in ledger_entries:
                if entry.category and entry.debit > 0:
                    categories[entry.category] = categories.get(entry.category, 0) + entry.debit
            result["expense_breakdown"] = categories

        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check account_id, consumer_key, consumer_secret, token_id, token_secret"],
                    sync_started=sync_started,
                )

            invoices = await self.fetch_invoices()
            ledger = await self.fetch_ledger()
            accounts = await self.get_accounts()
            vendors = await self.get_vendors()
            financials = self.map_to_financials(invoices=invoices, ledger_entries=ledger)

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=len(invoices) + len(ledger) + len(accounts) + len(vendors),
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "financials": financials,
                    "invoices_count": len(invoices),
                    "journal_entries_count": len(ledger),
                    "accounts_count": len(accounts),
                    "vendors_count": len(vendors),
                },
            )

        except Exception as e:
            logger.error(f"NetSuite sync failed: {e}")
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
