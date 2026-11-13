"""Canonical sample-company financials for the signup → first-insight path.

Keep the latest-month snapshot in lockstep with
``client/src/lib/sampleCompany.ts``. The first insight a new user sees
(burn + runway) is derived from these inputs with the same formula
``GET /metrics/computed`` uses: expenses = payroll + opex + other + cogs +
marketing; burn = expenses − revenue; runway = cash / burn.
"""
from datetime import datetime, timedelta
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Latest-month snapshot. Intentionally simple so the onboarding card can
# show input → output without rounding surprises.
SAMPLE_COMPANY = {
    "name": "Sample SaaS Co.",
    "website": "https://example.com",
    "industry": "general_saas",
    "stage": "seed",
    "currency": "USD",
    "amount_scale": "UNITS",
}

SAMPLE_FINANCIALS = {
    "monthly_revenue": 45000.0,
    "gross_margin_pct": 75.0,
    "opex": 22000.0,
    "payroll": 40000.0,
    "other_costs": 10000.0,
    "cogs": 0.0,
    "marketing_expense": 0.0,
    "cash_balance": 750000.0,
    "headcount": 12,
    "customers": 40,
}


def sample_monthly_expenses(fin: dict | None = None) -> float:
    snap = fin or SAMPLE_FINANCIALS
    return (
        float(snap.get("opex") or 0)
        + float(snap.get("payroll") or 0)
        + float(snap.get("other_costs") or 0)
        + float(snap.get("cogs") or 0)
        + float(snap.get("marketing_expense") or 0)
    )


def derive_sample_insight(
    monthly_revenue: float | None = None,
    monthly_expenses: float | None = None,
    cash_balance: float | None = None,
) -> dict:
    """Return the labelled input → output pair shown on first run."""
    revenue = float(SAMPLE_FINANCIALS["monthly_revenue"] if monthly_revenue is None else monthly_revenue)
    expenses = float(sample_monthly_expenses() if monthly_expenses is None else monthly_expenses)
    cash = float(SAMPLE_FINANCIALS["cash_balance"] if cash_balance is None else cash_balance)
    burn = expenses - revenue
    runway = round(cash / burn, 1) if burn > 0 and cash > 0 else None
    return {
        "inputs": {
            "monthly_revenue": revenue,
            "monthly_expenses": expenses,
            "cash_balance": cash,
        },
        "outputs": {
            "monthly_burn": burn,
            "runway_months": runway,
        },
    }


def insight_from_record(record: Any) -> dict:
    expenses = sample_monthly_expenses(
        {
            "opex": record.opex,
            "payroll": record.payroll,
            "other_costs": record.other_costs,
            "cogs": record.cogs,
            "marketing_expense": record.marketing_expense,
        }
    )
    revenue = record.mrr or record.revenue or 0
    cash = record.cash_balance or 0
    return derive_sample_insight(revenue, expenses, cash)


def build_sample_months(n: int = 12) -> list[dict]:
    """Oldest-first monthly rows. The last row is the canonical snapshot."""
    snap = SAMPLE_FINANCIALS
    months: list[dict] = []
    for i in range(n):
        steps_from_latest = n - 1 - i
        rev_factor = 1.08 ** (-steps_from_latest)
        exp_factor = 1.02 ** (-steps_from_latest)
        months.append(
            {
                "monthly_revenue": round(snap["monthly_revenue"] * rev_factor, 2),
                "opex": round(snap["opex"] * exp_factor, 2),
                "payroll": round(snap["payroll"] * exp_factor, 2),
                "other_costs": round(snap["other_costs"] * exp_factor, 2),
                "cogs": 0.0,
                "marketing_expense": 0.0,
                "gross_margin_pct": snap["gross_margin_pct"],
                "headcount": snap["headcount"],
                "customers": max(8, int(snap["customers"] - steps_from_latest * 2)),
            }
        )
    months[-1] = {
        "monthly_revenue": snap["monthly_revenue"],
        "opex": snap["opex"],
        "payroll": snap["payroll"],
        "other_costs": snap["other_costs"],
        "cogs": snap["cogs"],
        "marketing_expense": snap["marketing_expense"],
        "gross_margin_pct": snap["gross_margin_pct"],
        "headcount": snap["headcount"],
        "customers": snap["customers"],
    }

    # Cash walks backward from the canonical latest balance so the number
    # on the first-insight card matches the seeded latest record.
    cashes = [0.0] * n
    cashes[-1] = snap["cash_balance"]
    for i in range(n - 2, -1, -1):
        nxt = months[i + 1]
        nxt_expenses = sample_monthly_expenses(nxt)
        nxt_burn = nxt_expenses - nxt["monthly_revenue"]
        cashes[i] = round(cashes[i + 1] + max(nxt_burn, 0), 2)
    for i, row in enumerate(months):
        row["cash_balance"] = cashes[i]
    return months


SAMPLE_SOURCE_TYPE = "sample"


def is_sample_source(source_type: Any) -> bool:
    return source_type == SAMPLE_SOURCE_TYPE


