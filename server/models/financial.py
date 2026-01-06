from sqlalchemy import Column, Integer, Float, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base

class FinancialRecord(Base):
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
    
    company = relationship("Company", back_populates="financial_records")
