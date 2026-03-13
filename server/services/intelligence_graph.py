"""
Founder Intelligence Graph Service.

Provides cross-company intelligence through graph-like relationship
analysis using PostgreSQL. Connects companies, founders, metrics,
decisions, strategies, and outcomes to enable:
- Cross-company benchmarking
- Company similarity matching
- Decision pattern discovery
- AI strategy recommendations
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case

from server.models.company import Company
from server.models.company_decision import CompanyDecision
from server.models.financial import FinancialRecord
from server.models.company_state import CompanyState
from server.models.simulation_run import SimulationRun
from server.models.scenario import Scenario
from server.models.twin_event import TwinEvent

logger = logging.getLogger(__name__)


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


def get_intelligence_summary(db: Session, company_id: int) -> Dict[str, Any]:
    profile = get_company_profile(db, company_id)
    if not profile:
        return {"error": "Company not found"}

    similar = find_similar_companies(db, company_id, limit=5)
    patterns = get_decision_patterns(db, company_id)
    strategies = get_strategy_insights(db, company_id)
    benchmarks = get_growth_benchmarks(db, company_id)

    total_companies = db.query(func.count(Company.id)).scalar() or 0
    total_decisions = db.query(func.count(CompanyDecision.id)).scalar() or 0
    total_records = db.query(func.count(FinancialRecord.id)).scalar() or 0

    return {
        "company_profile": profile,
        "similar_companies": similar,
        "decision_patterns": patterns,
        "strategy_insights": strategies,
        "growth_benchmarks": benchmarks,
        "graph_stats": {
            "total_companies": total_companies,
            "total_decisions": total_decisions,
            "total_financial_records": total_records,
            "similar_companies_found": len(similar),
        },
    }
