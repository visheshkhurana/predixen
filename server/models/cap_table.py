from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Date, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from server.core.db import Base

JSONType = JSONB


class ShareClass(str, enum.Enum):
    COMMON = "common"
    PREFERRED = "preferred"


class GrantType(str, enum.Enum):
    ISO = "iso"
    NSO = "nso"
    RSA = "rsa"
    RSU = "rsu"


class GrantStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXERCISED = "exercised"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class VestingType(str, enum.Enum):
    STANDARD_4Y_1Y_CLIFF = "4y_1y_cliff"
    MONTHLY_NO_CLIFF = "monthly_no_cliff"
    CUSTOM = "custom"


class TransactionType(str, enum.Enum):
    ISSUANCE = "issuance"
    TRANSFER = "transfer"
    EXERCISE = "exercise"
    CANCELLATION = "cancellation"
    CONVERSION = "conversion"
    REPURCHASE = "repurchase"


class Shareholder(Base):
    __tablename__ = "shareholders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    type = Column(String, nullable=False, default="founder")
    relationship_type = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    equity_holdings = relationship("EquityHolding", back_populates="shareholder")
    option_grants = relationship("OptionGrant", back_populates="shareholder")
    transactions_from = relationship("EquityTransaction", foreign_keys="EquityTransaction.from_shareholder_id", back_populates="from_shareholder")
    transactions_to = relationship("EquityTransaction", foreign_keys="EquityTransaction.to_shareholder_id", back_populates="to_shareholder")

    __table_args__ = (
        Index("ix_shareholders_company_name", "company_id", "name"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "name": self.name,
            "email": self.email,
            "type": self.type,
            "relationship_type": self.relationship_type,
            "notes": self.notes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EquityHolding(Base):
    __tablename__ = "equity_holdings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    shareholder_id = Column(UUID(as_uuid=True), ForeignKey("shareholders.id"), nullable=False, index=True)
    share_class = Column(String, nullable=False, default=ShareClass.COMMON.value)
    series = Column(String, nullable=True)
    shares = Column(Float, nullable=False, default=0)
    price_per_share = Column(Float, nullable=True)
    issue_date = Column(Date, nullable=True)
    board_approval_date = Column(Date, nullable=True)
    certificate_number = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shareholder = relationship("Shareholder", back_populates="equity_holdings")

    __table_args__ = (
        Index("ix_equity_holdings_company_shareholder", "company_id", "shareholder_id"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "shareholder_id": str(self.shareholder_id),
            "shareholder_name": self.shareholder.name if self.shareholder else None,
            "share_class": self.share_class,
            "series": self.series,
            "shares": self.shares,
            "price_per_share": self.price_per_share,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "board_approval_date": self.board_approval_date.isoformat() if self.board_approval_date else None,
            "certificate_number": self.certificate_number,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OptionGrant(Base):
    __tablename__ = "option_grants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    shareholder_id = Column(UUID(as_uuid=True), ForeignKey("shareholders.id"), nullable=False, index=True)
    grant_type = Column(String, nullable=False, default=GrantType.ISO.value)
    shares_granted = Column(Float, nullable=False, default=0)
    exercise_price = Column(Float, nullable=False, default=0)
    grant_date = Column(Date, nullable=True)
    expiration_date = Column(Date, nullable=True)
    vesting_type = Column(String, nullable=False, default=VestingType.STANDARD_4Y_1Y_CLIFF.value)
    vesting_start_date = Column(Date, nullable=True)
    cliff_months = Column(Integer, default=12)
    vesting_months = Column(Integer, default=48)
    shares_vested = Column(Float, default=0)
    shares_exercised = Column(Float, default=0)
    status = Column(String, default=GrantStatus.ACTIVE.value)
    board_approval_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shareholder = relationship("Shareholder", back_populates="option_grants")

    __table_args__ = (
        Index("ix_option_grants_company_shareholder", "company_id", "shareholder_id"),
    )

    def to_dict(self):
        unvested = max(0, self.shares_granted - self.shares_vested - self.shares_exercised)
        exercisable = max(0, self.shares_vested - self.shares_exercised)
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "shareholder_id": str(self.shareholder_id),
            "shareholder_name": self.shareholder.name if self.shareholder else None,
            "grant_type": self.grant_type,
            "shares_granted": self.shares_granted,
            "exercise_price": self.exercise_price,
            "grant_date": self.grant_date.isoformat() if self.grant_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "vesting_type": self.vesting_type,
            "vesting_start_date": self.vesting_start_date.isoformat() if self.vesting_start_date else None,
            "cliff_months": self.cliff_months,
            "vesting_months": self.vesting_months,
            "shares_vested": self.shares_vested,
            "shares_exercised": self.shares_exercised,
            "shares_unvested": unvested,
            "shares_exercisable": exercisable,
            "status": self.status,
            "board_approval_date": self.board_approval_date.isoformat() if self.board_approval_date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EquityTransaction(Base):
    __tablename__ = "equity_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    transaction_type = Column(String, nullable=False)
    from_shareholder_id = Column(UUID(as_uuid=True), ForeignKey("shareholders.id"), nullable=True)
    to_shareholder_id = Column(UUID(as_uuid=True), ForeignKey("shareholders.id"), nullable=True)
    share_class = Column(String, nullable=True)
    series = Column(String, nullable=True)
    shares = Column(Float, nullable=False, default=0)
    price_per_share = Column(Float, nullable=True)
    total_value = Column(Float, nullable=True)
    grant_id = Column(UUID(as_uuid=True), ForeignKey("option_grants.id"), nullable=True)
    holding_id = Column(UUID(as_uuid=True), ForeignKey("equity_holdings.id"), nullable=True)
    round_id = Column(UUID(as_uuid=True), ForeignKey("fundraising_rounds.id"), nullable=True)
    board_approval_date = Column(Date, nullable=True)
    effective_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    from_shareholder = relationship("Shareholder", foreign_keys=[from_shareholder_id], back_populates="transactions_from")
    to_shareholder = relationship("Shareholder", foreign_keys=[to_shareholder_id], back_populates="transactions_to")

    __table_args__ = (
        Index("ix_equity_transactions_company", "company_id", "created_at"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "transaction_type": self.transaction_type,
            "from_shareholder_id": str(self.from_shareholder_id) if self.from_shareholder_id else None,
            "from_shareholder_name": self.from_shareholder.name if self.from_shareholder else None,
            "to_shareholder_id": str(self.to_shareholder_id) if self.to_shareholder_id else None,
            "to_shareholder_name": self.to_shareholder.name if self.to_shareholder else None,
            "share_class": self.share_class,
            "series": self.series,
            "shares": self.shares,
            "price_per_share": self.price_per_share,
            "total_value": self.total_value,
            "grant_id": str(self.grant_id) if self.grant_id else None,
            "holding_id": str(self.holding_id) if self.holding_id else None,
            "round_id": str(self.round_id) if self.round_id else None,
            "board_approval_date": self.board_approval_date.isoformat() if self.board_approval_date else None,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Valuation409A(Base):
    __tablename__ = "valuations_409a"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    valuation_date = Column(Date, nullable=False)
    fair_market_value = Column(Float, nullable=False)
    price_per_share = Column(Float, nullable=False)
    methodology = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    expiration_date = Column(Date, nullable=True)
    status = Column(String, default="active")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": self.company_id,
            "valuation_date": self.valuation_date.isoformat() if self.valuation_date else None,
            "fair_market_value": self.fair_market_value,
            "price_per_share": self.price_per_share,
            "methodology": self.methodology,
            "provider": self.provider,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
