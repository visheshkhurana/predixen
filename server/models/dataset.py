from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from server.core.db import Base

class DatasetType(str, enum.Enum):
    FINANCIAL = "financial"
    TRANSACTIONS = "transactions"
    CUSTOMERS = "customers"

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    row_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="datasets")
    truth_scan_upload = relationship("TruthScanUpload", back_populates="dataset", foreign_keys="TruthScanUpload.dataset_id")
