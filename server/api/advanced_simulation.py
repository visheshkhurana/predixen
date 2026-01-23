"""
Advanced Simulation API endpoints.

Provides:
- Macro-economic modifiers management
- Scenario versioning and comparison
- Sensitivity analysis
- Action recommendations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json

from server.core.db import get_db
from server.core.security import get_current_user
from server.models import User, Company, Scenario
from server.models.scenario_version import MacroEnvironment, SensitivityRun, Recommendation
from server.models.simulation_job import ScenarioVersion
from server.simulate.macro_modifiers import (
    MacroModifiers, MacroPreset, MACRO_PRESETS, 
    get_preset, list_presets, apply_macro_to_baseline
)

router = APIRouter(prefix="/simulator", tags=["advanced-simulation"])


class MacroModifiersRequest(BaseModel):
    preset: Optional[str] = None
    interest_rate: Optional[float] = Field(None, ge=0.0, le=0.25)
    inflation_rate: Optional[float] = Field(None, ge=-0.05, le=0.20)
    market_growth_factor: Optional[float] = Field(None, ge=0.5, le=2.0)
    currency_fx_rate: Optional[float] = Field(None, ge=0.1, le=10.0)
    credit_availability: Optional[float] = Field(None, ge=0.0, le=1.5)


class ScenarioVersionRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    change_notes: Optional[str] = None
    inputs_json: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


@router.get("/macros/presets", response_model=List[Dict[str, Any]])
async def get_macro_presets():
    """List all available macro-economic presets."""
    return list_presets()


@router.get("/macros/{company_id}", response_model=Dict[str, Any])
async def get_company_macro(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the active macro environment for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    active_macro = db.query(MacroEnvironment).filter(
        MacroEnvironment.company_id == company_id,
        MacroEnvironment.is_active == 1
    ).first()
    
    if not active_macro:
        default = MACRO_PRESETS[MacroPreset.NEUTRAL]
        return {
            "id": None,
            "preset": "neutral",
            "is_default": True,
            **default.model_dump()
        }
    
    return {
        "id": active_macro.id,
        "name": active_macro.name,
        "preset": active_macro.preset,
        "is_default": False,
        "interest_rate": float(active_macro.interest_rate) if active_macro.interest_rate else 0.05,
        "inflation_rate": float(active_macro.inflation_rate) if active_macro.inflation_rate else 0.03,
        "market_growth_factor": float(active_macro.market_growth_factor) if active_macro.market_growth_factor else 1.0,
        "currency_fx_rate": float(active_macro.currency_fx_rate) if active_macro.currency_fx_rate else 1.0,
        "credit_availability": float(active_macro.credit_availability) if active_macro.credit_availability else 1.0,
        "created_at": active_macro.created_at.isoformat() if active_macro.created_at else None,
        "updated_at": active_macro.updated_at.isoformat() if active_macro.updated_at else None
    }


@router.put("/macros/{company_id}", response_model=Dict[str, Any])
async def update_company_macro(
    company_id: int,
    request: MacroModifiersRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update or create macro environment for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if request.preset and request.preset != "custom":
        preset_config = get_preset(request.preset)
        values = preset_config.model_dump()
    else:
        values = {
            "interest_rate": request.interest_rate or 0.05,
            "inflation_rate": request.inflation_rate or 0.03,
            "market_growth_factor": request.market_growth_factor or 1.0,
            "currency_fx_rate": request.currency_fx_rate or 1.0,
            "credit_availability": request.credit_availability or 1.0,
        }
    
    db.query(MacroEnvironment).filter(
        MacroEnvironment.company_id == company_id
    ).update({"is_active": 0})
    
    macro = MacroEnvironment(
        company_id=company_id,
        name=request.preset or "custom",
        preset=request.preset or "custom",
        interest_rate=str(values["interest_rate"]),
        inflation_rate=str(values["inflation_rate"]),
        market_growth_factor=str(values["market_growth_factor"]),
        currency_fx_rate=str(values.get("currency_fx_rate", 1.0)),
        credit_availability=str(values.get("credit_availability", 1.0)),
        is_active=1
    )
    db.add(macro)
    db.commit()
    db.refresh(macro)
    
    return {
        "id": macro.id,
        "name": macro.name,
        "preset": macro.preset,
        "is_default": False,
        "interest_rate": float(macro.interest_rate) if macro.interest_rate else 0.05,
        "inflation_rate": float(macro.inflation_rate) if macro.inflation_rate else 0.03,
        "market_growth_factor": float(macro.market_growth_factor) if macro.market_growth_factor else 1.0,
        "currency_fx_rate": float(macro.currency_fx_rate) if macro.currency_fx_rate else 1.0,
        "credit_availability": float(macro.credit_availability) if macro.credit_availability else 1.0,
        "message": "Macro environment updated successfully"
    }


@router.get("/scenarios/{scenario_id}/versions", response_model=List[Dict[str, Any]])
async def list_scenario_versions(
    scenario_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all versions of a scenario."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    company = db.query(Company).filter(
        Company.id == scenario.company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    versions = db.query(ScenarioVersion).filter(
        ScenarioVersion.scenario_id == scenario_id
    ).order_by(ScenarioVersion.version.desc()).all()
    
    return [
        {
            "id": v.id,
            "version": v.version,
            "name": v.name,
            "description": v.description,
            "change_notes": v.change_notes,
            "created_by": v.created_by,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "tags": v.tags or []
        }
        for v in versions
    ]


@router.post("/scenarios/{scenario_id}/versions", response_model=Dict[str, Any])
async def create_scenario_version(
    scenario_id: int,
    request: ScenarioVersionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new version (snapshot) of a scenario."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    company = db.query(Company).filter(
        Company.id == scenario.company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    latest_version = db.query(ScenarioVersion).filter(
        ScenarioVersion.scenario_id == scenario_id
    ).order_by(ScenarioVersion.version.desc()).first()
    
    new_version_number = (latest_version.version + 1) if latest_version else 1
    
    version = ScenarioVersion(
        scenario_id=scenario_id,
        version=new_version_number,
        name=request.name or f"Version {new_version_number}",
        description=request.description or scenario.description,
        inputs_json=scenario.inputs_json or {},
        events_json=[],
        tags=request.tags or [],
        change_notes=request.change_notes,
        created_by=current_user.id
    )
    db.add(version)
    
    scenario.version = new_version_number
    
    db.commit()
    db.refresh(version)
    
    return {
        "id": version.id,
        "version": version.version,
        "name": version.name,
        "description": version.description,
        "change_notes": version.change_notes,
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "message": f"Version {new_version_number} created successfully"
    }


@router.post("/scenarios/{scenario_id}/clone", response_model=Dict[str, Any])
async def clone_scenario(
    scenario_id: int,
    request: ScenarioVersionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clone a scenario with updated assumptions, creating a new version."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    company = db.query(Company).filter(
        Company.id == scenario.company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    old_inputs = scenario.inputs_json or {}
    new_inputs = {**old_inputs, **(request.inputs_json or {})}
    
    new_version_number = (scenario.version or 0) + 1
    
    scenario.inputs_json = new_inputs
    if request.name:
        scenario.name = request.name
    if request.description:
        scenario.description = request.description
    if request.tags:
        scenario.tags = request.tags
    scenario.version = new_version_number
    scenario.updated_at = datetime.utcnow()
    
    version = ScenarioVersion(
        scenario_id=scenario_id,
        version=new_version_number,
        name=request.name or f"Version {new_version_number}",
        description=request.description or scenario.description,
        inputs_json=new_inputs,
        events_json=[],
        tags=request.tags or scenario.tags or [],
        change_notes=request.change_notes or "Cloned with updated assumptions",
        created_by=current_user.id
    )
    db.add(version)
    db.commit()
    db.refresh(scenario)
    db.refresh(version)
    
    return {
        "scenario_id": scenario.id,
        "version_id": version.id,
        "version": scenario.version,
        "name": scenario.name,
        "message": f"Scenario cloned to version {scenario.version}"
    }


@router.get("/scenarios/compare", response_model=Dict[str, Any])
async def compare_scenario_versions(
    scenario_id: int,
    from_version: int = Query(..., description="Source version number"),
    to_version: int = Query(..., description="Target version number"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compare two versions of a scenario."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    company = db.query(Company).filter(
        Company.id == scenario.company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    from_v = db.query(ScenarioVersion).filter(
        ScenarioVersion.scenario_id == scenario_id,
        ScenarioVersion.version == from_version
    ).first()
    
    to_v = db.query(ScenarioVersion).filter(
        ScenarioVersion.scenario_id == scenario_id,
        ScenarioVersion.version == to_version
    ).first()
    
    if not from_v or not to_v:
        raise HTTPException(status_code=404, detail="Version not found")
    
    from_inputs = from_v.inputs_json or {}
    to_inputs = to_v.inputs_json or {}
    diff = _compute_diff(from_inputs, to_inputs)
    
    return {
        "scenario_id": scenario_id,
        "from_version": {
            "number": from_version,
            "name": from_v.name,
            "created_at": from_v.created_at.isoformat() if from_v.created_at else None
        },
        "to_version": {
            "number": to_version,
            "name": to_v.name,
            "created_at": to_v.created_at.isoformat() if to_v.created_at else None
        },
        "diff": diff
    }


def _compute_diff(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the difference between two scenario inputs."""
    diff = {
        "added": {},
        "removed": {},
        "changed": {}
    }
    
    all_keys = set(old.keys()) | set(new.keys())
    
    for key in all_keys:
        old_val = old.get(key)
        new_val = new.get(key)
        
        if key not in old:
            diff["added"][key] = new_val
        elif key not in new:
            diff["removed"][key] = old_val
        elif old_val != new_val:
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                diff["changed"][key] = _compute_diff(old_val, new_val)
            else:
                diff["changed"][key] = {"from": old_val, "to": new_val}
    
    return diff


