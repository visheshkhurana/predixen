"""CRM pipeline snapshots: one row per (company, CRM, day).

CRM connectors used to hand over only won deals, as revenue; open pipeline,
stages and win rate were computed for the sync response and then dropped.
A snapshot keeps them, and one row per day (a same-day re-sync replaces it)
builds the pipeline trend over time.
"""

from datetime import datetime

from sqlalchemy import JSON, Column, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint

from server.core.db import Base


class CRMPipelineSnapshot(Base):
    __tablename__ = "crm_pipeline_snapshots"
    __table_args__ = (
        UniqueConstraint("company_id", "source", "snapshot_date", name="uq_crm_pipeline_source_day"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    source = Column(String(32), nullable=False)  # connector id, e.g. "hubspot"
    snapshot_date = Column(Date, nullable=False)
    currency = Column(String(3), nullable=True)  # the CRM's main currency

    open_count = Column(Integer, nullable=False, default=0)
    open_value = Column(Float, nullable=False, default=0.0)
    weighted_value = Column(Float, nullable=True)  # open value x stage probability
    won_count_30d = Column(Integer, nullable=False, default=0)
    won_value_30d = Column(Float, nullable=False, default=0.0)
    lost_count_30d = Column(Integer, nullable=False, default=0)
    win_rate_90d = Column(Float, nullable=True)  # won / (won + lost), closed in 90 days
    avg_won_deal_90d = Column(Float, nullable=True)
    deals_read = Column(Integer, nullable=False, default=0)
    truncated = Column(Integer, nullable=False, default=0)  # 1 when the CRM had more deals than read

    stages = Column(JSON, nullable=True)  # [{"stage", "count", "value"}] for open deals
    other_currencies = Column(JSON, nullable=True)  # {"EUR": {"count", "value"}} left out of totals

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
