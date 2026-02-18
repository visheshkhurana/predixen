"""Data Health API for scoring data completeness and consistency."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.models.company import Company
from server.models.truth_scan import TruthScan

router = APIRouter(tags=["data-health"])


class DataHealthIssue(BaseModel):
    severity: str
    code: str
    message: str
    suggested_fix: str


class DataHealthCoverage(BaseModel):
    pnl_periods: int
    cash_periods: int
    balance_sheet_present: bool
    unit_econ_present: bool
    currency_consistent: bool


class DataHealthResponse(BaseModel):
    score: int
    grade: str
    issues: List[DataHealthIssue]
    coverage: DataHealthCoverage


def calculate_data_health(truth_scan: Optional[TruthScan]) -> Dict[str, Any]:
    """Calculate data health score based on completeness and consistency."""
    score = 100
    issues: List[Dict[str, str]] = []
    
    if not truth_scan:
        return {
            "score": 0,
            "grade": "F",
            "issues": [{
                "severity": "high",
                "code": "NO_TRUTH_SCAN",
                "message": "No financial data has been analyzed yet",
                "suggested_fix": "Upload financial documents or enter data manually"
            }],
            "coverage": {
                "pnl_periods": 0,
                "cash_periods": 0,
                "balance_sheet_present": False,
                "unit_econ_present": False,
                "currency_consistent": True
            }
        }
    
    outputs = truth_scan.outputs_json or {}
    metrics = outputs.get("metrics", {})
    
    pnl_periods = 0
    cash_periods = 0
    balance_sheet_present = False
    unit_econ_present = False
    currency_consistent = True
    
    if metrics.get("monthly_revenue"):
        pnl_periods = min(6, metrics.get("periods_analyzed", 6))
    
    has_cash = metrics.get("cash_balance") is not None
    if has_cash:
        cash_periods = min(6, pnl_periods)
    
    balance_sheet_present = has_cash or metrics.get("total_assets") is not None
    
    unit_econ_present = (
        metrics.get("cac") is not None or 
        metrics.get("ltv") is not None or
        metrics.get("arpu") is not None
    )
    
    if not metrics.get("monthly_revenue"):
        score -= 25
        issues.append({
            "severity": "high",
            "code": "MISSING_PNL_PERIODS",
            "message": "Missing revenue data for recent periods",
            "suggested_fix": "Upload P&L statement or enter monthly revenue manually"
        })
    
    if not metrics.get("gross_margin") and not metrics.get("cogs"):
        score -= 10
        issues.append({
            "severity": "medium",
            "code": "MISSING_COGS",
            "message": "Missing COGS or gross margin data",
            "suggested_fix": "Add cost of goods sold to calculate accurate margins"
        })
    
    if not metrics.get("opex") and not metrics.get("operating_expenses"):
        score -= 10
        issues.append({
            "severity": "medium",
            "code": "MISSING_OPEX",
            "message": "Missing operating expense breakdown",
            "suggested_fix": "Upload detailed expense report or enter OpEx categories"
        })
    
    if not has_cash:
        score -= 10
        issues.append({
            "severity": "high",
            "code": "MISSING_CASH",
            "message": "Missing cash balance data",
            "suggested_fix": "Enter current cash position to calculate runway"
        })
    
    if not metrics.get("net_burn") and not metrics.get("runway_months"):
        score -= 10
        issues.append({
            "severity": "high",
            "code": "NO_RUNWAY",
            "message": "Cannot compute burn rate or runway",
            "suggested_fix": "Provide monthly expenses and cash balance"
        })
    
    if outputs.get("currency_issues"):
        score -= 10
        currency_consistent = False
        issues.append({
            "severity": "medium",
            "code": "CURRENCY_MISMATCH",
            "message": "Currency inconsistencies detected (e.g., INR crore/lakh)",
            "suggested_fix": "Verify and normalize currency formatting"
        })
    
    if outputs.get("period_mismatch"):
        score -= 5
        issues.append({
            "severity": "low",
            "code": "PERIOD_MISMATCH",
            "message": "Fiscal year vs calendar year mismatch detected",
            "suggested_fix": "Confirm fiscal year end date in company settings"
        })
    
    if outputs.get("extraction_anomalies"):
        score -= 10
        issues.append({
            "severity": "medium",
            "code": "EXTRACTION_ANOMALIES",
            "message": "Data extraction anomalies detected (decimals/formatting)",
            "suggested_fix": "Review extracted numbers on verification page"
        })
    
    score = max(0, min(100, score))
    
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"
    
    return {
        "score": score,
        "grade": grade,
        "issues": issues,
        "coverage": {
            "pnl_periods": pnl_periods,
            "cash_periods": cash_periods,
            "balance_sheet_present": balance_sheet_present,
            "unit_econ_present": unit_econ_present,
            "currency_consistent": currency_consistent
        }
    }


@router.get("/companies/{company_id}/data-health", response_model=DataHealthResponse)
def get_data_health(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get data health score and issues for a company."""
    company = get_user_company(db, company_id, current_user)
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    health = calculate_data_health(truth_scan)
    return health
