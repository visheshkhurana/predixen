from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.models.simulation_run import SimulationRun
from server.models.scenario import Scenario
from server.models.company_decision import CompanyDecision
from server.models.financial import FinancialRecord
from server.api.simulations import extract_metric_value

router = APIRouter(tags=["board-export"])

TEMPLATES = {
    "monthly-update": {
        "id": "monthly-update",
        "name": "Monthly Update",
        "description": "Standard monthly board update with key metrics and highlights",
        "sections": [
            {"type": "metrics", "title": "Key Metrics Overview", "dataSource": "truth_scan", "aiNarrative": True},
            {"type": "chart", "title": "Revenue & Burn Trend", "dataSource": "financial_records", "aiNarrative": False},
            {"type": "narrative", "title": "Executive Summary", "dataSource": "all", "aiNarrative": True},
            {"type": "metrics", "title": "Growth & Retention", "dataSource": "truth_scan", "aiNarrative": False},
            {"type": "simulation", "title": "Runway & Survival Outlook", "dataSource": "simulation_runs", "aiNarrative": True},
            {"type": "narrative", "title": "Key Decisions & Next Steps", "dataSource": "decisions", "aiNarrative": True},
        ],
    },
    "fundraising-prep": {
        "id": "fundraising-prep",
        "name": "Fundraising Prep",
        "description": "Investor-ready deck with traction, metrics, and projections",
        "sections": [
            {"type": "narrative", "title": "Company Overview & Vision", "dataSource": "all", "aiNarrative": True},
            {"type": "metrics", "title": "Traction & Key Metrics", "dataSource": "truth_scan", "aiNarrative": True},
            {"type": "chart", "title": "Revenue Growth Trajectory", "dataSource": "financial_records", "aiNarrative": False},
            {"type": "metrics", "title": "Unit Economics", "dataSource": "truth_scan", "aiNarrative": True},
            {"type": "simulation", "title": "Financial Projections", "dataSource": "simulation_runs", "aiNarrative": True},
            {"type": "narrative", "title": "Use of Funds & Milestones", "dataSource": "all", "aiNarrative": True},
        ],
    },
    "scenario-analysis": {
        "id": "scenario-analysis",
        "name": "Scenario Analysis",
        "description": "Deep dive into scenarios with comparison and recommendations",
        "sections": [
            {"type": "metrics", "title": "Current Baseline Metrics", "dataSource": "truth_scan", "aiNarrative": False},
            {"type": "comparison", "title": "Scenario Comparison", "dataSource": "scenarios", "aiNarrative": True},
            {"type": "simulation", "title": "Monte Carlo Results", "dataSource": "simulation_runs", "aiNarrative": True},
            {"type": "narrative", "title": "Risk Analysis & Sensitivity", "dataSource": "all", "aiNarrative": True},
            {"type": "narrative", "title": "Strategic Recommendations", "dataSource": "decisions", "aiNarrative": True},
        ],
    },
}


class GenerateRequest(BaseModel):
    templateId: str


