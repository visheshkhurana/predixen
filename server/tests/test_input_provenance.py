"""Connector sync provenance: source and synced_at, never a guess."""

from datetime import date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from server.api.connectors import _build_financial_record
from server.api.csv_import import provided_csv_input_fields, with_csv_import_provenance
from server.core.db import Base
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.services.input_provenance import (
    get_input_provenance_sources,
    parse_utc_timestamp,
    stamp_sync_provenance,
)

TODAY = date(2026, 10, 12)

CONNECTOR_PAYLOADS = {
    "tally": {"revenue": 95000, "cogs": 38000, "opex": 28000},
    "razorpayx": {"payroll": 85000, "headcount": 15},
    "stripe": {
        "revenue": 185000,
        "mrr": 15400,
        "arr": 184800,
        "customers": 312,
        "cash_balance": 420000,
        "cogs": 18500,
        "opex": 45000,
        "payroll": 95000,
        "api_key": "sk_live_secret",
        "account_number": "000123456789",
    },
    "zoho_books": {"revenue": 145000, "cogs": 29000, "opex": 43000, "cash_balance": 260000},
}


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Company.__table__, FinancialRecord.__table__],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _company(db, name="Provenance Co"):
    company = Company(user_id=1, name=name)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def _save_connector_record(db, company_id, provider_id, payload, synced_at="2026-10-12T15:00:00Z"):
    record = _build_financial_record(company_id, provider_id, provider_id, payload, TODAY)
    record.synced_at = synced_at
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def test_each_connector_sync_record_sets_source_and_synced_at(db):
    expected = {
        "tally": {"revenue", "cogs", "opex"},
        "razorpayx": {"payroll", "headcount"},
        "stripe": {"revenue", "mrr", "arr", "customers", "cash_balance", "cogs", "opex", "payroll"},
        "zoho_books": {"revenue", "cogs", "opex", "cash_balance"},
    }
    synced_at = "2026-10-12T15:04:05Z"

    for provider_id, fields in expected.items():
        company = _company(db, provider_id)
        record = _save_connector_record(
            db, company.id, provider_id, CONNECTOR_PAYLOADS[provider_id], synced_at
        )
        assert record.source == provider_id
        assert record.synced_at == synced_at
        assert parse_utc_timestamp(record.synced_at) is not None
        assert set(record.synced_fields) == fields
        assert "api_key" not in (record.synced_fields or [])
        assert "account_number" not in (record.synced_fields or [])
        assert "sk_live_secret" not in (record.extraction_summary or "")

        provenance = get_input_provenance_sources(company.id, db)
        assert set(provenance) == fields
        for field, entry in provenance.items():
            assert set(entry) == {"source", "synced_at"}
            assert entry == {"source": provider_id, "synced_at": synced_at}

        # Margin computed from revenue and cogs is stored, but it was not synced.
        if "cogs" in fields and "revenue" in fields:
            assert record.gross_margin is not None
            assert "gross_margin" not in provenance


def test_csv_import_row_sets_source_and_leaves_computed_fields_out(db):
    company = _company(db, "csv")
    provided = provided_csv_input_fields(
        revenue=10000,
        expenses=None,
        cogs=4000,
        other_costs=None,
        cash=50000,
        payroll=None,
        mrr=None,
        arr=None,
        customers=None,
        headcount=None,
        burn=None,
        gross_margin=None,
        cac=None,
    )
    assert provided == ["revenue", "cogs", "cash_balance"]
    synced_at = "2026-10-12T16:00:00Z"
    values = with_csv_import_provenance(
        {
            "revenue": 10000,
            "cogs": 4000,
            "cash_balance": 50000,
            "gross_margin": 60.0,
            "net_burn": 0,
            "runway_months": None,
            "source_type": "csv_import",
        },
        provided,
    )
    values["synced_at"] = synced_at
    record = FinancialRecord(
        company_id=company.id,
        period_start=TODAY,
        period_end=TODAY,
        **values,
    )
    db.add(record)
    db.commit()

    assert record.source == "csv_import"
    assert record.synced_fields == ["revenue", "cogs", "cash_balance"]
    provenance = get_input_provenance_sources(company.id, db)
    assert set(provenance) == {"revenue", "cogs", "cash_balance"}
    assert provenance["revenue"] == {"source": "csv_import", "synced_at": synced_at}
    assert "gross_margin" not in provenance
    assert "net_burn" not in provenance


