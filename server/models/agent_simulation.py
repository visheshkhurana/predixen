"""
AgentSimulationRun Model — stores results of agent-based simulations.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from datetime import datetime
from server.core.db import Base


class AgentSimulationRun(Base):
    __tablename__ = "agent_simulation_runs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    scenario_json = Column(Text, nullable=True)
    num_rounds = Column(Integer, default=24)
    seed = Column(Integer, nullable=True)

    survival_probability = Column(Float, nullable=True)
    funding_probability = Column(Float, nullable=True)
    final_cash = Column(Float, nullable=True)
    final_runway = Column(Float, nullable=True)

    results_json = Column(Text, nullable=False)
    events_json = Column(Text, nullable=True)
    memory_json = Column(Text, nullable=True)

    status = Column(String(20), default="completed")
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    share_token = Column(String(64), nullable=True, unique=True, index=True)

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "companyId": self.company_id,
            "numRounds": self.num_rounds,
            "survivalProbability": self.survival_probability,
            "fundingProbability": self.funding_probability,
            "finalCash": self.final_cash,
            "finalRunway": self.final_runway,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "shareToken": self.share_token,
        }
