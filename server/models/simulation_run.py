from sqlalchemy import Column, Integer, DateTime, ForeignKey, JSON
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
    
    scenario = relationship("Scenario", back_populates="simulation_runs")
    decisions = relationship("Decision", back_populates="simulation_run")
