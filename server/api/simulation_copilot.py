"""
API endpoints for simulation copilot features.

Provides context-aware prompts during simulation setup and narrative summaries for results.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.services.simulation_copilot import (
    get_context_aware_prompt,
    generate_simulation_narrative,
    validate_assumption_value
)

router = APIRouter(prefix="/simulation-copilot", tags=["simulation-copilot"])


class AssumptionChangeRequest(BaseModel):
    """Request for context-aware prompt on assumption change."""
    assumption: str
    old_value: float
    new_value: float


class AssumptionPromptResponse(BaseModel):
    """Response with context-aware guidance."""
    prompt: str
    effects: List[Dict[str, Any]]
    recommendation: Optional[str]
    warning: Optional[str]
    delta: float
    impact_level: str


class NarrativeSummaryRequest(BaseModel):
    """Request for narrative summary of simulation results."""
    simulation_results: Dict[str, Any]
    scenario_params: Dict[str, Any]
    scenario_name: str = "Custom Scenario"


class NarrativeSummaryResponse(BaseModel):
    """Response with narrative summary."""
    summary: str
    health_status: str
    key_metrics: Dict[str, Any]
    drivers: List[Dict[str, Any]]
    insights: List[str]
    recommendations: List[str]


class ValidationRequest(BaseModel):
    """Request to validate an assumption value."""
    assumption: str
    value: float


class ValidationResponse(BaseModel):
    """Response with validation result."""
    is_valid: bool
    is_typical: bool
    warning: Optional[str]
    valid_range: List[float]
    typical_range: List[float]


@router.post("/prompt/{company_id}", response_model=AssumptionPromptResponse)
async def get_assumption_prompt(
    company_id: int,
    request: AssumptionChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a context-aware prompt explaining the impact of changing an assumption.
    
    This provides real-time AI guidance as users adjust simulation parameters.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    current_metrics = {}
    if truth_scan and truth_scan.metrics:
        metrics = truth_scan.metrics
        current_metrics = {
            "monthly_revenue": _extract_value(metrics.get("monthly_revenue")),
            "monthly_burn": _extract_value(metrics.get("net_burn")),
            "runway_months": _extract_value(metrics.get("runway_months")),
            "ltv_cac_ratio": _extract_value(metrics.get("ltv_cac_ratio")),
            "churn_rate": _extract_value(metrics.get("churn_rate")),
            "gross_margin": _extract_value(metrics.get("gross_margin")),
            "cash_balance": _extract_value(metrics.get("cash_balance")),
        }
    
    result = get_context_aware_prompt(
        assumption=request.assumption,
        old_value=request.old_value,
        new_value=request.new_value,
        current_metrics=current_metrics
    )
    
    return AssumptionPromptResponse(**result)


@router.post("/narrative/{company_id}", response_model=NarrativeSummaryResponse)
async def get_narrative_summary(
    company_id: int,
    request: NarrativeSummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a narrative summary explaining simulation results in plain language.
    
    This provides text summaries, key drivers, and actionable recommendations.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    company_metrics = {}
    if truth_scan and truth_scan.metrics:
        metrics = truth_scan.metrics
        company_metrics = {
            "monthly_revenue": _extract_value(metrics.get("monthly_revenue")),
            "monthly_burn": _extract_value(metrics.get("net_burn")),
            "runway_months": _extract_value(metrics.get("runway_months")),
            "cash_balance": _extract_value(metrics.get("cash_balance")),
        }
    
    result = generate_simulation_narrative(
        simulation_results=request.simulation_results,
        scenario_params=request.scenario_params,
        company_metrics=company_metrics,
        scenario_name=request.scenario_name
    )
    
    return NarrativeSummaryResponse(**result)


@router.post("/validate", response_model=ValidationResponse)
async def validate_assumption(request: ValidationRequest):
    """
    Validate an assumption value against typical and valid ranges.
    
    Returns warnings if the value is outside expected ranges.
    """
    result = validate_assumption_value(
        assumption=request.assumption,
        value=request.value
    )
    
    return ValidationResponse(
        is_valid=result["is_valid"],
        is_typical=result["is_typical"],
        warning=result["warning"],
        valid_range=list(result["valid_range"]),
        typical_range=list(result["typical_range"])
    )


def _extract_value(metric: Any) -> float:
    """Extract numeric value from metric which may be dict or number."""
    if metric is None:
        return 0
    if isinstance(metric, dict):
        return float(metric.get("value", 0))
    if isinstance(metric, (int, float)):
        return float(metric)
    return 0