def _gather_company_data(db: Session, company: Company) -> Dict[str, Any]:
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company.id
    ).order_by(TruthScan.created_at.desc()).first()

    metrics = {}
    confidence = 50
    if truth_scan and truth_scan.outputs_json:
        metrics = truth_scan.outputs_json.get("metrics", {})
        try:
            confidence = int(float(truth_scan.outputs_json.get("data_confidence_score", 50)))
        except (ValueError, TypeError):
            confidence = 50

    financial_records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company.id)
        .order_by(FinancialRecord.period_start.desc())
        .limit(12)
        .all()
    )

    scenarios = (
        db.query(Scenario)
        .filter(Scenario.company_id == company.id, Scenario.is_archived == 0)
        .order_by(Scenario.updated_at.desc())
        .limit(10)
        .all()
    )

    scenario_data = []
    for s in scenarios:
        latest_run = s.get_latest_run()
        sim_data = None
        if latest_run and latest_run.outputs_json:
            out = latest_run.outputs_json
            sim_data = {
                "runway": out.get("runway"),
                "survival": out.get("survivalProbability", out.get("survival")),
                "summary": out.get("summary"),
            }
        scenario_data.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "inputs": s.inputs_json,
            "latest_simulation": sim_data,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    decisions = (
        db.query(CompanyDecision)
        .filter(CompanyDecision.company_id == company.id)
        .order_by(CompanyDecision.created_at.desc())
        .limit(10)
        .all()
    )

    decision_data = [d.to_dict() for d in decisions]

    latest_sim_run = (
        db.query(SimulationRun)
        .join(Scenario, SimulationRun.scenario_id == Scenario.id)
        .filter(Scenario.company_id == company.id, SimulationRun.status == "completed")
        .order_by(SimulationRun.created_at.desc())
        .first()
    )

    sim_outputs = {}
    if latest_sim_run and latest_sim_run.outputs_json:
        sim_outputs = latest_sim_run.outputs_json

    fin_records_data = []
    for fr in financial_records:
        fin_records_data.append({
            "period_start": fr.period_start.isoformat() if fr.period_start else None,
            "period_end": fr.period_end.isoformat() if fr.period_end else None,
            "revenue": float(fr.revenue or 0),
            "cogs": float(fr.cogs or 0),
            "opex": float(fr.opex or 0),
            "payroll": float(fr.payroll or 0),
            "other_costs": float(fr.other_costs or 0),
            "cash_balance": float(fr.cash_balance or 0),
            "mrr": float(fr.mrr or 0) if fr.mrr else None,
            "arr": float(fr.arr or 0) if fr.arr else None,
            "gross_margin": float(fr.gross_margin or 0) if fr.gross_margin is not None else None,
            "net_burn": float(fr.net_burn or 0) if fr.net_burn is not None else None,
            "runway_months": float(fr.runway_months or 0) if fr.runway_months is not None else None,
            "headcount": fr.headcount,
            "customers": fr.customers,
            "mom_growth": float(fr.mom_growth or 0) if fr.mom_growth is not None else None,
        })

    extracted_metrics = {
        "monthly_revenue": extract_metric_value(metrics.get("monthly_revenue"), 0),
        "mrr": extract_metric_value(metrics.get("mrr"), 0),
        "arr": extract_metric_value(metrics.get("arr"), 0),
        "burn_rate": extract_metric_value(metrics.get("monthly_burn"), 0),
        "cash_balance": extract_metric_value(metrics.get("cash_balance"), 0),
        "runway_months": extract_metric_value(metrics.get("runway_months"), 0),
        "gross_margin": extract_metric_value(metrics.get("gross_margin"), 0),
        "revenue_growth": extract_metric_value(metrics.get("revenue_growth_mom"), 0),
        "customers": extract_metric_value(metrics.get("customers"), 0),
        "churn_rate": extract_metric_value(metrics.get("churn_rate"), 0),
        "cac": extract_metric_value(metrics.get("cac"), 0),
        "ltv": extract_metric_value(metrics.get("ltv"), 0),
        "ltv_cac_ratio": extract_metric_value(metrics.get("ltv_cac_ratio"), 0),
        "ndr": extract_metric_value(metrics.get("ndr"), 0),
    }

    return {
        "company": {
            "id": company.id,
            "name": company.name,
            "industry": company.industry,
            "stage": company.stage,
            "currency": company.currency,
        },
        "metrics": extracted_metrics,
        "confidence": confidence,
        "financial_records": fin_records_data,
        "scenarios": scenario_data,
        "decisions": decision_data,
        "simulation": sim_outputs,
        "truth_scan_raw": metrics,
        "generated_at": datetime.utcnow().isoformat(),
    }


def _build_narrative_prompt(template_id: str, section: Dict, data: Dict) -> str:
    company_name = data["company"]["name"]
    metrics = data["metrics"]
    section_title = section["title"]

    metrics_summary = (
        f"Company: {company_name}\n"
        f"MRR: ${metrics.get('mrr', 0):,.0f}, ARR: ${metrics.get('arr', 0):,.0f}\n"
        f"Monthly Revenue: ${metrics.get('monthly_revenue', 0):,.0f}\n"
        f"Burn Rate: ${metrics.get('burn_rate', 0):,.0f}/mo\n"
        f"Cash Balance: ${metrics.get('cash_balance', 0):,.0f}\n"
        f"Runway: {metrics.get('runway_months', 0):.1f} months\n"
        f"Gross Margin: {metrics.get('gross_margin', 0):.1f}%\n"
        f"Revenue Growth MoM: {metrics.get('revenue_growth', 0):.1f}%\n"
        f"Churn Rate: {metrics.get('churn_rate', 0):.1f}%\n"
        f"LTV/CAC: {metrics.get('ltv_cac_ratio', 0):.1f}x\n"
        f"Data Confidence: {data.get('confidence', 50)}%\n"
    )

    scenarios_text = ""
    for sc in data.get("scenarios", [])[:3]:
        sim = sc.get("latest_simulation") or {}
        runway = sim.get("runway", {})
        scenarios_text += f"- {sc['name']}: P50 runway {runway.get('p50', 'N/A')}mo\n"

    decisions_text = ""
    for d in data.get("decisions", [])[:3]:
        decisions_text += f"- [{d.get('status', 'proposed')}] {d.get('title', 'Untitled')}\n"

    prompt = (
        f"You are a CFO assistant creating a board deck section.\n"
        f"Template: {template_id}\n"
        f"Section: {section_title}\n\n"
        f"Financial Data:\n{metrics_summary}\n"
    )

    if scenarios_text:
        prompt += f"Scenarios:\n{scenarios_text}\n"
    if decisions_text:
        prompt += f"Recent Decisions:\n{decisions_text}\n"

    prompt += (
        f"\nWrite a concise, professional narrative for the '{section_title}' section "
        f"of a {template_id.replace('-', ' ')} board deck. "
        f"Use specific numbers from the data. Keep it to 2-3 paragraphs. "
        f"Be direct and actionable. Do not use markdown headers."
    )

    return prompt


