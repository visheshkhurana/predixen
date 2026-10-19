"""
Lead model — extended for the lead-gen feature.

Schema changes (additive, backward-compatible):
  - Full contact fields: first_name, last_name, linkedin_url, website
  - Segmentation: source, sector, stage, last_funding_event
  - Lifecycle: status, hunter_status, enriched_at
  - Campaign tracking: last_email_at, reply_category, trial_signed_up_at,
    has_simulated, p50_survival
  - Enrichment cache: summary, hook
  - Generic: tags (jsonb), notes, updated_at

Historical columns (email, company, plan, created_at) are preserved as-is
so existing lead-capture code keeps working.
"""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from server.core.db import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, unique=True, index=True)
    company = Column(String, default="")
    plan = Column(String, default="")

    # Identity (new)
    first_name = Column(String(120), nullable=True)
    last_name = Column(String(120), nullable=True)
    linkedin_url = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)

    # Segmentation (new)
    source = Column(String(50), nullable=False, default="manual")
    sector = Column(String(80), nullable=True)
    stage = Column(String(40), nullable=True)
    last_funding_event = Column(Text, nullable=True)

    # Lifecycle (new)
    status = Column(String(40), nullable=False, default="new")
    hunter_status = Column(String(30), nullable=True)

    # Enrichment cache (new)
    summary = Column(Text, nullable=True)
    hook = Column(Text, nullable=True)
    enriched_at = Column(DateTime, nullable=True)

    # Campaign tracking (new)
    last_email_at = Column(DateTime, nullable=True)
    reply_category = Column(String(40), nullable=True)
    trial_signed_up_at = Column(DateTime, nullable=True)
    has_simulated = Column(Boolean, nullable=False, default=False)
    p50_survival = Column(Integer, nullable=True)

    tags = Column(JSONB, nullable=False, default=list)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
