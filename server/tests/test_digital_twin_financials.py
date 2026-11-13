"""Digital Twin must show entered cash, burn and runway (audit P1-6).

A pre-seed company is created with the stage sample on CompanyState
(cash 150_000, burn 12_000, runway 12.5). Onboarding then stores the
founder's numbers on FinancialRecord — the same row GET /metrics/computed
and /overview read. The twin used to keep the sample unless the entered
figure was more than 5x larger.
"""
import asyncio
import json
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.api.companies import _get_stage_sample_financials
from server.core.db import Base
from server.models.company import Company
from server.models.company_state import CompanyState
from server.models.financial import FinancialRecord
from server.models.truth_scan import TruthScan
from server.models.twin_event import TwinEvent

CASH = 600_000
BURN = 55_000
RUNWAY = round(CASH / BURN, 1)  # 10.9

# Pre-seed creation seed. 150_000 / 12_000 = 12.5 months.
FALLBACK_CASH = 150_000
FALLBACK_BURN = 12_000
FALLBACK_RUNWAY = 12.5


@pytest.fixture
def db(monkeypatch):
    import server.core.cache as cache

    monkeypatch.setattr(cache, "cache_get", lambda key: None)
    monkeypatch.setattr(cache, "cache_set", lambda *a, **k: False)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__,
            CompanyState.__table__,
            FinancialRecord.__table__,
            TruthScan.__table__,
            TwinEvent.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _company_with_sample_state(db, stage="pre_seed"):
    company = Company(user_id=1, name="Northwind", currency="USD", stage=stage)
    db.add(company)
    db.flush()

    sample = _get_stage_sample_financials(stage)
    db.add(CompanyState(
        company_id=company.id,
        environment="user",
        state_json=json.dumps(sample),
        snapshot_id="stage-sample",
        cash_balance=sample["cashBalance"],
        monthly_burn=sample["monthlyBurn"],
        revenue_monthly=sample["revenueMonthly"],
        revenue_growth_rate=str(sample["revenueGrowthRate"]),
        expenses_monthly=sample["expensesMonthly"],
    ))
    db.commit()
    db.refresh(company)
    return company


def _entered_record(db, company_id, cash=CASH, burn=BURN):
    """Same shape manual_baseline writes: breakdown plus stored net burn.

    source_type is left NULL, which is what onboarding actually stores.
    """
    record = FinancialRecord(
        company_id=company_id,
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 20),
        revenue=0,
        mrr=0,
        cogs=0,
        opex=0,
        payroll=0,
        other_costs=burn,
        marketing_expense=0,
        cash_balance=cash,
        net_burn=burn,
        source_type=None,
    )
    db.add(record)
    db.commit()
    return record


def _assert_no_fallback(state):
    fin = state["financials"]
    derived = state["derived_metrics"]
    assert fin["cash_balance"] != FALLBACK_CASH
    assert fin["monthly_burn"] != FALLBACK_BURN
    assert derived["runway_months"] != FALLBACK_RUNWAY
    blob = json.dumps({"financials": fin, "derived_metrics": derived})
    assert str(FALLBACK_CASH) not in blob
    assert str(FALLBACK_BURN) not in blob
    assert str(FALLBACK_RUNWAY) not in blob


def test_twin_uses_entered_financials_not_stage_sample(db):
    from server.api.ingest import get_computed_metrics
    from server.services.digital_twin import get_twin_state

    company = _company_with_sample_state(db)
    _entered_record(db, company.id)

    state = get_twin_state(db, company.id)
    fin = state["financials"]
    derived = state["derived_metrics"]

    assert fin["cash_balance"] == CASH
    assert fin["monthly_burn"] == BURN
    assert derived["runway_months"] == pytest.approx(RUNWAY, abs=0.05)
    assert derived["runway_months"] == pytest.approx(10.9, abs=0.05)
    assert fin["assumption_fields"] == []
    _assert_no_fallback(state)

    overview = asyncio.run(get_computed_metrics(
        company.id, db, SimpleNamespace(id=1),
    ))
    assert fin["cash_balance"] == overview["cashOnHand"]
    assert fin["monthly_burn"] == overview["netBurn"]
    assert derived["runway_months"] == pytest.approx(round(overview["runway"], 1), abs=0.05)


def test_twin_truth_scan_within_5x_replaces_stage_sample(db):
    """The old gate kept CompanyState unless truth-scan cash/burn was >5x larger.

    600_000 is only 4x the 150_000 seed, and 55_000 is only ~4.6x the 12_000
    seed, so both used to stay on the sample.
    """
    from server.services.digital_twin import get_twin_state

    company = _company_with_sample_state(db)
    db.add(TruthScan(
        company_id=company.id,
        outputs_json={"metrics": {"cash_balance": CASH, "net_burn": BURN}},
    ))
    db.commit()

    state = get_twin_state(db, company.id)
    assert state["financials"]["cash_balance"] == CASH
    assert state["financials"]["monthly_burn"] == BURN
    assert state["derived_metrics"]["runway_months"] == pytest.approx(10.9, abs=0.05)
    _assert_no_fallback(state)


def test_twin_does_not_invent_stage_sample_when_financials_missing(db):
    from server.services.digital_twin import get_twin_state

    company = _company_with_sample_state(db)
    state = get_twin_state(db, company.id)

    assert state["financials"]["cash_balance"] is None
    assert state["financials"]["monthly_burn"] is None
    assert state["financials"]["revenue_monthly"] is None
    assert state["derived_metrics"]["runway_months"] is None
    assert state["assumption_fields"] == []
    _assert_no_fallback(state)


def test_sample_record_is_labelled_assumption_not_silent(db):
    from server.services.digital_twin import get_twin_state

    company = _company_with_sample_state(db)
    record = _entered_record(db, company.id, cash=80_000, burn=10_000)
    record.source_type = "sample"
    db.commit()

    state = get_twin_state(db, company.id)
    assert state["financials"]["cash_balance"] == 80_000
    assert state["financials"]["monthly_burn"] == 10_000
    assert state["derived_metrics"]["runway_months"] == pytest.approx(8.0, abs=0.05)
    assert "cash_balance" in state["assumption_fields"]
    assert "monthly_burn" in state["assumption_fields"]
    assert "runway_months" in state["assumption_fields"]
    _assert_no_fallback(state)
