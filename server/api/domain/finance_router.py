"""
Domain Router: /api/finance
Aggregates financial endpoints — KPIs, records, confidence, cap table.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company

router = APIRouter(prefix="/finance", tags=["Finance Domain"])


@router.get("/kpis")
def get_financial_kpis(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from server.api.dashboard_kpis import compute_dashboard_kpis
    return compute_dashboard_kpis(db, company_id, user.id)


@router.get("/confidence")
def get_data_confidence(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from server.services.data_confidence import compute_all_confidence
    return compute_all_confidence(company_id)


@router.post("/confidence/refresh")
def refresh_confidence(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from server.services.data_confidence import save_confidence_scores
    return save_confidence_scores(company_id)


@router.get("/records")
def get_financial_records(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from sqlalchemy import text
    rows = db.execute(
        text("SELECT id, period, revenue, expenses, cash_balance, mrr, net_burn FROM financial_records WHERE company_id = :cid ORDER BY period_start DESC LIMIT 24"),
        {"cid": company_id},
    ).fetchall()
    return [
        {"id": r[0], "period": r[1], "revenue": r[2], "expenses": r[3], "cash_balance": r[4], "mrr": r[5], "net_burn": r[6]}
        for r in rows
    ]
