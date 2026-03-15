"""
Founder Intelligence Graph Service.

Provides cross-company intelligence through graph-like relationship
analysis using PostgreSQL. Connects companies, founders, metrics,
decisions, strategies, and outcomes to enable:
- Cross-company benchmarking
- Company similarity matching
- Decision pattern discovery
- AI strategy recommendations
- Event-driven graph ingestion pipeline
- Digital Twin synchronization
- AI-powered graph analysis
- Graph-powered simulation recommendations
- Network visualization data
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case, text

from server.models.company import Company
from server.models.company_decision import CompanyDecision
from server.models.financial import FinancialRecord
from server.models.company_state import CompanyState
from server.models.simulation_run import SimulationRun
from server.models.scenario import Scenario
from server.models.twin_event import TwinEvent

logger = logging.getLogger(__name__)

GRAPH_EVENT_TYPES = [
    "revenue_update",
    "expense_update",
    "decision_made",
    "decision_outcome",
    "simulation_run",
    "state_update",
    "connector_sync",
    "data_ingestion",
    "fundraising_update",
    "headcount_change",
]


STRATEGY_TYPES = {
    "cost_reduction": ["cut", "reduce", "cost", "optimize", "save", "lean"],
    "hiring": ["hire", "team", "headcount", "recruit", "talent"],
    "pricing": ["price", "pricing", "tier", "plan", "monetiz"],
    "fundraising": ["raise", "fundrais", "round", "investor", "capital", "fund"],
    "growth": ["growth", "market", "expand", "scale", "acquire", "channel"],
    "product": ["product", "feature", "launch", "build", "ship", "release"],
    "retention": ["churn", "retain", "retention", "nps", "satisfaction"],
    "partnership": ["partner", "integration", "alliance", "strategic"],
}


def _classify_decision_type(title: str) -> str:
    title_lower = (title or "").lower()
    for dtype, keywords in STRATEGY_TYPES.items():
        if any(kw in title_lower for kw in keywords):
            return dtype
    return "general"


def _classify_mrr_range(mrr: float) -> str:
    if mrr <= 0:
        return "pre_revenue"
    elif mrr < 5000:
        return "$0-5K"
    elif mrr < 25000:
        return "$5K-25K"
    elif mrr < 100000:
        return "$25K-100K"
    elif mrr < 500000:
        return "$100K-500K"
    return "$500K+"


def _classify_growth_tier(growth_pct: float) -> str:
    if growth_pct < 0:
        return "declining"
    elif growth_pct < 5:
        return "flat"
    elif growth_pct < 15:
        return "moderate"
    elif growth_pct < 30:
        return "strong"
    return "hypergrowth"


def _compute_company_similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    score = 0.0
    weights = {"industry": 0.25, "stage": 0.25, "mrr_range": 0.2, "growth_tier": 0.15, "employee_range": 0.15}

    for field, weight in weights.items():
        val_a = a.get(field, "")
        val_b = b.get(field, "")
        if val_a and val_b and val_a == val_b:
            score += weight

    return round(score, 3)


def get_company_profile(db: Session, company_id: int) -> Dict[str, Any]:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return {}

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

    mrr = float(latest_fin.mrr or latest_fin.revenue or 0) if latest_fin else 0
    prev_mrr = float(prev_fin.mrr or prev_fin.revenue or 0) if prev_fin else 0
    growth_pct = ((mrr - prev_mrr) / prev_mrr * 100) if prev_mrr > 0 else 0
    headcount = int(latest_fin.headcount or 0) if latest_fin and hasattr(latest_fin, "headcount") else 0

    emp_range = "1-5"
    if headcount > 200:
        emp_range = "200+"
    elif headcount > 50:
        emp_range = "51-200"
    elif headcount > 15:
        emp_range = "16-50"
    elif headcount > 5:
        emp_range = "6-15"

    return {
        "company_id": company_id,
        "name": company.name,
        "industry": (company.industry or "unknown").lower(),
        "stage": (company.stage or "unknown").lower(),
        "mrr": mrr,
        "mrr_range": _classify_mrr_range(mrr),
        "growth_pct": round(growth_pct, 1),
        "growth_tier": _classify_growth_tier(growth_pct),
        "headcount": headcount,
        "employee_range": emp_range,
        "cash_balance": float(latest_fin.cash_balance or 0) if latest_fin else 0,
        "burn_rate": float(latest_fin.net_burn or 0) if latest_fin and hasattr(latest_fin, "net_burn") else 0,
        "runway_months": float(latest_fin.runway_months or 0) if latest_fin and hasattr(latest_fin, "runway_months") else 0,
    }


def _bulk_load_company_profiles(db: Session, exclude_id: int = None) -> Dict[int, Dict[str, Any]]:
    from sqlalchemy import func as sqlfunc

    latest_fin_subq = (
        db.query(
            FinancialRecord.company_id,
            sqlfunc.max(FinancialRecord.period_start).label("max_period"),
        )
        .group_by(FinancialRecord.company_id)
        .subquery()
    )

    query = db.query(Company, FinancialRecord).outerjoin(
        latest_fin_subq, Company.id == latest_fin_subq.c.company_id
    ).outerjoin(
        FinancialRecord,
        and_(
            FinancialRecord.company_id == Company.id,
            FinancialRecord.period_start == latest_fin_subq.c.max_period,
        ),
    )
    if exclude_id:
        query = query.filter(Company.id != exclude_id)

    profiles = {}
    for company, fin in query.all():
        mrr = float(fin.mrr or fin.revenue or 0) if fin else 0
        headcount = int(fin.headcount or 0) if fin and hasattr(fin, "headcount") else 0
        emp_range = "1-5"
        if headcount > 200:
            emp_range = "200+"
        elif headcount > 50:
            emp_range = "51-200"
        elif headcount > 15:
            emp_range = "16-50"
        elif headcount > 5:
            emp_range = "6-15"

        profiles[company.id] = {
            "company_id": company.id,
            "industry": (company.industry or "unknown").lower(),
            "stage": (company.stage or "unknown").lower(),
            "mrr": mrr,
            "mrr_range": _classify_mrr_range(mrr),
            "growth_tier": _classify_growth_tier(0),
            "headcount": headcount,
            "employee_range": emp_range,
        }

    return profiles


def find_similar_companies(
    db: Session, company_id: int, min_similarity: float = 0.25, limit: int = 10
) -> List[Dict[str, Any]]:
    target_profile = get_company_profile(db, company_id)
    if not target_profile:
        return []

    peer_profiles = _bulk_load_company_profiles(db, exclude_id=company_id)
    results = []

    for i, (cid, profile) in enumerate(peer_profiles.items()):
        similarity = _compute_company_similarity(target_profile, profile)
        if similarity >= min_similarity:
            results.append({
                "peer_rank": i + 1,
                "similarity_score": similarity,
                "industry": profile["industry"],
                "stage": profile["stage"],
                "mrr_range": profile["mrr_range"],
                "growth_tier": profile["growth_tier"],
                "employee_range": profile["employee_range"],
                "shared_traits": _get_shared_traits(target_profile, profile),
            })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    for i, r in enumerate(results):
        r["peer_rank"] = i + 1
    return results[:limit]


def _get_shared_traits(a: Dict, b: Dict) -> List[str]:
    traits = []
    if a.get("industry") == b.get("industry") and a["industry"] != "unknown":
        traits.append(f"Same industry: {a['industry']}")
    if a.get("stage") == b.get("stage") and a["stage"] != "unknown":
        traits.append(f"Same stage: {a['stage']}")
    if a.get("mrr_range") == b.get("mrr_range"):
        traits.append(f"Similar MRR: {a['mrr_range']}")
    if a.get("growth_tier") == b.get("growth_tier"):
        traits.append(f"Similar growth: {a['growth_tier']}")
    if a.get("employee_range") == b.get("employee_range"):
        traits.append(f"Similar team size: {a['employee_range']}")
    return traits


def get_decision_patterns(db: Session, company_id: int) -> Dict[str, Any]:
    decisions = db.query(CompanyDecision).limit(500).all()
    if not decisions:
        return _default_decision_patterns()

    type_stats = defaultdict(lambda: {"total": 0, "accepted": 0, "rejected": 0, "high_confidence": 0})

    for d in decisions:
        dtype = _classify_decision_type(d.title)
        type_stats[dtype]["total"] += 1
        if d.status in ("accepted", "implemented", "resolved", "completed", "decided"):
            type_stats[dtype]["accepted"] += 1
        elif d.status == "rejected":
            type_stats[dtype]["rejected"] += 1
        if d.confidence == "high":
            type_stats[dtype]["high_confidence"] += 1

    patterns = []
    for dtype, stats in type_stats.items():
        acceptance_rate = (stats["accepted"] / stats["total"] * 100) if stats["total"] > 0 else 0
        patterns.append({
            "decision_type": dtype,
            "total_count": stats["total"],
            "acceptance_rate": round(acceptance_rate, 1),
            "high_confidence_count": stats["high_confidence"],
            "rejection_count": stats["rejected"],
        })

    patterns.sort(key=lambda p: p["total_count"], reverse=True)

    recent_decisions = (
        db.query(CompanyDecision)
        .filter(CompanyDecision.company_id == company_id)
        .order_by(CompanyDecision.created_at.desc())
        .limit(5)
        .all()
    )
    recent = [
        {
            "title": d.title,
            "type": _classify_decision_type(d.title),
            "status": d.status,
            "confidence": d.confidence,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in recent_decisions
    ]

    return {
        "patterns": patterns[:8],
        "total_decisions": sum(s["total"] for s in type_stats.values()),
        "your_recent_decisions": recent,
    }


def _default_decision_patterns() -> Dict[str, Any]:
    return {
        "patterns": [
            {"decision_type": "cost_reduction", "total_count": 0, "acceptance_rate": 75.0, "high_confidence_count": 0, "rejection_count": 0},
            {"decision_type": "hiring", "total_count": 0, "acceptance_rate": 60.0, "high_confidence_count": 0, "rejection_count": 0},
            {"decision_type": "pricing", "total_count": 0, "acceptance_rate": 70.0, "high_confidence_count": 0, "rejection_count": 0},
        ],
        "total_decisions": 0,
        "your_recent_decisions": [],
        "source": "industry_benchmarks",
    }


def get_strategy_insights(db: Session, company_id: int) -> Dict[str, Any]:
    profile = get_company_profile(db, company_id)
    if not profile:
        return {"strategies": [], "peer_insights": []}

    all_decisions = (
        db.query(CompanyDecision)
        .filter(CompanyDecision.status.in_(["accepted", "implemented", "resolved", "completed", "decided"]))
        .limit(300)
        .all()
    )

    strategy_outcomes = defaultdict(lambda: {"count": 0, "high_conf": 0, "companies": set()})
    for d in all_decisions:
        stype = _classify_decision_type(d.title)
        strategy_outcomes[stype]["count"] += 1
        strategy_outcomes[stype]["companies"].add(d.company_id)
        if d.confidence == "high":
            strategy_outcomes[stype]["high_conf"] += 1

    strategies = []
    for stype, data in strategy_outcomes.items():
        strategies.append({
            "strategy": stype,
            "adoption_count": data["count"],
            "company_count": len(data["companies"]),
            "high_confidence_rate": round(data["high_conf"] / data["count"] * 100, 1) if data["count"] > 0 else 0,
            "recommendation": _strategy_recommendation(stype, profile),
        })

    strategies.sort(key=lambda s: s["adoption_count"], reverse=True)

    peer_insights = _generate_peer_insights(db, profile)

    return {
        "strategies": strategies[:6],
        "peer_insights": peer_insights,
        "profile_summary": {
            "stage": profile["stage"],
            "industry": profile["industry"],
            "mrr_range": profile["mrr_range"],
            "growth_tier": profile["growth_tier"],
        },
    }


def _strategy_recommendation(strategy: str, profile: Dict[str, Any]) -> str:
    stage = profile.get("stage", "seed")
    growth = profile.get("growth_tier", "moderate")

    recs = {
        "cost_reduction": "Optimize vendor costs and non-critical spend. Companies at your stage that cut costs strategically extended runway by 3-6 months on average.",
        "hiring": "Focus hiring on revenue-generating roles first. Each hire should have a clear 90-day ROI target.",
        "pricing": "Consider a 10-20% price increase — most startups undercharge. Test with new customers first.",
        "fundraising": "Start investor conversations 6+ months before you need capital. Build relationships before the ask.",
        "growth": "Double down on your best-performing channel before experimenting with new ones.",
        "product": "Ship smaller, faster iterations. Validate with 5 customers before building for 500.",
        "retention": "Implement customer health scoring. Reducing churn by 5% can increase profits by 25-95%.",
        "partnership": "Strategic partnerships can accelerate growth with lower CAC than direct acquisition.",
        "general": "Focus on the decisions with highest potential impact on your current stage goals.",
    }

    base = recs.get(strategy, recs["general"])

    if growth == "declining" and strategy != "cost_reduction":
        base += " Given declining growth, prioritize unit economics before scaling."
    elif growth == "hypergrowth":
        base += " With strong growth momentum, ensure infrastructure can sustain the pace."

    return base


def _generate_peer_insights(db: Session, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    insights = []

    stage = profile.get("stage", "seed")
    industry = profile.get("industry", "unknown")

    peer_companies = (
        db.query(Company)
        .filter(
            Company.id != profile.get("company_id"),
            or_(
                Company.industry.ilike(f"%{industry}%"),
                Company.stage == stage,
            ),
        )
        .limit(50)
        .all()
    )

    if not peer_companies:
        return _default_peer_insights(profile)

    peer_ids = [c.id for c in peer_companies]

    peer_fins = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id.in_(peer_ids))
        .order_by(FinancialRecord.period_start.desc())
        .limit(200)
        .all()
    )

    if peer_fins:
        revenues = [float(f.revenue or 0) for f in peer_fins if f.revenue and f.revenue > 0]
        burns = [float(f.net_burn or 0) for f in peer_fins if hasattr(f, "net_burn") and f.net_burn]
        runways = [float(f.runway_months or 0) for f in peer_fins if hasattr(f, "runway_months") and f.runway_months and 0 < f.runway_months <= 120]

        if revenues:
            median_rev = sorted(revenues)[len(revenues) // 2]
            your_mrr = profile.get("mrr", 0)
            position = "above" if your_mrr > median_rev else "below" if your_mrr < median_rev else "at"
            insights.append({
                "type": "revenue_benchmark",
                "title": "Revenue vs Peers",
                "description": f"Your MRR is {position} the peer median of ${median_rev:,.0f}/mo across {len(revenues)} data points.",
                "metric": f"${median_rev:,.0f}",
                "your_value": f"${your_mrr:,.0f}",
                "position": position,
            })

        if runways:
            median_runway = sorted(runways)[len(runways) // 2]
            your_runway = profile.get("runway_months", 0)
            insights.append({
                "type": "runway_benchmark",
                "title": "Runway vs Peers",
                "description": f"Peer median runway is {median_runway:.0f} months. {'You have more buffer.' if your_runway > median_runway else 'Consider extending runway.'}",
                "metric": f"{median_runway:.0f}mo",
                "your_value": f"{your_runway:.0f}mo",
                "position": "above" if your_runway > median_runway else "below",
            })

    peer_decisions = (
        db.query(CompanyDecision)
        .filter(
            CompanyDecision.company_id.in_(peer_ids),
            CompanyDecision.status.in_(["accepted", "implemented"]),
        )
        .limit(100)
        .all()
    )

    if peer_decisions:
        type_counts = defaultdict(int)
        for d in peer_decisions:
            type_counts[_classify_decision_type(d.title)] += 1

        if type_counts:
            top_type = max(type_counts, key=type_counts.get)
            insights.append({
                "type": "decision_trend",
                "title": "Top Peer Strategy",
                "description": f"The most common strategy among peers is '{top_type}' ({type_counts[top_type]} decisions). Consider if this applies to your situation.",
                "metric": top_type,
                "count": type_counts[top_type],
            })

    return insights if insights else _default_peer_insights(profile)


def _default_peer_insights(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    stage = profile.get("stage", "seed")
    return [
        {
            "type": "benchmark",
            "title": "Industry Benchmark",
            "description": f"At the {stage} stage, top-quartile companies maintain 18+ months runway and grow MRR 15%+ MoM.",
            "source": "industry_data",
        },
        {
            "type": "strategy_tip",
            "title": "Common Strategy",
            "description": "Most successful startups at your stage focus on product-market fit and unit economics before scaling.",
            "source": "industry_data",
        },
    ]


def get_growth_benchmarks(db: Session, company_id: int) -> Dict[str, Any]:
    profile = get_company_profile(db, company_id)

    records_with_company = (
        db.query(FinancialRecord, Company.stage, Company.industry)
        .join(Company, FinancialRecord.company_id == Company.id)
        .order_by(FinancialRecord.period_start.desc())
        .limit(500)
        .all()
    )

    stage_groups = defaultdict(list)
    industry_groups = defaultdict(list)
    company_ids_seen = set()

    for rec, stage, industry in records_with_company:
        stage_key = (stage or "unknown").lower()
        industry_key = (industry or "unknown").lower()
        company_ids_seen.add(rec.company_id)
        rev = float(rec.revenue or 0)
        burn = float(rec.net_burn or 0) if hasattr(rec, "net_burn") and rec.net_burn else 0

        if rev > 0:
            stage_groups[stage_key].append(rev)
        if burn > 0:
            industry_groups[industry_key].append(burn)

    stage_benchmarks = {}
    for stage, revenues in stage_groups.items():
        if revenues:
            sorted_r = sorted(revenues)
            n = len(sorted_r)
            stage_benchmarks[stage] = {
                "p25": sorted_r[n // 4] if n >= 4 else sorted_r[0],
                "median": sorted_r[n // 2],
                "p75": sorted_r[3 * n // 4] if n >= 4 else sorted_r[-1],
                "sample_size": n,
            }

    return {
        "your_profile": {
            "stage": profile.get("stage"),
            "industry": profile.get("industry"),
            "mrr": profile.get("mrr", 0),
            "growth_pct": profile.get("growth_pct", 0),
            "runway_months": profile.get("runway_months", 0),
        },
        "stage_benchmarks": stage_benchmarks,
        "total_companies_analyzed": len(company_ids_seen),
        "total_data_points": len(records_with_company),
    }


def get_cross_company_patterns(db: Session, company_id: int) -> Dict[str, Any]:
    profile = get_company_profile(db, company_id)
    if not profile:
        return {"patterns": [], "source": "no_profile"}

    try:
        from server.services.pattern_aggregator import get_relevant_patterns
        patterns = get_relevant_patterns(
            db,
            industry=profile.get("industry", "unknown"),
            stage=profile.get("stage", "unknown"),
        )
        if patterns:
            return {
                "patterns": patterns,
                "source": "cross_company_aggregated",
                "your_industry": profile.get("industry"),
                "your_stage": profile.get("stage"),
            }
    except Exception as e:
        logger.debug(f"Cross-company patterns lookup failed: {e}")

    return {"patterns": [], "source": "insufficient_data"}


def get_intelligence_summary(db: Session, company_id: int) -> Dict[str, Any]:
    profile = get_company_profile(db, company_id)
    if not profile:
        return {"error": "Company not found"}

    similar = find_similar_companies(db, company_id, limit=5)
    patterns = get_decision_patterns(db, company_id)
    strategies = get_strategy_insights(db, company_id)
    benchmarks = get_growth_benchmarks(db, company_id)
    cross_company = get_cross_company_patterns(db, company_id)

    total_companies = db.query(func.count(Company.id)).scalar() or 0
    total_decisions = db.query(func.count(CompanyDecision.id)).scalar() or 0
    total_records = db.query(func.count(FinancialRecord.id)).scalar() or 0
    total_events = (
        db.query(func.count(TwinEvent.id))
        .filter(TwinEvent.company_id == company_id)
        .scalar() or 0
    )

    contributing_companies = (
        db.query(func.count(Company.id))
        .filter(Company.data_sharing_enabled == True)
        .scalar() or 0
    )

    return {
        "company_profile": profile,
        "similar_companies": similar,
        "decision_patterns": patterns,
        "strategy_insights": strategies,
        "growth_benchmarks": benchmarks,
        "cross_company_patterns": cross_company,
        "graph_stats": {
            "total_companies": total_companies,
            "total_decisions": total_decisions,
            "total_financial_records": total_records,
            "total_events": total_events,
            "similar_companies_found": len(similar),
            "contributing_companies": contributing_companies,
        },
    }


def process_graph_event(
    db: Session, company_id: int, event_type: str, payload: dict
) -> Dict[str, Any]:
    if event_type not in GRAPH_EVENT_TYPES:
        return {"processed": False, "reason": f"Event type '{event_type}' not tracked by intelligence graph"}

    result = {"processed": True, "event_type": event_type, "entities_updated": []}

    try:
        if event_type in ("revenue_update", "expense_update", "data_ingestion", "state_update"):
            profile = get_company_profile(db, company_id)
            if profile:
                result["entities_updated"].append({
                    "type": "company_metrics",
                    "company_id": company_id,
                    "mrr": profile.get("mrr"),
                    "growth_tier": profile.get("growth_tier"),
                    "mrr_range": profile.get("mrr_range"),
                })

        elif event_type == "decision_made":
            title = payload.get("title", "")
            decision_type = _classify_decision_type(title)
            result["entities_updated"].append({
                "type": "decision_node",
                "decision_type": decision_type,
                "title": title,
            })
            result["entities_updated"].append({
                "type": "strategy_link",
                "strategy": decision_type,
                "relationship": "USED_STRATEGY",
            })

        elif event_type == "decision_outcome":
            decision_id = payload.get("decision_id")
            impact = payload.get("impact", {})
            result["entities_updated"].append({
                "type": "outcome_node",
                "decision_id": decision_id,
                "revenue_change": impact.get("revenue_change"),
                "growth_change": impact.get("growth_change"),
                "relationship": "RESULTED_IN",
            })

        elif event_type == "simulation_run":
            result["entities_updated"].append({
                "type": "simulation_metric",
                "survival_probability": payload.get("survival_probability"),
                "median_runway": payload.get("median_runway"),
            })

        elif event_type == "fundraising_update":
            result["entities_updated"].append({
                "type": "investor_link",
                "round_type": payload.get("round_type"),
                "amount": payload.get("amount"),
                "relationship": "INVESTED_BY",
            })

        elif event_type == "connector_sync":
            result["entities_updated"].append({
                "type": "data_source",
                "provider": payload.get("provider"),
                "records_synced": payload.get("records_synced"),
            })

        elif event_type == "headcount_change":
            result["entities_updated"].append({
                "type": "team_metric",
                "headcount": payload.get("headcount"),
                "change": payload.get("change"),
            })

        similar_count = len(find_similar_companies(db, company_id, limit=3))
        result["similarity_recalculated"] = True
        result["similar_companies_count"] = similar_count

    except Exception as e:
        logger.error(f"Graph event processing error: {e}")
        result["processed"] = False
        result["error"] = str(e)

    return result


def sync_twin_to_graph(db: Session, company_id: int) -> Dict[str, Any]:
    from server.services.digital_twin import get_twin_state

    twin_state = get_twin_state(db, company_id)
    if "error" in twin_state:
        return {"synced": False, "error": twin_state["error"]}

    profile = get_company_profile(db, company_id)
    if not profile:
        return {"synced": False, "error": "Company profile not found"}

    nodes = []

    nodes.append({
        "type": "Company",
        "id": company_id,
        "properties": {
            "name": twin_state.get("company_name"),
            "stage": profile.get("stage"),
            "industry": profile.get("industry"),
            "mrr": profile.get("mrr"),
            "growth_rate": profile.get("growth_pct"),
        },
    })

    financials = twin_state.get("financials", {})
    metric_fields = {
        "cash_balance": financials.get("cash_balance"),
        "monthly_burn": financials.get("monthly_burn"),
        "revenue_monthly": financials.get("revenue_monthly"),
        "revenue_growth_rate": financials.get("revenue_growth_rate"),
    }
    for metric_name, value in metric_fields.items():
        if value is not None:
            nodes.append({
                "type": "Metric",
                "properties": {
                    "metric_name": metric_name,
                    "value": float(value) if value else 0,
                    "timestamp": twin_state.get("last_updated"),
                },
            })

    derived = twin_state.get("derived_metrics", {})
    derived_fields = ["runway_months", "gross_margin", "ltv", "cac", "churn_rate"]
    for field in derived_fields:
        val = derived.get(field)
        if val is not None:
            nodes.append({
                "type": "Metric",
                "properties": {
                    "metric_name": field,
                    "value": float(val) if val else 0,
                    "timestamp": twin_state.get("last_updated"),
                },
            })

    relationships = []
    for node in nodes:
        if node["type"] == "Metric":
            relationships.append({
                "from": {"type": "Company", "id": company_id},
                "to": node,
                "relationship": "HAS_METRIC",
            })

    decisions = (
        db.query(CompanyDecision)
        .filter(CompanyDecision.company_id == company_id)
        .order_by(CompanyDecision.created_at.desc())
        .limit(10)
        .all()
    )
    for d in decisions:
        dtype = _classify_decision_type(d.title)
        dec_node = {
            "type": "Decision",
            "properties": {
                "decision_type": dtype,
                "description": d.title,
                "status": d.status,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            },
        }
        nodes.append(dec_node)
        relationships.append({
            "from": {"type": "Company", "id": company_id},
            "to": dec_node,
            "relationship": "MADE_DECISION",
        })
        relationships.append({
            "from": {"type": "Company", "id": company_id},
            "to": {"type": "Strategy", "properties": {"strategy_name": dtype}},
            "relationship": "USED_STRATEGY",
        })

    similar = find_similar_companies(db, company_id, limit=5)
    for peer in similar:
        relationships.append({
            "from": {"type": "Company", "id": company_id},
            "to": {"type": "Company", "peer_rank": peer["peer_rank"]},
            "relationship": "SIMILAR_TO",
            "properties": {"similarity_score": peer["similarity_score"]},
        })

    return {
        "synced": True,
        "company_id": company_id,
        "nodes_count": len(nodes),
        "relationships_count": len(relationships),
        "nodes": nodes,
        "relationships": relationships,
        "twin_health": twin_state.get("health", {}),
        "last_updated": twin_state.get("last_updated"),
    }


def generate_ai_strategy_insights(db: Session, company_id: int) -> Dict[str, Any]:
    profile = get_company_profile(db, company_id)
    if not profile:
        return {"insights": [], "error": "Company not found"}

    similar = find_similar_companies(db, company_id, limit=10)
    patterns = get_decision_patterns(db, company_id)
    strategies = get_strategy_insights(db, company_id)
    benchmarks = get_growth_benchmarks(db, company_id)

    insights = []

    stage_data = benchmarks.get("stage_benchmarks", {}).get(profile.get("stage", ""), {})
    if stage_data:
        median_mrr = stage_data.get("median", 0)
        your_mrr = profile.get("mrr", 0)
        if median_mrr > 0:
            percentile = "above median" if your_mrr > median_mrr else "below median"
            ratio = your_mrr / median_mrr if median_mrr > 0 else 0
            if ratio < 0.5:
                insights.append({
                    "type": "revenue_gap",
                    "severity": "high",
                    "title": "Revenue significantly below peers",
                    "description": f"Your MRR (${your_mrr:,.0f}) is {(1-ratio)*100:.0f}% below the peer median (${median_mrr:,.0f}). Companies that closed this gap typically focused on pricing optimization and sales efficiency.",
                    "recommended_strategies": ["pricing", "growth"],
                })
            elif ratio > 1.5:
                insights.append({
                    "type": "revenue_leader",
                    "severity": "low",
                    "title": "Revenue outperforming peers",
                    "description": f"Your MRR (${your_mrr:,.0f}) is {(ratio-1)*100:.0f}% above the peer median. Consider this advantage when planning your next fundraise.",
                    "recommended_strategies": ["fundraising"],
                })

    peer_strategies = strategies.get("strategies", [])
    your_decisions = patterns.get("your_recent_decisions", [])
    your_decision_types = set(d.get("type") for d in your_decisions)

    for ps in peer_strategies[:3]:
        if ps["strategy"] not in your_decision_types and ps["adoption_count"] >= 2:
            insights.append({
                "type": "strategy_gap",
                "severity": "medium",
                "title": f"Peers are adopting '{ps['strategy'].replace('_', ' ')}' strategy",
                "description": f"{ps['adoption_count']} companies have implemented {ps['strategy'].replace('_', ' ')} decisions with {ps['high_confidence_rate']}% high-confidence outcomes. You haven't explored this strategy yet.",
                "recommended_strategies": [ps["strategy"]],
                "peer_evidence": {
                    "adoption_count": ps["adoption_count"],
                    "company_count": ps["company_count"],
                    "confidence_rate": ps["high_confidence_rate"],
                },
            })

    if similar:
        avg_similarity = sum(s["similarity_score"] for s in similar) / len(similar)
        most_common_traits = defaultdict(int)
        for s in similar:
            for trait in s.get("shared_traits", []):
                most_common_traits[trait] += 1
        top_traits = sorted(most_common_traits.items(), key=lambda x: x[1], reverse=True)[:3]
        insights.append({
            "type": "peer_network",
            "severity": "info",
            "title": f"Connected to {len(similar)} similar companies",
            "description": f"Average similarity score: {avg_similarity*100:.0f}%. Strongest shared traits: {', '.join(t[0] for t in top_traits)}.",
            "peer_count": len(similar),
            "avg_similarity": round(avg_similarity, 3),
            "top_shared_traits": [t[0] for t in top_traits],
        })

    growth_tier = profile.get("growth_tier", "moderate")
    runway = profile.get("runway_months", 0)
    if growth_tier == "declining" and runway < 12:
        insights.append({
            "type": "survival_risk",
            "severity": "critical",
            "title": "Critical: Declining growth with short runway",
            "description": f"With {runway:.0f} months runway and declining growth, immediate action is needed. Similar companies that survived this phase cut costs by 20-30% and focused on their strongest revenue channel.",
            "recommended_strategies": ["cost_reduction", "retention"],
        })
    elif growth_tier == "declining":
        insights.append({
            "type": "growth_warning",
            "severity": "high",
            "title": "Growth has turned negative",
            "description": "Declining growth requires a strategic pivot. Peer data shows companies that acted within 2 months of decline onset had 3x better recovery rates.",
            "recommended_strategies": ["growth", "product", "retention"],
        })

    insights.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(x.get("severity", "info"), 5))

    return {
        "company_id": company_id,
        "insights": insights,
        "profile": {
            "stage": profile.get("stage"),
            "industry": profile.get("industry"),
            "mrr": profile.get("mrr"),
            "growth_tier": growth_tier,
            "runway_months": runway,
        },
        "peer_count": len(similar),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_simulation_graph_recommendations(
    db: Session, company_id: int, simulation_result: Optional[Dict] = None
) -> Dict[str, Any]:
    profile = get_company_profile(db, company_id)
    if not profile:
        return {"recommendations": []}

    similar = find_similar_companies(db, company_id, limit=10)
    strategies = get_strategy_insights(db, company_id)
    ai_insights = generate_ai_strategy_insights(db, company_id)

    if not simulation_result:
        latest_sim = (
            db.query(SimulationRun)
            .join(Scenario, SimulationRun.scenario_id == Scenario.id)
            .filter(Scenario.company_id == company_id)
            .order_by(SimulationRun.created_at.desc())
            .first()
        )
        if latest_sim and latest_sim.outputs_json:
            try:
                simulation_result = json.loads(latest_sim.outputs_json) if isinstance(latest_sim.outputs_json, str) else latest_sim.outputs_json
            except (json.JSONDecodeError, TypeError):
                simulation_result = {}

    recommendations = []

    if simulation_result:
        survival_prob = simulation_result.get("survival_probability", simulation_result.get("summary", {}).get("survival_probability"))
        median_runway = simulation_result.get("median_runway_months", simulation_result.get("summary", {}).get("median_runway_months"))

        if survival_prob is not None and survival_prob < 0.5:
            recommendations.append({
                "type": "survival_action",
                "priority": "critical",
                "title": "Low survival probability detected",
                "description": f"Simulation shows {survival_prob*100:.0f}% survival probability. Peer companies that improved survival focused on cost reduction and revenue acceleration.",
                "suggested_actions": ["Reduce burn by 20-30%", "Accelerate top revenue channel", "Consider bridge financing"],
                "peer_evidence": f"{len(similar)} similar companies tracked",
            })
        elif survival_prob is not None and survival_prob > 0.8:
            recommendations.append({
                "type": "growth_opportunity",
                "priority": "medium",
                "title": "Strong survival — consider growth investments",
                "description": f"With {survival_prob*100:.0f}% survival probability, you have room to invest in growth. Peers at this confidence level typically accelerate hiring and market expansion.",
                "suggested_actions": ["Invest in sales team", "Explore new channels", "Consider fundraising"],
                "peer_evidence": f"Based on {len(similar)} peer companies",
            })

    peer_strategies = strategies.get("strategies", [])
    for ps in peer_strategies[:2]:
        if ps["adoption_count"] >= 2:
            recommendations.append({
                "type": "peer_strategy",
                "priority": "medium",
                "title": f"Peer-validated strategy: {ps['strategy'].replace('_', ' ').title()}",
                "description": ps.get("recommendation", f"{ps['adoption_count']} peer companies have successfully used this strategy."),
                "adoption_count": ps["adoption_count"],
                "confidence_rate": ps["high_confidence_rate"],
            })

    for insight in ai_insights.get("insights", []):
        if insight.get("severity") in ("critical", "high"):
            recommendations.append({
                "type": "ai_insight",
                "priority": insight["severity"],
                "title": insight["title"],
                "description": insight["description"],
                "recommended_strategies": insight.get("recommended_strategies", []),
            })

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recommendations.sort(key=lambda r: priority_order.get(r.get("priority", "low"), 4))

    return {
        "company_id": company_id,
        "recommendations": recommendations[:8],
        "simulation_available": simulation_result is not None,
        "peer_count": len(similar),
        "profile_summary": {
            "stage": profile.get("stage"),
            "mrr": profile.get("mrr"),
            "growth_tier": profile.get("growth_tier"),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_network_graph_data(db: Session, company_id: int) -> Dict[str, Any]:
    profile = get_company_profile(db, company_id)
    if not profile:
        return {"nodes": [], "edges": []}

    nodes = []
    edges = []

    nodes.append({
        "id": f"company_{company_id}",
        "type": "Company",
        "label": profile.get("name", "Your Company"),
        "properties": {
            "stage": profile.get("stage"),
            "industry": profile.get("industry"),
            "mrr": profile.get("mrr"),
            "growth_tier": profile.get("growth_tier"),
        },
        "is_self": True,
    })

    financials = profile.get("mrr", 0)
    metric_data = [
        ("MRR", profile.get("mrr")),
        ("Growth", profile.get("growth_pct")),
        ("Runway", profile.get("runway_months")),
        ("Cash", profile.get("cash_balance")),
        ("Burn Rate", profile.get("burn_rate")),
    ]
    for metric_name, value in metric_data:
        if value is not None and value != 0:
            node_id = f"metric_{metric_name.lower().replace(' ', '_')}"
            nodes.append({
                "id": node_id,
                "type": "Metric",
                "label": metric_name,
                "properties": {"value": value},
            })
            edges.append({
                "from": f"company_{company_id}",
                "to": node_id,
                "relationship": "HAS_METRIC",
            })

    decisions = (
        db.query(CompanyDecision)
        .filter(CompanyDecision.company_id == company_id)
        .order_by(CompanyDecision.created_at.desc())
        .limit(8)
        .all()
    )
    strategy_nodes_added = set()
    for d in decisions:
        dtype = _classify_decision_type(d.title)
        dec_id = f"decision_{d.id}"
        nodes.append({
            "id": dec_id,
            "type": "Decision",
            "label": d.title[:40],
            "properties": {
                "decision_type": dtype,
                "status": d.status,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            },
        })
        edges.append({
            "from": f"company_{company_id}",
            "to": dec_id,
            "relationship": "MADE_DECISION",
        })

        strat_id = f"strategy_{dtype}"
        if dtype not in strategy_nodes_added:
            strategy_nodes_added.add(dtype)
            nodes.append({
                "id": strat_id,
                "type": "Strategy",
                "label": dtype.replace("_", " ").title(),
                "properties": {"strategy_name": dtype},
            })
            edges.append({
                "from": f"company_{company_id}",
                "to": strat_id,
                "relationship": "USED_STRATEGY",
            })

        edges.append({
            "from": dec_id,
            "to": strat_id,
            "relationship": "IMPLEMENTS",
        })

        if d.status in ("completed", "decided", "accepted", "implemented"):
            outcome_id = f"outcome_{d.id}"
            nodes.append({
                "id": outcome_id,
                "type": "Outcome",
                "label": f"Result: {d.status}",
                "properties": {"status": d.status},
            })
            edges.append({
                "from": dec_id,
                "to": outcome_id,
                "relationship": "RESULTED_IN",
            })

    similar = find_similar_companies(db, company_id, limit=5)
    for peer in similar:
        peer_id = f"peer_{peer['peer_rank']}"
        nodes.append({
            "id": peer_id,
            "type": "Company",
            "label": f"Peer #{peer['peer_rank']}",
            "properties": {
                "industry": peer["industry"],
                "stage": peer["stage"],
                "mrr_range": peer["mrr_range"],
                "similarity_score": peer["similarity_score"],
            },
            "is_self": False,
        })
        edges.append({
            "from": f"company_{company_id}",
            "to": peer_id,
            "relationship": "SIMILAR_TO",
            "properties": {"score": peer["similarity_score"]},
        })

    latest_sim = (
        db.query(SimulationRun)
        .join(Scenario, SimulationRun.scenario_id == Scenario.id)
        .filter(Scenario.company_id == company_id)
        .order_by(SimulationRun.created_at.desc())
        .first()
    )
    if latest_sim:
        sim_node_id = f"simulation_{latest_sim.id}"
        nodes.append({
            "id": sim_node_id,
            "type": "Simulation",
            "label": "Latest Simulation",
            "properties": {
                "created_at": latest_sim.created_at.isoformat() if latest_sim.created_at else None,
            },
        })
        edges.append({
            "from": f"company_{company_id}",
            "to": sim_node_id,
            "relationship": "RAN_SIMULATION",
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_types": list(set(n["type"] for n in nodes)),
        "relationship_types": list(set(e["relationship"] for e in edges)),
    }


def ensure_graph_indexes(db: Session) -> Dict[str, Any]:
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_financial_records_company_period ON financial_records(company_id, period_start DESC)",
        "CREATE INDEX IF NOT EXISTS idx_company_decisions_company ON company_decisions(company_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_company_decisions_status ON company_decisions(status)",
        "CREATE INDEX IF NOT EXISTS idx_company_decisions_type_status ON company_decisions(status, company_id)",
        "CREATE INDEX IF NOT EXISTS idx_twin_events_company_type ON twin_events(company_id, event_type)",
        "CREATE INDEX IF NOT EXISTS idx_twin_events_created ON twin_events(company_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_companies_industry ON companies(industry)",
        "CREATE INDEX IF NOT EXISTS idx_companies_stage ON companies(stage)",
        "CREATE INDEX IF NOT EXISTS idx_simulation_runs_created ON simulation_runs(created_at DESC)",
    ]

    results = []
    for idx_sql in indexes:
        try:
            db.execute(text(idx_sql))
            results.append({"sql": idx_sql, "status": "created"})
        except Exception as e:
            results.append({"sql": idx_sql, "status": "error", "error": str(e)})

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit indexes: {e}")

    return {"indexes_processed": len(results), "results": results}


def upsert_graph_node(
    db: Session, company_id: int, node_type: str, entity_id: int,
    label: str, properties: Optional[Dict] = None,
) -> int:
    import json as _json
    existing = db.execute(
        text("SELECT id FROM graph_nodes WHERE company_id = :cid AND node_type = :nt AND entity_id = :eid"),
        {"cid": company_id, "nt": node_type, "eid": entity_id},
    ).fetchone()
    if existing:
        db.execute(
            text("UPDATE graph_nodes SET label = :label, properties_json = :props WHERE id = :id"),
            {"label": label, "props": _json.dumps(properties or {}), "id": existing[0]},
        )
        db.commit()
        return existing[0]
    else:
        result = db.execute(
            text("""
                INSERT INTO graph_nodes (company_id, node_type, entity_id, label, properties_json)
                VALUES (:cid, :nt, :eid, :label, :props) RETURNING id
            """),
            {"cid": company_id, "nt": node_type, "eid": entity_id, "label": label, "props": _json.dumps(properties or {})},
        )
        db.commit()
        return result.scalar()


def add_graph_edge(
    db: Session, company_id: int, source_node_id: int, target_node_id: int,
    relationship: str, weight: float = 1.0, properties: Optional[Dict] = None,
) -> int:
    import json as _json
    result = db.execute(
        text("""
            INSERT INTO graph_edges (company_id, source_node_id, target_node_id, relationship, weight, properties_json)
            VALUES (:cid, :src, :tgt, :rel, :w, :props) RETURNING id
        """),
        {"cid": company_id, "src": source_node_id, "tgt": target_node_id, "rel": relationship, "w": weight, "props": _json.dumps(properties or {})},
    )
    db.commit()
    return result.scalar()


def get_related_metrics(db: Session, company_id: int, metric_node_id: int) -> List[Dict]:
    rows = db.execute(
        text("""
            SELECT gn.id, gn.node_type, gn.label, gn.properties_json, ge.relationship, ge.weight
            FROM graph_edges ge
            JOIN graph_nodes gn ON gn.id = ge.target_node_id
            WHERE ge.source_node_id = :nid AND ge.company_id = :cid
            ORDER BY ge.weight DESC
        """),
        {"nid": metric_node_id, "cid": company_id},
    ).fetchall()
    return [
        {"node_id": r[0], "type": r[1], "label": r[2], "properties": json.loads(r[3]) if r[3] else {}, "relationship": r[4], "weight": r[5]}
        for r in rows
    ]


def get_decision_history(db: Session, company_id: int) -> List[Dict]:
    rows = db.execute(
        text("""
            SELECT gn.id, gn.label, gn.properties_json, ge.relationship
            FROM graph_nodes gn
            LEFT JOIN graph_edges ge ON ge.source_node_id = gn.id OR ge.target_node_id = gn.id
            WHERE gn.company_id = :cid AND gn.node_type = 'Decision'
            ORDER BY gn.created_at DESC LIMIT 50
        """),
        {"cid": company_id},
    ).fetchall()
    return [
        {"node_id": r[0], "label": r[1], "properties": json.loads(r[2]) if r[2] else {}, "relationship": r[3]}
        for r in rows
    ]


def get_strategy_patterns(db: Session, company_id: int) -> Dict[str, Any]:
    rows = db.execute(
        text("""
            SELECT ge.relationship, COUNT(*) as cnt, AVG(ge.weight) as avg_weight
            FROM graph_edges ge
            WHERE ge.company_id = :cid
            GROUP BY ge.relationship
            ORDER BY cnt DESC
        """),
        {"cid": company_id},
    ).fetchall()
    return {
        "patterns": [
            {"relationship": r[0], "count": r[1], "avg_weight": round(float(r[2]), 3) if r[2] else 0}
            for r in rows
        ],
        "total_edges": sum(r[1] for r in rows),
    }
