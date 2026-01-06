from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime
from server.core.db import Base

class Benchmark(Base):
    __tablename__ = "benchmarks"
    
    id = Column(Integer, primary_key=True, index=True)
    industry = Column(String, nullable=False)
    stage = Column(String, nullable=False)
    metric_name = Column(String, nullable=False)
    p25 = Column(Float, nullable=False)
    p50 = Column(Float, nullable=False)
    p75 = Column(Float, nullable=False)
    direction = Column(String, default="higher_is_better")
    updated_at = Column(DateTime, default=datetime.utcnow)
