from sqlalchemy import Column, Integer, Float, DateTime, Date, ForeignKey, String, Boolean, Enum, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base
import enum


class SignConvention(str, enum.Enum):
    ACCOUNTING = "accounting"
    ALL_POSITIVE = "all_positive"
    MIXED = "mixed"


class TimeGranularity(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    UNKNOWN = "unknown"


class PeriodMode(str, enum.Enum):
    LATEST = "latest"
    AVG_3MO = "avg_3mo"
    CUSTOM = "custom"


class ImportStatus(str, enum.Enum):
    PARSED = "parsed"
    VERIFIED = "verified"
    SAVED = "saved"
    FAILED = "failed"


class MetricClassification(str, enum.Enum):
    REVENUE = "revenue"
    EXPENSE = "expense"
    DERIVED = "derived"
    HEADER = "header"
    OTHER = "other"


class ExpenseBucket(str, enum.Enum):
    COGS = "cogs"
    MARKETING = "marketing"
    PAYROLL = "payroll"
    OPERATING = "operating"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceType(str, enum.Enum):
    EXCEL = "excel"
    PDF = "pdf"
    MANUAL = "manual"
    BENCHMARK = "benchmark"


class ImportSession(Base):
    """Tracks an import session from file upload through verification to save."""
    __tablename__ = "import_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    source_type = Column(String(20), nullable=False)
    filename = Column(String(255))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    detected_sign_convention = Column(String(20), default="all_positive")
    detected_time_granularity = Column(String(20), default="monthly")
    
    selected_period_mode = Column(String(20), default="latest")
    selected_period = Column(Date, nullable=True)
    
    status = Column(String(20), default="parsed")
    
    warnings = Column(JSON, default=list)
    errors = Column(JSON, default=list)
    
    raw_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = relationship("Company", back_populates="import_sessions")
    metric_points = relationship("FinancialMetricPoint", back_populates="import_session", cascade="all, delete-orphan")


class FinancialMetricPoint(Base):
    """Stores individual financial metric values with classification and normalization tracking."""
    __tablename__ = "financial_metric_points"
    
    id = Column(Integer, primary_key=True, index=True)
    import_session_id = Column(Integer, ForeignKey("import_sessions.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    period = Column(Date, nullable=False)
    
    metric_key = Column(String(50), nullable=False)
    
    value = Column(Float, nullable=False)
    value_raw = Column(Float, nullable=True)
    
    unit = Column(String(10), default="USD")
    
    source_type = Column(String(20), nullable=False)
    source_label = Column(String(255), nullable=True)
    
    confidence = Column(String(20), default="high")
    classification = Column(String(20), nullable=False)
    expense_bucket = Column(String(20), nullable=True)
    
    include_in_totals = Column(Boolean, default=True)
    
    row_index = Column(Integer, nullable=True)
    parent_row_index = Column(Integer, nullable=True)
    
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    import_session = relationship("ImportSession", back_populates="metric_points")
    company = relationship("Company", back_populates="metric_points")


class FinancialRecord(Base):
    """Aggregated financial record for a period (final verified data)."""
    __tablename__ = "financial_records"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    revenue = Column(Float, default=0)
    cogs = Column(Float, default=0)
    opex = Column(Float, default=0)
    payroll = Column(Float, default=0)
    other_costs = Column(Float, default=0)
    cash_balance = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    import_session_id = Column(Integer, ForeignKey("import_sessions.id"), nullable=True)
    
    mrr = Column(Float, nullable=True)
    arr = Column(Float, nullable=True)
    gross_profit = Column(Float, nullable=True)
    gross_margin = Column(Float, nullable=True)
    operating_income = Column(Float, nullable=True)
    operating_margin = Column(Float, nullable=True)
    net_burn = Column(Float, nullable=True)
    burn_multiple = Column(Float, nullable=True)  # Can be negative (e.g., -0.7)
    runway_months = Column(Float, nullable=True)
    
    headcount = Column(Integer, nullable=True)
    customers = Column(Integer, nullable=True)
    
    mom_growth = Column(Float, nullable=True)
    yoy_growth = Column(Float, nullable=True)
    
    ndr = Column(Float, nullable=True)
    ltv = Column(Float, nullable=True)
    cac = Column(Float, nullable=True)
    ltv_cac_ratio = Column(Float, nullable=True)
    arpu = Column(Float, nullable=True)
    
    marketing_expense = Column(Float, nullable=True)
    
    source_type = Column(String(20), nullable=True)
    extraction_summary = Column(Text, nullable=True)
    
    company = relationship("Company", back_populates="financial_records")
