from sqlalchemy import Column, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base

class Decision(Base):
    __tablename__ = "decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    simulation_run_id = Column(Integer, ForeignKey("simulation_runs.id"), nullable=False)
    recommended_actions_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    simulation_run = relationship("SimulationRun", back_populates="decisions")
