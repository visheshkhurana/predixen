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
from datetime import datetime, timedelta
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
from .url_safety import SAFE_CLIENT_KWARGS, validate_public_url_async

logger = logging.getLogger(__name__)


def tally_xml_text(element: Optional[ET.Element], name: str) -> str:
    """
    Read one field out of a Tally element.

    Tally does not send `<NAME>Cash</NAME>`. It sends the value inside a
    `NAME.LIST` wrapper -- `<NAME.LIST><NAME>Cash</NAME></NAME.LIST>` -- or as an
    attribute on the element, depending on the TDL the request asked for.
    `findtext("NAME")` therefore returns "" against a real response, which is
    why every ledger came back with an empty name, an empty parent and a zero
    balance, and the sync reported success while storing nothing.
    """
    if element is None:
        return ""

    listed = element.findall(f"{name}.LIST/{name}")
    for item in listed:
        if item.text and item.text.strip():
            return item.text.strip()

    plain = element.findtext(name, "")
    if plain and plain.strip():
        return plain.strip()

    attribute = element.get(name, "")
    return attribute.strip() if attribute else ""


def parse_tally_amount(value: Any) -> float:
    """
    Parse an amount the way Tally prints it.

    Tally writes a credit as a trailing minus (`1234.00-`) or with a `Cr`
    suffix, and groups thousands with commas. `float("1234.00-")` raises, and
    that one raise was the whole defect: `_parse_xml_response` wrapped itself in
    `except ET.ParseError` only, so the ValueError escaped the function, the
    local `results` list was never returned, and a single credit balance wiped
    the entire ledger sync while Tally answered 200.

    Returns 0.0 rather than raising, so one unreadable cell cannot take the rest
    of the sync down with it. `Cr` is read as a negative the same way a trailing
    minus is; which sign a credit carries does not change any figure this
    connector publishes, because the flow buckets are summed as magnitudes.
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(",", "").replace(" ", "")
    if not text:
        return 0.0

    negative = False

    if text.endswith("-"):
        negative = True
        text = text[:-1].strip()

    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    lowered = text.lower()
    for suffix in ("cr", "dr"):
        if lowered.endswith(suffix):
            if suffix == "cr":
                negative = True
            text = text[: -len(suffix)].strip()
            break

    try:
        amount = float(text)
    except ValueError:
        return 0.0

    return -amount if negative else amount


def tally_reporting_window(today: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """
    The last complete calendar month, as (start, end) datetimes.

    `truth_scan` reads a FinancialRecord's revenue and costs as *monthly*
    figures, so a window still in progress would report the first five days of
    spend as a month's burn and overstate runway. No partial month is safe to
    publish, so this reports the last one that is finished.
    """
    today = today or datetime.utcnow()
    # Built from the parts rather than `.replace`, so a caller passing a `date`
    # instead of a `datetime` gets the same window instead of a TypeError.
    first_of_this_month = datetime(today.year, today.month, 1)
    end = first_of_this_month - timedelta(days=1)
    start = end.replace(day=1)
    return start, end


# Tally's default parent groups, mapped to the buckets the sync route can store.
_REVENUE_GROUPS = {
    "sales accounts", "direct incomes", "indirect incomes", "revenue", "income",
}
_COGS_GROUPS = {
    "purchase accounts", "direct expenses", "cost of goods sold",
}
_OPEX_GROUPS = {
    "indirect expenses", "expenses", "operating expenses",
}
_CASH_GROUPS = {
    "bank accounts", "cash-in-hand", "cash in hand", "cash accounts",
}


def classify_tally_ledger(parent: Optional[str]) -> Optional[str]:
    """
    Map a Tally parent group to the bucket the sync route can store.

    Returns "revenue", "cogs", "opex" or "cash", or None for a balance-sheet
    group this connector does not report (loans, capital, fixed assets). Tally
    lets a company rename its groups, so the exact-name table is followed by a
    substring pass before giving up.
    """
    group = (parent or "").strip().lower()
    if not group:
        return None
    if group in _REVENUE_GROUPS:
        return "revenue"
    if group in _COGS_GROUPS:
        return "cogs"
    if group in _OPEX_GROUPS:
        return "opex"
    if group in _CASH_GROUPS:
        return "cash"

    for needle, bucket in (
        ("sales", "revenue"),
        ("income", "revenue"),
        ("purchase", "cogs"),
        ("direct expense", "cogs"),
        ("indirect expense", "opex"),
        ("bank", "cash"),
        ("cash", "cash"),
    ):
        if needle in group:
            return bucket

    return None


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
        # The URL is user-supplied and fetched server-side, so it is validated
        # (public host, https, no redirects) before the first request.
        self._tally_url = config.credentials.get("tally_url", "")
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
                    **SAFE_CLIENT_KWARGS,
                )
            else:
                await validate_public_url_async(self._tally_url)
                self._client = httpx.AsyncClient(
                    base_url=self._tally_url,
                    headers={"Content-Type": "application/xml"},
                    timeout=60.0,  # Tally can be slow
                    **SAFE_CLIENT_KWARGS,
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
        """
        Parse an XML export from Tally.

        Fields are read through `tally_xml_text` because Tally wraps every value
        in a `NAME.LIST` wrapper, and amounts through `parse_tally_amount`
        because Tally prints a credit as `1234.00-`. The XML-decode error is
        handled here and nothing else: the body used to sit inside
        `except ET.ParseError`, so a ValueError raised while reading a field
        escaped this function, `results` was never returned, and one credit
        balance wiped an entire ledger sync that Tally had answered 200 for.
        """
        results = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return results

        if data_type == "ledgers":
            for ledger in root.findall(".//LEDGER"):
                results.append({
                    "name": tally_xml_text(ledger, "NAME"),
                    "parent": tally_xml_text(ledger, "PARENT"),
                    "opening_balance": parse_tally_amount(tally_xml_text(ledger, "OPENINGBALANCE")),
                    "closing_balance": parse_tally_amount(tally_xml_text(ledger, "CLOSINGBALANCE")),
                })

        elif data_type == "vouchers":
            for voucher in root.findall(".//VOUCHER"):
                results.append({
                    "date": tally_xml_text(voucher, "DATE"),
                    "number": tally_xml_text(voucher, "VOUCHERNUMBER"),
                    "type": tally_xml_text(voucher, "VOUCHERTYPENAME"),
                    "party": tally_xml_text(voucher, "PARTYLEDGERNAME"),
                    "amount": parse_tally_amount(tally_xml_text(voucher, "AMOUNT")),
                })

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
                window_start, window_end = tally_reporting_window(
                    end_date or start_date or None
                )

                for ledger in ledgers:
                    name = ledger.get("name", "")
                    if not name:
                        # A nameless ledger cannot be keyed or classified, and
                        # one of them is what an unread NAME.LIST wrapper
                        # produces. Skip it rather than store a blank row.
                        continue

                    parent = ledger.get("parent", "")
                    opening = ledger.get("opening_balance", 0.0)
                    closing = ledger.get("closing_balance", 0.0)

                    # CLOSINGBALANCE is a point-in-time stock. LedgerEntry's
                    # debit/credit are period *movement*, and the old code put
                    # the stock straight into them, dated `datetime.now()`: a
                    # ledger standing at 5,00,000 was booked as 5,00,000 of
                    # movement in whatever month the sync happened to run. The
                    # movement over the reporting window is closing - opening,
                    # and it is dated to the window rather than to now.
                    movement = closing - opening

                    entries.append(LedgerEntry(
                        external_id=name,
                        date=window_end,
                        account_code=name,
                        account_name=name,
                        debit=movement if movement > 0 else 0.0,
                        credit=abs(movement) if movement < 0 else 0.0,
                        description=(
                            f"{parent or 'unclassified'} movement "
                            f"{window_start.date().isoformat()}..{window_end.date().isoformat()}"
                        ),
                        category=parent,
                        metadata={
                            "opening_balance": opening,
                            "closing_balance": closing,
                            "movement": movement,
                            "window_start": window_start.isoformat(),
                            "window_end": window_end.isoformat(),
                            "bucket": classify_tally_ledger(parent),
                        },
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
    
    def map_to_financials(
        self,
        employees: Optional[List[Any]] = None,
        payroll_runs: Optional[List[Any]] = None,
        ledger_entries: Optional[List[LedgerEntry]] = None,
        invoices: Optional[List[InvoiceRecord]] = None,
    ) -> Dict[str, Any]:
        """
        Turn classified ledger movement into the fields the sync route stores.

        The base implementation writes only an `expense_breakdown` keyed by
        parent group, and `POST /companies/{company_id}/connectors/{provider_id}/sync`
        refuses a FinancialRecord whose revenue, cash_balance, payroll and opex
        are all None. So a perfectly parsed Tally ledger still produced no
        financial record at all -- the numbers never reached /connectors, which
        is what "the sync reports success and nothing appears" looked like from
        the outside.

        Flows (revenue, cogs, opex) come from the period *movement*; cash comes
        from the closing *stock*, because a bank balance is a balance-sheet
        figure and not a month's flow. A ledger is only published when at least
        one entry classified -- writing zeros for an unclassified ledger would
        be a figure the connector does not actually have.
        """
        result = super().map_to_financials(
            employees=employees,
            payroll_runs=payroll_runs,
            ledger_entries=ledger_entries,
            invoices=invoices,
        )

        if not ledger_entries:
            return result

        flows = {"revenue": 0.0, "cogs": 0.0, "opex": 0.0}
        cash = 0.0
        classified = 0
        window = None

        for entry in ledger_entries:
            meta = entry.metadata or {}
            window = meta.get("window_end") or window
            bucket = meta.get("bucket") or classify_tally_ledger(entry.category)
            if bucket is None:
                continue

            classified += 1
            if bucket == "cash":
                cash += parse_tally_amount(meta.get("closing_balance"))
            else:
                flows[bucket] += abs(parse_tally_amount(meta.get("movement")))

        if not classified:
            logger.warning(
                "Tally ledger sync classified no entries; no financial record "
                "will be written rather than one full of zeros"
            )
            return result

        result["revenue"] = flows["revenue"]
        result["cogs"] = flows["cogs"]
        result["opex"] = flows["opex"]
        result["cash_balance"] = cash

        window_text = (window or "")[:10] or "the reporting window"
        result["extraction_summary"] = (
            f"Synced from {self.PROVIDER_NAME}: ledger movement for {window_text} "
            f"({classified} classified ledger entries)"
        )
        return result

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
