"""Accounting / banking connectors match the providers' published APIs.

One focused check per fix; no network (httpx.MockTransport). Each test names
the documented behaviour it pins.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import urllib.parse
from datetime import datetime

import httpx
import pytest

from server.api import connector_oauth as co
from server.connectors.base import ConnectorConfig


def _run(coro):
    return asyncio.run(coro)


def _cfg(provider, creds, settings=None):
    return ConnectorConfig(provider_id=provider, company_id=1, credentials=creds, settings=settings or {})


@pytest.fixture
def mock_http(monkeypatch):
    """Route every httpx.AsyncClient through `handler`; records requests."""
    state = {"handler": None, "requests": []}
    orig = httpx.AsyncClient

    def dispatch(request):
        state["requests"].append(request)
        return state["handler"](request)

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(dispatch)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    return state


# --- 1. Xero ----------------------------------------------------------------

def test_xero_default_scopes_are_granular(monkeypatch):
    monkeypatch.delenv("XERO_SCOPES", raising=False)
    scopes = co.PROVIDERS["xero"].default_scopes.split()
    assert "accounting.transactions.read" not in scopes
    assert "accounting.reports.read" not in scopes
    for s in ("offline_access", "accounting.settings.read", "accounting.contacts.read",
              "accounting.invoices.read", "accounting.reports.profitandloss.read",
              "accounting.reports.balancesheet.read"):
        assert s in scopes


def test_xero_scopes_env_override_still_wins(monkeypatch):
    monkeypatch.setenv("XERO_CLIENT_ID", "x")
    monkeypatch.setenv("XERO_CLIENT_SECRET", "y")
    monkeypatch.setenv("XERO_SCOPES", "offline_access accounting.transactions")
    assert co.PROVIDERS["xero"].app()["scopes"] == "offline_access accounting.transactions"


def _xero():
    from server.connectors.xero import XeroConnector
    c = XeroConnector(_cfg("xero", {"access_token": "a", "tenant_id": "t"}))
    c._authenticated = True
    return c


def test_xero_ledger_uses_bank_transactions_not_journals(mock_http):
    def handler(req):
        assert req.url.path != "/api.xro/2.0/Journals"
        if req.url.path.endswith("/Accounts"):
            return httpx.Response(200, json={"Accounts": [{"Code": "400", "Name": "Advertising", "Type": "EXPENSE"}]})
        if req.url.path.endswith("/BankTransactions"):
            assert "Date >= DateTime(2026,1,1)" in req.url.params["where"]
            return httpx.Response(200, json={"BankTransactions": [{
                "BankTransactionID": "bt1", "Type": "SPEND", "Status": "AUTHORISED",
                "Date": "/Date(1767916800000+0000)/",
                "LineItems": [{"LineItemID": "l1", "AccountCode": "400", "LineAmount": 120.5, "Description": "Ads"}],
            }, {
                "BankTransactionID": "bt2", "Type": "RECEIVE", "Status": "AUTHORISED",
                "DateString": "2026-01-10T00:00:00",
                "LineItems": [{"LineItemID": "l2", "AccountCode": "200", "LineAmount": 500}],
            }]})
        raise AssertionError(req.url)

    mock_http["handler"] = handler
    entries = _run(_xero().fetch_ledger(start_date=datetime(2026, 1, 1)))
    assert len(entries) == 2
    spend, receive = entries
    assert spend.debit == 120.5 and spend.credit == 0 and spend.category == "EXPENSE"
    assert spend.account_name == "Advertising" and spend.date.year == 2026
    assert receive.credit == 500 and receive.debit == 0


def test_xero_pnl_reads_nested_summary_rows(mock_http):
    report = {"Reports": [{"ReportName": "Profit and Loss", "ReportDate": "20 Nov 2026", "Rows": [
        {"RowType": "Header", "Cells": [{"Value": ""}, {"Value": "Nov-26"}]},
        {"RowType": "Section", "Title": "Income", "Rows": [
            {"RowType": "Row", "Cells": [{"Value": "Sales"}, {"Value": "1,000.00"}]},
            {"RowType": "SummaryRow", "Cells": [{"Value": "Total Income"}, {"Value": "1,000.00"}]},
        ]},
        {"RowType": "Section", "Title": "", "Rows": [
            {"RowType": "SummaryRow", "Cells": [{"Value": "Gross Profit"}, {"Value": "1000.00"}]}]},
        {"RowType": "Section", "Title": "Operating Expenses", "Rows": [
            {"RowType": "Row", "Cells": [{"Value": "Rent"}, {"Value": "300.00"}]},
            {"RowType": "SummaryRow", "Cells": [{"Value": "Total Operating Expenses"}, {"Value": "300.00"}]},
        ]},
        {"RowType": "Section", "Title": "", "Rows": [
            {"RowType": "SummaryRow", "Cells": [{"Value": "Net Profit"}, {"Value": "700.00"}]}]},
    ]}]}
    mock_http["handler"] = lambda req: httpx.Response(200, json=report)
    pnl = _run(_xero().get_profit_and_loss())
    assert pnl["Net Profit"] == 700.0 and pnl["Gross Profit"] == 1000.0
    assert pnl["Total Income"] == 1000.0
    assert pnl["sections"]["Income"] == {"Sales": 1000.0, "Total": 1000.0}
    assert pnl["sections"]["Operating Expenses"]["Total"] == 300.0
    assert "" not in pnl["sections"]


# --- 2. QuickBooks ------------------------------------------------------------

def _qbo():
    from server.connectors.quickbooks import QuickBooksConnector
    return QuickBooksConnector(_cfg("quickbooks", {"access_token": "a", "realm_id": "123"}))


def _sec(group, label, total, rows):
    return {"type": "Section", "group": group, "Header": {"ColData": [{"value": label}, {"value": ""}]},
            "Rows": {"Row": rows}, "Summary": {"ColData": [{"value": f"Total {label}"}, {"value": str(total)}]}}


def _data(label, amount):
    return {"type": "Data", "ColData": [{"value": label, "id": "1"}, {"value": str(amount)}]}


BALANCE_SHEET = {"Header": {"ReportName": "BalanceSheet"}, "Rows": {"Row": [
    _sec("TotalAssets", "ASSETS", 1500, [
        _sec("CurrentAssets", "Current Assets", 1500, [
            _sec("BankAccounts", "Bank Accounts", 1000, [_data("Operating", 600), _data("Reserve", 400)]),
            _sec("AR", "Accounts Receivable", 500, [_data("Client Receivables", 500)]),
        ]),
    ]),
    _sec("TotalLiabilitiesAndEquity", "LIABILITIES AND EQUITY", 1500, [
        _sec("Liabilities", "Liabilities", 300, [
            _sec("CurrentLiabilities", "Current Liabilities", 300, [
                _sec("AP", "Accounts Payable", 300, [_data("Vendors Payable", 300)]),
            ]),
        ]),
        _sec("Equity", "Equity", 1200, [_data("Retained Earnings", 1200)]),
    ]),
]}}


def test_qbo_requests_minorversion_75(mock_http):
    seen = []

    def handler(req):
        seen.append(req.url.params.get("minorversion"))
        return httpx.Response(200, json=BALANCE_SHEET)

    mock_http["handler"] = handler
    _run(_qbo().get_balance_sheet())
    _run(_qbo().get_profit_and_loss())
    assert seen and set(seen) == {"75"}


def test_qbo_balance_sheet_reads_nested_liabilities_equity_and_subtotals(mock_http):
    mock_http["handler"] = lambda req: httpx.Response(200, json=BALANCE_SHEET)
    bs = _run(_qbo().get_balance_sheet())
    assert bs["total_assets"] == 1500
    assert bs["total_liabilities"] == 300
    assert bs["total_equity"] == 1200
    assert bs["cash_and_equivalents"] == 1000
    assert bs["accounts_receivable"] == 500
    assert bs["accounts_payable"] == 300


def test_qbo_row_breakdown_recurses_into_subsections():
    section = _sec("Expenses", "Expenses", 900, [
        _data("Rent", 400),
        _sec(None, "Payroll Expenses", 500, [_data("Salaries", 450), _data("Payroll Taxes", 50)]),
    ])
    assert _qbo()._extract_row_breakdown(section) == {"Rent": 400.0, "Salaries": 450.0, "Payroll Taxes": 50.0}


# --- 3. FreshBooks -----------------------------------------------------------

def test_freshbooks_v3_status_strings_are_mapped():
    from server.connectors.freshbooks import freshbooks_invoice_status as st
    assert st({"v3_status": "paid", "status": 4}) == "paid"
    assert st({"v3_status": "autopaid"}) == "paid"
    assert st({"v3_status": "partial"}) == "partial"
    assert st({"v3_status": "draft"}) == "draft"
    assert st({"v3_status": "viewed"}) == "viewed"
    # numeric fallback: 3 is "viewed", not paid
    assert st({"status": 3}) == "viewed"
    assert st({"status": 4}) == "paid"


def test_freshbooks_refreshes_and_keeps_rotated_refresh_token(mock_http):
    from server.connectors.freshbooks import FreshBooksConnector
    conn = FreshBooksConnector(_cfg("freshbooks", {
        "access_token": "stale", "refresh_token": "r1", "client_id": "c", "client_secret": "s",
        "redirect_uri": "https://app/cb", "account_id": "acc"}))

    def handler(req):
        if req.url.path == "/auth/oauth/token":
            body = json.loads(req.content)
            assert req.method == "POST" and str(req.url).startswith("https://api.freshbooks.com/")
            assert body == {"grant_type": "refresh_token", "client_id": "c", "client_secret": "s",
                            "refresh_token": "r1", "redirect_uri": "https://app/cb"}
            return httpx.Response(200, json={"access_token": "fresh", "refresh_token": "r2"})
        if req.headers["authorization"] == "Bearer stale":
            return httpx.Response(401, json={})
        return httpx.Response(200, json={"response": {"result": {"clients": []}}})

    mock_http["handler"] = handler
    assert _run(conn.authenticate()) is True
    rotated = conn.rotated_credentials()
    assert rotated["access_token"] == "fresh" and rotated["refresh_token"] == "r2"


def test_freshbooks_token_only_credentials_still_work(mock_http):
    from server.connectors.freshbooks import FreshBooksConnector
    conn = FreshBooksConnector(_cfg("freshbooks", {"access_token": "a", "account_id": "acc"}))
    mock_http["handler"] = lambda req: httpx.Response(200, json={"response": {"result": {"clients": []}}})
    assert _run(conn.authenticate()) is True
    assert conn.rotated_credentials() is None


# --- 4. Mercury --------------------------------------------------------------

def test_mercury_transactions_use_singular_account_path(mock_http):
    from server.connectors.mercury import MercuryConnector
    conn = MercuryConnector(_cfg("mercury", {"api_key": "k"}))
    conn._authenticated = True
    paths = []

    def handler(req):
        paths.append(req.url.path)
        return httpx.Response(200, json={"transactions": [], "total": 0})

    mock_http["handler"] = handler
    _run(conn.get_transactions("acc-1"))
    assert paths == ["/api/v1/account/acc-1/transactions"]


# --- 5. Brex -----------------------------------------------------------------

def test_brex_uses_documented_host_and_paths(mock_http):
    from server.connectors.brex import BrexConnector
    conn = BrexConnector(_cfg("brex", {"api_key": "k"}))
    urls = []

    def handler(req):
        urls.append(str(req.url).split("?")[0])
        if req.url.path == "/v2/transactions/card/primary":
            return httpx.Response(200, json={"next_cursor": None, "items": [{
                "id": "t1", "card_id": "c1", "description": "AWS", "amount": {"amount": 1234, "currency": "USD"},
                "initiated_at_date": "2026-11-01", "posted_at_date": "2026-11-02",
                "merchant": {"raw_descriptor": "AWS", "mcc": "4816", "country": "USA"}}]})
        if req.url.path == "/v1/transfers":
            return httpx.Response(200, json={"next_cursor": None, "items": []})
        return httpx.Response(200, json={"items": [], "next_cursor": None})

    mock_http["handler"] = handler
    assert _run(conn.authenticate()) is True
    entries = _run(conn.fetch_ledger())
    assert urls[0] == "https://api.brex.com/v2/accounts/cash"
    assert "https://api.brex.com/v2/transactions/card/primary" in urls
    assert "https://api.brex.com/v1/transfers" in urls
    assert not any(u.endswith("/v2/accounts") for u in urls)
    (e,) = entries
    assert e.date == datetime(2026, 11, 2) and e.debit == 12.34 and e.description == "AWS"


# --- 6. Ramp -----------------------------------------------------------------

def test_ramp_defaults_to_production_and_fetches_client_credentials_token(mock_http):
    from server.connectors.ramp import RampConnector
    conn = RampConnector(_cfg("ramp", {"client_id": "cid", "client_secret": "sec"}))

    def handler(req):
        assert req.url.host == "api.ramp.com"
        if req.url.path == "/developer/v1/token":
            assert req.headers["authorization"] == "Basic " + base64.b64encode(b"cid:sec").decode()
            form = urllib.parse.parse_qs(req.content.decode())
            assert form["grant_type"] == ["client_credentials"]
            assert form["scope"] == ["transactions:read reimbursements:read bills:read"]
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 864000})
        assert req.headers["authorization"] == "Bearer tok"
        assert int(req.url.params.get("page_size", "2")) >= 2
        return httpx.Response(200, json={"data": [], "page": {"next": None}})

    mock_http["handler"] = handler
    assert _run(conn.authenticate()) is True
    assert conn.rotated_credentials()["access_token"] == "tok"


def test_ramp_sandbox_via_setting():
    from server.connectors.ramp import RampConnector
    conn = RampConnector(_cfg("ramp", {"access_token": "t"}, {"environment": "sandbox"}))
    assert conn._base_url == "https://demo-api.ramp.com/developer/v1"


def test_ramp_follows_page_next_full_url_and_parses_bill_amounts(mock_http):
    from server.connectors.ramp import RampConnector
    conn = RampConnector(_cfg("ramp", {"access_token": "t"}))
    conn._authenticated = True
    next_url = "https://api.ramp.com/developer/v1/bills?page_size=100&start=abc"
    calls = []

    def handler(req):
        calls.append(str(req.url))
        if "start=abc" in str(req.url):
            return httpx.Response(200, json={"data": [{"id": "b2", "amount": {"amount": 5000, "currency_code": "USD"},
                                                        "status": "OPEN", "issued_at": "2026-10-02T00:00:00Z"}],
                                             "page": {"next": None}})
        return httpx.Response(200, json={"data": [{"id": "b1", "amount": {"amount": 12345, "currency_code": "USD",
                                                                          "minor_unit_conversion_rate": 100},
                                                    "status": "PAID", "vendor": {"name": "Acme"},
                                                    "issued_at": "2026-10-01T00:00:00Z"}],
                                         "page": {"next": next_url}})

    mock_http["handler"] = handler
    bills = _run(conn.fetch_invoices())
    assert calls[1] == next_url
    assert [b.total for b in bills] == [123.45, 50.0]
    assert bills[0].status == "paid" and bills[0].customer_name == "Acme"
    assert bills[1].status == "pending"


# --- 7. Plaid ----------------------------------------------------------------

def test_plaid_defaults_to_production_and_drops_development():
    from server.connectors.plaid import PlaidConnector, PLAID_ENVIRONMENTS
    assert "development" not in PLAID_ENVIRONMENTS
    assert PlaidConnector(_cfg("plaid", {}))._base_url == "https://production.plaid.com"
    assert PlaidConnector(_cfg("plaid", {}, {"environment": "development"}))._base_url == "https://production.plaid.com"
    assert PlaidConnector(_cfg("plaid", {}, {"environment": "sandbox"}))._base_url == "https://sandbox.plaid.com"


def test_plaid_cash_sum_tolerates_null_balances():
    from server.connectors.plaid import PlaidConnector
    conn = PlaidConnector(_cfg("plaid", {}))
    conn._accounts = [
        {"type": "depository", "balances": {"current": None, "available": 50.0}},
        {"type": "depository", "balances": {"current": 100.0}},
        {"type": "depository", "balances": None},
        {"type": "credit", "balances": {"current": 999.0}},
    ]
    assert conn.map_to_financials()["cash_balance"] == 150.0


# --- 8. NetSuite -------------------------------------------------------------

def _rfc5849_signature(method, base_uri, params, ck_secret, tok_secret):
    enc = lambda v: urllib.parse.quote(str(v), safe="~")
    norm = "&".join(f"{k}={v}" for k, v in sorted((enc(k), enc(v)) for k, v in params))
    base = f"{method}&{enc(base_uri)}&{enc(norm)}"
    key = f"{enc(ck_secret)}&{enc(tok_secret)}"
    return base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha256).digest()).decode()


def test_netsuite_signature_excludes_query_from_uri_and_includes_params():
    from server.connectors.netsuite import NetSuiteConnector
    conn = NetSuiteConnector(_cfg("netsuite", {"account_id": "1234567_SB1", "consumer_key": "ck",
                                                "consumer_secret": "cs", "token_id": "tk", "token_secret": "ts"}))
    url = f"{conn._base_url}/account?limit=1"
    header = conn._generate_oauth_header("GET", url, {"offset": 10}, timestamp="1700000000", nonce="n1")
    sig = urllib.parse.unquote(header.split('oauth_signature="')[1].rstrip('"'))
    # RFC 5849 3.4.1.2: scheme and host lowercase, no query.
    base_uri = f"{conn._base_url}/account".replace("1234567-SB1", "1234567-sb1")
    expected = _rfc5849_signature("GET", base_uri, [
        ("limit", "1"), ("offset", "10"),
        ("oauth_consumer_key", "ck"), ("oauth_token", "tk"), ("oauth_signature_method", "HMAC-SHA256"),
        ("oauth_timestamp", "1700000000"), ("oauth_nonce", "n1"), ("oauth_version", "1.0"),
    ], "cs", "ts")
    assert sig == expected


def test_netsuite_request_signs_the_params_it_sends(mock_http):
    from server.connectors.netsuite import NetSuiteConnector
    conn = NetSuiteConnector(_cfg("netsuite", {"account_id": "123", "consumer_key": "ck",
                                                "consumer_secret": "cs", "token_id": "tk", "token_secret": "ts"}))
    captured = {}
    orig = conn._generate_oauth_header

    def spy(method, url, query_params=None, **kw):
        captured["params"] = query_params
        return orig(method, url, query_params, **kw)

    conn._generate_oauth_header = spy
    mock_http["handler"] = lambda req: httpx.Response(200, json={"items": []})
    _run(conn._make_request("GET", "/vendor", params={"limit": 100}))
    assert captured["params"] == {"limit": 100}


# --- 9. Tally ----------------------------------------------------------------

def test_tally_escapes_company_name_and_defaults_to_current_indian_fy():
    import xml.etree.ElementTree as ET
    from server.connectors.tally import TallyConnector, indian_fy_bounds
    conn = TallyConnector(_cfg("tally", {"tally_url": "http://tally.example.com:9000",
                                          "company_name": "Sharma & Sons <India>"}))
    xml = conn._build_xml_request("vouchers")
    root = ET.fromstring(xml)  # valid XML despite & and <
    assert root.find(".//SVCURRENTCOMPANY").text == "Sharma & Sons <India>"
    start, end = indian_fy_bounds()
    assert root.find(".//SVFROMDATE").text == start.strftime("%d-%b-%Y")
    assert root.find(".//SVTODATE").text == end.strftime("%d-%b-%Y")
    assert "2024" not in xml or start.year == 2024
    ET.fromstring(conn._build_xml_request("ledgers"))


def test_indian_fy_bounds():
    from server.connectors.tally import indian_fy_bounds
    assert indian_fy_bounds(datetime(2026, 11, 20)) == (datetime(2026, 4, 1), datetime(2027, 3, 31))
    assert indian_fy_bounds(datetime(2027, 2, 1)) == (datetime(2026, 4, 1), datetime(2027, 3, 31))
    assert indian_fy_bounds(datetime(2026, 4, 1)) == (datetime(2026, 4, 1), datetime(2027, 3, 31))


def test_tally_has_no_tally_so_mode():
    import inspect
    import server.connectors.tally as tally
    src = inspect.getsource(tally.TallyConnector)
    assert "api.tally.so" not in src and "use_tally_forms" not in src


# --- 10. Bench ---------------------------------------------------------------

def test_bench_reports_shutdown_and_makes_no_requests(mock_http):
    from server.connectors.bench import BenchConnector
    mock_http["handler"] = lambda req: (_ for _ in ()).throw(AssertionError("no request expected"))
    conn = BenchConnector(_cfg("bench", {"api_key": "k"}))
    assert _run(conn.authenticate()) is False
    assert "Bench has no public API" in conn.auth_error
    result = _run(conn.sync_all())
    assert result.success is False and "Bench has no public API" in result.errors[0]
    assert mock_http["requests"] == []


def test_bench_not_connectable_in_integrations_page():
    import pathlib
    src = pathlib.Path("client/src/pages/integrations.tsx").read_text()
    for name in ("CONNECTOR_BACKED_PROVIDERS", "connectorSyncIds", "connectorBackedIds"):
        line = next(l for l in src.splitlines() if name in l and "[" in l)
        assert '"bench"' not in line, name


# --- 11. Wave ----------------------------------------------------------------

def test_wave_does_not_query_transactions_and_paginates_invoices(mock_http):
    from server.connectors.wave import WaveConnector
    conn = WaveConnector(_cfg("wave", {"access_token": "t", "business_id": "biz"}))
    conn._authenticated = True
    queries = []

    def inv(i, status, paid):
        return {"node": {"id": f"i{i}", "status": status, "invoiceNumber": str(i), "invoiceDate": "2026-10-01",
                         "dueDate": "2026-10-31", "total": {"value": "100.00", "currency": {"code": "USD"}},
                         "amountDue": {"value": str(100 - paid)}, "amountPaid": {"value": str(paid)},
                         "customer": {"name": "C"}}}

    def handler(req):
        body = json.loads(req.content)
        queries.append(body)
        assert "transactions" not in body["query"]
        page = body["variables"]["page"]
        edges = [inv(1, "PAID", 100)] if page == 1 else [inv(2, "PARTIAL", 40)]
        return httpx.Response(200, json={"data": {"business": {"invoices": {
            "pageInfo": {"currentPage": page, "totalPages": 2, "totalCount": 2}, "edges": edges}}}})

    mock_http["handler"] = handler
    invoices = _run(conn.fetch_invoices())
    assert [i.external_id for i in invoices] == ["i1", "i2"]
    assert [q["variables"]["page"] for q in queries] == [1, 2]
    ledger = _run(conn.fetch_ledger())
    assert sorted(e.credit for e in ledger) == [40.0, 100.0]
    assert not hasattr(conn, "get_transactions_raw")
