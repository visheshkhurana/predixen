from sqlalchemy import Column, Integer, Float, String, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base

class TransactionRecord(Base):
    __tablename__ = "transaction_records"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    txn_date = Column(Date, nullable=False)
    customer_id = Column(String, nullable=True)
    product = Column(String, nullable=True)
    amount = Column(Float, default=0)
    cost = Column(Float, default=0)
    channel = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="transaction_records")
