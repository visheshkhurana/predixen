from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)
from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.core.pagination import paginate, create_paginated_response
from server.models.user import User
from server.models.company import Company
from server.models.scenario import Scenario
from server.models.simulation_run import SimulationRun
from server.models.truth_scan import TruthScan
from server.models.financial import FinancialRecord
from server.simulate.simulation_engine import SimulationInputs, run_monte_carlo, run_multi_scenario_simulation, DEFAULT_SCENARIOS
from server.simulate.enhanced_engine import EnhancedSimulationEngine, compute_decision_scores
from server.simulate.enhanced_monte_carlo import (
    EnhancedSimulationInputs, 
    SimulationConfig, 
    run_enhanced_monte_carlo
)
from server.simulate.models import (
    EnrichedSimulationInputs,
    ScenarioDefinition,
    ScenarioEvent,
    WhatMustBeTrueReport
)
from dataclasses import asdict
from typing import Union

router = APIRouter(tags=["simulations"])


def extract_metric_value(metric: Any, default: float = 0) -> float:
    """
    Extract the raw numeric value from a metric.
    Metrics can be either:
    - A raw number (int or float)
    - A dict with {value, benchmark_percentile} structure
    """
    if metric is None:
        return default
    if isinstance(metric, dict):
        return float(metric.get("value", default))
    if isinstance(metric, (int, float)):
        return float(metric)
    return default

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
    churn_change_pct: float = 0
    cac_change_pct: float = 0
    tags: Optional[List[str]] = None
    overwrite_id: Optional[int] = None

    @validator('fundraise_amount')
    def validate_fundraise_amount(cls, v):
        if v < 0:
            raise ValueError('fundraise_amount must be >= 0')
        return v

    @validator('burn_reduction_pct')
    def validate_burn_reduction(cls, v):
        if v < -100 or v > 100:
            raise ValueError('burn_reduction_pct must be between -100 and 100')
        return v

    @validator('fundraise_month')
    def validate_fundraise_month(cls, v):
        if v is not None and v < 1:
            return 1
        return v

class SimulateRequest(BaseModel):
    n_sims: int = 500
    seed: Optional[int] = None

