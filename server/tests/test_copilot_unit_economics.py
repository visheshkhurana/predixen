"""The copilot never hears the unit economics the truth scan invents.

A D2C founder entered revenue, costs, cash and headcount, plus October's
marketing spend (5,00,000) and new customers (1,200) on /profit. The truth scan
still wrote CAC 20,000 (30% of payroll as "marketing" over 8% of an assumed
150-customer book), LTV 2.9L, LTV:CAC 14.3x, NRR 108 and 150 customers. The
quick-chat data summary, the business context and the CFO agent prompt passed
those to the model as fact, so it could tell the founder "your CAC is 20K".

Now every copilot context builder reads unit economics through
server/copilot/unit_economics.company_unit_economics (record > D2C month >
real truth scan) and writes "not available (no data)" for unknowns. Metric
history (server/metrics/engine.py) uses the same rule; unknown is no point /
None, never 0. Scans saved before ``_estimated_metrics`` existed have every
unit-economics key dropped.
"""

from __future__ import annotations

import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import server.models  # noqa: F401  (register every table on Base)
from server.core.db import Base
from server.models.company import Company
from server.models.d2c_month import D2CMonth
from server.models.financial import FinancialRecord
from server.models.metric_definition import MetricDefinition
from server.models.truth_scan import TruthScan
from server.copilot.unit_economics import (
    NOT_AVAILABLE,
    company_unit_economics,
    format_unit_economics_lines,
)
from server.truth.invented_metrics import (
    INVENTED_UNIT_ECONOMICS_KEYS,
    strip_invented_from_outputs,
    strip_invented_unit_economics,
)

INVENTED_TS = {
    "monthly_revenue": 2_500_000.0,
    "cash_balance": 30_000_000.0,
    "gross_margin": 55.0,
    "net_burn": -575_000.0,
    "headcount": 14,
    "net_revenue_retention": 108,
    "customer_count": 150,
    "arpu": 16_666.67,
    "cac": 20_000.0,
    "ltv": 286_458.33,
    "ltv_cac_ratio": 14.32,
    "payback_months": 3,
    "_estimated_metrics": [
        "arpu", "customer_count", "churn_rate", "cac", "ltv",
        "ltv_cac_ratio", "payback_months", "net_revenue_retention",
    ],
}
# The same scan saved before the flag list existed.
OLD_TS = {k: v for k, v in INVENTED_TS.items() if k != "_estimated_metrics"}

INVENTED_FIGURES = ("20,000", "20000", "286,458", "286458", "14.3", "16,667", "16666", "108")


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _company(db, *, d2c_month=True, ts=INVENTED_TS, record_cac=None, name="Chai Co"):
    c = Company(user_id=1, name=name, currency="INR", industry="D2C")
    db.add(c)
    db.commit()
    db.refresh(c)
    db.add(FinancialRecord(
        company_id=c.id, period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
        revenue=2_500_000, payroll=800_000, cogs=1_125_000, cash_balance=30_000_000,
        headcount=14, cac=record_cac,
    ))
    if ts is not None:
        db.add(TruthScan(company_id=c.id, outputs_json={
            "metrics": dict(ts),
            "flags": [
                {"title": "Low LTV:CAC Ratio", "metrics_involved": ["ltv_cac_ratio", "cac", "ltv"]},
                {"title": "Low Gross Margin", "metrics_involved": ["gross_margin"]},
            ],
            "benchmark_comparisons": [
                {"metric": "net_revenue_retention", "value": 108},
                {"metric": "gross_margin", "value": 55.0},
            ],
            "data_confidence_score": 70,
        }))
    if d2c_month:
        db.add(D2CMonth(company_id=c.id, period=date(2026, 10, 1), marketing_spend=500_000, new_customers=1200))
    db.commit()
    return c


# --- old scans (no _estimated_metrics) ---------------------------------------

def test_old_scan_without_flag_list_drops_every_unit_economics_key():
    out = strip_invented_unit_economics(OLD_TS)
    for key in INVENTED_UNIT_ECONOMICS_KEYS:
        assert key not in out, key
    assert out["monthly_revenue"] == 2_500_000.0
    assert out["headcount"] == 14
    # A null list is treated the same as a missing one.
    assert "cac" not in strip_invented_unit_economics({**OLD_TS, "_estimated_metrics": None})


def test_new_scan_flag_list_still_decides():
    ts = {"cac": 900.0, "customer_count": 42, "_estimated_metrics": ["cac"]}
    assert strip_invented_unit_economics(ts) == {"customer_count": 42, "_estimated_metrics": ["cac"]}


