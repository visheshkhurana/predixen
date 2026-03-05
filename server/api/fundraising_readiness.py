from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging
import math

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.models.financial import FinancialRecord
from server.models.simulation_run import SimulationRun
from server.api.simulations import extract_metric_value

logger = logging.getLogger(__name__)

router = APIRouter(tags=["fundraising-readiness"])


def _score_runway(months: float) -> int:
    if months < 9:
        return 20
    elif months < 15:
        return 50
    elif months < 24:
        return 75
    else:
        return 95


def _score_growth(growth_pct: float) -> int:
    if growth_pct < 5:
        return 20
    elif growth_pct < 10:
        return 50
    elif growth_pct < 20:
        return 75
    else:
        return 95


def _score_unit_economics(ltv_cac: float) -> int:
    if ltv_cac < 2:
        return 20
    elif ltv_cac < 3:
        return 50
    elif ltv_cac < 4:
        return 75
    else:
        return 95


def _compute_readiness(
    metrics: Dict[str, Any],
    latest_record: Optional[FinancialRecord],
    truth_scan: Optional[TruthScan],
) -> Dict[str, Any]:
    ts_runway = extract_metric_value(metrics.get("runway_months"), 0)
    fr_runway = float(latest_record.runway_months) if latest_record and latest_record.runway_months else 0
    runway_months = ts_runway if ts_runway > 0 else fr_runway

    ts_growth = extract_metric_value(metrics.get("revenue_growth_mom"), 0)
    fr_growth = float(latest_record.mom_growth) if latest_record and latest_record.mom_growth else 0
    growth_pct = ts_growth if ts_growth != 0 else fr_growth
    if abs(growth_pct) < 1:
        growth_pct = growth_pct * 100

    ts_ltv_cac = extract_metric_value(metrics.get("ltv_cac_ratio"), 0)
    fr_ltv_cac = float(latest_record.ltv_cac_ratio) if latest_record and latest_record.ltv_cac_ratio else 0
    ltv_cac = ts_ltv_cac if ts_ltv_cac > 0 else fr_ltv_cac

    confidence_score = 60
    if truth_scan and truth_scan.outputs_json:
        cs = truth_scan.outputs_json.get("confidence_score")
        if cs is not None:
            confidence_score = float(cs)
        else:
            overall = truth_scan.outputs_json.get("overall_confidence")
            if overall is not None:
                confidence_score = float(overall)

    runway_score = _score_runway(runway_months)
    growth_score = _score_growth(growth_pct)
    unit_econ_score = _score_unit_economics(ltv_cac)
    market_score = 60
    narrative_score = min(100, max(0, int(confidence_score)))

    weights = {
        "runway": 0.25,
        "growth": 0.25,
        "unit_economics": 0.20,
        "market_timing": 0.15,
        "narrative_quality": 0.15,
    }

    overall = (
        runway_score * weights["runway"]
        + growth_score * weights["growth"]
        + unit_econ_score * weights["unit_economics"]
        + market_score * weights["market_timing"]
        + narrative_score * weights["narrative_quality"]
    )
    overall = round(overall, 1)

    if overall < 40:
        status = "not-ready"
    elif overall < 70:
        status = "getting-close"
    elif overall < 85:
        status = "ready"
    else:
        status = "optimal"

    breakdown = {
        "runway": {"score": runway_score, "weight": weights["runway"], "value": round(runway_months, 1), "label": "Runway"},
        "growth": {"score": growth_score, "weight": weights["growth"], "value": round(growth_pct, 1), "label": "Growth"},
        "unit_economics": {"score": unit_econ_score, "weight": weights["unit_economics"], "value": round(ltv_cac, 2), "label": "Unit Economics (LTV:CAC)"},
        "market_timing": {"score": market_score, "weight": weights["market_timing"], "value": None, "label": "Market Timing"},
        "narrative_quality": {"score": narrative_score, "weight": weights["narrative_quality"], "value": round(confidence_score, 1), "label": "Narrative / Data Quality"},
    }

    recommendations = []
    if runway_score < 70:
        recommendations.append({
            "category": "runway",
            "issue": f"Runway is {runway_months:.0f} months — below the 15-month threshold investors prefer.",
            "action": "Cut burn or raise a bridge round to extend runway above 18 months before approaching investors.",
            "currentValue": f"{runway_months:.0f} months",
            "targetValue": "18+ months",
            "impact": "high" if runway_score < 40 else "medium",
        })
    if growth_score < 70:
        recommendations.append({
            "category": "growth",
            "issue": f"MoM revenue growth is {growth_pct:.1f}% — below the 10% benchmark.",
            "action": "Focus on product-led growth or targeted sales to accelerate MoM growth above 10%.",
            "currentValue": f"{growth_pct:.1f}%",
            "targetValue": "10%+ MoM",
            "impact": "high" if growth_score < 40 else "medium",
        })
    if unit_econ_score < 70:
        recommendations.append({
            "category": "unit_economics",
            "issue": f"LTV:CAC ratio is {ltv_cac:.1f}x — below the 3x target.",
            "action": "Improve retention to increase LTV or optimize acquisition channels to lower CAC.",
            "currentValue": f"{ltv_cac:.1f}x",
            "targetValue": "3x+",
            "impact": "high" if unit_econ_score < 40 else "medium",
        })
    if narrative_score < 70:
        recommendations.append({
            "category": "narrative_quality",
            "issue": f"Data quality / confidence score is {confidence_score:.0f}% — investors need reliable data.",
            "action": "Upload audited financials and reconcile any discrepancies flagged by Truth Scan.",
            "currentValue": f"{confidence_score:.0f}%",
            "targetValue": "80%+",
            "impact": "medium",
        })

    months_to_peak = 0
    if growth_score >= 70 and runway_score >= 70:
        months_to_peak = 1
    elif growth_score >= 50:
        months_to_peak = max(1, int((70 - overall) / 3))
    else:
        months_to_peak = max(3, int((70 - overall) / 2))
    months_to_peak = max(1, min(months_to_peak, 18))

    raise_window = {
        "optimalStartMonth": months_to_peak,
        "optimalEndMonth": months_to_peak + 3,
        "estimatedDurationMonths": 4,
        "reasoning": f"Based on current trajectory, your score will peak in ~{months_to_peak} months. Plan 4-6 months for the full fundraise process.",
    }

    return {
        "overall": overall,
        "breakdown": breakdown,
        "status": status,
        "recommendations": recommendations,
        "raiseWindow": raise_window,
    }


