from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid as uuid_lib
import logging

logger = logging.getLogger(__name__)

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.simulation_run import SimulationRun
from server.models.decision import Decision
from server.models.company_decision import CompanyDecision
from server.models.truth_scan import TruthScan
from server.models.financial import FinancialRecord
from server.decision.decision_engine import generate_recommendations
from server.simulate.simulation_engine import SimulationInputs
from server.api.simulations import extract_metric_value

router = APIRouter(tags=["decisions"])


class DecisionOption(BaseModel):
    name: str
    description: str
    pros: List[str] = []
    cons: List[str] = []
    cost: Optional[str] = None
    risk: str = "medium"


class DecisionRecommendation(BaseModel):
    option: str
    rationale: str
    next_steps: List[str] = []


class CreateDecisionRequest(BaseModel):
    title: str
    context: Optional[str] = None
    options: List[DecisionOption] = []
    recommendation: Optional[DecisionRecommendation] = None
    status: str = "proposed"
    owner: Optional[str] = None
    tags: List[str] = []
    confidence: str = "medium"
    sources: List[str] = []


class UpdateDecisionRequest(BaseModel):
    title: Optional[str] = None
    context: Optional[str] = None
    options: Optional[List[DecisionOption]] = None
    recommendation: Optional[DecisionRecommendation] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    tags: Optional[List[str]] = None
    confidence: Optional[str] = None

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
    
    latest_record = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company.id)
        .order_by(FinancialRecord.period_start.desc())
        .first()
    )
    
    def metric_or_record(metric_key, record_attr, default):
        val = extract_metric_value(metrics.get(metric_key), 0)
        if val and val > 0:
            return val
        if latest_record and getattr(latest_record, record_attr, None):
            return float(getattr(latest_record, record_attr))
        return default
    
    baseline_inputs = SimulationInputs(
        baseline_revenue=metric_or_record("monthly_revenue", "revenue", 50000),
        baseline_growth_rate=extract_metric_value(metrics.get("revenue_growth_mom"), 10),
        gross_margin=extract_metric_value(metrics.get("gross_margin"), 70),
        opex=metric_or_record("opex", "opex", 20000),
        payroll=metric_or_record("payroll", "payroll", 30000),
        other_costs=metric_or_record("other_costs", "other_costs", 5000),
        cash_balance=metric_or_record("cash_balance", "cash_balance", 500000),
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

@router.post("/companies/{company_id}/strategic-diagnosis")
def generate_strategic_diagnosis(
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
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company.id
    ).order_by(TruthScan.created_at.desc()).first()
    
    metrics = {}
    confidence = 50
    if truth_scan:
        metrics = truth_scan.outputs_json.get("metrics", {})
        confidence = truth_scan.outputs_json.get("data_confidence_score", 50)
    
    latest_record = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company.id)
        .order_by(FinancialRecord.period_start.desc())
        .first()
    )
    
    revenue = extract_metric_value(metrics.get("monthly_revenue"), 0)
    if not revenue and latest_record and latest_record.revenue:
        revenue = float(latest_record.revenue)
    burn = extract_metric_value(metrics.get("monthly_burn"), 0)
    if not burn and latest_record:
        opex = float(latest_record.opex or 0)
        payroll = float(latest_record.payroll or 0)
        burn = opex + payroll
    cash = extract_metric_value(metrics.get("cash_balance"), 0)
    if not cash and latest_record and latest_record.cash_balance:
        cash = float(latest_record.cash_balance)
    growth = extract_metric_value(metrics.get("revenue_growth_mom"), 0)
    runway_months = cash / burn if burn > 0 else 24
    
    from server.models.scenario import Scenario
    scenarios = db.query(Scenario).filter(Scenario.company_id == company_id).all()
    sim_data = None
    if scenarios:
        for scenario in scenarios:
            sim_run = db.query(SimulationRun).filter(
                SimulationRun.scenario_id == scenario.id
            ).order_by(SimulationRun.created_at.desc()).first()
            if sim_run and sim_run.results_json:
                sim_data = sim_run.results_json
                break
    
    survival_prob = None
    if sim_data:
        survival = sim_data.get("survival", {})
        survival_prob = survival.get("probability_18m") or survival.get("probability_12m")
    
    company_context = f"""Company: {company.name}
Industry: {getattr(company, 'industry', 'Technology')}
Stage: {getattr(company, 'stage', 'Seed/Series A')}
Monthly Revenue: ${revenue:,.0f}
Monthly Burn: ${burn:,.0f}
Cash Balance: ${cash:,.0f}
Revenue Growth (MoM): {growth:.1f}%
Runway: {runway_months:.1f} months
Data Confidence: {confidence}%"""
    
    if survival_prob is not None:
        company_context += f"\n18-Month Survival Probability: {survival_prob:.1f}%"
    
    system_prompt = """You are a McKinsey senior partner and a16z venture partner combined. You write brutally honest, data-backed strategic briefing memos for startup founders. Write in plain prose — no bullet points, no dashboards, no charts. This is a document the founder will read top-to-bottom and forward to their team.

Respond in valid JSON with this exact structure:
{
  "situation_narrative": "A 3-5 sentence paragraph in plain English describing the company's current financial state. Use specific numbers from the data (MRR, burn rate, runway, growth rate). Example tone: 'TechFlow Analytics is currently burning $143K/month against $15.4K in MRR. At this rate, you have approximately 2.9 months of runway remaining. Revenue growth has stalled at 0%, which means the gap between what you earn and what you spend is not closing. This puts you in a critical position where decisive action in the next 2-4 weeks will significantly impact your outcomes.'",
  "recommendation_headline": "A bold, specific action statement — e.g. 'Cut Monthly Burn by 30% and Launch Emergency Revenue Sprint'",
  "recommendation_narrative": "2-3 paragraphs of WRITTEN RATIONALE. Not a one-liner. Explain WHY this action, WHY now, what happens if the founder waits, and what the trade-offs are. Use the company's specific numbers. Write as if you are advising a founder in person. Be specific about the mechanics — what to cut, who to talk to, what to prioritize.",
  "urgency_text": "A plain-English urgency statement — e.g. 'Act within the next 2 weeks' or 'This decision becomes less effective after 30 days'",
  "inaction_narrative": "A 2-3 paragraph written projection of what happens if the founder does nothing. Paint the specific picture: when cash runs out, what triggers the crisis, what options disappear. Use real numbers. Write it as a cautionary narrative, not a data table.",
  "company_stage_label": "One of: Pre-Revenue, Early Revenue, Growth, Scale, or Distressed",
  "health_score": 1-100,
  "health_label": "One of: Critical, Concerning, Stable, Healthy, Strong",
  "inaction_projection": {
    "months_to_crisis": integer,
    "crisis_description": "One-sentence summary",
    "probability": 0-100,
    "cash_at_crisis": number,
    "key_trigger": "Single trigger"
  },
  "top_3_priorities": [
    {
      "priority": "Short action label",
      "why_now": "One sentence on urgency",
      "expected_impact": "Quantified expected outcome"
    }
  ],
  "blind_spots": ["2-3 things the founder probably isn't thinking about"]
}"""
    
    try:
        from server.lib.llm.llm_router import get_llm_router, TaskType
        llm_router = get_llm_router(
            db_session=db,
            company_id=company_id,
            user_id=current_user.id
        )
        
        result = llm_router.chat(
            messages=[{"role": "user", "content": f"Provide a strategic diagnosis for this company:\n\n{company_context}"}],
            task_type=TaskType.STRATEGY,
            system=system_prompt,
            temperature=0.6,
            max_tokens=4096,
        )
        
        import json
        content = result.get("content", "{}")
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        diagnosis = json.loads(content)
        diagnosis["company_name"] = company.name
        diagnosis["generated_at"] = datetime.utcnow().isoformat()
        diagnosis["model_used"] = result.get("model", "unknown")
        
        return diagnosis
        
    except Exception as e:
        import traceback
        logger.error(f"Strategic diagnosis failed: {traceback.format_exc()}")
        growth_text = "Revenue growth is positive, which is encouraging, but it is not yet enough to close the gap between what you earn and what you spend." if growth > 0 else f"Revenue growth is at {growth:.1f}%, which means the gap between what you earn and what you spend is not closing."
        crisis_months = max(1, int(runway_months - 2))
        return {
            "situation_narrative": f"{company.name} is currently burning ${burn:,.0f}/month against ${revenue:,.0f} in monthly revenue. At this rate, you have approximately {runway_months:.1f} months of runway remaining. {growth_text} This puts you in a {'critical' if runway_months < 6 else 'challenging'} position where decisive action in the next {'2-4 weeks' if runway_months < 6 else '1-2 months'} will significantly impact your outcomes.",
            "recommendation_headline": "Cut Monthly Burn by 25% and Launch an Emergency Revenue Sprint" if runway_months < 12 else "Accelerate Revenue Growth While Maintaining Capital Efficiency",
            "recommendation_narrative": f"Your most urgent priority is {'survival' if runway_months < 12 else 'sustainable growth'}. With ${cash:,.0f} in the bank and a monthly burn of ${burn:,.0f}, every week of delay narrows your options. The single highest-leverage action right now is to {'reduce burn immediately — audit every vendor contract, pause non-essential hiring, and consolidate overlapping tools' if runway_months < 12 else 'increase revenue velocity while keeping costs disciplined'}.\n\n{'If you wait even 30 days to act, you will have consumed another $' + f'{burn:,.0f}' + ' and your negotiating position with investors, vendors, and partners weakens with every passing week. The trade-off is real: cutting costs may slow product development, but the alternative — running out of cash — is worse.' if runway_months < 12 else 'The trade-off is clear: investing in growth now means accepting higher short-term burn, but the compounding effect of revenue growth will extend your effective runway and strengthen your position for future fundraising.'}",
            "urgency_text": f"Act within the next {'2 weeks' if runway_months < 6 else '30 days'}. {'Every day of delay costs you $' + f'{burn/30:,.0f}' + ' and reduces your options.' if runway_months < 12 else 'This window of opportunity will not remain open indefinitely.'}",
            "inaction_narrative": f"If you change nothing about how {company.name} operates today, here is what happens: In approximately {crisis_months} months, your cash reserves will drop below a safe operating threshold. At that point, you will be forced into emergency fundraising — which means accepting worse terms, higher dilution, and potentially losing control of key decisions.\n\nThe trigger is straightforward: your monthly burn of ${burn:,.0f} continues to outpace your revenue of ${revenue:,.0f}. Without intervention, this math does not change. By month {crisis_months}, you will have approximately ${max(0, cash - burn * crisis_months):,.0f} remaining — not enough to operate with confidence or negotiate from strength.",
            "diagnosis_narrative": f"Based on your current metrics, {company.name} has approximately {runway_months:.0f} months of runway at the current burn rate of ${burn:,.0f}/month. {growth_text} Focus on extending runway while pursuing growth opportunities.",
            "company_stage_label": "Early Revenue" if revenue > 0 else "Pre-Revenue",
            "health_score": min(100, max(10, int(runway_months * 5 + growth * 2))),
            "health_label": "Stable" if runway_months > 12 else ("Concerning" if runway_months > 6 else "Critical"),
            "inaction_projection": {
                "months_to_crisis": crisis_months,
                "crisis_description": f"Cash reserves depleted at current burn rate of ${burn:,.0f}/month",
                "probability": 70 if runway_months < 12 else 40,
                "cash_at_crisis": 0,
                "key_trigger": "Cash balance drops below 2 months of operating expenses"
            },
            "top_3_priorities": [
                {"priority": "Extend runway", "why_now": "Current runway is limited", "expected_impact": "Add 3-6 months of operating time"},
                {"priority": "Accelerate revenue", "why_now": "Revenue growth compounds over time", "expected_impact": "Reduce dependency on external funding"},
                {"priority": "Optimize burn", "why_now": "Every dollar saved extends runway", "expected_impact": "10-20% burn reduction possible"}
            ],
            "blind_spots": [
                "Customer concentration risk if relying on few large accounts",
                "Team capacity constraints that could limit growth execution",
                "Market timing risk as conditions may shift"
            ],
            "company_name": company.name,
            "generated_at": datetime.utcnow().isoformat(),
            "model_used": "fallback",
            "error": str(e)
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


@router.get("/companies/{company_id}/decisions")
def list_company_decisions(
    company_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    query = db.query(CompanyDecision).filter(CompanyDecision.company_id == company_id)
    
    if status:
        query = query.filter(CompanyDecision.status == status)
    
    decisions = query.order_by(CompanyDecision.created_at.desc()).all()
    
    return {
        "decisions": [d.to_dict() for d in decisions],
        "total": len(decisions)
    }


@router.get("/companies/{company_id}/decisions/{decision_id}")
def get_company_decision(
    company_id: int,
    decision_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        decision_uuid = uuid_lib.UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision ID format")
    
    decision = db.query(CompanyDecision).filter(
        CompanyDecision.id == decision_uuid,
        CompanyDecision.company_id == company_id
    ).first()
    
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    return decision.to_dict()


@router.post("/companies/{company_id}/decisions")
def create_company_decision(
    company_id: int,
    request: CreateDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    decision = CompanyDecision(
        company_id=company_id,
        title=request.title,
        context=request.context,
        options_json=[o.model_dump() for o in request.options],
        recommendation_json=request.recommendation.model_dump() if request.recommendation else {},
        status=request.status,
        owner=request.owner,
        tags=request.tags,
        confidence=request.confidence,
        sources_json=request.sources
    )
    
    db.add(decision)
    db.commit()
    db.refresh(decision)
    
    return decision.to_dict()


@router.patch("/companies/{company_id}/decisions/{decision_id}")
def update_company_decision(
    company_id: int,
    decision_id: str,
    request: UpdateDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        decision_uuid = uuid_lib.UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision ID format")
    
    decision = db.query(CompanyDecision).filter(
        CompanyDecision.id == decision_uuid,
        CompanyDecision.company_id == company_id
    ).first()
    
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    if request.title is not None:
        decision.title = request.title
    if request.context is not None:
        decision.context = request.context
    if request.options is not None:
        decision.options_json = [o.model_dump() for o in request.options]
    if request.recommendation is not None:
        decision.recommendation_json = request.recommendation.model_dump()
    if request.status is not None:
        decision.status = request.status
    if request.owner is not None:
        decision.owner = request.owner
    if request.tags is not None:
        decision.tags = request.tags
    if request.confidence is not None:
        decision.confidence = request.confidence
    
    decision.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(decision)
    
    return decision.to_dict()


@router.delete("/companies/{company_id}/decisions/{decision_id}")
def delete_company_decision(
    company_id: int,
    decision_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        decision_uuid = uuid_lib.UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision ID format")
    
    decision = db.query(CompanyDecision).filter(
        CompanyDecision.id == decision_uuid,
        CompanyDecision.company_id == company_id
    ).first()
    
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    db.delete(decision)
    db.commit()
    
    return {"success": True, "message": "Decision deleted"}
