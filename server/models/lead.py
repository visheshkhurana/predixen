from sqlalchemy import Column, Integer, String, DateTime
from server.core.db import Base
from datetime import datetime

class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    company = Column(String, default="")
    plan = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
