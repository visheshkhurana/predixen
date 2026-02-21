"""
Additional models for advanced simulation features.
Note: ScenarioVersion and SensitivityAnalysis already exist in simulation_job.py
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base


class MacroEnvironment(Base):
    """Stores macro-economic environment settings per company."""
    __tablename__ = "macro_environments"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    name = Column(String, nullable=False)
    preset = Column(String, default="neutral")
    
    interest_rate = Column(String, default="0.05")
    inflation_rate = Column(String, default="0.03")
    market_growth_factor = Column(String, default="1.0")
    currency_fx_rate = Column(String, default="1.0")
    credit_availability = Column(String, default="1.0")
    
    is_active = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = relationship("Company")


class SensitivityRun(Base):
    """Stores sensitivity analysis results for a simulation run."""
    __tablename__ = "sensitivity_runs"

    id = Column(Integer, primary_key=True, index=True)
    simulation_cache_id = Column(Integer, ForeignKey("simulation_cache.id"), nullable=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    target_metric = Column(String, nullable=False)
    perturbation_pct = Column(String, default="0.10")
    
    results_json = Column(JSON, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company")
    scenario = relationship("Scenario")


class Recommendation(Base):
    """Stores generated recommendations based on simulation results."""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    simulation_cache_id = Column(Integer, ForeignKey("simulation_cache.id"), nullable=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    recommendation_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    
    impact_json = Column(JSON, nullable=True)
    
    priority = Column(Integer, default=0)
    status = Column(String, default="pending")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company")
    scenario = relationship("Scenario")
