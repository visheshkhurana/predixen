from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from server.core.db import get_db
from server.core.security import get_current_user, require_investor_mode
from server.core.config import settings
from server.models.user import User

router = APIRouter(prefix="/investor", tags=["investor"])

def check_investor_mode():
    if not settings.FEATURE_INVESTOR_MODE:
        raise HTTPException(
            status_code=403,
            detail="Investor mode is not enabled"
        )

@router.get("/diligence/{company_id}")
def get_diligence(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_investor_mode()
    return {"message": "Investor diligence endpoint", "company_id": company_id}

@router.get("/benchmarks/{company_id}")
def get_investor_benchmarks(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_investor_mode()
    return {"message": "Investor benchmarks endpoint", "company_id": company_id}

@router.get("/memo/{company_id}")
def get_investor_memo(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_investor_mode()
    return {"message": "Investor memo endpoint", "company_id": company_id}
