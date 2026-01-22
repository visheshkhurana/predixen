from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from server.core.db import Base


class CompanySource(Base):
    """Source citations for facts and claims (PDF, web, manual)."""
    __tablename__ = "company_sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    kind = Column(String, nullable=False)
    title = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    doc_id = Column(Text, nullable=True)
    page = Column(Integer, nullable=True)
    table_id = Column(Text, nullable=True)
    row_ref = Column(Text, nullable=True)
    cell_ref = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="company_sources")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "kind": self.kind,
            "title": self.title,
            "url": self.url,
            "doc_id": self.doc_id,
            "page": self.page,
            "table_id": self.table_id,
            "row_ref": self.row_ref,
            "cell_ref": self.cell_ref,
            "snippet": self.snippet,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def get_label(self) -> str:
        """Generate a human-readable label for the citation."""
        if self.kind == "pdf":
            parts = ["PDF"]
            if self.page:
                parts.append(f"p{self.page}")
            if self.table_id:
                parts.append(self.table_id)
            return " ".join(parts)
        elif self.kind == "web":
            return f"Web: {self.title or self.url or 'Source'}"
        else:
            return f"Manual: {self.title or 'Entry'}"


class CompanyWorkstream(Base):
    """Operating cadence workstreams (weekly metrics, monthly board, etc.)."""
    __tablename__ = "company_workstreams"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    cadence = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
    config_json = Column(JSONB, nullable=True, default=dict)
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = relationship("Company", back_populates="company_workstreams")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "name": self.name,
            "cadence": self.cadence,
            "enabled": self.enabled,
            "config": self.config_json or {},
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class CompanyAlert(Base):
    """Alerts and reminders triggered by metrics."""
    __tablename__ = "company_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    type = Column(String, nullable=False)
    severity = Column(String, default="medium")
    message = Column(Text, nullable=True)
    rule_json = Column(JSONB, nullable=True, default=dict)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    status = Column(String, default="open")
    
    company = relationship("Company", back_populates="company_alerts")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "type": self.type,
            "severity": self.severity,
            "message": self.message,
            "rule": self.rule_json or {},
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "status": self.status
        }


class CompanyDriverModel(Base):
    """Driver-based forecasting models."""
    __tablename__ = "company_driver_models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    model_name = Column(String, nullable=False)
    template = Column(String, nullable=False)
    drivers_json = Column(JSONB, nullable=True, default=dict)
    assumptions_json = Column(JSONB, nullable=True, default=dict)
    outputs_json = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = relationship("Company", back_populates="company_driver_models")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "model_name": self.model_name,
            "template": self.template,
            "drivers": self.drivers_json or {},
            "assumptions": self.assumptions_json or {},
            "outputs": self.outputs_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


DRIVER_TEMPLATES = {
    "saas": {
        "name": "SaaS Revenue Model",
        "drivers": {
            "new_customers_per_month": {"label": "New Customers/Month", "type": "number", "default": 10},
            "arpa": {"label": "ARPA ($/month)", "type": "number", "default": 100},
            "churn_pct": {"label": "Monthly Churn %", "type": "number", "default": 3}
        },
        "description": "Subscription-based revenue model with customer acquisition and churn"
    },
    "marketplace": {
        "name": "Marketplace/GMV Model",
        "drivers": {
            "gmv": {"label": "Monthly GMV", "type": "number", "default": 100000},
            "take_rate": {"label": "Take Rate %", "type": "number", "default": 15},
            "contribution_margin_pct": {"label": "Contribution Margin %", "type": "number", "default": 50}
        },
        "description": "GMV-based model with take rate and contribution margin"
    },
    "services": {
        "name": "Services Revenue Model",
        "drivers": {
            "billable_headcount": {"label": "Billable Headcount", "type": "number", "default": 10},
            "utilization_pct": {"label": "Utilization %", "type": "number", "default": 75},
            "blended_rate": {"label": "Blended Rate ($/hr)", "type": "number", "default": 150}
        },
        "description": "Headcount-based services revenue model"
    }
}
