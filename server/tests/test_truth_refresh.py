"""
Tests for the scheduled truth-scan refresh.

Why this exists: every derived metric a founder sees is read from the newest
stored TruthScan row, not computed per request. Before this scheduler, that row
was only written on a manual "Refresh Scan" click or an import — so a fix to how
a metric is computed could be live in production for hours while the dashboard
kept serving the old value. That happened on 8 Aug with the fabricated 0% churn.

These tests pin the three properties that make the loop safe to leave running:
it refreshes what is stale, it does nothing when nothing is stale, and one bad
company cannot take the rest of the cycle down.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.core.db import Base
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.models.truth_scan import TruthScan
from server.services import truth_refresh
import server.truth.truth_scan as truth_scan_module


NOW = datetime(2026, 8, 8, 12, 0, 0)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Company.__table__, FinancialRecord.__table__, TruthScan.__table__],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def seeded(db):
    """Four companies covering every branch of the staleness decision.

    1: financial data, scan 30h old  -> stale, must refresh
    2: financial data, scan 2h old   -> fresh, must be left alone
    3: financial data, no scan ever  -> stale by definition, must refresh
    4: NO financial data             -> must be ignored entirely
    """
    for cid in (1, 2, 3, 4):
        db.add(Company(id=cid, name=f"co{cid}", user_id=1))
    db.commit()

    for cid in (1, 2, 3):
        db.add(FinancialRecord(
            company_id=cid,
            period_start=NOW.date(),
            period_end=NOW.date(),
            revenue=100,
        ))
    db.add(TruthScan(company_id=1, outputs_json={}, created_at=NOW - timedelta(hours=30)))
    db.add(TruthScan(company_id=2, outputs_json={}, created_at=NOW - timedelta(hours=2)))
    db.commit()
    return db


def _record_calls(monkeypatch, calls, fail_for=()):
    def fake_compute(company, session):
        if company.id in fail_for:
            raise RuntimeError("compute blew up")
        calls.append(company.id)
        return {"metrics": {"mrr": 1}}
    # truth_refresh imports compute_truth_scan inside the function, so patching
    # the module attribute is enough.
    monkeypatch.setattr(truth_scan_module, "compute_truth_scan", fake_compute)


def test_refreshes_only_stale_companies_with_financial_data(seeded, monkeypatch):
    calls = []
    _record_calls(monkeypatch, calls)

    result = truth_refresh.refresh_stale_truth_scans(seeded, now=NOW)

    assert sorted(calls) == [1, 3]
    assert 2 not in calls, "a scan inside the staleness window must not be recomputed"
    assert 4 not in calls, "a company with no financial data must be skipped entirely"
    assert result["refreshed"] == 2
    assert result["failed"] == 0


def test_is_a_no_op_when_nothing_is_stale(seeded, monkeypatch):
    calls = []
    _record_calls(monkeypatch, calls)

    truth_refresh.refresh_stale_truth_scans(seeded, now=NOW)
    calls.clear()
    second = truth_refresh.refresh_stale_truth_scans(seeded, now=NOW)

    assert calls == [], "running again immediately must not recompute anything"
    assert second["refreshed"] == 0


def test_one_failing_company_does_not_stop_the_cycle(seeded, monkeypatch):
    seeded.query(TruthScan).delete()
    seeded.commit()

    calls = []
    _record_calls(monkeypatch, calls, fail_for={3})

    result = truth_refresh.refresh_stale_truth_scans(seeded, now=NOW)

    assert result["failed"] == 1
    assert result["refreshed"] == 2
    assert sorted(calls) == [1, 2], "companies either side of the failure must still run"


def test_respects_the_per_cycle_cap(db, monkeypatch):
    """A large backlog degrades into catching up over several cycles."""
    total = truth_refresh.MAX_PER_CYCLE + 10
    for cid in range(1, total + 1):
        db.add(Company(id=cid, name=f"co{cid}", user_id=1))
        db.add(FinancialRecord(
            company_id=cid,
            period_start=NOW.date(),
            period_end=NOW.date(),
            revenue=100,
        ))
    db.commit()

    calls = []
    _record_calls(monkeypatch, calls)

    result = truth_refresh.refresh_stale_truth_scans(db, now=NOW)

    assert result["refreshed"] == truth_refresh.MAX_PER_CYCLE
    assert len(calls) == truth_refresh.MAX_PER_CYCLE
