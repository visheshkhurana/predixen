from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from server.core.db import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class CompanyDecision(Base):
    __tablename__ = "company_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    context = Column(Text, nullable=True)
    options_json = Column(JSONType, nullable=True, default=list)
    recommendation_json = Column(JSONType, nullable=True, default=dict)
    status = Column(String, default="proposed")
    owner = Column(String, nullable=True)
    tags = Column(JSONType, nullable=True, default=list)
    confidence = Column(String, default="medium")
    sources_json = Column(JSONType, nullable=True, default=list)
    created_from_message_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    metrics_snapshot_at_decision = Column(JSONType, nullable=True)
    metrics_snapshot_at_followup = Column(JSONType, nullable=True)
    outcome_recorded_at = Column(DateTime, nullable=True)
    outcome_delta_json = Column(JSONType, nullable=True)
    outcome_rating = Column(String(20), nullable=True)
    followup_days = Column(Integer, default=60)

    __table_args__ = (
        CheckConstraint(
            "outcome_rating IS NULL OR outcome_rating IN ('positive', 'neutral', 'negative')",
            name="ck_outcome_rating_values"
        ),
        CheckConstraint(
            "followup_days IS NULL OR (followup_days >= 7 AND followup_days <= 365)",
            name="ck_followup_days_range"
        ),
    )
    implemented_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="company_decisions")

    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "title": self.title,
            "context": self.context,
            "options": self.options_json or [],
            "recommendation": self.recommendation_json or {},
            "status": self.status,
            "owner": self.owner,
            "tags": self.tags or [],
            "confidence": self.confidence,
            "sources": self.sources_json or [],
            "created_from_message_id": str(self.created_from_message_id) if self.created_from_message_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metrics_snapshot_at_decision": self.metrics_snapshot_at_decision,
            "metrics_snapshot_at_followup": self.metrics_snapshot_at_followup,
            "outcome_recorded_at": self.outcome_recorded_at.isoformat() if self.outcome_recorded_at else None,
            "outcome_delta_json": self.outcome_delta_json,
            "outcome_rating": self.outcome_rating,
            "followup_days": self.followup_days or 60,
            "implemented_at": self.implemented_at.isoformat() if self.implemented_at else None,
        }


class CompanyScenario(Base):
    __tablename__ = "company_scenarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    base_scenario_id = Column(UUID(as_uuid=True), ForeignKey("company_scenarios.id"), nullable=True, index=True)
    assumptions_json = Column(JSONType, nullable=True, default=dict)
    outputs_json = Column(JSONType, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = relationship("Company", back_populates="company_scenarios")
    base_scenario = relationship("CompanyScenario", remote_side=[id], backref="forks")
    
    def to_dict(self):
        outputs = self.outputs_json or {}
        has_simulation = bool(outputs and (outputs.get('runway') or outputs.get('survival') or outputs.get('summary')))
        latest_sim = None
        if has_simulation:
            latest_sim = {
                "runway": outputs.get('runway'),
                "survival": outputs.get('survival'),
                "summary": outputs.get('summary'),
            }
        assumptions = self.assumptions_json or {}
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "name": self.name,
            "base_scenario_id": str(self.base_scenario_id) if self.base_scenario_id else None,
            "assumptions": assumptions,
            "outputs": outputs,
            "latest_simulation": latest_sim,
            "tags": assumptions.get('tags', []),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
