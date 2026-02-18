from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.simulate.calibrator import InputCalibrator

router = APIRouter(tags=["calibration"])


class CalibrateRequest(BaseModel):
    raw_inputs: Dict[str, Any]
    sources: Optional[Dict[str, str]] = None
    industry: str = "saas"
    required_fields: Optional[List[str]] = None


class AutoCalibrateRequest(BaseModel):
    industry: Optional[str] = None


@router.post("/companies/{company_id}/calibrate", response_model=Dict[str, Any])
def calibrate_inputs(
    company_id: int,
    request: CalibrateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = get_user_company(db, company_id, current_user)
    
    calibrator = InputCalibrator(industry=request.industry)
    result = calibrator.calibrate(
        raw_inputs=request.raw_inputs,
        sources=request.sources,
        required_fields=request.required_fields
    )
    
    return calibrator.get_confidence_summary(result)


@router.post("/companies/{company_id}/auto-calibrate", response_model=Dict[str, Any])
def auto_calibrate_from_truth_scan(
    company_id: int,
    request: AutoCalibrateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = get_user_company(db, company_id, current_user)
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    
    raw_inputs = {
        "baseline_mrr": metrics.get("monthly_revenue"),
        "cash_balance": metrics.get("cash_balance"),
        "gross_margin": metrics.get("gross_margin"),
        "growth_rate": metrics.get("revenue_growth_mom"),
        "opex": metrics.get("opex"),
        "payroll": metrics.get("payroll"),
        "churn_rate": metrics.get("churn_rate"),
        "cac": metrics.get("cac"),
        "ltv_cac_ratio": metrics.get("ltv_cac_ratio"),
        "burn_multiple": metrics.get("burn_multiple"),
        "magic_number": metrics.get("magic_number"),
    }
    
    raw_inputs = {k: v for k, v in raw_inputs.items() if v is not None}
    
    sources = {
        key: "extracted" if truth_scan.outputs_json.get("data_confidence_score", 0) > 60 else "imputed"
        for key in raw_inputs.keys()
    }
    
    industry = request.industry or str(company.industry) if company.industry else "saas"
    calibrator = InputCalibrator(industry=str(industry))
    
    result = calibrator.calibrate(
        raw_inputs=raw_inputs,
        sources=sources
    )
    
    return {
        **calibrator.get_confidence_summary(result),
        "simulation_inputs": calibrator.to_simulation_inputs(result)
    }


@router.get("/industries/benchmarks", response_model=Dict[str, Any])
def get_industry_benchmarks(
    industry: str = "saas",
    current_user: User = Depends(get_current_user)
):
    from server.simulate.calibrator import INDUSTRY_BENCHMARKS
    
    benchmarks = INDUSTRY_BENCHMARKS.get(industry.lower(), INDUSTRY_BENCHMARKS["default"])
    
    return {
        "industry": industry,
        "benchmarks": benchmarks
    }
