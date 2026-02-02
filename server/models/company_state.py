"""
CompanyState Model - Canonical single source of truth for company financial data.

This model stores the latest published actuals for a company with a snapshot hash
for deterministic simulation snapshotting and provenance tracking.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base
import hashlib
import json


def stable_stringify(obj: dict) -> str:
    """Create a stable JSON string with sorted keys for consistent hashing."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


def compute_snapshot_id(state_json: dict) -> str:
    """Compute a SHA256 hash of the state JSON for snapshotting."""
    stable_json = stable_stringify(state_json)
    return hashlib.sha256(stable_json.encode('utf-8')).hexdigest()[:16]


class CompanyState(Base):
    """
    Canonical company state - single source of truth for all modules.
    
    Every simulation run references the snapshot_id at the time of execution
    to ensure reproducibility and provenance tracking.
    """
    __tablename__ = "company_states"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, unique=True, index=True)
    environment = Column(String(20), nullable=False, default="user")
    
    state_json = Column(Text, nullable=False)
    snapshot_id = Column(String(64), nullable=False, index=True)
    fundraising_rounds_json = Column(Text, nullable=True, default="[]")
    
    cash_balance = Column(Integer, nullable=True)
    monthly_burn = Column(Integer, nullable=True)
    revenue_monthly = Column(Integer, nullable=True)
    revenue_growth_rate = Column(String(20), nullable=True)
    expenses_monthly = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_company_state_updated', 'updated_at'),
        Index('idx_company_state_snapshot', 'snapshot_id'),
    )
    
    @classmethod
    def from_financials(cls, company_id: int, financials: dict, environment: str = "user"):
        """Create a CompanyState from raw financials data."""
        state_json = financials
        snapshot_id = compute_snapshot_id(state_json)
        
        return cls(
            company_id=company_id,
            environment=environment,
            state_json=json.dumps(state_json),
            snapshot_id=snapshot_id,
            cash_balance=financials.get("cashBalance") or financials.get("cash_balance"),
            monthly_burn=financials.get("monthlyBurn") or financials.get("monthly_burn"),
            revenue_monthly=financials.get("revenueMonthly") or financials.get("revenue_monthly"),
            revenue_growth_rate=str(financials.get("revenueGrowthRate") or financials.get("revenue_growth_rate") or "0"),
            expenses_monthly=financials.get("expensesMonthly") or financials.get("expenses_monthly"),
        )
    
    def update_from_financials(self, financials: dict):
        """Update the state from new financials data."""
        self.state_json = json.dumps(financials)
        self.snapshot_id = compute_snapshot_id(financials)
        self.cash_balance = financials.get("cashBalance") or financials.get("cash_balance")
        self.monthly_burn = financials.get("monthlyBurn") or financials.get("monthly_burn")
        self.revenue_monthly = financials.get("revenueMonthly") or financials.get("revenue_monthly")
        self.revenue_growth_rate = str(financials.get("revenueGrowthRate") or financials.get("revenue_growth_rate") or "0")
        self.expenses_monthly = financials.get("expensesMonthly") or financials.get("expenses_monthly")
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to API response format."""
        updated_at_val = self.updated_at
        growth_rate_val = self.revenue_growth_rate
        state_json_val = self.state_json
        fundraising_val = self.fundraising_rounds_json
        
        return {
            "companyId": self.company_id,
            "environment": self.environment,
            "snapshotId": self.snapshot_id,
            "updatedAt": updated_at_val.isoformat() if updated_at_val else None,
            "financials": {
                "cashBalance": self.cash_balance,
                "monthlyBurn": self.monthly_burn,
                "revenueMonthly": self.revenue_monthly,
                "revenueGrowthRate": float(growth_rate_val) if growth_rate_val else 0,
                "expensesMonthly": self.expenses_monthly,
            },
            "fundraisingRounds": json.loads(str(fundraising_val)) if fundraising_val else [],
            "stateJson": json.loads(str(state_json_val)) if state_json_val else {},
        }
