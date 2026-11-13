"""simulation_v2 reads connector provenance as sync_records.

get_input_provenance_sources(include_values=True) -> sync_records keyed by
simulation input -> normalize_simulation_inputs labels the field synced with
source and synced_at. No LLM call is made anywhere in this module.
"""
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api import simulation_v2
from server.api.connectors import _build_financial_record
from server.core.db import Base, get_db
from server.core.security import get_current_user
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.services.simulation.input_normalization import (
    inputs_for_simulation_request,
    sync_records_from_financial_provenance,
)

SYNCED_AT = "2026-11-01T00:00:00Z"


@pytest.fixture
def db():
    # StaticPool: the route runs in TestClient's thread and must see this database.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Company.__table__, FinancialRecord.__table__])
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _stripe_company(db, user_id=11):
    company = Company(user_id=user_id, name="Synced Co")
    db.add(company)
    db.commit()
    record = _build_financial_record(
        company.id, "stripe", "Stripe",
        {"mrr": 15400, "customers": 312, "cash_balance": 420000, "headcount": 9},
        date(2026, 11, 1),
    )
    record.synced_at = SYNCED_AT
    db.add(record)
    db.commit()
    return company


def test_mapping_keeps_only_usable_one_to_one_fields():
    records = sync_records_from_financial_provenance({
        "mrr": {"value": 15400.0, "source": "stripe", "synced_at": SYNCED_AT},
        "customers": {"value": 312, "source": "stripe", "synced_at": SYNCED_AT},
        "headcount": {"value": 0, "source": "razorpayx", "synced_at": SYNCED_AT},  # below team_size min
        "cash_balance": {"value": -5, "source": "tally", "synced_at": SYNCED_AT},  # below min
        "net_burn": {"value": 9000, "source": "tally", "synced_at": SYNCED_AT},  # not mapped
    })
    assert records == {
        "monthly_revenue": {"value": 15400.0, "source": "stripe", "synced_at": SYNCED_AT},
        "customers": {"value": 312, "source": "stripe", "synced_at": SYNCED_AT},
    }
    assert sync_records_from_financial_provenance(None) == {}


def test_request_fields_stay_entered_and_omitted_fields_take_the_sync(db):
    _stripe_company(db)
    from server.services.input_provenance import get_input_provenance_sources

    company = db.query(Company).one()
    sync_records = sync_records_from_financial_provenance(
        get_input_provenance_sources(company.id, db, include_values=True)
    )
    request = simulation_v2.SimulationV2Request(monthly_revenue=20000, total_rounds=6)
    values, provenance = inputs_for_simulation_request(request, sync_records=sync_records)

    assert values["monthly_revenue"] == 20000
    assert provenance["monthly_revenue"] == {"kind": "entered"}
    assert values["customers"] == 312
    assert provenance["customers"] == {"kind": "synced", "source": "stripe", "synced_at": SYNCED_AT}
    assert values["cash_balance"] == 420000
    assert provenance["cash_balance"]["kind"] == "synced"
    assert values["team_size"] == 9
    assert provenance["team_size"]["source"] == "stripe"
    # Unmapped fields still fall back to the canned baseline.
    assert provenance["monthly_burn"] == {"kind": "assumed"}


def test_no_company_or_no_sync_leaves_inputs_unchanged(db):
    user = SimpleNamespace(id=999)
    assert simulation_v2._simulation_sync_records(db, user) == {}

    request = simulation_v2.SimulationV2Request(total_rounds=6)
    assert inputs_for_simulation_request(request, sync_records={}) == inputs_for_simulation_request(request)


def test_sync_lookup_failure_falls_back_to_empty(monkeypatch):
    class _Broken:
        def query(self, *a, **k):
            raise RuntimeError("db down")

        def rollback(self):
            pass

    assert simulation_v2._simulation_sync_records(_Broken(), SimpleNamespace(id=1)) == {}


def test_run_route_passes_sync_records(db, monkeypatch):
    company = _stripe_company(db, user_id=11)
    user = SimpleNamespace(id=11, email="founder@example.com")
    captured = {}

    class _Stop(Exception):
        pass

    def _capture(request, sync_records=None):
        captured["sync_records"] = sync_records
        raise _Stop()

    monkeypatch.setattr(simulation_v2, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(simulation_v2, "_audited_simulation_client", lambda db, user: object())
    monkeypatch.setattr(simulation_v2, "reserve_monthly_quota", lambda *a, **k: None)
    monkeypatch.setattr(simulation_v2, "inputs_for_simulation_request", _capture)

    app = FastAPI()
    app.include_router(simulation_v2.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    with pytest.raises(_Stop):
        client.post("/simulation/v2/run", json={"total_rounds": 6})

    assert company.id is not None
    assert captured["sync_records"]["customers"] == {"value": 312, "source": "stripe", "synced_at": SYNCED_AT}
    assert captured["sync_records"]["monthly_revenue"]["value"] == 15400
