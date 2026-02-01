from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid as uuid_lib

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.company_decision import CompanyScenario
from server.models.truth_scan import TruthScan

router = APIRouter(tags=["scenarios"])


class CreateScenarioRequest(BaseModel):
    name: str
    base_scenario_id: Optional[str] = None
    assumptions: Dict[str, Any] = {}
    baseline_diff: Optional[str] = None
    template_id: Optional[str] = None


class UpdateScenarioRequest(BaseModel):
    name: Optional[str] = None
    assumptions: Optional[Dict[str, Any]] = None


class ForkScenarioRequest(BaseModel):
    name: str
    assumptions: Dict[str, Any] = {}


@router.get("/companies/{company_id}/scenarios")
def list_scenarios(
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
    
    scenarios = db.query(CompanyScenario).filter(
        CompanyScenario.company_id == company_id
    ).order_by(CompanyScenario.created_at.desc()).all()
    
    return {
        "scenarios": [s.to_dict() for s in scenarios],
        "total": len(scenarios)
    }


@router.get("/companies/{company_id}/scenarios/{scenario_id}")
def get_scenario(
    company_id: int,
    scenario_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        scenario_uuid = uuid_lib.UUID(scenario_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scenario ID format")
    
    scenario = db.query(CompanyScenario).filter(
        CompanyScenario.id == scenario_uuid,
        CompanyScenario.company_id == company_id
    ).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return scenario.to_dict()


@router.post("/companies/{company_id}/scenarios")
def create_scenario(
    company_id: int,
    request: CreateScenarioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    base_uuid = None
    if request.base_scenario_id:
        try:
            base_uuid = uuid_lib.UUID(request.base_scenario_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid base scenario ID format")
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    outputs = compute_scenario_outputs(
        request.assumptions, 
        truth_scan.outputs_json if truth_scan else {}
    )
    
    outputs["baseline_diff"] = request.baseline_diff
    outputs["template_id"] = request.template_id
    
    scenario = CompanyScenario(
        company_id=company_id,
        name=request.name,
        base_scenario_id=base_uuid,
        assumptions_json=request.assumptions,
        outputs_json=outputs
    )
    
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    return scenario.to_dict()


@router.post("/companies/{company_id}/scenarios/{scenario_id}/fork")
def fork_scenario(
    company_id: int,
    scenario_id: str,
    request: ForkScenarioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        base_uuid = uuid_lib.UUID(scenario_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scenario ID format")
    
    base_scenario = db.query(CompanyScenario).filter(
        CompanyScenario.id == base_uuid,
        CompanyScenario.company_id == company_id
    ).first()
    
    if not base_scenario:
        raise HTTPException(status_code=404, detail="Base scenario not found")
    
    merged_assumptions = {
        **(base_scenario.assumptions_json or {}),
        **request.assumptions
    }
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    outputs = compute_scenario_outputs(
        merged_assumptions, 
        truth_scan.outputs_json if truth_scan else {}
    )
    
    forked = CompanyScenario(
        company_id=company_id,
        name=request.name,
        base_scenario_id=base_uuid,
        assumptions_json=merged_assumptions,
        outputs_json=outputs
    )
    
    db.add(forked)
    db.commit()
    db.refresh(forked)
    
    return forked.to_dict()


@router.patch("/companies/{company_id}/scenarios/{scenario_id}")
def update_scenario(
    company_id: int,
    scenario_id: str,
    request: UpdateScenarioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        scenario_uuid = uuid_lib.UUID(scenario_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scenario ID format")
    
    scenario = db.query(CompanyScenario).filter(
        CompanyScenario.id == scenario_uuid,
        CompanyScenario.company_id == company_id
    ).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    if request.name is not None:
        scenario.name = request.name
    
    if request.assumptions is not None:
        scenario.assumptions_json = request.assumptions
        truth_scan = db.query(TruthScan).filter(
            TruthScan.company_id == company_id
        ).order_by(TruthScan.created_at.desc()).first()
        
        prior_baseline_diff = scenario.outputs_json.get("baseline_diff") if scenario.outputs_json else None
        prior_template_id = scenario.outputs_json.get("template_id") if scenario.outputs_json else None
        
        new_outputs = compute_scenario_outputs(
            request.assumptions, 
            truth_scan.outputs_json if truth_scan else {}
        )
        
        if prior_baseline_diff:
            new_outputs["baseline_diff"] = prior_baseline_diff
        if prior_template_id:
            new_outputs["template_id"] = prior_template_id
        
        scenario.outputs_json = new_outputs
    
    scenario.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(scenario)
    
    return scenario.to_dict()


@router.delete("/companies/{company_id}/scenarios/{scenario_id}")
def delete_scenario(
    company_id: int,
    scenario_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        scenario_uuid = uuid_lib.UUID(scenario_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scenario ID format")
    
    scenario = db.query(CompanyScenario).filter(
        CompanyScenario.id == scenario_uuid,
        CompanyScenario.company_id == company_id
    ).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    forks = db.query(CompanyScenario).filter(
        CompanyScenario.base_scenario_id == scenario_uuid
    ).count()
    
    if forks > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete scenario with {forks} fork(s). Delete forks first."
        )
    
    db.delete(scenario)
    db.commit()
    
    return {"success": True, "message": "Scenario deleted"}


@router.get("/companies/{company_id}/scenarios/compare")
def compare_scenarios(
    company_id: int,
    scenario_ids: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    ids = [s.strip() for s in scenario_ids.split(",")]
    
    scenarios = []
    for sid in ids:
        try:
            suuid = uuid_lib.UUID(sid)
            scenario = db.query(CompanyScenario).filter(
                CompanyScenario.id == suuid,
                CompanyScenario.company_id == company_id
            ).first()
            if scenario:
                scenarios.append(scenario.to_dict())
        except ValueError:
            continue
    
    return {
        "scenarios": scenarios,
        "comparison": generate_comparison(scenarios)
    }


def compute_scenario_outputs(assumptions: Dict[str, Any], truth_data: Dict[str, Any]) -> Dict[str, Any]:
    metrics = truth_data.get("metrics", {})
    
    base_revenue = metrics.get("monthly_revenue", 50000)
    base_burn = metrics.get("net_burn", 30000)
    base_cash = metrics.get("cash_balance", 500000)
    base_growth = metrics.get("revenue_growth_mom", 5)
    
    revenue_change = assumptions.get("revenue_change_pct", 0)
    burn_change = assumptions.get("burn_change_pct", 0)
    raise_amount = assumptions.get("raise_usd", 0)
    cac_change = assumptions.get("cac_change_pct", 0)
    growth_change = assumptions.get("growth_change_pct", 0)
    
    new_revenue = base_revenue * (1 + revenue_change / 100)
    new_burn = base_burn * (1 + burn_change / 100)
    new_cash = base_cash + raise_amount
    new_growth = base_growth * (1 + growth_change / 100)
    
    runway = new_cash / new_burn if new_burn > 0 else 999
    
    year_1_revenue = 0
    monthly = new_revenue
    for i in range(12):
        year_1_revenue += monthly
        monthly *= (1 + new_growth / 100)
    
    return {
        "monthly_revenue": new_revenue,
        "annual_revenue_y1": year_1_revenue,
        "monthly_burn": new_burn,
        "cash_balance": new_cash,
        "runway_months": round(runway, 1),
        "growth_rate": new_growth,
        "assumptions_applied": assumptions
    }


def generate_comparison(scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(scenarios) < 2:
        return {"message": "Need at least 2 scenarios to compare"}
    
    metrics = ["runway_months", "monthly_revenue", "monthly_burn", "annual_revenue_y1", "growth_rate"]
    comparison = {}
    
    for metric in metrics:
        values = []
        for s in scenarios:
            outputs = s.get("outputs", {})
            values.append({
                "scenario": s.get("name"),
                "value": outputs.get(metric, "N/A")
            })
        comparison[metric] = values
    
    best = {}
    for metric in metrics:
        vals = [(s.get("name"), s.get("outputs", {}).get(metric, 0)) for s in scenarios]
        vals = [(n, v) for n, v in vals if isinstance(v, (int, float))]
        if vals:
            if metric == "monthly_burn":
                best[metric] = min(vals, key=lambda x: x[1])[0]
            else:
                best[metric] = max(vals, key=lambda x: x[1])[0]
    
    return {
        "metrics": comparison,
        "best_scenario_by_metric": best
    }
