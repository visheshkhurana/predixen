from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base

class CustomerRecord(Base):
    __tablename__ = "customer_records"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    customer_id = Column(String, nullable=False)
    segment = Column(String, nullable=True)
    signup_date = Column(Date, nullable=True)
    region = Column(String, nullable=True)
    plan = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="customer_records")
