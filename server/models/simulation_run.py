from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    n_sims = Column(Integer, default=1000)
    seed = Column(Integer, nullable=True)
    outputs_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    data_snapshot_id = Column(String(64), nullable=False, index=True)
    inputs_json = Column(JSON, nullable=True)
    status = Column(String(20), default="completed")
    error_message = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    scenario = relationship("Scenario", back_populates="simulation_runs")
    decisions = relationship("Decision", back_populates="simulation_run")
    
    def to_dict(self) -> dict:
        """Convert to API response format with provenance."""
        return {
            "runId": self.id,
            "scenarioId": self.scenario_id,
            "dataSnapshotId": self.data_snapshot_id,
            "nSims": self.n_sims,
            "seed": self.seed,
            "status": self.status,
            "outputs": self.outputs_json,
            "inputs": self.inputs_json,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "errorMessage": self.error_message,
        }
