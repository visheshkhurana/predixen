"""
Event Ledger System — Event Sourcing for FounderConsole.

Stores all state changes as immutable events for replay, auditing,
AI training, and workflow triggers.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import text
from server.core.db import SessionLocal

logger = logging.getLogger(__name__)

EVENT_TYPES = [
    "financial_record_added",
    "scenario_created",
    "simulation_completed",
    "decision_created",
    "decision_outcome_recorded",
    "connector_synced",
    "copilot_request",
    "ai_recommendation_generated",
    "alert_triggered",
    "truth_scan_completed",
    "feature_flag_changed",
    "autopilot_run",
    "user_login",
    "company_updated",
]

AGGREGATE_TYPES = [
    "company", "scenario", "decision", "simulation",
    "connector", "copilot", "alert", "user", "system",
]


def emit_event(
    company_id: int,
    user_id: Optional[int],
    event_type: str,
    aggregate_type: str,
    aggregate_id: Optional[int] = None,
    payload: Optional[dict] = None,
    version: int = 1,
) -> Optional[int]:
    try:
        with SessionLocal() as db:
            result = db.execute(
                text("""
                    INSERT INTO events (company_id, user_id, event_type, aggregate_type, aggregate_id, timestamp, version)
                    VALUES (:company_id, :user_id, :event_type, :aggregate_type, :aggregate_id, :timestamp, :version)
                    RETURNING id
                """),
                {
                    "company_id": company_id,
                    "user_id": user_id,
                    "event_type": event_type,
                    "aggregate_type": aggregate_type,
                    "aggregate_id": aggregate_id,
                    "timestamp": datetime.now(timezone.utc),
                    "version": version,
                },
            )
            event_id = result.scalar()

            if payload and event_id:
                db.execute(
                    text("""
                        INSERT INTO event_payloads (event_id, payload_json)
                        VALUES (:event_id, :payload_json)
                    """),
                    {"event_id": event_id, "payload_json": json.dumps(payload, default=str)},
                )

            db.commit()
            logger.debug(f"Event emitted: {event_type} for company {company_id} (id={event_id})")
            return event_id
    except Exception as e:
        logger.error(f"Failed to emit event {event_type}: {e}")
        return None


def get_events(
    company_id: int,
    event_type: Optional[str] = None,
    aggregate_type: Optional[str] = None,
    aggregate_id: Optional[int] = None,
    since_id: Optional[int] = None,
    limit: int = 100,
) -> list[dict]:
    try:
        with SessionLocal() as db:
            query = """
                SELECT e.id, e.company_id, e.user_id, e.event_type,
                       e.aggregate_type, e.aggregate_id, e.timestamp, e.version,
                       ep.payload_json
                FROM events e
                LEFT JOIN event_payloads ep ON ep.event_id = e.id
                WHERE e.company_id = :company_id
            """
            params: dict[str, Any] = {"company_id": company_id, "limit": limit}

            if event_type:
                query += " AND e.event_type = :event_type"
                params["event_type"] = event_type
            if aggregate_type:
                query += " AND e.aggregate_type = :aggregate_type"
                params["aggregate_type"] = aggregate_type
            if aggregate_id:
                query += " AND e.aggregate_id = :aggregate_id"
                params["aggregate_id"] = aggregate_id
            if since_id:
                query += " AND e.id > :since_id"
                params["since_id"] = since_id

            query += " ORDER BY e.id DESC LIMIT :limit"

            rows = db.execute(text(query), params).fetchall()
            return [
                {
                    "id": r[0],
                    "company_id": r[1],
                    "user_id": r[2],
                    "event_type": r[3],
                    "aggregate_type": r[4],
                    "aggregate_id": r[5],
                    "timestamp": r[6].isoformat() if r[6] else None,
                    "version": r[7],
                    "payload": json.loads(r[8]) if r[8] else None,
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get events: {e}")
        return []


def replay_events(
    company_id: int,
    aggregate_type: str,
    aggregate_id: Optional[int] = None,
) -> list[dict]:
    return get_events(
        company_id=company_id,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        limit=10000,
    )


def subscribe_consumer(consumer_name: str) -> Optional[int]:
    try:
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT last_event_id FROM event_consumers WHERE consumer_name = :name"),
                {"name": consumer_name},
            ).fetchone()
            return row[0] if row else 0
    except Exception:
        return 0


def update_consumer_position(consumer_name: str, last_event_id: int) -> None:
    try:
        with SessionLocal() as db:
            db.execute(
                text("""
                    INSERT INTO event_consumers (consumer_name, last_event_id)
                    VALUES (:name, :last_event_id)
                    ON CONFLICT (consumer_name) DO UPDATE SET last_event_id = :last_event_id
                """),
                {"name": consumer_name, "last_event_id": last_event_id},
            )
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update consumer {consumer_name}: {e}")


def save_projection(projection_name: str, state: dict) -> None:
    try:
        with SessionLocal() as db:
            db.execute(
                text("""
                    INSERT INTO event_projections (projection_name, state_json)
                    VALUES (:name, :state)
                    ON CONFLICT (projection_name) DO UPDATE SET state_json = :state
                """),
                {"name": projection_name, "state": json.dumps(state, default=str)},
            )
            db.commit()
    except Exception as e:
        logger.error(f"Failed to save projection {projection_name}: {e}")


def get_projection(projection_name: str) -> Optional[dict]:
    try:
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT state_json FROM event_projections WHERE projection_name = :name"),
                {"name": projection_name},
            ).fetchone()
            return json.loads(row[0]) if row else None
    except Exception:
        return None


def get_event_stats(company_id: int) -> dict:
    try:
        with SessionLocal() as db:
            rows = db.execute(
                text("""
                    SELECT event_type, COUNT(*) as count
                    FROM events
                    WHERE company_id = :company_id
                    GROUP BY event_type
                    ORDER BY count DESC
                """),
                {"company_id": company_id},
            ).fetchall()
            total = db.execute(
                text("SELECT COUNT(*) FROM events WHERE company_id = :company_id"),
                {"company_id": company_id},
            ).scalar() or 0
            return {
                "total_events": total,
                "by_type": {r[0]: r[1] for r in rows},
            }
    except Exception as e:
        logger.error(f"Failed to get event stats: {e}")
        return {"total_events": 0, "by_type": {}}
