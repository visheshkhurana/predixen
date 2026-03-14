"""
Founder Autopilot Service — Daily automated risk detection and briefing generation.

Autopilot loop:
1. Read Digital Twin state
2. Detect risks (runway, churn, burn vs growth)
3. Run simulations for detected risks
4. Generate decisions / recommendations
5. Notify founder via CEO briefing
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import text
from server.core.db import SessionLocal

logger = logging.getLogger(__name__)

AUTOPILOT_RULES = [
    {
        "id": "low_runway",
        "name": "Low Runway Alert",
        "condition": lambda state: state.get("runway_months", 999) < 12,
        "action": "simulate_hiring_slowdown",
        "severity": "critical",
        "description": "Runway below 12 months — simulate hiring slowdown",
    },
    {
        "id": "churn_spike",
        "name": "Churn Spike Detection",
        "condition": lambda state: state.get("churn_rate", 0) > 0.08,
        "action": "simulate_pricing_change",
        "severity": "high",
        "description": "Churn rate above 8% — simulate pricing adjustments",
    },
    {
        "id": "burn_exceeds_growth",
        "name": "Burn vs Growth Imbalance",
        "condition": lambda state: (
            state.get("monthly_burn", 0) > 0
            and state.get("mrr", 0) > 0
            and state.get("monthly_burn", 0) > state.get("mrr", 0) * 1.5
        ),
        "action": "simulate_cost_reduction",
        "severity": "high",
        "description": "Burn exceeds 1.5x revenue — simulate cost reduction",
    },
    {
        "id": "declining_mrr",
        "name": "MRR Decline",
        "condition": lambda state: state.get("mrr_growth_rate", 0) < -0.05,
        "action": "simulate_growth_initiatives",
        "severity": "high",
        "description": "MRR declining more than 5% — simulate growth initiatives",
    },
    {
        "id": "high_cac",
        "name": "High CAC Alert",
        "condition": lambda state: (
            state.get("cac", 0) > 0
            and state.get("ltv", 0) > 0
            and state.get("ltv", 0) / state.get("cac", 1) < 3
        ),
        "action": "simulate_channel_optimization",
        "severity": "medium",
        "description": "LTV/CAC ratio below 3 — simulate channel optimization",
    },
]


def get_company_twin_state(company_id: int) -> dict:
    try:
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT state_json, cash_balance, monthly_burn, revenue_monthly FROM company_states WHERE company_id = :cid"),
                {"cid": company_id},
            ).fetchone()
            if not row:
                return {}

            state = json.loads(row[0]) if row[0] else {}
            state.setdefault("cash_balance", row[1] or 0)
            state.setdefault("monthly_burn", row[2] or 0)
            state.setdefault("mrr", row[3] or 0)

            if state.get("cash_balance") and state.get("monthly_burn") and state["monthly_burn"] > 0:
                state.setdefault("runway_months", state["cash_balance"] / state["monthly_burn"])

            return state
    except Exception as e:
        logger.error(f"Failed to get twin state for company {company_id}: {e}")
        return {}


def detect_risks(company_id: int) -> list[dict]:
    state = get_company_twin_state(company_id)
    if not state:
        return []

    triggered = []
    for rule in AUTOPILOT_RULES:
        try:
            if rule["condition"](state):
                triggered.append({
                    "rule_id": rule["id"],
                    "name": rule["name"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "action": rule["action"],
                    "current_state": {
                        k: state.get(k)
                        for k in ["runway_months", "churn_rate", "monthly_burn", "mrr", "cac", "ltv", "mrr_growth_rate"]
                        if state.get(k) is not None
                    },
                })
        except Exception as e:
            logger.debug(f"Rule {rule['id']} check failed: {e}")

    return triggered


def generate_briefing(company_id: int) -> dict:
    state = get_company_twin_state(company_id)
    risks = detect_risks(company_id)

    briefing = {
        "company_id": company_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": _build_summary(state, risks),
        "risks": risks,
        "risk_count": len(risks),
        "critical_count": sum(1 for r in risks if r["severity"] == "critical"),
        "high_count": sum(1 for r in risks if r["severity"] == "high"),
        "medium_count": sum(1 for r in risks if r["severity"] == "medium"),
        "state_snapshot": {
            "mrr": state.get("mrr", 0),
            "monthly_burn": state.get("monthly_burn", 0),
            "cash_balance": state.get("cash_balance", 0),
            "runway_months": round(state.get("runway_months", 0), 1) if state.get("runway_months") else None,
            "churn_rate": state.get("churn_rate"),
        },
        "suggestions": _generate_suggestions(risks, state),
    }

    _save_briefing(company_id, briefing)
    return briefing


def _build_summary(state: dict, risks: list[dict]) -> str:
    if not state:
        return "No company data available for briefing."

    parts = []
    mrr = state.get("mrr", 0)
    burn = state.get("monthly_burn", 0)
    runway = state.get("runway_months")

    if mrr:
        parts.append(f"MRR: ${mrr:,.0f}")
    if burn:
        parts.append(f"Monthly Burn: ${burn:,.0f}")
    if runway:
        parts.append(f"Runway: {runway:.0f} months")

    summary = "Current state: " + ", ".join(parts) if parts else "Limited data available"

    if risks:
        critical = [r for r in risks if r["severity"] == "critical"]
        high = [r for r in risks if r["severity"] == "high"]
        if critical:
            summary += f". CRITICAL: {len(critical)} issue(s) requiring immediate attention"
        if high:
            summary += f". {len(high)} high-priority risk(s) detected"
    else:
        summary += ". No immediate risks detected — company metrics are within healthy ranges."

    return summary


def _generate_suggestions(risks: list[dict], state: dict) -> list[dict]:
    suggestions = []

    action_map = {
        "simulate_hiring_slowdown": {
            "title": "Reduce Hiring Pace",
            "description": "Slow down hiring to extend runway. Consider freezing non-critical roles and focusing on revenue-generating positions.",
            "impact": "Could extend runway by 3-6 months",
        },
        "simulate_pricing_change": {
            "title": "Review Pricing Strategy",
            "description": "High churn may indicate pricing misalignment. Consider value-based pricing tiers or annual contract incentives.",
            "impact": "Could reduce churn by 2-4% and increase ARPU",
        },
        "simulate_cost_reduction": {
            "title": "Optimize Cost Structure",
            "description": "Burn rate significantly exceeds revenue growth. Identify and cut non-essential spend.",
            "impact": "Could improve burn multiple and extend runway",
        },
        "simulate_growth_initiatives": {
            "title": "Accelerate Growth",
            "description": "Revenue is declining. Double down on best-performing channels and consider product-led growth.",
            "impact": "Could reverse MRR decline within 2-3 months",
        },
        "simulate_channel_optimization": {
            "title": "Improve Unit Economics",
            "description": "CAC is too high relative to LTV. Optimize acquisition channels and improve onboarding.",
            "impact": "Could improve LTV/CAC ratio to 3x+",
        },
    }

    for risk in risks:
        action = risk.get("action", "")
        if action in action_map:
            suggestion = action_map[action].copy()
            suggestion["severity"] = risk["severity"]
            suggestion["triggered_by"] = risk["rule_id"]
            suggestions.append(suggestion)

    return suggestions


def _save_briefing(company_id: int, briefing: dict) -> None:
    try:
        with SessionLocal() as db:
            db.execute(
                text("""
                    INSERT INTO autopilot_runs (company_id, briefing_json, risk_count, created_at)
                    VALUES (:cid, :briefing, :risk_count, :created_at)
                """),
                {
                    "cid": company_id,
                    "briefing": json.dumps(briefing, default=str),
                    "risk_count": briefing["risk_count"],
                    "created_at": datetime.now(timezone.utc),
                },
            )
            db.commit()
    except Exception as e:
        logger.error(f"Failed to save autopilot briefing: {e}")


def get_latest_briefing(company_id: int) -> Optional[dict]:
    try:
        with SessionLocal() as db:
            row = db.execute(
                text("""
                    SELECT briefing_json, created_at FROM autopilot_runs
                    WHERE company_id = :cid
                    ORDER BY created_at DESC LIMIT 1
                """),
                {"cid": company_id},
            ).fetchone()
            if row:
                briefing = json.loads(row[0])
                briefing["saved_at"] = row[1].isoformat() if row[1] else None
                return briefing
            return None
    except Exception:
        return None


def get_briefing_history(company_id: int, limit: int = 10) -> list[dict]:
    try:
        with SessionLocal() as db:
            rows = db.execute(
                text("""
                    SELECT id, risk_count, created_at FROM autopilot_runs
                    WHERE company_id = :cid
                    ORDER BY created_at DESC LIMIT :limit
                """),
                {"cid": company_id, "limit": limit},
            ).fetchall()
            return [
                {"id": r[0], "risk_count": r[1], "created_at": r[2].isoformat() if r[2] else None}
                for r in rows
            ]
    except Exception:
        return []


def run_autopilot(company_id: int) -> dict:
    from server.events.event_store import emit_event

    briefing = generate_briefing(company_id)

    emit_event(
        company_id=company_id,
        user_id=None,
        event_type="autopilot_run",
        aggregate_type="system",
        payload={"risk_count": briefing["risk_count"], "critical": briefing["critical_count"]},
    )

    return briefing
