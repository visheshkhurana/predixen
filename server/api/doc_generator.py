from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.models.financial import FinancialRecord
from server.models.scenario import Scenario
from server.api.simulations import extract_metric_value

logger = logging.getLogger(__name__)
router = APIRouter(tags=["doc-generator"])

DOC_TYPES = {
    "financial-model": {
        "id": "financial-model",
        "name": "Financial Model",
        "description": "Revenue projections, cost structure, unit economics, and growth assumptions",
        "icon": "bar-chart",
        "sections": ["Revenue Model", "Cost Structure", "Unit Economics", "Growth Assumptions", "Scenario Analysis"],
    },
    "investor-memo": {
        "id": "investor-memo",
        "name": "Investor Memo",
        "description": "Concise investment thesis, traction highlights, market opportunity, and ask",
        "icon": "briefcase",
        "sections": ["Investment Thesis", "Company Overview", "Traction & Metrics", "Market Opportunity", "The Ask"],
    },
    "board-memo": {
        "id": "board-memo",
        "name": "Board Memo",
        "description": "Monthly or quarterly board update with financials, milestones, and decisions",
        "icon": "file-text",
        "sections": ["Executive Summary", "Financial Highlights", "Key Milestones", "Challenges & Risks", "Upcoming Decisions"],
    },
    "kpi-report": {
        "id": "kpi-report",
        "name": "KPI Report",
        "description": "Detailed KPI dashboard with trends, benchmarks, and commentary",
        "icon": "activity",
        "sections": ["KPI Summary", "Revenue Metrics", "Growth Metrics", "Efficiency Metrics", "Benchmark Comparison"],
    },
    "pitch-deck-outline": {
        "id": "pitch-deck-outline",
        "name": "Pitch Deck Outline",
        "description": "Structured pitch deck content with narrative, data points, and slide-by-slide guidance",
        "icon": "presentation",
        "sections": ["Problem & Solution", "Market Size", "Product & Traction", "Business Model", "Team & Ask"],
    },
    "scenario-brief": {
        "id": "scenario-brief",
        "name": "Scenario Brief",
        "description": "Deep analysis of a specific scenario with risks, trade-offs, and recommendations",
        "icon": "git-branch",
        "sections": ["Scenario Overview", "Financial Impact", "Risk Assessment", "Trade-offs", "Recommendation"],
    },
}

SECTION_TASK_TYPES = {
    "Revenue Model": "financial_analysis",
    "Cost Structure": "financial_analysis",
    "Unit Economics": "financial_analysis",
    "Growth Assumptions": "strategy",
    "Scenario Analysis": "financial_analysis",
    "Investment Thesis": "creative_writing",
    "Company Overview": "creative_writing",
    "Traction & Metrics": "financial_analysis",
    "Market Opportunity": "strategy",
    "The Ask": "strategy",
    "Executive Summary": "creative_writing",
    "Financial Highlights": "financial_analysis",
    "Key Milestones": "strategy",
    "Challenges & Risks": "strategy",
    "Upcoming Decisions": "strategy",
    "KPI Summary": "financial_analysis",
    "Revenue Metrics": "financial_analysis",
    "Growth Metrics": "financial_analysis",
    "Efficiency Metrics": "financial_analysis",
    "Benchmark Comparison": "strategy",
    "Problem & Solution": "creative_writing",
    "Market Size": "strategy",
    "Product & Traction": "creative_writing",
    "Business Model": "strategy",
    "Team & Ask": "creative_writing",
    "Scenario Overview": "strategy",
    "Financial Impact": "financial_analysis",
    "Risk Assessment": "financial_analysis",
    "Trade-offs": "strategy",
    "Recommendation": "strategy",
}


class GenerateDocRequest(BaseModel):
    doc_type: str
    custom_instructions: Optional[str] = None
    include_web_research: bool = False
    scenario_id: Optional[int] = None


def _gather_company_context(db: Session, company: Company) -> Dict[str, Any]:
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
        .limit(5)
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
            }
        scenario_data.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "latest_simulation": sim_data,
        })

    fin_records_data = []
    for fr in financial_records:
        fin_records_data.append({
            "period_start": fr.period_start.isoformat() if fr.period_start else None,
            "revenue": float(fr.revenue or 0),
            "cogs": float(fr.cogs or 0),
            "opex": float(fr.opex or 0),
            "payroll": float(fr.payroll or 0),
            "cash_balance": float(fr.cash_balance or 0),
            "mrr": float(fr.mrr or 0) if fr.mrr else None,
            "arr": float(fr.arr or 0) if fr.arr else None,
            "gross_margin": float(fr.gross_margin or 0) if fr.gross_margin is not None else None,
            "net_burn": float(fr.net_burn or 0) if fr.net_burn is not None else None,
            "runway_months": float(fr.runway_months or 0) if fr.runway_months is not None else None,
            "headcount": fr.headcount,
            "customers": fr.customers,
        })

    extracted_metrics = {
        "mrr": extract_metric_value(metrics.get("mrr"), 0),
        "arr": extract_metric_value(metrics.get("arr"), 0),
        "monthly_revenue": extract_metric_value(metrics.get("monthly_revenue"), 0),
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
    }