@router.get("/companies/{company_id}/board-export/data")
def get_board_export_data(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)
    data = _gather_company_data(db, company)
    data["templates"] = list(TEMPLATES.values())
    return data


@router.post("/companies/{company_id}/board-export/generate")
def generate_board_export(
    company_id: int,
    request: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)

    template = TEMPLATES.get(request.templateId)
    if not template:
        raise HTTPException(status_code=400, detail=f"Unknown template: {request.templateId}")

    data = _gather_company_data(db, company)

    sections_result = []
    for section in template["sections"]:
        section_out = {
            "type": section["type"],
            "title": section["title"],
            "dataSource": section["dataSource"],
            "narrative": None,
            "data": None,
        }

        if section["type"] == "metrics":
            section_out["data"] = data["metrics"]
        elif section["type"] == "chart":
            section_out["data"] = data["financial_records"]
        elif section["type"] == "simulation":
            section_out["data"] = data["simulation"]
        elif section["type"] == "comparison":
            section_out["data"] = data["scenarios"]

        if section.get("aiNarrative"):
            try:
                from server.lib.llm.llm_router import LLMRouter, TaskType

                llm = LLMRouter(
                    db_session=db,
                    company_id=company_id,
                    user_id=current_user.id,
                )

                prompt = _build_narrative_prompt(request.templateId, section, data)
                task_type = _get_section_task_type(section)

                result = llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    task_type=task_type,
                    temperature=0.5,
                    max_tokens=1024,
                )

                section_out["narrative"] = result.get("content", "")
                section_out["model_used"] = result.get("model", "unknown")
                section_out["provider_used"] = result.get("provider", "unknown")
            except Exception as e:
                logger.warning(f"AI narrative generation failed for section '{section['title']}': {e}")
                section_out["narrative"] = _generate_fallback_narrative(section, data)
                section_out["model_used"] = "fallback"
                section_out["provider_used"] = "rule-based"

        sections_result.append(section_out)

    return {
        "template": template,
        "sections": sections_result,
        "company": data["company"],
        "generated_at": datetime.utcnow().isoformat(),
    }


def _get_section_task_type(section: Dict) -> "TaskType":
    from server.lib.llm.llm_router import TaskType

    title = section.get("title", "").lower()
    section_type = section.get("type", "")

    if any(kw in title for kw in ["executive", "overview", "vision"]):
        return TaskType.CREATIVE_WRITING
    elif any(kw in title for kw in ["strategy", "recommendation", "strategic"]):
        return TaskType.STRATEGY
    elif any(kw in title for kw in ["decision", "next steps", "milestone", "funds"]):
        return TaskType.STRATEGY
    elif section_type == "simulation" or any(kw in title for kw in ["runway", "survival", "projection", "monte carlo"]):
        return TaskType.FINANCIAL_ANALYSIS
    elif section_type == "metrics" or any(kw in title for kw in ["metric", "traction", "unit economics", "growth", "revenue", "burn"]):
        return TaskType.FINANCIAL_ANALYSIS
    elif any(kw in title for kw in ["risk", "sensitivity", "analysis"]):
        return TaskType.FINANCIAL_ANALYSIS
    elif section_type == "comparison" or any(kw in title for kw in ["scenario", "comparison"]):
        return TaskType.STRATEGY
    else:
        return TaskType.SIMPLE_TASK


class GraphicRequest(BaseModel):
    prompt: str
    style: str = "professional"
    aspect_ratio: str = "16:9"
    section_context: Optional[str] = None


