"""
Agent Memory System — per-agent memory for simulation context.

Short-term memory lives in-memory during simulation.
Long-term memory persists to Postgres after simulation completes.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentMemoryStore:
    def __init__(self):
        self._store: Dict[str, List[Dict[str, Any]]] = {}

    def record(self, agent_type: str, month: int, key: str, value: Any):
        if agent_type not in self._store:
            self._store[agent_type] = []
        self._store[agent_type].append({
            "month": month,
            "key": key,
            "value": value,
            "recorded_at": datetime.utcnow().isoformat(),
        })

    def recall(self, agent_type: str, key: str, last_n: int = 1) -> List[Any]:
        if agent_type not in self._store:
            return []
        matches = [m["value"] for m in self._store[agent_type] if m["key"] == key]
        return matches[-last_n:] if matches else []

    def recall_latest(self, agent_type: str, key: str) -> Optional[Any]:
        results = self.recall(agent_type, key, 1)
        return results[0] if results else None

    def get_agent_history(self, agent_type: str) -> List[Dict[str, Any]]:
        return self._store.get(agent_type, [])

    def get_all_memories(self) -> Dict[str, List[Dict[str, Any]]]:
        return self._store

    def to_serializable(self) -> Dict[str, Any]:
        return {k: v for k, v in self._store.items()}


def persist_simulation_memory(db, simulation_id: int, memory_store: AgentMemoryStore):
    from server.models.agent_simulation import AgentSimulationRun
    try:
        run = db.query(AgentSimulationRun).filter(AgentSimulationRun.id == simulation_id).first()
        if run:
            existing = json.loads(run.memory_json) if run.memory_json else {}
            existing.update(memory_store.to_serializable())
            run.memory_json = json.dumps(existing)
            db.commit()
    except Exception as e:
        logger.error(f"Failed to persist memory for simulation {simulation_id}: {e}")
        db.rollback()
