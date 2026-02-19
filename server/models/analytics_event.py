from sqlalchemy import Column, Integer, String, DateTime, JSON
from server.core.db import Base
from datetime import datetime

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    id = Column(Integer, primary_key=True)
    event_name = Column(String, nullable=False)
    user_id = Column(Integer, nullable=True)
    company_id = Column(Integer, nullable=True)
    meta_json = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
