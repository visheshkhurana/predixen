"""Tests for atomic per-key writes to companies.metadata_json.

The PostgreSQL tests are the ones that matter: they run two concurrent sessions
and assert that a write to one key survives a write to another. That is the
exact failure that made a freshly-created hiring plan 404 on /simulate.

They need a local PostgreSQL and are skipped when one is not reachable, so the
suite still runs on a bare checkout. The SQLite tests cover the fallback path's
semantics everywhere else.
"""

import os

import pytest
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.dialects.postgresql import JSON as PG_JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import JSON

from server.core.company_metadata import (
    delete_metadata_value,
    save_metadata_value,
)

PG_ADMIN_URL = os.environ.get("TEST_PG_ADMIN_URL", "postgresql://localhost/postgres")
TEST_DB_NAME = "fc_metadata_test"


def _pg_available() -> bool:
    try:
        engine = create_engine(PG_ADMIN_URL, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


pg_only = pytest.mark.skipif(not _pg_available(), reason="no local PostgreSQL")


def _make_model(json_type):
    """A minimal mapping of the columns the helper touches.

    Deliberately not the real Company model: that would drag in every FK'd table
    just to exercise two columns.
    """
    Base = declarative_base()

    class Company(Base):
        __tablename__ = "companies"
        id = Column(Integer, primary_key=True)
        name = Column(String, nullable=True)
        metadata_json = Column(json_type, nullable=True)

    return Base, Company


# --------------------------------------------------------------------------
# PostgreSQL: the concurrency guarantees
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pg_engine():
    admin = create_engine(PG_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    admin.dispose()

    url = PG_ADMIN_URL.rsplit("/", 1)[0] + "/" + TEST_DB_NAME
    engine = create_engine(url)
    yield engine
    engine.dispose()

    admin = create_engine(PG_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    admin.dispose()


@pytest.fixture
def pg_setup(pg_engine):
    Base, Company = _make_model(PG_JSON)
    Base.metadata.drop_all(pg_engine)
    Base.metadata.create_all(pg_engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)

    session = Session()
    session.add(Company(id=1, name="TechFlow", metadata_json={"existing": {"keep": True}}))
    session.commit()
    session.close()

    return Session, Company


@pg_only
def test_concurrent_writers_to_different_keys_both_survive(pg_setup):
    """The lost-update bug: two sessions, two different keys, both must persist."""
    Session, Company = pg_setup

    session_a = Session()
    session_b = Session()
    try:
        # A reads the row first -- its in-memory blob has neither new key.
        company_a = session_a.get(Company, 1)
        assert "smart_alerts" not in (company_a.metadata_json or {})

        # B writes a different key and commits while A is still working.
        company_b = session_b.get(Company, 1)
        save_metadata_value(session_b, company_b, "hiring_plans", [{"id": "plan-1"}])

        # A now writes its own key, from its stale read.
        save_metadata_value(session_a, company_a, "smart_alerts", [{"id": "alert-1"}])
    finally:
        session_a.close()
        session_b.close()

    verify = Session()
    try:
        stored = verify.get(Company, 1).metadata_json
    finally:
        verify.close()

    assert stored["hiring_plans"] == [{"id": "plan-1"}], "B's write was clobbered by A"
    assert stored["smart_alerts"] == [{"id": "alert-1"}]
    assert stored["existing"] == {"keep": True}, "pre-existing key was dropped"


@pg_only
def test_naive_read_modify_write_loses_the_sibling(pg_setup):
    """Characterizes the old behaviour, so the regression stays visible."""
    Session, Company = pg_setup

    session_a = Session()
    session_b = Session()
    try:
        company_a = session_a.get(Company, 1)
        _ = company_a.metadata_json  # A's stale read

        company_b = session_b.get(Company, 1)
        save_metadata_value(session_b, company_b, "hiring_plans", [{"id": "plan-1"}])

        # The old pattern: full-dict replace from the stale read.
        metadata = dict(company_a.metadata_json or {})
        metadata["smart_alerts"] = [{"id": "alert-1"}]
        company_a.metadata_json = metadata
        session_a.commit()
    finally:
        session_a.close()
        session_b.close()

    verify = Session()
    try:
        stored = verify.get(Company, 1).metadata_json
    finally:
        verify.close()

    assert "hiring_plans" not in stored, "expected the naive write to lose the sibling"


@pg_only
def test_nested_path_creates_missing_parent(pg_setup):
    """jsonb_set's create_missing would no-op here; the merge must not."""
    Session, Company = pg_setup

    session = Session()
    try:
        company = session.get(Company, 1)
        assert "connectors" not in (company.metadata_json or {})
        save_metadata_value(session, company, ("connectors", "stripe"), {"connected": True})
        session.refresh(company)
        assert company.metadata_json["connectors"]["stripe"] == {"connected": True}
        assert company.metadata_json["existing"] == {"keep": True}
    finally:
        session.close()


@pg_only
def test_concurrent_connector_writes_do_not_race(pg_setup):
    """Two providers connecting at once must not overwrite each other."""
    Session, Company = pg_setup

    session_a = Session()
    session_b = Session()
    try:
        company_a = session_a.get(Company, 1)
        company_b = session_b.get(Company, 1)
        save_metadata_value(session_a, company_a, ("connectors", "stripe"), {"connected": True})
        save_metadata_value(session_b, company_b, ("connectors", "quickbooks"), {"connected": True})
    finally:
        session_a.close()
        session_b.close()

    verify = Session()
    try:
        connectors = verify.get(Company, 1).metadata_json["connectors"]
    finally:
        verify.close()

    assert set(connectors) == {"stripe", "quickbooks"}


@pg_only
def test_delete_removes_only_the_addressed_path(pg_setup):
    Session, Company = pg_setup

    session = Session()
    try:
        company = session.get(Company, 1)
        save_metadata_value(session, company, ("connectors", "stripe"), {"connected": True})
        save_metadata_value(session, company, ("connectors", "quickbooks"), {"connected": True})

        delete_metadata_value(session, company, ("connectors", "stripe"))
        session.refresh(company)

        assert set(company.metadata_json["connectors"]) == {"quickbooks"}
        assert company.metadata_json["existing"] == {"keep": True}
    finally:
        session.close()


@pg_only
def test_uncommitted_write_holds_until_caller_commits(pg_setup):
    """commit=False must still be visible in-session and invisible outside it."""
    Session, Company = pg_setup

    session = Session()
    other = Session()
    try:
        company = session.get(Company, 1)
        save_metadata_value(session, company, "auto_simulations", [{"id": "sim-1"}], commit=False)

        # Visible to the writing session...
        assert company.metadata_json["auto_simulations"] == [{"id": "sim-1"}]
        # ...and not yet to anyone else.
        assert "auto_simulations" not in (other.get(Company, 1).metadata_json or {})

        session.commit()
        other.expire_all()
        assert other.get(Company, 1).metadata_json["auto_simulations"] == [{"id": "sim-1"}]
    finally:
        session.close()
        other.close()


@pg_only
def test_pending_orm_write_cannot_clobber_the_statement(pg_setup):
    """A caller that dirtied metadata_json must not have it flushed over us."""
    Session, Company = pg_setup

    session = Session()
    try:
        company = session.get(Company, 1)
        company.metadata_json = {"stale": True}  # dirty, never flushed
        save_metadata_value(session, company, "smart_alerts", [{"id": "a"}])
        session.refresh(company)

        assert company.metadata_json["smart_alerts"] == [{"id": "a"}]
        assert "stale" not in company.metadata_json
        assert company.metadata_json["existing"] == {"keep": True}
    finally:
        session.close()


# --------------------------------------------------------------------------
# SQLite: the fallback path's semantics
# --------------------------------------------------------------------------


@pytest.fixture
def sqlite_setup():
    Base, Company = _make_model(JSON)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = Session()
    session.add(Company(id=1, name="TechFlow", metadata_json={"existing": {"keep": True}}))
    session.commit()

    yield session, Company
    session.close()
    engine.dispose()


def test_sqlite_set_and_nested_set(sqlite_setup):
    session, Company = sqlite_setup
    company = session.get(Company, 1)

    save_metadata_value(session, company, "smart_alerts", [{"id": "a"}])
    save_metadata_value(session, company, ("connectors", "stripe"), {"connected": True})

    session.refresh(company)
    assert company.metadata_json["smart_alerts"] == [{"id": "a"}]
    assert company.metadata_json["connectors"]["stripe"] == {"connected": True}
    assert company.metadata_json["existing"] == {"keep": True}


def test_sqlite_delete(sqlite_setup):
    session, Company = sqlite_setup
    company = session.get(Company, 1)

    save_metadata_value(session, company, ("connectors", "stripe"), {"connected": True})
    save_metadata_value(session, company, ("connectors", "quickbooks"), {"connected": True})
    delete_metadata_value(session, company, ("connectors", "stripe"))

    session.refresh(company)
    assert set(company.metadata_json["connectors"]) == {"quickbooks"}


def test_sqlite_delete_of_absent_path_is_a_noop(sqlite_setup):
    session, Company = sqlite_setup
    company = session.get(Company, 1)

    delete_metadata_value(session, company, ("connectors", "stripe"))

    session.refresh(company)
    assert company.metadata_json["existing"] == {"keep": True}


def test_sqlite_overwrites_non_dict_ancestor(sqlite_setup):
    session, Company = sqlite_setup
    company = session.get(Company, 1)

    save_metadata_value(session, company, "connectors", "not-a-dict")
    save_metadata_value(session, company, ("connectors", "stripe"), {"connected": True})

    session.refresh(company)
    assert company.metadata_json["connectors"] == {"stripe": {"connected": True}}


# --------------------------------------------------------------------------
# Path validation
# --------------------------------------------------------------------------


@pytest.mark.parametrize("bad_path", [(), "", ("connectors", ""), ("connectors", None), ("a", "b", "c", "d", "e")])
def test_invalid_paths_are_rejected(sqlite_setup, bad_path):
    session, Company = sqlite_setup
    company = session.get(Company, 1)

    with pytest.raises(ValueError):
        save_metadata_value(session, company, bad_path, {"x": 1})
