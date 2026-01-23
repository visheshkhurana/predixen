"""
API endpoints for Assumption Sets management.

Provides CRUD operations for assumption sets and access to strategy templates.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import hashlib
import json
import uuid
import logging

from server.core.db import get_db
from server.core.security import get_current_user
from server.models import User, Company
from server.models.assumption_set import AssumptionSetModel, SimulationCache
from server.models.financial import FinancialRecord
from server.simulate.assumptions import (
    AssumptionSet,
    AssumptionSetCreate,
    AssumptionSetUpdate,
    validate_assumption_set
)
from server.simulate.templates import (
    list_templates,
    get_template,
    create_from_template,
    StrategyTemplate
)


router = APIRouter(prefix="/simulator", tags=["simulator"])


def compute_cache_hash(assumptions: Dict, config: Optional[Dict] = None) -> str:
    """Compute a deterministic hash for caching."""
    data = json.dumps(assumptions, sort_keys=True)
    if config:
        data += json.dumps(config, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:64]


@router.post("/assumptions", response_model=Dict[str, Any])
async def create_assumption_set(
    company_id: int,
    request: AssumptionSetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new assumption set for a company.
    
    Can optionally be based on a template with custom overrides.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if request.template_id:
        assumption_set = create_from_template(
            template_id=request.template_id,
            name=request.name,
            overrides=request.model_dump(exclude_unset=True, exclude={"name", "template_id"})
        )
        if not assumption_set:
            raise HTTPException(status_code=400, detail=f"Template '{request.template_id}' not found")
    else:
        assumption_data = {"name": request.name}
        if request.description:
            assumption_data["description"] = request.description
        if request.revenue_growth:
            assumption_data["revenue_growth"] = request.revenue_growth
        if request.churn_rate:
            assumption_data["churn_rate"] = request.churn_rate
        if request.price_change:
            assumption_data["price_change"] = request.price_change
        if request.burn_reduction:
            assumption_data["burn_reduction"] = request.burn_reduction
        if request.headcount_plan:
            assumption_data["headcount_plan"] = request.headcount_plan
        if request.fundraise:
            assumption_data["fundraise"] = request.fundraise
        if request.capex:
            assumption_data["capex"] = request.capex
        if request.custom_fields:
            assumption_data["custom_fields"] = request.custom_fields
        if request.simulation_config:
            assumption_data["simulation_config"] = request.simulation_config
        assumption_set = AssumptionSet(**assumption_data)
    
    errors = validate_assumption_set(assumption_set)
    if errors:
        raise HTTPException(status_code=400, detail={"validation_errors": errors})
    
    assumptions_dict = assumption_set.model_dump()
    cache_hash = compute_cache_hash(assumptions_dict)
    
    db_model = AssumptionSetModel(
        company_id=company_id,
        name=assumption_set.name,
        description=assumption_set.description,
        template_id=request.template_id,
        assumptions_json=assumptions_dict,
        cache_hash=cache_hash,
        created_by=current_user.id
    )
    
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    
    return {
        "id": db_model.id,
        "name": db_model.name,
        "description": db_model.description,
        "template_id": db_model.template_id,
        "cache_hash": db_model.cache_hash,
        "assumptions": assumptions_dict,
        "created_at": db_model.created_at.isoformat() if db_model.created_at else None
    }


@router.get("/assumptions", response_model=List[Dict[str, Any]])
async def list_assumption_sets(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all assumption sets for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    assumption_sets = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.company_id == company_id
    ).order_by(AssumptionSetModel.created_at.desc()).all()
    
    return [
        {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "template_id": a.template_id,
            "cache_hash": a.cache_hash,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None
        }
        for a in assumption_sets
    ]


@router.get("/assumptions/{assumption_id}", response_model=Dict[str, Any])
async def get_assumption_set(
    assumption_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific assumption set with full details."""
    assumption = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.id == assumption_id
    ).first()
    
    if not assumption:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    company = db.query(Company).filter(
        Company.id == assumption.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "id": assumption.id,
        "name": assumption.name,
        "description": assumption.description,
        "template_id": assumption.template_id,
        "cache_hash": assumption.cache_hash,
        "assumptions": assumption.assumptions_json,
        "created_at": assumption.created_at.isoformat() if assumption.created_at else None,
        "updated_at": assumption.updated_at.isoformat() if assumption.updated_at else None
    }


