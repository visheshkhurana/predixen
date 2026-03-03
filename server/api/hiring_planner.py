from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import Dict, Any, List, Optional
import logging
import uuid
from datetime import datetime

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.models.financial import FinancialRecord
from server.api.simulations import extract_metric_value

logger = logging.getLogger(__name__)

router = APIRouter(tags=["hiring-planner"])


class HireItem(BaseModel):
    role_id: str
    role_title: str
    department: str
    count: int
    start_month: int
    monthly_salary: float
    location: str = "Remote US"

    @validator('count')
    def validate_count(cls, v):
        return max(1, min(v, 100))

    @validator('start_month')
    def validate_start_month(cls, v):
        return max(1, min(v, 12))

    @validator('monthly_salary')
    def validate_monthly_salary(cls, v):
        return max(0, min(v, 500000))


class HiringPlanCreate(BaseModel):
    name: str
    hires: List[HireItem] = []

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Plan name is required")
        return v.strip()

    @validator('hires')
    def validate_hires_size(cls, v):
        if len(v) > 50:
            return v[:50]
        return v


class HiringPlanUpdate(BaseModel):
    name: Optional[str] = None
    hires: Optional[List[HireItem]] = None

    @validator('hires')
    def validate_hires_size(cls, v):
        if v is not None and len(v) > 50:
            return v[:50]
        return v


def _get_hiring_plans(company: Company) -> List[Dict]:
    meta = company.metadata_json or {}
    return meta.get("hiring_plans", [])


def _save_hiring_plans(db: Session, company: Company, plans: List[Dict]):
    meta = dict(company.metadata_json or {})
    meta["hiring_plans"] = plans
    company.metadata_json = meta
    db.commit()