def test_razorpayx_provider_id_is_stored_as_canonical_id():
    stamped = stamp_sync_provenance("razorpayx_payroll", ["payroll", "api_secret"])
    assert stamped["source"] == "razorpayx"
    assert stamped["synced_fields"] == ["payroll"]
    assert parse_utc_timestamp(stamped["synced_at"]) is not None


def test_manual_and_unknown_values_are_left_out(db):
    company = _company(db, "mixed")
    _save_connector_record(
        db,
        company.id,
        "stripe",
        {"revenue": 185000, "mrr": 15400},
        synced_at="2026-10-01T00:00:00Z",
    )
    db.add(FinancialRecord(
        company_id=company.id,
        period_start=TODAY,
        period_end=TODAY,
        revenue=999,
        payroll=1000,
        source_type="manual",
        source=None,
        synced_at=None,
        created_at=datetime(2026, 10, 2, 0, 0, 0),
    ))
    db.add(FinancialRecord(
        company_id=company.id,
        period_start=TODAY,
        period_end=TODAY,
        cash_balance=42,
        source="acct_123456789",
        synced_at="2026-10-03T00:00:00Z",
        synced_fields=["cash_balance"],
        created_at=datetime(2026, 10, 3, 0, 0, 0),
    ))
    db.add(FinancialRecord(
        company_id=company.id,
        period_start=TODAY,
        period_end=TODAY,
        customers=8,
        source="founder@example.com",
        synced_at="2026-10-04T00:00:00Z",
        synced_fields=["customers"],
        created_at=datetime(2026, 10, 4, 0, 0, 0),
    ))
    db.add(FinancialRecord(
        company_id=company.id,
        period_start=TODAY,
        period_end=TODAY,
        opex=10,
        source="connector_stripe",
        synced_at="2026-10-05T00:00:00Z",
        synced_fields=["opex"],
        created_at=datetime(2026, 10, 5, 0, 0, 0),
    ))
    db.commit()

    provenance = get_input_provenance_sources(company.id, db)
    # Later manual revenue replaces the stripe number, so revenue is unlabeled.
    # mrr was only on the stripe row.
    assert "revenue" not in provenance
    assert "payroll" not in provenance
    assert "cash_balance" not in provenance
    assert "customers" not in provenance
    assert "opex" not in provenance
    assert provenance["mrr"] == {"source": "stripe", "synced_at": "2026-10-01T00:00:00Z"}


def test_only_manual_company_has_no_provenance(db):
    company = _company(db, "manual-only")
    db.add(FinancialRecord(
        company_id=company.id,
        period_start=TODAY,
        period_end=TODAY,
        revenue=5000,
        cash_balance=80000,
        source_type="manual",
    ))
    db.commit()
    assert get_input_provenance_sources(company.id, db) == {}


def test_latest_sync_wins_per_field_and_ties_are_omitted(db):
    company = _company(db, "latest")
    _save_connector_record(
        db,
        company.id,
        "stripe",
        {"revenue": 100, "mrr": 80},
        synced_at="2026-09-01T00:00:00Z",
    )
    _save_connector_record(
        db,
        company.id,
        "tally",
        {"revenue": 200, "cogs": 50},
        synced_at="2026-10-01T00:00:00Z",
    )
    _save_connector_record(
        db,
        company.id,
        "zoho_books",
        {"cogs": 70},
        synced_at="2026-10-01T00:00:00Z",
    )

    provenance = get_input_provenance_sources(company.id, db)
    assert provenance["revenue"] == {"source": "tally", "synced_at": "2026-10-01T00:00:00Z"}
    assert provenance["mrr"] == {"source": "stripe", "synced_at": "2026-09-01T00:00:00Z"}
    assert "cogs" not in provenance


