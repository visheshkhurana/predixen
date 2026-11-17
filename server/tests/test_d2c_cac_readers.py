"""Every reader of CAC / LTV uses one rule, and none shows invented values.

A D2C founder entered October's marketing spend (5,00,000) and new customers
(1,200) on /profit, which showed CAC 417. /overview still said CAC "N/A -- needs
marketing spend & new customers", because /metrics/computed only read the
FinancialRecord and the (invented, stripped) truth-scan CAC. Meanwhile the board
export and the realtime KPI feed still read the truth scan directly, so a board
deck could print the invented CAC 20,000 / LTV 2.9L / LTV:CAC 14.3x.

Rule (server/truth/invented_metrics.resolve_unit_economics):
  CAC: FinancialRecord > newest D2C month (spend / new customers) > real truth scan
  LTV: FinancialRecord > real truth scan (never derived from one D2C month)
"""

from __future__ import annotations

import asyncio
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import server.models  # noqa: F401  (register every table on Base)
from server.core.db import Base
from server.models.company import Company
from server.models.d2c_month import D2CMonth
from server.models.financial import FinancialRecord
from server.models.truth_scan import TruthScan
from server.services.d2c_months import d2c_cac_by_month, latest_d2c_cac
from server.truth.invented_metrics import resolve_unit_economics

