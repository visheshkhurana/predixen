"""
SQLAlchemy models for lead-gen tables.

Place at: server/models/lead_gen.py
(Matches the schema defined in shared/lead-gen-schema.ts + migrations/0001_lead_gen.sql)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from server.core.database import Base  # existing declarative base


class LeadCampaign(Base):
    __tablename__ = "lead_campaigns"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)

    target_segment = Column(JSONB, nullable=False, default=dict)
    n8n_workflow_id = Column(String(80), nullable=True)
    n8n_webhook_path = Column(String(200), nullable=True)

    cadence_days = Column(JSONB, nullable=False, default=lambda: [0, 2, 5, 9])
    goal_metric = Column(String(40), nullable=False, default="trial_signup")
    status = Column(String(20), nullable=False, default="draft")

    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    events = relationship("LeadEvent", back_populates="campaign")


class LeadEvent(Base):
    __tablename__ = "lead_events"
    __table_args__ = (
        Index("lead_events_lead_idx", "lead_id"),
        Index("lead_events_kind_idx", "kind"),
        Index("lead_events_created_idx", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("lead_campaigns.id", ondelete="SET NULL"), nullable=True)

    kind = Column(String(40), nullable=False)
    email_subject = Column(Text, nullable=True)
    email_body_preview = Column(Text, nullable=True)
    gmail_thread_id = Column(String(64), nullable=True)
    gmail_message_id = Column(String(64), nullable=True)
    reply_category = Column(String(40), nullable=True)
    metadata = Column(JSONB, nullable=False, default=dict)
    source_system = Column(String(40), nullable=False, default="n8n")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    lead = relationship("Lead", backref="events")
    campaign = relationship("LeadCampaign", back_populates="events")


class LeadTemplate(Base):
    __tablename__ = "lead_templates"

    id = Column(Integer, primary_key=True)
    key = Column(String(80), unique=True, nullable=False)
    label = Column(String(120), nullable=False)
    category = Column(String(40), nullable=False)
    system_prompt = Column(Text, nullable=False)
    sample_subject = Column(String(200), nullable=True)
    sample_body = Column(Text, nullable=True)
    model = Column(String(60), nullable=True, default="gpt-4o-mini")
    is_active = Column(Boolean, nullable=False, default=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class LeadGenSettings(Base):
    __tablename__ = "lead_gen_settings"

    id = Column(Integer, primary_key=True)  # always 1
    n8n_base_url = Column(String(255), nullable=True)
    n8n_api_key_encrypted = Column(Text, nullable=True)
    outbound_webhook_url = Column(String(255), nullable=True)
    activation_webhook_url = Column(String(255), nullable=True)
    sending_domain = Column(String(120), nullable=True)
    daily_send_limit = Column(Integer, nullable=False, default=30)
    is_enabled = Column(Boolean, nullable=False, default=False)
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
