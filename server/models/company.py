from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    stage = Column(String, nullable=True)
    currency = Column(String, default="USD")
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="companies")
    datasets = relationship("Dataset", back_populates="company")
    financial_records = relationship("FinancialRecord", back_populates="company")
    transaction_records = relationship("TransactionRecord", back_populates="company")
    customer_records = relationship("CustomerRecord", back_populates="company")
    truth_scans = relationship("TruthScan", back_populates="company")
    scenarios = relationship("Scenario", back_populates="company")
    chat_sessions = relationship("ChatSession", back_populates="company")
    import_sessions = relationship("ImportSession", back_populates="company")
    metric_points = relationship("FinancialMetricPoint", back_populates="company")
    subscriptions = relationship("Subscription", back_populates="company")
    notifications = relationship("Notification", back_populates="company")
    company_decisions = relationship("CompanyDecision", back_populates="company")
    company_scenarios = relationship("CompanyScenario", back_populates="company")
    company_sources = relationship("CompanySource", back_populates="company")
    company_workstreams = relationship("CompanyWorkstream", back_populates="company")
    company_alerts = relationship("CompanyAlert", back_populates="company")
    company_driver_models = relationship("CompanyDriverModel", back_populates="company")
