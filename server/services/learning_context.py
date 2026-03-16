import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


def build_learning_context(company_id: int, db: Session, query_type: Optional[str] = None) -> Dict[str, Any]:
    context: Dict[str, Any] = {
        "recommendation_insights": [],
        "common_pitfalls": [],
        "simulation_accuracy": None,
        "high_quality_categories": [],
        "low_quality_categories": [],
    }

    try:
        from server.services.feedback_analyzer import compute_recommendation_quality, correlate_with_outcomes
        quality_scores = compute_recommendation_quality(db, company_id=company_id)

        high_quality = []
        low_quality = []
        for cat, score in quality_scores.items():
            if score >= 70:
                high_quality.append({"category": cat, "score": score})
            elif score < 40:
                low_quality.append({"category": cat, "score": score})

        high_quality.sort(key=lambda x: x["score"], reverse=True)
        low_quality.sort(key=lambda x: x["score"])
        context["high_quality_categories"] = high_quality[:5]
        context["low_quality_categories"] = low_quality[:5]

        outcome_correlations = correlate_with_outcomes(db, company_id=company_id)
        for corr in outcome_correlations[:5]:
            cat = corr["advice_category"]
            pos_rate = corr["positive_rate"]
            total = corr["total_decisions"]
            if total >= 2:
                context["recommendation_insights"].append({
                    "category": cat,
                    "insight": f"{cat.replace('_', ' ').title()} recommendations have a {pos_rate:.0f}% positive outcome rate across {total} tracked decisions.",
                    "positive_rate": pos_rate,
                    "sample_size": total,
                })

        negative_corrs = [c for c in outcome_correlations if c.get("negative_rate", 0) > 40 and c["total_decisions"] >= 2]
        for corr in negative_corrs[:3]:
            cat = corr["advice_category"]
            context["common_pitfalls"].append({
                "category": cat,
                "warning": f"Historically, {cat.replace('_', ' ')} advice has had a {corr['negative_rate']:.0f}% negative outcome rate. Extra caution advised.",
                "negative_rate": corr["negative_rate"],
            })

    except Exception as e:
        logger.debug(f"Failed to build feedback-based learning context: {e}")

    try:
        context["simulation_accuracy"] = _get_simulation_accuracy(db, company_id)
    except Exception as e:
        logger.debug(f"Failed to get simulation accuracy: {e}")

    try:
        context["company_specific"] = _get_company_specific_learning(db, company_id)
    except Exception as e:
        logger.debug(f"Failed to get company-specific learning: {e}")

    return context


def _get_simulation_accuracy(db: Session, company_id: int) -> Optional[Dict[str, Any]]:
    try:
        rows = db.execute(text("""
            SELECT COUNT(*) as total,
                   AVG(CASE WHEN ss.results_json IS NOT NULL THEN 1 ELSE 0 END) as completed_rate
            FROM survival_simulations ss
        """)).fetchone()
        if rows and rows[0] > 0:
            return {
                "total_simulations": int(rows[0]),
                "note": "Simulation engine actively used for projections.",
            }
    except Exception:
        pass
    return None


def _get_company_specific_learning(db: Session, company_id: int) -> Optional[Dict[str, Any]]:
    try:
        row = db.execute(text("""
            SELECT COUNT(*) as cnt,
                   SUM(CASE WHEN rating = 'helpful' THEN 1 ELSE 0 END) as helpful
            FROM copilot_feedback
            WHERE company_id = :cid
        """), {"cid": company_id}).fetchone()
        if row and row[0] > 0:
            total = int(row[0])
            helpful = int(row[1])
            return {
                "total_interactions_rated": total,
                "satisfaction_rate": round(helpful / max(total, 1) * 100, 1),
            }
    except Exception:
        pass
    return None


def format_learning_context_for_prompt(learning_ctx: Dict[str, Any]) -> str:
    lines = []

    insights = learning_ctx.get("recommendation_insights", [])
    if insights:
        lines.append("## Recommendation Effectiveness (from tracked outcomes)")
        for ins in insights:
            lines.append(f"- {ins['insight']}")

    pitfalls = learning_ctx.get("common_pitfalls", [])
    if pitfalls:
        lines.append("\n## Known Pitfalls")
        for p in pitfalls:
            lines.append(f"- WARNING: {p['warning']}")

    high_q = learning_ctx.get("high_quality_categories", [])
    if high_q:
        lines.append("\n## High-Performing Advice Categories")
        for hq in high_q:
            lines.append(f"- {hq['category']}: {hq['score']:.0f}% quality score")

    low_q = learning_ctx.get("low_quality_categories", [])
    if low_q:
        lines.append("\n## Low-Performing Advice Categories (use with extra caution)")
        for lq in low_q:
            lines.append(f"- {lq['category']}: {lq['score']:.0f}% quality score — consider alternative approaches")

    sim_acc = learning_ctx.get("simulation_accuracy")
    if sim_acc:
        lines.append(f"\n## Simulation Context")
        lines.append(f"- {sim_acc.get('note', 'Simulation data available.')}")
        if sim_acc.get("total_simulations"):
            lines.append(f"- Total simulations run: {sim_acc['total_simulations']}")

    company_ctx = learning_ctx.get("company_specific")
    if company_ctx:
        lines.append(f"\n## This Company's AI Interaction History")
        lines.append(f"- {company_ctx['total_interactions_rated']} AI responses rated by this user")
        lines.append(f"- Satisfaction rate: {company_ctx['satisfaction_rate']:.0f}%")

    if not lines:
        return ""

    return "\n".join(lines)
