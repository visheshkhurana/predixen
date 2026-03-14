"""
AI Governance Layer — Budgets, rate limits, logging, and approval gates.

Prevents runaway AI behavior by enforcing per-agent budgets, daily request limits,
and requiring human approval for high-risk actions.
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import text
from server.core.db import SessionLocal

logger = logging.getLogger(__name__)

DEFAULT_AGENT_PERMISSIONS = {
    "router": {"allowed_actions": ["classify", "dispatch", "aggregate"], "max_daily_requests": 1000, "requires_human_approval": False},
    "cfo_agent": {"allowed_actions": ["analyze_financials", "forecast", "benchmark"], "max_daily_requests": 200, "requires_human_approval": False},
    "market_agent": {"allowed_actions": ["research", "benchmark", "analyze_trends"], "max_daily_requests": 200, "requires_human_approval": False},
    "strategy_agent": {"allowed_actions": ["plan", "recommend", "evaluate"], "max_daily_requests": 200, "requires_human_approval": False},
    "operations_agent": {"allowed_actions": ["execute_plan", "optimize", "schedule"], "max_daily_requests": 100, "requires_human_approval": False},
    "review_agent": {"allowed_actions": ["validate", "reflect", "score"], "max_daily_requests": 200, "requires_human_approval": False},
    "simulation_agent": {"allowed_actions": ["run_monte_carlo", "stress_test", "what_if"], "max_daily_requests": 100, "requires_human_approval": False},
    "autopilot": {"allowed_actions": ["read_twin", "detect_risks", "generate_briefing"], "max_daily_requests": 10, "requires_human_approval": True},
    "doc_generator": {"allowed_actions": ["generate_document", "format", "export"], "max_daily_requests": 50, "requires_human_approval": False},
}


def ensure_agent_permissions() -> None:
    try:
        with SessionLocal() as db:
            for agent, perms in DEFAULT_AGENT_PERMISSIONS.items():
                db.execute(
                    text("""
                        INSERT INTO ai_agent_permissions (agent_name, allowed_actions, max_daily_requests, requires_human_approval)
                        VALUES (:name, :actions, :max_req, :approval)
                        ON CONFLICT (agent_name) DO NOTHING
                    """),
                    {
                        "name": agent,
                        "actions": json.dumps(perms["allowed_actions"]),
                        "max_req": perms["max_daily_requests"],
                        "approval": perms["requires_human_approval"],
                    },
                )
            db.commit()
        logger.info(f"Ensured {len(DEFAULT_AGENT_PERMISSIONS)} agent permissions")
    except Exception as e:
        logger.warning(f"Could not seed agent permissions: {e}")


def check_permission(agent_name: str, action: str) -> dict:
    result = {"allowed": True, "reason": None, "requires_approval": False}
    try:
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT allowed_actions, max_daily_requests, requires_human_approval FROM ai_agent_permissions WHERE agent_name = :name"),
                {"name": agent_name},
            ).fetchone()

            if not row:
                result["allowed"] = True
                return result

            allowed_actions = json.loads(row[0]) if row[0] else []
            max_daily = row[1] or 1000
            requires_approval = bool(row[2])

            if allowed_actions and action not in allowed_actions:
                result["allowed"] = False
                result["reason"] = f"Action '{action}' not in allowed list for {agent_name}"
                return result

            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            count = db.execute(
                text("SELECT COUNT(*) FROM ai_agent_logs WHERE agent_name = :name AND timestamp >= :start"),
                {"name": agent_name, "start": today_start},
            ).scalar() or 0

            if count >= max_daily:
                result["allowed"] = False
                result["reason"] = f"Daily limit ({max_daily}) reached for {agent_name}"
                return result

            result["requires_approval"] = requires_approval
            return result
    except Exception as e:
        logger.error(f"Permission check failed for {agent_name}: {e}")
        return result


def log_agent_activity(
    agent_name: str,
    task: str,
    input_data: Optional[dict] = None,
    output_data: Optional[dict] = None,
    cost: float = 0.0,
    company_id: Optional[int] = None,
) -> Optional[int]:
    try:
        with SessionLocal() as db:
            result = db.execute(
                text("""
                    INSERT INTO ai_agent_logs (agent_name, task, input_json, output_json, cost, timestamp, company_id)
                    VALUES (:name, :task, :input, :output, :cost, :ts, :cid)
                    RETURNING id
                """),
                {
                    "name": agent_name,
                    "task": task,
                    "input": json.dumps(input_data, default=str) if input_data else None,
                    "output": json.dumps(output_data, default=str) if output_data else None,
                    "cost": cost,
                    "ts": datetime.now(timezone.utc),
                    "cid": company_id,
                },
            )
            log_id = result.scalar()
            db.commit()
            return log_id
    except Exception as e:
        logger.error(f"Failed to log agent activity for {agent_name}: {e}")
        return None


def check_budget(company_id: int, agent_name: str, estimated_cost: float = 0.0) -> dict:
    result = {"within_budget": True, "remaining": None, "usage": 0.0, "budget": None}
    try:
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT monthly_budget, usage FROM ai_agent_budgets WHERE company_id = :cid AND agent_name = :name"),
                {"cid": company_id, "name": agent_name},
            ).fetchone()

            if not row:
                return result

            budget = float(row[0])
            usage = float(row[1])
            result["budget"] = budget
            result["usage"] = usage
            result["remaining"] = budget - usage

            if usage + estimated_cost > budget:
                result["within_budget"] = False

            return result
    except Exception as e:
        logger.error(f"Budget check failed: {e}")
        return result


def update_budget_usage(company_id: int, agent_name: str, cost: float) -> None:
    try:
        with SessionLocal() as db:
            db.execute(
                text("""
                    INSERT INTO ai_agent_budgets (company_id, agent_name, monthly_budget, usage)
                    VALUES (:cid, :name, 100.0, :cost)
                    ON CONFLICT (company_id, agent_name)
                    DO UPDATE SET usage = ai_agent_budgets.usage + :cost
                """),
                {"cid": company_id, "name": agent_name, "cost": cost},
            )
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update budget: {e}")


def get_agent_stats(company_id: Optional[int] = None, days: int = 7) -> dict:
    try:
        with SessionLocal() as db:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            params: dict = {"since": since}
            company_filter = ""
            if company_id:
                company_filter = " AND company_id = :cid"
                params["cid"] = company_id

            rows = db.execute(
                text(f"""
                    SELECT agent_name, COUNT(*) as requests, COALESCE(SUM(cost), 0) as total_cost
                    FROM ai_agent_logs
                    WHERE timestamp >= :since{company_filter}
                    GROUP BY agent_name
                    ORDER BY requests DESC
                """),
                params,
            ).fetchall()

            total = db.execute(
                text(f"SELECT COUNT(*) FROM ai_agent_logs WHERE timestamp >= :since{company_filter}"),
                params,
            ).scalar() or 0

            return {
                "total_requests": total,
                "period_days": days,
                "agents": [
                    {"agent_name": r[0], "requests": r[1], "total_cost": float(r[2])}
                    for r in rows
                ],
            }
    except Exception as e:
        logger.error(f"Failed to get agent stats: {e}")
        return {"total_requests": 0, "period_days": days, "agents": []}


def get_all_permissions() -> list[dict]:
    try:
        with SessionLocal() as db:
            rows = db.execute(
                text("SELECT agent_name, allowed_actions, max_daily_requests, requires_human_approval FROM ai_agent_permissions ORDER BY agent_name")
            ).fetchall()
            return [
                {
                    "agent_name": r[0],
                    "allowed_actions": json.loads(r[1]) if r[1] else [],
                    "max_daily_requests": r[2],
                    "requires_human_approval": bool(r[3]),
                }
                for r in rows
            ]
    except Exception:
        return []