@router.put("/assumptions/{assumption_id}", response_model=Dict[str, Any])
async def update_assumption_set(
    assumption_id: int,
    request: AssumptionSetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing assumption set."""
    assumption = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.id == assumption_id
    ).first()
    
    if not assumption:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    company = db.query(Company).filter(
        Company.id == assumption.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = request.model_dump(exclude_unset=True)
    current_assumptions: Dict[str, Any] = dict(assumption.assumptions_json) if assumption.assumptions_json else {}
    
    for key, value in update_data.items():
        if key in ["name", "description"]:
            setattr(assumption, key, value)
        elif value is not None:
            if hasattr(value, "model_dump"):
                current_assumptions[key] = value.model_dump()
            else:
                current_assumptions[key] = value
    
    assumption_set = AssumptionSet(**current_assumptions)
    errors = validate_assumption_set(assumption_set)
    if errors:
        raise HTTPException(status_code=400, detail={"validation_errors": errors})
    
    setattr(assumption, "assumptions_json", current_assumptions)
    setattr(assumption, "cache_hash", compute_cache_hash(current_assumptions))
    
    db.commit()
    db.refresh(assumption)
    
    return {
        "id": assumption.id,
        "name": assumption.name,
        "description": assumption.description,
        "template_id": assumption.template_id,
        "cache_hash": assumption.cache_hash,
        "assumptions": assumption.assumptions_json,
        "updated_at": assumption.updated_at.isoformat() if assumption.updated_at else None
    }


@router.delete("/assumptions/{assumption_id}")
async def delete_assumption_set(
    assumption_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an assumption set."""
    assumption = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.id == assumption_id
    ).first()
    
    if not assumption:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    company = db.query(Company).filter(
        Company.id == assumption.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete(assumption)
    db.commit()
    
    return {"message": "Assumption set deleted successfully"}


@router.get("/templates", response_model=List[Dict[str, Any]])
async def get_templates(
    category: Optional[str] = Query(None, description="Filter by category: growth, efficiency, survival, balanced")
):
    """
    List all available strategy templates.
    
    Templates are pre-configured assumption sets for common startup strategies.
    """
    templates = list_templates(category=category)
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "category": t.category,
            "tags": t.tags,
            "recommended_for": t.recommended_for
        }
        for t in templates
    ]


@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_template_details(template_id: str):
    """Get full details of a strategy template including assumptions."""
    template = get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "tags": template.tags,
        "recommended_for": template.recommended_for,
        "assumptions": template.assumptions.model_dump()
    }


logger = logging.getLogger(__name__)

_simulation_jobs: Dict[str, Dict[str, Any]] = {}


class SimulationRequest(BaseModel):
    assumption_set_id: int
    iterations: int = 1000
    horizon_months: int = 24
    use_cache: bool = True
    seed: Optional[int] = None


class OptimizationRequest(BaseModel):
    assumption_set_id: int
    target_metric: str = "runway"
    target_value: float = 18.0
    optimize_fields: List[str] = ["burn_reduction", "revenue_growth"]
    iterations: int = 500
    search_method: str = "random"


def run_simulation_job(
    job_id: str,
    assumption_set: AssumptionSetModel,
    config: Dict[str, Any],
    baseline_metrics: Dict[str, float]
):
    """Background task to run Monte Carlo simulation."""
    from server.simulate.transformer import transform_assumptions_to_inputs
    from server.simulate.enhanced_monte_carlo import run_enhanced_monte_carlo, SimulationConfig
    from server.simulate.assumptions import AssumptionSet
    
    try:
        _simulation_jobs[job_id]["status"] = "running"
        _simulation_jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
        
        assumptions = AssumptionSet(**assumption_set.assumptions_json)
        inputs = transform_assumptions_to_inputs(assumptions, baseline_metrics)
        
        sim_config = SimulationConfig(
            iterations=config.get("iterations", 1000),
            horizon_months=config.get("horizon_months", 24),
            seed=config.get("seed"),
            confidence_intervals=config.get("confidence_intervals", [10, 25, 50, 75, 90])
        )
        
        results = run_enhanced_monte_carlo(inputs, sim_config)
        
        _simulation_jobs[job_id]["status"] = "completed"
        _simulation_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        _simulation_jobs[job_id]["results"] = results
        
    except Exception as e:
        logger.error(f"Simulation job {job_id} failed: {str(e)}")
        _simulation_jobs[job_id]["status"] = "failed"
        _simulation_jobs[job_id]["error"] = str(e)


