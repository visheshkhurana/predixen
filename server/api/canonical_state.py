"""
Canonical State API - Single source of truth endpoints.

These endpoints provide the canonical company state used by all modules
to ensure data consistency across Overview, Truth Scan, Simulation, and Compare views.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
import json
from datetime import datetime

from server.core.db import get_db
from server.core.security import get_current_user
from server.models import Company, CompanyState, Scenario, SimulationRun
from server.models.company_state import compute_snapshot_id
from server.schemas.canonical import (
    CompanyStateSchema,
    CompanyStateUpdate,
    Financials,
    FundraisingRoundSummary,
    CreateScenarioRequest,
    UpdateScenarioRequest,
    RunSimulationRequest,
    RunSimulationResponse,
    ScenarioOverrides,
    SimulationInput,
    SimulationOutput,
    SimulationMetrics,
    PercentileMetric,
    Provenance,
    SimulationConfig,
)

router = APIRouter(prefix="/canonical", tags=["Canonical State"])


def get_or_create_company_state(db: Session, company_id: int) -> CompanyState:
    """Get existing company state or create from Truth Scan data."""
    state = db.query(CompanyState).filter(CompanyState.company_id == company_id).first()
    
    if state:
        return state
    
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    from server.models import TruthDataset
    truth_dataset = None
    if company.latest_truth_dataset_id:
        truth_dataset = db.query(TruthDataset).filter(
            TruthDataset.id == company.latest_truth_dataset_id
        ).first()
    
    financials = {}
    if truth_dataset and truth_dataset.financials_json:
        fin_data = truth_dataset.financials_json
        if isinstance(fin_data, str):
            fin_data = json.loads(fin_data)
        financials = {
            "cashBalance": fin_data.get("cash_balance", 0) or fin_data.get("cashBalance", 0),
            "monthlyBurn": fin_data.get("net_burn", 0) or fin_data.get("monthlyBurn", 0),
            "revenueMonthly": fin_data.get("revenue", 0) or fin_data.get("revenueMonthly", 0),
            "revenueGrowthRate": fin_data.get("growth_rate", 0) or fin_data.get("revenueGrowthRate", 0),
            "expensesMonthly": fin_data.get("total_expenses", 0) or fin_data.get("expensesMonthly", 0),
        }
    else:
        financials = {
            "cashBalance": 0,
            "monthlyBurn": 0,
            "revenueMonthly": 0,
            "revenueGrowthRate": 0,
            "expensesMonthly": 0,
        }
    
    snapshot_id = compute_snapshot_id(financials)
    state = CompanyState(
        company_id=company_id,
        environment="user",
        state_json=json.dumps(financials),
        snapshot_id=snapshot_id,
        cash_balance=int(financials.get("cashBalance", 0) or 0),
        monthly_burn=int(financials.get("monthlyBurn", 0) or 0),
        revenue_monthly=int(financials.get("revenueMonthly", 0) or 0),
        revenue_growth_rate=str(financials.get("revenueGrowthRate", 0) or 0),
        expenses_monthly=int(financials.get("expensesMonthly", 0) or 0),
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


@router.get("/companies/{company_id}/state")
async def get_company_state(
    company_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get the canonical company state - single source of truth for all modules.
    
    This endpoint is used by Overview, Truth Scan, Simulation, and Compare pages
    to ensure consistent data display across the application.
    """
    state = get_or_create_company_state(db, company_id)
    return state.to_dict()