@router.get("/companies/{company_id}/hiring-plans")
def list_hiring_plans(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = get_user_company(db, company_id, current_user)
    plans = _get_hiring_plans(company)
    return {"plans": plans}


@router.post("/companies/{company_id}/hiring-plans")
def create_hiring_plan(
    company_id: int,
    request: HiringPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = get_user_company(db, company_id, current_user)
    plans = _get_hiring_plans(company)

    new_plan = {
        "id": str(uuid.uuid4()),
        "name": request.name,
        "hires": [h.model_dump() for h in request.hires],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    plans.append(new_plan)
    _save_hiring_plans(db, company, plans)

    return new_plan


@router.put("/companies/{company_id}/hiring-plans/{plan_id}")
def update_hiring_plan(
    company_id: int,
    plan_id: str,
    request: HiringPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = get_user_company(db, company_id, current_user)
    plans = _get_hiring_plans(company)

    plan_idx = next((i for i, p in enumerate(plans) if p.get("id") == plan_id), None)
    if plan_idx is None:
        raise HTTPException(status_code=404, detail="Hiring plan not found")

    plan = plans[plan_idx]
    if request.name is not None:
        plan["name"] = request.name
    if request.hires is not None:
        plan["hires"] = [h.model_dump() for h in request.hires]
    plan["updated_at"] = datetime.utcnow().isoformat()

    plans[plan_idx] = plan
    _save_hiring_plans(db, company, plans)

    return plan


@router.delete("/companies/{company_id}/hiring-plans/{plan_id}")
def delete_hiring_plan(
    company_id: int,
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = get_user_company(db, company_id, current_user)
    plans = _get_hiring_plans(company)

    original_len = len(plans)
    plans = [p for p in plans if p.get("id") != plan_id]
    if len(plans) == original_len:
        raise HTTPException(status_code=404, detail="Hiring plan not found")

    _save_hiring_plans(db, company, plans)
    return {"status": "deleted", "id": plan_id}


@router.post("/companies/{company_id}/hiring-plans/{plan_id}/simulate")
def simulate_hiring_plan(
    company_id: int,
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = get_user_company(db, company_id, current_user)
    plans = _get_hiring_plans(company)

    plan = next((p for p in plans if p.get("id") == plan_id), None)
    if plan is None:
        raise HTTPException(status_code=404, detail="Hiring plan not found")

    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company.id
    ).order_by(TruthScan.created_at.desc()).first()

    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first to get baseline metrics")

    metrics = truth_scan.outputs_json.get("metrics", {})

    latest_record = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company.id
    ).order_by(FinancialRecord.period_end.desc()).first()

    ts_revenue = extract_metric_value(metrics.get("monthly_revenue"), 0)
    fr_revenue = float(latest_record.revenue) if latest_record and latest_record.revenue else 0
    baseline_revenue = max(0, ts_revenue if ts_revenue > 0 else fr_revenue)

    ts_growth = extract_metric_value(metrics.get("revenue_growth_mom"), 0)
    fr_growth = float(latest_record.mom_growth) if latest_record and latest_record.mom_growth else 0
    baseline_growth = ts_growth if ts_growth != 0 else fr_growth

    ts_cash = extract_metric_value(metrics.get("cash_balance"), 0)
    fr_cash = float(latest_record.cash_balance) if latest_record and latest_record.cash_balance else 0
    baseline_cash = max(0, ts_cash if ts_cash > 0 else fr_cash)

    fr_gm = float(latest_record.gross_margin) if latest_record and latest_record.gross_margin is not None else 0
    fr_opex = max(0, float(latest_record.opex) if latest_record and latest_record.opex else 0)
    fr_payroll = max(0, float(latest_record.payroll) if latest_record and latest_record.payroll else 0)
    fr_other = max(0, float(latest_record.other_costs) if latest_record and latest_record.other_costs else 0)

    hires = plan.get("hires", [])
    hiring_plan_for_sim = []
    for hire in hires:
        hiring_plan_for_sim.append({
            "role": hire.get("role_title", "Unknown"),
            "count": hire.get("count", 1),
            "start_month": hire.get("start_month", 1),
            "monthly_cost": hire.get("monthly_salary", 0) * hire.get("count", 1),
        })

    total_monthly_cost_increase = sum(
        h.get("monthly_salary", 0) * h.get("count", 1) for h in hires
    )

    try:
        from server.simulate.simulation_engine import SimulationInputs, run_monte_carlo

        sim_inputs = SimulationInputs(
            baseline_revenue=baseline_revenue,
            baseline_growth_rate=baseline_growth,
            gross_margin=extract_metric_value(metrics.get("gross_margin"), fr_gm),
            opex=extract_metric_value(metrics.get("opex"), fr_opex),
            payroll=extract_metric_value(metrics.get("payroll"), fr_payroll),
            other_costs=extract_metric_value(metrics.get("other_costs"), fr_other),
            cash_balance=baseline_cash,
            hiring_plan=hiring_plan_for_sim,
            n_simulations=500,
            horizon_months=24,
        )

        outputs = run_monte_carlo(sim_inputs)

        total_costs = fr_opex + fr_payroll + fr_other
        net_burn = total_costs - baseline_revenue
        current_runway = baseline_cash / net_burn if net_burn > 0 else 120

        return {
            "plan_id": plan_id,
            "plan_name": plan.get("name"),
            "runway": {
                "p10": outputs["runway"]["p10"],
                "p50": outputs["runway"]["p50"],
                "p90": outputs["runway"]["p90"],
            },
            "survival": {
                "6m": outputs["survival"]["6m"],
                "12m": outputs["survival"]["12m"],
                "18m": outputs["survival"]["18m"],
                "24m": outputs["survival"]["24m"],
            },
            "current_runway_estimate": round(current_runway, 1),
            "total_monthly_cost_increase": total_monthly_cost_increase,
            "total_new_hires": sum(h.get("count", 1) for h in hires),
            "bands": outputs.get("bands", {}),
            "summary": outputs.get("summary", {}),
            "n_simulations": outputs.get("n_simulations", 500),
        }
    except Exception as e:
        logger.error(f"Hiring plan simulation failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Simulation failed: {str(e)}. Check your hiring plan and try again."
        )
