"""HAG-263. Tally's first sync stored nothing, and said it had succeeded.

Three defects stacked on the same path, and each one alone was enough to keep a
number off `/connectors`.

1. `_parse_xml_response` wrapped its *body* in `except ET.ParseError`. Tally
   prints a credit as `1234.00-`, `float("1234.00-")` raises ValueError, and a
   ValueError is not a ParseError -- so one credit balance escaped the function,
   the local `results` list was never returned, and the entire ledger response
   was lost while Tally answered 200. `fetch_ledger`'s own `except Exception`
   then caught it, logged it, and returned an empty list.
2. Every field was read with `findtext("NAME")`. Tally sends
   `<NAME.LIST><NAME>...</NAME></NAME.LIST>`, so on a real response every name,
   parent and balance came back empty or zero.
3. Even with a perfect parse nothing landed, because `map_to_financials` wrote
   only an `expense_breakdown` and the sync route refuses a FinancialRecord
   whose revenue, cash_balance, payroll and opex are all None. `CLOSINGBALANCE`
   is also a point-in-time *stock* and it was being written into the period
   *movement* fields, dated `datetime.now()`.

This file is the card's stated proof: a realistic Tally fixture goes in and a
real revenue figure comes out. The first two tests fail on `main` `f9ff1f6a`.

Run: .venv/bin/python -m pytest server/tests/test_tally_first_sync.py -q
"""

import asyncio
import pathlib
from datetime import datetime

import pytest

import server.connectors as connectors_pkg
from server.connectors.base import ConnectorConfig
from server.connectors.tally import (
    TallyConnector,
    classify_tally_ledger,
    parse_tally_amount,
    tally_reporting_window,
    tally_xml_text,
)
from server.connectors.registry import ConnectorRegistry

# A ledger collection as Tally actually exports it: values inside NAME.LIST
# wrappers, thousands separators, and credits as a trailing minus.
LEDGER_RESPONSE = """<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION NAME="List of Ledgers">
        <LEDGER NAME="Sales">
          <NAME.LIST><NAME>Sales</NAME></NAME.LIST>
          <PARENT>Sales Accounts</PARENT>
          <OPENINGBALANCE>1,00,000.00</OPENINGBALANCE>
          <CLOSINGBALANCE>6,00,000.00</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER NAME="Purchases">
          <NAME.LIST><NAME>Purchases</NAME></NAME.LIST>
          <PARENT>Purchase Accounts</PARENT>
          <OPENINGBALANCE>50,000.00</OPENINGBALANCE>
          <CLOSINGBALANCE>2,50,000.00</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER NAME="Rent">
          <NAME.LIST><NAME>Rent</NAME></NAME.LIST>
          <PARENT>Indirect Expenses</PARENT>
          <OPENINGBALANCE>0.00</OPENINGBALANCE>
          <CLOSINGBALANCE>1,20,000.00</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER NAME="HDFC Bank">
          <NAME.LIST><NAME>HDFC Bank</NAME></NAME.LIST>
          <PARENT>Bank Accounts</PARENT>
          <OPENINGBALANCE>8,00,000.00-</OPENINGBALANCE>
          <CLOSINGBALANCE>12,40,000.00-</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER NAME="Capital Account">
          <NAME.LIST><NAME>Capital Account</NAME></NAME.LIST>
          <PARENT>Capital Account</PARENT>
          <OPENINGBALANCE>0.00</OPENINGBALANCE>
          <CLOSINGBALANCE>5,00,000.00Cr</CLOSINGBALANCE>
        </LEDGER>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>"""


class _FakeResponse:
    status_code = 200

    def __init__(self, text):
        self.text = text


class _FakeClient:
    """Stands in for the Tally HTTP endpoint, which is a localhost service."""

    async def post(self, path, content=None):
        return _FakeResponse(LEDGER_RESPONSE)

    async def aclose(self):
        return None


def _connected_connector():
    connector = TallyConnector(
        ConnectorConfig(
            provider_id="tally",
            company_id=1,
            credentials={"tally_url": "http://localhost:9000", "company_name": "Acme"},
        )
    )
    connector._authenticated = True

    async def _client():
        return _FakeClient()

    connector._get_client = _client
    return connector


def _run_sync(connector):
    return asyncio.run(connector.sync_all())


# --------------------------------------------------------------------------
# 1. The defect, stated directly. Fails on main.
# --------------------------------------------------------------------------


def test_one_credit_balance_does_not_wipe_the_ledger_response():
    """The trailing-minus credit, which used to lose every ledger in the reply."""
    connector = _connected_connector()
    parsed = connector._parse_xml_response(LEDGER_RESPONSE, "ledgers")

    names = [row["name"] for row in parsed]
    assert names == ["Sales", "Purchases", "Rent", "HDFC Bank", "Capital Account"], (
        "a ledger with a credit balance took the rest of the response with it; "
        f"parsed only {names}"
    )


def test_a_real_number_reaches_the_financials():
    """The card's stated proof: a number comes out of a realistic fixture."""
    connector = _connected_connector()
    result = _run_sync(connector)

    assert result.success, f"sync failed: {result.errors}"
    financials = result.metadata["financials"]

    # Revenue is the movement over the window: 6,00,000 - 1,00,000.
    assert financials["revenue"] == pytest.approx(500_000.0), (
        "revenue did not reach the financials, so the sync route writes no "
        f"FinancialRecord at all. Got: {financials!r}"
    )
    assert financials["cogs"] == pytest.approx(200_000.0)
    assert financials["opex"] == pytest.approx(120_000.0)
    assert "revenue" in financials and "cash_balance" in financials

    assert result.records_synced == 5


