from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from datetime import datetime
from server.core.db import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class CopilotFeedback(Base):
    __tablename__ = "copilot_feedback"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(String(100), nullable=True, index=True)
    message_index = Column(Integer, nullable=True)
    rating = Column(String(20), nullable=False)
    feedback_text = Column(Text, nullable=True)
    context_snapshot_json = Column(JSONType, nullable=True)
    response_type = Column(String(50), nullable=True, index=True)
    tags = Column(JSONType, nullable=True, default=list)
    message_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "message_index": self.message_index,
            "rating": self.rating,
            "feedback_text": self.feedback_text,
            "context_snapshot_json": self.context_snapshot_json,
            "response_type": self.response_type,
            "tags": self.tags or [],
            "message_id": self.message_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
