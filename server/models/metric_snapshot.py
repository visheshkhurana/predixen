from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from server.core.db import Base


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    metric_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
