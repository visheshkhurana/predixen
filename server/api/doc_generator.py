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


# Doc-generator metric -> truth-scan keys to try, in order.
_METRIC_SOURCES = {
    "mrr": ["mrr"],
    "arr": ["arr"],
    "monthly_revenue": ["monthly_revenue"],
    "burn_rate": ["net_burn", "monthly_burn"],
    "cash_balance": ["cash_balance"],
    "runway_months": ["runway_months", "runway_p50"],
    "gross_margin": ["gross_margin"],
    "revenue_growth": ["revenue_growth_mom"],
    "customers": ["customer_count", "customers"],
    "churn_rate": ["churn_rate"],
    "cac": ["cac"],
    "ltv": ["ltv"],
    "ltv_cac_ratio": ["ltv_cac_ratio"],
    "ndr": ["net_revenue_retention", "ndr"],
}

_ESTIMATE_MARKERS = ("estimat", "imput", "placeholder", "default", "assum")


def _is_estimated(key: str, value: Any, estimated: set) -> bool:
    if key in estimated:
        return True
    if isinstance(value, dict):
        for marker_key in ("source", "confidence", "status", "origin"):
            marker = value.get(marker_key)
            if marker is not None and any(t in str(marker).lower() for t in _ESTIMATE_MARKERS):
                return True
    return False


