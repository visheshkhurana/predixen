"""Empty/new company honesty: copilot follow-ups read as sentences, and the
strategic diagnosis never spends an AI call on a company with no figures."""
import re
from types import SimpleNamespace

from server.api.copilot import _generate_followups, _followup_money
from server.api.decisions import record_has_figures
from server.copilot.agents.cfo_agent import data_gap_question


PLACEHOLDER = re.compile(r"[{}]|\$0\b|\bNone\b|\b999\b|: ?No financial data")


def test_data_gap_question_is_a_sentence():
    q = data_gap_question(["No financial data available - upload documents or run Truth Scan"])
    assert "Can you provide:" not in q
    assert "No financial data available" not in q
    assert q.endswith("?")
    assert "Data Input" in q

    q = data_gap_question(["revenue", "gross_margin", "cash_balance", "burn_rate"])
    assert q == "Can you share your monthly revenue, gross margin and cash balance?"
    assert "_" not in q

    assert data_gap_question(["cash_balance"]) == "Can you share your cash balance?"
    assert data_gap_question([]).endswith("?")


def test_followups_skip_zero_and_sentinel_numbers():
    for _ in range(30):  # pools are shuffled
        ctx = {"metrics": {"runway_months": 999, "monthly_revenue": 0, "net_burn": 0}, "company": {"currency": "INR"}}
        for msg in ["what is my runway", "revenue trend", "hello"]:
            for f in _generate_followups(msg, ctx):
                assert not PLACEHOLDER.search(f), f


def test_followups_use_company_currency():
    ctx = {"metrics": {"monthly_revenue": 450000, "net_burn": 200000}, "company": {"currency": "INR"}}
    seen = set()
    for _ in range(60):
        seen.update(_generate_followups("revenue", ctx))
    personal = [f for f in seen if "break even" in f]
    assert personal, seen
    assert "$" not in personal[0]
    assert "₹4.5L" in personal[0]


def test_followup_money():
    assert _followup_money(45000, "USD") == "$45K"
    assert _followup_money(12_000_000, "INR") == "₹1.2Cr"
    assert _followup_money(500, None) == "$500"


def test_record_has_figures():
    assert record_has_figures(None) is False
    empty = SimpleNamespace(revenue=0, mrr=None, cogs=0, opex=0, payroll=0, other_costs=0, cash_balance=None, net_burn=None)
    assert record_has_figures(empty) is False
    assert record_has_figures(SimpleNamespace(**{**vars(empty), "cash_balance": 100.0})) is True
