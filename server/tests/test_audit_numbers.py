"""Audit 2026-10-15 P0s: fundraise window after cash-out, board memo zeros.

Uses the AlphaKids numbers from TEST-REPORT-2026-09-16 (runway 12.5 months,
low growth), where the window landed 15 months out and the memo stated
"burn $0/mo, runway 0 months".
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from server.api import doc_generator
from server.api.fundraising_readiness import _compute_readiness

RAISE_MONTHS = 4


# --- fundraise window -------------------------------------------------------

def _window(runway, growth=1.5, ltv_cac=1.0):
    metrics = {
        "runway_months": {"value": runway},
        "revenue_growth_mom": {"value": growth},
        "ltv_cac_ratio": {"value": ltv_cac},
    }
    return _compute_readiness(metrics, None, None)["raiseWindow"]


def test_alphakids_raise_closes_before_cash_out():
    w = _window(12.5)
    assert w["optimalStartMonth"] + RAISE_MONTHS <= 12.5, w
    assert "must start by month" in w["reasoning"]


def test_runway_shorter_than_a_raise_says_start_now():
    w = _window(3.0)
    assert w["optimalStartMonth"] == 0
    assert "Start now" in w["reasoning"]


@pytest.mark.parametrize("runway", [6.0, 9.9, 12.5, 18.0, 24.0, 40.0])
def test_window_never_starts_after_cash_out_minus_raise(runway):
    w = _window(runway)
    assert w["optimalStartMonth"] + RAISE_MONTHS <= max(runway, RAISE_MONTHS), (runway, w)


def test_long_runway_keeps_the_score_based_timing():
    # 40 months of runway: the score-based peak is well inside the cap.
    w = _window(40.0, growth=25.0, ltv_cac=5.0)
    assert w["optimalStartMonth"] == 1
    assert "score will peak" in w["reasoning"]


def test_unknown_runway_falls_back_to_score_timing():
    w = _compute_readiness({}, None, None)["raiseWindow"]
    assert w["optimalStartMonth"] >= 1


# --- board memo context ------------------------------------------------------

def _context(metrics, records=()):
    db = MagicMock()
    truth_scan = SimpleNamespace(outputs_json={"metrics": metrics, "data_confidence_score": 70})
    q = db.query.return_value
    q.filter.return_value.order_by.return_value.first.return_value = truth_scan
    q.filter.return_value.order_by.return_value.limit.return_value.all.side_effect = [list(records), []]
    company = SimpleNamespace(id=1, name="AlphaKids", industry="EdTech", stage="Seed", currency="USD")
    return doc_generator._gather_company_context(db, company)


def test_memo_reads_net_burn_which_the_truth_scan_writes():
    ctx = _context({"net_burn": {"value": 64980}, "runway_months": {"value": 12.5},
                    "cash_balance": {"value": 815430}})
    assert ctx["metrics"]["burn_rate"] == 64980
    prompt = doc_generator._build_section_prompt("board-memo", "Financial Summary", ctx)
    assert "$64,980/mo" in prompt
    assert "12.5 months" in prompt


def test_missing_metrics_are_not_available_not_zero():
    ctx = _context({"mrr": {"value": 3600}})
    m = ctx["metrics"]
    assert m["burn_rate"] is None and m["runway_months"] is None and m["customers"] is None
    prompt = doc_generator._build_section_prompt("board-memo", "Financial Summary", ctx)
    assert "Burn Rate: not available" in prompt
    assert "Runway: not available" in prompt
    assert "Customers: not available" in prompt
    assert "$0/mo" not in prompt and "0.0 months" not in prompt
    assert "never state, estimate or imply a figure" in prompt


def test_financial_record_fills_gaps_in_the_truth_scan():
    record = SimpleNamespace(
        period_start=None, revenue=3600, cogs=5616, opex=40000, payroll=28580,
        cash_balance=815430, mrr=3600, arr=43200, gross_margin=-56.0,
        net_burn=64980, runway_months=12.5, headcount=7, customers=120,
    )
    ctx = _context({}, records=[record])
    m = ctx["metrics"]
    assert m["burn_rate"] == 64980
    assert m["runway_months"] == 12.5
    assert m["customers"] == 120