def test_unparsable_synced_at_is_left_out(db):
    company = _company(db, "bad-time")
    record = _save_connector_record(
        db, company.id, "tally", {"revenue": 1}, synced_at="yesterday"
    )
    assert record.source == "tally"
    assert get_input_provenance_sources(company.id, db) == {}


def test_company_id_lookup_uses_session_when_db_omitted(db, monkeypatch):
    company = _company(db, "session-local")
    _save_connector_record(db, company.id, "tally", {"revenue": 10}, "2026-10-12T00:00:00Z")

    def _open():
        return db

    closed = {"value": False}
    original_close = db.close

    def _close():
        closed["value"] = True

    monkeypatch.setattr("server.services.input_provenance.SessionLocal", _open)
    monkeypatch.setattr(db, "close", _close)
    try:
        provenance = get_input_provenance_sources(company.id)
    finally:
        monkeypatch.setattr(db, "close", original_close)
    assert closed["value"] is True
    assert provenance["revenue"]["source"] == "tally"


def _column_names(url):
    engine = create_engine(url)
    try:
        return {column["name"] for column in inspect(engine).get_columns("financial_records")}
    finally:
        engine.dispose()


def _scalar(url, sql):
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return connection.execute(text(sql)).scalar()
    finally:
        engine.dispose()


def test_migration_up_down_up(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db_path = tmp_path / "provenance.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE financial_records (
                id INTEGER PRIMARY KEY,
                company_id INTEGER NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                revenue FLOAT
            )
        """))
        connection.execute(text(
            "INSERT INTO financial_records (id, company_id, period_start, period_end, revenue) "
            "VALUES (1, 7, '2026-10-01', '2026-10-31', 95000)"
        ))
    engine.dispose()

    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    provenance = {"source", "synced_at", "synced_fields"}

    command.upgrade(config, "head")
    upgraded = _column_names(url)
    print(f"upgrade head columns: {sorted(upgraded)}")
    assert provenance <= upgraded
    assert _scalar(url, "SELECT revenue FROM financial_records WHERE id = 1") == 95000

    command.downgrade(config, "base")
    downgraded = _column_names(url)
    print(f"downgrade base columns: {sorted(downgraded)}")
    assert provenance.isdisjoint(downgraded)
    assert _scalar(url, "SELECT revenue FROM financial_records WHERE id = 1") == 95000

    command.upgrade(config, "head")
    restored = _column_names(url)
    print(f"upgrade head again columns: {sorted(restored)}")
    assert provenance <= restored
    assert _scalar(url, "SELECT revenue FROM financial_records WHERE id = 1") == 95000
    engine = create_engine(url)
    with engine.connect() as connection:
        source, synced_at, synced_fields = connection.execute(text(
            "SELECT source, synced_at, synced_fields FROM financial_records WHERE id = 1"
        )).one()
    engine.dispose()
    print(
        "existing row after up/down/up: "
        f"source={source!r} synced_at={synced_at!r} synced_fields={synced_fields!r} revenue=95000"
    )
    assert source is None and synced_at is None and synced_fields is None

    command.upgrade(config, "head")
    assert _column_names(url) == restored


def test_migration_upgrade_when_columns_already_present(tmp_path, monkeypatch):
    """create_all on the current model already has the columns; upgrade must no-op."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db_path = tmp_path / "already.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine, tables=[FinancialRecord.__table__])
    engine.dispose()

    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    before = _column_names(url)
    command.upgrade(config, "head")
    assert _column_names(url) == before
    assert {"source", "synced_at", "synced_fields"} <= before