def test_outputs_strip_drops_flags_and_benchmarks_built_on_invented_values():
    outputs = {
        "metrics": dict(OLD_TS),
        "flags": [
            {"title": "Low LTV:CAC Ratio", "metrics_involved": ["ltv_cac_ratio", "cac", "ltv"]},
            {"title": "Low Gross Margin", "metrics_involved": ["gross_margin"]},
        ],
        "benchmark_comparisons": [{"metric": "net_revenue_retention"}, {"metric": "gross_margin"}],
        "data_confidence_score": 70,
    }
    out = strip_invented_from_outputs(outputs)
    assert "cac" not in out["metrics"] and "_estimated_metrics" not in out["metrics"]
    assert [f["title"] for f in out["flags"]] == ["Low Gross Margin"]
    assert out["benchmark_comparisons"] == [{"metric": "gross_margin"}]
    assert out["data_confidence_score"] == 70
    # The stored scan is not mutated (simulations still read it).
    assert outputs["metrics"]["cac"] == 20_000.0


# --- the resolved values -----------------------------------------------------

def test_company_unit_economics_uses_d2c_cac_and_none_for_unknown(db):
    c = _company(db)
    rec = db.query(FinancialRecord).filter(FinancialRecord.company_id == c.id).first()
    ue = company_unit_economics(db, c.id, INVENTED_TS, rec)
    assert ue["cac"] == pytest.approx(416.67, abs=0.01)
    assert (ue["cac_source"], ue["cac_period"]) == ("d2c_month", "2026-10-01")
    for key in ("ltv", "ltv_cac_ratio", "customers", "arpu", "net_revenue_retention", "payback_months"):
        assert ue[key] is None, key


def test_company_unit_economics_is_scoped_to_the_company(db):
    other = _company(db, name="Other Co")             # has a D2C month
    mine = _company(db, d2c_month=False, name="Mine")  # has none
    assert company_unit_economics(db, mine.id, INVENTED_TS, None)["cac"] is None
    assert company_unit_economics(db, other.id, INVENTED_TS, None)["cac"] is not None


def test_format_lines_spell_out_unknowns():
    lines = format_unit_economics_lines({}, "INR")
    assert lines[0] == f"CAC: {NOT_AVAILABLE}"
    assert all(NOT_AVAILABLE in line for line in lines)
    lines = format_unit_economics_lines({
        "cac": 416.666, "cac_source": "d2c_month", "cac_period": "2026-10-01",
        "d2c_marketing_spend": 500_000.0, "d2c_new_customers": 1200,
        "ltv": 9_000.0, "ltv_source": "reported", "ltv_cac_ratio": 21.6, "customers": 800,
    }, "INR")
    assert lines[0] == "CAC: INR 416.67 (Oct 2026 D2C month: marketing spend / new customers = INR 500,000 / 1,200)"
    assert "LTV: INR 9,000 (founder-reported)" in lines
    assert "LTV:CAC: 21.6x" in lines
    assert "Customers: 800" in lines


# --- copilot context text ----------------------------------------------------

def _quick_chat_summary(db, company):
    from server.api.copilot import _build_data_summary
    from server.copilot.context_pack import build_context_pack
    return _build_data_summary(build_context_pack(company, db))


def _business_context_text(db, company):
    from server.copilot.business_context import build_business_context, format_context_for_prompt
    return format_context_for_prompt(build_business_context(company, db))


def _ue_lines(text):
    keys = ("cac", "ltv", "customer", "arpu", "retention", "nrr", "payback")
    return "\n".join(l for l in text.splitlines() if any(k in l.lower() for k in keys))


@pytest.mark.parametrize("ts", [INVENTED_TS, OLD_TS], ids=["flagged", "old_scan"])
@pytest.mark.parametrize("builder", [_quick_chat_summary, _business_context_text])
def test_copilot_context_has_d2c_cac_and_no_invented_values(db, ts, builder):
    c = _company(db, ts=ts)
    text = builder(db, c)
    ue_text = _ue_lines(text)
    for figure in INVENTED_FIGURES:
        assert figure not in ue_text, (figure, ue_text)
    assert "customer_count" not in text and "Low LTV:CAC" not in text
    assert "CAC: INR 416.67 (Oct 2026 D2C month" in text
    assert f"LTV: {NOT_AVAILABLE}" in text
    assert f"Customers: {NOT_AVAILABLE}" in text
    assert f"NRR: {NOT_AVAILABLE}" in text


@pytest.mark.parametrize("builder", [_quick_chat_summary, _business_context_text])
def test_copilot_context_without_d2c_says_cac_not_available(db, builder):
    c = _company(db, d2c_month=False)
    text = builder(db, c)
    assert f"CAC: {NOT_AVAILABLE}" in text
    assert "20,000" not in text and "20000" not in text


def test_business_context_keeps_founder_reported_cac(db):
    c = _company(db, record_cac=900.0)
    text = _business_context_text(db, c)
    assert "CAC: INR 900.00 (founder-reported)" in text


# --- CFO agent ---------------------------------------------------------------

