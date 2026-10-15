"""HAG-363 regression — a manual save must not leave a connector's provenance on the row it overwrote.

The contract (``server/services/input_provenance.py`` docstring, lines 14-17):

    "A field is returned only when the latest value for that field is a sync whose
     connector id and timestamp are both known, and the connector actually supplied
     that field. Manual rows, unknown ids, derived numbers, and ties between
     different origins are left out."

This file drives the REAL write path — ``POST /companies/{id}/financials/save``
(``server/api/ingest.py:838`` ``save_financial_baseline``) — not a hand-built row,
because the row shape the product produces is the thing under test.

Assertions are on the CONTRACT only (what the reader reports), never on the
mechanism, so a fix that satisfies the contract by any means passes.
"""

import asyncio
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.api.connectors import _build_financial_record
from server.api.ingest import NormalizedFinancials, save_financial_baseline
from server.core.db import Base
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.models.user import User
from server.services.input_provenance import get_input_provenance_sources

# sqlite cannot render Postgres JSONB, and the app builds its whole schema here.
# A render shim, not an assertion: it changes DDL text only.
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def _jsonb_as_json(type_, compiler, **kw):
    return "JSON"

FIRST_OF_MONTH = date.today().replace(day=1)
SYNCED_AT = "2026-10-05T00:00:00Z"
STRIPE_REVENUE = 185000.0
TYPED_REVENUE = 9999.0


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    # Full metadata, not a hand-picked subset: the real handler also writes the
    # `datasets` row and reads `truth_scans`, so the schema must be what the app builds.
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _user_and_company(db):
    user = User(email="hag363@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    company = Company(user_id=user.id, name="HAG-363 Co")
    db.add(company)
    db.commit()
    db.refresh(company)
    return user, company


def _stripe_synced_month(db, company_id):
    """A month Stripe has already synced, built by the app's own connector builder."""
    record = _build_financial_record(
        company_id, "stripe", "Stripe",
        {"revenue": STRIPE_REVENUE, "cogs": 18500.0}, FIRST_OF_MONTH,
    )
    record.synced_at = SYNCED_AT
    db.add(record)
    db.commit()
    assert record.period_start == FIRST_OF_MONTH
    assert record.source == "stripe"
    return record


def _manual_save(db, company_id, user, revenue):
    """The real handler, called directly: db and current_user are plain params."""
    baseline = NormalizedFinancials.model_validate({
        "monthly_revenue": revenue,
        "cash_on_hand": 100000.0,
        "expense_breakdown": {"cogs": 111.0, "operating": 5000.0},
        "number_of_employees": 4,
    })
    return asyncio.run(
        save_financial_baseline(
            company_id=company_id, baseline=baseline, request=None,
            db=db, current_user=user,
        )
    )


# --------------------------------------------------------------------------
# POSITIVE CONTROL — the instrument can see a sync at all. Must pass today.
# If this ever fails the other two assert nothing.
# --------------------------------------------------------------------------
def test_a_synced_month_reports_revenue_as_synced(db):
    _, company = _user_and_company(db)
    _stripe_synced_month(db, company.id)

    sources = get_input_provenance_sources(company.id, db=db)

    assert sources.get("revenue") == {"source": "stripe", "synced_at": SYNCED_AT}
    assert sources.get("cogs") == {"source": "stripe", "synced_at": SYNCED_AT}


# --------------------------------------------------------------------------
# CONTROL — a manual save on a month with no synced row. Must pass today.
# --------------------------------------------------------------------------
def test_a_manual_save_on_an_unsynced_month_is_not_reported_as_synced(db):
    user, company = _user_and_company(db)

    _manual_save(db, company.id, user, TYPED_REVENUE)

    sources = get_input_provenance_sources(company.id, db=db)

    assert "revenue" not in sources, sources
    assert "cogs" not in sources, sources


# --------------------------------------------------------------------------
# HAG-363 — the manual save overwrites a synced month. FAILS TODAY.
#
# Connect Stripe -> the month auto-fills -> the founder corrects a number by
# hand and saves. That is the ordinary first-run sequence, and the sequence
# input_provenance.py was written for. The revenue on the row is now typed by
# the user, so the contract says the field must NOT be reported as synced.
# --------------------------------------------------------------------------
def test_a_manual_save_over_a_synced_month_is_not_reported_as_synced(db):
    user, company = _user_and_company(db)
    _stripe_synced_month(db, company.id)

    _manual_save(db, company.id, user, TYPED_REVENUE)

    row = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company.id,
        FinancialRecord.period_start == FIRST_OF_MONTH,
    ).one()
    assert row.revenue == TYPED_REVENUE, "precondition: the typed value is what is stored"

    sources = get_input_provenance_sources(company.id, db=db)

    assert "revenue" not in sources, (
        "revenue holds a hand-typed %r but is still reported as %r — the latest "
        "value for the field is a manual save, so the contract says leave it out"
        % (TYPED_REVENUE, sources.get("revenue"))
    )
    assert "cogs" not in sources, (
        "cogs carries the connector's number on a row a manual save overwrote"
    )
