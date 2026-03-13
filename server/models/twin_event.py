"""
TwinEvent model — tracks all state changes in the Digital Twin.
Every financial update, connector sync, manual entry, decision, or simulation
generates an event that feeds the twin's continuous state model.
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from server.core.db import Base


class TwinEvent(Base):
    __tablename__ = "twin_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    source = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_twin_events_company_type", "company_id", "event_type"),
        Index("ix_twin_events_created", "created_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "event_type": self.event_type,
            "source": self.source,
            "payload": self.payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
