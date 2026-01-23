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
    
    async def _refresh_access_token(self) -> bool:
        """Refresh the OAuth access token using refresh token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ZOHO_AUTH_URL,
                    data={
                        "refresh_token": self._refresh_token,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "grant_type": "refresh_token",
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._access_token = data.get("access_token", "")
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
                base_url=ZOHO_API_BASE,
                headers={
                    "Authorization": f"Zoho-oauthtoken {self._access_token}",
                    "Content-Type": "application/json",
                },
                params={"organization_id": self._organization_id},
                timeout=30.0,
            )
        return self._client
    
    async def authenticate(self) -> bool:
        """Verify authentication by testing API access."""
        try:
            # Refresh token if needed
            if not self._access_token and self._refresh_token:
                if not await self._refresh_access_token():
                    return False
            
            client = await self._get_client()
            response = await client.get("/settings/organization")
            
            if response.status_code == 200:
                self._authenticated = True
                logger.info("Zoho Books authentication successful")
                return True
            elif response.status_code == 401:
                # Try refreshing token
                if await self._refresh_access_token():
                    # Update client headers
                    if self._client:
                        self._client.headers["Authorization"] = f"Zoho-oauthtoken {self._access_token}"
                    return await self.authenticate()
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
                response = await client.get(ZOHO_API_BASE)
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
                        amount=inv.get("sub_total", 0),
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
            
            # Fetch chart of accounts first
            accounts_response = await client.get("/chartofaccounts")
            accounts = {}
            if accounts_response.status_code == 200:
                for acc in accounts_response.json().get("chartofaccounts", []):
                    accounts[acc.get("account_id")] = acc.get("account_name")
            
            # Fetch journal entries
            params: Dict[str, Any] = {"per_page": 200}
            if start_date:
                params["date_start"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                params["date_end"] = end_date.strftime("%Y-%m-%d")
            
            response = await client.get("/journals", params=params)
            
            if response.status_code == 200:
                data = response.json()
                journals = data.get("journals", [])
                
                for journal in journals:
                    # Each journal can have multiple line items
                    for line in journal.get("line_items", []):
                        entries.append(LedgerEntry(
                            external_id=f"{journal.get('journal_id')}_{line.get('line_id', '')}",
                            date=datetime.fromisoformat(journal["journal_date"]) if journal.get("journal_date") else datetime.now(),
                            account_code=line.get("account_id", ""),
                            account_name=accounts.get(line.get("account_id"), line.get("account_name", "")),
                            debit=line.get("debit_amount", 0),
                            credit=line.get("credit_amount", 0),
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
            response = await client.get("/expenses", params={"per_page": 200})
            
            if response.status_code == 200:
                expenses = response.json().get("expenses", [])
                logger.info(f"Fetched {len(expenses)} expenses from Zoho Books")
            
        except Exception as e:
            logger.error(f"Error fetching Zoho Books expenses: {e}")
        
        return expenses
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
