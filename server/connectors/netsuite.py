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
from urllib.parse import quote, urlsplit, parse_qsl

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

SUITEQL_PAGE_SIZE = 1000
SUITEQL_MAX_ROWS = 10000


def _f(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_ns_date(value: Any) -> Optional[datetime]:
    """Queries ask for TO_CHAR(..., 'YYYY-MM-DD'); other formats are a fallback
    (the account's own date format, which is ambiguous for D/M vs M/D)."""
    if not value:
        return None
    text = str(value)[:10]
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None

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
        self.query_errors: List[str] = []
        self._consumer_key = config.credentials.get("consumer_key", "")
        self._consumer_secret = config.credentials.get("consumer_secret", "")
        self._token_id = config.credentials.get("token_id", "")
        self._token_secret = config.credentials.get("token_secret", "")
        self._base_url = f"https://{self._account_id.replace('_', '-')}.suitetalk.api.netsuite.com/services/rest/record/v1" if self._account_id else ""
        self._client: Optional[httpx.AsyncClient] = None

    def _generate_oauth_header(
        self,
        method: str,
        url: str,
        query_params: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
        nonce: Optional[str] = None,
    ) -> str:
        """
        OAuth 1.0a (TBA) Authorization header, signed per RFC 5849 section 3.4.1.

        The base-string URI is scheme://host/path with the query removed, and
        every query parameter (from the URL and from `query_params`) joins the
        oauth_* parameters in the normalized parameter string. Signing the URL
        with its query left in, and leaving the query out of the parameters,
        made NetSuite reject every request that carried `?limit=`.
        """
        timestamp = timestamp or str(int(time.time()))
        nonce = nonce or uuid.uuid4().hex

        def enc(v: Any) -> str:
            return quote(str(v), safe="~")

        parts = urlsplit(url)
        base_uri = f"{parts.scheme.lower()}://{parts.netloc.lower()}{parts.path}"

        oauth_params = {
            "oauth_consumer_key": self._consumer_key,
            "oauth_token": self._token_id,
            "oauth_signature_method": "HMAC-SHA256",
            "oauth_timestamp": timestamp,
            "oauth_nonce": nonce,
            "oauth_version": "1.0",
        }

        pairs = list(parse_qsl(parts.query, keep_blank_values=True))
        for k, v in (query_params or {}).items():
            if isinstance(v, (list, tuple)):
                pairs.extend((k, item) for item in v)
            elif v is not None:
                pairs.append((k, v))
        pairs.extend(oauth_params.items())

        encoded = sorted((enc(k), enc(v)) for k, v in pairs)
        sorted_params = "&".join(f"{k}={v}" for k, v in encoded)
        base_string = f"{method.upper()}&{enc(base_uri)}&{enc(sorted_params)}"
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
        auth_header = self._generate_oauth_header(method, full_url, kwargs.get("params"))
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

    @property
    def _suiteql_url(self) -> str:
        return self._base_url.replace("/services/rest/record/v1", "/services/rest/query/v1/suiteql")

    async def _suiteql(self, query: str, max_rows: int = SUITEQL_MAX_ROWS) -> Optional[List[Dict[str, Any]]]:
        """Run a SuiteQL query, following hasMore/offset. None if the first
        page fails (bad permissions or an unknown field), so a sync can say so
        instead of reporting zero.

        The REST record list endpoints (GET /record/v1/invoice) return only
        `id` and `links` per item, which is why invoices used to come back as
        0 dated "now" and journal entries had no lines.
        https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_156414087576.html
        """
        client = await self._get_client()
        rows: List[Dict[str, Any]] = []
        offset = 0
        while len(rows) < max_rows:
            params = {"limit": SUITEQL_PAGE_SIZE, "offset": offset}
            headers = {
                "Authorization": self._generate_oauth_header("POST", self._suiteql_url, params),
                "Prefer": "transient",
            }
            try:
                res = await client.post(self._suiteql_url, params=params, headers=headers, json={"q": query})
            except Exception as e:
                logger.error(f"NetSuite SuiteQL error: {e}")
                return rows or None
            if res.status_code != 200:
                logger.error(f"NetSuite SuiteQL {res.status_code}: {res.text[:300]}")
                self.query_errors.append(f"NetSuite query failed (HTTP {res.status_code})")
                return rows or None
            body = res.json() or {}
            items = body.get("items") or []
            rows.extend(i for i in items if isinstance(i, dict))
            if not body.get("hasMore") or not items:
                break
            offset += len(items)
        return rows

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[InvoiceRecord]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        start = (start_date or datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        end = (end_date or datetime.now()).strftime("%Y-%m-%d")
        # foreigntotal is the invoice total in its own currency; currency.symbol
        # is the ISO code.
        query = (
            "SELECT t.id, t.tranid, TO_CHAR(t.trandate, 'YYYY-MM-DD') AS trandate, "
            "TO_CHAR(t.duedate, 'YYYY-MM-DD') AS duedate, t.foreigntotal, t.memo, "
            "BUILTIN.DF(t.status) AS status_name, BUILTIN.DF(t.entity) AS customer, "
            "BUILTIN.DF(t.subsidiary) AS subsidiary, c.symbol AS currency "
            "FROM transaction t LEFT JOIN currency c ON c.id = t.currency "
            "WHERE t.type = 'CustInvc' "
            f"AND t.trandate >= TO_DATE('{start}', 'YYYY-MM-DD') "
            f"AND t.trandate <= TO_DATE('{end}', 'YYYY-MM-DD') "
            "ORDER BY t.trandate DESC"
        )
        rows = await self._suiteql(query) or []
        invoices: List[InvoiceRecord] = []
        for inv in rows:
            inv_date = _parse_ns_date(inv.get("trandate")) or datetime.now()
            total = _f(inv.get("foreigntotal"))
            status_name = str(inv.get("status_name") or "").lower()
            if "paid" in status_name:
                status = "paid"
            elif "void" in status_name or "rejected" in status_name:
                status = "cancelled"
            else:
                status = "open"
            invoices.append(
                InvoiceRecord(
                    external_id=str(inv.get("id", "")),
                    date=inv_date,
                    due_date=_parse_ns_date(inv.get("duedate")),
                    customer_name=str(inv.get("customer") or ""),
                    amount=total,
                    tax=0.0,
                    total=total,
                    currency=str(inv.get("currency") or "USD").upper()[:3],
                    status=status,
                    metadata={
                        "tran_id": inv.get("tranid"),
                        "memo": inv.get("memo"),
                        "subsidiary": inv.get("subsidiary"),
                        "status_name": inv.get("status_name"),
                        "source": "netsuite_invoice",
                    },
                )
            )
        return invoices

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        start = (start_date or datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        end = (end_date or datetime.now()).strftime("%Y-%m-%d")
        query = (
            "SELECT t.id, t.tranid, TO_CHAR(t.trandate, 'YYYY-MM-DD') AS trandate, "
            "t.memo AS header_memo, tl.id AS line_id, tl.memo, "
            "tl.debitforeignamount, tl.creditforeignamount, tl.expenseaccount AS account_id, "
            "BUILTIN.DF(tl.expenseaccount) AS account_name, BUILTIN.DF(t.subsidiary) AS subsidiary "
            "FROM transaction t JOIN transactionline tl ON tl.transaction = t.id "
            "WHERE t.type = 'Journal' AND t.posting = 'T' "
            f"AND t.trandate >= TO_DATE('{start}', 'YYYY-MM-DD') "
            f"AND t.trandate <= TO_DATE('{end}', 'YYYY-MM-DD') "
            "ORDER BY t.trandate DESC"
        )
        rows = await self._suiteql(query) or []
        entries: List[LedgerEntry] = []
        for line in rows:
            account_name = str(line.get("account_name") or "")
            entries.append(
                LedgerEntry(
                    external_id=f"{line.get('id', '')}-{line.get('line_id', '')}",
                    date=_parse_ns_date(line.get("trandate")) or datetime.now(),
                    account_code=str(line.get("account_id") or ""),
                    account_name=account_name,
                    debit=_f(line.get("debitforeignamount")),
                    credit=_f(line.get("creditforeignamount")),
                    description=line.get("memo") or line.get("header_memo") or "",
                    category=account_name,
                    metadata={
                        "journal_id": line.get("id"),
                        "tran_id": line.get("tranid"),
                        "subsidiary": line.get("subsidiary"),
                        "source": "netsuite_journal",
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
            "source_type": "connector_netsuite",
            "extraction_summary": "Synced from Oracle NetSuite ERP",
        }

        if invoices:
            # Invoiced this month (accrual), in the main currency. The old
            # figure summed every paid invoice the list returned.
            today = datetime.now().date()
            month_start = today.replace(day=1)
            live = [i for i in invoices if i.status != "cancelled"]
            counts: Dict[str, int] = {}
            for i in live:
                counts[i.currency] = counts.get(i.currency, 0) + 1
            main = max(counts, key=counts.get) if counts else None
            month = [i for i in live if month_start <= i.date.date() <= today and i.currency == main]
            result["revenue"] = round(sum(i.total for i in month), 2)
            if main:
                result["revenue_currency"] = main
            result["period_start"] = month_start.isoformat()
            result["period_end"] = today.isoformat()
            result["invoices_count"] = len(invoices)
            result["accounts_receivable"] = round(
                sum(i.total for i in live if i.status == "open" and i.currency == main), 2)

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
                warnings=list(dict.fromkeys(self.query_errors)),
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
