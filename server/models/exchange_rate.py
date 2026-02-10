from sqlalchemy import Column, Integer, String, Float, DateTime, Date, UniqueConstraint
from datetime import datetime
from server.core.db import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint('base_currency', 'quote_currency', 'rate_date', name='uq_exchange_rate'),
    )

    id = Column(Integer, primary_key=True, index=True)
    base_currency = Column(String(3), nullable=False, index=True)
    quote_currency = Column(String(3), nullable=False, index=True)
    rate = Column(Float, nullable=False)
    rate_date = Column(Date, nullable=False, index=True)
    source = Column(String(50), default="ecb")
    fetched_at = Column(DateTime, default=datetime.utcnow)
