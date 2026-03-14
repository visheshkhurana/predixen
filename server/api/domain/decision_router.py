"""
Domain Router: /api/decisions
Aggregates decision engine endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company

router = APIRouter(prefix="/decisions", tags=["Decisions Domain"])


@router.get("/list")
def list_decisions(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from sqlalchemy import text
    rows = db.execute(
        text("SELECT id, title, status, confidence, created_at FROM company_decisions WHERE company_id = :cid ORDER BY created_at DESC"),
        {"cid": company_id},
    ).fetchall()
    return [{"id": r[0], "title": r[1], "status": r[2], "confidence": r[3], "created_at": r[4].isoformat() if r[4] else None} for r in rows]


@router.get("/patterns")
def get_decision_patterns(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from server.services.intelligence_graph import get_decision_patterns
    return get_decision_patterns(db, company_id)
