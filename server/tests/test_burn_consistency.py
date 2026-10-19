"""Burn/runway consistency: one shared rule, no invented cash/COGS, deduped alerts.

Canonical rule (server/core/burn.py):
    net_burn = payroll + marketing_expense + opex + cogs + other_costs - revenue
Negative net burn = profitable -> runway is "profitable" (None), never a capped
number and never sign-flipped.
"""
import asyncio
import copy
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.core.burn import burn_summary, gross_burn, net_burn, runway_months, runway_status
from server.core.db import Base
from server.models.company import Company
from server.models.dataset import Dataset
from server.models.financial import FinancialRecord, ImportSession
from server.models.truth_scan import TruthScan


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _rec(**kw):
    base = dict(revenue=0, cogs=0, opex=0, payroll=0, other_costs=0,
                marketing_expense=None, cash_balance=None, net_burn=None)
    base.update(kw)
    return SimpleNamespace(**base)


def test_gross_burn_includes_marketing_and_cogs():
    r = _rec(payroll=5000, marketing_expense=2000, opex=1000, cogs=1500, other_costs=500)
    assert gross_burn(r) == 10000


def test_net_burn_is_signed_and_profitable_runway_is_none():
    r = _rec(revenue=16000, payroll=5000, marketing_expense=2000, opex=1000, cogs=1500,
             other_costs=500, cash_balance=345000)
    assert net_burn(r) == -6000  # profitable: never flipped to +6000
    s = burn_summary(r)
    assert s["is_profitable"] is True
    assert s["runway_status"] == "profitable"
    assert s["runway_months"] is None  # not 36 / 57.5 / 60


def test_burning_runway_and_unknown_cash():
    r = _rec(revenue=4000, payroll=8000, marketing_expense=2000, cash_balance=60000)
    assert net_burn(r) == 6000
    assert runway_months(r.cash_balance, 6000) == pytest.approx(10.0)
    no_cash = _rec(revenue=4000, payroll=8000, marketing_expense=2000, cash_balance=None)
    s = burn_summary(no_cash)
    assert s["runway_months"] is None
    assert s["runway_status"] == "unknown"  # not 0, not a fabricated 12
    assert runway_status(0, 6000) == "finite"
    assert runway_months(0, 6000) == 0.0


def test_stored_scalar_only_without_breakdown():
    assert net_burn(_rec(net_burn=4200)) == 4200
    assert net_burn(_rec(revenue=1000, opex=3000, net_burn=99)) == 2000
    assert net_burn(None) is None
    assert burn_summary({"revenue": 0, "payroll": 1000, "cash_balance": 5000})["runway_months"] == 5


# ---------------------------------------------------------------------------
# DB fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Company.__table__, FinancialRecord.__table__, ImportSession.__table__,
                Dataset.__table__, TruthScan.__table__],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


USER = SimpleNamespace(id=1)


