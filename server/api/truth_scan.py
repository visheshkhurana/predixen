from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.truth.truth_scan import compute_truth_scan

router = APIRouter(tags=["truth"])

@router.post("/companies/{company_id}/truth/run", response_model=Dict[str, Any])
def run_truth_scan(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    outputs = compute_truth_scan(company, db)
    
    scan = TruthScan(
        company_id=company_id,
        outputs_json=outputs
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    
    return {
        "id": scan.id,
        **outputs
    }

@router.get("/companies/{company_id}/truth/latest", response_model=Dict[str, Any])
def get_latest_truth_scan(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if not scan:
        raise HTTPException(status_code=404, detail="No truth scan found. Run a scan first.")
    
    return {
        "id": scan.id,
        **scan.outputs_json,
        "created_at": scan.created_at.isoformat()
    }