def _known_metrics(metrics: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """Reported metrics only. Missing or estimated values are None, never 0.

    truth_scan writes placeholders (CAC, LTV, NRR, a 150-customer default) into
    `metrics` and lists them on `_estimated_metrics`; those must not reach the
    prompt as if the founder reported them.
    """
    metrics = metrics if isinstance(metrics, dict) else {}
    listed = metrics.get("_estimated_metrics")
    estimated = {str(x) for x in listed} if isinstance(listed, list) else set()
    out: Dict[str, Optional[float]] = {}
    for name, keys in _METRIC_SOURCES.items():
        out[name] = None
        for key in keys:
            raw = metrics.get(key)
            if raw is None or _is_estimated(key, raw, estimated):
                continue
            if isinstance(raw, dict) and raw.get("value") is None:
                continue
            try:
                out[name] = extract_metric_value(raw, None)
            except Exception:
                out[name] = None
            if out[name] is not None:
                break
    return out


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

    def _num(v: Any) -> Optional[float]:
        return float(v) if v is not None else None

    fin_records_data = []
    for fr in financial_records:
        fin_records_data.append({
            "period_start": fr.period_start.isoformat() if fr.period_start else None,
            "revenue": _num(fr.revenue),
            "cogs": _num(fr.cogs),
            "opex": _num(fr.opex),
            "payroll": _num(fr.payroll),
            "cash_balance": _num(fr.cash_balance),
            "mrr": _num(fr.mrr),
            "arr": _num(fr.arr),
            "gross_margin": _num(fr.gross_margin),
            "net_burn": _num(fr.net_burn),
            "runway_months": _num(fr.runway_months),
            "headcount": fr.headcount,
            "customers": fr.customers,
        })

    extracted_metrics = _known_metrics(metrics)
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


def _fmt_money(v: float) -> str:
    return f"${v:,.0f}"


def _fmt_pct(v: float) -> str:
    return f"{v:.1f}%"


# (label, metric key, formatter) — the order they appear in the prompt.
_PROMPT_METRICS = [
    ("MRR", "mrr", _fmt_money),
    ("ARR", "arr", _fmt_money),
    ("Monthly Revenue", "monthly_revenue", _fmt_money),
    ("Net Burn (monthly)", "burn_rate", _fmt_money),
    ("Cash Balance", "cash_balance", _fmt_money),
    ("Runway", "runway_months", lambda v: f"{v:.1f} months"),
    ("Gross Margin", "gross_margin", _fmt_pct),
    ("Revenue Growth MoM", "revenue_growth", _fmt_pct),
    ("Customers", "customers", lambda v: f"{v:,.0f}"),
    ("Monthly Churn", "churn_rate", _fmt_pct),
    ("CAC", "cac", _fmt_money),
    ("LTV", "ltv", _fmt_money),
    ("LTV/CAC", "ltv_cac_ratio", lambda v: f"{v:.1f}x"),
    ("Net Revenue Retention", "ndr", _fmt_pct),
]


def _format_financial_records(records: List[Dict[str, Any]]) -> str:
    lines = []
    for fr in records[:12]:
        parts = [fr.get("period_start") or "unknown period"]
        for label, key in (
            ("revenue", "revenue"), ("cogs", "cogs"), ("opex", "opex"),
            ("payroll", "payroll"), ("cash", "cash_balance"), ("net burn", "net_burn"),
        ):
            val = fr.get(key)
            if val is not None:
                parts.append(f"{label} ${val:,.0f}")
        if fr.get("headcount") is not None:
            parts.append(f"headcount {fr['headcount']}")
        if fr.get("customers") is not None:
            parts.append(f"customers {fr['customers']}")
        lines.append("- " + ", ".join(parts))
    return "\n".join(lines)


def _build_section_prompt(doc_type: str, section: str, context: Dict, custom_instructions: Optional[str] = None) -> str:
    company = context["company"]
    m = context["metrics"]

    known_lines = []
    unknown_labels = []
    for label, key, fmt in _PROMPT_METRICS:
        val = m.get(key)
        if val is None:
            unknown_labels.append(label)
        else:
            known_lines.append(f"{label}: {fmt(val)}")

    data_block = (
        f"Company: {company['name']} ({company.get('industry') or 'industry not available'}, "
        f"{company.get('stage') or 'stage not available'})\n"
    )
    data_block += "\n".join(known_lines) + ("\n" if known_lines else "")
    if unknown_labels:
        data_block += "Not available (no reported data): " + ", ".join(unknown_labels) + "\n"
    data_block += f"Data Confidence: {context.get('confidence', 50)}%\n"

    records_text = _format_financial_records(context.get("financial_records") or [])

    scenarios_text = ""
    for sc in context.get("scenarios", [])[:3]:
        sim = sc.get("latest_simulation") or {}
        runway = sim.get("runway") or {}
        p50 = runway.get("p50") if isinstance(runway, dict) else None
        if p50 is not None:
            scenarios_text += f"- {sc['name']}: P50 runway {p50} months\n"
        else:
            scenarios_text += f"- {sc['name']}: no simulation result yet\n"

    prompt = (
        f"You are a top-tier startup CFO and strategy consultant.\n"
        f"Document type: {doc_type.replace('-', ' ').title()}\n"
        f"Section: {section}\n\n"
        f"Company Data:\n{data_block}\n"
    )

    if records_text:
        prompt += f"Monthly Financial Records (most recent first):\n{records_text}\n\n"

    if scenarios_text:
        prompt += f"Active Scenarios:\n{scenarios_text}\n"

    if custom_instructions:
        prompt += f"\nAdditional Instructions: {custom_instructions}\n"

    prompt += (
        f"\nWrite the '{section}' section for this {doc_type.replace('-', ' ')}. "
        f"Use only the numbers given above. Never invent, estimate or assume a figure "
        f"that is not listed; where a metric is marked not available, say it is not yet "
        f"tracked rather than giving a number. "
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

    succeeded = [s for s in sections_result if s["model_used"] != "error"]

    # No "your document is ready" email for a document with nothing in it.
    if succeeded:
        try:
            from server.email.activity_triggers import trigger_document_generated_email
            trigger_document_generated_email(
                user_email=current_user.email,
                company_name=company.name,
                doc_type=request.doc_type,
                doc_name=doc_config["name"],
                sections_count=len(succeeded),
                sections=[{"title": s["title"]} for s in succeeded],
            )
        except Exception as e:
            logger.warning(f"Doc generator email trigger failed: {e}")

    return {
        "doc_type": doc_config,
        "sections": sections_result,
        "company": context["company"],
        "metrics": context["metrics"],
        "generated_at": datetime.utcnow().isoformat(),
    }