def _mark_company_sample(db, company) -> None:
    from server.core.company_metadata import save_metadata_value

    save_metadata_value(db, company, "is_sample", True, commit=False)


def financial_source_counts(db, company_id: int) -> tuple[int, int]:
    """Return (sample_count, real_count) for a company's financial records."""
    from server.models.financial import FinancialRecord

    rows = (
        db.query(FinancialRecord.source_type)
        .filter(FinancialRecord.company_id == company_id)
        .all()
    )
    sample = sum(1 for (source_type,) in rows if is_sample_source(source_type))
    return sample, len(rows) - sample


def replace_sample_financials(db, company_id: int) -> int:
    """Delete remaining ``source_type=sample`` rows. Caller owns the transaction."""
    from server.models.financial import FinancialRecord

    deleted = (
        db.query(FinancialRecord)
        .filter(
            FinancialRecord.company_id == company_id,
            FinancialRecord.source_type == SAMPLE_SOURCE_TYPE,
        )
        .delete(synchronize_session="fetch")
    )
    return int(deleted or 0)


def clear_is_sample(db, company_id: int, *, commit: bool = False) -> bool:
    """Clear ``metadata_json.is_sample`` only when real rows exist and no sample rows remain.

    Mixed leftover sample rows keep the flag on so the banner cannot claim
    "your numbers" while simulated records are still in the table.
    """
    from server.core.company_metadata import save_metadata_value
    from server.models.company import Company

    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None or not company.is_sample:
        return False
    sample_count, real_count = financial_source_counts(db, company_id)
    if real_count < 1 or sample_count > 0:
        return False
    save_metadata_value(db, company, "is_sample", False, commit=commit)
    return True


def on_real_financials_written(db, company_id: int, *, commit: bool = False) -> bool:
    """Atomic replace of sample rows, then clear ``is_sample`` if only real rows remain.

    Call after staging real (non-sample) ``FinancialRecord`` writes for
    ``company_id``, before the caller's commit. No-op when no real row is
    staged (so a /data click or empty upload cannot wipe sample). Mixed
    leftover sample rows after a failed replace keep the label on.
    """
    db.flush()
    _sample_count, real_count = financial_source_counts(db, company_id)
    if real_count < 1:
        return False
    replace_sample_financials(db, company_id)
    db.flush()
    return clear_is_sample(db, company_id, commit=commit)


def seed_sample_company(db, company_id: int, template: str = "saas_seed"):
    from server.models.financial import FinancialRecord

    company = None
    try:
        from server.models.company import Company

        company = db.query(Company).filter(Company.id == company_id).first()
    except Exception:
        company = None

    existing = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(FinancialRecord.period_end.desc())
        .all()
    )

    if existing:
        already_sample = bool(company.is_sample) if company is not None else False
        has_real = any(not is_sample_source(row.source_type) for row in existing)
        # A cleared real company (is_sample already false, or real rows present)
        # must not be re-labelled sample just because records exist.
        if has_real or not already_sample:
            insight = insight_from_record(existing[0])
            return {
                "already_seeded": True,
                "record_count": len(existing),
                "is_sample": already_sample,
                **insight,
            }
        if company is not None:
            _mark_company_sample(db, company)
            db.commit()
        insight = insight_from_record(existing[0])
        return {
            "already_seeded": True,
            "record_count": len(existing),
            "is_sample": True,
            **insight,
        }

    months = build_sample_months(12)
    base_date = datetime.now() - timedelta(days=30 * 11)

    for i, row in enumerate(months):
        month_date = base_date + timedelta(days=30 * i)
        revenue = row["monthly_revenue"]
        expenses = sample_monthly_expenses(row)
        net_burn = expenses - revenue
        cash = row["cash_balance"]
        customers = row["customers"]
        fin_record = FinancialRecord(
            company_id=company_id,
            period_start=month_date.date(),
            period_end=(month_date + timedelta(days=29)).date(),
            revenue=revenue,
            cogs=row["cogs"],
            opex=row["opex"],
            payroll=row["payroll"],
            other_costs=row["other_costs"],
            marketing_expense=row["marketing_expense"],
            cash_balance=cash,
            mrr=revenue,
            arr=round(revenue * 12, 2),
            gross_margin=row["gross_margin_pct"],
            customers=customers,
            ndr=108.0,
            arpu=round(revenue / customers, 2) if customers else 0,
            headcount=row["headcount"],
            net_burn=round(net_burn, 2),
            runway_months=round(cash / net_burn, 1) if net_burn > 0 else None,
            mom_growth=8.0 if i else 0.0,
            ltv=4800.0,
            cac=1500.0,
            ltv_cac_ratio=3.2,
            source_type=SAMPLE_SOURCE_TYPE,
            extraction_summary="Seeded sample data — not the founder's company.",
        )
        db.add(fin_record)

    if company is not None:
        _mark_company_sample(db, company)

    db.commit()
    insight = derive_sample_insight()
    logger.info(f"Seeded 12 sample financial records for company {company_id}")
    return {
        "already_seeded": False,
        "record_count": 12,
        "is_sample": True,
        **insight,
    }
