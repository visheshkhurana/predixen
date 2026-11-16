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

    fundraising_rounds = []
    try:
        from server.models.fundraising import FundraisingRound
        rounds = (
            db.query(FundraisingRound)
            .filter(FundraisingRound.company_id == company.id)
            .order_by(FundraisingRound.created_at.desc())
            .limit(5)
            .all()
        )
        for r in rounds:
            round_dict = {
                "name": r.name,
                "target_raise": float(r.target_raise) if r.target_raise else None,
                "status": r.status,
                "pre_money_valuation": float(r.pre_money_valuation) if getattr(r, 'pre_money_valuation', None) else None,
                "use_of_funds": getattr(r, 'use_of_funds', None) or getattr(r, 'notes', None),
            }
            fundraising_rounds.append(round_dict)
    except Exception:
        pass

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

    # Unit economics the truth scan invented from defaults (CAC, LTV, LTV:CAC,
    # customers, NDR...) are never presented to a board as the company's own.
    # CAC / LTV come from the founder's record, then a D2C month's marketing
    # spend / new customers, then real truth-scan values -- the same rule as
    # /metrics/computed. Anything still unknown is None ("not available").
    from server.services.d2c_months import latest_d2c_cac
    from server.truth.invented_metrics import (
        resolve_unit_economics,
        strip_invented_unit_economics,
    )
    unit_econ = resolve_unit_economics(
        metrics,
        financial_records[0] if financial_records else None,
        latest_d2c_cac(db, company.id),
    )
    real_metrics = strip_invented_unit_economics(metrics)

    def _known(value: float) -> Optional[float]:
        return value if value and value > 0 else None

    latest_customers = financial_records[0].customers if financial_records else None
    customers = _known(
        float(latest_customers or 0)
        or extract_metric_value(real_metrics.get("customers"), 0)
        or extract_metric_value(real_metrics.get("customer_count"), 0)
    )
    latest_ndr = financial_records[0].ndr if financial_records else None
    ndr = _known(float(latest_ndr or 0) or extract_metric_value(real_metrics.get("net_revenue_retention"), 0))

    extracted_metrics = {
        "monthly_revenue": extract_metric_value(metrics.get("monthly_revenue"), 0),
        "mrr": extract_metric_value(metrics.get("mrr"), 0),
        "arr": extract_metric_value(metrics.get("arr"), 0),
        "burn_rate": extract_metric_value(metrics.get("net_burn"), 0),
        "cash_balance": extract_metric_value(metrics.get("cash_balance"), 0),
        "runway_months": extract_metric_value(metrics.get("runway_p50"), 0),
        "gross_margin": extract_metric_value(metrics.get("gross_margin"), 0),
        "revenue_growth": extract_metric_value(metrics.get("revenue_growth_mom"), 0),
        "customers": customers,
        "churn_rate": extract_metric_value(metrics.get("churn_rate"), 0),
        "cac": _known(unit_econ["cac"]),
        "cac_source": unit_econ["cac_source"],
        "cac_period": unit_econ["cac_period"],
        "ltv": _known(unit_econ["ltv"]),
        "ltv_cac_ratio": _known(unit_econ["ltv_cac_ratio"]),
        "ndr": ndr,
        "headcount": extract_metric_value(metrics.get("headcount"), 0),
        "is_profitable": bool(extract_metric_value(metrics.get("is_profitable"), False)),
        "runway_sustainable": bool(extract_metric_value(metrics.get("runway_sustainable"), False)),
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
        "truth_scan_raw": real_metrics,
        "fundraising_rounds": fundraising_rounds,
        "generated_at": datetime.utcnow().isoformat(),
    }


def _indian_grouping(value: float) -> str:
    """12,50,000 style grouping: Indian founders and investors read lakhs."""
    neg = value < 0
    digits = f"{abs(value):.0f}"
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    return ("-" if neg else "") + digits


def _money(value: float, currency: Optional[str]) -> str:
    code = (currency or "USD").upper()
    value = float(value or 0)
    if code == "INR":
        return f"\u20b9{_indian_grouping(value)}"
    symbol = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "SGD": "S$"}.get(code)
    return f"{symbol}{value:,.0f}" if symbol else f"{code} {value:,.0f}"


def _burn_phrase(burn: float, currency: Optional[str]) -> str:
    """Net burn in words. Negative burn is a monthly surplus, never '-X burn'."""
    burn = float(burn or 0)
    if burn > 0:
        return f"{_money(burn, currency)}/month net burn"
    if burn < 0:
        return f"not burning cash (monthly surplus of {_money(-burn, currency)})"
    return "break-even (no net burn)"


def _runway_phrase(metrics: Dict[str, Any]) -> str:
    if metrics.get("runway_sustainable") or float(metrics.get("burn_rate") or 0) < 0:
        return "runway is not a constraint while revenue covers costs"
    return f"approximately {float(metrics.get('runway_months') or 0):.1f} months of runway"


