from __future__ import annotations
"""Founder-set goals (targets with an optional deadline) for a company."""
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text

from server.core.db import Base


class CompanyGoal(Base):
    __tablename__ = "company_goals"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    title = Column(String, nullable=False)
    # What the target is measured in: currency (company currency), months,
    # percent, count, or none (a milestone with no number).
    unit = Column(String, nullable=False, default="none")
    target_value = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    deadline = Column(Date, nullable=True)
    # on_track | at_risk | off_track | done
    status = Column(String, nullable=False, default="on_track")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
