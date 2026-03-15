"""
Data Anonymization Service for Cross-Company Learning.

Strips identifying information from company metrics and decision outcomes,
returning only industry, stage, and normalized metrics for aggregation
into the shared intelligence pool.
"""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from server.models.company import Company
from server.models.company_decision import CompanyDecision
from server.models.financial import FinancialRecord

logger = logging.getLogger(__name__)


def _classify_revenue_range(revenue: float) -> str:
    if revenue <= 0:
        return "pre_revenue"
    elif revenue < 10000:
        return "$0-10K"
    elif revenue < 50000:
        return "$10K-50K"
    elif revenue < 200000:
        return "$50K-200K"
    elif revenue < 1000000:
        return "$200K-1M"
    return "$1M+"


def _classify_burn_range(burn: float) -> str:
    if burn <= 0:
        return "profitable"
    elif burn < 20000:
        return "$0-20K"
    elif burn < 50000:
        return "$20K-50K"
    elif burn < 150000:
        return "$50K-150K"
    return "$150K+"


def _classify_employee_range(headcount: int) -> str:
    if headcount <= 5:
        return "1-5"
    elif headcount <= 15:
        return "6-15"
    elif headcount <= 50:
        return "16-50"
    elif headcount <= 200:
        return "51-200"
    return "200+"


def _classify_runway_range(runway: float) -> str:
    if runway <= 0:
        return "critical"
    elif runway < 6:
        return "0-6mo"
    elif runway < 12:
        return "6-12mo"
    elif runway < 18:
        return "12-18mo"
    elif runway < 24:
        return "18-24mo"
    return "24mo+"


def anonymize_company_metrics(db: Session, company_id: int) -> Optional[Dict[str, Any]]:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return None

    if not getattr(company, "data_sharing_enabled", False):
        return None

    latest_fin = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(FinancialRecord.period_start.desc())
        .first()
    )

    prev_fin = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(FinancialRecord.period_start.desc())
        .offset(1)
        .first()
    )

    revenue = float(latest_fin.mrr or latest_fin.revenue or 0) if latest_fin else 0
    prev_revenue = float(prev_fin.mrr or prev_fin.revenue or 0) if prev_fin else 0
    burn = float(latest_fin.net_burn or 0) if latest_fin and hasattr(latest_fin, "net_burn") else 0
    runway = float(latest_fin.runway_months or 0) if latest_fin and hasattr(latest_fin, "runway_months") else 0
    headcount = int(latest_fin.headcount or 0) if latest_fin and hasattr(latest_fin, "headcount") else 0
    gross_margin = float(latest_fin.gross_margin or 0) if latest_fin and hasattr(latest_fin, "gross_margin") else 0

    growth_pct = ((revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

    return {
        "industry": (company.industry or "unknown").lower(),
        "stage": (company.stage or "unknown").lower(),
        "revenue_range": _classify_revenue_range(revenue),
        "burn_range": _classify_burn_range(burn),
        "runway_range": _classify_runway_range(runway),
        "employee_range": _classify_employee_range(headcount),
        "gross_margin_pct": round(gross_margin, 0),
        "growth_pct": round(growth_pct, 1),
        "normalized_metrics": {
            "revenue": revenue,
            "burn": burn,
            "runway_months": runway,
            "headcount": headcount,
            "gross_margin": gross_margin,
        },
    }


def anonymize_decision_outcome(db: Session, decision_id: str) -> Optional[Dict[str, Any]]:
    decision = db.query(CompanyDecision).filter(CompanyDecision.id == decision_id).first()
    if not decision:
        return None

    company = db.query(Company).filter(Company.id == decision.company_id).first()
    if not company or not getattr(company, "data_sharing_enabled", False):
        return None

    title_lower = (decision.title or "").lower()
    decision_type = "general"
    type_keywords = {
        "hiring": ["hire", "team", "headcount", "recruit", "talent"],
        "pricing": ["price", "pricing", "tier", "plan", "monetiz"],
        "cost_reduction": ["cut", "reduce", "cost", "optimize", "save", "lean"],
        "fundraising": ["raise", "fundrais", "round", "investor", "capital", "fund"],
        "growth": ["growth", "market", "expand", "scale", "acquire", "channel"],
        "product": ["product", "feature", "launch", "build", "ship", "release"],
        "retention": ["churn", "retain", "retention", "nps", "satisfaction"],
    }
    for dtype, keywords in type_keywords.items():
        if any(kw in title_lower for kw in keywords):
            decision_type = dtype
            break

    tags = []
    if hasattr(decision, "tags") and decision.tags:
        try:
            tags = decision.tags if isinstance(decision.tags, list) else []
        except Exception:
            tags = []

    outcome_positive = (
        decision.status in ("accepted", "implemented", "resolved", "completed", "decided")
        and (decision.confidence or "medium") in ("high", "medium")
    )

    outcome_json = {}
    if hasattr(decision, "recommendation_json") and decision.recommendation_json:
        rec = decision.recommendation_json
        if isinstance(rec, dict):
            outcome_json = {
                "had_simulation": bool(rec.get("simulation_id")),
                "impact_estimate": rec.get("expected_impact"),
            }

    return {
        "industry": (company.industry or "unknown").lower(),
        "stage": (company.stage or "unknown").lower(),
        "decision_type": decision_type,
        "tags": tags,
        "status": decision.status,
        "confidence": decision.confidence or "medium",
        "outcome_positive": outcome_positive,
        "outcome_details": outcome_json,
    }


def get_opted_in_company_ids(db: Session) -> List[int]:
    companies = (
        db.query(Company.id)
        .filter(Company.data_sharing_enabled == True)
        .all()
    )
    return [c.id for c in companies]


def anonymize_all_opted_in_metrics(db: Session) -> List[Dict[str, Any]]:
    company_ids = get_opted_in_company_ids(db)
    results = []
    for cid in company_ids:
        metrics = anonymize_company_metrics(db, cid)
        if metrics:
            results.append(metrics)
    return results
