from __future__ import annotations
"""Software spend: one row per (company, month, source connector, vendor).

Why its own table and not opex: a seat-cost connector (1Password) knows one
vendor's cost, and a card connector (Ramp, Brex) knows only the card share of
software. Either written as opex would read as the company's whole opex for
the month. Kept apart, they add up to a software-spend view without changing
the burn figures. A re-sync replaces that source's rows for the month, so
nothing is counted twice.
"""

from datetime import datetime

from sqlalchemy import JSON, Column, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint

from server.core.db import Base


class SoftwareSpend(Base):
    __tablename__ = "software_spend"
    __table_args__ = (
        UniqueConstraint("company_id", "period", "source", "vendor", name="uq_software_spend_vendor_month"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    period = Column(Date, nullable=False)  # first day of the month
    source = Column(String(32), nullable=False)  # connector id, e.g. "onepassword"
    vendor = Column(String(255), nullable=False)

    currency = Column(String(3), nullable=True)
    amount = Column(Float, nullable=False, default=0.0)  # in `currency`
    # In the company's currency: equal to `amount` when currencies match,
    # converted with a stored market rate when one exists, else NULL.
    amount_company = Column(Float, nullable=True)

    basis = Column(String(16), nullable=False, default="card")  # "card" | "seats"
    transactions = Column(Integer, nullable=True)
    seats = Column(Integer, nullable=True)
    active_users = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
