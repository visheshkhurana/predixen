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
from typing import List, Optional, Dict, Any, Tuple
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

# Tally XML encodes credit as a trailing minus (`1234.00-`) or a Cr/Dr suffix.
# float("1234.00-") raises ValueError and used to abort the whole ledger parse,
# so first sync landed zero financials even when Tally responded 200.
_SALES_VOUCHER_TYPES = {
    "sales",
    "invoice",
    "sales invoice",
    "tax invoice",
    "gst sales",
    "gst invoice",
}

_REVENUE_GROUPS = {
    "sales accounts",
    "direct incomes",
    "direct income",
}
_COGS_GROUPS = {
    "purchase accounts",
    "direct expenses",
    "direct expense",
}
_OPEX_GROUPS = {
    "indirect expenses",
    "indirect expense",
}
_CASH_GROUPS = {
    "bank accounts",
    "cash-in-hand",
    "cash in hand",
    "cash",
}


def parse_tally_amount(raw: Any) -> float:
    """Parse a Tally XML amount into a signed float.

    Credit balances are `1234.00-` or `1234.00Cr`; debits may carry `Dr`.
    Commas are thousands separators. Unparseable values return 0.0 rather
    than raising, so one bad ledger cannot wipe the rest of the sync.
    """
    if raw is None:
        return 0.0
    text = str(raw).strip()
    if not text:
        return 0.0

    sign = 1.0
    if text.startswith("(") and text.endswith(")"):
        sign = -1.0
        text = text[1:-1].strip()

    text = text.replace(",", "").replace(" ", "")
    lower = text.lower()
    if lower.endswith("cr") or text.endswith("-"):
        sign = -1.0
        text = text[:-2] if lower.endswith("cr") else text[:-1]
    elif lower.endswith("dr"):
        text = text[:-2]

    text = text.strip()
    if not text:
        return 0.0
    try:
        return sign * float(text)
    except ValueError:
        logger.warning("Unparseable Tally amount: %r", raw)
        return 0.0


def tally_xml_text(element: ET.Element, tag: str, default: str = "") -> str:
    """Read a Tally field from a child, NAME.LIST wrapper, or attribute."""
    child = element.find(tag)
    if child is not None and (child.text or "").strip():
        return child.text.strip()
    wrapped = element.find(f"{tag}.LIST")
    if wrapped is not None:
        nested = wrapped.find(tag)
        if nested is not None and (nested.text or "").strip():
            return nested.text.strip()
    attr = element.get(tag)
    if attr and str(attr).strip():
        return str(attr).strip()
    return default


def classify_tally_ledger(parent: str, name: str = "") -> Optional[str]:
    """Map a Tally ledger group to a FounderConsole financial field."""
    parent_n = (parent or "").strip().lower()
    name_n = (name or "").strip().lower()
    if parent_n in _CASH_GROUPS or name_n in {"cash", "petty cash"}:
        return "cash"
    if parent_n in _REVENUE_GROUPS:
        return "revenue"
    if parent_n in _COGS_GROUPS:
        return "cogs"
    if parent_n in _OPEX_GROUPS:
        return "opex"
    return None


