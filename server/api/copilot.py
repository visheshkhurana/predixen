from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.scenario import Scenario
from server.models.simulation_run import SimulationRun
from server.models.truth_scan import TruthScan
from server.copilot.context_pack import build_context_pack
from server.simulate.simulation_engine import SimulationInputs, run_monte_carlo

router = APIRouter(tags=["copilot"])

class SimulateDeltas(BaseModel):
    pricing_change_pct: float = 0
    growth_uplift_pct: float = 0
    burn_reduction_pct: float = 0
    fundraise_month: Optional[int] = None
    fundraise_amount: float = 0
    gross_margin_delta_pct: float = 0

class CompareRequest(BaseModel):
    action_ids: List[str]

@router.get("/companies/{company_id}/context", response_model=Dict[str, Any])
def get_context(
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
    
    context = build_context_pack(company, db)
    return context

@router.post("/companies/{company_id}/simulate", response_model=Dict[str, Any])
def quick_simulate(
    company_id: int,
    deltas: SimulateDeltas,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    
    scenario = Scenario(
        company_id=company_id,
        name=f"Quick simulation",
        inputs_json=deltas.model_dump()
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    inputs = SimulationInputs(
        baseline_revenue=metrics.get("monthly_revenue", 50000),
        baseline_growth_rate=metrics.get("revenue_growth_mom", 5),
        gross_margin=metrics.get("gross_margin", 70) + deltas.gross_margin_delta_pct,
        opex=metrics.get("opex", 20000),
        payroll=metrics.get("payroll", 30000),
        other_costs=metrics.get("other_costs", 5000),
        cash_balance=metrics.get("cash_balance", 500000),
        pricing_change_pct=deltas.pricing_change_pct,
        growth_uplift_pct=deltas.growth_uplift_pct,
        burn_reduction_pct=deltas.burn_reduction_pct,
        fundraise_month=deltas.fundraise_month,
        fundraise_amount=deltas.fundraise_amount,
        n_simulations=500
    )
    
    outputs = run_monte_carlo(inputs, seed=None)
    
    sim_run = SimulationRun(
        scenario_id=scenario.id,
        n_sims=500,
        seed=None,
        outputs_json=outputs
    )
    db.add(sim_run)
    db.commit()
    db.refresh(sim_run)
    
    return {
        "scenario_id": scenario.id,
        "simulation_id": sim_run.id,
        **outputs
    }

@router.post("/companies/{company_id}/decision/compare", response_model=Dict[str, Any])
def compare_decisions(
    company_id: int,
    request: CompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    confidence = truth_scan.outputs_json.get("data_confidence_score", 50)
    
    from server.decision.decision_engine import generate_recommendations
    
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
    
    return {
        "recommendations": recommendations,
        "compared_actions": request.action_ids
    }


class CopilotChatRequest(BaseModel):
    """Request for copilot chat."""
    message: str
    include_financials: bool = True
    include_market: bool = False
    include_strategy: bool = True


class CopilotChatResponse(BaseModel):
    """Response from copilot chat."""
    executive_summary: List[str]
    company_snapshot: List[str]
    financials: Optional[Dict[str, Any]] = None
    market_and_customers: Optional[Dict[str, Any]] = None
    strategy_options: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[Dict[str, Any]]] = None
    assumptions: List[str]
    risks: List[str]
    next_questions: List[str]
    confidence: str
    ckb_updated: bool = False


@router.post("/companies/{company_id}/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    company_id: int,
    request: CopilotChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Multi-agent copilot chat endpoint.
    
    Routes the user's message to appropriate specialist agents (CFO, Market, Strategy)
    and returns a structured, actionable response.
    """
    from server.copilot.agents import RouterAgent
    from server.copilot.agents.base import CompanyKnowledgeBase
    from server.copilot.ckb_storage import CKBStorage
    
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    ckb_storage = CKBStorage(db)
    ckb = ckb_storage.get_ckb(company_id)
    
    if not ckb:
        ckb = CompanyKnowledgeBase(
            company_id=company.id,
            company_name=company.name or "",
            industry=company.industry or "",
            stage=company.stage or "",
            currency=company.currency or "USD"
        )
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    context = {
        "has_document": False,
        "extracted_financials": None,
        "truth_scan": truth_scan.outputs_json if truth_scan else None
    }
    
    router = RouterAgent()
    response = await router.process(request.message, ckb, context)
    
    ckb_storage.save_ckb(ckb)
    
    output = response.structured_output
    
    return CopilotChatResponse(
        executive_summary=output.get("executive_summary", []),
        company_snapshot=output.get("company_snapshot", []),
        financials=output.get("financials"),
        market_and_customers=output.get("market_and_customers"),
        strategy_options=output.get("strategy_options"),
        recommendations=output.get("recommendations"),
        assumptions=response.assumptions,
        risks=response.risks,
        next_questions=response.next_questions,
        confidence=response.confidence.value,
        ckb_updated=True
    )


@router.get("/companies/{company_id}/ckb", response_model=Dict[str, Any])
def get_company_knowledge_base(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the Company Knowledge Base for a company."""
    from server.copilot.ckb_storage import CKBStorage
    
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    ckb_storage = CKBStorage(db)
    ckb = ckb_storage.get_ckb(company_id)
    
    if not ckb:
        return {"company_id": company_id, "message": "No CKB data available"}
    
    return ckb.to_dict()


@router.put("/companies/{company_id}/ckb/{section}")
def update_ckb_section(
    company_id: int,
    section: str,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a specific section of the Company Knowledge Base."""
    from server.copilot.ckb_storage import CKBStorage
    
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    ckb_storage = CKBStorage(db)
    success = ckb_storage.update_ckb_section(company_id, section, data)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to update {section}")
    
    return {"success": True, "section": section}
