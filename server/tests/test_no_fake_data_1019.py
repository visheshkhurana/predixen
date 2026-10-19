"""No fabricated data (audit 10-19).

1. truth scan never invents runway P10/P90 as multiples of P50
2. dashboard KPI sparklines come from real FinancialRecord rows (no random)
6. metric engine stores nothing when there is no data / the query fails
7. customer_count maps to FinancialRecord.customers, not headcount
12. smart alerts honour the stored rule thresholds / enabled flags
"""
import asyncio
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.core.db import Base
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.models.truth_scan import TruthScan
from server.models.metric_definition import MetricDefinition
from server.models.metric_value import MetricValue
from server.models.raw_data_event import RawDataEvent

USER = SimpleNamespace(id=1)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Company.__table__, FinancialRecord.__table__, TruthScan.__table__,
                MetricDefinition.__table__, MetricValue.__table__, RawDataEvent.__table__],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _company(db, **meta):
    c = Company(user_id=1, name="Acme", currency="USD", metadata_json=meta or None)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _rec(db, company_id, month, **kw):
    base = dict(revenue=10000, payroll=15000, opex=0, cogs=0, other_costs=0, cash_balance=None)
    base.update(kw)
    r = FinancialRecord(company_id=company_id, period_start=date(2026, month, 1),
                        period_end=date(2026, month, 28), **base)
    db.add(r)
    db.commit()
    return r


# ---------------------------------------------------------------------------
# 1. Truth scan P10/P90
# ---------------------------------------------------------------------------

def test_truth_scan_does_not_invent_runway_band(db, monkeypatch):
    import server.truth.truth_scan as ts

    monkeypatch.setattr(ts, "get_benchmarks", lambda *a, **k: {})
    monkeypatch.setattr(ts, "compare_to_benchmarks", lambda *a, **k: {})
    q = db.query

    def query(model, *a, **k):
        if model in (ts.TransactionRecord, ts.CustomerRecord):
            return SimpleNamespace(filter=lambda *x, **y: SimpleNamespace(all=lambda: []))
        return q(model, *a, **k)

    monkeypatch.setattr(db, "query", query)
    c = _company(db)
    _rec(db, c.id, 8, revenue=9000, cash_balance=60000)
    _rec(db, c.id, 9, revenue=10000, cash_balance=50000)

    out = ts.compute_truth_scan(c, db)
    m = out["metrics"]
    assert m["runway_p50"] == pytest.approx(10.0)  # 50000 / (15000 - 10000)
    assert m["runway_p10"] is None  # was 0.7 x P50
    assert m["runway_p90"] is None  # was 1.4 x P50
    assert out["latest_period_end"] == "2026-09-28"


# ---------------------------------------------------------------------------
# 2. Dashboard KPI sparklines
# ---------------------------------------------------------------------------

def test_kpi_history_is_real_and_needs_two_points(db):
    from server.api.dashboard_kpis import get_real_history

    c = _company(db)
    _rec(db, c.id, 7, revenue=8000, cash_balance=80000)
    _rec(db, c.id, 8, revenue=9000, cash_balance=70000)
    _rec(db, c.id, 9, revenue=10000, cash_balance=None)  # cash unknown
    fin = db.query(FinancialRecord).order_by(FinancialRecord.period_end.desc()).all()

    runway = get_real_history(fin, "runway")
    # Sep has no cash -> no point (not 0); Jul/Aug are real cash / net burn.
    assert [p["date"] for p in runway] == ["2026-07", "2026-08"]
    assert runway[0]["value"] == pytest.approx(80000 / 7000)
    assert runway[1]["value"] == pytest.approx(70000 / 6000)

    bm = get_real_history(fin, "burn_multiple")
    # Aug: 6000 / ((9000 - 8000) * 12); Sep: 5000 / ((10000 - 9000) * 12)
    assert [p["value"] for p in bm] == [pytest.approx(0.5), pytest.approx(0.42)]

    # Same inputs -> same output (nothing random).
    assert get_real_history(fin, "runway") == runway

    # No record 12 months back -> no YoY points -> no sparkline at all.
    assert get_real_history(fin, "revenue_growth_yoy") == []
    # A single computable point is not a trend.
    assert get_real_history(fin[:1], "revenue") == []


def test_dashboard_kpis_module_has_no_mock_generator():
    import server.api.dashboard_kpis as dk
    assert not hasattr(dk, "generate_mock_history")
    assert not hasattr(dk, "random")


# ---------------------------------------------------------------------------
# 6 + 7. Metric engine
# ---------------------------------------------------------------------------

def _metric(db, company_id, key="signups", formula="count()"):
    m = MetricDefinition(company_id=company_id, key=key, name=key, formula=formula)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def test_formula_metric_with_no_events_stores_nothing(db):
    from server.metrics.engine import MetricEngine, MetricNoData

    c = _company(db)
    m = _metric(db, c.id)
    eng = MetricEngine(db)
    with pytest.raises(MetricNoData):
        eng.compute_metric(m, datetime(2026, 9, 1), datetime(2026, 10, 1))
    assert db.query(MetricValue).count() == 0

    res = eng.recompute_all_metrics(c.id)
    assert res["metrics_success"] == 0
    assert res["metrics_no_data"] == 1
    assert db.query(MetricValue).count() == 0


