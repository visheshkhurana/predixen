from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base

class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, default="viewer")  # owner, admin, editor, viewer
    status = Column(String, default="active")  # active, pending, suspended
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    invited_at = Column(DateTime, default=datetime.utcnow)
    joined_at = Column(DateTime, nullable=True)
    
    company = relationship("Company", backref="workspace_members")
    user = relationship("User", foreign_keys=[user_id], backref="workspace_memberships")
    inviter = relationship("User", foreign_keys=[invited_by])


class WorkspaceInvite(Base):
    __tablename__ = "workspace_invites"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    email = Column(String, nullable=False)
    role = Column(String, default="viewer")
    status = Column(String, default="pending")  # pending, accepted, expired, revoked
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    invited_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    token = Column(String, unique=True, nullable=False)
    
    company = relationship("Company", backref="invites")
    inviter = relationship("User")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    email_enabled = Column(Boolean, default=True)
    email_address = Column(String, nullable=True)
    alert_types = Column(JSON, default=dict)
    thresholds = Column(JSON, default=dict)
    frequency = Column(String, default="immediate")  # immediate, daily, weekly
    monthly_digest = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", backref="notification_preferences")


class AlertNotification(Base):
    __tablename__ = "alert_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    alert_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    severity = Column(String, default="warning")  # info, warning, critical
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    
    user = relationship("User")
    company = relationship("Company")
