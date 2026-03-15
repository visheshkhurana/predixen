"""
Cross-Company Pattern Aggregation Service.

Aggregates anonymized decision outcomes and financial metrics across
opted-in companies to compute success rates, benchmark percentiles,
and pattern intelligence. Privacy-first: only statistical aggregates
are stored — no individual company data is exposed.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import text, func

from server.models.company import Company
from server.models.company_decision import CompanyDecision
from server.models.financial import FinancialRecord
from server.services.data_anonymizer import (
    anonymize_company_metrics,
    anonymize_decision_outcome,
    get_opted_in_company_ids,
)

logger = logging.getLogger(__name__)


def aggregate_decision_patterns(db: Session) -> Dict[str, Any]:
    opted_in_ids = get_opted_in_company_ids(db)
    if not opted_in_ids:
        return {"patterns": [], "contributing_companies": 0, "total_decisions": 0}

    decisions = (
        db.query(CompanyDecision)
        .filter(
            CompanyDecision.company_id.in_(opted_in_ids),
            CompanyDecision.status.in_(["resolved", "accepted", "implemented", "completed", "decided", "rejected"]),
        )
        .limit(2000)
        .all()
    )

    company_cache = {}
    groups = defaultdict(lambda: defaultdict(lambda: {"total": 0, "positive": 0, "companies": set()}))

    for decision in decisions:
        cid = decision.company_id
        if cid not in company_cache:
            company = db.query(Company).filter(Company.id == cid).first()
            if not company:
                continue
            company_cache[cid] = {
                "industry": (company.industry or "unknown").lower(),
                "stage": (company.stage or "unknown").lower(),
            }

        profile = company_cache[cid]
        title_lower = (decision.title or "").lower()
        decision_type = _classify_decision_type(title_lower)

        key = (profile["industry"], profile["stage"])
        groups[key][decision_type]["total"] += 1
        groups[key][decision_type]["companies"].add(cid)

        outcome_positive = (
            decision.status in ("accepted", "implemented", "resolved", "completed", "decided")
            and (decision.confidence or "medium") in ("high", "medium")
        )
        if outcome_positive:
            groups[key][decision_type]["positive"] += 1

    patterns = []
    for (industry, stage), type_stats in groups.items():
        for dtype, stats in type_stats.items():
            if stats["total"] < 2:
                continue
            success_rate = stats["positive"] / stats["total"] * 100 if stats["total"] > 0 else 0
            patterns.append({
                "industry": industry,
                "stage": stage,
                "decision_type": dtype,
                "sample_size": stats["total"],
                "success_rate": round(success_rate, 1),
                "contributing_companies": len(stats["companies"]),
            })

    _store_patterns(db, patterns)

    return {
        "patterns": patterns,
        "contributing_companies": len(opted_in_ids),
        "total_decisions": len(decisions),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def aggregate_benchmark_updates(db: Session) -> Dict[str, Any]:
    opted_in_ids = get_opted_in_company_ids(db)
    if not opted_in_ids:
        return {"benchmarks": {}, "contributing_companies": 0}

    records = (
        db.query(FinancialRecord, Company.stage, Company.industry)
        .join(Company, FinancialRecord.company_id == Company.id)
        .filter(Company.id.in_(opted_in_ids))
        .order_by(FinancialRecord.period_start.desc())
        .limit(2000)
        .all()
    )

    stage_metrics = defaultdict(lambda: {"revenues": [], "burns": [], "runways": [], "margins": [], "companies": set()})

    for rec, stage, industry in records:
        key = (stage or "unknown").lower()
        rev = float(rec.revenue or 0)
        burn = float(rec.net_burn or 0) if hasattr(rec, "net_burn") and rec.net_burn else 0
        runway = float(rec.runway_months or 0) if hasattr(rec, "runway_months") and rec.runway_months else 0
        margin = float(rec.gross_margin or 0) if hasattr(rec, "gross_margin") and rec.gross_margin else 0

        if rev > 0:
            stage_metrics[key]["revenues"].append(rev)
        if burn > 0:
            stage_metrics[key]["burns"].append(burn)
        if 0 < runway <= 120:
            stage_metrics[key]["runways"].append(runway)
        if margin > 0:
            stage_metrics[key]["margins"].append(margin)
        stage_metrics[key]["companies"].add(rec.company_id)

    benchmarks = {}
    for stage, data in stage_metrics.items():
        benchmarks[stage] = {
            "revenue": _compute_percentiles(data["revenues"]),
            "burn": _compute_percentiles(data["burns"]),
            "runway": _compute_percentiles(data["runways"]),
            "gross_margin": _compute_percentiles(data["margins"]),
            "sample_size": len(data["companies"]),
        }

    _store_benchmarks(db, benchmarks)

    return {
        "benchmarks": benchmarks,
        "contributing_companies": len(opted_in_ids),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def get_relevant_patterns(
    db: Session,
    industry: str,
    stage: str,
) -> List[Dict[str, Any]]:
    try:
        result = db.execute(
            text("""
                SELECT pattern_type, industry, stage, decision_type,
                       sample_size, success_rate, median_impact, p25_impact, p75_impact,
                       contributing_companies, computed_at
                FROM cross_company_patterns
                WHERE (industry = :industry OR industry = 'all')
                  AND (stage = :stage OR stage = 'all')
                ORDER BY sample_size DESC
                LIMIT 20
            """),
            {"industry": industry.lower(), "stage": stage.lower()},
        )
        rows = result.fetchall()
        return [
            {
                "pattern_type": r[0],
                "industry": r[1],
                "stage": r[2],
                "decision_type": r[3],
                "sample_size": r[4],
                "success_rate": r[5],
                "median_impact": r[6],
                "p25_impact": r[7],
                "p75_impact": r[8],
                "contributing_companies": r[9],
                "computed_at": r[10].isoformat() if r[10] else None,
            }
            for r in rows
        ]
    except Exception as e:
        logger.debug(f"Error fetching patterns: {e}")
        return []


def get_platform_intelligence_stats(db: Session) -> Dict[str, Any]:
    try:
        total_contributing = (
            db.query(func.count(Company.id))
            .filter(Company.data_sharing_enabled == True)
            .scalar() or 0
        )
        total_companies = db.query(func.count(Company.id)).scalar() or 0

        pattern_count = 0
        latest_computed = None
        try:
            result = db.execute(text(
                "SELECT COUNT(*), MAX(computed_at) FROM cross_company_patterns"
            ))
            row = result.fetchone()
            if row:
                pattern_count = row[0] or 0
                latest_computed = row[1].isoformat() if row[1] else None
        except Exception:
            pass

        total_decisions = (
            db.query(func.count(CompanyDecision.id))
            .filter(
                CompanyDecision.status.in_(["resolved", "accepted", "implemented", "completed", "decided"])
            )
            .scalar() or 0
        )

        total_financial_records = db.query(func.count(FinancialRecord.id)).scalar() or 0

        return {
            "total_companies": total_companies,
            "contributing_companies": total_contributing,
            "participation_rate": round(total_contributing / max(total_companies, 1) * 100, 1),
            "patterns_discovered": pattern_count,
            "total_decisions_analyzed": total_decisions,
            "total_financial_records": total_financial_records,
            "last_computed": latest_computed,
        }
    except Exception as e:
        logger.error(f"Error getting platform stats: {e}")
        return {
            "total_companies": 0,
            "contributing_companies": 0,
            "participation_rate": 0,
            "patterns_discovered": 0,
            "total_decisions_analyzed": 0,
            "total_financial_records": 0,
            "last_computed": None,
        }


def _classify_decision_type(title_lower: str) -> str:
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
            return dtype
    return "general"


def _compute_percentiles(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"p25": 0, "median": 0, "p75": 0, "sample_size": 0}
    s = sorted(values)
    n = len(s)
    return {
        "p25": round(s[n // 4] if n >= 4 else s[0], 2),
        "median": round(s[n // 2], 2),
        "p75": round(s[3 * n // 4] if n >= 4 else s[-1], 2),
        "sample_size": n,
    }


def _store_patterns(db: Session, patterns: List[Dict[str, Any]]) -> None:
    try:
        for p in patterns:
            db.execute(
                text("""
                    INSERT INTO cross_company_patterns
                        (pattern_type, industry, stage, decision_type,
                         sample_size, success_rate, contributing_companies, computed_at)
                    VALUES
                        ('decision_outcome', :industry, :stage, :decision_type,
                         :sample_size, :success_rate, :contributing_companies, NOW())
                    ON CONFLICT (pattern_type, industry, stage, decision_type)
                    DO UPDATE SET
                        sample_size = :sample_size,
                        success_rate = :success_rate,
                        contributing_companies = :contributing_companies,
                        computed_at = NOW()
                """),
                {
                    "industry": p["industry"],
                    "stage": p["stage"],
                    "decision_type": p["decision_type"],
                    "sample_size": p["sample_size"],
                    "success_rate": p["success_rate"],
                    "contributing_companies": p["contributing_companies"],
                },
            )
        db.commit()
    except Exception as e:
        logger.error(f"Error storing patterns: {e}")
        db.rollback()


def _store_benchmarks(db: Session, benchmarks: Dict[str, Any]) -> None:
    try:
        for stage, data in benchmarks.items():
            for metric_name, percentiles in data.items():
                if metric_name == "sample_size":
                    continue
                if not isinstance(percentiles, dict):
                    continue
                db.execute(
                    text("""
                        INSERT INTO cross_company_patterns
                            (pattern_type, industry, stage, decision_type,
                             sample_size, median_impact, p25_impact, p75_impact,
                             contributing_companies, computed_at)
                        VALUES
                            ('benchmark', 'all', :stage, :metric_name,
                             :sample_size, :median, :p25, :p75,
                             :contributing_companies, NOW())
                        ON CONFLICT (pattern_type, industry, stage, decision_type)
                        DO UPDATE SET
                            sample_size = :sample_size,
                            median_impact = :median,
                            p25_impact = :p25,
                            p75_impact = :p75,
                            contributing_companies = :contributing_companies,
                            computed_at = NOW()
                    """),
                    {
                        "stage": stage,
                        "metric_name": metric_name,
                        "sample_size": percentiles.get("sample_size", 0),
                        "median": percentiles.get("median", 0),
                        "p25": percentiles.get("p25", 0),
                        "p75": percentiles.get("p75", 0),
                        "contributing_companies": data.get("sample_size", 0),
                    },
                )
        db.commit()
    except Exception as e:
        logger.error(f"Error storing benchmarks: {e}")
        db.rollback()
