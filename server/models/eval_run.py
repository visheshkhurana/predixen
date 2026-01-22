"""Eval Run model for tracking evaluation results."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

from server.core.db import Base


class EvalRun(Base):
    __tablename__ = "eval_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suite_name = Column(String(255), nullable=False)
    inputs_json = Column(JSON, nullable=True)
    outputs_json = Column(JSON, nullable=True)
    scores_json = Column(JSON, nullable=True)
    overall_score = Column(Float, nullable=True)
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "suite_name": self.suite_name,
            "inputs_json": self.inputs_json,
            "outputs_json": self.outputs_json,
            "scores_json": self.scores_json,
            "overall_score": self.overall_score,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
