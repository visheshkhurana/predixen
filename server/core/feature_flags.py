"""
Feature Flag System — Safe deployment and gradual rollouts.

Supports global flags, company-level overrides, and user-level overrides.
Resolution order: user_flags > company_flags > feature_flags (global).
"""
import logging
from typing import Optional
from sqlalchemy import text
from server.core.db import SessionLocal

logger = logging.getLogger(__name__)

DEFAULT_FLAGS = {
    "copilot_v2": {"description": "Enhanced AI Copilot with parallel agents", "enabled": True},
    "simulation_monte_carlo": {"description": "Monte Carlo simulation engine", "enabled": True},
    "founder_autopilot": {"description": "Automated daily founder briefings", "enabled": False},
    "data_confidence_badges": {"description": "Show confidence scores on metrics", "enabled": False},
    "event_ledger": {"description": "Event sourcing for all state changes", "enabled": True},
    "intelligence_graph_v2": {"description": "Enhanced intelligence graph with adjacency", "enabled": False},
    "ai_governance": {"description": "AI agent budgets and rate limiting", "enabled": True},
    "digital_twin_v2": {"description": "Enhanced digital twin with live updates", "enabled": True},
    "hiring_planner": {"description": "Team planning and salary modeling", "enabled": True},
    "board_deck_export": {"description": "AI-powered board deck generation", "enabled": True},
}


def ensure_default_flags() -> None:
    try:
        with SessionLocal() as db:
            for key, meta in DEFAULT_FLAGS.items():
                db.execute(
                    text("""
                        INSERT INTO feature_flags (key, description, enabled)
                        VALUES (:key, :description, :enabled)
                        ON CONFLICT (key) DO NOTHING
                    """),
                    {"key": key, "description": meta["description"], "enabled": meta["enabled"]},
                )
            db.commit()
        logger.info(f"Ensured {len(DEFAULT_FLAGS)} default feature flags")
    except Exception as e:
        logger.warning(f"Could not seed feature flags: {e}")


def is_feature_enabled(
    flag_key: str,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> bool:
    try:
        with SessionLocal() as db:
            if user_id:
                row = db.execute(
                    text("SELECT enabled FROM user_flags WHERE user_id = :uid AND flag_key = :key"),
                    {"uid": user_id, "key": flag_key},
                ).fetchone()
                if row:
                    return bool(row[0])

            if company_id:
                row = db.execute(
                    text("SELECT enabled FROM company_flags WHERE company_id = :cid AND flag_key = :key"),
                    {"cid": company_id, "key": flag_key},
                ).fetchone()
                if row:
                    return bool(row[0])

            row = db.execute(
                text("SELECT enabled FROM feature_flags WHERE key = :key"),
                {"key": flag_key},
            ).fetchone()
            if row:
                return bool(row[0])

            return False
    except Exception as e:
        logger.error(f"Feature flag check failed for {flag_key}: {e}")
        return flag_key in DEFAULT_FLAGS and DEFAULT_FLAGS[flag_key]["enabled"]


def set_feature_flag(flag_key: str, enabled: bool, description: Optional[str] = None) -> None:
    try:
        with SessionLocal() as db:
            db.execute(
                text("""
                    INSERT INTO feature_flags (key, description, enabled)
                    VALUES (:key, :desc, :enabled)
                    ON CONFLICT (key) DO UPDATE SET enabled = :enabled
                """),
                {"key": flag_key, "desc": description or flag_key, "enabled": enabled},
            )
            db.commit()
    except Exception as e:
        logger.error(f"Failed to set feature flag {flag_key}: {e}")


def set_company_flag(company_id: int, flag_key: str, enabled: bool) -> None:
    try:
        with SessionLocal() as db:
            db.execute(
                text("""
                    INSERT INTO company_flags (company_id, flag_key, enabled)
                    VALUES (:cid, :key, :enabled)
                    ON CONFLICT (company_id, flag_key) DO UPDATE SET enabled = :enabled
                """),
                {"cid": company_id, "key": flag_key, "enabled": enabled},
            )
            db.commit()
    except Exception as e:
        logger.error(f"Failed to set company flag: {e}")


def set_user_flag(user_id: int, flag_key: str, enabled: bool) -> None:
    try:
        with SessionLocal() as db:
            db.execute(
                text("""
                    INSERT INTO user_flags (user_id, flag_key, enabled)
                    VALUES (:uid, :key, :enabled)
                    ON CONFLICT (user_id, flag_key) DO UPDATE SET enabled = :enabled
                """),
                {"uid": user_id, "key": flag_key, "enabled": enabled},
            )
            db.commit()
    except Exception as e:
        logger.error(f"Failed to set user flag: {e}")


def get_all_flags() -> list[dict]:
    try:
        with SessionLocal() as db:
            rows = db.execute(
                text("SELECT key, description, enabled FROM feature_flags ORDER BY key")
            ).fetchall()
            return [{"key": r[0], "description": r[1], "enabled": bool(r[2])} for r in rows]
    except Exception:
        return [{"key": k, "description": v["description"], "enabled": v["enabled"]} for k, v in DEFAULT_FLAGS.items()]


def get_company_flags(company_id: int) -> list[dict]:
    try:
        with SessionLocal() as db:
            rows = db.execute(
                text("""
                    SELECT ff.key, ff.description, 
                           COALESCE(cf.enabled, ff.enabled) as enabled,
                           cf.enabled IS NOT NULL as has_override
                    FROM feature_flags ff
                    LEFT JOIN company_flags cf ON cf.flag_key = ff.key AND cf.company_id = :cid
                    ORDER BY ff.key
                """),
                {"cid": company_id},
            ).fetchall()
            return [
                {"key": r[0], "description": r[1], "enabled": bool(r[2]), "has_override": bool(r[3])}
                for r in rows
            ]
    except Exception:
        return get_all_flags()
