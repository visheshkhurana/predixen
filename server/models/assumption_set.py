"""
Database model for Assumption Sets.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from server.core.db import Base


class AssumptionSetModel(Base):
    """Database model for storing assumption sets."""
    __tablename__ = "assumption_sets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    template_id = Column(String(100), nullable=True, index=True)

    assumptions_json = Column(JSON, nullable=False)

    cache_hash = Column(String(64), nullable=True, index=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    company = relationship("Company", back_populates="assumption_sets")


class SimulationCache(Base):
    """Cache for simulation results to avoid recomputing identical scenarios."""
    __tablename__ = "simulation_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(64), unique=True, nullable=False, index=True)
    assumption_set_id = Column(Integer, ForeignKey("assumption_sets.id"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    
    config_json = Column(JSON, nullable=True)
    results_json = Column(JSON, nullable=False)
    
    iterations = Column(Integer, default=1000)
    horizon_months = Column(Integer, default=24)
    
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)
    hit_count = Column(Integer, default=0)
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        from datetime import datetime
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