@router.get("/companies/{company_id}/fundraising/readiness")
def get_fundraising_readiness(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)

    truth_scan = (
        db.query(TruthScan)
        .filter(TruthScan.company_id == company.id)
        .order_by(TruthScan.created_at.desc())
        .first()
    )

    metrics = {}
    if truth_scan and truth_scan.outputs_json:
        metrics = truth_scan.outputs_json.get("metrics", {})

    latest_record = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company.id)
        .order_by(FinancialRecord.period_end.desc())
        .first()
    )

    result = _compute_readiness(metrics, latest_record, truth_scan)
    return result


class OnePagerRequest(BaseModel):
    context: Optional[Dict[str, Any]] = None


@router.post("/companies/{company_id}/fundraising/one-pager")
def generate_one_pager(
    company_id: int,
    request: OnePagerRequest = OnePagerRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)

    truth_scan = (
        db.query(TruthScan)
        .filter(TruthScan.company_id == company.id)
        .order_by(TruthScan.created_at.desc())
        .first()
    )

    metrics = {}
    if truth_scan and truth_scan.outputs_json:
        metrics = truth_scan.outputs_json.get("metrics", {})

    latest_record = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company.id)
        .order_by(FinancialRecord.period_end.desc())
        .first()
    )

    revenue = extract_metric_value(metrics.get("monthly_revenue"), 0)
    if not revenue and latest_record and latest_record.revenue:
        revenue = float(latest_record.revenue)

    growth = extract_metric_value(metrics.get("revenue_growth_mom"), 0)
    if not growth and latest_record and latest_record.mom_growth:
        growth = float(latest_record.mom_growth)

    runway = extract_metric_value(metrics.get("runway_months"), 0)
    if not runway and latest_record and latest_record.runway_months:
        runway = float(latest_record.runway_months)

    customers = extract_metric_value(metrics.get("customers"), 0)
    if not customers and latest_record and latest_record.customers:
        customers = int(latest_record.customers)

    ltv_cac = extract_metric_value(metrics.get("ltv_cac_ratio"), 0)
    if not ltv_cac and latest_record and latest_record.ltv_cac_ratio:
        ltv_cac = float(latest_record.ltv_cac_ratio)

    gross_margin = extract_metric_value(metrics.get("gross_margin"), 0)
    if not gross_margin and latest_record and latest_record.gross_margin is not None:
        gross_margin = float(latest_record.gross_margin)

    company_context = {
        "name": company.name,
        "industry": company.industry or "Technology",
        "stage": company.stage or "Early Stage",
        "revenue": revenue,
        "growth": growth,
        "runway": runway,
        "customers": customers,
        "ltv_cac": ltv_cac,
        "gross_margin": gross_margin,
    }

    try:
        from server.lib.llm.llm_router import get_llm_router, TaskType

        llm = get_llm_router(
            db_session=db,
            company_id=company.id,
            user_id=current_user.id,
        )

        prompt = f"""Generate a concise investment one-pager memo for {company_context['name']}.

Company Details:
- Industry: {company_context['industry']}
- Stage: {company_context['stage']}
- Monthly Revenue: ${revenue:,.0f}
- MoM Growth: {growth:.1f}%
- Runway: {runway:.0f} months
- Customers: {int(customers)}
- LTV:CAC Ratio: {ltv_cac:.1f}x
- Gross Margin: {gross_margin:.0f}%

Generate a professional investment memo in markdown with these sections:
# {company_context['name']} — Investment One-Pager

## Problem
## Solution
## Traction
## Market
## Team
## Financials
## The Ask

Use the financial data provided. Keep each section to 2-3 sentences. Be specific with numbers where available."""

        response = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            task_type=TaskType.CREATIVE_WRITING,
            temperature=0.7,
            max_tokens=2000,
        )

        markdown = response.get("content", "")
        if not markdown:
            markdown = _generate_fallback_memo(company_context)

        return {"markdown": markdown, "company": company_context}

    except Exception as e:
        logger.warning(f"LLM generation failed, using fallback: {e}")
        markdown = _generate_fallback_memo(company_context)
        return {"markdown": markdown, "company": company_context}


