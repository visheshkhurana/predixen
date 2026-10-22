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
from server.services.peer_privacy import (
    INSUFFICIENT_PEERS,
    MIN_DISTINCT_PEERS,
    band_counts,
    empty_peer_view,
    opted_in,
)

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


def _bulk_load_company_profiles(
    db: Session, exclude_id: int = None, opted_in_only: bool = False
) -> Dict[int, Dict[str, Any]]:
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
    if opted_in_only:
        query = query.filter(Company.data_sharing_enabled == True)

    profiles = {}
    for company, fin in query.all():
        if opted_in_only and not opted_in(company):
            continue
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
            "opted_in": opted_in(company),
        }

    return profiles


def find_similar_companies(
    db: Session, company_id: int, min_similarity: float = 0.25, limit: int = 10
) -> Dict[str, Any]:
    """Opted-in peer cohort as aggregates, or an empty list.

    Individual peer names, ids, revenue, and revenue bands are never returned.
    A band is included only when at least MIN_DISTINCT_PEERS distinct opted-in
    companies share it. ``limit`` is accepted for existing callers and does not
    truncate the cohort: a cap would either publish a group under the threshold
    or hide a publishable one.
    """
    _ = limit
    target_profile = get_company_profile(db, company_id)
    if not target_profile:
        return empty_peer_view()

    peer_profiles = _bulk_load_company_profiles(
        db, exclude_id=company_id, opted_in_only=True
    )
    matched_ids = set()
    mrr_ids: Dict[str, set] = defaultdict(set)
    stage_ids: Dict[str, set] = defaultdict(set)
    industry_ids: Dict[str, set] = defaultdict(set)
    growth_ids: Dict[str, set] = defaultdict(set)
    employee_ids: Dict[str, set] = defaultdict(set)

    for cid, profile in peer_profiles.items():
        if not profile.get("opted_in"):
            continue
        similarity = _compute_company_similarity(target_profile, profile)
        if similarity < min_similarity:
            continue
        matched_ids.add(cid)
        mrr_ids[profile["mrr_range"]].add(cid)
        stage_ids[profile["stage"]].add(cid)
        industry_ids[profile["industry"]].add(cid)
        growth_ids[profile["growth_tier"]].add(cid)
        employee_ids[profile["employee_range"]].add(cid)

    if len(matched_ids) < MIN_DISTINCT_PEERS:
        return empty_peer_view()

    return {
        "similar_companies": [],
        "aggregates": {
            "peer_count": len(matched_ids),
            "mrr_bands": band_counts(mrr_ids),
            "stages": band_counts(stage_ids),
            "industries": band_counts(industry_ids),
            "growth_tiers": band_counts(growth_ids),
            "employee_ranges": band_counts(employee_ids),
        },
        "peer_count": len(matched_ids),
        "reason": None,
    }


