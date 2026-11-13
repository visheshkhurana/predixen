"""Razorpay billing tables.

razorpay_subscriptions maps a Razorpay subscription id to the local user and
to the tier/currency/interval the SERVER chose when it created it. Webhooks
and payment verification resolve the user from this row, never from the
client.

razorpay_webhook_events holds one row per processed webhook event id, so a
redelivered event is acknowledged without being applied twice.

Both are created idempotently at boot (server/main.py) with checkfirst=True.
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String

from server.core.db import Base


class RazorpaySubscription(Base):
    __tablename__ = "razorpay_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    razorpay_subscription_id = Column(String, unique=True, nullable=False, index=True)
    razorpay_customer_id = Column(String, nullable=True, index=True)
    razorpay_plan_id = Column(String, nullable=True)
    plan = Column(String, nullable=False)
    interval = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)  # major units, per interval
    status = Column(String, nullable=False, default="created")
    # created_at (unix seconds) of the newest webhook event applied, so a
    # late, out-of-order delivery cannot roll the state back.
    last_event_at = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RazorpayWebhookEvent(Base):
    __tablename__ = "razorpay_webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    razorpay_subscription_id = Column(String, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
