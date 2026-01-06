from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.scenario import Scenario
from server.models.simulation_run import SimulationRun
from server.models.truth_scan import TruthScan
from server.simulate.simulation_engine import SimulationInputs, run_monte_carlo

router = APIRouter(tags=["simulations"])

class HiringPlan(BaseModel):
    role: str
    count: int
    start_month: int
    monthly_cost: float

class ScenarioCreate(BaseModel):
    name: str
    pricing_change_pct: float = 0
    growth_uplift_pct: float = 0
    burn_reduction_pct: float = 0
    hiring_plan: List[HiringPlan] = []
    fundraise_month: Optional[int] = None
    fundraise_amount: float = 0
    gross_margin_delta_pct: float = 0

class SimulateRequest(BaseModel):
    n_sims: int = 1000
    seed: Optional[int] = None

@router.post("/companies/{company_id}/scenarios", response_model=Dict[str, Any])
def create_scenario(
    company_id: int,
    request: ScenarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    scenario = Scenario(
        company_id=company_id,
        name=request.name,
        inputs_json=request.model_dump()
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    return {
        "id": scenario.id,
        "name": scenario.name,
        "inputs": scenario.inputs_json
    }

@router.get("/companies/{company_id}/scenarios", response_model=List[Dict[str, Any]])
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
    
    scenarios = db.query(Scenario).filter(Scenario.company_id == company_id).all()
    
    return [
        {"id": s.id, "name": s.name, "inputs": s.inputs_json, "created_at": s.created_at.isoformat()}
        for s in scenarios
    ]

@router.post("/scenarios/{scenario_id}/simulate", response_model=Dict[str, Any])
def run_simulation(
    scenario_id: int,
    request: SimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    company = db.query(Company).filter(
        Company.id == scenario.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company.id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    scenario_inputs = scenario.inputs_json
    
    inputs = SimulationInputs(
        baseline_revenue=metrics.get("monthly_revenue", 50000),
        baseline_growth_rate=metrics.get("revenue_growth_mom", 5),
        gross_margin=metrics.get("gross_margin", 70),
        opex=metrics.get("opex", 20000),
        payroll=metrics.get("payroll", 30000),
        other_costs=metrics.get("other_costs", 5000),
        cash_balance=metrics.get("cash_balance", 500000),
        pricing_change_pct=scenario_inputs.get("pricing_change_pct", 0),
        growth_uplift_pct=scenario_inputs.get("growth_uplift_pct", 0),
        burn_reduction_pct=scenario_inputs.get("burn_reduction_pct", 0),
        hiring_plan=[h for h in scenario_inputs.get("hiring_plan", [])],
        fundraise_month=scenario_inputs.get("fundraise_month"),
        fundraise_amount=scenario_inputs.get("fundraise_amount", 0),
        gross_margin_delta_pct=scenario_inputs.get("gross_margin_delta_pct", 0),
        n_simulations=request.n_sims
    )
    
    outputs = run_monte_carlo(inputs, request.seed)
    
    sim_run = SimulationRun(
        scenario_id=scenario_id,
        n_sims=request.n_sims,
        seed=request.seed,
        outputs_json=outputs
    )
    db.add(sim_run)
    db.commit()
    db.refresh(sim_run)
    
    return {
        "id": sim_run.id,
        "scenario_id": scenario_id,
        **outputs
    }

@router.get("/scenarios/{scenario_id}/simulation/latest", response_model=Dict[str, Any])
def get_latest_simulation(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    company = db.query(Company).filter(
        Company.id == scenario.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    sim_run = db.query(SimulationRun).filter(
        SimulationRun.scenario_id == scenario_id
    ).order_by(SimulationRun.created_at.desc()).first()
    
    if not sim_run:
        raise HTTPException(status_code=404, detail="No simulation found")
    
    return {
        "id": sim_run.id,
        "scenario_id": scenario_id,
        **sim_run.outputs_json,
        "created_at": sim_run.created_at.isoformat()
    }