def _cac_basis(metrics: Dict[str, Any]) -> str:
    if metrics.get("cac_source") == "d2c_month" and metrics.get("cac_period"):
        return f" (marketing spend / new customers, {metrics['cac_period'][:7]})"
    return ""


def _unit_economics_lines(metrics: Dict[str, Any], data: Dict[str, Any]) -> str:
    """Prompt lines for CAC / LTV / LTV:CAC / NDR. Unknown values are stated as
    not available so the model never fills them in or reads 0 as measured."""
    currency = (data.get("company") or {}).get("currency")
    cac, ltv, ratio, ndr = (metrics.get(k) for k in ("cac", "ltv", "ltv_cac_ratio", "ndr"))
    na = "not available (no data; do not estimate)"
    return (
        f"CAC: {_money(cac, currency) + _cac_basis(metrics) if cac else na}\n"
        f"LTV: {_money(ltv, currency) if ltv else na}\n"
        f"LTV/CAC: {f'{ratio:.1f}x' if ratio else na}\n"
        f"NDR: {f'{ndr:.0f}%' if ndr else na}\n"
    )


def _unit_economics_sentence(metrics: Dict[str, Any], data: Dict[str, Any]) -> str:
    """Rule-based unit-economics text: only metrics backed by data are named."""
    currency = (data.get("company") or {}).get("currency")
    cac, ltv, ratio = metrics.get("cac"), metrics.get("ltv"), metrics.get("ltv_cac_ratio")
    parts = []
    if ratio and cac and ltv:
        parts.append(
            f"LTV/CAC ratio stands at {ratio:.1f}x (LTV: {_money(ltv, currency)}, "
            f"CAC: {_money(cac, currency)})."
        )
    else:
        if cac:
            parts.append(f"CAC is {_money(cac, currency)}{_cac_basis(metrics)}.")
        if ltv:
            parts.append(f"LTV is {_money(ltv, currency)}.")
        missing = [n for n, v in (("CAC", cac), ("LTV", ltv), ("LTV/CAC", ratio)) if not v]
        if missing:
            parts.append(f"{', '.join(missing)} not available yet (needs customer and marketing data).")
    gm = metrics.get("gross_margin")
    if gm:
        parts.append(f"Gross margin is {gm:.1f}%.")
    return " ".join(parts)


