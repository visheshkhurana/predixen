"""
Tally ERP Connector

Integrates with Tally ERP via XML-over-HTTP for:
- Ledger accounts
- Vouchers and transactions
- Stock items
- Financial reports

For on-premises Tally installations, data is exchanged via XML requests.
For Tally Forms (SaaS), REST API is used.

Documentation: https://developers.tallysolutions.com/
"""

import httpx
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import xml.etree.ElementTree as ET

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


@ConnectorRegistry.register
class TallyConnector(BaseConnector):
    """
    Tally ERP connector for syncing accounting data.
    
    Supports both Tally Prime (on-prem via XML) and Tally Forms API.
    """
    
    PROVIDER_ID = "tally"
    PROVIDER_NAME = "Tally ERP"
    PROVIDER_DESCRIPTION = "Sync ledger, vouchers, and financial reports from Tally ERP"
    PROVIDER_CATEGORY = ProviderCategory.ERP
    AUTH_TYPE = AuthType.CUSTOM
    DOCS_URL = "https://developers.tallysolutions.com/"
    
    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        # For on-prem Tally
        self._tally_url = config.credentials.get("tally_url", "http://localhost:9000")
        self._company_name = config.credentials.get("company_name", "")
        # For Tally Forms API
        self._api_key = config.credentials.get("api_key", "")
        self._use_tally_forms = config.credentials.get("use_tally_forms", False)
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self._client:
            if self._use_tally_forms:
                self._client = httpx.AsyncClient(
                    base_url="https://api.tally.so",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )
            else:
                self._client = httpx.AsyncClient(
                    base_url=self._tally_url,
                    headers={"Content-Type": "application/xml"},
                    timeout=60.0,  # Tally can be slow
                )
        return self._client
    
    def _build_xml_request(self, request_type: str, filters: Dict[str, Any] = None) -> str:
        """Build XML request for Tally ERP."""
        filters = filters or {}
        
        if request_type == "ledgers":
            return f'''
            <ENVELOPE>
                <HEADER>
                    <VERSION>1</VERSION>
                    <TALLYREQUEST>Export</TALLYREQUEST>
                    <TYPE>Collection</TYPE>
                    <ID>List of Ledgers</ID>
                </HEADER>
                <BODY>
                    <DESC>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{self._company_name}</SVCURRENTCOMPANY>
                        </STATICVARIABLES>
                        <TDL>
                            <TDLMESSAGE>
                                <COLLECTION NAME="List of Ledgers">
                                    <TYPE>Ledger</TYPE>
                                    <FETCH>NAME, PARENT, OPENINGBALANCE, CLOSINGBALANCE</FETCH>
                                </COLLECTION>
                            </TDLMESSAGE>
                        </TDL>
                    </DESC>
                </BODY>
            </ENVELOPE>
            '''
        
        elif request_type == "vouchers":
            from_date = filters.get("from_date", "01-Apr-2024")
            to_date = filters.get("to_date", "31-Mar-2025")
            
            return f'''
            <ENVELOPE>
                <HEADER>
                    <VERSION>1</VERSION>
                    <TALLYREQUEST>Export</TALLYREQUEST>
                    <TYPE>Collection</TYPE>
                    <ID>Voucher Collection</ID>
                </HEADER>
                <BODY>
                    <DESC>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{self._company_name}</SVCURRENTCOMPANY>
                            <SVFROMDATE>{from_date}</SVFROMDATE>
                            <SVTODATE>{to_date}</SVTODATE>
                        </STATICVARIABLES>
                        <TDL>
                            <TDLMESSAGE>
                                <COLLECTION NAME="Voucher Collection">
                                    <TYPE>Voucher</TYPE>
                                    <FETCH>DATE, VOUCHERNUMBER, VOUCHERTYPENAME, PARTYLEDGERNAME, AMOUNT</FETCH>
                                </COLLECTION>
                            </TDLMESSAGE>
                        </TDL>
                    </DESC>
                </BODY>
            </ENVELOPE>
            '''
        
        return "<ENVELOPE></ENVELOPE>"
    
    def _parse_xml_response(self, xml_text: str, data_type: str) -> List[Dict[str, Any]]:
        """Parse XML response from Tally."""
        results = []
        try:
            root = ET.fromstring(xml_text)
            
            if data_type == "ledgers":
                for ledger in root.findall(".//LEDGER"):
                    results.append({
                        "name": ledger.findtext("NAME", ""),
                        "parent": ledger.findtext("PARENT", ""),
                        "opening_balance": float(ledger.findtext("OPENINGBALANCE", "0").replace(",", "") or 0),
                        "closing_balance": float(ledger.findtext("CLOSINGBALANCE", "0").replace(",", "") or 0),
                    })
            
            elif data_type == "vouchers":
                for voucher in root.findall(".//VOUCHER"):
                    results.append({
                        "date": voucher.findtext("DATE", ""),
                        "number": voucher.findtext("VOUCHERNUMBER", ""),
                        "type": voucher.findtext("VOUCHERTYPENAME", ""),
                        "party": voucher.findtext("PARTYLEDGERNAME", ""),
                        "amount": float(voucher.findtext("AMOUNT", "0").replace(",", "") or 0),
                    })
            
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
        
        return results
    
    async def authenticate(self) -> bool:
        """Verify connectivity to Tally."""
        try:
            client = await self._get_client()
            
            if self._use_tally_forms:
                response = await client.get("/api/me")
                if response.status_code == 200:
                    self._authenticated = True
                    return True
            else:
                # For on-prem, try a simple request
                xml_request = self._build_xml_request("ledgers")
                response = await client.post("/", content=xml_request)
                
                if response.status_code == 200 and "ENVELOPE" in response.text:
                    self._authenticated = True
                    logger.info("Tally ERP connection successful")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Tally authentication error: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Quick connectivity test."""
        try:
            client = await self._get_client()
            if self._use_tally_forms:
                response = await client.get("/")
            else:
                response = await client.get("/")
            return response.status_code in [200, 400, 401, 403]
        except Exception:
            return False
    
    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[LedgerEntry]:
        """Fetch ledger entries from Tally."""
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        entries = []
        
        try:
            client = await self._get_client()
            
            # Fetch ledger accounts
            xml_request = self._build_xml_request("ledgers")
            response = await client.post("/", content=xml_request)
            
            if response.status_code == 200:
                ledgers = self._parse_xml_response(response.text, "ledgers")
                
                for ledger in ledgers:
                    closing = ledger.get("closing_balance", 0)
                    entries.append(LedgerEntry(
                        external_id=ledger.get("name", ""),
                        date=datetime.now(),  # Ledger balance as of now
                        account_code=ledger.get("name", ""),
                        account_name=ledger.get("name", ""),
                        debit=closing if closing > 0 else 0,
                        credit=abs(closing) if closing < 0 else 0,
                        category=ledger.get("parent", ""),
                    ))
            
            logger.info(f"Fetched {len(entries)} ledger entries from Tally")
            
        except Exception as e:
            logger.error(f"Error fetching Tally ledger: {e}")
        
        return entries
    
    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[InvoiceRecord]:
        """Fetch sales vouchers/invoices from Tally."""
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        invoices = []
        
        try:
            client = await self._get_client()
            
            filters = {}
            if start_date:
                filters["from_date"] = start_date.strftime("%d-%b-%Y")
            if end_date:
                filters["to_date"] = end_date.strftime("%d-%b-%Y")
            
            xml_request = self._build_xml_request("vouchers", filters)
            response = await client.post("/", content=xml_request)
            
            if response.status_code == 200:
                vouchers = self._parse_xml_response(response.text, "vouchers")
                
                for v in vouchers:
                    if v.get("type", "").lower() in ["sales", "invoice"]:
                        try:
                            date = datetime.strptime(v.get("date", ""), "%Y%m%d")
                        except ValueError:
                            date = datetime.now()
                        
                        invoices.append(InvoiceRecord(
                            external_id=v.get("number", ""),
                            date=date,
                            customer_name=v.get("party"),
                            total=abs(v.get("amount", 0)),
                            currency="INR",
                            status="completed",
                            metadata={"voucher_type": v.get("type")},
                        ))
            
            logger.info(f"Fetched {len(invoices)} invoices from Tally")
            
        except Exception as e:
            logger.error(f"Error fetching Tally invoices: {e}")
        
        return invoices
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
