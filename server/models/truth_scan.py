from sqlalchemy import Column, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base

class TruthScan(Base):
    __tablename__ = "truth_scans"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    outputs_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="truth_scans")