def get_decision_patterns(db: Session, company_id: int) -> Dict[str, Any]:
    from server.services.data_anonymizer import get_opted_in_company_ids

    peer_ids = get_opted_in_company_ids(db, exclude_company_id=company_id)
    decisions = []
    if peer_ids:
        decisions = (
            db.query(CompanyDecision)
            .filter(CompanyDecision.company_id.in_(peer_ids))
            .limit(500)
            .all()
        )

    type_stats = defaultdict(lambda: {
        "total": 0, "accepted": 0, "rejected": 0, "high_confidence": 0, "companies": set(),
    })

    for d in decisions:
        dtype = _classify_decision_type(d.title)
        type_stats[dtype]["total"] += 1
        type_stats[dtype]["companies"].add(d.company_id)
        if d.status in ("accepted", "implemented", "resolved", "completed", "decided"):
            type_stats[dtype]["accepted"] += 1
        elif d.status == "rejected":
            type_stats[dtype]["rejected"] += 1
        if d.confidence == "high":
            type_stats[dtype]["high_confidence"] += 1

    patterns = []
    for dtype, stats in type_stats.items():
        if len(stats["companies"]) < MIN_DISTINCT_PEERS:
            continue
        acceptance_rate = (stats["accepted"] / stats["total"] * 100) if stats["total"] > 0 else 0
        patterns.append({
            "decision_type": dtype,
            "total_count": stats["total"],
            "acceptance_rate": round(acceptance_rate, 1),
            "high_confidence_count": stats["high_confidence"],
            "rejection_count": stats["rejected"],
            "company_count": len(stats["companies"]),
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
        "total_decisions": sum(p["total_count"] for p in patterns),
        "your_recent_decisions": recent,
        "reason": None if patterns else INSUFFICIENT_PEERS,
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


def get_strategy_insights(
    db: Session, company_id: int, include_peer_benchmarks: bool = False
) -> Dict[str, Any]:
    profile = get_company_profile(db, company_id)
    if not profile:
        return {"strategies": [], "peer_insights": []}

    from server.services.data_anonymizer import get_opted_in_company_ids

    peer_ids = get_opted_in_company_ids(db, exclude_company_id=company_id)
    all_decisions = []
    if peer_ids:
        all_decisions = (
            db.query(CompanyDecision)
            .filter(
                CompanyDecision.company_id.in_(peer_ids),
                CompanyDecision.status.in_(["accepted", "implemented", "resolved", "completed", "decided"]),
            )
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
        if len(data["companies"]) < MIN_DISTINCT_PEERS:
            continue
        strategies.append({
            "strategy": stype,
            "adoption_count": data["count"],
            "company_count": len(data["companies"]),
            "high_confidence_rate": round(data["high_conf"] / data["count"] * 100, 1) if data["count"] > 0 else 0,
            "recommendation": _strategy_recommendation(stype, profile),
        })

    strategies.sort(key=lambda s: s["adoption_count"], reverse=True)

    # Off by default. _generate_peer_insights medians other companies' raw
    # FinancialRecord revenue and runway. Pass True only for a future opt-in
    # design that also enforces a minimum group size.
    if include_peer_benchmarks:
        peer_insights = _generate_peer_insights(db, profile)
    else:
        peer_insights = _default_peer_insights(profile)

    peer_view = find_similar_companies(db, company_id)

    return {
        "strategies": strategies[:6],
        "peer_insights": peer_insights,
        "profile_summary": {
            "stage": profile["stage"],
            "industry": profile["industry"],
            "mrr_range": profile["mrr_range"],
            "growth_tier": profile["growth_tier"],
        },
        "similar_companies": peer_view["similar_companies"],
        "similar_company_aggregates": peer_view["aggregates"],
        "similar_companies_reason": peer_view["reason"],
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


# Cross-tenant aggregates need at least this many distinct other companies per
# bucket, or a "median" is one identifiable company's numbers.
MIN_PEER_COMPANIES = 5


def _eligible_peers(companies) -> List[Any]:
    """Opted-in, non-sample companies only."""
    out = []
    for c in companies:
        if not getattr(c, "data_sharing_enabled", False):
            continue
        if getattr(c, "is_sample", False):
            continue
        out.append(c)
    return out


def _median(values: List[float]) -> float:
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def _insufficient_peers_insight(peer_count: int) -> Dict[str, Any]:
    return {
        "type": "insufficient_peers",
        "title": "Not enough peers yet",
        "description": (
            f"Peer comparisons need at least {MIN_PEER_COMPANIES} comparable companies "
            "that share data. There are not enough yet."
        ),
        "peer_count": peer_count,
        "min_peers": MIN_PEER_COMPANIES,
    }


def _latest_per_company(peer_fins, attr: str, valid) -> List[float]:
    """One value per company (its most recent valid record)."""
    seen: Dict[int, float] = {}
    for f in peer_fins:
        if f.company_id in seen:
            continue
        raw = getattr(f, attr, None)
        if raw is None:
            continue
        value = float(raw)
        if valid(value):
            seen[f.company_id] = value
    return list(seen.values())


def _generate_peer_insights(db: Session, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    insights = []

    stage = profile.get("stage", "seed")
    industry = profile.get("industry", "unknown")

    peer_companies = _eligible_peers(
        db.query(Company)
        .filter(
            Company.id != profile.get("company_id"),
            Company.data_sharing_enabled == True,  # noqa: E712
            or_(
                Company.industry.ilike(f"%{industry}%"),
                Company.stage == stage,
            ),
        )
        .limit(200)
        .all()
    )

    if len(peer_companies) < MIN_PEER_COMPANIES:
        return [_insufficient_peers_insight(len(peer_companies))]

    peer_ids = [c.id for c in peer_companies]

    peer_fins = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id.in_(peer_ids))
        .order_by(FinancialRecord.period_start.desc())
        .limit(2000)
        .all()
    )

    if peer_fins:
        revenues = _latest_per_company(peer_fins, "revenue", lambda v: v > 0)
        runways = _latest_per_company(peer_fins, "runway_months", lambda v: 0 < v <= 120)

        if len(revenues) >= MIN_PEER_COMPANIES:
            median_rev = _median(revenues)
            your_mrr = profile.get("mrr", 0)
            position = "above" if your_mrr > median_rev else "below" if your_mrr < median_rev else "at"
            insights.append({
                "type": "revenue_benchmark",
                "title": "Revenue vs Peers",
                "description": f"Your MRR is {position} the peer median of ${median_rev:,.0f}/mo across {len(revenues)} companies.",
                "metric": f"${median_rev:,.0f}",
                "your_value": f"${your_mrr:,.0f}",
                "position": position,
                "peer_count": len(revenues),
            })

        if len(runways) >= MIN_PEER_COMPANIES:
            median_runway = _median(runways)
            your_runway = profile.get("runway_months", 0)
            insights.append({
                "type": "runway_benchmark",
                "title": "Runway vs Peers",
                "description": f"Peer median runway is {median_runway:.0f} months. {'You have more buffer.' if your_runway > median_runway else 'Consider extending runway.'}",
                "metric": f"{median_runway:.0f}mo",
                "your_value": f"{your_runway:.0f}mo",
                "position": "above" if your_runway > median_runway else "below",
                "peer_count": len(runways),
            })

    peer_decisions = (
        db.query(CompanyDecision)
        .filter(
            CompanyDecision.company_id.in_(peer_ids),
            CompanyDecision.status.in_(["accepted", "implemented"]),
        )
        .limit(500)
        .all()
    )

    if len({d.company_id for d in peer_decisions}) >= MIN_PEER_COMPANIES:
        type_companies: Dict[str, set] = defaultdict(set)
        type_counts = defaultdict(int)
        for d in peer_decisions:
            t = _classify_decision_type(d.title)
            type_counts[t] += 1
            type_companies[t].add(d.company_id)

        eligible = {t: n for t, n in type_counts.items() if len(type_companies[t]) >= MIN_PEER_COMPANIES}
        if eligible:
            top_type = max(eligible, key=eligible.get)
            insights.append({
                "type": "decision_trend",
                "title": "Top Peer Strategy",
                "description": f"The most common strategy among peers is '{top_type}' ({type_counts[top_type]} decisions). Consider if this applies to your situation.",
                "metric": top_type,
                "count": type_counts[top_type],
            })

    return insights if insights else [_insufficient_peers_insight(len(peer_companies))]


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
    """Raw cross-company revenue percentiles.

    Unsafe for tenant-facing responses: the newest 500 FinancialRecords across
    every company, with no opt-in, no is_sample filter, and no minimum group
    size. p25/median/p75 can be another company's exact revenue. The
    intelligence benchmarks and summary endpoints must not call this.
    """
    profile = get_company_profile(db, company_id)

    peers = _eligible_peers(
        db.query(Company)
        .filter(Company.id != company_id, Company.data_sharing_enabled == True)  # noqa: E712
        .all()
    )
    peer_stage = {c.id: (c.stage or "unknown").lower() for c in peers}

    records = []
    if peer_stage:
        records = (
            db.query(FinancialRecord)
            .filter(FinancialRecord.company_id.in_(list(peer_stage)))
            .order_by(FinancialRecord.period_start.desc())
            .limit(5000)
            .all()
        )

    # Latest positive revenue per company, bucketed by stage.
    latest_rev: Dict[int, float] = {}
    for rec in records:
        if rec.company_id in latest_rev:
            continue
        rev = float(rec.revenue or 0)
        if rev > 0:
            latest_rev[rec.company_id] = rev

    stage_groups: Dict[str, List[float]] = defaultdict(list)
    for cid, rev in latest_rev.items():
        stage_groups[peer_stage[cid]].append(rev)

    stage_benchmarks = {}
    insufficient_stages: Dict[str, int] = {}
    for stage, revenues in stage_groups.items():
        n = len(revenues)
        if n < MIN_PEER_COMPANIES:
            insufficient_stages[stage] = n
            continue
        sorted_r = sorted(revenues)
        stage_benchmarks[stage] = {
            "p25": sorted_r[n // 4],
            "median": sorted_r[n // 2],
            "p75": sorted_r[3 * n // 4],
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
        # Stages with fewer than MIN_PEER_COMPANIES opted-in peers: count only.
        "insufficient_peers": insufficient_stages,
        "min_peers": MIN_PEER_COMPANIES,
        "total_companies_analyzed": len(latest_rev),
        "total_data_points": len(records),
    }


def get_cross_company_patterns(db: Session, company_id: int) -> Dict[str, Any]:
    profile = get_company_profile(db, company_id)
    if not profile:
        return {"patterns": [], "source": "no_profile"}

    try:
        from server.services.pattern_aggregator import (
            aggregate_benchmark_updates,
            aggregate_decision_patterns,
            get_relevant_patterns,
        )
        # Recompute without this company and without writing the global rows.
        live = aggregate_decision_patterns(db, exclude_company_id=company_id)
        benchmarks = aggregate_benchmark_updates(db, exclude_company_id=company_id)
        patterns = []
        for row in live.get("patterns") or []:
            patterns.append({**row, "pattern_type": "decision_outcome"})
        for stage, stats in (benchmarks.get("benchmarks") or {}).items():
            for metric_name, percentiles in stats.items():
                if metric_name == "sample_size" or not isinstance(percentiles, dict):
                    continue
                patterns.append({
                    "pattern_type": "benchmark",
                    "stage": stage,
                    "decision_type": metric_name,
                    "sample_size": percentiles.get("sample_size", 0),
                    "contributing_companies": percentiles.get("companies", 0),
                    "p25_impact": percentiles.get("p25"),
                    "median_impact": percentiles.get("median"),
                    "p75_impact": percentiles.get("p75"),
                })
        stored = get_relevant_patterns(
            db,
            industry=profile.get("industry", "unknown"),
            stage=profile.get("stage", "unknown"),
        )
        patterns.extend(row for row in stored if row.get("pattern_type") == "research")
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

    peer_view = find_similar_companies(db, company_id, limit=5)
    patterns = get_decision_patterns(db, company_id)
    # Do not call get_growth_benchmarks or peer financial benchmarks. Both
    # aggregate other companies' FinancialRecord.revenue with no opt-in and
    # no minimum group size. Own profile and non-financial blocks stay.
    strategies = get_strategy_insights(db, company_id, include_peer_benchmarks=False)
    cross_company = get_cross_company_patterns(db, company_id)

    total_events = (
        db.query(func.count(TwinEvent.id))
        .filter(TwinEvent.company_id == company_id)
        .scalar() or 0
    )

    return {
        "company_profile": profile,
        "similar_companies": peer_view["similar_companies"],
        "similar_company_aggregates": peer_view["aggregates"],
        "similar_companies_reason": peer_view["reason"],
        "decision_patterns": patterns,
        "strategy_insights": strategies,
        "growth_benchmarks": None,
        "cross_company_patterns": cross_company,
        "graph_stats": {
            "total_events": total_events,
            "similar_companies_found": peer_view["peer_count"],
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

        peer_view = find_similar_companies(db, company_id, limit=3)
        result["similarity_recalculated"] = True
        result["similar_companies_count"] = peer_view["peer_count"]
        if peer_view["reason"]:
            result["similar_companies_reason"] = peer_view["reason"]

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

    peer_view = find_similar_companies(db, company_id, limit=5)
    if peer_view["aggregates"]:
        relationships.append({
            "from": {"type": "Company", "id": company_id},
            "to": {"type": "PeerCohort", "peer_count": peer_view["peer_count"]},
            "relationship": "SIMILAR_TO",
            "properties": {"peer_count": peer_view["peer_count"]},
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


def generate_ai_strategy_insights(
    db: Session, company_id: int, include_peer_benchmarks: bool = False
) -> Dict[str, Any]:
    profile = get_company_profile(db, company_id)
    if not profile:
        return {"insights": [], "error": "Company not found"}

    peer_view = find_similar_companies(db, company_id, limit=10)
    patterns = get_decision_patterns(db, company_id)
    strategies = get_strategy_insights(
        db, company_id, include_peer_benchmarks=include_peer_benchmarks
    )
    # Do not call get_growth_benchmarks. Its stage median is another company's
    # raw revenue, and recommendations copies that sentence into its response.
    # This handler does not call an LLM, so there is no prompt to scrub.

    insights = []

    peer_strategies = strategies.get("strategies", [])
    your_decisions = patterns.get("your_recent_decisions", [])
    your_decision_types = set(d.get("type") for d in your_decisions)

    for ps in peer_strategies[:3]:
        if ps["strategy"] not in your_decision_types and ps["adoption_count"] >= 2:
            insights.append({
                "type": "strategy_gap",
                "severity": "medium",
                "title": f"Peers are adopting '{ps['strategy'].replace('_', ' ')}' strategy",
                "description": f"{ps['company_count']} companies have implemented {ps['strategy'].replace('_', ' ')} decisions with {ps['high_confidence_rate']}% high-confidence outcomes. You haven't explored this strategy yet.",
                "recommended_strategies": [ps["strategy"]],
                "peer_evidence": {
                    "adoption_count": ps["adoption_count"],
                    "company_count": ps["company_count"],
                    "confidence_rate": ps["high_confidence_rate"],
                },
            })

    if peer_view["aggregates"]:
        insights.append({
            "type": "peer_network",
            "severity": "info",
            "title": f"Aggregated cohort of {peer_view['peer_count']} similar companies",
            "description": (
                f"Aggregated from {peer_view['peer_count']} opted-in companies. "
                "Individual companies are not listed."
            ),
            "peer_count": peer_view["peer_count"],
            "aggregates": peer_view["aggregates"],
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
        "similar_companies": peer_view["similar_companies"],
        "similar_company_aggregates": peer_view["aggregates"],
        "similar_companies_reason": peer_view["reason"],
        "peer_count": peer_view["peer_count"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_simulation_graph_recommendations(
    db: Session, company_id: int, simulation_result: Optional[Dict] = None
) -> Dict[str, Any]:
    profile = get_company_profile(db, company_id)
    if not profile:
        return {"recommendations": []}

    peer_view = find_similar_companies(db, company_id, limit=10)
    strategies = get_strategy_insights(db, company_id, include_peer_benchmarks=False)
    ai_insights = generate_ai_strategy_insights(db, company_id, include_peer_benchmarks=False)

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
                "peer_evidence": (
                    f"Aggregated from {peer_view['peer_count']} opted-in companies"
                    if peer_view["aggregates"]
                    else "Peer detail withheld"
                ),
            })
        elif survival_prob is not None and survival_prob > 0.8:
            recommendations.append({
                "type": "growth_opportunity",
                "priority": "medium",
                "title": "Strong survival — consider growth investments",
                "description": f"With {survival_prob*100:.0f}% survival probability, you have room to invest in growth. Peers at this confidence level typically accelerate hiring and market expansion.",
                "suggested_actions": ["Invest in sales team", "Explore new channels", "Consider fundraising"],
                "peer_evidence": (
                    f"Aggregated from {peer_view['peer_count']} opted-in companies"
                    if peer_view["aggregates"]
                    else "Peer detail withheld"
                ),
            })

    peer_strategies = strategies.get("strategies", [])
    for ps in peer_strategies[:2]:
        if ps["adoption_count"] >= 2:
            recommendations.append({
                "type": "peer_strategy",
                "priority": "medium",
                "title": f"Peer-validated strategy: {ps['strategy'].replace('_', ' ').title()}",
                "description": ps.get("recommendation", f"{ps['company_count']} peer companies have successfully used this strategy."),
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
        "similar_companies": peer_view["similar_companies"],
        "similar_company_aggregates": peer_view["aggregates"],
        "similar_companies_reason": peer_view["reason"],
        "peer_count": peer_view["peer_count"],
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

    peer_view = find_similar_companies(db, company_id, limit=5)
    if peer_view["aggregates"]:
        nodes.append({
            "id": "peer_cohort",
            "type": "PeerCohort",
            "label": f"{peer_view['peer_count']} similar companies",
            "properties": {"peer_count": peer_view["peer_count"]},
            "is_self": False,
        })
        edges.append({
            "from": f"company_{company_id}",
            "to": "peer_cohort",
            "relationship": "SIMILAR_TO",
            "properties": {"peer_count": peer_view["peer_count"]},
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