def _generate_fallback_memo(ctx: Dict[str, Any]) -> str:
    growth_display = f"{ctx['growth']:.1f}%" if abs(ctx["growth"]) < 1 else f"{ctx['growth'] * 100:.0f}%"
    if abs(ctx["growth"]) < 1:
        growth_display = f"{ctx['growth'] * 100:.1f}%"
    else:
        growth_display = f"{ctx['growth']:.1f}%"

    return f"""# {ctx['name']} — Investment One-Pager

## Problem
{ctx['name']} operates in the {ctx['industry']} space, addressing key challenges faced by its target customers.

## Solution
The company provides a differentiated solution with demonstrated product-market fit and growing adoption.

## Traction
- **Monthly Revenue:** ${ctx['revenue']:,.0f}
- **MoM Growth:** {growth_display}
- **Customers:** {int(ctx['customers'])}
- **LTV:CAC:** {ctx['ltv_cac']:.1f}x

## Market
The {ctx['industry']} market represents a significant opportunity with strong tailwinds for innovative solutions.

## Team
The founding team brings deep domain expertise in {ctx['industry']} with prior startup and enterprise experience.

## Financials
- **Gross Margin:** {ctx['gross_margin']:.0f}%
- **Runway:** {ctx['runway']:.0f} months
- **Stage:** {ctx['stage']}

## The Ask
{ctx['name']} is raising its next round to accelerate growth, expand the team, and capture market share.
"""
