"""Truth Scan validation layer models.

This module defines the data models for the Truth Scan validation gate
that sits between data uploads and simulation runs.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from datetime import datetime
import uuid
import enum
from server.core.db import Base


class SourceKind(str, enum.Enum):
    """Source type for truth scan uploads."""
    IMPORT_SESSION = "import_session"
    DATASET = "dataset"
    MANUAL_BASELINE = "manual_baseline"


class TruthScanStatus(str, enum.Enum):
    """Status flow for truth scan uploads."""
    RECEIVED = "received"
    NORMALIZED = "normalized"
    VALIDATED = "validated"
    NEEDS_USER = "needs_user"
    FINALIZED = "finalized"
    FAILED = "failed"


class IssueSeverity(str, enum.Enum):
    """Severity levels for validation issues."""
    BLOCKED = "blocked"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueCategory(str, enum.Enum):
    """Categories for validation issues."""
    STRUCTURAL = "structural"
    ARITHMETIC = "arithmetic"
    ACCOUNTING = "accounting"
    PLAUSIBILITY = "plausibility"
    COMPLETENESS = "completeness"
    CONFLICT = "conflict"


class IssueStatus(str, enum.Enum):
    """Status for validation issues."""
    OPEN = "open"
    AUTO_FIXED = "auto_fixed"
    USER_NEEDED = "user_needed"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class DecisionAction(str, enum.Enum):
    """Actions logged in decision log."""
    AUTO_FIX_APPLIED = "auto_fix_applied"
    USER_OVERRIDE_APPLIED = "user_override_applied"
    CONFLICT_RESOLVED = "conflict_resolved"
    DATASET_FINALIZED = "dataset_finalized"


class DecisionActor(str, enum.Enum):
    """Actor types for decisions."""
    SYSTEM = "system"
    USER = "user"
    ADMIN = "admin"


def generate_uuid():
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class TruthScanUpload(Base):
    """Represents a Truth Scan run input pointer.
    
    Points to the source of data being validated - either an ImportSession,
    a Dataset, or a manual baseline entry.
    """
    __tablename__ = "truth_scan_uploads"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    source_kind = Column(String(20), nullable=False)
    import_session_id = Column(Integer, ForeignKey("import_sessions.id"), nullable=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True, index=True)
    manual_baseline_payload = Column(JSON, nullable=True)
    
    file_hash_sha256 = Column(String(64), nullable=True, index=True)
    
    status = Column(String(20), default=TruthScanStatus.RECEIVED.value, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = relationship("Company", back_populates="truth_scan_uploads")
    import_session = relationship("ImportSession", back_populates="truth_scan_upload", foreign_keys=[import_session_id])
    dataset = relationship("Dataset", back_populates="truth_scan_upload", foreign_keys=[dataset_id])
    truth_datasets = relationship("TruthDataset", back_populates="source_upload")
    validation_reports = relationship("ValidationReport", back_populates="source_upload")
    decision_logs = relationship("TruthDecisionLog", back_populates="source_upload")


class TruthDataset(Base):
    """Canonical monthly time series with derived metrics and provenance.
    
    This is the "single source of truth" that the simulator reads from.
    """
    __tablename__ = "truth_datasets"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    source_upload_id = Column(String(36), ForeignKey("truth_scan_uploads.id"), nullable=False, index=True)
    
    version = Column(Integer, nullable=False, index=True)
    finalized = Column(Boolean, default=False, index=True)
    is_latest = Column(Boolean, default=False, index=True)
    
    assumptions = Column(JSON, nullable=False, default=dict)
    facts = Column(JSON, nullable=False, default=dict)
    derived = Column(JSON, nullable=False, default=dict)
    coverage = Column(JSON, nullable=False, default=dict)
    confidence_summary = Column(JSON, nullable=False, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="truth_datasets")
    source_upload = relationship("TruthScanUpload", back_populates="truth_datasets")
    validation_reports = relationship("ValidationReport", back_populates="truth_dataset")


class ValidationReport(Base):
    """Summary report of a validation run."""
    __tablename__ = "validation_reports"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    source_upload_id = Column(String(36), ForeignKey("truth_scan_uploads.id"), nullable=False, index=True)
    truth_dataset_id = Column(String(36), ForeignKey("truth_datasets.id"), nullable=False, index=True)
    
    summary = Column(JSON, nullable=False, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="validation_reports")
    source_upload = relationship("TruthScanUpload", back_populates="validation_reports")
    truth_dataset = relationship("TruthDataset", back_populates="validation_reports")
    issues = relationship("ValidationIssue", back_populates="report", cascade="all, delete-orphan")


class ValidationIssue(Base):
    """Individual validation issue with evidence and fix suggestions."""
    __tablename__ = "validation_issues"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("validation_reports.id"), nullable=False, index=True)
    
    severity = Column(String(20), nullable=False)
    category = Column(String(20), nullable=False)
    metric_key = Column(String(50), nullable=True, index=True)
    
    message = Column(String(500), nullable=False)
    evidence = Column(JSON, nullable=False, default=dict)
    suggestion = Column(JSON, nullable=True)
    
    can_autofix = Column(Boolean, default=False)
    autofix_patch = Column(JSON, nullable=True)
    
    status = Column(String(20), default=IssueStatus.OPEN.value, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    report = relationship("ValidationReport", back_populates="issues")
    decision_logs = relationship("TruthDecisionLog", back_populates="issue")


class TruthDecisionLog(Base):
    """Audit trail for all decisions made during Truth Scan."""
    __tablename__ = "truth_decision_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_upload_id = Column(String(36), ForeignKey("truth_scan_uploads.id"), nullable=False, index=True)
    issue_id = Column(String(36), ForeignKey("validation_issues.id"), nullable=True)
    
    action = Column(String(30), nullable=False)
    patch = Column(JSON, nullable=False, default=dict)
    rationale = Column(Text, nullable=True)
    actor = Column(String(10), default=DecisionActor.SYSTEM.value)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    source_upload = relationship("TruthScanUpload", back_populates="decision_logs")
    issue = relationship("ValidationIssue", back_populates="decision_logs")


class TruthScan(Base):
    """Legacy TruthScan model - kept for backward compatibility.
    
    New code should use TruthDataset and ValidationReport instead.
    """
    __tablename__ = "truth_scans"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    outputs_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="truth_scans")
