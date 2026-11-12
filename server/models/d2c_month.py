"""One month of D2C operating inputs per company (see server/core/d2c.py).

Different sources fill different fields: Shopify knows orders, sales and COD
share; a shipping partner knows RTO and freight; the founder types COGS and
ad spend. One row per company-month holds them all, and `field_sources`
records which source set each field, so a manual entry is never overwritten
by the next sync.
"""

from datetime import datetime

from sqlalchemy import JSON, Column, Date, DateTime, Float, ForeignKey, Integer, UniqueConstraint

from server.core.db import Base


class D2CMonth(Base):
    __tablename__ = "d2c_months"
    __table_args__ = (UniqueConstraint("company_id", "period", name="uq_d2c_month_company_period"),)

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    period = Column(Date, nullable=False)  # first day of the month

    orders_shipped = Column(Integer, nullable=True)
    gross_sales = Column(Float, nullable=True)
    discounts = Column(Float, nullable=True)
    rto_orders = Column(Integer, nullable=True)
    customer_returns_value = Column(Float, nullable=True)
    customer_returns_orders = Column(Integer, nullable=True)
    cogs = Column(Float, nullable=True)
    forward_shipping_per_order = Column(Float, nullable=True)
    rto_shipping_per_order = Column(Float, nullable=True)
    packaging_per_order = Column(Float, nullable=True)
    return_shipping_per_order = Column(Float, nullable=True)
    cod_share = Column(Float, nullable=True)
    payment_gateway_pct = Column(Float, nullable=True)
    cod_fee_per_order = Column(Float, nullable=True)
    marketing_spend = Column(Float, nullable=True)
    new_customers = Column(Integer, nullable=True)

    field_sources = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
