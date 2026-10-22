"""ensure_simulation_accuracy_tables must not abort Postgres on startup.

The column is created as JSONB, and an unconditional
``ALTER COLUMN variance_pct_json TYPE JSONB`` can abort the transaction or
rewrite the table. These tests run the function twice on a fresh database,
on a database whose column is already jsonb, and on json/text columns.
"""

import logging
import os
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, event, text

from server.core.migrations import (
    _referenced_parent_tables,
    _skip_simulation_accuracy_if_parent_missing,
    ensure_simulation_accuracy_tables,
)

TEST_DB_NAME = "fc_sim_accuracy_mig_test"
_CANDIDATE_ADMIN_URLS = (
    os.environ.get("TEST_PG_ADMIN_URL"),
    "postgresql+psycopg2:///postgres",
    "postgresql+psycopg2://localhost/postgres",
    "postgresql://localhost/postgres",
)


def _working_admin_url():
    for url in _CANDIDATE_ADMIN_URLS:
        if not url:
            continue
        try:
            engine = create_engine(url, connect_args={"connect_timeout": 2})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return url
        except Exception:
            continue
    return None


def _database_url(admin_url: str, database: str) -> str:
    return admin_url.rsplit("/", 1)[0] + "/" + database


@pytest.fixture(scope="module")
def pg_engine():
    admin_url = _working_admin_url()
    if admin_url is None:
        pytest.skip("no local PostgreSQL")

    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    admin.dispose()

    engine = create_engine(_database_url(admin_url, TEST_DB_NAME))
    yield engine
    engine.dispose()

    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(
            text(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = :datname AND pid <> pg_backend_pid()
                """
            ),
            {"datname": TEST_DB_NAME},
        )
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    admin.dispose()


@pytest.fixture
def fresh_pg(pg_engine):
    with pg_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS simulation_accuracy CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS calibration_biases CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS companies CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS simulation_accuracy_child CASCADE"))
    yield pg_engine


def _is_variance_type_alter(statement: str) -> bool:
    compact = " ".join(statement.lower().split())
    return (
        "alter table simulation_accuracy" in compact
        and "alter column variance_pct_json" in compact
        and "type jsonb" in compact
    )


@contextmanager
def capturing_variance_type_alters(engine):
    found = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if statement and _is_variance_type_alter(statement):
            found.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield found
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def _column_type(engine, table_name: str, column_name: str):
    with engine.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT data_type, udt_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = :table_name
                  AND column_name = :column_name
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).first()


def _index_names(engine):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND tablename IN ('simulation_accuracy', 'calibration_biases')
                """
            )
        ).fetchall()
    return {row[0] for row in rows}


def test_referenced_parent_tables_from_create_and_index():
    create = """
        CREATE TABLE IF NOT EXISTS simulation_accuracy (
            company_id INTEGER NOT NULL REFERENCES companies(id),
            simulation_run_id INTEGER REFERENCES public.simulation_runs(id)
        )
    """
    assert _referenced_parent_tables(create) == ["companies", "simulation_runs"]
    assert _referenced_parent_tables(
        "CREATE INDEX IF NOT EXISTS ix_sim_accuracy_company ON simulation_accuracy(company_id)"
    ) == ["simulation_accuracy"]
    assert _referenced_parent_tables(
        "CREATE TABLE IF NOT EXISTS calibration_biases (id SERIAL PRIMARY KEY)"
    ) == []


def test_fresh_database_run_twice_does_not_alter_jsonb(fresh_pg, caplog):
    engine = fresh_pg
    with caplog.at_level(logging.WARNING, logger="server.core.migrations"):
        with capturing_variance_type_alters(engine) as alters:
            ensure_simulation_accuracy_tables(engine)
            ensure_simulation_accuracy_tables(engine)

    assert alters == []
    assert "referenced parent table" not in caplog.text
    assert _column_type(engine, "simulation_accuracy", "variance_pct_json") == ("jsonb", "jsonb")
    assert _column_type(engine, "simulation_accuracy", "predicted_churn") is not None
    assert _column_type(engine, "simulation_accuracy", "actual_churn") is not None
    assert {
        "ix_sim_accuracy_company",
        "ix_sim_accuracy_run",
        "ix_sim_accuracy_computed",
        "ix_cal_biases_company",
        "ix_cal_biases_active",
    } <= _index_names(engine)

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO calibration_biases (company_id, metric) VALUES (1, 'revenue')"
            )
        )
        stored = conn.execute(
            text("SELECT metric FROM calibration_biases")
        ).scalar()
    assert stored == "revenue"


