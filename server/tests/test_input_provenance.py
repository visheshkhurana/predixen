"""Connector sync provenance: source and synced_at, never a guess."""

import logging
from datetime import date, datetime
import os

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from server.api.connectors import _build_financial_record
from server.api.csv_import import provided_csv_input_fields, with_csv_import_provenance
from server.core.db import Base
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.services.input_provenance import (
    MISSING_PROVENANCE_COLUMNS_WARNING,
    get_input_provenance_sources,
    parse_utc_timestamp,
    reset_provenance_column_state,
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


def test_sync_leaves_source_out_when_provenance_columns_are_missing(caplog):
    """A connector write still commits when the live table has no provenance columns."""
    reset_provenance_column_state()
    caplog.set_level(logging.WARNING, logger="server.services.input_provenance")

    engine = create_engine("sqlite:///:memory:")
    FinancialRecord.__table__.create(engine)
    with engine.begin() as connection:
        for name in ("source", "synced_at", "synced_fields"):
            connection.execute(text(f"ALTER TABLE financial_records DROP COLUMN {name}"))
    db = sessionmaker(bind=engine)()
    try:
        record = _build_financial_record(
            42,
            "stripe",
            "Stripe",
            {
                "revenue": 95000,
                "api_key": "sk_live_secret",
                "account_number": "000123456789",
                "email": "founder@example.com",
            },
            TODAY,
        )
        db.add(record)
        db.commit()

        stored = db.query(FinancialRecord).filter(FinancialRecord.company_id == 42).one()
        stored.revenue = 96000
        stored.source = "stripe"
        stored.synced_at = "2026-10-12T00:00:00Z"
        stored.synced_fields = ["revenue"]
        db.commit()

        revenue = db.execute(text("SELECT revenue FROM financial_records")).scalar()
        assert revenue == 96000
        assert get_input_provenance_sources(42, db) == {}
        assert get_input_provenance_sources(42, db) == {}
    finally:
        db.close()
        engine.dispose()

    warnings = [
        rec
        for rec in caplog.records
        if rec.name == "server.services.input_provenance" and rec.levelno >= logging.WARNING
    ]
    assert len(warnings) == 1
    assert warnings[0].getMessage() == MISSING_PROVENANCE_COLUMNS_WARNING
    leaked = ("95000", "96000", "sk_live_secret", "000123456789", "founder@example.com", "42")
    assert all(secret not in warnings[0].getMessage() for secret in leaked)

    # The missing-column flush trims null-insert bookkeeping on the mapper.
    # A later database that has the columns must still store a real source.
    migrated = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(migrated, tables=[Company.__table__, FinancialRecord.__table__])
    migrated_db = sessionmaker(bind=migrated)()
    try:
        company = _company(migrated_db, "after-unmigrated")
        saved = _save_connector_record(
            migrated_db, company.id, "tally", {"revenue": 10}, "2026-10-12T00:00:00Z"
        )
        assert saved.source == "tally"
        assert get_input_provenance_sources(company.id, migrated_db)["revenue"]["source"] == "tally"
    finally:
        migrated_db.close()
        migrated.dispose()


# --------------------------------------------------------------------------
# Schema: model columns and the startup migration (server/core/migrations.py).
# Railway never runs Alembic; ensure_financial_record_columns is the path.
# --------------------------------------------------------------------------
LEGACY_TABLE_SQL = """
    CREATE TABLE financial_records (
        id INTEGER PRIMARY KEY,
        company_id INTEGER NOT NULL,
        period_start DATE NOT NULL,
        period_end DATE NOT NULL,
        revenue FLOAT
    )
"""
PROVENANCE_COLUMNS = {"source", "synced_at", "synced_fields"}


def test_model_declares_nullable_provenance_columns():
    from sqlalchemy import JSON, String

    columns = FinancialRecord.__table__.c
    assert isinstance(columns.source.type, String) and columns.source.type.length == 64
    assert isinstance(columns.synced_at.type, String) and columns.synced_at.type.length == 40
    assert isinstance(columns.synced_fields.type, JSON)
    for name in PROVENANCE_COLUMNS:
        assert columns[name].nullable is True
        assert columns[name].default is None
        assert columns[name].server_default is None


def test_startup_migration_adds_columns_to_existing_table_idempotently(tmp_path):
    from server.core.migrations import ensure_financial_record_columns

    url = f"sqlite:///{tmp_path / 'startup.db'}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text(LEGACY_TABLE_SQL))
        connection.execute(text(
            "INSERT INTO financial_records (id, company_id, period_start, period_end, revenue) "
            "VALUES (1, 7, '2026-10-01', '2026-10-31', 95000)"
        ))
    ensure_financial_record_columns(engine)
    first = _column_names(url)
    ensure_financial_record_columns(engine)
    engine.dispose()

    assert PROVENANCE_COLUMNS <= first
    assert _column_names(url) == first
    assert _scalar(url, "SELECT revenue FROM financial_records WHERE id = 1") == 95000
    assert _scalar(
        url,
        "SELECT COUNT(*) FROM financial_records "
        "WHERE source IS NULL AND synced_at IS NULL AND synced_fields IS NULL",
    ) == 1


class _RecordingConnection:
    """Captures DDL text. Stands in for a Postgres connection."""

    class _Dialect:
        name = "postgresql"

    class _Nested:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def __init__(self):
        self.dialect = self._Dialect()
        self.statements = []
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, clause):
        self.statements.append(str(clause))

    def begin_nested(self):
        return self._Nested()

    def commit(self):
        self.committed = True