@router.post("/simulate", response_model=Dict[str, Any])
async def start_simulation(
    request: SimulationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a Monte Carlo simulation using the specified assumption set.
    
    Returns a job ID that can be used to poll for results.
    """
    assumption = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.id == request.assumption_set_id
    ).first()
    
    if not assumption:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    company = db.query(Company).filter(
        Company.id == assumption.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    config = {
        "iterations": request.iterations,
        "horizon_months": request.horizon_months,
        "seed": request.seed,
    }
    config_hash = compute_cache_hash(assumption.assumptions_json, config)
    
    if request.use_cache:
        cached = db.query(SimulationCache).filter(
            SimulationCache.cache_key == config_hash,
            SimulationCache.company_id == company.id
        ).first()
        
        if cached and not cached.is_expired:
            cached.hit_count = (cached.hit_count or 0) + 1
            db.commit()
            return {
                "job_id": f"cached-{cached.id}",
                "status": "completed",
                "cached": True,
                "results": cached.results_json
            }
    
    from server.truth.truth_scan import run_truth_scan
    from server.simulate.transformer import extract_baseline_from_truth_scan
    
    try:
        financials = db.query(FinancialRecord).filter(
            FinancialRecord.company_id == company.id
        ).order_by(FinancialRecord.period_end.desc()).limit(12).all()
        
        if financials:
            financial_dicts = [{"revenue": f.revenue, "cogs": f.cogs, "payroll": f.payroll, 
                               "operating_expenses": f.operating_expenses, "cash": f.cash} 
                              for f in financials]
            from server.simulate.transformer import extract_baseline_from_financials
            baseline_metrics = extract_baseline_from_financials(financial_dicts)
        else:
            baseline_metrics = {
                "revenue": 100000, "growth_rate": 5.0, "gross_margin": 70.0,
                "opex": 50000, "payroll": 100000, "other_costs": 20000,
                "cash": 1000000, "churn_rate": 5.0, "cac": 0, "ltv": 0
            }
    except Exception as e:
        logger.warning(f"Could not fetch financials: {e}")
        baseline_metrics = {
            "revenue": 100000, "growth_rate": 5.0, "gross_margin": 70.0,
            "opex": 50000, "payroll": 100000, "other_costs": 20000,
            "cash": 1000000, "churn_rate": 5.0, "cac": 0, "ltv": 0
        }
    
    job_id = str(uuid.uuid4())
    _simulation_jobs[job_id] = {
        "status": "pending",
        "assumption_set_id": request.assumption_set_id,
        "company_id": company.id,
        "user_id": current_user.id,
        "config": config,
        "cache_hash": config_hash,
        "created_at": datetime.utcnow().isoformat()
    }
    
    background_tasks.add_task(
        run_simulation_job,
        job_id,
        assumption,
        config,
        baseline_metrics
    )
    
    return {
        "job_id": job_id,
        "status": "pending",
        "cached": False
    }


@router.get("/simulate/{job_id}", response_model=Dict[str, Any])
async def get_simulation_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the status and results of a simulation job.
    """
    if job_id.startswith("cached-"):
        cache_id = int(job_id.replace("cached-", ""))
        cached = db.query(SimulationCache).filter(
            SimulationCache.id == cache_id
        ).first()
        
        if not cached:
            raise HTTPException(status_code=404, detail="Cached result not found")
        
        if cached.company_id:
            company = db.query(Company).filter(
                Company.id == cached.company_id,
                Company.user_id == current_user.id
            ).first()
            if not company:
                raise HTTPException(status_code=403, detail="Access denied")
        
        cached.hit_count = (cached.hit_count or 0) + 1
        db.commit()
        
        return {
            "job_id": job_id,
            "status": "completed",
            "cached": True,
            "results": cached.results_json
        }
    
    if job_id not in _simulation_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = _simulation_jobs[job_id]
    
    if job.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = {
        "job_id": job_id,
        "status": job["status"],
        "cached": False,
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at")
    }
    
    if job["status"] == "completed":
        response["results"] = job.get("results")
        
        existing_cache = db.query(SimulationCache).filter(
            SimulationCache.cache_key == job["cache_hash"]
        ).first()
        
        if not existing_cache:
            cache_entry = SimulationCache(
                assumption_set_id=job["assumption_set_id"],
                company_id=job["company_id"],
                cache_key=job["cache_hash"],
                config_json=job.get("config"),
                results_json=job["results"],
                iterations=job.get("config", {}).get("iterations", 1000),
                horizon_months=job.get("config", {}).get("horizon_months", 24),
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            db.add(cache_entry)
            db.commit()
        
    elif job["status"] == "failed":
        response["error"] = job.get("error")
    
    return response


@router.get("/metrics/{assumption_set_id}", response_model=Dict[str, Any])
async def get_simulation_metrics(
    assumption_set_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregated metrics from the most recent simulation for an assumption set.
    """
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
    
    if not cached:
        raise HTTPException(status_code=404, detail="No simulation results found. Run a simulation first.")
    
    results = cached.results_json
    
    summary = results.get("summary", {})
    percentiles = results.get("percentiles", {})
    
    return {
        "assumption_set_id": assumption_set_id,
        "assumption_set_name": assumption.name,
        "simulation_date": cached.created_at.isoformat() if cached.created_at else None,
        "metrics": {
            "runway": {
                "mean": summary.get("mean_runway_months"),
                "median": percentiles.get("runway", {}).get("p50"),
                "p10": percentiles.get("runway", {}).get("p10"),
                "p90": percentiles.get("runway", {}).get("p90"),
            },
            "survival_probability": summary.get("survival_rate"),
            "final_cash": {
                "mean": summary.get("mean_final_cash"),
                "p10": percentiles.get("cash", {}).get("p10"),
                "p50": percentiles.get("cash", {}).get("p50"),
                "p90": percentiles.get("cash", {}).get("p90"),
            },
            "final_revenue": {
                "mean": summary.get("mean_final_revenue"),
                "p10": percentiles.get("revenue", {}).get("p10"),
                "p50": percentiles.get("revenue", {}).get("p50"),
                "p90": percentiles.get("revenue", {}).get("p90"),
            },
            "growth_rate": {
                "mean": summary.get("mean_final_growth")
            }
        },
        "iterations": summary.get("iterations"),
        "horizon_months": summary.get("horizon_months")
    }



@router.post("/optimise", response_model=Dict[str, Any])
async def run_goal_optimization(
    request: OptimizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run goal-seeking optimization to find assumption configurations
    that achieve a target metric value.
    
    Uses grid, random, or Bayesian search methods to explore the
    assumption space and find optimal configurations.
    """
    from server.simulate.optimizer import run_optimization, OptimizationConfig
    from server.simulate.transformer import extract_baseline_from_financials
    
    assumption = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.id == request.assumption_set_id
    ).first()
    
    if not assumption:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    company = db.query(Company).filter(
        Company.id == assumption.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        financials = db.query(FinancialRecord).filter(
            FinancialRecord.company_id == company.id
        ).order_by(FinancialRecord.period_end.desc()).limit(12).all()
        
        if financials:
            financial_dicts = [{"revenue": f.revenue, "cogs": f.cogs, "payroll": f.payroll, 
                               "operating_expenses": f.operating_expenses, "cash": f.cash} 
                              for f in financials]
            baseline_metrics = extract_baseline_from_financials(financial_dicts)
        else:
            baseline_metrics = {
                "revenue": 100000, "growth_rate": 5.0, "gross_margin": 70.0,
                "opex": 50000, "payroll": 100000, "other_costs": 20000,
                "cash": 1000000, "churn_rate": 5.0, "cac": 0, "ltv": 0
            }
    except Exception as e:
        logger.warning(f"Could not fetch financials: {e}")
        baseline_metrics = {
            "revenue": 100000, "growth_rate": 5.0, "gross_margin": 70.0,
            "opex": 50000, "payroll": 100000, "other_costs": 20000,
            "cash": 1000000, "churn_rate": 5.0, "cac": 0, "ltv": 0
        }
    
    config = OptimizationConfig(
        target_metric=request.target_metric,
        target_value=request.target_value,
        optimize_fields=request.optimize_fields,
        max_iterations=request.iterations,
        search_method=request.search_method
    )
    
    assumptions = AssumptionSet(**assumption.assumptions_json)
    
    result = run_optimization(assumptions, baseline_metrics, config)
    
    return {
        "job_id": result.job_id,
        "status": result.status,
        "best_assumptions": result.best_assumptions,
        "best_metric_value": result.best_metric_value,
        "target_metric": request.target_metric,
        "target_value": request.target_value,
        "iterations_run": result.iterations_run,
        "convergence_history": result.convergence_history[-10:],
        "search_space": result.search_space,
        "elapsed_time_ms": result.elapsed_time_ms
    }


@router.get("/validate/{assumption_set_id}", response_model=Dict[str, Any])
async def validate_assumption_set_ranges(
    assumption_set_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate an assumption set for consistency and realistic ranges.
    """
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
    
    from server.simulate.assumptions import validate_assumption_set
    
    assumptions = AssumptionSet(**assumption.assumptions_json)
    errors = validate_assumption_set(assumptions)
    
    warnings = []
    
    if assumptions.revenue_growth:
        growth_mean = get_distribution_mean(assumptions.revenue_growth)
        if growth_mean > 30:
            warnings.append({
                "field": "revenue_growth",
                "message": f"Revenue growth of {growth_mean:.1f}% is aggressive for most stages"
            })
    
    if assumptions.burn_reduction:
        burn_mean = get_distribution_mean(assumptions.burn_reduction)
        if burn_mean > 25:
            warnings.append({
                "field": "burn_reduction",
                "message": f"Burn reduction of {burn_mean:.1f}% may be difficult to achieve"
            })
    
    if assumptions.churn_rate:
        churn_mean = get_distribution_mean(assumptions.churn_rate)
        if churn_mean > 10:
            warnings.append({
                "field": "churn_rate",
                "message": f"Churn rate of {churn_mean:.1f}% is high for B2B SaaS"
            })
    
    return {
        "assumption_set_id": assumption_set_id,
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def get_distribution_mean(dist) -> float:
    """Helper to get distribution mean."""
    from server.simulate.transformer import get_distribution_mean as _get_mean
    return _get_mean(dist)