INVENTED_TS = {
    "monthly_revenue": 2_500_000.0,
    "gross_margin": 55.0,
    "churn_rate": 3.2,
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

USER = SimpleNamespace(id=1, email="founder@example.com")


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _company(db, *, d2c_month=True, record_cac=None, ts=INVENTED_TS):
    c = Company(user_id=1, name="Chai Co", currency="INR", industry="D2C")
    db.add(c)
    db.commit()
    db.refresh(c)
    db.add(FinancialRecord(
        company_id=c.id, period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
        revenue=2_500_000, payroll=800_000, cogs=1_125_000, cash_balance=30_000_000,
        cac=record_cac,
    ))
    if ts is not None:
        db.add(TruthScan(company_id=c.id, outputs_json={"metrics": dict(ts), "data_confidence_score": 70}))
    if d2c_month:
        # Older complete month, newest complete month, and a newer month without
        # new customers (skipped, not guessed).
        db.add(D2CMonth(company_id=c.id, period=date(2026, 9, 1), marketing_spend=300_000, new_customers=600))
        db.add(D2CMonth(company_id=c.id, period=date(2026, 10, 1), marketing_spend=500_000, new_customers=1200))
        db.add(D2CMonth(company_id=c.id, period=date(2026, 11, 1), marketing_spend=200_000, new_customers=None))
    db.commit()
    return c


# --- D2C month CAC -----------------------------------------------------------

def test_latest_d2c_cac_uses_newest_complete_month(db):
    c = _company(db)
    got = latest_d2c_cac(db, c.id)
    assert got["period"] == "2026-10-01"
    assert got["cac"] == pytest.approx(416.67, abs=0.01)
    by_month = d2c_cac_by_month(db, c.id)
    assert set(by_month) == {date(2026, 9, 1), date(2026, 10, 1)}
    assert by_month[date(2026, 9, 1)]["cac"] == pytest.approx(500.0)


def test_latest_d2c_cac_none_without_months(db):
    c = _company(db, d2c_month=False)
    assert latest_d2c_cac(db, c.id) is None
    assert d2c_cac_by_month(db, c.id) == {}


# --- the shared rule ---------------------------------------------------------

def test_resolve_order_record_then_d2c_then_real_truth_scan():
    d2c = {"cac": 416.67, "period": "2026-10-01"}
    rec = SimpleNamespace(cac=900.0, ltv=None, ltv_cac_ratio=None)
    assert resolve_unit_economics(INVENTED_TS, rec, d2c)["cac_source"] == "reported"
    out = resolve_unit_economics(INVENTED_TS, None, d2c)
    assert (out["cac"], out["cac_source"], out["cac_period"]) == (416.67, "d2c_month", "2026-10-01")
    # LTV / ratio stay unknown: invented values are dropped, nothing derived.
    assert out["ltv"] == 0 and out["ltv_cac_ratio"] == 0 and out["ltv_source"] is None
    real_ts = {"cac": 800.0, "ltv": 4_000.0, "_estimated_metrics": []}
    out = resolve_unit_economics(real_ts, None, None)
    assert (out["cac"], out["cac_source"], out["ltv"], out["ltv_cac_ratio"]) == (800.0, "truth_scan", 4_000.0, 5.0)
    assert resolve_unit_economics(INVENTED_TS, None, None)["cac"] == 0


# --- /metrics/computed -------------------------------------------------------

def _computed(db, company_id):
    from server.api.ingest import get_computed_metrics
    return asyncio.run(get_computed_metrics(company_id, db=db, current_user=USER))


def test_computed_uses_d2c_month_cac(db):
    c = _company(db)
    out = _computed(db, c.id)
    assert out["cac"] == pytest.approx(416.67, abs=0.01)
    assert out["cacSource"] == "d2c_month"
    assert out["cacPeriod"] == "2026-10-01"
    assert out["ltv"] == 0
    assert out["ltvCacRatio"] == 0


def test_computed_without_d2c_months_cac_unknown(db):
    c = _company(db, d2c_month=False)
    out = _computed(db, c.id)
    assert out["cac"] == 0
    assert out["cacSource"] is None


def test_computed_record_cac_beats_d2c_month(db):
    c = _company(db, record_cac=750.0)
    out = _computed(db, c.id)
    assert out["cac"] == 750.0
    assert out["cacSource"] == "reported"


# --- board export ------------------------------------------------------------

def test_board_export_data_never_has_invented_unit_economics(db):
    from server.api.board_export import get_board_export_data
    c = _company(db)
    data = get_board_export_data(c.id, db=db, current_user=USER)
    m = data["metrics"]
    assert m["cac"] == pytest.approx(416.67, abs=0.01)
    assert m["cac_source"] == "d2c_month"
    assert m["ltv"] is None and m["ltv_cac_ratio"] is None
    assert m["ndr"] is None and m["customers"] is None
    raw = data["truth_scan_raw"]
    for key in ("cac", "ltv", "ltv_cac_ratio", "customer_count", "net_revenue_retention", "arpu"):
        assert key not in raw, key


def test_board_export_no_d2c_omits_cac(db):
    from server.api.board_export import get_board_export_data
    c = _company(db, d2c_month=False)
    m = get_board_export_data(c.id, db=db, current_user=USER)["metrics"]
    assert m["cac"] is None and m["ltv"] is None and m["ltv_cac_ratio"] is None


def _all_text(db, company):
    from server.api.board_export import (
        TEMPLATES, _build_narrative_prompt, _gather_company_data, _generate_fallback_narrative,
    )
    data = _gather_company_data(db, company)
    texts = []
    for tid, tpl in TEMPLATES.items():
        for section in tpl["sections"]:
            texts.append(_build_narrative_prompt(tid, section, data))
            texts.append(_generate_fallback_narrative(section, data))
    return "\n".join(texts)


@pytest.mark.parametrize("d2c", [True, False])
def test_board_narratives_never_print_invented_or_zero_unit_economics(db, d2c):
    text = _all_text(db, _company(db, d2c_month=d2c))
    for invented in ("20,000", "286,458", "14.3x", "108%", "150 customers"):
        assert invented not in text, invented
    for zero in ("LTV/CAC: 0.0x", "LTV/CAC ratio stands at 0.0x", "CAC: $0", "LTV: $0",
                 "NDR: 0%", "with 0 customers"):
        assert zero not in text, zero
    assert "LTV: not available" in text
    if d2c:
        assert "CAC: ₹417 (marketing spend / new customers, 2026-10)" in text
        assert "CAC is ₹417" in text
    else:
        assert "CAC: not available" in text
        assert "CAC, LTV, LTV/CAC not available yet" in text


# --- realtime ----------------------------------------------------------------

def test_realtime_snapshot_uses_rule(db):
    from server.api.realtime import get_company_kpi_metrics
    c = _company(db)
    m = get_company_kpi_metrics(c.id, db)
    assert m["cac"] == pytest.approx(416.67, abs=0.01)
    assert m["ltv"] == 0 and m["ltv_cac_ratio"] == 0
    c2 = _company(db, d2c_month=False)
    m2 = get_company_kpi_metrics(c2.id, db)
    assert m2["cac"] == 0 and m2["ltv"] == 0 and m2["ltv_cac_ratio"] == 0


def test_realtime_history_uses_same_month_d2c_cac(db):
    from server.api.realtime import get_kpi_history
    c = _company(db)
    db.add(FinancialRecord(company_id=c.id, period_start=date(2026, 9, 1), period_end=date(2026, 9, 30),
                           revenue=2_000_000, payroll=800_000))
    db.add(FinancialRecord(company_id=c.id, period_start=date(2026, 8, 1), period_end=date(2026, 8, 31),
                           revenue=1_800_000, payroll=800_000))
    db.commit()
    hist = get_kpi_history(c.id, months=12, db=db, current_user=USER)["data"]
    cacs = [round(h["cac"], 2) for h in hist]
    assert cacs == [0, 500.0, 416.67]  # Aug has no D2C month -> unknown, not 20,000
    assert all(h["ltv"] == 0 and h["ltv_cac_ratio"] == 0 for h in hist)
