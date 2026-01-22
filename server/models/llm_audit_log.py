"""LLM Audit Log model for tracking all OpenAI API calls."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from server.core.db import Base


class PIIMode(enum.Enum):
    off = "off"
    standard = "standard"
    strict = "strict"


class LLMAuditLog(Base):
    __tablename__ = "llm_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    endpoint = Column(Text, nullable=False)
    model = Column(Text, nullable=False)
    pii_mode = Column(String(20), default="standard")
    prompt_hash = Column(String(64), nullable=False)
    input_chars_original = Column(Integer, nullable=False)
    input_chars_redacted = Column(Integer, nullable=False)
    pii_findings_json = Column(JSON, nullable=True)
    redacted_prompt_preview = Column(Text, nullable=True)
    redacted_output_preview = Column(Text, nullable=True)
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "user_id": self.user_id,
            "endpoint": self.endpoint,
            "model": self.model,
            "pii_mode": self.pii_mode,
            "prompt_hash": self.prompt_hash,
            "input_chars_original": self.input_chars_original,
            "input_chars_redacted": self.input_chars_redacted,
            "pii_findings_json": self.pii_findings_json,
            "redacted_prompt_preview": self.redacted_prompt_preview,
            "redacted_output_preview": self.redacted_output_preview,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