def _company(db):
    c = Company(user_id=1, name="Acme", currency="USD")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _import_session(db, company_id, total_expenses=9500, other=500):
    s = ImportSession(
        company_id=company_id,
        source_type="excel",
        raw_data={
            "rows": [],
            "canonical": {
                "revenue": 10000,
                "total_expenses": total_expenses,
                "expenses": {"cogs": 1000, "marketing": 2000, "payroll": 5000,
                             "operating": 1000, "other": other},
            },
        },
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _save_import(db, session_id, **kw):
    from server.api.imports import SaveRequest, save_import
    req = SaveRequest(selected_period="2026-09-01", **kw)
    return asyncio.run(save_import(session_id, req, db=db, current_user=USER))


# ---------------------------------------------------------------------------
# Imports save (items 1-3)
# ---------------------------------------------------------------------------

def test_import_save_does_not_double_count_marketing(db):
    c = _company(db)
    s = _import_session(db, c.id)
    resp = _save_import(db, s.id, cash_on_hand=100000)
    rec = db.query(FinancialRecord).filter_by(company_id=c.id).one()
    assert rec.marketing_expense == 2000
    assert rec.other_costs == 500  # "other" only, not marketing + other
    assert gross_burn(rec) == 9500  # equals the imported total
    assert net_burn(rec) == -500
    assert resp.baseline.expenseBreakdown["otherOpex"] == 500


def test_import_save_blank_cash_is_null_not_invented(db):
    c = _company(db)
    s = _import_session(db, c.id, total_expenses=12000, other=500)
    resp = _save_import(db, s.id)  # no cash_on_hand
    rec = db.query(FinancialRecord).filter_by(company_id=c.id).one()
    assert rec.cash_balance is None  # used to be burn x 12 or $2M
    assert resp.baseline.cashOnHand is None
    assert burn_summary(rec)["runway_status"] == "unknown"


def test_import_save_expense_override_above_buckets_is_kept(db):
    c = _company(db)
    s = _import_session(db, c.id)
    _save_import(db, s.id, cash_on_hand=50000, expense_override=15000)
    rec = db.query(FinancialRecord).filter_by(company_id=c.id).one()
    assert gross_burn(rec) == pytest.approx(15000)
    assert rec.other_costs == pytest.approx(15000 - 9000)
    assert net_burn(rec) == pytest.approx(5000)


def test_import_save_expense_override_below_buckets_scales_them(db):
    c = _company(db)
    s = _import_session(db, c.id)
    _save_import(db, s.id, cash_on_hand=50000, expense_override=4750)
    rec = db.query(FinancialRecord).filter_by(company_id=c.id).one()
    assert gross_burn(rec) == pytest.approx(4750)
    assert rec.marketing_expense == pytest.approx(1000)  # 2000 * 0.5


# ---------------------------------------------------------------------------
# /financials/save (item 4)
# ---------------------------------------------------------------------------

def _save_financials(db, company_id, payload):
    from server.api.ingest import NormalizedFinancials, save_financial_baseline
    baseline = NormalizedFinancials(**payload)
    return asyncio.run(save_financial_baseline(company_id, baseline, None, db=db, current_user=USER))


def test_financials_save_does_not_invent_cogs(db):
    c = _company(db)
    resp = _save_financials(db, c.id, {
        "cashOnHand": 200000, "monthlyRevenue": 20000,
        "expenseBreakdown": {"payroll": 10000, "marketing": 3000, "operating": 2000},
    })
    rec = db.query(FinancialRecord).filter_by(company_id=c.id).one()
    assert rec.cogs == 0  # used to be 35% of revenue = 7000
    assert rec.gross_margin is None  # unknown without COGS, not 65% / 100%
    assert gross_burn(rec) == 15000
    assert rec.net_burn == -5000  # signed, not clamped to 0
    assert resp["calculatedMetrics"]["netBurnRate"] == -5000
    assert resp["calculatedMetrics"]["isProfitable"] is True
    assert resp["calculatedMetrics"]["runwayMonths"] is None


def test_financials_save_total_only_is_used(db):
    c = _company(db)
    resp = _save_financials(db, c.id, {
        "cashOnHand": 90000, "monthlyRevenue": 10000, "totalMonthlyExpenses": 25000,
    })
    rec = db.query(FinancialRecord).filter_by(company_id=c.id).one()
    assert rec.cogs == 0
    assert gross_burn(rec) == 25000
    assert net_burn(rec) == 15000
    assert resp["calculatedMetrics"]["runwayMonths"] == 6.0


def test_financials_save_without_cash_does_not_crash(db):
    c = _company(db)
    resp = _save_financials(db, c.id, {"monthlyRevenue": 1000, "totalMonthlyExpenses": 5000})
    rec = db.query(FinancialRecord).filter_by(company_id=c.id).one()
    assert rec.cash_balance is None
    assert resp["calculatedMetrics"]["runwayMonths"] is None


# ---------------------------------------------------------------------------
# Smart alert dedupe (item 10)
# ---------------------------------------------------------------------------

def _alert(id_, type_="runway_warning", metric="runway_months", period="2026-09-01", **kw):
    a = {"id": id_, "type": type_, "metric": metric, "period": period, "acknowledged": False,
         "currentValue": 8.0, "message": "m", "timestamp": "t0"}
    a.update(kw)
    return a


def test_merge_alerts_dedupes_and_keeps_acknowledged():
    from server.api.smart_alerts import _merge_alerts
    stored = [_alert("a1", acknowledged=True)]
    merged, fresh = _merge_alerts([_alert("new", currentValue=7.5, timestamp="t1")], stored)
    assert fresh == []
    assert len(merged) == 1
    assert merged[0]["id"] == "a1"
    assert merged[0]["acknowledged"] is True
    assert merged[0]["currentValue"] == 7.5  # values refresh
    assert merged[0]["timestamp"] == "t0"  # first-seen kept


def test_merge_alerts_new_period_is_new_alert():
    from server.api.smart_alerts import _merge_alerts
    stored = [_alert("a1")]
    merged, fresh = _merge_alerts([_alert("a2", period="2026-10-01")], stored)
    assert [a["id"] for a in fresh] == ["a2"]
    assert [a["id"] for a in merged] == ["a2", "a1"]


def test_merge_alerts_collapses_legacy_duplicates():
    from server.api.smart_alerts import _merge_alerts
    legacy = [_alert("old1", period=None), _alert("old2", period=None, acknowledged=True)]
    for a in legacy:
        a.pop("period")
    merged, fresh = _merge_alerts([_alert("n1")], legacy)
    assert fresh == []
    assert len(merged) == 1
    assert merged[0]["id"] == "old1"
    assert merged[0]["acknowledged"] is True
    assert merged[0]["period"] == "2026-09-01"


def test_evaluate_twice_does_not_duplicate(db, monkeypatch):
    import server.api.smart_alerts as sa

    c = _company(db)
    db.add(FinancialRecord(company_id=c.id, period_start=date(2026, 9, 1), period_end=date(2026, 9, 28),
                           revenue=1000, payroll=8000, marketing_expense=2000, cash_balance=50000))
    db.commit()

    store = {}

    def fake_save(db_, company, key, value):
        store[key] = value
        company.metadata_json = {**(company.metadata_json or {}), key: value}

    monkeypatch.setattr(sa, "_save_key", fake_save)
    monkeypatch.setattr(sa, "get_user_company", lambda db_, cid, user: c)

    first = sa.evaluate_alerts(c.id, db=db, current_user=USER)
    assert first["new_alerts"] >= 1
    runway = [a for a in store["smart_alerts"] if a["type"] == "runway_warning"]
    assert len(runway) == 1
    # net burn incl. marketing = 9000 -> 50000/9000 = 5.6 months
    assert runway[0]["currentValue"] == pytest.approx(5.6)
    # Acknowledge it the way the ack endpoint does: rewrite the stored list.
    acked = copy.deepcopy(store["smart_alerts"])
    for a in acked:
        if a["type"] == "runway_warning":
            a["acknowledged"] = True
    fake_save(db, c, "smart_alerts", acked)

    second = sa.evaluate_alerts(c.id, db=db, current_user=USER)
    assert second["new_alerts"] == 0
    runway = [a for a in store["smart_alerts"] if a["type"] == "runway_warning"]
    assert len(runway) == 1
    assert runway[0]["acknowledged"] is True


# ---------------------------------------------------------------------------
# Recommendation runway delta + copilot grounding
# ---------------------------------------------------------------------------

def _sim(p50, cash):
    return {"runway": {"p50": p50}, "survival": {"18m": 100},
            "summary": {"final_cash_p50": cash, "avg_burn_p50": 0}}


def test_runway_delta_zero_when_both_sustainable():
    from server.decision.decision_engine import score_action
    action = {"id": "x", "title": "Extend Runway (Conservative)",
              "scenario_deltas": {"burn_reduction_pct": 15, "growth_uplift_pct": -2}}
    scored = score_action(action, _sim(999, 400000), _sim(999, 900000), {}, 80)
    assert scored["delta_runway_p50"] == 0.0  # was clamped to -12


def test_runway_delta_when_one_side_sustainable_is_bounded():
    from server.decision.decision_engine import score_action
    action = {"id": "x", "title": "t", "scenario_deltas": {}}
    scored = score_action(action, _sim(999, 1), _sim(30, 1), {}, 80)
    assert scored["delta_runway_p50"] == pytest.approx(90.0)  # 120 cap - 30


def test_copilot_burn_status_states_sign_and_profitable_flag():
    from server.api.copilot import _format_burn_status
    txt = _format_burn_status(burn_summary(_rec(revenue=16000, payroll=10000, cash_balance=345000)))
    assert "-6,000" in txt
    assert "is_profitable: TRUE" in txt
    assert "NOT APPLICABLE" in txt
    assert "57.5" not in txt
    burning = _format_burn_status(burn_summary(_rec(revenue=1000, payroll=7000, cash_balance=None)))
    assert "+6,000" in burning and "UNKNOWN" in burning


def test_context_pack_serializes_signed_burn_for_profitable_record():
    from server.copilot.context_pack import _serialize_financial_record
    rec = FinancialRecord(period_start=date(2026, 9, 1), period_end=date(2026, 9, 28),
                          revenue=16000, payroll=10000, opex=0, cogs=0, other_costs=0,
                          cash_balance=345000, net_burn=6000, runway_months=57.5)
    out = _serialize_financial_record(rec)
    assert out["net_burn"] == -6000
    assert out["is_profitable"] is True
    assert out["runway_months"] is None


# ---------------------------------------------------------------------------
# Realtime KPI snapshot (items 5-6) and connector sample preview (item 9)
# ---------------------------------------------------------------------------

def test_realtime_snapshot_profitable_has_no_fabricated_runway(db):
    from server.api.realtime import get_company_kpi_metrics
    c = _company(db)
    db.add(FinancialRecord(company_id=c.id, period_start=date(2026, 9, 1), period_end=date(2026, 9, 28),
                           revenue=20000, payroll=10000, marketing_expense=4000, cash_balance=100000))
    db.commit()
    m = get_company_kpi_metrics(c.id, db)
    assert m["net_burn"] == -6000  # signed, marketing included
    assert m["runway_months"] is None  # not 36 / 60
    assert m["is_profitable"] is True
    assert m["churn_rate"] is None  # not an invented 2%


def test_connector_sample_preview_persists_nothing(db, monkeypatch):
    import server.api.connectors as conn
    c = _company(db)
    saved = []
    monkeypatch.setattr(conn, "save_metadata_value", lambda *a, **k: saved.append(a))
    resp = asyncio.run(conn.test_with_sample_data(c.id, "google_sheets", db=db, current_user=USER))
    assert resp["persisted"] is False
    assert resp["verification"]["revenue"]["stored"] == 72000
    assert db.query(FinancialRecord).filter_by(company_id=c.id).count() == 0
    assert saved == []  # connector not marked connected


def test_disconnect_removes_connector_records(db, monkeypatch):
    import server.api.connectors as conn
    c = _company(db)
    for src in ("connector_google_sheets", "manual"):
        db.add(FinancialRecord(company_id=c.id, period_start=date(2026, 9, 1), period_end=date(2026, 9, 28),
                               revenue=1, source_type=src))
    db.commit()
    resp = asyncio.run(conn.disconnect_provider(c.id, "google_sheets", db=db, current_user=USER))
    assert resp["records_removed"] == 1
    left = [r.source_type for r in db.query(FinancialRecord).filter_by(company_id=c.id)]
    assert left == ["manual"]