def test_startup_migration_emits_postgres_add_column_if_not_exists():
    from server.core.migrations import ensure_financial_record_columns

    connection = _RecordingConnection()

    class _Engine:
        def connect(self):
            return connection

    ensure_financial_record_columns(_Engine())

    assert connection.committed is True
    expected = {
        "ALTER TABLE financial_records ADD COLUMN IF NOT EXISTS source VARCHAR(64)",
        "ALTER TABLE financial_records ADD COLUMN IF NOT EXISTS synced_at VARCHAR(40)",
        "ALTER TABLE financial_records ADD COLUMN IF NOT EXISTS synced_fields JSON",
    }
    assert expected <= set(connection.statements)
    # Every statement is a plain nullable add: no default, no backfill, nothing destructive.
    for statement in connection.statements:
        upper = statement.upper()
        assert upper.startswith("ALTER TABLE FINANCIAL_RECORDS ADD COLUMN IF NOT EXISTS ")
        assert "NOT NULL" not in upper and "DEFAULT" not in upper
        assert "UPDATE " not in upper and "DROP " not in upper


PG_ADMIN_URL = os.environ.get("TEST_PG_ADMIN_URL", "postgresql+psycopg2://localhost/postgres")
PG_TEST_DB = "fc_provenance_test"


def _pg_available() -> bool:
    try:
        engine = create_engine(PG_ADMIN_URL, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _pg_available(), reason="no local PostgreSQL")
def test_startup_migration_on_postgres_with_existing_rows():
    from sqlalchemy.engine import make_url

    from server.core.migrations import ensure_financial_record_columns

    admin = create_engine(PG_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {PG_TEST_DB}"))
        conn.execute(text(f"CREATE DATABASE {PG_TEST_DB}"))
    url = make_url(PG_ADMIN_URL).set(database=PG_TEST_DB)
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text(LEGACY_TABLE_SQL.replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY")))
            connection.execute(text(
                "INSERT INTO financial_records (company_id, period_start, period_end, revenue) "
                "VALUES (7, '2026-10-01', '2026-10-31', 95000)"
            ))
        ensure_financial_record_columns(engine)
        ensure_financial_record_columns(engine)
        with engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT column_name, data_type, character_maximum_length, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_name = 'financial_records' "
                "AND column_name IN ('source', 'synced_at', 'synced_fields') ORDER BY column_name"
            )).all()
            revenue = connection.execute(text("SELECT revenue FROM financial_records")).scalar()
        assert [tuple(r) for r in rows] == [
            ("source", "character varying", 64, "YES", None),
            ("synced_at", "character varying", 40, "YES", None),
            ("synced_fields", "json", None, "YES", None),
        ]
        assert revenue == 95000
    finally:
        engine.dispose()
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {PG_TEST_DB}"))
        admin.dispose()


# --------------------------------------------------------------------------
# Ingest paths: connector API builder, worker, csv import endpoint.
# --------------------------------------------------------------------------
def test_connector_builder_ignores_d2c_and_ad_spend_keys(db):
    company = _company(db, "shopify-d2c")
    record = _save_connector_record(
        db,
        company.id,
        "shopify",
        {
            "revenue": 230000,
            "cogs": 92000,
            "customers": 1840,
            "d2c": {"orders": 900, "cod_share": 0.4},
            "ad_spend": 12000,
        },
        "2026-10-12T00:00:00Z",
    )
    assert record.source == "shopify"
    assert record.source_type == "connector_shopify"
    assert set(record.synced_fields) == {"revenue", "cogs", "customers"}
    # Derived fields are still computed exactly as before.
    assert record.gross_profit == 230000 - 92000
    assert record.gross_margin == pytest.approx((230000 - 92000) / 230000 * 100)


