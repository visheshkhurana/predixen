"""checkout.session.completed must attach a user or fail closed so Stripe retries."""

from __future__ import annotations

import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api import billing
from server.models.stripe_reconciliation import StripeReconciliationEvent


@pytest.fixture
def webhook(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL)"
        ))
        conn.execute(text("""
            CREATE TABLE subscriptions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                plan VARCHAR,
                status VARCHAR,
                stripe_subscription_id VARCHAR,
                stripe_customer_id VARCHAR,
                current_period_start TIMESTAMP,
                current_period_end TIMESTAMP,
                monthly_price FLOAT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """))
    StripeReconciliationEvent.__table__.create(bind=engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    state = {
        "event": {},
        "subscription": {
            "id": "sub_1",
            "status": "active",
            "customer": "cus_1",
            "metadata": {},
            "items": {"data": []},
        },
        "customer": {},
        "customer_calls": 0,
    }

    monkeypatch.setattr(billing, "SessionLocal", lambda: Session())
    monkeypatch.setattr(billing.stripe_billing, "stripe_enabled", lambda: True)
    monkeypatch.setattr(
        billing.stripe_billing,
        "verify_webhook",
        lambda payload, sig: state["event"],
    )

    import stripe

    def retrieve_subscription(_sub_id):
        return state["subscription"]

    def retrieve_customer(_customer_id):
        state["customer_calls"] += 1
        return state["customer"]

    monkeypatch.setattr(stripe.Subscription, "retrieve", retrieve_subscription)
    monkeypatch.setattr(stripe.Customer, "retrieve", retrieve_customer)

    app = FastAPI()
    app.include_router(billing.router)
    client = TestClient(app)

    def add_user(user_id: int, email: str) -> None:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (id, email) VALUES (:id, :email)"),
                {"id": user_id, "email": email},
            )

    def post():
        return client.post(
            "/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "t=1,v1=test"},
        )

    def subs():
        with engine.connect() as conn:
            return conn.execute(text(
                "SELECT user_id, plan, status, stripe_subscription_id, stripe_customer_id "
                "FROM subscriptions ORDER BY id"
            )).fetchall()

    def recon():
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT stripe_event_id, status, customer_email, reason, payload_json "
                "FROM stripe_reconciliation_events ORDER BY id"
            )).fetchall()
        return rows

    return {
        "engine": engine,
        "state": state,
        "add_user": add_user,
        "post": post,
        "subs": subs,
        "recon": recon,
    }


def _checkout_event(**obj_overrides):
    obj = {
        "id": "cs_1",
        "mode": "subscription",
        "subscription": "sub_1",
        "customer": "cus_1",
        "metadata": {},
        "customer_details": {},
    }
    obj.update(obj_overrides)
    return {
        "id": "evt_1",
        "type": "checkout.session.completed",
        "data": {"object": obj},
    }


def test_subscription_metadata_resolves_without_customer_lookup(webhook):
    webhook["add_user"](7, "founder@example.com")
    webhook["state"]["subscription"]["metadata"] = {"fc_user_id": "7", "fc_plan": "growth"}
    webhook["state"]["event"] = _checkout_event()

    resp = webhook["post"]()

    assert resp.status_code == 200
    assert resp.json() == {"received": True}
    assert webhook["state"]["customer_calls"] == 0
    rows = webhook["subs"]()
    assert len(rows) == 1
    assert rows[0].user_id == 7
    assert rows[0].plan == "growth"
    assert rows[0].stripe_subscription_id == "sub_1"
    assert webhook["recon"]() == []


def test_client_reference_id_resolves(webhook):
    webhook["add_user"](4, "founder@example.com")
    webhook["state"]["subscription"]["metadata"] = {"fc_plan": "starter"}
    webhook["state"]["event"] = _checkout_event(client_reference_id="4")

    resp = webhook["post"]()

    assert resp.status_code == 200
    assert webhook["subs"]()[0].user_id == 4
    assert webhook["state"]["customer_calls"] == 0


def test_session_metadata_resolves(webhook):
    webhook["add_user"](9, "founder@example.com")
    webhook["state"]["event"] = _checkout_event(metadata={"fc_user_id": "9"})

    resp = webhook["post"]()

    assert resp.status_code == 200
    assert webhook["subs"]()[0].user_id == 9
    assert webhook["state"]["customer_calls"] == 0


def test_existing_customer_row_resolves(webhook):
    webhook["add_user"](3, "founder@example.com")
    with webhook["engine"].begin() as conn:
        conn.execute(text(
            "INSERT INTO subscriptions (user_id, stripe_customer_id, plan, status) "
            "VALUES (3, 'cus_1', 'free', 'active')"
        ))
    webhook["state"]["event"] = _checkout_event()

    resp = webhook["post"]()

    assert resp.status_code == 200
    assert webhook["state"]["customer_calls"] == 0
    rows = webhook["subs"]()
    assert len(rows) == 1
    assert rows[0].user_id == 3
    assert rows[0].stripe_subscription_id == "sub_1"


