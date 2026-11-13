"""Sample-data first-run snapshot: labelled inputs must match calculated insight."""
import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "services" / "sample_data.py"
_spec = importlib.util.spec_from_file_location("fc_sample_data", _PATH)
assert _spec and _spec.loader
sample_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sample_data)

SAMPLE_FINANCIALS = sample_data.SAMPLE_FINANCIALS
SAMPLE_SOURCE_TYPE = sample_data.SAMPLE_SOURCE_TYPE
build_sample_months = sample_data.build_sample_months
derive_sample_insight = sample_data.derive_sample_insight
sample_monthly_expenses = sample_data.sample_monthly_expenses
clear_is_sample = sample_data.clear_is_sample
financial_source_counts = sample_data.financial_source_counts
on_real_financials_written = sample_data.on_real_financials_written
seed_sample_company = sample_data.seed_sample_company


def test_canonical_insight_is_27k_burn_and_27_8_runway():
    insight = derive_sample_insight()
    expenses = sample_monthly_expenses()
    assert expenses == 72000.0
    assert insight["inputs"]["monthly_revenue"] == 45000.0
    assert insight["inputs"]["monthly_expenses"] == 72000.0
    assert insight["inputs"]["cash_balance"] == 750000.0
    assert insight["outputs"]["monthly_burn"] == 27000.0
    assert insight["outputs"]["runway_months"] == 27.8


def test_latest_seeded_month_matches_canonical_snapshot():
    months = build_sample_months(12)
    assert len(months) == 12
    latest = months[-1]
    assert latest["monthly_revenue"] == SAMPLE_FINANCIALS["monthly_revenue"]
    assert latest["opex"] == SAMPLE_FINANCIALS["opex"]
    assert latest["payroll"] == SAMPLE_FINANCIALS["payroll"]
    assert latest["other_costs"] == SAMPLE_FINANCIALS["other_costs"]
    assert latest["cash_balance"] == SAMPLE_FINANCIALS["cash_balance"]
    insight = derive_sample_insight(
        latest["monthly_revenue"],
        sample_monthly_expenses(latest),
        latest["cash_balance"],
    )
    assert insight["outputs"]["monthly_burn"] == 27000.0
    assert insight["outputs"]["runway_months"] == 27.8


def test_computed_metrics_formula_includes_breakdown_not_cogs_double_count():
    """cogs and marketing are zero in the snapshot so the onboarding card
    (opex+payroll+other) matches GET /metrics/computed (those plus cogs + marketing)."""
    snap = SAMPLE_FINANCIALS
    card_expenses = snap["opex"] + snap["payroll"] + snap["other_costs"]
    computed_expenses = card_expenses + snap["cogs"] + snap["marketing_expense"]
    assert card_expenses == computed_expenses == 72000.0


# ---------------------------------------------------------------------------
# is_sample set on seed / clear only after real financials replace sample
# ---------------------------------------------------------------------------

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.core.db import Base
from server.models.company import Company
from server.models.financial import FinancialRecord


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


def _company(db, name="Sample Co"):
    company = Company(user_id=1, name=name)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def _add_real_record(db, company_id, source_type="manual"):
    db.add(
        FinancialRecord(
            company_id=company_id,
            period_start=date(2026, 9, 1),
            period_end=date(2026, 9, 21),
            revenue=12000,
            cogs=0,
            opex=4000,
            payroll=5000,
            other_costs=1000,
            cash_balance=80000,
            source_type=source_type,
        )
    )


def test_seed_sets_is_sample_and_sample_source_rows(db):
    company = _company(db)
    result = seed_sample_company(db, company.id)
    db.refresh(company)

    assert result["is_sample"] is True
    assert result["already_seeded"] is False
    assert result["record_count"] == 12
    assert company.is_sample is True
    sample, real = financial_source_counts(db, company.id)
    assert sample == 12
    assert real == 0


def test_already_seeded_keeps_sample_when_only_sample_rows(db):
    company = _company(db)
    seed_sample_company(db, company.id)
    again = seed_sample_company(db, company.id)
    db.refresh(company)

    assert again["already_seeded"] is True
    assert again["is_sample"] is True
    assert company.is_sample is True
    sample, real = financial_source_counts(db, company.id)
    assert sample == 12
    assert real == 0


def test_real_financial_write_replaces_sample_and_clears_is_sample(db):
    company = _company(db)
    seed_sample_company(db, company.id)
    assert company.is_sample is True

    _add_real_record(db, company.id, source_type="manual")
    cleared = on_real_financials_written(db, company.id, commit=True)
    db.refresh(company)

    assert cleared is True
    assert company.is_sample is False
    sample, real = financial_source_counts(db, company.id)
    assert sample == 0
    assert real == 1
    leftover = (
        db.query(FinancialRecord)
        .filter(
            FinancialRecord.company_id == company.id,
            FinancialRecord.source_type == SAMPLE_SOURCE_TYPE,
        )
        .count()
    )
    assert leftover == 0


def test_clear_does_not_run_while_sample_rows_remain(db):
    company = _company(db)
    seed_sample_company(db, company.id)
    _add_real_record(db, company.id, source_type="csv_import")
    db.commit()

    # Mixed rows: helper that only clears (no replace) must leave the label on.
    assert clear_is_sample(db, company.id, commit=True) is False
    db.refresh(company)
    assert company.is_sample is True
    sample, real = financial_source_counts(db, company.id)
    assert sample == 12
    assert real == 1


def test_clear_does_not_run_without_a_real_row(db):
    company = _company(db)
    seed_sample_company(db, company.id)
    assert clear_is_sample(db, company.id, commit=True) is False
    db.refresh(company)
    assert company.is_sample is True


def test_helper_without_real_row_does_not_wipe_sample(db):
    company = _company(db)
    seed_sample_company(db, company.id)
    assert on_real_financials_written(db, company.id, commit=True) is False
    db.refresh(company)
    assert company.is_sample is True
    sample, real = financial_source_counts(db, company.id)
    assert sample == 12
    assert real == 0


def test_already_seeded_does_not_relabel_cleared_real_company(db):
    company = _company(db)
    seed_sample_company(db, company.id)
    _add_real_record(db, company.id, source_type="connector_stripe")
    on_real_financials_written(db, company.id, commit=True)
    db.refresh(company)
    assert company.is_sample is False

    again = seed_sample_company(db, company.id)
    db.refresh(company)

    assert again["already_seeded"] is True
    assert again["is_sample"] is False
    assert company.is_sample is False
    sample, real = financial_source_counts(db, company.id)
    assert sample == 0
    assert real >= 1
