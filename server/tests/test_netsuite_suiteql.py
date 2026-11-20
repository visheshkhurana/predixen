"""NetSuite reads invoices and journal lines through SuiteQL.

The REST record list endpoints return only `id` and `links` per item, so the
old code produced invoices of 0 dated "now" and journal entries with no lines.
https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_156414087576.html
"""

import asyncio
import json
from datetime import date

import httpx
import pytest

from server.connectors.base import ConnectorConfig
from server.connectors.netsuite import NetSuiteConnector


def _conn() -> NetSuiteConnector:
    conn = NetSuiteConnector(ConnectorConfig(provider_id="netsuite", company_id=1, credentials={
        "account_id": "1234567_SB1", "consumer_key": "ck", "consumer_secret": "cs",
        "token_id": "tk", "token_secret": "ts"}))
    conn._authenticated = True
    return conn


@pytest.fixture
def mock_http(monkeypatch):
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


def test_invoices_come_from_suiteql_with_paging(mock_http):
    today = date.today().isoformat()

    def handler(req: httpx.Request):
        assert req.method == "POST"
        assert req.url.path == "/services/rest/query/v1/suiteql"
        assert req.headers["prefer"] == "transient"
        assert req.headers["authorization"].startswith("OAuth ")
        q = json.loads(req.content)["q"]
        assert "t.type = 'CustInvc'" in q
        offset = int(req.url.params["offset"])
        if offset == 0:
            return httpx.Response(200, json={"hasMore": True, "items": [
                {"id": "1", "tranid": "INV-1", "trandate": today, "foreigntotal": "1200.50",
                 "status_name": "Invoice : Paid In Full", "customer": "Acme", "currency": "INR"}]})
        return httpx.Response(200, json={"hasMore": False, "items": [
            {"id": "2", "tranid": "INV-2", "trandate": today, "foreigntotal": "300",
             "status_name": "Invoice : Open", "customer": "Beta", "currency": "INR"}]})

    mock_http["handler"] = handler
    conn = _conn()
    invoices = asyncio.run(conn.fetch_invoices())
    assert [i.total for i in invoices] == [1200.5, 300.0]
    assert [i.status for i in invoices] == ["paid", "open"]
    assert invoices[0].currency == "INR" and invoices[0].customer_name == "Acme"
    assert len(mock_http["requests"]) == 2

    out = conn.map_to_financials(invoices=invoices)
    assert out["revenue"] == 1500.5 and out["revenue_currency"] == "INR"
    assert out["accounts_receivable"] == 300.0


def test_journal_lines_come_from_transactionline(mock_http):
    def handler(req: httpx.Request):
        q = json.loads(req.content)["q"]
        assert "transactionline" in q and "t.type = 'Journal'" in q
        return httpx.Response(200, json={"hasMore": False, "items": [
            {"id": "9", "line_id": "1", "trandate": "2026-11-02", "debitforeignamount": "500",
             "creditforeignamount": None, "account_id": "61", "account_name": "Rent"},
            {"id": "9", "line_id": "2", "trandate": "2026-11-02", "debitforeignamount": None,
             "creditforeignamount": "500", "account_id": "10", "account_name": "Bank"}]})

    mock_http["handler"] = handler
    entries = asyncio.run(_conn().fetch_ledger())
    assert [(e.account_name, e.debit, e.credit) for e in entries] == [("Rent", 500.0, 0.0), ("Bank", 0.0, 500.0)]
    assert entries[0].date.date() == date(2026, 11, 2)


def test_query_failure_is_a_warning_not_silent_zero(mock_http):
    mock_http["handler"] = lambda req: httpx.Response(400, json={"o:errorDetails": [{"detail": "Invalid search"}]})
    conn = _conn()
    assert asyncio.run(conn.fetch_invoices()) == []
    assert conn.query_errors == ["NetSuite query failed (HTTP 400)"]
