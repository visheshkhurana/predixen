from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from server.models.financial import FinancialRecord

logger = logging.getLogger(__name__)


def seed_sample_company(db: Session, company_id: int, template: str = "saas_seed"):
    existing = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id
    ).count()

    if existing > 0:
        return {"already_seeded": True, "record_count": existing}

    base_date = datetime.now() - timedelta(days=365)
    revenue = 45000.0
    expenses = 72000.0
    cash = 4500000.0

    for i in range(12):
        month_date = base_date + timedelta(days=30 * i)
        growth_rate = 1.08
        revenue = revenue * growth_rate
        expenses = expenses * 1.02
        cash = cash - (expenses - revenue)

        customers_count = 20 + i * 2
        headcount_val = 35 + (i // 4)
        mrr_val = round(revenue, 2)
        fin_record = FinancialRecord(
            company_id=company_id,
            period_start=month_date.date(),
            period_end=(month_date + timedelta(days=29)).date(),
            revenue=mrr_val,
            cogs=round(revenue * 0.22, 2),
            opex=round(expenses * 0.35, 2),
            payroll=round(expenses * 0.52, 2),
            other_costs=round(expenses * 0.13, 2),
            cash_balance=round(max(cash, 100000), 2),
            mrr=mrr_val,
            arr=round(mrr_val * 12, 2),
            gross_margin=78.0,
            customers=customers_count,
            ndr=108.0 + i * 0.3,
            arpu=round(mrr_val / customers_count, 2),
            headcount=headcount_val,
            net_burn=round(max(0, expenses - revenue), 2),
            runway_months=round(max(cash, 100000) / max(expenses - revenue, 1), 1),
            mom_growth=round((growth_rate - 1) * 100, 1),
            ltv=4800.0,
            cac=1500.0,
            ltv_cac_ratio=3.2,
        )
        db.add(fin_record)

    db.commit()
    logger.info(f"Seeded 12 sample financial records for company {company_id}")
    return {"already_seeded": False, "record_count": 12}