class SensitivityRequest(BaseModel):
    target_metric: str = Field(default="runway_months", description="Metric to analyze")
    perturbation_pct: float = Field(default=0.10, ge=0.01, le=0.50)
    iterations: int = Field(default=500, ge=100, le=2000)
    horizon_months: int = Field(default=24, ge=6, le=60)


@router.post("/sensitivity/{assumption_set_id}", response_model=Dict[str, Any])
async def run_sensitivity_analysis(
    assumption_set_id: int,
    request: SensitivityRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run sensitivity analysis on an assumption set.
    
    Uses OAT (One-At-a-Time) method to determine which assumptions
    have the greatest impact on the target metric.
    """
    from server.models.assumption_set import AssumptionSetModel
    from server.simulate.sensitivity import run_sensitivity_analysis as run_analysis
    from server.truth.truth_scan import run_truth_scan
    
    assumption = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.id == assumption_set_id
    ).first()
    
    if not assumption:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    company = db.query(Company).filter(
        Company.id == assumption.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    truth_scan = run_truth_scan(company.id, db)
    baseline_metrics = {
        "cash_balance": truth_scan.get("raw_values", {}).get("cash_balance", 100000),
        "monthly_revenue": truth_scan.get("raw_values", {}).get("monthly_revenue", 50000),
        "burn_rate": truth_scan.get("raw_values", {}).get("burn_rate", 60000),
        "runway_months": truth_scan.get("raw_values", {}).get("runway_months", 12),
        "gross_margin": truth_scan.get("raw_values", {}).get("gross_margin", 0.70),
        "churn_rate": truth_scan.get("raw_values", {}).get("churn_rate", 0.05)
    }
    
    results = run_analysis(
        assumptions_json=assumption.assumptions_json or {},
        baseline_metrics=baseline_metrics,
        target_metric=request.target_metric,
        perturbation_pct=request.perturbation_pct,
        iterations=request.iterations,
        horizon_months=request.horizon_months
    )
    
    sensitivity_run = SensitivityRun(
        company_id=company.id,
        target_metric=request.target_metric,
        perturbation_pct=str(request.perturbation_pct),
        results_json=results
    )
    db.add(sensitivity_run)
    db.commit()
    db.refresh(sensitivity_run)
    
    return {
        "id": sensitivity_run.id,
        "assumption_set_id": assumption_set_id,
        **results
    }


@router.get("/sensitivity/{run_id}/results", response_model=Dict[str, Any])
async def get_sensitivity_results(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the results of a sensitivity analysis run."""
    sensitivity_run = db.query(SensitivityRun).filter(
        SensitivityRun.id == run_id
    ).first()
    
    if not sensitivity_run:
        raise HTTPException(status_code=404, detail="Sensitivity run not found")
    
    company = db.query(Company).filter(
        Company.id == sensitivity_run.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "id": sensitivity_run.id,
        "company_id": sensitivity_run.company_id,
        "target_metric": sensitivity_run.target_metric,
        "perturbation_pct": float(sensitivity_run.perturbation_pct) if sensitivity_run.perturbation_pct else 0.10,
        "created_at": sensitivity_run.created_at.isoformat() if sensitivity_run.created_at else None,
        "results": sensitivity_run.results_json
    }


@router.post("/recommendations/{assumption_set_id}", response_model=Dict[str, Any])
async def generate_recommendations(
    assumption_set_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate action recommendations based on simulation results.
    
    Analyzes health metrics and suggests specific actions to improve
    financial outcomes.
    """
    from server.models.assumption_set import AssumptionSetModel, SimulationCache
    from server.simulate.recommendations import generate_recommendations as gen_recommendations
    from server.truth.truth_scan import run_truth_scan
    
    assumption = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.id == assumption_set_id
    ).first()
    
    if not assumption:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    company = db.query(Company).filter(
        Company.id == assumption.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    cached = db.query(SimulationCache).filter(
        SimulationCache.assumption_set_id == assumption_set_id
    ).order_by(SimulationCache.created_at.desc()).first()
    
    if cached and cached.results_json:
        simulation_results = cached.results_json
    else:
        from server.simulate.transformer import transform_assumptions_to_inputs
        from server.simulate.enhanced_monte_carlo import run_enhanced_monte_carlo
        
        truth_scan = run_truth_scan(company.id, db)
        baseline = {
            "cash_balance": truth_scan.get("raw_values", {}).get("cash_balance", 100000),
            "monthly_revenue": truth_scan.get("raw_values", {}).get("monthly_revenue", 50000),
            "burn_rate": truth_scan.get("raw_values", {}).get("burn_rate", 60000),
        }
        
        inputs = transform_assumptions_to_inputs(assumption.assumptions_json or {}, baseline)
        simulation_results = run_enhanced_monte_carlo(inputs=inputs, iterations=500)
    
    truth_scan = run_truth_scan(company.id, db)
    baseline_metrics = {
        "cash_balance": truth_scan.get("raw_values", {}).get("cash_balance", 100000),
        "monthly_revenue": truth_scan.get("raw_values", {}).get("monthly_revenue", 50000),
        "burn_rate": truth_scan.get("raw_values", {}).get("burn_rate", 60000),
        "gross_margin": truth_scan.get("raw_values", {}).get("gross_margin", 0.70),
        "churn_rate": truth_scan.get("raw_values", {}).get("churn_rate", 0.05)
    }
    
    recommendations_result = gen_recommendations(
        simulation_results=simulation_results,
        baseline_metrics=baseline_metrics,
        assumptions_json=assumption.assumptions_json
    )
    
    for rec in recommendations_result.get("recommendations", [])[:3]:
        rec_entry = Recommendation(
            company_id=company.id,
            recommendation_type=rec["type"],
            title=rec["title"],
            description=rec["description"],
            impact_json=rec.get("impact"),
            priority=["critical", "high", "medium", "low"].index(rec["priority"]) if rec["priority"] in ["critical", "high", "medium", "low"] else 2
        )
        db.add(rec_entry)
    db.commit()
    
    return {
        "assumption_set_id": assumption_set_id,
        "company_id": company.id,
        **recommendations_result
    }


@router.get("/recommendations/company/{company_id}", response_model=Dict[str, Any])
async def get_company_recommendations(
    company_id: int,
    limit: int = Query(default=10, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent recommendations for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    recommendations = db.query(Recommendation).filter(
        Recommendation.company_id == company_id
    ).order_by(Recommendation.created_at.desc()).limit(limit).all()
    
    return {
        "company_id": company_id,
        "recommendations": [
            {
                "id": r.id,
                "type": r.recommendation_type,
                "title": r.title,
                "description": r.description,
                "priority": r.priority,
                "status": r.status,
                "impact": r.impact_json,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in recommendations
        ],
        "total": len(recommendations)
    }


class ConstraintInput(BaseModel):
    metric: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class ConstrainedOptimizationRequest(BaseModel):
    target_metric: str = Field(default="runway", description="Primary metric to optimize")
    target_value: float = Field(default=18.0, description="Target value for primary metric")
    direction: str = Field(default="maximize", description="maximize or minimize")
    optimize_fields: List[str] = Field(
        default=["burn_reduction", "revenue_growth"],
        description="Fields to optimize"
    )
    constraints: List[ConstraintInput] = Field(
        default=[],
        description="Constraints on other metrics"
    )
    multi_objective: bool = Field(default=False, description="Use multi-objective optimization")
    objective_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Weights for multi-objective optimization"
    )
    max_iterations: int = Field(default=50, ge=10, le=200)
    simulation_iterations: int = Field(default=200, ge=100, le=1000)


SUPPORTED_OPTIMIZATION_METRICS = {"runway", "survival", "cash", "revenue", "growth", "dilution", "gross_margin", "burn_multiple"}


@router.post("/optimise/constrained/{assumption_set_id}", response_model=Dict[str, Any])
async def run_constrained_optimization(
    assumption_set_id: int,
    request: ConstrainedOptimizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run constrained optimization with multi-objective support.
    
    Finds optimal assumption configuration while respecting constraints
    on multiple metrics (e.g., maximize runway while keeping dilution < 20%).
    
    Supported metrics: runway, survival, cash, revenue, growth, dilution, gross_margin, burn_multiple
    """
    from server.models.assumption_set import AssumptionSetModel
    from server.simulate.optimizer import (
        constrained_random_search,
        OptimizationConfig,
        Constraint
    )
    from server.simulate.assumptions import AssumptionSet
    from server.truth.truth_scan import run_truth_scan
    
    if request.target_metric not in SUPPORTED_OPTIMIZATION_METRICS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid target_metric. Supported: {', '.join(SUPPORTED_OPTIMIZATION_METRICS)}"
        )
    
    for c in request.constraints:
        if c.metric not in SUPPORTED_OPTIMIZATION_METRICS:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid constraint metric '{c.metric}'. Supported: {', '.join(SUPPORTED_OPTIMIZATION_METRICS)}"
            )
    
    if request.objective_weights:
        invalid_weights = [k for k in request.objective_weights.keys() if k not in SUPPORTED_OPTIMIZATION_METRICS]
        if invalid_weights:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid objective_weights keys: {invalid_weights}. Supported: {', '.join(SUPPORTED_OPTIMIZATION_METRICS)}"
            )
    
    assumption = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.id == assumption_set_id
    ).first()
    
    if not assumption:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    company = db.query(Company).filter(
        Company.id == assumption.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    truth_scan = run_truth_scan(company.id, db)
    baseline_metrics = {
        "cash_balance": truth_scan.get("raw_values", {}).get("cash_balance", 100000),
        "monthly_revenue": truth_scan.get("raw_values", {}).get("monthly_revenue", 50000),
        "burn_rate": truth_scan.get("raw_values", {}).get("burn_rate", 60000),
        "gross_margin": truth_scan.get("raw_values", {}).get("gross_margin", 0.70),
        "churn_rate": truth_scan.get("raw_values", {}).get("churn_rate", 0.05)
    }
    
    constraints = [
        Constraint(
            metric=c.metric,
            min_value=c.min_value,
            max_value=c.max_value
        )
        for c in request.constraints
    ]
    
    config = OptimizationConfig(
        target_metric=request.target_metric,
        target_value=request.target_value,
        direction=request.direction,
        optimize_fields=request.optimize_fields,
        max_iterations=request.max_iterations,
        simulation_iterations=request.simulation_iterations,
        constraints=constraints,
        multi_objective=request.multi_objective,
        objective_weights=request.objective_weights or {}
    )
    
    assumptions = AssumptionSet(**(assumption.assumptions_json or {}))
    
    result = constrained_random_search(
        assumptions=assumptions,
        baseline_metrics=baseline_metrics,
        config=config
    )
    
    return {
        "job_id": result.job_id,
        "status": result.status,
        "assumption_set_id": assumption_set_id,
        "best_assumptions": result.best_assumptions,
        "best_metric_value": result.best_metric_value,
        "iterations_run": result.iterations_run,
        "elapsed_time_ms": result.elapsed_time_ms,
        "constraints_summary": getattr(result, 'constraints_summary', {}),
        "search_space": result.search_space,
        "convergence_history": result.convergence_history[-10:] if result.convergence_history else []
    }
