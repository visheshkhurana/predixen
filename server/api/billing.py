from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/billing", tags=["billing"])

class Plan(BaseModel):
    id: str
    name: str
    price_monthly: float
    price_annual: float
    features: List[str]
    max_scenarios: int
    max_integrations: int

class Subscription(BaseModel):
    plan_id: str
    status: str
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False

PLANS = [
    Plan(id="free", name="Free", price_monthly=0, price_annual=0,
         features=["1 scenario template", "Sample data only", "Basic dashboard"],
         max_scenarios=1, max_integrations=0),
    Plan(id="pro", name="Pro", price_monthly=99, price_annual=948,
         features=["All 11 scenario templates", "All integrations", "AI copilot", "Decision journal", "Sensitivity analysis", "Counter-moves", "Export to PDF"],
         max_scenarios=50, max_integrations=5),
    Plan(id="team", name="Team", price_monthly=249, price_annual=2388,
         features=["Everything in Pro", "Team collaboration", "Investor portal", "Custom scenarios", "Priority support", "API access"],
         max_scenarios=200, max_integrations=10),
]

@router.get("/plans")
def get_plans():
    return {"plans": [p.model_dump() for p in PLANS]}

@router.get("/plans/{plan_id}")
def get_plan(plan_id: str):
    plan = next((p for p in PLANS if p.id == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan.model_dump()

@router.get("/subscription")
def get_subscription():
    return {
        "plan_id": "free",
        "status": "active",
        "current_period_start": datetime.utcnow().isoformat(),
        "current_period_end": None,
        "cancel_at_period_end": False,
        "usage": {"scenarios_used": 0, "integrations_used": 0}
    }

@router.post("/subscribe/{plan_id}")
def subscribe(plan_id: str):
    plan = next((p for p in PLANS if p.id == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.price_monthly == 0:
        return {"message": "Free plan activated", "plan": plan.model_dump()}
    return {"message": "Stripe checkout session required", "checkout_url": None, "plan": plan.model_dump()}

@router.post("/cancel")
def cancel_subscription():
    return {"message": "Subscription will cancel at end of billing period", "cancel_at_period_end": True}
