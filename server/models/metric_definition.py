"""
MetricDefinition model for defining computed metrics with YAML DSL.
Supports versioning, status lifecycle, and full DSL definitions.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Index, Text
from sqlalchemy.sql import func
from server.core.db import Base


class MetricDefinition(Base):
    """
    Defines a metric with its computation formula using YAML DSL.
    Metrics are computed from RawDataEvents using the DSL compiler.
    """
    __tablename__ = "metric_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    key = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    
    definition = Column(Text, nullable=True)
    
    formula = Column(String(500), nullable=True)
    source_connector = Column(String(255), nullable=True)
    
    grain = Column(String(50), default="monthly")
    unit = Column(String(50), nullable=True)
    format_type = Column(String(50), default="number")
    
    version = Column(Integer, default=1)
    status = Column(String(50), default="draft")
    
    is_system = Column(Boolean, default=False)
    
    dependencies = Column(JSON, nullable=True)
    
    config = Column(JSON, nullable=True)
    
    tags = Column(JSON, nullable=True)
    owners = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    published_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_metric_def_company_key", "company_id", "key", unique=True),
        Index("ix_metric_def_status", "status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "definition": self.definition,
            "formula": self.formula,
            "source_connector": self.source_connector,
            "grain": self.grain,
            "unit": self.unit,
            "format_type": self.format_type,
            "version": self.version,
            "status": self.status,
            "is_system": self.is_system,
            "dependencies": self.dependencies,
            "config": self.config,
            "tags": self.tags,
            "owners": self.owners,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