def _build_narrative_prompt(template_id: str, section: Dict, data: Dict) -> str:
    company_name = data["company"]["name"]
    metrics = data["metrics"]
    section_title = section["title"]
    cur = (data.get("company") or {}).get("currency")

    runway_val = metrics.get('runway_months', 0)
    runway_display = "Sustainable (profitable)" if metrics.get('runway_sustainable') else f"{runway_val:.1f} months"

    metrics_summary = (
        f"Company: {company_name}\n"
        f"Currency: {(cur or 'USD').upper()} (state every amount in this currency)\n"
        f"MRR: {_money(metrics.get('mrr', 0), cur)}, ARR: {_money(metrics.get('arr', 0), cur)}\n"
        f"Monthly Revenue: {_money(metrics.get('monthly_revenue', 0), cur)}\n"
        f"Net Burn: {_burn_phrase(metrics.get('burn_rate', 0), cur)}\n"
        f"Cash Balance: {_money(metrics.get('cash_balance', 0), cur)}\n"
        f"Runway: {runway_display}\n"
        f"Profitable: {'Yes' if metrics.get('is_profitable') else 'No'}\n"
        f"Gross Margin: {metrics.get('gross_margin', 0):.1f}%\n"
        f"Revenue Growth MoM: {metrics.get('revenue_growth', 0):.1f}%\n"
        f"Headcount: {int(metrics.get('headcount', 0))}\n"
        f"Churn Rate: {metrics.get('churn_rate', 0):.1f}%\n"
        f"{_unit_economics_lines(metrics, data)}"
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

    template_guidance = {
        "monthly-update": (
            "This is a MONTHLY BOARD UPDATE for existing board members and investors. "
            "Focus on month-over-month changes, operational progress, and what happened since last update. "
            "Tone: transparent, metric-driven, concise. Highlight wins and flag concerns early. "
            "Board members want to see trends, not just snapshots."
        ),
        "fundraising-prep": (
            "This is an INVESTOR-FACING FUNDRAISING DECK for prospective investors. "
            "Focus on traction, market opportunity, unit economics strength, and growth trajectory. "
            "Tone: compelling, confident, forward-looking. Emphasize why this is a great investment. "
            "Investors want to see momentum, defensibility, and efficient capital deployment."
        ),
        "scenario-analysis": (
            "This is a SCENARIO ANALYSIS DECK for strategic planning discussions. "
            "Focus on comparing different paths forward, risk-reward tradeoffs, and sensitivity to assumptions. "
            "Tone: analytical, balanced, thorough. Present multiple options with clear trade-offs. "
            "Stakeholders want to understand downside risks and upside potential of each path."
        ),
    }

    template_context = template_guidance.get(template_id, "Write a professional board deck narrative.")

    prompt = (
        f"You are a CFO assistant creating a board deck section.\n"
        f"Template: {template_id}\n"
        f"Section: {section_title}\n\n"
        f"TEMPLATE CONTEXT: {template_context}\n\n"
        f"Financial Data:\n{metrics_summary}\n"
    )

    fundraising_text = ""
    for fr in data.get("fundraising_rounds", [])[:3]:
        name = fr.get("name", "Round")
        target = fr.get("target_raise")
        status = fr.get("status", "")
        use_of_funds = fr.get("use_of_funds", "")
        pre_money = fr.get("pre_money_valuation")
        line = f"- {name}: Target {_money(target, cur)}" if target else f"- {name}"
        if pre_money:
            line += f" at {_money(pre_money, cur)} pre-money"
        if status:
            line += f" ({status})"
        fundraising_text += line + "\n"
        if use_of_funds:
            fundraising_text += f"  Use of funds: {use_of_funds}\n"

    if scenarios_text:
        prompt += f"Scenarios:\n{scenarios_text}\n"
    if decisions_text:
        prompt += f"Recent Decisions:\n{decisions_text}\n"
    if fundraising_text:
        prompt += f"Fundraising Rounds:\n{fundraising_text}\n"

    prompt += (
        f"\nWrite a concise, professional narrative for the '{section_title}' section "
        f"of a {template_id.replace('-', ' ')} board deck. "
        f"Use specific numbers from the data. Keep it to 2-3 paragraphs. "
        f"Be direct and actionable. Do not use markdown headers. "
        f"Tailor the tone and emphasis to match the template context above."
    )

    if section_title == "Use of Funds & Milestones" and fundraising_text:
        prompt += (
            " Include specific use of funds allocation from fundraising data. "
            "Break down how capital will be deployed across hiring, product, marketing, and operations."
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

    try:
        from server.email.activity_triggers import trigger_document_generated_email
        trigger_document_generated_email(
            user_email=current_user.email,
            company_name=company.name,
            doc_type=request.templateId,
            doc_name=template["name"],
            sections_count=len(sections_result),
            sections=[{"title": s["title"]} for s in sections_result],
        )
    except Exception as e:
        logger.warning(f"Board export email trigger failed: {e}")

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
    cur = (data.get("company") or {}).get("currency")
    m = lambda v: _money(v, cur)  # noqa: E731
    burn_words = _burn_phrase(burn, cur)
    runway_words = _runway_phrase(metrics)

    if "executive" in title.lower() or "overview" in title.lower():
        return (
            f"{company_name} generated {m(revenue)} in monthly revenue with "
            f"{growth:.1f}% month-over-month growth. The company is at {burn_words} "
            f"with {m(cash)} in cash; {runway_words}."
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
        return _unit_economics_sentence(metrics, data)
    elif "traction" in title.lower():
        customers = metrics.get("customers")
        with_customers = f" with {customers:,.0f} customers" if customers else ""
        return (
            f"{company_name} has {m(revenue)} in monthly revenue growing at "
            f"{growth:.1f}% MoM{with_customers}."
        )
    elif "scenario" in title.lower() or "comparison" in title.lower():
        scenarios = data.get("scenarios", [])
        if scenarios:
            names = ", ".join([s["name"] for s in scenarios[:3]])
            return f"Active scenarios under analysis: {names}."
        return "No scenarios available for comparison."
    elif "risk" in title.lower() or "sensitivity" in title.lower():
        if float(burn or 0) <= 0:
            return (
                f"Revenue currently covers costs ({burn_words}); key risks are margin "
                f"pressure and growth deceleration."
            )
        return (
            f"With {runway_words} at {burn_words}, "
            f"key risks include cash depletion and growth deceleration."
        )
    elif "funds" in title.lower() or "milestone" in title.lower():
        return (
            f"Current cash position of {m(cash)}, at {burn_words}; {runway_words}."
        )
    elif "projection" in title.lower():
        sim = data.get("simulation", {})
        runway_data = sim.get("runway", {})
        p50 = runway_data.get("p50", runway)
        return f"Financial projections show a median runway of {p50:.1f} months based on current trajectory."
    elif "recommendation" in title.lower():
        return (
            f"Based on current metrics ({growth:.1f}% MoM growth; {runway_words}), "
            f"focus areas include optimizing burn rate and accelerating revenue growth."
        )
    else:
        return (
            f"{company_name}: Revenue {m(revenue)}/mo, {burn_words}, "
            f"Cash {m(cash)}, {runway_words}, Growth {growth:.1f}% MoM."
        )