def _precreate_simulation_accuracy(engine, variance_type: str) -> None:
    """Existing table with every indexed column, and a chosen variance type."""
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                CREATE TABLE simulation_accuracy (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    simulation_run_id INTEGER,
                    scenario_id INTEGER,
                    prediction_month INTEGER NOT NULL,
                    predicted_revenue FLOAT,
                    actual_revenue FLOAT,
                    predicted_burn FLOAT,
                    actual_burn FLOAT,
                    predicted_cash FLOAT,
                    actual_cash FLOAT,
                    predicted_churn FLOAT,
                    actual_churn FLOAT,
                    variance_pct_json {variance_type},
                    accuracy_score FLOAT,
                    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO simulation_accuracy (company_id, prediction_month, variance_pct_json)
                VALUES (7, 1, '{"revenue": 1}')
                """
            )
        )


def test_already_jsonb_column_issues_no_alter(fresh_pg):
    engine = fresh_pg
    _precreate_simulation_accuracy(engine, "JSONB")

    with capturing_variance_type_alters(engine) as alters:
        ensure_simulation_accuracy_tables(engine)
    assert alters == []
    assert _column_type(engine, "simulation_accuracy", "variance_pct_json") == ("jsonb", "jsonb")
    with engine.connect() as conn:
        stored = conn.execute(
            text("SELECT variance_pct_json::text FROM simulation_accuracy")
        ).scalar()
    assert stored == '{"revenue": 1}'

    with capturing_variance_type_alters(engine) as second:
        ensure_simulation_accuracy_tables(engine)
    assert second == []


@pytest.mark.parametrize("source_type", ["json", "text"])
def test_json_or_text_column_is_altered_once(fresh_pg, source_type):
    engine = fresh_pg
    _precreate_simulation_accuracy(engine, source_type)

    with capturing_variance_type_alters(engine) as first_alters:
        ensure_simulation_accuracy_tables(engine)
    assert len(first_alters) == 1
    assert _column_type(engine, "simulation_accuracy", "variance_pct_json") == ("jsonb", "jsonb")
    with engine.connect() as conn:
        stored = conn.execute(
            text("SELECT variance_pct_json::text FROM simulation_accuracy")
        ).scalar()
    assert stored == '{"revenue": 1}'

    with capturing_variance_type_alters(engine) as second_alters:
        ensure_simulation_accuracy_tables(engine)
    assert second_alters == []


def test_missing_referenced_parent_skips_with_warning_and_keeps_transaction(fresh_pg, caplog):
    engine = fresh_pg
    create_child = """
        CREATE TABLE IF NOT EXISTS simulation_accuracy_child (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id)
        )
    """
    missing_index = (
        "CREATE INDEX IF NOT EXISTS ix_sim_accuracy_company ON simulation_accuracy(company_id)"
    )
    with caplog.at_level(logging.WARNING, logger="server.core.migrations"):
        with engine.connect() as conn:
            assert _skip_simulation_accuracy_if_parent_missing(conn, create_child) is True
            assert _skip_simulation_accuracy_if_parent_missing(conn, missing_index) is True
            conn.execute(text("SELECT 1"))
            conn.commit()

    warning = caplog.text.lower()
    assert "companies" in warning
    assert "simulation_accuracy" in warning
    assert "missing" in warning
    with engine.connect() as conn:
        child = conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                  AND table_name = 'simulation_accuracy_child'
                """
            )
        ).first()
    assert child is None


def test_sqlite_still_rejects_postgres_only_create():
    """Non-Postgres execution is unchanged: this DDL already failed on SQLite."""
    engine = create_engine("sqlite://")
    with pytest.raises(Exception, match=r"near \"\(\""):
        ensure_simulation_accuracy_tables(engine)
    engine.dispose()
