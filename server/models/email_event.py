from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from datetime import datetime
from server.core.db import Base


class EmailEvent(Base):
    __tablename__ = "email_events"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(String, unique=True, index=True, nullable=False)
    to_email = Column(String, nullable=True, index=True)
    subject = Column(String, nullable=True)
    from_email = Column(String, nullable=True)
    recipient_id = Column(String, nullable=True, index=True)
    campaign = Column(String, nullable=True, index=True)
    
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    bounced_at = Column(DateTime, nullable=True)
    complained_at = Column(DateTime, nullable=True)
    
    open_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    clicked_urls = Column(JSON, default=list)
    
    classification = Column(String, nullable=True)
    is_bot_open = Column(Boolean, default=False)
    
    utm_source = Column(String, nullable=True)
    utm_medium = Column(String, nullable=True)
    utm_campaign = Column(String, nullable=True)
    utm_content = Column(String, nullable=True)
    utm_term = Column(String, nullable=True)
    
    events_json = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmailLinkClick(Base):
    __tablename__ = "email_link_clicks"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(String, index=True, nullable=True)
    tracking_id = Column(String, unique=True, index=True, nullable=False)
    recipient_email = Column(String, nullable=True, index=True)
    recipient_id = Column(String, nullable=True)
    destination_url = Column(String, nullable=False)
    link_label = Column(String, nullable=True)
    clicked = Column(Boolean, default=False)
    click_count = Column(Integer, default=0)
    first_clicked_at = Column(DateTime, nullable=True)
    last_clicked_at = Column(DateTime, nullable=True)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailFeedback(Base):
    __tablename__ = "email_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(String, index=True, nullable=True)
    recipient_email = Column(String, nullable=True, index=True)
    rating = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    campaign = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