def _build_section_prompt(doc_type: str, section: str, context: Dict, custom_instructions: Optional[str] = None) -> str:
    company = context["company"]
    m = context["metrics"]

    data_block = (
        f"Company: {company['name']} ({company.get('industry', 'Tech')}, {company.get('stage', 'Seed')})\n"
        f"MRR: ${m.get('mrr', 0):,.0f} | ARR: ${m.get('arr', 0):,.0f}\n"
        f"Monthly Revenue: ${m.get('monthly_revenue', 0):,.0f}\n"
        f"Burn Rate: ${m.get('burn_rate', 0):,.0f}/mo | Cash: ${m.get('cash_balance', 0):,.0f}\n"
        f"Runway: {m.get('runway_months', 0):.1f} months\n"
        f"Gross Margin: {m.get('gross_margin', 0):.1f}% | Revenue Growth MoM: {m.get('revenue_growth', 0):.1f}%\n"
        f"Customers: {m.get('customers', 0):.0f} | Churn: {m.get('churn_rate', 0):.1f}%\n"
        f"LTV/CAC: {m.get('ltv_cac_ratio', 0):.1f}x (LTV: ${m.get('ltv', 0):,.0f}, CAC: ${m.get('cac', 0):,.0f})\n"
        f"Data Confidence: {context.get('confidence', 50)}%\n"
    )

    scenarios_text = ""
    for sc in context.get("scenarios", [])[:3]:
        sim = sc.get("latest_simulation") or {}
        runway = sim.get("runway", {})
        scenarios_text += f"- {sc['name']}: P50 runway {runway.get('p50', 'N/A')}mo\n"

    prompt = (
        f"You are a top-tier startup CFO and strategy consultant.\n"
        f"Document type: {doc_type.replace('-', ' ').title()}\n"
        f"Section: {section}\n\n"
        f"Company Data:\n{data_block}\n"
    )

    if scenarios_text:
        prompt += f"Active Scenarios:\n{scenarios_text}\n"

    if custom_instructions:
        prompt += f"\nAdditional Instructions: {custom_instructions}\n"

    prompt += (
        f"\nWrite the '{section}' section for this {doc_type.replace('-', ' ')}. "
        f"Use specific numbers and data points from the company data. "
        f"Be concise, professional, and actionable. Write 2-4 paragraphs. "
        f"Do not use markdown headers. Use plain text with clear structure."
    )

    return prompt


@router.get("/companies/{company_id}/doc-generator/types")
def get_doc_types(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    return {"doc_types": list(DOC_TYPES.values())}


@router.post("/companies/{company_id}/doc-generator/generate")
def generate_document(
    company_id: int,
    request: GenerateDocRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)

    doc_config = DOC_TYPES.get(request.doc_type)
    if not doc_config:
        raise HTTPException(status_code=400, detail=f"Unknown document type: {request.doc_type}")

    context = _gather_company_context(db, company)

    from server.lib.llm.llm_router import LLMRouter, TaskType

    llm = LLMRouter(
        db_session=db,
        company_id=company_id,
        user_id=current_user.id,
    )

    sections_result = []
    for section_name in doc_config["sections"]:
        task_type_str = SECTION_TASK_TYPES.get(section_name, "strategy")
        try:
            task_type = TaskType(task_type_str)
        except ValueError:
            task_type = TaskType.STRATEGY

        prompt = _build_section_prompt(
            request.doc_type, section_name, context, request.custom_instructions
        )

        web_context = ""
        if request.include_web_research and section_name in [
            "Market Opportunity", "Market Size", "Benchmark Comparison",
            "Investment Thesis", "Challenges & Risks"
        ]:
            try:
                industry = context["company"].get("industry", "technology")
                search_result = llm.web_search(
                    query=f"{industry} startup market trends benchmarks 2026",
                    model="sonar",
                )
                web_context = search_result.get("content", "")
                if web_context:
                    prompt += f"\n\nWeb Research Context:\n{web_context[:2000]}\n"
            except Exception as e:
                logger.warning(f"Web research failed for section '{section_name}': {e}")

        try:
            result = llm.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type=task_type,
                temperature=0.5,
                max_tokens=1024,
            )

            sections_result.append({
                "title": section_name,
                "content": result.get("content", ""),
                "model_used": result.get("model", "unknown"),
                "provider_used": result.get("provider", "unknown"),
                "task_type": task_type_str,
                "has_web_research": bool(web_context),
            })
        except Exception as e:
            logger.warning(f"Doc generation failed for section '{section_name}': {e}")
            sections_result.append({
                "title": section_name,
                "content": f"Unable to generate this section. Please try again.",
                "model_used": "error",
                "provider_used": "none",
                "task_type": task_type_str,
                "has_web_research": False,
            })

    return {
        "doc_type": doc_config,
        "sections": sections_result,
        "company": context["company"],
        "metrics": context["metrics"],
        "generated_at": datetime.utcnow().isoformat(),
    }