@router.post("/companies/{company_id}/scenarios", response_model=Dict[str, Any])
def create_scenario(
    company_id: int,
    request: ScenarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = get_user_company(db, company_id, current_user)
    
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

@router.get("/companies/{company_id}/scenarios")
def list_scenarios(
    company_id: int,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page (max 200)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List scenarios for a company with pagination.

    - **page**: Page number (1-indexed, default=1)
    - **page_size**: Items per page (default=50, max=200)
    """
    company = get_user_company(db, company_id, current_user)

    query = db.query(Scenario).filter(
        Scenario.company_id == company_id,
        Scenario.is_archived == 0
    ).order_by(Scenario.updated_at.desc() if hasattr(Scenario, 'updated_at') else Scenario.created_at.desc())

    # Apply pagination
    scenarios, total = paginate(query, page=page, page_size=page_size)

    result = []
    for s in scenarios:
        latest_run = s.get_latest_run()
        latest_sim = None
        summary = None
        if latest_run and latest_run.outputs_json:
            out = latest_run.outputs_json
            latest_sim = {
                "runway": out.get("runway"),
                "survival": out.get("survivalProbability", out.get("survival")),
                "survivalProbability": out.get("survivalProbability", out.get("survival")),
                "summary": out.get("summary"),
                "breakEvenMonth": out.get("breakEvenMonth"),
            }
            summary = out.get("summary")
        result.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "inputs": s.inputs_json,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            "version": s.version,
            "parent_id": s.parent_id,
            "tags": s.tags or [],
            "latest_simulation": latest_sim,
            "summary": summary,
        })

    return create_paginated_response(
        items=result,
        total=total,
        page=page,
        page_size=page_size
    )


INPUT_GUARDRAILS = {
    "pricing_change_pct": {"min": -50, "max": 100, "label": "Pricing change", "unit": "%"},
    "growth_uplift_pct": {"min": -30, "max": 50, "label": "Growth uplift", "unit": "%"},
    "burn_reduction_pct": {"min": -100, "max": 80, "label": "Burn reduction", "unit": "%"},
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
    
    company = get_user_company(db, original.company_id, current_user)
    
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
    
    company = get_user_company(db, scenario.company_id, current_user)
    
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
    
    company = get_user_company(db, scenario.company_id, current_user)
    
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
    
    company = get_user_company(db, scenario.company_id, current_user)
    
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


def _validate_simulation_output(inputs: 'EnhancedSimulationInputs', outputs: Dict[str, Any]) -> List[str]:
    warnings = []
    try:
        total_costs = inputs.opex + inputs.payroll + inputs.other_costs
        net_burn = total_costs - inputs.baseline_revenue
        simple_runway = inputs.cash_balance / net_burn if net_burn > 0 else 120
        sim_runway_p50 = outputs.get("runway", {}).get("p50", 0)

        burn_change = inputs.burn_reduction_pct
        is_adverse = burn_change < -20 or inputs.cac_change_pct > 15 or inputs.churn_change_pct > 5

        if is_adverse and sim_runway_p50 > simple_runway * 1.3 and sim_runway_p50 < 900:
            warnings.append(
                f"Adverse scenario shows {sim_runway_p50:.1f}mo runway vs "
                f"{simple_runway:.1f}mo simple calculation. "
                f"Revenue growth assumptions may be offsetting the adverse inputs."
            )

        if burn_change < -30:
            expected_burn = total_costs * (1 - burn_change / 100)
            expected_runway = inputs.cash_balance / max(expected_burn - inputs.baseline_revenue, 1)
            if sim_runway_p50 > expected_runway * 1.5 and sim_runway_p50 < 900:
                warnings.append(
                    f"Burn increased {abs(burn_change)}% but runway ({sim_runway_p50:.1f}mo) "
                    f"exceeds simple estimate ({expected_runway:.1f}mo). "
                    f"Growth projections may be overly optimistic."
                )

        if inputs.cac_change_pct > 15:
            eff_score = outputs.get("summary", {}).get("capital_efficiency_score", 0)
            if eff_score and eff_score >= 8:
                warnings.append(
                    f"CAC increased {inputs.cac_change_pct}% but capital efficiency "
                    f"score is {eff_score}/10. Verify growth assumptions justify higher acquisition costs."
                )
    except Exception as e:
        logger.warning(f"Simulation sanity check error: {e}")

    return warnings


@router.post("/scenarios/{scenario_id}/simulate", response_model=Dict[str, Any])
def run_simulation(
    scenario_id: int,
    request: SimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from server.utils.websocket_broadcast import broadcast_metric_update_sync
    
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    company = get_user_company(db, scenario.company_id, current_user)
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company.id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    scenario_inputs = scenario.inputs_json
    
    latest_record = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company.id
    ).order_by(FinancialRecord.period_end.desc()).first()
    
    ts_growth = extract_metric_value(metrics.get("revenue_growth_mom"), 0)
    fr_growth = float(latest_record.mom_growth) if latest_record and latest_record.mom_growth else 0
    baseline_growth = ts_growth if ts_growth != 0 else fr_growth
    
    ts_revenue = extract_metric_value(metrics.get("monthly_revenue"), 0)
    fr_revenue = float(latest_record.revenue) if latest_record and latest_record.revenue else 0
    baseline_revenue = ts_revenue if ts_revenue > 0 else fr_revenue
    
    ts_cash = extract_metric_value(metrics.get("cash_balance"), 0)
    fr_cash = float(latest_record.cash_balance) if latest_record and latest_record.cash_balance else 0
    baseline_cash = ts_cash if ts_cash > 0 else fr_cash
    
    fr_gm = float(latest_record.gross_margin) if latest_record and latest_record.gross_margin is not None else 0
    fr_opex = float(latest_record.opex) if latest_record and latest_record.opex else 0
    fr_payroll = float(latest_record.payroll) if latest_record and latest_record.payroll else 0
    fr_other = float(latest_record.other_costs) if latest_record and latest_record.other_costs else 0
    
    enhanced_inputs = EnhancedSimulationInputs(
        baseline_revenue=baseline_revenue,
        baseline_growth_rate=baseline_growth,
        gross_margin=extract_metric_value(metrics.get("gross_margin"), fr_gm),
        opex=extract_metric_value(metrics.get("opex"), fr_opex),
        payroll=extract_metric_value(metrics.get("payroll"), fr_payroll),
        other_costs=extract_metric_value(metrics.get("other_costs"), fr_other),
        cash_balance=baseline_cash,
        pricing_change_pct=scenario_inputs.get("pricing_change_pct", 0),
        growth_uplift_pct=scenario_inputs.get("growth_uplift_pct", 0),
        burn_reduction_pct=scenario_inputs.get("burn_reduction_pct", 0),
        fundraise_month=scenario_inputs.get("fundraise_month"),
        fundraise_amount=scenario_inputs.get("fundraise_amount", 0),
        gross_margin_delta_pct=scenario_inputs.get("gross_margin_delta_pct", 0),
        churn_change_pct=scenario_inputs.get("churn_change_pct", 0),
        cac_change_pct=scenario_inputs.get("cac_change_pct", 0),
    )
    
    sim_config = SimulationConfig(
        iterations=request.n_sims,
        horizon_months=24,
        seed=request.seed
    )
    
    outputs = run_enhanced_monte_carlo(enhanced_inputs, sim_config)
    
    sanity_warnings = _validate_simulation_output(enhanced_inputs, outputs)
    if sanity_warnings:
        outputs["sanity_warnings"] = sanity_warnings
    
    counter_moves_results = _run_counter_moves(scenario, metrics, latest_record)
    outputs["counter_moves"] = counter_moves_results
    
    fundraising_intel = _compute_fundraising_metrics(scenario, metrics, latest_record, outputs)
    if fundraising_intel:
        outputs["fundraising_intelligence"] = fundraising_intel
    
    sim_run = SimulationRun(
        scenario_id=scenario_id,
        n_sims=request.n_sims,
        seed=request.seed,
        outputs_json=outputs
    )
    db.add(sim_run)
    db.commit()
    db.refresh(sim_run)
    
    broadcast_metric_update_sync(
        company_id=company.id,
        metrics={
            "runway_months": outputs.get("runway", {}).get("p50", 0),
            "survival_12m": outputs.get("survival", {}).get("12m", 0),
            "survival_18m": outputs.get("survival", {}).get("18m", 0),
            "cash_balance": outputs.get("summary", {}).get("end_cash", 0),
            "monthly_revenue": enhanced_inputs.baseline_revenue,
            "gross_margin": enhanced_inputs.gross_margin,
            "net_burn": enhanced_inputs.opex + enhanced_inputs.payroll + enhanced_inputs.other_costs - enhanced_inputs.baseline_revenue,
        },
        source="simulation"
    )
    
    try:
        from server.api.metric_trends import save_simulation_snapshot
        save_simulation_snapshot(db, company.id, outputs)
    except Exception:
        pass
    
    return {
        "id": sim_run.id,
        "scenario_id": scenario_id,
        **outputs
    }


def _build_enhanced_inputs(scenario: Scenario, metrics: Dict, latest_record, overrides: Dict = None) -> EnhancedSimulationInputs:
    ts_growth = extract_metric_value(metrics.get("revenue_growth_mom"), 0)
    fr_growth = float(latest_record.mom_growth) if latest_record and latest_record.mom_growth else 0
    baseline_growth = ts_growth if ts_growth != 0 else fr_growth
    ts_revenue = extract_metric_value(metrics.get("monthly_revenue"), 0)
    fr_revenue = float(latest_record.revenue) if latest_record and latest_record.revenue else 0
    baseline_revenue = ts_revenue if ts_revenue > 0 else fr_revenue
    ts_cash = extract_metric_value(metrics.get("cash_balance"), 0)
    fr_cash = float(latest_record.cash_balance) if latest_record and latest_record.cash_balance else 0
    baseline_cash = ts_cash if ts_cash > 0 else fr_cash

    fr_gm = float(latest_record.gross_margin) if latest_record and latest_record.gross_margin is not None else 0
    fr_opex = float(latest_record.opex) if latest_record and latest_record.opex else 0
    fr_payroll = float(latest_record.payroll) if latest_record and latest_record.payroll else 0
    fr_other = float(latest_record.other_costs) if latest_record and latest_record.other_costs else 0

    si = scenario.inputs_json or {}
    if overrides:
        si = {**si, **overrides}

    return EnhancedSimulationInputs(
        baseline_revenue=baseline_revenue,
        baseline_growth_rate=baseline_growth,
        gross_margin=extract_metric_value(metrics.get("gross_margin"), fr_gm),
        opex=extract_metric_value(metrics.get("opex"), fr_opex),
        payroll=extract_metric_value(metrics.get("payroll"), fr_payroll),
        other_costs=extract_metric_value(metrics.get("other_costs"), fr_other),
        cash_balance=baseline_cash,
        pricing_change_pct=si.get("pricing_change_pct", 0),
        growth_uplift_pct=si.get("growth_uplift_pct", 0),
        burn_reduction_pct=si.get("burn_reduction_pct", 0),
        fundraise_month=si.get("fundraise_month"),
        fundraise_amount=si.get("fundraise_amount", 0),
        gross_margin_delta_pct=si.get("gross_margin_delta_pct", 0),
        churn_change_pct=si.get("churn_change_pct", 0),
        cac_change_pct=si.get("cac_change_pct", 0),
    )


def _compute_fundraising_metrics(
    scenario, 
    metrics: Dict, 
    latest_record, 
    simulation_outputs: Dict
) -> Optional[Dict[str, Any]]:
    """Compute fundraising intelligence metrics when scenario involves fundraising."""
    si = scenario.inputs_json or {}
    fundraise_amount = si.get("fundraise_amount", 0)
    fundraise_month = si.get("fundraise_month")
    
    if not fundraise_amount or fundraise_amount <= 0:
        return None
    
    ts_cash = extract_metric_value(metrics.get("cash_balance"), 0)
    fr_cash = float(latest_record.cash_balance) if latest_record and latest_record.cash_balance else 0
    current_cash = ts_cash if ts_cash > 0 else fr_cash
    
    ts_revenue = extract_metric_value(metrics.get("monthly_revenue"), 0)
    fr_revenue = float(latest_record.revenue) if latest_record and latest_record.revenue else 0
    monthly_revenue = ts_revenue if ts_revenue > 0 else fr_revenue
    
    fr_opex = float(latest_record.opex) if latest_record and latest_record.opex else 0
    fr_payroll = float(latest_record.payroll) if latest_record and latest_record.payroll else 0
    fr_other = float(latest_record.other_costs) if latest_record and latest_record.other_costs else 0
    fr_gm = float(latest_record.gross_margin) if latest_record and latest_record.gross_margin is not None else 0
    
    opex = extract_metric_value(metrics.get("opex"), fr_opex)
    payroll = extract_metric_value(metrics.get("payroll"), fr_payroll)
    other_costs = extract_metric_value(metrics.get("other_costs"), fr_other)
    gross_margin_pct = extract_metric_value(metrics.get("gross_margin"), fr_gm) / 100
    
    gross_profit = monthly_revenue * gross_margin_pct
    monthly_burn = max(0, opex + payroll + other_costs - gross_profit)
    
    pre_raise_runway = current_cash / monthly_burn if monthly_burn > 0 else 48
    post_raise_cash = current_cash + fundraise_amount
    post_raise_runway = post_raise_cash / monthly_burn if monthly_burn > 0 else 48
    runway_extension = post_raise_runway - pre_raise_runway
    
    annual_revenue = monthly_revenue * 12
    if annual_revenue > 0:
        valuation_low = annual_revenue * 8
        valuation_mid = annual_revenue * 12
        valuation_high = annual_revenue * 18
    else:
        valuation_low = fundraise_amount * 3
        valuation_mid = fundraise_amount * 5
        valuation_high = fundraise_amount * 8
    
    dilution_low = (fundraise_amount / (valuation_high + fundraise_amount)) * 100
    dilution_mid = (fundraise_amount / (valuation_mid + fundraise_amount)) * 100
    dilution_high = (fundraise_amount / (valuation_low + fundraise_amount)) * 100
    
    founder_ownership_pre = 100.0
    founder_ownership_post_low = founder_ownership_pre * (1 - dilution_low / 100)
    founder_ownership_post_mid = founder_ownership_pre * (1 - dilution_mid / 100)
    founder_ownership_post_high = founder_ownership_pre * (1 - dilution_high / 100)
    
    def _get_survival_18m(outputs: Dict) -> float:
        sp = outputs.get("survivalProbability", {})
        if isinstance(sp, dict) and "18m" in sp:
            return sp["18m"]
        sv = outputs.get("survival", {})
        if isinstance(sv, dict) and "18m" in sv:
            return sv["18m"]
        return 0
    
    survival_18m = _get_survival_18m(simulation_outputs)
    runway_p50 = simulation_outputs.get("runway", {}).get("p50", 0)
    
    no_raise_inputs = _build_enhanced_inputs(scenario, metrics, latest_record, overrides={"fundraise_amount": 0})
    no_raise_config = SimulationConfig(iterations=500, horizon_months=24, seed=42)
    try:
        no_raise_outputs = run_enhanced_monte_carlo(no_raise_inputs, no_raise_config)
        no_raise_survival = _get_survival_18m(no_raise_outputs)
        no_raise_runway = no_raise_outputs.get("runway", {}).get("p50", 0)
        survival_lift = survival_18m - no_raise_survival
        runway_lift = runway_p50 - no_raise_runway
    except Exception as e:
        logger.warning(f"No-raise simulation failed: {e}")
        survival_lift = 0
        runway_lift = runway_extension
    
    simulated_runway_ext = runway_lift if runway_lift > 0 else runway_extension
    capital_efficiency = simulated_runway_ext / (fundraise_amount / 1_000_000) if fundraise_amount > 0 else 0
    
    return {
        "fundraise_amount": fundraise_amount,
        "fundraise_month": fundraise_month,
        "dilution": {
            "low": round(dilution_low, 1),
            "mid": round(dilution_mid, 1),
            "high": round(dilution_high, 1),
        },
        "ownership_post_raise": {
            "best_case": round(founder_ownership_post_low, 1),
            "expected": round(founder_ownership_post_mid, 1),
            "worst_case": round(founder_ownership_post_high, 1),
        },
        "valuation_range": {
            "low": round(valuation_low),
            "mid": round(valuation_mid),
            "high": round(valuation_high),
        },
        "runway_extension_months": round(simulated_runway_ext, 1),
        "capital_efficiency": round(capital_efficiency, 1),
        "pre_raise_runway": round(pre_raise_runway, 1),
        "post_raise_runway": round(min(post_raise_runway, 48), 1),
        "monthly_burn": round(monthly_burn),
        "survival_lift_pct": round(survival_lift, 1),
        "runway_lift_months": round(runway_lift, 1),
    }


def _run_counter_moves(scenario, metrics: Dict, latest_record) -> list:
    """Run all counter-move simulations and return results list."""
    sim_config = SimulationConfig(iterations=500, horizon_months=24, seed=42)
    si = scenario.inputs_json or {}
    results = []
    for move in COUNTER_MOVES:
        try:
            merged = {}
            for key, val in move["overrides"].items():
                if key in move.get("additive_keys", []):
                    merged[key] = si.get(key, 0) + val
                else:
                    merged[key] = val
            enhanced = _build_enhanced_inputs(scenario, metrics, latest_record, overrides=merged)
            outputs = run_enhanced_monte_carlo(enhanced, sim_config)
            results.append({
                "id": move["id"],
                "name": move["name"],
                "description": move["description"],
                "icon": move["icon"],
                "overrides_applied": merged,
                "runway": outputs.get("runway"),
                "survival": outputs.get("survival", outputs.get("survivalProbability")),
                "survivalProbability": outputs.get("survivalProbability", outputs.get("survival")),
                "breakEvenMonth": outputs.get("breakEvenMonth"),
                "summary": outputs.get("summary"),
            })
        except Exception:
            pass
    return results


COUNTER_MOVES = [
    {
        "id": "cost_cut_20",
        "name": "Cut Costs 20%",
        "description": "Reduce operating expenses by 20% across the board",
        "icon": "scissors",
        "overrides": {"burn_reduction_pct": 20},
        "additive_keys": ["burn_reduction_pct"],
    },
    {
        "id": "raise_price_10",
        "name": "Raise Prices 10%",
        "description": "Increase pricing by 10% with expected minor churn impact",
        "icon": "dollar-sign",
        "overrides": {"pricing_change_pct": 10, "churn_change_pct": 1.5},
        "additive_keys": ["pricing_change_pct", "churn_change_pct"],
    },
    {
        "id": "reduce_hiring",
        "name": "Freeze Hiring",
        "description": "Pause all new hires, reducing payroll growth and burn",
        "icon": "user-minus",
        "overrides": {"burn_reduction_pct": 15, "growth_uplift_pct": -2},
        "additive_keys": ["burn_reduction_pct", "growth_uplift_pct"],
    },
]


@router.post("/scenarios/{scenario_id}/counter-moves", response_model=Dict[str, Any])
def simulate_counter_moves(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    company = get_user_company(db, scenario.company_id, current_user)

    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company.id
    ).order_by(TruthScan.created_at.desc()).first()
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")

    metrics = truth_scan.outputs_json.get("metrics", {})
    latest_record = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company.id
    ).order_by(FinancialRecord.period_end.desc()).first()

    sim_config = SimulationConfig(iterations=500, horizon_months=24, seed=42)
    si = scenario.inputs_json or {}

    results = []
    for move in COUNTER_MOVES:
        merged = {}
        for key, val in move["overrides"].items():
            if key in move.get("additive_keys", []):
                merged[key] = si.get(key, 0) + val
            else:
                merged[key] = val

        enhanced = _build_enhanced_inputs(scenario, metrics, latest_record, overrides=merged)
        outputs = run_enhanced_monte_carlo(enhanced, sim_config)

        results.append({
            "id": move["id"],
            "name": move["name"],
            "description": move["description"],
            "icon": move["icon"],
            "overrides_applied": merged,
            "runway": outputs.get("runway"),
            "survival": outputs.get("survival", outputs.get("survivalProbability")),
            "survivalProbability": outputs.get("survivalProbability", outputs.get("survival")),
            "breakEvenMonth": outputs.get("breakEvenMonth"),
            "summary": outputs.get("summary"),
        })

    return {"scenario_id": scenario_id, "counter_moves": results}


@router.get("/scenarios/{scenario_id}/simulation/latest", response_model=Dict[str, Any])
def get_latest_simulation(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    company = get_user_company(db, scenario.company_id, current_user)
    
    sim_run = db.query(SimulationRun).filter(
        SimulationRun.scenario_id == scenario_id
    ).order_by(SimulationRun.created_at.desc()).first()
    
    if not sim_run:
        raise HTTPException(status_code=404, detail="No simulation found")
    
    outputs = sim_run.outputs_json or {}
    
    if 'survivalProbability' not in outputs and 'survival' in outputs:
        survival = outputs['survival']
        if isinstance(survival, dict):
            sp = {}
            for k in ['6m', '12m', '18m', '24m']:
                if k in survival:
                    sp[k] = survival[k]
            if sp:
                outputs['survivalProbability'] = sp
            if 'curve' in survival and 'survivalCurve' not in outputs:
                outputs['survivalCurve'] = survival['curve']
    
    counter_moves_results = []
    if "counter_moves" in outputs:
        counter_moves_results = outputs.pop("counter_moves")
    else:
        try:
            truth_scan = db.query(TruthScan).filter(
                TruthScan.company_id == company.id
            ).order_by(TruthScan.created_at.desc()).first()
            if truth_scan:
                metrics = truth_scan.outputs_json.get("metrics", {})
                latest_record = db.query(FinancialRecord).filter(
                    FinancialRecord.company_id == company.id
                ).order_by(FinancialRecord.period_end.desc()).first()
                counter_moves_results = _run_counter_moves(scenario, metrics, latest_record)
        except Exception:
            pass

    fundraising_intel = outputs.pop("fundraising_intelligence", None)
    if fundraising_intel is None:
        try:
            truth_scan_fi = db.query(TruthScan).filter(
                TruthScan.company_id == company.id
            ).order_by(TruthScan.created_at.desc()).first()
            if truth_scan_fi:
                fi_metrics = truth_scan_fi.outputs_json.get("metrics", {})
                fi_record = db.query(FinancialRecord).filter(
                    FinancialRecord.company_id == company.id
                ).order_by(FinancialRecord.period_end.desc()).first()
                fundraising_intel = _compute_fundraising_metrics(scenario, fi_metrics, fi_record, outputs)
        except Exception:
            pass

    result = {
        "id": sim_run.id,
        "scenario_id": scenario_id,
        **outputs,
        "counter_moves": counter_moves_results,
        "created_at": sim_run.created_at.isoformat()
    }
    if fundraising_intel:
        result["fundraising_intelligence"] = fundraising_intel
    return result


@router.get("/scenarios/{scenario_id}/timeseries", response_model=Dict[str, Any])
def get_scenario_timeseries(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get month-by-month projection timeseries for the ProjectionChart component"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    company = get_user_company(db, scenario.company_id, current_user)
    
    sim_run = db.query(SimulationRun).filter(
        SimulationRun.scenario_id == scenario_id
    ).order_by(SimulationRun.created_at.desc()).first()
    
    if not sim_run:
        raise HTTPException(status_code=404, detail="No simulation found for this scenario")
    
    outputs = sim_run.outputs_json or {}
    metrics = outputs.get("metrics", {})
    revenue_data = metrics.get("revenue", [])
    cash_data = metrics.get("cash", [])
    burn_data = metrics.get("burn", [])
    scenario_inputs = scenario.inputs_json or {}
    
    horizon = max(len(revenue_data), len(cash_data), len(burn_data))
    
    timeseries = []
    for i in range(horizon):
        rev = revenue_data[i] if i < len(revenue_data) else {}
        cas = cash_data[i] if i < len(cash_data) else {}
        brn = burn_data[i] if i < len(burn_data) else {}
        
        cash_balance = cas.get("p50", 0)
        monthly_burn = brn.get("p50", 0)
        monthly_revenue = rev.get("p50", 0)
        runway_remaining = cash_balance / monthly_burn if monthly_burn > 0 else 48
        
        timeseries.append({
            "month": i + 1,
            "cashBalance": cash_balance,
            "monthlyBurn": monthly_burn,
            "monthlyRevenue": monthly_revenue,
            "runwayRemaining": min(runway_remaining, 48),
            "revenue_p10": rev.get("p10", 0),
            "revenue_p50": rev.get("p50", 0),
            "revenue_p90": rev.get("p90", 0),
            "cash_p10": cas.get("p10", 0),
            "cash_p50": cas.get("p50", 0),
            "cash_p90": cas.get("p90", 0),
            "burn_p10": brn.get("p10", 0),
            "burn_p50": brn.get("p50", 0),
            "burn_p90": brn.get("p90", 0),
        })
    
    funding_events = []
    fundraise_month = scenario_inputs.get("fundraise_month")
    fundraise_amount = scenario_inputs.get("fundraise_amount", 0)
    if fundraise_month is not None and fundraise_amount > 0:
        funding_events.append({
            "month": fundraise_month,
            "amount": fundraise_amount,
            "label": f"Funding: ${fundraise_amount/1000000:.1f}M" if fundraise_amount >= 1000000 else f"Funding: ${fundraise_amount/1000:.0f}K"
        })
    
    return {
        "scenario_id": scenario_id,
        "scenario_name": scenario.name,
        "timeseries": timeseries,
        "fundingEvents": funding_events,
        "summary": outputs.get("summary", {}),
        "runway": outputs.get("runway", {}),
        "survival": outputs.get("survivalProbability", outputs.get("survival", {}))
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
    company = get_user_company(db, company_id, current_user)
    
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
    company = get_user_company(db, company_id, current_user)
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    
    latest_record = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id
    ).order_by(FinancialRecord.period_end.desc()).first()
    
    fr_revenue = float(latest_record.revenue) if latest_record and latest_record.revenue else 0
    fr_growth = float(latest_record.mom_growth) if latest_record and latest_record.mom_growth else 0
    fr_gm = float(latest_record.gross_margin) if latest_record and latest_record.gross_margin is not None else 0
    fr_opex = float(latest_record.opex) if latest_record and latest_record.opex else 0
    fr_payroll = float(latest_record.payroll) if latest_record and latest_record.payroll else 0
    fr_other = float(latest_record.other_costs) if latest_record and latest_record.other_costs else 0
    fr_cash = float(latest_record.cash_balance) if latest_record and latest_record.cash_balance else 0
    
    base_inputs = SimulationInputs(
        baseline_revenue=extract_metric_value(metrics.get("monthly_revenue"), fr_revenue),
        baseline_growth_rate=extract_metric_value(metrics.get("revenue_growth_mom"), fr_growth),
        gross_margin=extract_metric_value(metrics.get("gross_margin"), fr_gm),
        opex=extract_metric_value(metrics.get("opex"), fr_opex),
        payroll=extract_metric_value(metrics.get("payroll"), fr_payroll),
        other_costs=extract_metric_value(metrics.get("other_costs"), fr_other),
        cash_balance=extract_metric_value(metrics.get("cash_balance"), fr_cash),
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
    n_sims: int = 500
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
    n_sims: int = 500
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
    company = get_user_company(db, company_id, current_user)
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    
    latest_record = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id
    ).order_by(FinancialRecord.period_end.desc()).first()
    
    fr_revenue = float(latest_record.revenue) if latest_record and latest_record.revenue else 0
    fr_growth = float(latest_record.mom_growth) if latest_record and latest_record.mom_growth else 0
    fr_gm = float(latest_record.gross_margin) if latest_record and latest_record.gross_margin is not None else 0
    fr_opex = float(latest_record.opex) if latest_record and latest_record.opex else 0
    fr_payroll = float(latest_record.payroll) if latest_record and latest_record.payroll else 0
    fr_other = float(latest_record.other_costs) if latest_record and latest_record.other_costs else 0
    fr_cash = float(latest_record.cash_balance) if latest_record and latest_record.cash_balance else 0
    
    inputs = EnrichedSimulationInputs(
        baseline_mrr=extract_metric_value(metrics.get("monthly_revenue"), fr_revenue),
        baseline_growth_rate=extract_metric_value(metrics.get("revenue_growth_mom"), fr_growth),
        gross_margin=extract_metric_value(metrics.get("gross_margin"), fr_gm),
        opex=extract_metric_value(metrics.get("opex"), fr_opex),
        payroll=extract_metric_value(metrics.get("payroll"), fr_payroll),
        other_costs=extract_metric_value(metrics.get("other_costs"), fr_other),
        cash_balance=extract_metric_value(metrics.get("cash_balance"), fr_cash),
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
    company = get_user_company(db, company_id, current_user)
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    
    latest_record = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id
    ).order_by(FinancialRecord.period_end.desc()).first()
    
    fr_revenue = float(latest_record.revenue) if latest_record and latest_record.revenue else 0
    fr_growth = float(latest_record.mom_growth) if latest_record and latest_record.mom_growth else 0
    fr_gm = float(latest_record.gross_margin) if latest_record and latest_record.gross_margin is not None else 0
    fr_opex = float(latest_record.opex) if latest_record and latest_record.opex else 0
    fr_payroll = float(latest_record.payroll) if latest_record and latest_record.payroll else 0
    fr_other = float(latest_record.other_costs) if latest_record and latest_record.other_costs else 0
    fr_cash = float(latest_record.cash_balance) if latest_record and latest_record.cash_balance else 0
    
    base_inputs = EnrichedSimulationInputs(
        baseline_mrr=extract_metric_value(metrics.get("monthly_revenue"), fr_revenue),
        baseline_growth_rate=extract_metric_value(metrics.get("revenue_growth_mom"), fr_growth),
        gross_margin=extract_metric_value(metrics.get("gross_margin"), fr_gm),
        opex=extract_metric_value(metrics.get("opex"), fr_opex),
        payroll=extract_metric_value(metrics.get("payroll"), fr_payroll),
        other_costs=extract_metric_value(metrics.get("other_costs"), fr_other),
        cash_balance=extract_metric_value(metrics.get("cash_balance"), fr_cash),
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
    
    score_map = {s.scenario_key: s for s in decision_scores}
    
    scenarios_output = {}
    for result in all_results:
        result.decision_score = score_map.get(result.scenario_key)
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
    company = get_user_company(db, company_id, current_user)
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    
    latest_record = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id
    ).order_by(FinancialRecord.period_end.desc()).first()
    
    fr_revenue = float(latest_record.revenue) if latest_record and latest_record.revenue else 0
    fr_growth = float(latest_record.mom_growth) if latest_record and latest_record.mom_growth else 0
    fr_gm = float(latest_record.gross_margin) if latest_record and latest_record.gross_margin is not None else 0
    fr_opex = float(latest_record.opex) if latest_record and latest_record.opex else 0
    fr_payroll = float(latest_record.payroll) if latest_record and latest_record.payroll else 0
    fr_other = float(latest_record.other_costs) if latest_record and latest_record.other_costs else 0
    fr_cash = float(latest_record.cash_balance) if latest_record and latest_record.cash_balance else 0
    
    inputs = EnrichedSimulationInputs(
        baseline_mrr=extract_metric_value(metrics.get("monthly_revenue"), fr_revenue),
        baseline_growth_rate=extract_metric_value(metrics.get("revenue_growth_mom"), fr_growth),
        gross_margin=extract_metric_value(metrics.get("gross_margin"), fr_gm),
        opex=extract_metric_value(metrics.get("opex"), fr_opex),
        payroll=extract_metric_value(metrics.get("payroll"), fr_payroll),
        other_costs=extract_metric_value(metrics.get("other_costs"), fr_other),
        cash_balance=extract_metric_value(metrics.get("cash_balance"), fr_cash),
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
        "total_gap": wmbt_report.total_gap,
        "key_drivers": [
            {
                "driver": d.driver,
                "impact_direction": d.impact_direction,
                "impact_magnitude": round(d.impact_magnitude * 100, 1),
                "threshold_value": d.threshold_value,
                "explanation": d.explanation,
                "current_value": d.current_value,
                "target_threshold": d.target_threshold,
                "recommended_change": d.recommended_change,
                "achievable": d.achievable,
                "gap_contribution": round(d.gap_contribution, 1),
                "benchmark_value": d.benchmark_value,
                "benchmark_comparison": d.benchmark_comparison
            }
            for d in wmbt_report.key_drivers
        ],
        "gap_breakdown": [
            {
                "driver": g.driver,
                "contribution_pct": g.contribution_pct,
                "absolute_contribution": g.absolute_contribution
            }
            for g in wmbt_report.gap_breakdown
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
    company = get_user_company(db, company_id, current_user)
    
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