@router.put("/companies/{company_id}/state")
async def update_company_state(
    company_id: int,
    update: CompanyStateUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update the canonical company state.
    
    This invalidates any queued/running simulation runs and updates the snapshot ID.
    All modules will reflect this change on next read.
    """
    state = get_or_create_company_state(db, company_id)
    
    if update.financials:
        financials = update.financials.model_dump()
        state.update_from_financials(financials)
    
    if update.fundraisingRounds:
        rounds_json = json.dumps([r.model_dump() for r in update.fundraisingRounds])
        state.fundraising_rounds_json = rounds_json
    
    db.query(SimulationRun).filter(
        SimulationRun.scenario_id.in_(
            db.query(Scenario.id).filter(Scenario.company_id == company_id)
        ),
        SimulationRun.status.in_(["queued", "running"])
    ).update({"status": "cancelled"}, synchronize_session=False)
    
    db.commit()
    db.refresh(state)
    
    return state.to_dict()


@router.get("/companies/{company_id}/scenarios")
async def list_scenarios(
    company_id: int,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all scenarios for a company."""
    query = db.query(Scenario).filter(Scenario.company_id == company_id)
    if not include_archived:
        query = query.filter(Scenario.is_archived == 0)
    
    scenarios = query.order_by(Scenario.updated_at.desc()).all()
    
    return [{
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "overrides": s.overrides_json or {},
        "version": s.version,
        "tags": s.tags or [],
        "createdAt": s.created_at.isoformat() if s.created_at else None,
        "updatedAt": s.updated_at.isoformat() if s.updated_at else None,
        "latestRunId": s.get_latest_run().id if s.get_latest_run() else None,
    } for s in scenarios]


@router.post("/companies/{company_id}/scenarios")
async def create_scenario(
    company_id: int,
    request: CreateScenarioRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new scenario with optional overrides."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    scenario = Scenario(
        company_id=company_id,
        name=request.name,
        description=request.description,
        inputs_json={},
        overrides_json=request.overrides.model_dump(exclude_none=True),
        tags=request.tags,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    return {
        "id": scenario.id,
        "name": scenario.name,
        "description": scenario.description,
        "overrides": scenario.overrides_json or {},
        "tags": scenario.tags or [],
    }


@router.put("/scenarios/{scenario_id}")
async def update_scenario(
    scenario_id: int,
    request: UpdateScenarioRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update an existing scenario."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    if request.name is not None:
        scenario.name = request.name
    if request.description is not None:
        scenario.description = request.description
    if request.overrides is not None:
        scenario.overrides_json = request.overrides.model_dump(exclude_none=True)
    if request.tags is not None:
        scenario.tags = request.tags
    
    scenario.version += 1
    db.commit()
    db.refresh(scenario)
    
    return {
        "id": scenario.id,
        "name": scenario.name,
        "description": scenario.description,
        "overrides": scenario.overrides_json or {},
        "version": scenario.version,
        "tags": scenario.tags or [],
    }


@router.get("/scenarios/{scenario_id}/runs/latest")
async def get_latest_run(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get the latest completed simulation run for a scenario."""
    run = db.query(SimulationRun).filter(
        SimulationRun.scenario_id == scenario_id,
        SimulationRun.status == "completed"
    ).order_by(SimulationRun.created_at.desc()).first()
    
    if not run:
        return {"status": "not_run", "message": "No completed runs found"}
    
    return run.to_dict()


@router.get("/runs/{run_id}")
async def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific simulation run by ID."""
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return run.to_dict()


@router.post("/companies/{company_id}/scenarios/{scenario_id}/run")
async def run_simulation(
    company_id: int,
    scenario_id: int,
    request: RunSimulationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Run a Monte Carlo simulation for a scenario.
    
    This creates a frozen snapshot of the current company state and scenario overrides,
    ensuring reproducibility and provenance tracking.
    """
    state = get_or_create_company_state(db, company_id)
    scenario = db.query(Scenario).filter(
        Scenario.id == scenario_id,
        Scenario.company_id == company_id
    ).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    base_financials = Financials(
        cashBalance=float(state.cash_balance or 0),
        monthlyBurn=float(state.monthly_burn or 0),
        revenueMonthly=float(state.revenue_monthly or 0),
        revenueGrowthRate=float(state.revenue_growth_rate or 0),
        expensesMonthly=float(state.expenses_monthly or 0),
    )
    
    overrides = ScenarioOverrides(**(scenario.overrides_json or {}))
    
    from server.schemas.canonical import compute_hash
    
    sim_input_dict = {
        "companyId": company_id,
        "scenarioId": scenario_id,
        "dataSnapshotId": state.snapshot_id,
        "asOf": datetime.utcnow().isoformat(),
        "base": base_financials.model_dump(),
        "overrides": overrides.model_dump(exclude_none=True),
        "config": request.config.model_dump(),
    }
    input_hash = compute_hash(sim_input_dict)
    sim_input_dict["inputHash"] = input_hash
    
    run = SimulationRun(
        scenario_id=scenario_id,
        n_sims=request.config.numPaths,
        seed=request.config.seed,
        data_snapshot_id=state.snapshot_id,
        inputs_json=sim_input_dict,
        status="running",
        outputs_json={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    try:
        from server.simulate.enhanced_monte_carlo import (
            run_enhanced_monte_carlo, 
            EnhancedSimulationInputs, 
            SimulationConfig
        )
        
        expense_mult = overrides.expenseMultiplier or 1.0
        growth_delta = overrides.revenueGrowthDelta or 0.0
        pricing_delta = overrides.pricingDelta or 0.0
        
        monthly_burn = base_financials.monthlyBurn or 0
        expenses = base_financials.expensesMonthly or monthly_burn
        revenue = base_financials.revenueMonthly or 0
        
        opex = expenses * 0.4 * expense_mult
        payroll = expenses * 0.5 * expense_mult
        other_costs = expenses * 0.1 * expense_mult
        
        base_growth = base_financials.revenueGrowthRate or 0.0
        gross_margin = 70.0 if revenue > 0 else 50.0
        
        sim_inputs = EnhancedSimulationInputs(
            baseline_revenue=float(revenue),
            baseline_growth_rate=float(base_growth) + growth_delta,
            gross_margin=gross_margin,
            opex=float(opex),
            payroll=float(payroll),
            other_costs=float(other_costs),
            cash_balance=float(base_financials.cashBalance or 0),
            pricing_change_pct=pricing_delta,
        )
        
        sim_config = SimulationConfig(
            iterations=request.config.numPaths,
            horizon_months=request.config.horizonMonths,
            seed=request.config.seed,
        )
        
        result = run_enhanced_monte_carlo(sim_inputs, sim_config)
        
        outputs = result if isinstance(result, dict) else result
        
        run.outputs_json = outputs
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        db.commit()
        
        return {
            "runId": run.id,
            "status": "completed",
            "dataSnapshotId": state.snapshot_id,
            "output": outputs,
        }
        
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        db.commit()
        
        return {
            "runId": run.id,
            "status": "failed",
            "error": str(e),
        }
