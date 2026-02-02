from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from datetime import datetime
from server.core.db import Base


class EmailEvent(Base):
    __tablename__ = "email_events"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(String, unique=True, index=True, nullable=False)
    to_email = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    classification = Column(String, nullable=True)
    events_json = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
