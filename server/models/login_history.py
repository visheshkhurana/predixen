from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base


class LoginHistory(Base):
    """Track all login attempts for audit and security."""
    __tablename__ = "login_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_type = Column(String(50), nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    success = Column(Boolean, default=True)
    failure_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="login_history")


class Notification(Base):
    """Global notifications for admin dashboard."""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    type = Column(String(50), nullable=False)
    severity = Column(String(20), default="info")
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="notifications")
    company = relationship("Company", back_populates="notifications")
