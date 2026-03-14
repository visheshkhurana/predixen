"""
Domain Router: /api/ai
Aggregates AI Copilot, governance, and agent endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company

router = APIRouter(prefix="/ai", tags=["AI Domain"])


@router.get("/agents")
def list_agents():
    from server.copilot.ai_governance import get_all_permissions
    return {"agents": get_all_permissions()}


@router.get("/agents/stats")
def agent_stats(company_id: int = Query(...), days: int = 7, db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from server.copilot.ai_governance import get_agent_stats
    return get_agent_stats(company_id=company_id, days=days)


@router.get("/governance/budgets")
def get_budgets(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from sqlalchemy import text
    rows = db.execute(
        text("SELECT agent_name, monthly_budget, usage FROM ai_agent_budgets WHERE company_id = :cid"),
        {"cid": company_id},
    ).fetchall()
    return [{"agent": r[0], "budget": r[1], "usage": r[2]} for r in rows]


@router.get("/flags")
def get_feature_flags(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from server.core.feature_flags import get_company_flags
    return {"flags": get_company_flags(company_id)}
