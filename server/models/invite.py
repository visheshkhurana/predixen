from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from server.core.db import Base
import secrets


def generate_invite_token():
    return secrets.token_urlsafe(32)


class Invite(Base):
    """Track user invitations."""
    __tablename__ = "invites"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, default=generate_invite_token)
    role = Column(String(20), default="viewer")
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    accepted = Column(Boolean, default=False)
    accepted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    invited_by = relationship("User", foreign_keys=[invited_by_id])
    
    @classmethod
    def create_invite(cls, email: str, role: str, invited_by_id: int, expires_days: int = 7):
        return cls(
            email=email,
            role=role,
            invited_by_id=invited_by_id,
            expires_at=datetime.utcnow() + timedelta(days=expires_days)
        )
    
    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self):
        return not self.accepted and not self.is_expired