def test_the_route_accepts_the_record_the_sync_produces():
    """The validation that made a perfect parse still store nothing."""
    connector = _connected_connector()
    financials = _run_sync(connector).metadata["financials"]

    stored = [financials.get(k) for k in ("revenue", "cash_balance", "payroll", "opex")]
    assert any(v is not None for v in stored), (
        "POST .../sync raises 'Financial record must contain at least one "
        "financial metric' when all four of these are None"
    )


# --------------------------------------------------------------------------
# 2. Stock vs flow
# --------------------------------------------------------------------------


def test_closing_balance_is_not_booked_as_period_movement():
    """A balance is not a month's flow, and it is not dated to now."""
    connector = _connected_connector()
    entries = asyncio.run(connector.fetch_ledger())

    by_name = {e.account_name: e for e in entries}
    sales = by_name["Sales"]

    # Stock is 6,00,000. Movement over the window is 5,00,000.
    assert sales.metadata["closing_balance"] == pytest.approx(600_000.0)
    assert sales.debit == pytest.approx(500_000.0), (
        "the closing balance is being written as the period movement"
    )

    start, end = tally_reporting_window()
    assert sales.date == end, "the entry is dated now instead of the window it covers"
    assert start < end


def test_the_window_is_a_complete_calendar_month():
    """truth_scan reads these as monthly figures, so a partial month is unsafe."""
    start, end = tally_reporting_window(datetime(2026, 10, 14, 9, 30))

    assert (start.year, start.month, start.day) == (2026, 9, 1)
    assert (end.year, end.month, end.day) == (2026, 9, 30)
    assert start <= end < datetime(2026, 10, 1)


def test_cash_uses_the_closing_stock_not_the_movement():
    connector = _connected_connector()
    entries = asyncio.run(connector.fetch_ledger())
    bank = {e.account_name: e for e in entries}["HDFC Bank"]

    # Both balances carry Tally's credit sign, so the movement is -4,40,000 --
    # the arithmetic is signed and stays signed. What a runway calculation
    # needs, and what the base class would have used, is the balance itself.
    assert bank.metadata["movement"] == pytest.approx(-440_000.0)
    assert bank.metadata["closing_balance"] == pytest.approx(-1_240_000.0)


# --------------------------------------------------------------------------
# 3. The parsing helpers
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1234.00-", -1234.0),
        ("1,234.00", 1234.0),
        ("1,00,000.00", 100_000.0),
        ("5000", 5000.0),
        ("(250.50)", -250.50),
        ("5,00,000.00Cr", -500_000.0),
        ("2,000.00Dr", 2000.0),
        ("", 0.0),
        ("-", 0.0),
        (None, 0.0),
        ("not a number", 0.0),
    ],
)
def test_parse_tally_amount(text, expected):
    assert parse_tally_amount(text) == pytest.approx(expected)


def test_tally_xml_text_reads_the_name_list_wrapper():
    import xml.etree.ElementTree as ET

    element = ET.fromstring("<LEDGER><NAME.LIST><NAME>Sales</NAME></NAME.LIST></LEDGER>")
    assert tally_xml_text(element, "NAME") == "Sales", (
        'findtext("NAME") returns "" on a real Tally response'
    )

    plain = ET.fromstring("<LEDGER><PARENT>Bank Accounts</PARENT></LEDGER>")
    assert tally_xml_text(plain, "PARENT") == "Bank Accounts"

    attribute = ET.fromstring('<LEDGER NAME="Cash"></LEDGER>')
    assert tally_xml_text(attribute, "NAME") == "Cash"

    assert tally_xml_text(None, "NAME") == ""


@pytest.mark.parametrize(
    "parent,expected",
    [
        ("Sales Accounts", "revenue"),
        ("Direct Incomes", "revenue"),
        ("Purchase Accounts", "cogs"),
        ("Direct Expenses", "cogs"),
        ("Indirect Expenses", "opex"),
        ("Bank Accounts", "cash"),
        ("Cash-in-Hand", "cash"),
        ("Capital Account", None),
        ("Loans (Liability)", None),
        ("", None),
        (None, None),
    ],
)
def test_classify_tally_ledger(parent, expected):
    assert classify_tally_ledger(parent) == expected


def test_an_unclassified_ledger_writes_no_zeros():
    """A figure the connector does not have is worse than no figure."""
    connector = _connected_connector()
    connector._parse_xml_response = lambda *a, **k: [
        {"name": "Capital Account", "parent": "Capital Account",
         "opening_balance": 0.0, "closing_balance": 500_000.0}
    ]

    financials = _run_sync(connector).metadata["financials"]
    assert financials.get("revenue") is None, (
        "a ledger that classified into nothing was published as a zero, which "
        "reads as a real month of no revenue"
    )


# --------------------------------------------------------------------------
# 4. Nothing else in the catalogue broke
# --------------------------------------------------------------------------


def test_the_connector_registers_and_the_catalogue_still_builds():
    """The catalogue still imports and Tally is still in it.

    This deliberately does not call `ConnectorRegistry.list_connectors()`. That
    call raises on the commit this branch is based on -- `GoogleSheetsConnector`
    does not implement the abstract `authenticate`, and `list_connectors()`
    instantiates every registered class to read its metadata, so
    `GET /connectors/providers` 500s. That is HAG-262's defect and HAG-262's
    fix (PR #90); asserting it here would make this card's test pass only in a
    tree that already carries another card's fix. What HAG-263 owns is that the
    catalogue still imports and Tally is still registered.
    """
    connectors_pkg.load_all_connectors()
    assert ConnectorRegistry.get_connector_class("tally") is TallyConnector


def test_the_test_file_is_where_the_card_says_it_is():
    assert pathlib.Path("server/tests/test_tally_first_sync.py").exists()
