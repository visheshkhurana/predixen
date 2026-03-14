"""
Data Confidence Engine — Scoring the reliability of financial metrics.

Computes a weighted confidence score per metric based on:
  - Freshness (30%): How recently the data was updated
  - Coverage (40%): How complete the data is across expected fields
  - Accuracy (30%): Cross-validation score from truth scan results
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import text
from server.core.db import SessionLocal

logger = logging.getLogger(__name__)

METRIC_DEFINITIONS = {
    "mrr": {"category": "revenue", "required_sources": ["financial_records", "stripe"]},
    "arr": {"category": "revenue", "required_sources": ["financial_records"]},
    "burn_rate": {"category": "expenses", "required_sources": ["financial_records"]},
    "runway": {"category": "computed", "required_sources": ["financial_records"]},
    "cash_balance": {"category": "balance_sheet", "required_sources": ["financial_records", "plaid"]},
    "churn_rate": {"category": "retention", "required_sources": ["financial_records"]},
    "cac": {"category": "unit_economics", "required_sources": ["financial_records"]},
    "ltv": {"category": "unit_economics", "required_sources": ["financial_records"]},
    "gross_margin": {"category": "profitability", "required_sources": ["financial_records"]},
    "headcount": {"category": "team", "required_sources": ["team_members"]},
    "growth_rate": {"category": "growth", "required_sources": ["financial_records"]},
    "net_burn": {"category": "expenses", "required_sources": ["financial_records"]},
}


def compute_freshness_score(last_updated: Optional[datetime]) -> float:
    if not last_updated:
        return 0.0
    now = datetime.now(timezone.utc)
    if last_updated.tzinfo is None:
        from datetime import timezone as tz
        last_updated = last_updated.replace(tzinfo=tz.utc)
    age_hours = (now - last_updated).total_seconds() / 3600
    if age_hours < 1:
        return 1.0
    if age_hours < 24:
        return 0.9
    if age_hours < 168:
        return 0.7
    if age_hours < 720:
        return 0.4
    return 0.1


def compute_coverage_score(company_id: int, metric_name: str) -> float:
    try:
        with SessionLocal() as db:
            record_count = db.execute(
                text("""
                    SELECT COUNT(*) FROM financial_records
                    WHERE company_id = :cid AND period IS NOT NULL
                """),
                {"cid": company_id},
            ).scalar() or 0

            if record_count >= 12:
                return 1.0
            if record_count >= 6:
                return 0.8
            if record_count >= 3:
                return 0.6
            if record_count >= 1:
                return 0.3
            return 0.0
    except Exception:
        return 0.0


def compute_accuracy_score(company_id: int) -> float:
    try:
        with SessionLocal() as db:
            row = db.execute(
                text("""
                    SELECT overall_score FROM truth_scans
                    WHERE company_id = :cid
                    ORDER BY created_at DESC LIMIT 1
                """),
                {"cid": company_id},
            ).fetchone()

            if row and row[0]:
                return min(1.0, float(row[0]) / 100.0)
            return 0.5
    except Exception:
        return 0.5


def compute_confidence(company_id: int, metric_name: str) -> dict:
    try:
        with SessionLocal() as db:
            row = db.execute(
                text("""
                    SELECT updated_at FROM financial_records
                    WHERE company_id = :cid
                    ORDER BY updated_at DESC LIMIT 1
                """),
                {"cid": company_id},
            ).fetchone()
            last_updated = row[0] if row else None

        freshness = compute_freshness_score(last_updated)
        coverage = compute_coverage_score(company_id, metric_name)
        accuracy = compute_accuracy_score(company_id)

        confidence = (freshness * 0.3) + (coverage * 0.4) + (accuracy * 0.3)

        return {
            "metric_name": metric_name,
            "freshness_score": round(freshness, 3),
            "coverage_score": round(coverage, 3),
            "accuracy_score": round(accuracy, 3),
            "confidence_score": round(confidence, 3),
            "grade": _score_to_grade(confidence),
            "last_updated": last_updated.isoformat() if last_updated else None,
        }
    except Exception as e:
        logger.error(f"Confidence computation failed for {metric_name}: {e}")
        return {
            "metric_name": metric_name,
            "freshness_score": 0,
            "coverage_score": 0,
            "accuracy_score": 0,
            "confidence_score": 0,
            "grade": "unknown",
            "last_updated": None,
        }


def _score_to_grade(score: float) -> str:
    if score >= 0.9:
        return "high"
    if score >= 0.7:
        return "good"
    if score >= 0.5:
        return "moderate"
    if score >= 0.3:
        return "low"
    return "very_low"


def compute_all_confidence(company_id: int) -> dict:
    results = {}
    for metric_name in METRIC_DEFINITIONS:
        results[metric_name] = compute_confidence(company_id, metric_name)

    scores = [r["confidence_score"] for r in results.values() if r["confidence_score"] > 0]
    overall = sum(scores) / len(scores) if scores else 0.0

    return {
        "company_id": company_id,
        "overall_confidence": round(overall, 3),
        "overall_grade": _score_to_grade(overall),
        "metrics": results,
    }


def save_confidence_scores(company_id: int) -> dict:
    all_scores = compute_all_confidence(company_id)
    try:
        with SessionLocal() as db:
            for metric_name, data in all_scores["metrics"].items():
                db.execute(
                    text("""
                        INSERT INTO data_confidence_scores
                            (company_id, metric_name, freshness_score, coverage_score, accuracy_score, confidence_score, updated_at)
                        VALUES (:cid, :metric, :fresh, :coverage, :accuracy, :conf, :updated)
                        ON CONFLICT (company_id, metric_name)
                        DO UPDATE SET
                            freshness_score = :fresh,
                            coverage_score = :coverage,
                            accuracy_score = :accuracy,
                            confidence_score = :conf,
                            updated_at = :updated
                    """),
                    {
                        "cid": company_id,
                        "metric": metric_name,
                        "fresh": data["freshness_score"],
                        "coverage": data["coverage_score"],
                        "accuracy": data["accuracy_score"],
                        "conf": data["confidence_score"],
                        "updated": datetime.now(timezone.utc),
                    },
                )
            db.commit()
    except Exception as e:
        logger.error(f"Failed to save confidence scores: {e}")
    return all_scores
