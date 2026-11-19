"""
Zoho Books Connector

Integrates with Zoho Books API to fetch:
- Invoices and payments
- Expenses
- Chart of accounts / Ledger
- Contacts (customers/vendors)

API Documentation: https://www.zoho.com/books/api/v3/
Authentication: OAuth 2.0
"""

import httpx
import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import (
    BaseConnector,
    ConnectorConfig,
    AuthType,
    ProviderCategory,
    LedgerEntry,
    InvoiceRecord,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

ZOHO_API_BASE = "https://books.zoho.com/api/v3"
ZOHO_AUTH_URL = "https://accounts.zoho.com/oauth/v2/token"

# Zoho runs separate data centres; an org on zoho.in can only be reached
# through the .in hosts. The OAuth callback tells us which one
# (accounts-server); only these known domains are accepted.
# Data centre -> (accounts host, API host). Canada lives on zohocloud.ca.
ZOHO_DCS = {
    "com": ("accounts.zoho.com", "www.zohoapis.com"),
    "in": ("accounts.zoho.in", "www.zohoapis.in"),
    "eu": ("accounts.zoho.eu", "www.zohoapis.eu"),
    "com.au": ("accounts.zoho.com.au", "www.zohoapis.com.au"),
    "jp": ("accounts.zoho.jp", "www.zohoapis.jp"),
    "uk": ("accounts.zoho.uk", "www.zohoapis.uk"),
    "ae": ("accounts.zoho.ae", "www.zohoapis.ae"),
    "sg": ("accounts.zoho.sg", "www.zohoapis.sg"),
    "sa": ("accounts.zoho.sa", "www.zohoapis.sa"),
    "ca": ("accounts.zohocloud.ca", "www.zohoapis.ca"),
    "com.cn": ("accounts.zoho.com.cn", "www.zohoapis.com.cn"),
}
ZOHO_DC_DOMAINS = tuple(ZOHO_DCS)
_ACCOUNTS_HOST_TO_DC = {hosts[0]: dc for dc, hosts in ZOHO_DCS.items()}


def zoho_dc_from_accounts_server(accounts_server: str) -> str:
    """'https://accounts.zoho.in' -> 'in'; anything unknown -> 'com'."""
    match = re.fullmatch(r"https://([a-z.]+)/?", (accounts_server or "").strip())
    return _ACCOUNTS_HOST_TO_DC.get(match.group(1), "com") if match else "com"


def zoho_urls(dc: str) -> tuple:
    """(token_url, books_api_base) for a data centre."""
    accounts, api = ZOHO_DCS.get(dc, ZOHO_DCS["com"])
    return f"https://{accounts}/oauth/v2/token", f"https://{api}/books/v3"


PER_PAGE = 200
MAX_PAGES = 50
MAX_JOURNAL_DETAILS = 500  # one detail call per journal; cap a single sync


def _zoho_line_amounts(line: Dict[str, Any]) -> tuple:
    """(debit, credit) for a journal line. Documented shape: amount + debit_or_credit."""
    if "debit_or_credit" in line:
        amount = float(line.get("amount") or 0)
        return (amount, 0.0) if line.get("debit_or_credit") == "debit" else (0.0, amount)
    return float(line.get("debit_amount") or 0), float(line.get("credit_amount") or 0)


@ConnectorRegistry.register
class ZohoBooksConnector(BaseConnector):
    """
    Zoho Books connector for syncing accounting data.
    
    Authentication uses OAuth 2.0 with access and refresh tokens.
    """
    
    PROVIDER_ID = "zoho_books"
    PROVIDER_NAME = "Zoho Books"
    PROVIDER_DESCRIPTION = "Sync invoices, expenses, and ledger data from Zoho Books"
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.OAUTH2
    DOCS_URL = "https://www.zoho.com/books/api/v3/"
    
    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client_id = config.credentials.get("client_id", "")
        self._client_secret = config.credentials.get("client_secret", "")
        self._refresh_token = config.credentials.get("refresh_token", "")
        self._access_token = config.credentials.get("access_token", "")
        self._organization_id = config.credentials.get("organization_id", "")
        self._client: Optional[httpx.AsyncClient] = None
        # Connections made through "Connect with Zoho" record their data centre;
        # older pasted-token connections keep the original .com hosts.
        dc = (config.credentials.get("dc") or "").strip()
        if dc:
            self._token_url, self._api_base = zoho_urls(dc)
        else:
            self._token_url, self._api_base = ZOHO_AUTH_URL, ZOHO_API_BASE
    
    async def _refresh_access_token(self) -> bool:
        """Refresh the OAuth access token using refresh token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._token_url,
                    data={
                        "refresh_token": self._refresh_token,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "grant_type": "refresh_token",
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    token = data.get("access_token", "")
                    if not token:
                        # Zoho reports some failures as HTTP 200 + {"error": ...}
                        logger.error(f"Token refresh failed: {data.get('error')}")
                        return False
                    self._access_token = token
                    if self._client:
                        self._client.headers["Authorization"] = f"Zoho-oauthtoken {token}"
                    logger.info("Zoho Books access token refreshed")
                    return True
                else:
                    logger.error(f"Token refresh failed: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create authenticated HTTP client."""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._api_base,
                headers={
                    "Authorization": f"Zoho-oauthtoken {self._access_token}",
                    "Content-Type": "application/json",
                },
                params={"organization_id": self._organization_id},
                timeout=30.0,
            )
        return self._client
    
    async def authenticate(self, _retried: bool = False) -> bool:
        """Verify authentication by testing API access."""
        try:
            # Refresh token if needed
            if not self._access_token and self._refresh_token:
                if not await self._refresh_access_token():
                    return False
            
            client = await self._get_client()
            # Books v3 has no /settings/organization; this was a 404 every time.
            response = await client.get(f"/organizations/{self._organization_id}")
            
            if response.status_code == 200:
                self._authenticated = True
                logger.info("Zoho Books authentication successful")
                return True
            elif response.status_code == 401:
                # Try refreshing token
                # Refresh once; a second 401 (wrong org or data centre) is final.
                if not _retried and await self._refresh_access_token():
                    if self._client:
                        self._client.headers["Authorization"] = f"Zoho-oauthtoken {self._access_token}"
                    return await self.authenticate(_retried=True)
                return False
            else:
                logger.warning(f"Zoho Books auth failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Zoho Books authentication error: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Quick connectivity test."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self._api_base)
                return response.status_code in [200, 401, 403]
        except Exception:
            return False
    
    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[InvoiceRecord]:
        """
        Fetch invoices from Zoho Books.
        
        Uses GET /invoices endpoint.
        """
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        invoices = []
        page = 1
        
        try:
            client = await self._get_client()
            
            while True:
                params: Dict[str, Any] = {"page": page, "per_page": 200}
                if start_date:
                    params["date_start"] = start_date.strftime("%Y-%m-%d")
                if end_date:
                    params["date_end"] = end_date.strftime("%Y-%m-%d")
                
                response = await client.get("/invoices", params=params)
                
                if response.status_code != 200:
                    logger.warning(f"Zoho Books invoices fetch failed: {response.status_code}")
                    break
                
                data = response.json()
                invoice_list = data.get("invoices", [])
                
                if not invoice_list:
                    break
                
                for inv in invoice_list:
                    invoices.append(InvoiceRecord(
                        external_id=inv.get("invoice_id", ""),
                        date=datetime.fromisoformat(inv["date"]) if inv.get("date") else datetime.now(),
                        due_date=datetime.fromisoformat(inv["due_date"]) if inv.get("due_date") else None,
                        customer_name=inv.get("customer_name"),
                        # The list endpoint returns total/balance only; sub_total,
                        # tax_total and line_items exist on GET /invoices/{id}.
                        amount=inv.get("sub_total", inv.get("total", 0)),
                        tax=inv.get("tax_total", 0),
                        total=inv.get("total", 0),
                        currency=inv.get("currency_code", "INR"),
                        status=inv.get("status", "pending"),
                        line_items=inv.get("line_items", []),
                        metadata={
                            "invoice_number": inv.get("invoice_number"),
                            "reference_number": inv.get("reference_number"),
                            "balance": inv.get("balance"),
                        },
                    ))
                
                # Check pagination
                page_context = data.get("page_context", {})
                if not page_context.get("has_more_page"):
                    break
                page += 1
            
            logger.info(f"Fetched {len(invoices)} invoices from Zoho Books")
            
        except Exception as e:
            logger.error(f"Error fetching Zoho Books invoices: {e}")
        
        return invoices
    
    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[LedgerEntry]:
        """
        Fetch journal entries / transactions from Zoho Books.
        
        Uses GET /journals and /transactions endpoints.
        """
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        entries = []
        
        try:
            client = await self._get_client()
            
            # Chart of accounts (paginated)
            accounts: Dict[str, str] = {}
            for acc in await self._paged_list(client, "/chartofaccounts", "chartofaccounts", {}):
                accounts[acc.get("account_id")] = acc.get("account_name")

            # Journals: the list has summaries only; line items come from
            # GET /journals/{id}, with `amount` + `debit_or_credit` per line.
            params: Dict[str, Any] = {}
            if start_date:
                params["date_start"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                params["date_end"] = end_date.strftime("%Y-%m-%d")
            journals = await self._paged_list(client, "/journals", "journals", params)

            for journal in journals[:MAX_JOURNAL_DETAILS]:
                lines = journal.get("line_items")
                if lines is None and journal.get("journal_id"):
                    detail = await client.get(f"/journals/{journal['journal_id']}")
                    lines = (detail.json().get("journal") or {}).get("line_items", []) if detail.status_code == 200 else []
                for line in lines or []:
                    debit, credit = _zoho_line_amounts(line)
                    entries.append(LedgerEntry(
                        external_id=f"{journal.get('journal_id')}_{line.get('line_id', '')}",
                        date=datetime.fromisoformat(journal["journal_date"]) if journal.get("journal_date") else datetime.now(),
                        account_code=line.get("account_id", ""),
                        account_name=accounts.get(line.get("account_id"), line.get("account_name", "")),
                        debit=debit,
                        credit=credit,
                        description=line.get("description") or journal.get("notes"),
                        category=line.get("account_type"),
                        metadata={
                            "journal_id": journal.get("journal_id"),
                            "reference_number": journal.get("reference_number"),
                        },
                    ))

            logger.info(f"Fetched {len(entries)} ledger entries from Zoho Books")
            
        except Exception as e:
            logger.error(f"Error fetching Zoho Books ledger: {e}")
        
        return entries
    
    async def fetch_expenses(self) -> List[Dict[str, Any]]:
        """
        Fetch expenses from Zoho Books.
        
        Useful for categorizing operating costs.
        """
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        expenses = []
        
        try:
            client = await self._get_client()
            expenses = await self._paged_list(client, "/expenses", "expenses", {})
            logger.info(f"Fetched {len(expenses)} expenses from Zoho Books")
            
        except Exception as e:
            logger.error(f"Error fetching Zoho Books expenses: {e}")
        
        return expenses
    
    async def _paged_list(self, client, path: str, key: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Every row of a Zoho list endpoint (page/per_page)."""
        rows: List[Dict[str, Any]] = []
        for page in range(1, MAX_PAGES + 1):
            res = await client.get(path, params={**params, "page": page, "per_page": PER_PAGE})
            if res.status_code != 200:
                logger.warning(f"Zoho Books {path} page {page} failed: {res.status_code}")
                break
            data = res.json()
            batch = data.get(key, []) or []
            rows.extend(batch)
            more = (data.get("page_context") or {}).get("has_more_page")
            if not batch or more is False or (more is None and len(batch) < PER_PAGE):
                break
        return rows

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
