import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import text
from server.core.db import SessionLocal

logger = logging.getLogger(__name__)


def compute_accuracy(company_id: int) -> dict:
    try:
        with SessionLocal() as db:
            runs = db.execute(
                text("""
                    SELECT sr.id, sr.scenario_id, sr.outputs_json, sr.created_at
                    FROM simulation_runs sr
                    JOIN scenarios s ON sr.scenario_id = s.id
                    WHERE s.company_id = :cid
                      AND sr.status = 'completed'
                      AND sr.created_at >= NOW() - INTERVAL '12 months'
                      AND sr.outputs_json IS NOT NULL
                    ORDER BY sr.created_at DESC
                    LIMIT 20
                """),
                {"cid": company_id},
            ).fetchall()

            if not runs:
                return {"status": "no_runs", "message": "No simulation runs found in past 12 months", "records_created": 0}

            actuals = db.execute(
                text("""
                    SELECT period_start, revenue, net_burn, cash_balance, mrr, customers
                    FROM financial_records
                    WHERE company_id = :cid
                    ORDER BY period_start DESC
                    LIMIT 24
                """),
                {"cid": company_id},
            ).fetchall()

            if not actuals:
                return {"status": "no_actuals", "message": "No financial records to compare against", "records_created": 0}

            actuals_by_month = {}
            prev_customers = None
            prev_mrr = None
            actuals_sorted = sorted(actuals, key=lambda r: r[0] if r[0] else datetime.min.date())
            for row in actuals_sorted:
                period = row[0]
                month_key = f"{period.year}-{period.month:02d}" if period else None
                if month_key:
                    customers = row[5]
                    mrr_val = row[4] or row[1] or 0
                    churn_amount = None
                    if prev_customers is not None and customers is not None and prev_customers > 0:
                        lost = max(0, prev_customers - customers)
                        if lost > 0 and prev_mrr and prev_customers > 0:
                            churn_amount = lost * (prev_mrr / prev_customers)
                        elif lost > 0:
                            churn_amount = 0.0
                    actuals_by_month[month_key] = {
                        "revenue": row[1] or row[4] or 0,
                        "burn": row[2] or 0,
                        "cash": row[3] or 0,
                        "churn": churn_amount,
                    }
                    prev_customers = customers
                    prev_mrr = mrr_val

            records_created = 0
            accuracy_scores = []

            existing_keys = set()
            existing_rows = db.execute(
                text("""
                    SELECT simulation_run_id, prediction_month
                    FROM simulation_accuracy
                    WHERE company_id = :cid
                """),
                {"cid": company_id},
            ).fetchall()
            for er in existing_rows:
                existing_keys.add((er[0], er[1]))

            for run in runs:
                run_id = run[0]
                scenario_id = run[1]
                outputs = run[2] if isinstance(run[2], dict) else json.loads(run[2]) if run[2] else {}
                run_date = run[3]

                bands = outputs.get("bands", {})
                if not bands:
                    continue

                revenue_p50 = bands.get("revenue", {}).get("p50", [])
                burn_p50 = bands.get("burn", {}).get("p50", [])
                cash_p50 = bands.get("cash", {}).get("p50", [])
                churn_p50 = bands.get("churn", {}).get("p50", [])

                if not revenue_p50:
                    continue

                for month_idx in range(min(len(revenue_p50), 12)):
                    if not run_date:
                        continue

                    if (run_id, month_idx + 1) in existing_keys:
                        continue

                    predicted_date = run_date + timedelta(days=30 * (month_idx + 1))
                    month_key = f"{predicted_date.year}-{predicted_date.month:02d}"

                    if month_key not in actuals_by_month:
                        continue

                    actual = actuals_by_month[month_key]
                    pred_rev = revenue_p50[month_idx] if month_idx < len(revenue_p50) else None
                    pred_burn = burn_p50[month_idx] if month_idx < len(burn_p50) else None
                    pred_cash = cash_p50[month_idx] if month_idx < len(cash_p50) else None
                    pred_churn = churn_p50[month_idx] if month_idx < len(churn_p50) else None

                    variance_pct = {}
                    score_components = []

                    if pred_rev is not None and actual["revenue"] is not None:
                        denom = pred_rev if pred_rev != 0 else 1
                        var = ((actual["revenue"] - pred_rev) / denom * 100)
                        variance_pct["revenue"] = round(var, 2)
                        score_components.append(max(0, 100 - abs(var)))

                    if pred_burn is not None and actual["burn"] is not None:
                        denom = pred_burn if pred_burn != 0 else 1
                        var = ((actual["burn"] - pred_burn) / denom * 100)
                        variance_pct["burn"] = round(var, 2)
                        score_components.append(max(0, 100 - abs(var)))

                    if pred_cash is not None and actual["cash"] is not None:
                        denom = pred_cash if pred_cash != 0 else 1
                        var = ((actual["cash"] - pred_cash) / denom * 100)
                        variance_pct["cash"] = round(var, 2)
                        score_components.append(max(0, 100 - abs(var)))

                    actual_churn = actual.get("churn")
                    if pred_churn is not None and actual_churn is not None:
                        denom = pred_churn if pred_churn != 0 else 1
                        var = ((actual_churn - pred_churn) / denom * 100)
                        variance_pct["churn"] = round(var, 2)
                        score_components.append(max(0, 100 - abs(var)))

                    accuracy_score = sum(score_components) / len(score_components) if score_components else None

                    if accuracy_score is not None:
                        accuracy_scores.append(accuracy_score)

                    db.execute(
                        text("""
                            INSERT INTO simulation_accuracy
                                (company_id, simulation_run_id, scenario_id, prediction_month,
                                 predicted_revenue, actual_revenue, predicted_burn, actual_burn,
                                 predicted_cash, actual_cash, predicted_churn, actual_churn,
                                 variance_pct_json, accuracy_score, computed_at)
                            VALUES (:cid, :run_id, :scenario_id, :month,
                                    :pred_rev, :act_rev, :pred_burn, :act_burn,
                                    :pred_cash, :act_cash, :pred_churn, :act_churn,
                                    :variance, :score, :now)
                        """),
                        {
                            "cid": company_id,
                            "run_id": run_id,
                            "scenario_id": scenario_id,
                            "month": month_idx + 1,
                            "pred_rev": pred_rev,
                            "act_rev": actual["revenue"],
                            "pred_burn": pred_burn,
                            "act_burn": actual["burn"],
                            "pred_cash": pred_cash,
                            "act_cash": actual["cash"],
                            "pred_churn": pred_churn,
                            "act_churn": actual_churn,
                            "variance": json.dumps(variance_pct),
                            "score": accuracy_score,
                            "now": datetime.now(timezone.utc),
                        },
                    )
                    records_created += 1

            db.commit()

            overall_score = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else None

            return {
                "status": "computed",
                "records_created": records_created,
                "overall_accuracy": round(overall_score, 1) if overall_score is not None else None,
                "runs_analyzed": len(runs),
            }

    except Exception as e:
        logger.error(f"Failed to compute accuracy for company {company_id}: {e}")
        return {"status": "error", "message": str(e), "records_created": 0}