def _cfo_prompt(context):
    from server.copilot.agents.base import CompanyKnowledgeBase
    from server.copilot.agents.cfo_agent import CFOAgent

    agent = CFOAgent(llm_router=object())
    captured = {}

    async def fake_llm(messages, **_kw):
        captured["prompt"] = messages[0]["content"]
        return "ok"

    agent._acall_llm = fake_llm
    ckb = CompanyKnowledgeBase(company_id=1, company_name="Chai Co", industry="D2C", stage="seed", currency="INR")
    response = asyncio.run(agent.process("What is my CAC?", ckb, context))
    return captured["prompt"], response


def test_cfo_prompt_never_uses_invented_truth_scan_unit_economics(db):
    c = _company(db)
    rec = db.query(FinancialRecord).filter(FinancialRecord.company_id == c.id).first()
    context = {
        "truth_scan": {"metrics": dict(OLD_TS)},  # even an old, unflagged scan
        "unit_economics": company_unit_economics(db, c.id, OLD_TS, rec),
    }
    prompt, response = _cfo_prompt(context)
    metrics_block = prompt.split("<user_question>")[0]
    assert "20.0K" not in metrics_block and "14.3x" not in metrics_block
    assert "CAC: INR 416.67 (Oct 2026 D2C month" in metrics_block
    assert f"LTV: {NOT_AVAILABLE}" in metrics_block
    assert f"LTV/CAC: {NOT_AVAILABLE}" in metrics_block
    fin = response.structured_output["financials"]
    assert fin["unit_economics"]["ltv"] is None
    assert fin["unit_economics"]["cac"] == pytest.approx(416.67, abs=0.01)


def test_cfo_prompt_without_unit_economics_context_says_not_available():
    prompt, _ = _cfo_prompt({"truth_scan": {"metrics": dict(INVENTED_TS)}})
    metrics_block = prompt.split("<user_question>")[0]
    assert f"CAC: {NOT_AVAILABLE}" in metrics_block
    assert "20.0K" not in metrics_block


# --- grounding guard ---------------------------------------------------------

def test_guard_does_not_count_old_scan_cac_as_verified():
    from server.copilot.trust import merge_available_metrics
    merged = merge_available_metrics({"metrics": dict(OLD_TS)}, None)
    assert "cac" not in merged and "customer_count" not in merged
    assert merged["monthly_revenue"] == 2_500_000.0


def test_guard_counts_d2c_cac_as_verified(db):
    from server.api.copilot import _guard_available_metrics
    c = _company(db)
    scan = db.query(TruthScan).filter(TruthScan.company_id == c.id).first()
    assert _guard_available_metrics(db, c.id, scan)["cac"] == pytest.approx(416.67, abs=0.01)


# --- metric history (server/metrics/engine.py) -------------------------------

def _engine_series(db, company, key):
    from server.metrics.engine import MetricEngine
    db.add(MetricDefinition(company_id=company.id, key=key, name=key))
    db.commit()
    return MetricEngine(db).get_metric_timeseries(company.id, key)


def test_metric_history_cac_uses_d2c_month_not_truth_scan(db):
    c = _company(db, ts=OLD_TS)
    points = _engine_series(db, c, "cac")
    assert [round(p["value"], 2) for p in points] == [416.67]


def test_metric_history_unknown_ltv_is_absent_not_zero(db):
    c = _company(db)
    assert _engine_series(db, c, "ltv") == []
    assert _engine_series(db, c, "ltv_cac_ratio") == []


def test_metric_history_without_d2c_has_no_cac_points(db):
    c = _company(db, d2c_month=False)
    assert _engine_series(db, c, "cac") == []


def test_snapshot_fallback_unknown_unit_economics_is_none(db):
    from server.metrics.engine import MetricEngine
    engine = MetricEngine(db)
    snapshot = {"cac": 0.0, "ltv": 0.0, "ltv_cac_ratio": 0, "net_burn": 0.0}
    with patch("server.api.realtime.get_company_kpi_metrics", return_value=snapshot):
        assert engine._get_snapshot_value(1, "cac") is None
        assert engine._get_snapshot_value(1, "ltv") is None
        assert engine._get_snapshot_value(1, "ltv_cac_ratio") is None
        assert engine._get_snapshot_value(1, "net_burn") == 0.0  # a real zero stays
    with patch("server.api.realtime.get_company_kpi_metrics", return_value={"cac": 416.67}):
        assert engine._get_snapshot_value(1, "cac") == pytest.approx(416.67)


def test_business_context_uses_company_currency_and_surplus_wording():
    from server.copilot.business_context import format_context_for_prompt
    text = format_context_for_prompt({
        "company": {"name": "Chai Point Direct", "currency": "INR"},
        "financials": {"revenue": 2_500_000, "net_burn": -575_000, "opex": 100_000},
    })
    assert "Monthly Revenue: ₹2,500,000" in text
    assert "Net Burn: none (monthly surplus of ₹575,000" in text
    assert "$" not in text
    usd = format_context_for_prompt({"company": {"currency": "USD"}, "financials": {"revenue": 40_000}})
    assert "Monthly Revenue: $40,000" in usd
