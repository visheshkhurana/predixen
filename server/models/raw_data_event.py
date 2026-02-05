"""
RawDataEvent model for storing raw data from connectors.
All connector data flows through this table before metric computation.
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from server.core.db import Base


class RawDataEvent(Base):
    """
    Stores raw data events from connectors.
    This is the source of truth for all metric computations.
    """
    __tablename__ = "raw_data_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    connector_id = Column(String(255), nullable=False, index=True)
    source = Column(String(255), nullable=False)
    payload = Column(JSON, nullable=False)
    occurred_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_raw_data_events_company_connector", "company_id", "connector_id"),
        Index("ix_raw_data_events_occurred_at", "occurred_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "connector_id": self.connector_id,
            "source": self.source,
            "payload": self.payload,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
