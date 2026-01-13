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


class ScenarioComment(Base):
    __tablename__ = "scenario_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    scenario = relationship("Scenario", back_populates="comments")
    user = relationship("User")
