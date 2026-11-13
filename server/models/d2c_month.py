"""One month of D2C operating inputs per company (see server/core/d2c.py).

Different sources fill different fields: Shopify knows orders, sales and COD
share; a shipping partner knows RTO and freight; the founder types COGS and
ad spend. One row per company-month holds them all, and `field_sources`
records which source set each field, so a manual entry is never overwritten
by the next sync.
"""

from datetime import datetime

from sqlalchemy import JSON, Column, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint

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


class D2CAdSpend(Base):
    """Ad spend for one month from one ad account of one ad platform.

    Why a child table and not a `meta_spend` column: spend is summed across
    platforms (Meta + Google + ...), each platform can have several accounts,
    and each account has its own currency. One row per (month, source,
    account) means a new platform adds rows, not columns; a re-sync replaces
    that platform's rows for the month, so nothing is counted twice; and an
    account in another currency keeps its native amount instead of being
    mixed into the total. d2c_months.marketing_spend holds the sum (unless the
    founder typed it), so the engine reads one number as before.

    Platform-reported purchases and purchase value live here too. They are
    what the ad platform's attribution claims, not store revenue.
    """

    __tablename__ = "d2c_ad_spend"
    __table_args__ = (
        UniqueConstraint("company_id", "period", "source", "account_id", name="uq_d2c_ad_spend_account_month"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    period = Column(Date, nullable=False)  # first day of the month
    source = Column(String(32), nullable=False)  # connector id, e.g. "meta_ads"
    account_id = Column(String(64), nullable=False)
    account_name = Column(String(255), nullable=True)

    currency = Column(String(3), nullable=True)  # the ad account's currency
    spend = Column(Float, nullable=False, default=0.0)  # in `currency`
    # Spend in the company's currency: equal to `spend` when currencies match,
    # converted when a stored market rate exists, else NULL (shown as a mismatch).
    spend_company = Column(Float, nullable=True)
    fx_rate = Column(Float, nullable=True)
    fx_rate_date = Column(Date, nullable=True)

    impressions = Column(Integer, nullable=True)
    clicks = Column(Integer, nullable=True)
    purchases = Column(Float, nullable=True)  # platform-attributed
    purchase_value = Column(Float, nullable=True)  # platform-attributed, in `currency`

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
