from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.simulation_run import SimulationRun
from server.models.decision import Decision
from server.models.truth_scan import TruthScan
from server.decision.decision_engine import generate_recommendations
from server.simulate.simulation_engine import SimulationInputs

router = APIRouter(tags=["decisions"])

@router.post("/simulation/{run_id}/decisions/generate", response_model=Dict[str, Any])
def generate_decisions(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sim_run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    
    from server.models.scenario import Scenario
    scenario = db.query(Scenario).filter(Scenario.id == sim_run.scenario_id).first()
    
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
    confidence = truth_scan.outputs_json.get("data_confidence_score", 50)
    
    baseline_inputs = SimulationInputs(
        baseline_revenue=metrics.get("monthly_revenue", 50000),
        baseline_growth_rate=metrics.get("revenue_growth_mom", 5),
        gross_margin=metrics.get("gross_margin", 70),
        opex=metrics.get("opex", 20000),
        payroll=metrics.get("payroll", 30000),
        other_costs=metrics.get("other_costs", 5000),
        cash_balance=metrics.get("cash_balance", 500000),
        n_simulations=500
    )
    
    recommendations = generate_recommendations(metrics, confidence, baseline_inputs)
    
    decision = Decision(
        simulation_run_id=run_id,
        recommended_actions_json=recommendations
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    
    return {
        "id": decision.id,
        "simulation_run_id": run_id,
        "recommendations": recommendations
    }

@router.get("/companies/{company_id}/decisions/latest", response_model=Dict[str, Any])
def get_latest_decisions(
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
    
    from server.models.scenario import Scenario
    scenarios = db.query(Scenario).filter(Scenario.company_id == company_id).all()
    
    if not scenarios:
        raise HTTPException(status_code=404, detail="No scenarios found")
    
    latest_decision = None
    for scenario in scenarios:
        sim_runs = db.query(SimulationRun).filter(
            SimulationRun.scenario_id == scenario.id
        ).all()
        
        for run in sim_runs:
            decision = db.query(Decision).filter(
                Decision.simulation_run_id == run.id
            ).order_by(Decision.created_at.desc()).first()
            
            if decision:
                if latest_decision is None or decision.created_at > latest_decision.created_at:
                    latest_decision = decision
    
    if not latest_decision:
        raise HTTPException(status_code=404, detail="No decisions found")
    
    return {
        "id": latest_decision.id,
        "recommendations": latest_decision.recommended_actions_json,
        "created_at": latest_decision.created_at.isoformat()
    }
