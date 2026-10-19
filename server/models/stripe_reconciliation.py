"""Verified Stripe events that could not be attached to a user.

checkout.session.completed returns 500 until the user can be resolved so
Stripe retries. This table keeps one row per event for the retries that
eventually stop, and for an operator to attach the payment by hand.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from server.core.db import Base


class StripeReconciliationEvent(Base):
    __tablename__ = "stripe_reconciliation_events"

    id = Column(Integer, primary_key=True, index=True)
    stripe_event_id = Column(String, unique=True, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    stripe_object_id = Column(String, nullable=True)
    customer_id = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    payload_json = Column(Text, nullable=False)
    reason = Column(String, nullable=False, default="unresolved_user")
    status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
