"""
Domain Router: /api/company
Aggregates company-related endpoints into a single domain.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company

router = APIRouter(prefix="/company", tags=["Company Domain"])


@router.get("/profile")
def get_company_profile(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    company = get_user_company(db, company_id, user)
    return {
        "id": company.id,
        "name": company.name,
        "industry": company.industry,
        "stage": company.stage,
        "description": getattr(company, "description", None),
    }


@router.get("/team")
def get_company_team(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from sqlalchemy import text
    rows = db.execute(
        text("SELECT id, name, email, role, department, status FROM team_members WHERE company_id = :cid"),
        {"cid": company_id},
    ).fetchall()
    return [{"id": r[0], "name": r[1], "email": r[2], "role": r[3], "department": r[4], "status": r[5]} for r in rows]


@router.get("/settings")
def get_company_settings(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    company = get_user_company(db, company_id, user)
    metadata = {}
    if hasattr(company, "metadata_json") and company.metadata_json:
        import json
        try:
            metadata = json.loads(company.metadata_json) if isinstance(company.metadata_json, str) else company.metadata_json
        except Exception:
            pass
    return {"company_id": company_id, "name": company.name, "settings": metadata}
