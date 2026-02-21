from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base
import enum


class SimulationJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimulationJob(Base):
    __tablename__ = "simulation_jobs"

    id = Column(String, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False, index=True)
    status = Column(String, default=SimulationJobStatus.PENDING.value)
    progress = Column(Float, default=0)

    config_json = Column(JSON, nullable=False, default={
        "iterations": 1000,
        "horizon_months": 24,
        "confidence_intervals": [10, 25, 50, 75, 90]
    })

    results_json = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    seed = Column(Integer, nullable=True)
    
    scenario = relationship("Scenario")


class ScenarioVersion(Base):
    __tablename__ = "scenario_versions"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    inputs_json = Column(JSON, nullable=False)
    events_json = Column(JSON, default=list)
    tags = Column(JSON, default=list)

    change_notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    scenario = relationship("Scenario")


class SensitivityAnalysis(Base):
    __tablename__ = "sensitivity_analyses"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("simulation_jobs.id"), nullable=True, index=True)
    
    target_metric = Column(String, nullable=False, default="runway")
    parameters_json = Column(JSON, nullable=False)
    results_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    execution_time_ms = Column(Integer, nullable=True)
    
    scenario = relationship("Scenario")
