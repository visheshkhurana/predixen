"""
Decision Outcome Tracking Service.

Captures metric snapshots when decisions are implemented and again after
a configurable followup period, then computes deltas and an outcome rating.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from server.core.db import SessionLocal

logger = logging.getLogger(__name__)

TRACKED_METRICS = [
    "mrr", "monthly_burn", "cash_balance", "runway_months",
    "churn_rate", "growth_rate", "headcount", "customers",
]


def _get_metrics_snapshot(db: Session, company_id: int) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {}

    try:
        state_row = db.execute(
            text("""
                SELECT state_json, cash_balance, monthly_burn, revenue_monthly
                FROM company_states WHERE company_id = :cid
            """),
            {"cid": company_id},
        ).fetchone()

        if state_row:
            import json
            state = json.loads(state_row[0]) if state_row[0] else {}
            snapshot["mrr"] = state.get("mrr") or (state_row[3] if state_row[3] else 0)
            snapshot["monthly_burn"] = state.get("monthly_burn") or (state_row[2] if state_row[2] else 0)
            snapshot["cash_balance"] = state.get("cash_balance") or (state_row[1] if state_row[1] else 0)
            snapshot["runway_months"] = state.get("runway_months", 0)
            snapshot["churn_rate"] = state.get("churn_rate", 0)
            snapshot["growth_rate"] = state.get("mrr_growth_rate", 0)
    except Exception as e:
        logger.debug(f"Could not read company_states for {company_id}: {e}")

    try:
        from server.models.financial import FinancialRecord
        latest_fin = (
            db.query(FinancialRecord)
            .filter(FinancialRecord.company_id == company_id)
            .order_by(FinancialRecord.period_start.desc())
            .first()
        )
        if latest_fin:
            if not snapshot.get("mrr") and latest_fin.revenue:
                snapshot["mrr"] = float(latest_fin.revenue)
            if hasattr(latest_fin, "headcount") and latest_fin.headcount:
                snapshot["headcount"] = int(latest_fin.headcount)
            if hasattr(latest_fin, "customers") and latest_fin.customers:
                snapshot["customers"] = int(latest_fin.customers)
            if hasattr(latest_fin, "mom_growth") and latest_fin.mom_growth:
                snapshot.setdefault("growth_rate", float(latest_fin.mom_growth))
            if hasattr(latest_fin, "runway_months") and latest_fin.runway_months:
                snapshot.setdefault("runway_months", float(latest_fin.runway_months))
            if not snapshot.get("monthly_burn"):
                burn = 0
                if latest_fin.opex:
                    burn += float(latest_fin.opex)
                if latest_fin.payroll:
                    burn += float(latest_fin.payroll)
                if latest_fin.other_costs:
                    burn += float(latest_fin.other_costs)
                if burn > 0:
                    snapshot["monthly_burn"] = burn
    except Exception as e:
        logger.debug(f"Could not read financial records for {company_id}: {e}")

    if snapshot.get("cash_balance") and snapshot.get("monthly_burn") and snapshot["monthly_burn"] > 0:
        snapshot.setdefault("runway_months", snapshot["cash_balance"] / snapshot["monthly_burn"])

    snapshot["captured_at"] = datetime.utcnow().isoformat()
    return snapshot


def _compute_deltas(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    deltas: Dict[str, Any] = {}
    for metric in TRACKED_METRICS:
        val_before = before.get(metric)
        val_after = after.get(metric)
        if val_before is not None and val_after is not None:
            try:
                b = float(val_before)
                a = float(val_after)
                absolute = a - b
                pct = ((a - b) / b * 100) if b != 0 else 0
                deltas[metric] = {
                    "before": round(b, 2),
                    "after": round(a, 2),
                    "absolute_change": round(absolute, 2),
                    "percent_change": round(pct, 2),
                }
            except (ValueError, TypeError):
                pass
    return deltas


def compute_outcome_rating(delta_json: Dict[str, Any]) -> str:
    if not delta_json:
        return "neutral"

    positive_signals = 0
    negative_signals = 0

    positive_metrics = {"mrr", "cash_balance", "runway_months", "growth_rate", "headcount", "customers"}
    negative_metrics = {"monthly_burn", "churn_rate"}

    for metric, data in delta_json.items():
        if not isinstance(data, dict):
            continue
        pct = data.get("percent_change", 0)
        if metric in positive_metrics:
            if pct > 2:
                positive_signals += 1
            elif pct < -2:
                negative_signals += 1
        elif metric in negative_metrics:
            if pct < -2:
                positive_signals += 1
            elif pct > 2:
                negative_signals += 1

    if positive_signals > negative_signals and positive_signals >= 2:
        return "positive"
    elif negative_signals > positive_signals and negative_signals >= 2:
        return "negative"
    return "neutral"


def snapshot_metrics_at_decision(db: Session, company_id: int, decision_id) -> Dict[str, Any]:
    from server.models.company_decision import CompanyDecision

    decision = db.query(CompanyDecision).filter(
        CompanyDecision.id == decision_id,
        CompanyDecision.company_id == company_id,
    ).first()

    if not decision:
        logger.warning(f"Decision {decision_id} not found for company {company_id}")
        return {}

    snapshot = _get_metrics_snapshot(db, company_id)
    decision.metrics_snapshot_at_decision = snapshot
    decision.implemented_at = datetime.utcnow()

    logger.info(f"Metrics snapshot captured for decision {decision_id} at implementation")
    return snapshot


def record_followup_outcome(db: Session, company_id: int, decision_id) -> Optional[Dict[str, Any]]:
    from server.models.company_decision import CompanyDecision

    decision = db.query(CompanyDecision).filter(
        CompanyDecision.id == decision_id,
        CompanyDecision.company_id == company_id,
    ).first()

    if not decision:
        logger.warning(f"Decision {decision_id} not found for company {company_id}")
        return None

    if not decision.metrics_snapshot_at_decision:
        logger.warning(f"Decision {decision_id} has no initial snapshot, cannot record followup")
        return None

    if decision.outcome_recorded_at:
        logger.info(f"Decision {decision_id} already has outcome recorded")
        return decision.outcome_delta_json

    followup_snapshot = _get_metrics_snapshot(db, company_id)
    deltas = _compute_deltas(decision.metrics_snapshot_at_decision, followup_snapshot)
    rating = compute_outcome_rating(deltas)

    decision.metrics_snapshot_at_followup = followup_snapshot
    decision.outcome_delta_json = deltas
    decision.outcome_rating = rating
    decision.outcome_recorded_at = datetime.utcnow()

    db.commit()

    from server.events.event_store import emit_event
    emit_event(
        company_id=company_id,
        user_id=None,
        event_type="decision_outcome_recorded",
        aggregate_type="decision",
        payload={
            "decision_id": str(decision_id),
            "outcome_rating": rating,
            "deltas_summary": {k: v.get("percent_change", 0) for k, v in deltas.items() if isinstance(v, dict)},
        },
    )

    logger.info(f"Followup outcome recorded for decision {decision_id}: rating={rating}")
    return deltas


def check_pending_followups(company_id: int) -> List[str]:
    recorded = []
    try:
        with SessionLocal() as db:
            from server.models.company_decision import CompanyDecision

            now = datetime.utcnow()
            decisions = (
                db.query(CompanyDecision)
                .filter(
                    CompanyDecision.company_id == company_id,
                    CompanyDecision.status == "implemented",
                    CompanyDecision.metrics_snapshot_at_decision.isnot(None),
                    CompanyDecision.outcome_recorded_at.is_(None),
                    CompanyDecision.implemented_at.isnot(None),
                )
                .all()
            )

            for decision in decisions:
                followup_days = decision.followup_days or 60
                if decision.implemented_at:
                    deadline = decision.implemented_at + timedelta(days=followup_days)
                    if now >= deadline:
                        result = record_followup_outcome(db, company_id, decision.id)
                        if result is not None:
                            recorded.append(str(decision.id))

    except Exception as e:
        logger.error(f"Error checking pending followups for company {company_id}: {e}")

    return recorded
