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
from server.simulate.simulation_engine import SimulationInputs, run_monte_carlo, run_multi_scenario_simulation, DEFAULT_SCENARIOS
from server.simulate.enhanced_engine import EnhancedSimulationEngine, compute_decision_scores
from server.simulate.models import (
    EnrichedSimulationInputs,
    ScenarioDefinition,
    ScenarioEvent,
    WhatMustBeTrueReport
)
from dataclasses import asdict

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
    
    scenarios = db.query(Scenario).filter(
        Scenario.company_id == company_id,
        Scenario.is_archived == 0
    ).all()
    
    return [
        {
            "id": s.id, 
            "name": s.name, 
            "description": s.description,
            "inputs": s.inputs_json, 
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            "version": s.version,
            "parent_id": s.parent_id,
            "tags": s.tags or []
        }
        for s in scenarios
    ]


INPUT_GUARDRAILS = {
    "pricing_change_pct": {"min": -50, "max": 100, "label": "Pricing change", "unit": "%"},
    "growth_uplift_pct": {"min": -30, "max": 50, "label": "Growth uplift", "unit": "%"},
    "burn_reduction_pct": {"min": 0, "max": 80, "label": "Burn reduction", "unit": "%"},
    "churn_rate": {"min": 0, "max": 30, "label": "Monthly churn rate", "unit": "%"},
    "gross_margin": {"min": 10, "max": 95, "label": "Gross margin", "unit": "%"},
    "cac": {"min": 0, "max": 50000, "label": "Customer acquisition cost", "unit": "$"},
    "fundraise_amount": {"min": 0, "max": 100000000, "label": "Fundraise amount", "unit": "$"},
}


def validate_inputs(inputs: Dict[str, Any]) -> List[Dict[str, str]]:
    warnings = []
    for key, limits in INPUT_GUARDRAILS.items():
        if key in inputs:
            value = inputs[key]
            unit = limits.get("unit", "")
            if value < limits["min"]:
                warnings.append({
                    "field": key,
                    "message": f"{limits['label']} cannot be below {unit}{limits['min']}" if unit == "$" else f"{limits['label']} cannot be below {limits['min']}{unit}",
                    "severity": "error"
                })
            if value > limits["max"]:
                warnings.append({
                    "field": key,
                    "message": f"{limits['label']} exceeds maximum of {unit}{limits['max']:,}" if unit == "$" else f"{limits['label']} exceeds maximum of {limits['max']}{unit}",
                    "severity": "warning"
                })
    return warnings


class ScenarioDuplicate(BaseModel):
    new_name: str


class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class ScenarioCommentCreate(BaseModel):
    content: str