def test_customer_metadata_fallback(webhook):
    webhook["add_user"](11, "founder@example.com")
    webhook["state"]["customer"] = {"id": "cus_1", "metadata": {"fc_user_id": "11"}, "email": None}
    webhook["state"]["event"] = _checkout_event()

    resp = webhook["post"]()

    assert resp.status_code == 200
    assert webhook["state"]["customer_calls"] == 1
    assert webhook["subs"]()[0].user_id == 11


def test_customer_email_fallback_is_case_insensitive(webhook):
    webhook["add_user"](12, "Founder@Example.com")
    webhook["state"]["customer"] = {"id": "cus_1", "metadata": {}, "email": "founder@example.com"}
    webhook["state"]["event"] = _checkout_event()

    resp = webhook["post"]()

    assert resp.status_code == 200
    assert webhook["subs"]()[0].user_id == 12


def test_session_email_fallback_when_customer_has_no_email(webhook):
    webhook["add_user"](13, "ada@example.com")
    webhook["state"]["customer"] = {"id": "cus_1", "metadata": {}, "email": None}
    webhook["state"]["event"] = _checkout_event(
        customer_details={"email": "ada@example.com"},
    )

    resp = webhook["post"]()

    assert resp.status_code == 200
    assert webhook["subs"]()[0].user_id == 13


def test_stale_metadata_id_falls_through_to_email(webhook):
    webhook["add_user"](15, "ada@example.com")
    webhook["state"]["subscription"]["metadata"] = {"fc_user_id": "999"}
    webhook["state"]["customer"] = {"id": "cus_1", "metadata": {}, "email": "ada@example.com"}
    webhook["state"]["event"] = _checkout_event(client_reference_id="998")

    resp = webhook["post"]()

    assert resp.status_code == 200
    assert webhook["subs"]()[0].user_id == 15


def test_unresolved_checkout_persists_and_returns_500(webhook, caplog):
    webhook["state"]["customer"] = {
        "id": "cus_1",
        "metadata": {},
        "email": "missing@example.com",
    }
    webhook["state"]["event"] = _checkout_event(
        customer_details={"email": "missing@example.com"},
    )

    with caplog.at_level(logging.ERROR, logger="server.api.billing"):
        resp = webhook["post"]()

    assert resp.status_code == 500
    body = resp.json()
    assert "received" not in body
    assert "retry" in body["detail"].lower()
    assert webhook["subs"]() == []
    rows = webhook["recon"]()
    assert len(rows) == 1
    assert rows[0].stripe_event_id == "evt_1"
    assert rows[0].status == "open"
    assert rows[0].customer_email == "missing@example.com"
    assert rows[0].reason == "unresolved_user"
    payload = json.loads(rows[0].payload_json)
    assert payload["checkout_session_id"] == "cs_1"
    assert payload["customer_id"] == "cus_1"
    assert any("returning 500 so Stripe retries" in rec.message for rec in caplog.records)
    assert any(rec.levelno >= logging.ERROR for rec in caplog.records)


def test_unresolved_retry_updates_one_row_then_resolves(webhook):
    webhook["state"]["customer"] = {"id": "cus_1", "metadata": {}, "email": "ada@example.com"}
    webhook["state"]["event"] = _checkout_event(customer_details={"email": "ada@example.com"})

    first = webhook["post"]()
    second = webhook["post"]()

    assert first.status_code == 500
    assert second.status_code == 500
    assert len(webhook["recon"]()) == 1
    assert webhook["subs"]() == []

    webhook["add_user"](21, "ada@example.com")
    third = webhook["post"]()

    assert third.status_code == 200
    assert third.json() == {"received": True}
    assert webhook["subs"]()[0].user_id == 21
    rows = webhook["recon"]()
    assert len(rows) == 1
    assert rows[0].status == "resolved"


def test_invalid_signature_is_400_and_writes_nothing(webhook, monkeypatch):
    def reject(_payload, _sig):
        raise ValueError("bad sig")

    monkeypatch.setattr(billing.stripe_billing, "verify_webhook", reject)
    webhook["state"]["event"] = _checkout_event()

    resp = webhook["post"]()

    assert resp.status_code == 400
    assert webhook["subs"]() == []
    assert webhook["recon"]() == []


def test_payments_disabled_is_503(webhook, monkeypatch):
    monkeypatch.setattr(billing.stripe_billing, "stripe_enabled", lambda: False)
    webhook["state"]["event"] = _checkout_event()

    resp = webhook["post"]()

    assert resp.status_code == 503
    assert webhook["recon"]() == []