def test_both_razorpayx_ids_store_razorpayx():
    for provider_id in ("razorpayx", "razorpayx_payroll"):
        stamped = stamp_sync_provenance(provider_id, ["payroll"])
        assert stamped["source"] == "razorpayx", provider_id


def test_unknown_provider_stamps_nothing():
    assert stamp_sync_provenance("connector_stripe", ["revenue"]) == {
        "source": None, "synced_at": None, "synced_fields": None,
    }


@pytest.fixture
def full_db():
    """Every table the app builds, for handlers that touch more than two."""
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")
    def _jsonb_as_json(type_, compiler, **kw):  # DDL render shim only
        return "JSON"

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def test_connector_worker_stamps_provenance(full_db, monkeypatch):
    from server.workers.handlers import connector_handler

    company = _company(full_db, "worker")

    class _FakeConnector:
        def authenticate(self, credentials):
            return True

        def sync_all(self):
            return {"ok": True}

        def map_to_financials(self, result):
            return {"revenue": 5000, "payroll": 1200, "api_key": "sk_live_secret"}

    real_load = __import__("server.connectors", fromlist=["load_all_connectors"]).load_all_connectors
    calls = {"n": 0}

    def _load():
        # First call is the worker's lookup; later calls come from the
        # provenance helper building the canonical id set.
        calls["n"] += 1
        if calls["n"] == 1:
            return {"stripe": _FakeConnector}
        return real_load()

    monkeypatch.setattr("server.core.db.SessionLocal", lambda: full_db)
    monkeypatch.setattr("server.connectors.load_all_connectors", _load)
    monkeypatch.setattr("server.core.cache.cache_delete", lambda key: True)
    monkeypatch.setattr("server.services.digital_twin.emit_twin_event", lambda *a, **k: None)
    monkeypatch.setattr(full_db, "close", lambda: None)

    result = connector_handler.handle_connector_sync(
        {"company_id": company.id, "connector_type": "stripe", "credentials": {}}
    )
    assert result["status"] == "completed"

    record = full_db.query(FinancialRecord).filter(FinancialRecord.company_id == company.id).one()
    assert record.source == "stripe"
    assert parse_utc_timestamp(record.synced_at) is not None
    assert set(record.synced_fields) == {"revenue", "payroll"}
    provenance = get_input_provenance_sources(company.id, full_db)
    assert set(provenance) == {"revenue", "payroll"}


def test_csv_import_endpoint_stamps_rows(full_db, monkeypatch):
    from server.api.csv_import import ColumnMappingRequest, import_csv_data
    from server.models.user import User

    user = User(email="csv-provenance@example.com")
    full_db.add(user)
    full_db.commit()
    company = Company(user_id=user.id, name="CSV provenance")
    full_db.add(company)
    full_db.commit()

    # The truth-scan recompute after import is not under test.
    monkeypatch.setattr("server.truth.truth_scan.compute_truth_scan", lambda *a, **k: {})

    import_csv_data(
        company_id=company.id,
        data=ColumnMappingRequest(
            mappings={"date": "Month", "revenue": "Revenue", "cogs": "COGS", "cash_balance": "Cash"},
            rows=[{"Month": "2026-09-01", "Revenue": "10000", "COGS": "4000", "Cash": "50000"}],
        ),
        db=full_db,
        current_user=user,
    )

    record = full_db.query(FinancialRecord).filter(FinancialRecord.company_id == company.id).one()
    assert record.source == "csv_import"
    assert record.source_type == "csv_import"
    assert parse_utc_timestamp(record.synced_at) is not None
    assert record.synced_fields == ["revenue", "cogs", "cash_balance"]
    assert record.gross_margin == 60.0  # computed, still stored
    provenance = get_input_provenance_sources(company.id, full_db)
    assert set(provenance) == {"revenue", "cogs", "cash_balance"}


def test_include_values_returns_winning_number(db):
    company = _company(db, "values")
    _save_connector_record(db, company.id, "stripe", {"mrr": 15400, "customers": 312}, "2026-10-01T00:00:00Z")
    _save_connector_record(db, company.id, "stripe", {"mrr": 16000}, "2026-11-01T00:00:00Z")

    plain = get_input_provenance_sources(company.id, db)
    assert plain["mrr"] == {"source": "stripe", "synced_at": "2026-11-01T00:00:00Z"}

    valued = get_input_provenance_sources(company.id, db, include_values=True)
    assert valued["mrr"] == {"source": "stripe", "synced_at": "2026-11-01T00:00:00Z", "value": 16000}
    assert valued["customers"]["value"] == 312