def tally_reporting_window(
    now: Optional[datetime] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Tuple[datetime, datetime]:
    """Calendar month in progress, unless the caller already bounded the fetch."""
    now = now or datetime.utcnow()
    start = start_date or now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = end_date or now
    return start, end


def tally_period_flow(kind: str, opening: float, closing: float) -> float:
    """Period movement from signed Tally balances (positive=debit, negative=credit).

    CLOSINGBALANCE is a point-in-time stock, often YTD/mid-FY. Revenue/COGS/opex
    on a FinancialRecord are flows for period_start..period_end, so we take
    closing minus opening (flipped for credit-nature income).
    """
    if kind == "revenue":
        return opening - closing
    if kind in {"cogs", "opex"}:
        return closing - opening
    return 0.0


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
            start, end = tally_reporting_window()
            from_date = filters.get("from_date", start.strftime("%d-%b-%Y"))
            to_date = filters.get("to_date", end.strftime("%d-%b-%Y"))
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
                            <SVFROMDATE>{from_date}</SVFROMDATE>
                            <SVTODATE>{to_date}</SVTODATE>
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
            start, end = tally_reporting_window()
            from_date = filters.get("from_date", start.strftime("%d-%b-%Y"))
            to_date = filters.get("to_date", end.strftime("%d-%b-%Y"))
            
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
                    row: Dict[str, Any] = {
                        "name": tally_xml_text(ledger, "NAME"),
                        "parent": tally_xml_text(ledger, "PARENT"),
                        "closing_balance": parse_tally_amount(
                            tally_xml_text(ledger, "CLOSINGBALANCE", "0")
                        ),
                    }
                    opening_raw = tally_xml_text(ledger, "OPENINGBALANCE")
                    if opening_raw != "":
                        row["opening_balance"] = parse_tally_amount(opening_raw)
                    results.append(row)
            
            elif data_type == "vouchers":
                for voucher in root.findall(".//VOUCHER"):
                    results.append({
                        "date": tally_xml_text(voucher, "DATE"),
                        "number": tally_xml_text(voucher, "VOUCHERNUMBER"),
                        "type": tally_xml_text(voucher, "VOUCHERTYPENAME"),
                        "party": tally_xml_text(voucher, "PARTYLEDGERNAME"),
                        "amount": parse_tally_amount(
                            tally_xml_text(voucher, "AMOUNT", "0")
                        ),
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
        """Fetch ledger accounts for the current reporting window.

        SVFROMDATE/SVTODATE make OPENINGBALANCE the start-of-window stock and
        CLOSINGBALANCE the end-of-window stock. P&L flows are the difference;
        cash uses closing as a point-in-time balance.
        """
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        period_start, period_end = tally_reporting_window(
            start_date=start_date, end_date=end_date
        )
        entries = []
        
        try:
            client = await self._get_client()
            xml_request = self._build_xml_request("ledgers", {
                "from_date": period_start.strftime("%d-%b-%Y"),
                "to_date": period_end.strftime("%d-%b-%Y"),
            })
            response = await client.post("/", content=xml_request)
            
            if response.status_code == 200:
                ledgers = self._parse_xml_response(response.text, "ledgers")
                
                for ledger in ledgers:
                    closing = ledger.get("closing_balance", 0)
                    meta: Dict[str, Any] = {
                        "closing_balance": closing,
                        "period_start": period_start.date().isoformat(),
                        "period_end": period_end.date().isoformat(),
                    }
                    if "opening_balance" in ledger:
                        meta["opening_balance"] = ledger["opening_balance"]
                    entries.append(LedgerEntry(
                        external_id=ledger.get("name", ""),
                        date=period_end,
                        account_code=ledger.get("name", ""),
                        account_name=ledger.get("name", ""),
                        debit=closing if closing > 0 else 0,
                        credit=abs(closing) if closing < 0 else 0,
                        category=ledger.get("parent", ""),
                        metadata=meta,
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
        """Fetch sales vouchers/invoices from Tally for the reporting window."""
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        period_start, period_end = tally_reporting_window(
            start_date=start_date, end_date=end_date
        )
        invoices = []
        
        try:
            client = await self._get_client()
            xml_request = self._build_xml_request("vouchers", {
                "from_date": period_start.strftime("%d-%b-%Y"),
                "to_date": period_end.strftime("%d-%b-%Y"),
            })
            response = await client.post("/", content=xml_request)
            
            if response.status_code == 200:
                vouchers = self._parse_xml_response(response.text, "vouchers")
                
                for v in vouchers:
                    if v.get("type", "").lower() not in _SALES_VOUCHER_TYPES:
                        continue
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

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        """Turn Tally ledgers/vouchers into the fields /connectors sync persists.

        P&L fields are period *flows* (closing − opening for the fetch window).
        Unbounded CLOSINGBALANCE is a stock — often YTD at mid-FY — and is not
        written as monthly revenue/COGS/opex. Cash closing is a point-in-time
        cash_balance. period_start/period_end on the result match the window.
        """
        result: Dict[str, Any] = {
            "source_type": f"connector_{self.PROVIDER_ID}",
            "extraction_summary": f"Synced from {self.PROVIDER_NAME}",
        }

        revenue = 0.0
        cogs = 0.0
        opex = 0.0
        cash = 0.0
        saw = {"revenue": False, "cogs": False, "opex": False, "cash": False}
        period_start = None
        period_end = None

        def note_period(meta: Dict[str, Any]) -> None:
            nonlocal period_start, period_end
            if period_start is None and meta.get("period_start"):
                period_start = meta["period_start"]
            if period_end is None and meta.get("period_end"):
                period_end = meta["period_end"]

        if ledger_entries:
            for entry in ledger_entries:
                kind = classify_tally_ledger(entry.category or "", entry.account_name or "")
                if not kind:
                    continue
                meta = entry.metadata or {}
                note_period(meta)
                closing = meta.get("closing_balance")
                if closing is None:
                    closing = (entry.debit or 0.0) - (entry.credit or 0.0)

                if kind == "cash":
                    # Stock, not a flow.
                    cash += closing
                    saw["cash"] = True
                    continue

                if "opening_balance" not in meta:
                    # Lifetime/YTD close with no window opening — skip P&L.
                    continue
                flow = tally_period_flow(kind, float(meta["opening_balance"]), float(closing))
                if kind == "revenue":
                    revenue += flow
                    saw["revenue"] = True
                elif kind == "cogs":
                    cogs += flow
                    saw["cogs"] = True
                elif kind == "opex":
                    opex += flow
                    saw["opex"] = True

        if invoices:
            invoice_revenue = sum(
                inv.total or 0.0
                for inv in invoices
                if (inv.status or "").lower() in {"paid", "completed"}
            )
            if not saw["revenue"] and invoice_revenue:
                revenue = invoice_revenue
                saw["revenue"] = True
                if period_start is None and invoices:
                    dates = [inv.date for inv in invoices if inv.date]
                    if dates:
                        period_start = min(dates)
                        period_end = max(dates)

        if period_start is not None:
            result["period_start"] = period_start
        if period_end is not None:
            result["period_end"] = period_end
        if saw["revenue"]:
            result["revenue"] = revenue
        if saw["cogs"]:
            result["cogs"] = cogs
        if saw["opex"]:
            result["opex"] = opex
        if saw["cash"]:
            result["cash_balance"] = cash

        mapped = [k for k, v in saw.items() if v]
        if mapped:
            result["extraction_summary"] = (
                f"Synced from {self.PROVIDER_NAME}: " + ", ".join(mapped)
            )
        return result
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