@router.post("/companies/{company_id}/board-export/generate-graphic")
def generate_board_graphic(
    company_id: int,
    request: GraphicRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)

    from server.lib.llm.image_generator import NanoBananaImageGenerator

    try:
        generator = NanoBananaImageGenerator(
            db_session=db,
            company_id=company_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    full_prompt = request.prompt
    if request.section_context:
        full_prompt = f"For a board deck section about '{request.section_context}': {request.prompt}"

    result = generator.generate_image(
        prompt=full_prompt,
        style=request.style,
        aspect_ratio=request.aspect_ratio,
    )

    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])

    return result


def _generate_fallback_narrative(section: Dict, data: Dict) -> str:
    metrics = data["metrics"]
    company_name = data["company"]["name"]
    title = section["title"]

    revenue = metrics.get("monthly_revenue", 0)
    burn = metrics.get("burn_rate", 0)
    cash = metrics.get("cash_balance", 0)
    runway = metrics.get("runway_months", 0)
    growth = metrics.get("revenue_growth", 0)

    if "executive" in title.lower() or "overview" in title.lower():
        return (
            f"{company_name} generated ${revenue:,.0f} in monthly revenue with "
            f"{growth:.1f}% month-over-month growth. Current burn rate is ${burn:,.0f}/month "
            f"with ${cash:,.0f} in cash, providing approximately {runway:.1f} months of runway."
        )
    elif "decision" in title.lower() or "next steps" in title.lower():
        decisions = data.get("decisions", [])
        if decisions:
            items = ", ".join([d.get("title", "Untitled") for d in decisions[:3]])
            return f"Key decisions under consideration: {items}."
        return "No pending decisions at this time."
    elif "runway" in title.lower() or "survival" in title.lower():
        sim = data.get("simulation", {})
        runway_data = sim.get("runway", {})
        survival = sim.get("survivalProbability", sim.get("survival", {}))
        p50 = runway_data.get("p50", runway)
        s12 = survival.get("12m", "N/A") if isinstance(survival, dict) else "N/A"
        return (
            f"Monte Carlo simulation projects a median runway of {p50:.1f} months. "
            f"12-month survival probability: {s12}%." if isinstance(s12, (int, float)) else
            f"Monte Carlo simulation projects a median runway of {p50:.1f} months."
        )
    elif "unit economics" in title.lower():
        ltv_cac = metrics.get("ltv_cac_ratio", 0)
        cac = metrics.get("cac", 0)
        ltv = metrics.get("ltv", 0)
        return (
            f"LTV/CAC ratio stands at {ltv_cac:.1f}x (LTV: ${ltv:,.0f}, CAC: ${cac:,.0f}). "
            f"Gross margin is {metrics.get('gross_margin', 0):.1f}%."
        )
    elif "traction" in title.lower():
        return (
            f"{company_name} has ${revenue:,.0f} in monthly revenue growing at "
            f"{growth:.1f}% MoM with {metrics.get('customers', 0):.0f} customers."
        )
    elif "scenario" in title.lower() or "comparison" in title.lower():
        scenarios = data.get("scenarios", [])
        if scenarios:
            names = ", ".join([s["name"] for s in scenarios[:3]])
            return f"Active scenarios under analysis: {names}."
        return "No scenarios available for comparison."
    elif "risk" in title.lower() or "sensitivity" in title.lower():
        return (
            f"With {runway:.1f} months of runway and ${burn:,.0f}/month burn, "
            f"key risks include cash depletion and growth deceleration."
        )
    elif "funds" in title.lower() or "milestone" in title.lower():
        return (
            f"Current cash position of ${cash:,.0f} with ${burn:,.0f}/month burn rate. "
            f"Projected runway: {runway:.1f} months."
        )
    elif "projection" in title.lower():
        sim = data.get("simulation", {})
        runway_data = sim.get("runway", {})
        p50 = runway_data.get("p50", runway)
        return f"Financial projections show a median runway of {p50:.1f} months based on current trajectory."
    elif "recommendation" in title.lower():
        return (
            f"Based on current metrics ({growth:.1f}% MoM growth, {runway:.1f} months runway), "
            f"focus areas include optimizing burn rate and accelerating revenue growth."
        )
    else:
        return (
            f"{company_name}: Revenue ${revenue:,.0f}/mo, Burn ${burn:,.0f}/mo, "
            f"Cash ${cash:,.0f}, Runway {runway:.1f}mo, Growth {growth:.1f}% MoM."
        )
