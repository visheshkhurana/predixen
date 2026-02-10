from sqlalchemy import Column, Integer, String, JSON, DateTime, Text
from datetime import datetime
from server.core.db import Base


class SharedScenario(Base):
    __tablename__ = "shared_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    company_id = Column(Integer, nullable=False)
    scenario_name = Column(String, nullable=False)
    scenario_description = Column(Text, nullable=True)
    simulation_data = Column(JSON, nullable=False)
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
