import json
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import text
from server.core.db import SessionLocal

logger = logging.getLogger(__name__)

MIN_SAMPLES_FOR_CONFIDENCE = 3
HIGH_CONFIDENCE_THRESHOLD = 10
MEDIUM_CONFIDENCE_THRESHOLD = 5


def analyze_prediction_bias(company_id: int) -> dict:
    try:
        with SessionLocal() as db:
            rows = db.execute(
                text("""
                    SELECT 
                        predicted_revenue, actual_revenue,
                        predicted_burn, actual_burn,
                        predicted_cash, actual_cash,
                        predicted_churn, actual_churn
                    FROM simulation_accuracy
                    WHERE company_id = :cid AND accuracy_score IS NOT NULL
                    ORDER BY computed_at DESC
                    LIMIT 100
                """),
                {"cid": company_id},
            ).fetchall()

            if not rows:
                return {"status": "insufficient_data", "biases": {}, "sample_count": 0}

            metrics = {
                "revenue": {"diffs": [], "pct_diffs": []},
                "burn": {"diffs": [], "pct_diffs": []},
                "cash": {"diffs": [], "pct_diffs": []},
                "churn": {"diffs": [], "pct_diffs": []},
            }

            for row in rows:
                pred_rev, act_rev, pred_burn, act_burn, pred_cash, act_cash = row[0], row[1], row[2], row[3], row[4], row[5]
                pred_churn = row[6] if len(row) > 6 else None
                act_churn = row[7] if len(row) > 7 else None

                if pred_rev is not None and act_rev is not None and act_rev != 0:
                    pct = ((pred_rev - act_rev) / abs(act_rev)) * 100
                    metrics["revenue"]["pct_diffs"].append(pct)

                if pred_burn is not None and act_burn is not None and act_burn != 0:
                    pct = ((pred_burn - act_burn) / abs(act_burn)) * 100
                    metrics["burn"]["pct_diffs"].append(pct)

                if pred_cash is not None and act_cash is not None and act_cash != 0:
                    pct = ((pred_cash - act_cash) / abs(act_cash)) * 100
                    metrics["cash"]["pct_diffs"].append(pct)

                if pred_churn is not None and act_churn is not None and act_churn != 0:
                    pct = ((pred_churn - act_churn) / abs(act_churn)) * 100
                    metrics["churn"]["pct_diffs"].append(pct)

            biases = {}
            for metric, data in metrics.items():
                diffs = data["pct_diffs"]
                if not diffs:
                    continue

                avg_bias = sum(diffs) / len(diffs)
                count = len(diffs)

                if count >= HIGH_CONFIDENCE_THRESHOLD:
                    confidence = "high"
                elif count >= MEDIUM_CONFIDENCE_THRESHOLD:
                    confidence = "medium"
                else:
                    confidence = "low"

                direction = "optimistic" if avg_bias > 0 else "pessimistic" if avg_bias < 0 else "neutral"

                biases[metric] = {
                    "bias_pct": round(avg_bias, 2),
                    "direction": direction,
                    "sample_count": count,
                    "confidence": confidence,
                    "description": f"Predictions trend {abs(avg_bias):.1f}% {direction}" if direction != "neutral" else "Predictions are well-calibrated",
                }

            return {
                "status": "analyzed",
                "biases": biases,
                "sample_count": len(rows),
            }

    except Exception as e:
        logger.error(f"Failed to analyze bias for company {company_id}: {e}")
        return {"status": "error", "biases": {}, "sample_count": 0}


def suggest_calibration_adjustments(company_id: int) -> dict:
    analysis = analyze_prediction_bias(company_id)
    if analysis["status"] != "analyzed":
        return {"status": analysis["status"], "adjustments": [], "message": "Insufficient data for calibration suggestions"}

    adjustments = []
    for metric, bias_data in analysis["biases"].items():
        bias_pct = bias_data["bias_pct"]
        confidence = bias_data["confidence"]

        if abs(bias_pct) < 3.0:
            continue

        if confidence == "low":
            continue

        correction = -bias_pct

        supported_metrics = {"revenue", "burn", "churn"}
        metric_map = {
            "revenue": "baseline_growth_rate",
            "burn": "burn_reduction_pct",
            "churn": "churn_rate",
        }

        if metric not in supported_metrics:
            continue

        adjustments.append({
            "metric": metric,
            "target_input": metric_map.get(metric, metric),
            "correction_pct": round(correction, 2),
            "bias_pct": round(bias_pct, 2),
            "confidence": confidence,
            "sample_count": bias_data.get("sample_count", 0),
            "description": f"Your {metric} projections trend {abs(bias_pct):.1f}% {'high' if bias_pct > 0 else 'low'} — applying {abs(correction):.1f}% correction",
        })

    return {
        "status": "suggested",
        "adjustments": adjustments,
        "analysis": analysis,
    }


def apply_calibration(company_id: int, adjustments: Optional[list] = None) -> dict:
    if adjustments is None:
        suggestion = suggest_calibration_adjustments(company_id)
        if suggestion["status"] != "suggested":
            return {"status": "no_adjustments", "applied": 0}
        adjustments = suggestion["adjustments"]

    if not adjustments:
        return {"status": "no_adjustments", "applied": 0}

    try:
        with SessionLocal() as db:
            db.execute(
                text("UPDATE calibration_biases SET is_active = 0 WHERE company_id = :cid"),
                {"cid": company_id},
            )

            applied = 0
            for adj in adjustments:
                db.execute(
                    text("""
                        INSERT INTO calibration_biases 
                            (company_id, metric, bias_pct, sample_count, confidence, is_active, applied_at, computed_at)
                        VALUES (:cid, :metric, :bias, :samples, :conf, 1, :now, :now)
                    """),
                    {
                        "cid": company_id,
                        "metric": adj["metric"],
                        "bias": adj["correction_pct"],
                        "samples": adj.get("sample_count", 0),
                        "conf": adj["confidence"],
                        "now": datetime.now(timezone.utc),
                    },
                )
                applied += 1

            db.commit()

            from server.events.event_store import emit_event
            emit_event(
                company_id=company_id,
                user_id=None,
                event_type="calibration_adjustment",
                aggregate_type="simulation",
                payload={
                    "adjustments_applied": applied,
                    "corrections": [
                        {"metric": a["metric"], "correction_pct": a["correction_pct"]}
                        for a in adjustments
                    ],
                },
            )

            return {"status": "applied", "applied": applied, "adjustments": adjustments}

    except Exception as e:
        logger.error(f"Failed to apply calibration for company {company_id}: {e}")
        return {"status": "error", "applied": 0, "message": str(e)}


def get_active_biases(company_id: int) -> dict:
    try:
        with SessionLocal() as db:
            rows = db.execute(
                text("""
                    SELECT metric, bias_pct, confidence, applied_at
                    FROM calibration_biases
                    WHERE company_id = :cid AND is_active = 1
                    ORDER BY applied_at DESC
                """),
                {"cid": company_id},
            ).fetchall()

            biases = {}
            for row in rows:
                biases[row[0]] = {
                    "bias_pct": row[1],
                    "confidence": row[2],
                    "applied_at": row[3].isoformat() if row[3] else None,
                }

            return biases
    except Exception as e:
        logger.error(f"Failed to get active biases: {e}")
        return {}
