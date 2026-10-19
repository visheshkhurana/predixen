"""DELETE /companies/{id} cascade.

The old hand-written cascade filtered InvestorPipeline.company_id, a column
the model does not have, so every company delete raised and returned 500.
The cascade is now derived from FK metadata (server/core/company_purge.py).

The metadata tests run everywhere. The PostgreSQL test builds the real schema
and deletes a company with fundraising, cap-table and billing rows; it is
skipped when no local PostgreSQL is reachable.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from server.core.company_purge import describe_plan, plan_company_purge

PG_ADMIN_URL = os.environ.get("TEST_PG_ADMIN_URL", "postgresql://localhost/postgres")
TEST_DB_NAME = "fc_company_purge_test"


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


def _index(plan, entry):
    return plan.index(entry)


def test_investor_pipeline_is_cleared_through_its_real_relations():
    plan = describe_plan(1)
    # Reached through both parents, never through a nonexistent company_id.
    assert "delete investor_pipeline.round_id" in plan
    assert "delete investor_pipeline.investor_id" in plan
    assert not any(p.startswith("delete investor_pipeline.company_id") for p in plan)
    assert _index(plan, "delete investor_pipeline.round_id") < _index(plan, "delete fundraising_rounds.company_id")
    assert _index(plan, "delete investor_pipeline.investor_id") < _index(plan, "delete investors.company_id")
    assert _index(plan, "delete round_terms.round_id") < _index(plan, "delete fundraising_rounds.company_id")


def test_billing_and_audit_rows_are_detached_not_deleted():
    plan = describe_plan(1)
    assert "nullify subscriptions.company_id" in plan
    assert "nullify llm_audit_logs.company_id" in plan
    assert not any(p.startswith("delete subscriptions.") for p in plan)


def test_every_table_with_a_required_company_fk_is_covered():
    from server.core.db import Base

    plan = set(describe_plan(1))
    for table in Base.metadata.sorted_tables:
        for fk in table.foreign_keys:
            if fk.column.table.name == "companies" and not fk.parent.nullable:
                assert f"delete {table.name}.{fk.parent.name}" in plan, table.name


def test_missing_tables_are_skipped_with_their_subtree():
    from server.core.db import Base

    existing = set(Base.metadata.tables) - {"fundraising_rounds"}
    names = {(s.action, s.table.name, s.column.name) for s in plan_company_purge(1, existing)}
    assert ("delete", "investor_pipeline", "round_id") not in names
    assert ("delete", "investor_pipeline", "investor_id") in names


@pytest.fixture(scope="module")
def pg_session():
    admin = create_engine(PG_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    admin.dispose()

    from server.core.company_purge import _load_all_models
    from server.core.db import Base

    _load_all_models()
    url = PG_ADMIN_URL.rsplit("/", 1)[0] + "/" + TEST_DB_NAME
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()

    admin = create_engine(PG_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    admin.dispose()


@pg_only
def test_delete_company_with_fundraising_and_billing_rows(pg_session):
    from server.core.company_purge import purge_company
    from server.models.company import Company
    from server.models.fundraising import FundraisingRound, Investor, InvestorPipeline, RoundTerms
    from server.models.user import User

    db = pg_session
    user = User(email=f"purge-{uuid.uuid4().hex[:8]}@example.com", password_hash="x")
    db.add(user)
    db.flush()
    keep = Company(name="Keep Co", user_id=user.id)
    doomed = Company(name="Doomed Co", user_id=user.id)
    db.add_all([keep, doomed])
    db.flush()

    def fundraising(company):
        rnd = FundraisingRound(company_id=company.id, name="Seed")
        inv = Investor(company_id=company.id, name="Fund I")
        db.add_all([rnd, inv])
        db.flush()
        db.add(RoundTerms(round_id=rnd.id))
        db.add(InvestorPipeline(round_id=rnd.id, investor_id=inv.id))
        db.flush()
        return rnd

    fundraising(doomed)
    kept_round = fundraising(keep)
    db.execute(
        text("INSERT INTO subscriptions (user_id, company_id, plan, status) VALUES (:u, :c, 'starter', 'active')"),
        {"u": user.id, "c": doomed.id},
    )
    db.commit()

    doomed_id, keep_id = doomed.id, keep.id
    db.expunge(doomed)
    purge_company(db, doomed_id)
    db.commit()

    assert db.query(Company).filter(Company.id == doomed_id).count() == 0
    assert db.query(FundraisingRound).filter(FundraisingRound.company_id == doomed_id).count() == 0
    assert db.query(Investor).filter(Investor.company_id == doomed_id).count() == 0
    # The other company's fundraising data is untouched.
    assert db.query(InvestorPipeline).filter(InvestorPipeline.round_id == kept_round.id).count() == 1
    assert db.query(Company).filter(Company.id == keep_id).count() == 1
    # The billing row survives, detached.
    row = db.execute(text("SELECT company_id FROM subscriptions WHERE user_id = :u"), {"u": user.id}).fetchone()
    assert row is not None and row[0] is None
