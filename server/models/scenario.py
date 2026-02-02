from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base

class Scenario(Base):
    __tablename__ = "scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    inputs_json = Column(JSON, nullable=False)
    overrides_json = Column(JSON, default=dict)
    outputs_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(Integer, default=1)
    parent_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True)
    tags = Column(JSON, default=list)
    is_archived = Column(Integer, default=0)
    
    company = relationship("Company", back_populates="scenarios")
    simulation_runs = relationship("SimulationRun", back_populates="scenario")
    parent = relationship("Scenario", remote_side=[id], backref="versions")
    comments = relationship("ScenarioComment", back_populates="scenario", cascade="all, delete-orphan")
    
    def get_overrides(self) -> dict:
        """Get scenario overrides with defaults."""
        return self.overrides_json or {}
    
    def get_latest_run(self):
        """Get the most recent completed simulation run."""
        if not self.simulation_runs:
            return None
        completed = [r for r in self.simulation_runs if r.status == "completed"]
        if not completed:
            return None
        return max(completed, key=lambda r: r.created_at)


class ScenarioComment(Base):
    __tablename__ = "scenario_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    scenario = relationship("Scenario", back_populates="comments")
    user = relationship("User")
