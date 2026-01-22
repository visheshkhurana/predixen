from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from server.core.db import Base


class InstrumentType(str, enum.Enum):
    EQUITY = "equity"
    SAFE = "safe"
    NOTE = "note"


class RoundStatus(str, enum.Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    CLOSED = "closed"


class InvestorType(str, enum.Enum):
    VC = "vc"
    PE = "pe"
    ANGEL = "angel"
    STRATEGIC = "strategic"
    FAMILY_OFFICE = "family_office"


class PipelineStage(str, enum.Enum):
    SOURCED = "sourced"
    CONTACTED = "contacted"
    MEETING = "meeting"
    DD = "dd"
    TERM_SHEET = "term_sheet"
    COMMITTED = "committed"
    PASSED = "passed"


class CompanyCapTable(Base):
    __tablename__ = "company_cap_tables"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False, default="Current Cap Table")
    as_of_date = Column(Date, nullable=True)
    currency = Column(String, default="USD")
    cap_table_json = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = relationship("Company", back_populates="cap_tables")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "name": self.name,
            "as_of_date": self.as_of_date.isoformat() if self.as_of_date else None,
            "currency": self.currency,
            "cap_table": self.cap_table_json or {
                "common": [],
                "preferred": [],
                "options": {"pool_percent": 0.0, "allocated_percent": 0.0},
                "notes": [],
                "fully_diluted_shares": 0
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class FundraisingRound(Base):
    __tablename__ = "fundraising_rounds"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    target_raise = Column(Float, nullable=True)
    pre_money = Column(Float, nullable=True)
    post_money = Column(Float, nullable=True)
    instrument = Column(String, default=InstrumentType.EQUITY.value)
    option_pool_refresh_percent = Column(Float, nullable=True)
    use_of_funds_json = Column(JSONB, nullable=True, default=dict)
    status = Column(String, default=RoundStatus.PLANNED.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = relationship("Company", back_populates="fundraising_rounds")
    terms = relationship("RoundTerms", back_populates="round", uselist=False)
    pipeline = relationship("InvestorPipeline", back_populates="round")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "name": self.name,
            "target_raise": self.target_raise,
            "pre_money": self.pre_money,
            "post_money": self.post_money,
            "instrument": self.instrument,
            "option_pool_refresh_percent": self.option_pool_refresh_percent,
            "use_of_funds": self.use_of_funds_json or {},
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class RoundTerms(Base):
    __tablename__ = "round_terms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id = Column(UUID(as_uuid=True), ForeignKey("fundraising_rounds.id"), nullable=False)
    terms_json = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    round = relationship("FundraisingRound", back_populates="terms")
    
    def to_dict(self):
        default_terms = {
            "valuation": {"pre_money": None, "post_money": None},
            "security": "preferred",
            "liquidation_preference": {"multiple": 1.0, "participating": False, "cap": None},
            "dividends": {"rate": 0, "cumulative": False},
            "anti_dilution": "broad_based_weighted_average",
            "pro_rata_rights": {"enabled": True, "threshold": 0.0},
            "board": {"composition": []},
            "protective_provisions": [],
            "option_pool": {"size": 0.0, "refresh": 0.0},
            "vesting": {"founder_reset": False},
            "closing_conditions": [],
            "legal": {"governing_law": "Delaware", "counsel": None, "fees": None}
        }
        return {
            "id": str(self.id),
            "round_id": str(self.round_id),
            "terms": {**default_terms, **(self.terms_json or {})},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Investor(Base):
    __tablename__ = "investors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, default=InvestorType.VC.value)
    geography = Column(String, nullable=True)
    stage_focus = Column(String, nullable=True)
    thesis_tags = Column(JSONB, nullable=True, default=list)
    contact_json = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="investors")
    pipeline_entries = relationship("InvestorPipeline", back_populates="investor")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "name": self.name,
            "type": self.type,
            "geography": self.geography,
            "stage_focus": self.stage_focus,
            "thesis_tags": self.thesis_tags or [],
            "contact": self.contact_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class InvestorPipeline(Base):
    __tablename__ = "investor_pipeline"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id = Column(UUID(as_uuid=True), ForeignKey("fundraising_rounds.id"), nullable=False)
    investor_id = Column(UUID(as_uuid=True), ForeignKey("investors.id"), nullable=False)
    stage = Column(String, default=PipelineStage.SOURCED.value)
    probability = Column(Float, default=0.0)
    last_contacted_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    round = relationship("FundraisingRound", back_populates="pipeline")
    investor = relationship("Investor", back_populates="pipeline_entries")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "round_id": str(self.round_id),
            "investor_id": str(self.investor_id),
            "investor_name": self.investor.name if self.investor else None,
            "stage": self.stage,
            "probability": self.probability,
            "last_contacted_at": self.last_contacted_at.isoformat() if self.last_contacted_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