@router.post("/scenarios/{scenario_id}/duplicate", response_model=Dict[str, Any])
def duplicate_scenario(
    scenario_id: int,
    request: ScenarioDuplicate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    original = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    company = db.query(Company).filter(
        Company.id == original.company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    new_scenario = Scenario(
        company_id=original.company_id,
        name=request.new_name,
        description=f"Duplicated from {original.name}",
        inputs_json=original.inputs_json.copy(),
        parent_id=original.id,
        version=1,
        tags=original.tags or []
    )
    db.add(new_scenario)
    db.commit()
    db.refresh(new_scenario)
    
    return {
        "id": new_scenario.id,
        "name": new_scenario.name,
        "parent_id": new_scenario.parent_id,
        "version": new_scenario.version
    }


@router.patch("/scenarios/{scenario_id}", response_model=Dict[str, Any])
def update_scenario(
    scenario_id: int,
    request: ScenarioUpdate,
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
    
    if request.name is not None:
        scenario.name = request.name
    if request.description is not None:
        scenario.description = request.description
    if request.tags is not None:
        scenario.tags = request.tags
    
    scenario.version = (scenario.version or 1) + 1
    db.commit()
    db.refresh(scenario)
    
    return {
        "id": scenario.id,
        "name": scenario.name,
        "description": scenario.description,
        "version": scenario.version,
        "tags": scenario.tags
    }


@router.delete("/scenarios/{scenario_id}")
def archive_scenario(
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
    
    scenario.is_archived = 1
    db.commit()
    
    return {"status": "archived", "id": scenario_id}


@router.get("/scenarios/{scenario_id}/versions", response_model=List[Dict[str, Any]])
def get_scenario_versions(
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
    
    root_id = scenario.parent_id or scenario.id
    versions = db.query(Scenario).filter(
        (Scenario.id == root_id) | (Scenario.parent_id == root_id)
    ).order_by(Scenario.created_at.desc()).all()
    
    return [
        {
            "id": v.id,
            "name": v.name,
            "version": v.version,
            "created_at": v.created_at.isoformat()
        }
        for v in versions
    ]


@router.get("/input-guardrails", response_model=Dict[str, Any])
def get_input_guardrails(
    current_user: User = Depends(get_current_user)
):
    return {"guardrails": INPUT_GUARDRAILS}


@router.post("/validate-inputs", response_model=Dict[str, Any])
def validate_scenario_inputs(
    inputs: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    warnings = validate_inputs(inputs)
    return {
        "valid": len([w for w in warnings if w["severity"] == "error"]) == 0,
        "warnings": warnings
    }


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
    
    outputs = sim_run.outputs_json or {}
    return {
        "id": sim_run.id,
        "scenario_id": scenario_id,
        **outputs,
        "created_at": sim_run.created_at.isoformat()
    }


class MultiScenarioRequest(BaseModel):
    n_sims: int = 500
    horizon_months: int = 24
    scenario_keys: Optional[List[str]] = None
    seed: Optional[int] = None


@router.get("/companies/{company_id}/default-scenarios", response_model=Dict[str, Any])
def get_default_scenarios(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return the list of default scenario definitions"""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "scenarios": [
            {"key": key, **params}
            for key, params in DEFAULT_SCENARIOS.items()
        ]
    }


@router.post("/companies/{company_id}/simulate-multi", response_model=Dict[str, Any])
def simulate_multiple_scenarios(
    company_id: int,
    request: MultiScenarioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run Monte Carlo simulation for multiple scenarios at once.
    Returns month-indexed P10/P50/P90 metrics for each scenario.
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
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    
    base_inputs = SimulationInputs(
        baseline_revenue=metrics.get("monthly_revenue", 50000),
        baseline_growth_rate=metrics.get("revenue_growth_mom", 5),
        gross_margin=metrics.get("gross_margin", 70),
        opex=metrics.get("opex", 20000),
        payroll=metrics.get("payroll", 30000),
        other_costs=metrics.get("other_costs", 5000),
        cash_balance=metrics.get("cash_balance", 500000),
        n_simulations=request.n_sims,
        horizon_months=request.horizon_months
    )
    
    scenarios_to_run = None
    if request.scenario_keys:
        scenarios_to_run = {
            key: DEFAULT_SCENARIOS[key]
            for key in request.scenario_keys
            if key in DEFAULT_SCENARIOS
        }
    
    results = run_multi_scenario_simulation(
        base_inputs=base_inputs,
        scenarios=scenarios_to_run,
        seed=request.seed
    )
    
    return results


class EnhancedSimulationRequest(BaseModel):
    n_sims: int = 1000
    horizon_months: int = 24
    starting_regime: str = "base"
    enable_regime_transitions: bool = True
    churn_rate: float = 3.0
    cac: float = 500.0
    dso: float = 45.0
    conversion_rate: float = 5.0
    headcount: int = 10
    total_customers: int = 100
    arpu: float = 500.0
    pipeline_value: float = 0.0
    seed: Optional[int] = None


class ScenarioEventInput(BaseModel):
    event_type: str
    start_month: int
    end_month: Optional[int] = None
    params: Dict[str, Any] = {}
    description: str = ""


class EnhancedScenarioInput(BaseModel):
    name: str
    description: str = ""
    events: List[ScenarioEventInput] = []
    starting_regime: str = "base"
    regime_override: Optional[str] = None


class EnhancedMultiScenarioRequest(BaseModel):
    n_sims: int = 1000
    horizon_months: int = 24
    starting_regime: str = "base"
    enable_regime_transitions: bool = True
    churn_rate: float = 3.0
    cac: float = 500.0
    dso: float = 45.0
    scenarios: List[EnhancedScenarioInput] = []
    include_sensitivity: bool = False
    seed: Optional[int] = None


@router.post("/companies/{company_id}/simulate-enhanced", response_model=Dict[str, Any])
def simulate_enhanced(
    company_id: int,
    request: EnhancedSimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run enhanced Monte Carlo simulation with regime-aware drivers and correlated sampling.
    Returns enriched results with regime distribution, monthly states, and survival curves.
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
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    
    inputs = EnrichedSimulationInputs(
        baseline_mrr=metrics.get("monthly_revenue", 50000),
        baseline_growth_rate=metrics.get("revenue_growth_mom", 5),
        gross_margin=metrics.get("gross_margin", 70),
        opex=metrics.get("opex", 20000),
        payroll=metrics.get("payroll", 30000),
        other_costs=metrics.get("other_costs", 5000),
        cash_balance=metrics.get("cash_balance", 500000),
        churn_rate=request.churn_rate,
        cac=request.cac,
        dso=request.dso,
        conversion_rate=request.conversion_rate,
        headcount=request.headcount,
        total_customers=request.total_customers,
        arpu=request.arpu,
        pipeline_value=request.pipeline_value,
        starting_regime=request.starting_regime,
        enable_regime_transitions=request.enable_regime_transitions,
        n_simulations=request.n_sims,
        horizon_months=request.horizon_months
    )
    
    engine = EnhancedSimulationEngine(inputs, seed=request.seed)
    result = engine.run_monte_carlo()
    
    return {
        "scenario_key": result.scenario_key,
        "scenario_name": result.scenario_name,
        "runway": result.runway,
        "survival": result.survival,
        "survival_curve": result.survival_curve,
        "bands": result.bands,
        "monthly_states": result.monthly_states,
        "regime_distribution": result.regime_distribution,
        "n_simulations": result.n_simulations,
        "horizon_months": result.horizon_months
    }


@router.post("/companies/{company_id}/simulate-scenarios-enhanced", response_model=Dict[str, Any])
def simulate_scenarios_enhanced(
    company_id: int,
    request: EnhancedMultiScenarioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run enhanced Monte Carlo simulation across multiple scenarios with decision ranking.
    Supports time-windowed events and optional sensitivity analysis.
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
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    
    base_inputs = EnrichedSimulationInputs(
        baseline_mrr=metrics.get("monthly_revenue", 50000),
        baseline_growth_rate=metrics.get("revenue_growth_mom", 5),
        gross_margin=metrics.get("gross_margin", 70),
        opex=metrics.get("opex", 20000),
        payroll=metrics.get("payroll", 30000),
        other_costs=metrics.get("other_costs", 5000),
        cash_balance=metrics.get("cash_balance", 500000),
        churn_rate=request.churn_rate,
        cac=request.cac,
        dso=request.dso,
        starting_regime=request.starting_regime,
        enable_regime_transitions=request.enable_regime_transitions,
        n_simulations=request.n_sims,
        horizon_months=request.horizon_months
    )
    
    scenarios_to_run = request.scenarios if request.scenarios else [
        EnhancedScenarioInput(name="Baseline", description="Current trajectory"),
        EnhancedScenarioInput(
            name="Cost Cutting",
            description="Reduce expenses by 20%",
            events=[ScenarioEventInput(
                event_type="cost_cut",
                start_month=1,
                params={"opex_reduction_pct": 20, "payroll_reduction_pct": 15}
            )]
        ),
        EnhancedScenarioInput(
            name="Growth Investment",
            description="Increase marketing spend for growth",
            events=[ScenarioEventInput(
                event_type="marketing_spend_change",
                start_month=1,
                params={"change_pct": 30}
            )]
        ),
    ]
    
    all_results = []
    
    for scenario_input in scenarios_to_run:
        engine = EnhancedSimulationEngine(base_inputs, seed=request.seed)
        
        scenario_def = ScenarioDefinition(
            name=scenario_input.name,
            description=scenario_input.description,
            events=[
                ScenarioEvent(
                    event_type=e.event_type,
                    start_month=e.start_month,
                    end_month=e.end_month,
                    params=e.params,
                    description=e.description
                )
                for e in scenario_input.events
            ],
            starting_regime=scenario_input.starting_regime,
            regime_override=scenario_input.regime_override
        )
        
        result = engine.run_monte_carlo(scenario_def)
        all_results.append(result)
    
    decision_scores = compute_decision_scores(all_results)
    
    scenarios_output = {}
    for i, result in enumerate(all_results):
        result.decision_score = decision_scores[i] if i < len(decision_scores) else None
        scenarios_output[result.scenario_key] = {
            "name": result.scenario_name,
            "runway": result.runway,
            "survival": result.survival,
            "survival_curve": result.survival_curve,
            "bands": result.bands,
            "monthly_states": result.monthly_states,
            "regime_distribution": result.regime_distribution,
            "decision_score": asdict(result.decision_score) if result.decision_score else None,
        }
    
    comparison = [
        {
            "key": s.scenario_key,
            "name": s.scenario_name,
            "runway_p50": s.runway["p50"],
            "survival_18m": s.survival.get("18m", 0),
            "composite_score": s.decision_score.composite_score if s.decision_score else 0,
            "rank": s.decision_score.rank if s.decision_score else 0
        }
        for s in all_results
    ]
    comparison.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
    
    sensitivity_report = None
    if request.include_sensitivity and all_results:
        baseline_result = all_results[0]
        engine = EnhancedSimulationEngine(base_inputs, seed=request.seed)
        wmbt_report = engine.compute_sensitivity(baseline_result)
        sensitivity_report = {
            "target_runway_months": wmbt_report.target_runway_months,
            "target_probability": wmbt_report.target_probability,
            "achievable": wmbt_report.achievable,
            "current_probability": wmbt_report.current_probability,
            "key_drivers": [asdict(d) for d in wmbt_report.key_drivers],
            "recommendations": wmbt_report.recommendations
        }
    
    return {
        "scenarios": scenarios_output,
        "comparison": comparison,
        "decision_ranking": [asdict(s) for s in decision_scores],
        "sensitivity": sensitivity_report,
        "n_simulations": request.n_sims,
        "horizon_months": request.horizon_months
    }


@router.post("/companies/{company_id}/sensitivity-analysis", response_model=Dict[str, Any])
def run_sensitivity_analysis(
    company_id: int,
    target_runway: int = 18,
    target_probability: float = 0.7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run driver sensitivity analysis to determine what must be true to achieve target runway.
    Returns key drivers, thresholds, and actionable recommendations.
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
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    
    inputs = EnrichedSimulationInputs(
        baseline_mrr=metrics.get("monthly_revenue", 50000),
        baseline_growth_rate=metrics.get("revenue_growth_mom", 5),
        gross_margin=metrics.get("gross_margin", 70),
        opex=metrics.get("opex", 20000),
        payroll=metrics.get("payroll", 30000),
        other_costs=metrics.get("other_costs", 5000),
        cash_balance=metrics.get("cash_balance", 500000),
        n_simulations=500,
        horizon_months=24
    )
    
    engine = EnhancedSimulationEngine(inputs)
    baseline_result = engine.run_monte_carlo()
    
    wmbt_report = engine.compute_sensitivity(
        baseline_result, 
        target_runway=target_runway,
        target_probability=target_probability
    )
    
    return {
        "target_runway_months": wmbt_report.target_runway_months,
        "target_probability": wmbt_report.target_probability,
        "achievable": wmbt_report.achievable,
        "current_probability": wmbt_report.current_probability,
        "key_drivers": [
            {
                "driver": d.driver,
                "impact_direction": d.impact_direction,
                "impact_magnitude": round(d.impact_magnitude * 100, 1),
                "threshold_value": d.threshold_value,
                "explanation": d.explanation
            }
            for d in wmbt_report.key_drivers
        ],
        "recommendations": wmbt_report.recommendations
    }


class RecommendationsRequest(BaseModel):
    runway_p50: float
    survival_18m: float
    current_burn: float = 50000
    current_revenue: float = 40000
    cash_balance: float = 500000
    target_runway: int = 18
    min_survival: float = 0.8


@router.post("/companies/{company_id}/recommendations", response_model=Dict[str, Any])
def generate_recommendations(
    company_id: int,
    request: RecommendationsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate actionable recommendations based on simulation results and benchmarks.
    Returns prioritized list of actions to improve runway and survival probability.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    recommendations = []
    priority = 1
    
    survival_rate = request.survival_18m / 100 if request.survival_18m > 1 else request.survival_18m
    meets_runway = request.runway_p50 >= request.target_runway
    meets_survival = survival_rate >= request.min_survival
    
    net_burn = request.current_burn - request.current_revenue
    
    if not meets_runway:
        runway_gap = max(0, request.target_runway - request.runway_p50)
        
        if net_burn > 0:
            if request.runway_p50 > 0:
                burn_cut_needed = min(30, (runway_gap / request.runway_p50) * 100 * 0.5)
            else:
                burn_cut_needed = 30
            recommendations.append({
                "priority": priority,
                "action": "Reduce burn rate",
                "description": f"Cut monthly burn by {burn_cut_needed:.0f}% to extend runway by ~{runway_gap:.1f} months",
                "impact": {"runway_gain_months": max(1, runway_gap * 0.5), "difficulty": "medium"},
                "category": "cost_reduction"
            })
            priority += 1
        
        fundraise_needed = max(100000, net_burn * runway_gap if net_burn > 0 else 500000)
        recommendations.append({
            "priority": priority,
            "action": "Raise bridge funding",
            "description": f"Raise ${fundraise_needed/1000:.0f}K to extend runway to {request.target_runway} months",
            "impact": {"runway_gain_months": max(1, runway_gap), "difficulty": "high"},
            "category": "fundraising"
        })
        priority += 1
    
    if not meets_survival:
        survival_gap = (request.min_survival - survival_rate) * 100
        
        recommendations.append({
            "priority": priority,
            "action": "Accelerate revenue growth",
            "description": f"Increase MoM growth by 3-5% to improve survival probability by ~{survival_gap:.0f}%",
            "impact": {"survival_improvement_pct": survival_gap * 0.6, "difficulty": "medium"},
            "category": "growth"
        })
        priority += 1
        
        recommendations.append({
            "priority": priority,
            "action": "Improve pricing",
            "description": "Increase prices by 10-15% to improve unit economics and extend runway",
            "impact": {"runway_gain_months": 2, "revenue_increase_pct": 10, "difficulty": "low"},
            "category": "pricing"
        })
        priority += 1
    
    if meets_runway and meets_survival:
        recommendations.append({
            "priority": 1,
            "action": "Maintain current trajectory",
            "description": f"Current path achieves {request.runway_p50:.1f} months runway with {survival_rate*100:.0f}% survival",
            "impact": {"status": "on_track"},
            "category": "maintain"
        })
    
    return {
        "company_id": company_id,
        "benchmarks": {
            "target_runway": request.target_runway,
            "min_survival": request.min_survival,
            "meets_runway": meets_runway,
            "meets_survival": meets_survival
        },
        "current_metrics": {
            "runway_p50": request.runway_p50,
            "survival_18m": survival_rate,
            "monthly_burn": request.current_burn,
            "monthly_revenue": request.current_revenue,
            "cash_balance": request.cash_balance
        },
        "recommendations": recommendations
    }


class ExplainRequest(BaseModel):
    runway_p50: float
    survival_12m: float
    survival_18m: float
    scenario_name: str = "Current Scenario"
    sensitivity: Optional[List[Dict[str, Any]]] = None
    decision_ranking: Optional[List[Dict[str, Any]]] = None


@router.post("/explain-simulation", response_model=Dict[str, Any])
def explain_simulation(
    request: ExplainRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate natural language explanations for simulation results."""
    from server.simulate.explainer import (
        generate_runway_explanation,
        generate_driver_impact_explanation,
        generate_decision_recommendation
    )
    
    explanations = {
        "summary": generate_runway_explanation(
            runway_p50=request.runway_p50,
            survival_12m=request.survival_12m,
            survival_18m=request.survival_18m,
            scenario_name=request.scenario_name
        )
    }
    
    if request.sensitivity:
        explanations["drivers"] = generate_driver_impact_explanation(request.sensitivity)
    
    if request.decision_ranking:
        explanations["recommendation"] = generate_decision_recommendation(request.decision_ranking)
    
    return explanations