def get_accuracy_history(company_id: int, limit: int = 50) -> list[dict]:
    try:
        with SessionLocal() as db:
            rows = db.execute(
                text("""
                    SELECT id, simulation_run_id, scenario_id, prediction_month,
                           predicted_revenue, actual_revenue, predicted_burn, actual_burn,
                           predicted_cash, actual_cash, variance_pct_json, accuracy_score, computed_at,
                           predicted_churn, actual_churn
                    FROM simulation_accuracy
                    WHERE company_id = :cid
                    ORDER BY computed_at DESC
                    LIMIT :lim
                """),
                {"cid": company_id, "lim": limit},
            ).fetchall()

            return [
                {
                    "id": r[0],
                    "simulation_run_id": r[1],
                    "scenario_id": r[2],
                    "prediction_month": r[3],
                    "predicted_revenue": r[4],
                    "actual_revenue": r[5],
                    "predicted_burn": r[6],
                    "actual_burn": r[7],
                    "predicted_cash": r[8],
                    "actual_cash": r[9],
                    "variance_pct": r[10] if isinstance(r[10], dict) else (json.loads(r[10]) if r[10] else {}),
                    "accuracy_score": r[11],
                    "computed_at": r[12].isoformat() if r[12] else None,
                    "predicted_churn": r[13] if len(r) > 13 else None,
                    "actual_churn": r[14] if len(r) > 14 else None,
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get accuracy history: {e}")
        return []


def get_accuracy_summary(company_id: int) -> dict:
    try:
        with SessionLocal() as db:
            row = db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total,
                        AVG(accuracy_score) as avg_score,
                        MIN(accuracy_score) as min_score,
                        MAX(accuracy_score) as max_score
                    FROM simulation_accuracy
                    WHERE company_id = :cid AND accuracy_score IS NOT NULL
                """),
                {"cid": company_id},
            ).fetchone()

            metric_rows = db.execute(
                text("""
                    SELECT 
                        AVG(CASE WHEN predicted_revenue > 0 THEN ((actual_revenue - predicted_revenue) / predicted_revenue * 100) END) as avg_revenue_var,
                        AVG(CASE WHEN predicted_burn > 0 THEN ((actual_burn - predicted_burn) / predicted_burn * 100) END) as avg_burn_var,
                        AVG(CASE WHEN predicted_cash > 0 THEN ((actual_cash - predicted_cash) / predicted_cash * 100) END) as avg_cash_var,
                        AVG(CASE WHEN predicted_churn > 0 THEN ((actual_churn - predicted_churn) / predicted_churn * 100) END) as avg_churn_var
                    FROM simulation_accuracy
                    WHERE company_id = :cid
                """),
                {"cid": company_id},
            ).fetchone()

            recent = db.execute(
                text("""
                    SELECT accuracy_score, computed_at
                    FROM simulation_accuracy
                    WHERE company_id = :cid AND accuracy_score IS NOT NULL
                    ORDER BY computed_at DESC
                    LIMIT 12
                """),
                {"cid": company_id},
            ).fetchall()

            return {
                "total_comparisons": row[0] if row else 0,
                "overall_accuracy": round(row[1], 1) if row and row[1] is not None else None,
                "min_accuracy": round(row[2], 1) if row and row[2] is not None else None,
                "max_accuracy": round(row[3], 1) if row and row[3] is not None else None,
                "per_metric": {
                    "revenue_bias_pct": round(metric_rows[0], 2) if metric_rows and metric_rows[0] else None,
                    "burn_bias_pct": round(metric_rows[1], 2) if metric_rows and metric_rows[1] else None,
                    "cash_bias_pct": round(metric_rows[2], 2) if metric_rows and metric_rows[2] else None,
                    "churn_bias_pct": round(metric_rows[3], 2) if metric_rows and len(metric_rows) > 3 and metric_rows[3] else None,
                },
                "trend": [
                    {"score": r[0], "date": r[1].isoformat() if r[1] else None}
                    for r in reversed(recent)
                ] if recent else [],
            }
    except Exception as e:
        logger.error(f"Failed to get accuracy summary: {e}")
        return {"total_comparisons": 0, "overall_accuracy": None, "per_metric": {}, "trend": []}