def test_formula_metric_with_events_still_stores(db):
    from server.metrics.engine import MetricEngine

    c = _company(db)
    m = _metric(db, c.id)
    db.add(RawDataEvent(company_id=c.id, connector_id="stripe", source="stripe",
                        occurred_at=datetime(2026, 9, 5), payload={"x": 1}))
    db.commit()
    mv = MetricEngine(db).compute_metric(m, datetime(2026, 9, 1), datetime(2026, 10, 1))
    assert mv.value == 1


def test_dsl_sql_error_stores_nothing(db, monkeypatch):
    import server.metrics.engine as engine_mod
    from server.metrics.engine import MetricEngine, MetricComputeError
    import server.metrics.dsl.parser as p
    import server.metrics.dsl.compiler as comp

    c = _company(db)
    m = _metric(db, c.id, key="mrr_dsl")
    m.definition = "key: mrr_dsl"
    db.commit()
    monkeypatch.setattr(p, "DSLParser", lambda d: SimpleNamespace(parse=lambda: None))
    monkeypatch.setattr(comp, "DSLCompiler", lambda s, cid: SimpleNamespace(
        compile=lambda: SimpleNamespace(sql="SELECT * FROM no_such_table", params=[], lineage={})))
    with pytest.raises(MetricComputeError):
        MetricEngine(db).compute_metric(m, datetime(2026, 9, 1), datetime(2026, 10, 1))
    assert db.query(MetricValue).count() == 0


def test_customer_count_maps_to_customers_not_headcount(db):
    from server.metrics.engine import MetricEngine

    assert MetricEngine.SNAPSHOT_KEY_MAP["customer_count"] == "customers"
    c = _company(db)
    _metric(db, c.id, key="customer_count")
    _metric(db, c.id, key="headcount")
    _rec(db, c.id, 9, headcount=12, customers=340)
    eng = MetricEngine(db)
    assert [p["value"] for p in eng.get_metric_timeseries(c.id, "customer_count")] == [340.0]
    assert [p["value"] for p in eng.get_metric_timeseries(c.id, "headcount")] == [12.0]

    # Customers not provided -> no point, never the headcount.
    c2 = _company(db)
    _metric(db, c2.id, key="customer_count")
    _rec(db, c2.id, 9, headcount=12, customers=None)
    assert eng.get_metric_timeseries(c2.id, "customer_count") == []


# ---------------------------------------------------------------------------
# 12. Smart alert rules
# ---------------------------------------------------------------------------

def _rule_store(monkeypatch, c):
    import server.api.smart_alerts as sa

    def fake_save(db_, company, key, value):
        company.metadata_json = {**(company.metadata_json or {}), key: value}

    monkeypatch.setattr(sa, "_save_key", fake_save)
    monkeypatch.setattr(sa, "get_user_company", lambda db_, cid, user: c)
    return sa


def test_rules_endpoint_shape_and_ids(db, monkeypatch):
    c = _company(db)
    sa = _rule_store(monkeypatch, c)
    out = sa.list_rules(c.id, db=db, current_user=USER)
    assert isinstance(out, dict) and isinstance(out["rules"], list)
    ids = {r["id"] for r in out["rules"]}
    assert "default-burn-spike" in ids
    # Legacy client id resolves to the default rule instead of 404.
    upd = sa.update_rule(c.id, "burn-spike", sa.AlertRuleUpdate(threshold=40), db=db, current_user=USER)
    assert upd["rule"]["id"] == "default-burn-spike"
    assert upd["rule"]["threshold"] == 40


def test_evaluate_uses_stored_thresholds_and_enabled(db, monkeypatch):
    c = _company(db)
    sa = _rule_store(monkeypatch, c)
    # Burn 10000 -> 12000 = +20%; runway 50000 / (12000 - 1000) = 4.5 mo.
    _rec(db, c.id, 8, revenue=1000, payroll=10000, cash_balance=60000)
    _rec(db, c.id, 9, revenue=1000, payroll=12000, cash_balance=50000)

    types = {a["type"] for a in sa._evaluate_alerts(c, db)}
    assert "burn_spike" in types  # 20% > default 15%
    assert "runway_warning" in types  # 4.5 < 12

    sa.update_rule(c.id, "default-burn-spike", sa.AlertRuleUpdate(threshold=25), db=db, current_user=USER)
    sa.update_rule(c.id, "default-runway-warning", sa.AlertRuleUpdate(enabled=False), db=db, current_user=USER)
    alerts = sa._evaluate_alerts(c, db)
    types = {a["type"] for a in alerts}
    assert "burn_spike" not in types  # 20% < stored 25%
    assert "runway_warning" not in types  # rule disabled
    caution = [a for a in alerts if a["type"] == "runway_caution"]
    assert caution and "18-month" in caution[0]["message"]

    sa.update_rule(c.id, "default-runway-caution", sa.AlertRuleUpdate(threshold=3), db=db, current_user=USER)
    assert "runway_caution" not in {a["type"] for a in sa._evaluate_alerts(c, db)}
