import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, text

logger = logging.getLogger(__name__)

ADVICE_CATEGORIES = [
    "cost_cutting",
    "fundraising",
    "pricing",
    "hiring",
    "growth_strategy",
    "market_expansion",
    "product_strategy",
    "runway_extension",
    "unit_economics",
    "general",
]


def analyze_feedback_patterns(db: Session, company_id: Optional[int] = None, days: int = 90) -> Dict[str, Any]:
    cutoff = datetime.utcnow() - timedelta(days=days)

    filters = "WHERE cf.created_at >= :cutoff"
    params: Dict[str, Any] = {"cutoff": cutoff}
    if company_id:
        filters += " AND cf.company_id = :company_id"
        params["company_id"] = company_id

    try:
        by_type_rows = db.execute(text(f"""
            SELECT cf.response_type,
                   COUNT(*) as total,
                   SUM(CASE WHEN cf.rating = 'helpful' THEN 1 ELSE 0 END) as helpful_count,
                   SUM(CASE WHEN cf.rating = 'not_helpful' THEN 1 ELSE 0 END) as not_helpful_count
            FROM copilot_feedback cf
            {filters}
            GROUP BY cf.response_type
            ORDER BY total DESC
        """), params).fetchall()
    except Exception as e:
        logger.debug(f"Feedback pattern analysis failed: {e}")
        by_type_rows = []

    by_type = {}
    total_feedback = 0
    total_helpful = 0
    for row in by_type_rows:
        rtype = row[0] or "general"
        total = int(row[1])
        helpful = int(row[2])
        not_helpful = int(row[3])
        total_feedback += total
        total_helpful += helpful
        by_type[rtype] = {
            "total": total,
            "helpful": helpful,
            "not_helpful": not_helpful,
            "quality_score": round(helpful / max(total, 1) * 100, 1),
        }

    try:
        by_tag_rows = db.execute(text(f"""
            SELECT tag, COUNT(*) as cnt,
                   SUM(CASE WHEN cf.rating = 'helpful' THEN 1 ELSE 0 END) as helpful
            FROM copilot_feedback cf, jsonb_array_elements_text(COALESCE(cf.tags, '[]'::jsonb)) AS tag
            {filters}
            GROUP BY tag
            ORDER BY cnt DESC
            LIMIT 20
        """), params).fetchall()
    except Exception:
        by_tag_rows = []

    by_tag = {}
    for row in by_tag_rows:
        tag = row[0]
        cnt = int(row[1])
        helpful = int(row[2])
        by_tag[tag] = {
            "total": cnt,
            "helpful": helpful,
            "quality_score": round(helpful / max(cnt, 1) * 100, 1),
        }

    return {
        "total_feedback": total_feedback,
        "total_helpful": total_helpful,
        "overall_quality_score": round(total_helpful / max(total_feedback, 1) * 100, 1),
        "by_response_type": by_type,
        "by_tag": by_tag,
        "period_days": days,
    }


def correlate_with_outcomes(db: Session, company_id: Optional[int] = None, days: int = 180) -> List[Dict[str, Any]]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    filters = "WHERE cd.created_at >= :cutoff AND cd.outcome_rating IS NOT NULL"
    params: Dict[str, Any] = {"cutoff": cutoff}
    if company_id:
        filters += " AND cd.company_id = :company_id"
        params["company_id"] = company_id

    try:
        rows = db.execute(text(f"""
            SELECT cd.tags,
                   cd.outcome_rating,
                   cd.confidence,
                   COUNT(*) as cnt
            FROM company_decisions cd
            {filters}
            GROUP BY cd.tags, cd.outcome_rating, cd.confidence
        """), params).fetchall()
    except Exception as e:
        logger.debug(f"Outcome correlation failed: {e}")
        return []

    tag_outcomes: Dict[str, Dict[str, int]] = {}
    for row in rows:
        tags = row[0] or []
        outcome = row[1]
        count = int(row[3])
        if isinstance(tags, list):
            for tag in tags:
                if tag not in tag_outcomes:
                    tag_outcomes[tag] = {"positive": 0, "neutral": 0, "negative": 0, "total": 0}
                tag_outcomes[tag][outcome] = tag_outcomes[tag].get(outcome, 0) + count
                tag_outcomes[tag]["total"] += count

    correlations = []
    for tag, outcomes in tag_outcomes.items():
        total = outcomes["total"]
        if total < 1:
            continue
        correlations.append({
            "advice_category": tag,
            "total_decisions": total,
            "positive_rate": round(outcomes.get("positive", 0) / total * 100, 1),
            "negative_rate": round(outcomes.get("negative", 0) / total * 100, 1),
            "effectiveness_score": round(
                (outcomes.get("positive", 0) * 1.0 - outcomes.get("negative", 0) * 0.5) / total * 100, 1
            ),
        })

    correlations.sort(key=lambda x: x["effectiveness_score"], reverse=True)
    return correlations


def compute_recommendation_quality(db: Session, company_id: Optional[int] = None) -> Dict[str, float]:
    feedback_patterns = analyze_feedback_patterns(db, company_id=company_id)
    outcome_correlations = correlate_with_outcomes(db, company_id=company_id)

    quality_scores: Dict[str, float] = {}

    for rtype, data in feedback_patterns.get("by_response_type", {}).items():
        if data["total"] >= 3:
            quality_scores[rtype] = data["quality_score"]

    for tag_data in feedback_patterns.get("by_tag", {}).items():
        tag, data = tag_data
        if data["total"] >= 3:
            quality_scores[f"tag:{tag}"] = data["quality_score"]

    for corr in outcome_correlations:
        cat = corr["advice_category"]
        if corr["total_decisions"] >= 2:
            existing = quality_scores.get(f"tag:{cat}", 50.0)
            blended = (existing + corr["effectiveness_score"]) / 2
            quality_scores[f"outcome:{cat}"] = round(blended, 1)

    return quality_scores


def get_feedback_stats(db: Session, company_id: Optional[int] = None) -> Dict[str, Any]:
    patterns = analyze_feedback_patterns(db, company_id=company_id)
    quality = compute_recommendation_quality(db, company_id=company_id)
    correlations = correlate_with_outcomes(db, company_id=company_id)

    try:
        trend_sql = """
            SELECT DATE(created_at) as day, COUNT(*) as cnt,
                   SUM(CASE WHEN rating = 'helpful' THEN 1 ELSE 0 END) as helpful
            FROM copilot_feedback
            WHERE created_at >= NOW() - INTERVAL '30 days'
        """
        trend_params: Dict[str, Any] = {}
        if company_id:
            trend_sql += " AND company_id = :company_id"
            trend_params["company_id"] = company_id
        trend_sql += " GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 30"
        recent_rows = db.execute(text(trend_sql), trend_params).fetchall()
        daily_trend = [
            {"date": str(r[0]), "total": int(r[1]), "helpful": int(r[2])}
            for r in recent_rows
        ]
    except Exception:
        daily_trend = []

    return {
        "patterns": patterns,
        "quality_scores": quality,
        "outcome_correlations": correlations,
        "daily_trend": daily_trend,
    }
