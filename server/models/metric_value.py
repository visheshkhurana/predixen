"""
MetricValue model for storing computed metric values with full lineage.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index, JSON
from sqlalchemy.sql import func
from server.core.db import Base


class MetricValue(Base):
    """
    Stores computed metric values for each period with full lineage tracking.
    """
    __tablename__ = "metric_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_id = Column(Integer, ForeignKey("metric_definitions.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    value = Column(Float, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    computed_at = Column(DateTime, server_default=func.now(), nullable=False)
    metric_version = Column(Integer, default=1)
    
    raw_event_count = Column(Integer, default=0)
    contributing_connectors = Column(JSON, nullable=True)
    
    source_versions = Column(JSON, nullable=True)
    
    compiled_sql = Column(String(2000), nullable=True)

    __table_args__ = (
        Index("ix_metric_values_metric_period", "metric_id", "period_start"),
        Index("ix_metric_values_company_period", "company_id", "period_start"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "metric_id": self.metric_id,
            "company_id": self.company_id,
            "value": self.value,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
            "metric_version": self.metric_version,
            "raw_event_count": self.raw_event_count,
            "contributing_connectors": self.contributing_connectors,
            "source_versions": self.source_versions,
        }
