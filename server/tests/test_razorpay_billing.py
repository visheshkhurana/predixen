"""Razorpay billing: off by default, signatures, webhook idempotency and state,
regional pricing and currency resolution. No real Razorpay calls are made."""

from __future__ import annotations

import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api import billing
from server.core import plans, razorpay_billing
from server.core.billing_region import resolve_currency
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.razorpay_billing import RazorpaySubscription, RazorpayWebhookEvent

KEY_ID = "rzp_test_key"
KEY_SECRET = "test_key_secret"
WEBHOOK_SECRET = "test_webhook_secret"
PLAN_ENV = {
    "RAZORPAY_PLAN_STARTER_MONTHLY_INR": "plan_inr_m",
    "RAZORPAY_PLAN_STARTER_ANNUAL_INR": "plan_inr_a",
    "RAZORPAY_PLAN_STARTER_MONTHLY_USD": "plan_usd_m",
    "RAZORPAY_PLAN_STARTER_ANNUAL_USD": "plan_usd_a",
    "RAZORPAY_PLAN_STARTER_MONTHLY_AED": "plan_aed_m",
    "RAZORPAY_PLAN_STARTER_ANNUAL_AED": "plan_aed_a",
}
ALL_ENV = ["BILLING_PROVIDER", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET", *PLAN_ENV]


def _clear_env(monkeypatch):
    for name in ALL_ENV:
        monkeypatch.delenv(name, raising=False)


def _enable(monkeypatch):
    monkeypatch.setenv("BILLING_PROVIDER", "razorpay")
    monkeypatch.setenv("RAZORPAY_KEY_ID", KEY_ID)
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", KEY_SECRET)
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    for k, v in PLAN_ENV.items():
        monkeypatch.setenv(k, v)


def _sig(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def env(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setattr(billing.stripe_billing, "stripe_enabled", lambda: False)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL, created_at TIMESTAMP)"))
        conn.execute(text("""
            CREATE TABLE subscriptions (
                id INTEGER PRIMARY KEY, user_id INTEGER, plan VARCHAR, status VARCHAR,
                stripe_subscription_id VARCHAR, stripe_customer_id VARCHAR,
                current_period_start TIMESTAMP, current_period_end TIMESTAMP,
                trial_start TIMESTAMP, trial_end TIMESTAMP,
                monthly_price FLOAT, created_at TIMESTAMP, updated_at TIMESTAMP
            )
        """))
        conn.execute(text(
            "CREATE TABLE companies (id INTEGER PRIMARY KEY, user_id INTEGER, currency VARCHAR, metadata_json TEXT)"
        ))
        conn.execute(text("INSERT INTO users (id, email) VALUES (1, 'a@example.com'), (2, 'b@example.com')"))
    RazorpaySubscription.__table__.create(bind=engine, checkfirst=True)
    RazorpayWebhookEvent.__table__.create(bind=engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(billing, "SessionLocal", lambda: Session())

    state = {"user": SimpleNamespace(id=1, email="a@example.com", display_name="A", is_master=False)}

    app = FastAPI()
    app.include_router(billing.router)

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: state["user"]
    client = TestClient(app, raise_server_exceptions=False)

    def q(sql, **params):
        with engine.begin() as conn:
            result = conn.execute(text(sql), params)
            return result.fetchall() if result.returns_rows else None

    return SimpleNamespace(client=client, engine=engine, Session=Session, state=state, q=q, mp=monkeypatch)


def _seed_rz(env, sub_id="sub_1", user_id=1, status="created", plan="starter", currency="INR",
             interval="monthly", customer="cust_1"):
    env.q(
        """INSERT INTO razorpay_subscriptions
             (user_id, razorpay_subscription_id, razorpay_customer_id, razorpay_plan_id, plan, interval,
              currency, amount, status, created_at, updated_at)
           VALUES (:u, :s, :c, :p, :plan, :i, :cur, 3000, :st, '2026-11-01', '2026-11-01')""",
        u=user_id, s=sub_id, c=customer, p="plan_inr_m", plan=plan, i=interval, cur=currency, st=status,
    )


def _post_webhook(env, event: dict, event_id="evt_1", secret=WEBHOOK_SECRET, raw=None, sig=None):
    body = raw if raw is not None else json.dumps(event).encode()
    headers = {"Content-Type": "application/json"}
    if event_id:
        headers["X-Razorpay-Event-Id"] = event_id
    headers["X-Razorpay-Signature"] = sig if sig is not None else _sig(secret, body)
    return env.client.post("/billing/razorpay/webhook", content=body, headers=headers)


def _sub_event(etype, status, sub_id="sub_1", plan_id="plan_inr_m", created_at=1_800_000_000,
               current_start=1_800_000_000, current_end=1_802_592_000):
    return {
        "entity": "event",
        "event": etype,
        "created_at": created_at,
        "payload": {
            "subscription": {
                "entity": {
                    "id": sub_id, "status": status, "plan_id": plan_id, "customer_id": "cust_1",
                    "current_start": current_start, "current_end": current_end,
                    "notes": {"fc_user_id": "1"},
                }
            }
        },
    }


def _local_sub(env, user_id=1):
    rows = env.q("SELECT plan, status, monthly_price FROM subscriptions WHERE user_id = :u", u=user_id)
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Disabled by default
# ---------------------------------------------------------------------------

def test_disabled_when_env_unset(env):
    assert razorpay_billing.razorpay_enabled() is False
    assert billing.billing_provider() == "stripe"
    assert billing.payments_enabled() is False


@pytest.mark.parametrize("missing", ["BILLING_PROVIDER", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET"])
def test_disabled_when_any_required_var_missing(env, missing):
    _enable(env.mp)
    env.mp.delenv(missing)
    assert razorpay_billing.razorpay_enabled() is False
    assert billing.billing_provider() == "stripe"


def test_provider_must_be_razorpay_explicitly(env):
    _enable(env.mp)
    env.mp.setenv("BILLING_PROVIDER", "stripe")
    assert razorpay_billing.razorpay_enabled() is False


def test_plans_unchanged_when_env_unset(env):
    r = env.client.get("/billing/plans")
    assert r.status_code == 200
    data = r.json()
    assert data["payments_enabled"] is False
    assert data["provider"] == "stripe"
    assert data["currency"] == "USD"
    by_id = {p["id"]: p for p in data["plans"]}
    assert set(by_id) == {"free", "starter", "growth", "scale"}
    for tier in ("starter", "growth", "scale"):
        assert by_id[tier]["price_monthly"] == plans.PLAN_DETAILS[tier]["price_monthly"]
        assert by_id[tier]["price_annual"] == plans.PLAN_DETAILS[tier]["price_annual"]


def test_subscribe_still_503_when_env_unset(env):
    r = env.client.post("/billing/subscribe/starter", json={"interval": "monthly"})
    assert r.status_code == 503


def test_webhook_refused_when_secret_unset(env):
    r = _post_webhook(env, _sub_event("subscription.activated", "active"))
    assert r.status_code == 503
    assert env.q("SELECT COUNT(*) FROM razorpay_webhook_events")[0][0] == 0


def test_verify_refused_when_disabled(env):
    r = env.client.post("/billing/razorpay/verify", json={
        "razorpay_payment_id": "pay_1", "razorpay_subscription_id": "sub_1", "razorpay_signature": "x",
    })
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# Signatures
# ---------------------------------------------------------------------------

def test_payment_signature_valid(env):
    _enable(env.mp)
    sig = _sig(KEY_SECRET, b"pay_1|sub_1")
    assert razorpay_billing.verify_payment_signature("pay_1", "sub_1", sig) is True


def test_payment_signature_invalid(env):
    _enable(env.mp)
    assert razorpay_billing.verify_payment_signature("pay_1", "sub_1", "0" * 64) is False
    # Signed for a different subscription.
    assert razorpay_billing.verify_payment_signature("pay_1", "sub_2", _sig(KEY_SECRET, b"pay_1|sub_1")) is False
    # Signed with the wrong secret.
    assert razorpay_billing.verify_payment_signature("pay_1", "sub_1", _sig("other", b"pay_1|sub_1")) is False


def test_payment_signature_missing_secret(env):
    sig = _sig(KEY_SECRET, b"pay_1|sub_1")
    assert razorpay_billing.verify_payment_signature("pay_1", "sub_1", sig) is False


def test_webhook_signature_valid_invalid_tampered_missing(env):
    body = b'{"event":"subscription.activated"}'
    env.mp.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    good = _sig(WEBHOOK_SECRET, body)
    assert razorpay_billing.verify_webhook_signature(body, good) is True
    assert razorpay_billing.verify_webhook_signature(body, "deadbeef") is False
    assert razorpay_billing.verify_webhook_signature(body + b" ", good) is False
    assert razorpay_billing.verify_webhook_signature(body, None) is False
    assert razorpay_billing.verify_webhook_signature(body, "") is False
    env.mp.delenv("RAZORPAY_WEBHOOK_SECRET")
    assert razorpay_billing.verify_webhook_signature(body, good) is False


def test_webhook_endpoint_rejects_bad_signature(env):
    _enable(env.mp)
    _seed_rz(env)
    r = _post_webhook(env, _sub_event("subscription.activated", "active"), sig="0" * 64)
    assert r.status_code == 400
    assert _local_sub(env) is None


def test_webhook_endpoint_rejects_tampered_body(env):
    _enable(env.mp)
    _seed_rz(env)
    original = json.dumps(_sub_event("subscription.activated", "active")).encode()
    sig = _sig(WEBHOOK_SECRET, original)
    tampered = original.replace(b"plan_inr_m", b"plan_usd_a")
    r = _post_webhook(env, {}, raw=tampered, sig=sig)
    assert r.status_code == 400
    assert _local_sub(env) is None


def test_webhook_works_with_only_webhook_secret(env):
    # A provider switch back to Stripe must still record Razorpay cancellations.
    env.mp.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    for k, v in PLAN_ENV.items():
        env.mp.setenv(k, v)
    _seed_rz(env, status="active")
    r = _post_webhook(env, _sub_event("subscription.cancelled", "cancelled"))
    assert r.status_code == 200
    assert _local_sub(env)[1] == "canceled"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def test_webhook_idempotent_on_event_id(env):
    _enable(env.mp)
    _seed_rz(env)
    calls = []
    real = billing._apply_razorpay_state
    env.mp.setattr(billing, "_apply_razorpay_state", lambda *a, **k: calls.append(1) or real(*a, **k))

    event = _sub_event("subscription.activated", "active")
    r1 = _post_webhook(env, event, event_id="evt_same")
    r2 = _post_webhook(env, event, event_id="evt_same")
    assert r1.status_code == 200 and r1.json() == {"received": True}
    assert r2.status_code == 200 and r2.json().get("duplicate") is True
    assert len(calls) == 1
    assert env.q("SELECT COUNT(*) FROM razorpay_webhook_events")[0][0] == 1


def test_webhook_dedupes_on_body_hash_without_event_id(env):
    _enable(env.mp)
    _seed_rz(env)
    event = _sub_event("subscription.activated", "active")
    assert _post_webhook(env, event, event_id=None).json() == {"received": True}
    assert _post_webhook(env, event, event_id=None).json().get("duplicate") is True
    assert env.q("SELECT COUNT(*) FROM razorpay_webhook_events")[0][0] == 1


def test_webhook_processing_error_is_not_marked_processed(env):
    _enable(env.mp)
    _seed_rz(env)

    def boom(*a, **k):
        raise RuntimeError("db down")

    env.mp.setattr(billing, "_apply_razorpay_state", boom)
    r = _post_webhook(env, _sub_event("subscription.activated", "active"), event_id="evt_err")
    assert r.status_code == 500
    assert env.q("SELECT COUNT(*) FROM razorpay_webhook_events")[0][0] == 0


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

def test_activated_then_charged_then_halted_then_cancelled(env):
    _enable(env.mp)
    _seed_rz(env)

    assert _post_webhook(env, _sub_event("subscription.activated", "active", created_at=100), "e1").status_code == 200
    assert _local_sub(env)[:2] == ("starter", "active")
    assert env.q("SELECT status FROM razorpay_subscriptions")[0][0] == "active"

    assert _post_webhook(env, _sub_event("subscription.charged", "active", created_at=200,
                                         current_end=1_805_000_000), "e2").status_code == 200
    assert _local_sub(env)[1] == "active"

    assert _post_webhook(env, _sub_event("subscription.halted", "halted", created_at=300), "e3").status_code == 200
    assert _local_sub(env)[1] == "past_due"

    assert _post_webhook(env, _sub_event("subscription.cancelled", "cancelled", created_at=400), "e4").status_code == 200
    assert _local_sub(env)[1] == "canceled"


def test_completed_maps_to_canceled(env):
    _enable(env.mp)
    _seed_rz(env, status="active")
    _post_webhook(env, _sub_event("subscription.completed", "completed"))
    assert _local_sub(env)[1] == "canceled"


def test_authenticated_grants_nothing(env):
    _enable(env.mp)
    _seed_rz(env)
    _post_webhook(env, _sub_event("subscription.authenticated", "authenticated"))
    assert _local_sub(env) is None


def test_out_of_order_event_is_ignored(env):
    _enable(env.mp)
    _seed_rz(env)
    _post_webhook(env, _sub_event("subscription.cancelled", "cancelled", created_at=500), "late1")
    _post_webhook(env, _sub_event("subscription.activated", "active", created_at=100), "early1")
    assert _local_sub(env)[1] == "canceled"


def test_payment_failed_downgrades_active_subscription(env):
    _enable(env.mp)
    _seed_rz(env, status="active")
    env.q("INSERT INTO subscriptions (user_id, plan, status, created_at) VALUES (1, 'starter', 'active', '2026-11-01')")
    event = {"event": "payment.failed", "created_at": 900, "payload": {"payment": {"entity": {
        "id": "pay_x", "subscription_id": "sub_1", "customer_id": "cust_1", "status": "failed"}}}}
    assert _post_webhook(env, event).status_code == 200
    assert _local_sub(env)[1] == "past_due"


def test_payment_failed_does_not_end_a_trial(env):
    _enable(env.mp)
    _seed_rz(env, status="created")
    env.q("INSERT INTO subscriptions (user_id, plan, status, created_at) VALUES (1, 'scale', 'trialing', '2026-11-01')")
    event = {"event": "payment.failed", "payload": {"payment": {"entity": {
        "id": "pay_x", "customer_id": "cust_1", "status": "failed"}}}}
    assert _post_webhook(env, event).status_code == 200
    assert _local_sub(env)[:2] == ("scale", "trialing")


def test_tier_comes_from_plan_id_not_notes(env):
    _enable(env.mp)
    _seed_rz(env)
    event = _sub_event("subscription.activated", "active", plan_id="plan_usd_m")
    event["payload"]["subscription"]["entity"]["notes"] = {"fc_user_id": "1", "fc_plan": "scale"}
    _post_webhook(env, event)
    plan, status, monthly_price = _local_sub(env)
    assert (plan, status) == ("starter", "active")
    assert monthly_price == 39.0  # USD subscriptions feed the USD MRR sum
    assert env.q("SELECT currency FROM razorpay_subscriptions")[0][0] == "USD"


def test_inr_subscription_does_not_inflate_usd_mrr(env):
    _enable(env.mp)
    _seed_rz(env)
    _post_webhook(env, _sub_event("subscription.activated", "active"))
    assert _local_sub(env)[2] == 0.0


def test_unknown_subscription_adopted_only_with_valid_notes_and_plan(env):
    _enable(env.mp)
    _post_webhook(env, _sub_event("subscription.activated", "active", sub_id="sub_new"), "a1")
    assert _local_sub(env)[:2] == ("starter", "active")

    bad = _sub_event("subscription.activated", "active", sub_id="sub_bad", plan_id="plan_not_ours")
    bad["payload"]["subscription"]["entity"]["notes"] = {"fc_user_id": "2"}
    _post_webhook(env, bad, "a2")
    assert _local_sub(env, user_id=2) is None


# ---------------------------------------------------------------------------
# Checkout, verify, cancel
# ---------------------------------------------------------------------------

def _mock_api(env, sub_status="active"):
    calls = {"create_sub": [], "cancel": []}
    env.mp.setattr(razorpay_billing, "get_or_create_customer", lambda *a, **k: "cust_1")

    def create_sub(plan_id, interval, user_id, tier, currency, customer_id=None):
        calls["create_sub"].append((plan_id, interval, tier, currency))
        return {"id": "sub_new1", "status": "created"}

    env.mp.setattr(razorpay_billing, "create_subscription", create_sub)
    env.mp.setattr(razorpay_billing, "fetch_subscription", lambda sid: {
        "id": sid, "status": sub_status, "plan_id": "plan_inr_m", "customer_id": "cust_1",
        "current_start": 1_800_000_000, "current_end": 1_802_592_000})

    def cancel(sid, at_cycle_end=True):
        calls["cancel"].append((sid, at_cycle_end))
        return {"id": sid, "status": "active", "current_end": 1_802_592_000}

    env.mp.setattr(razorpay_billing, "cancel_subscription", cancel)
    return calls


def test_subscribe_returns_checkout_params(env):
    _enable(env.mp)
    calls = _mock_api(env)
    r = env.client.post("/billing/subscribe/starter", json={"interval": "annual"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["subscription_id"] == "sub_new1"
    assert data["key_id"] == KEY_ID
    assert data["currency"] == "INR" and data["amount"] == 30000
    assert calls["create_sub"] == [("plan_inr_a", "annual", "starter", "INR")]
    row = env.q("SELECT user_id, plan, interval, currency, amount FROM razorpay_subscriptions")[0]
    assert tuple(row) == (1, "starter", "annual", "INR", 30000)


def test_subscribe_ignores_client_amount_and_rejects_bad_currency(env):
    _enable(env.mp)
    calls = _mock_api(env)
    r = env.client.post("/billing/subscribe/starter", json={"interval": "monthly", "currency": "AED", "amount": 1})
    assert r.status_code == 200
    assert r.json()["amount"] == 149
    assert calls["create_sub"][-1][0] == "plan_aed_m"

    r = env.client.post("/billing/subscribe/starter", json={"interval": "monthly", "currency": "EUR"})
    assert r.status_code == 400


def test_subscribe_unoffered_tier_404(env):
    _enable(env.mp)
    _mock_api(env)
    assert env.client.post("/billing/subscribe/scale", json={}).status_code == 404


def test_subscribe_missing_plan_env_503(env):
    _enable(env.mp)
    _mock_api(env)
    env.mp.delenv("RAZORPAY_PLAN_STARTER_MONTHLY_INR")
    assert env.client.post("/billing/subscribe/starter", json={}).status_code == 503


def test_plans_show_regional_prices_when_enabled(env):
    _enable(env.mp)
    data = env.client.get("/billing/plans", params={"currency": "INR"}).json()
    assert data["provider"] == "razorpay" and data["payments_enabled"] is True
    assert data["currency"] == "INR" and data["currency_symbol"] == "₹"
    assert data["annual_label"] == "2 months free"
    by_id = {p["id"]: p for p in data["plans"]}
    assert set(by_id) == {"free", "starter"}  # higher tiers hidden on Razorpay for now
    assert by_id["starter"]["price_monthly"] == 3000 and by_id["starter"]["price_annual"] == 30000
    usd = {p["id"]: p for p in env.client.get("/billing/plans", params={"currency": "usd"}).json()["plans"]}
    assert usd["starter"]["price_monthly"] == 39
    assert env.client.get("/billing/plans", params={"currency": "EUR"}).json()["currency"] == "INR"


def test_verify_activates_from_fetched_state(env):
    _enable(env.mp)
    _mock_api(env, sub_status="active")
    _seed_rz(env)
    sig = _sig(KEY_SECRET, b"pay_1|sub_1")
    r = env.client.post("/billing/razorpay/verify", json={
        "razorpay_payment_id": "pay_1", "razorpay_subscription_id": "sub_1", "razorpay_signature": sig})
    assert r.status_code == 200 and r.json()["status"] == "active"
    assert _local_sub(env)[:2] == ("starter", "active")


def test_verify_pending_when_not_yet_charged(env):
    _enable(env.mp)
    _mock_api(env, sub_status="authenticated")
    _seed_rz(env)
    sig = _sig(KEY_SECRET, b"pay_1|sub_1")
    r = env.client.post("/billing/razorpay/verify", json={
        "razorpay_payment_id": "pay_1", "razorpay_subscription_id": "sub_1", "razorpay_signature": sig})
    assert r.json()["status"] == "pending"
    assert _local_sub(env) is None


def test_verify_rejects_bad_signature_and_other_users_subscription(env):
    _enable(env.mp)
    _mock_api(env)
    _seed_rz(env)
    _seed_rz(env, sub_id="sub_other", user_id=2, customer="cust_2")
    r = env.client.post("/billing/razorpay/verify", json={
        "razorpay_payment_id": "pay_1", "razorpay_subscription_id": "sub_1", "razorpay_signature": "0" * 64})
    assert r.status_code == 400
    sig = _sig(KEY_SECRET, b"pay_1|sub_other")
    r = env.client.post("/billing/razorpay/verify", json={
        "razorpay_payment_id": "pay_1", "razorpay_subscription_id": "sub_other", "razorpay_signature": sig})
    assert r.status_code == 404
    assert _local_sub(env) is None and _local_sub(env, 2) is None


def test_cancel_at_cycle_end(env):
    _enable(env.mp)
    calls = _mock_api(env)
    _seed_rz(env, status="active")
    r = env.client.post("/billing/cancel")
    assert r.status_code == 200 and r.json()["cancelled_at_cycle_end"] is True
    assert calls["cancel"] == [("sub_1", True)]


def test_cancel_without_subscription_400(env):
    _enable(env.mp)
    _mock_api(env)
    assert env.client.post("/billing/cancel").status_code == 400


def test_rest_client_uses_basic_auth_and_cancel_at_cycle_end(env, monkeypatch):
    _enable(env.mp)
    seen = {}

    class Resp:
        status_code = 200

        def json(self):
            return {"id": "sub_1", "status": "active"}

    def fake_request(method, url, json=None, auth=None, timeout=None):
        seen.update(method=method, url=url, json=json, auth=auth)
        return Resp()

    monkeypatch.setattr(razorpay_billing.httpx, "request", fake_request)
    razorpay_billing.cancel_subscription("sub_1")
    assert seen["method"] == "POST"
    assert seen["url"] == "https://api.razorpay.com/v1/subscriptions/sub_1/cancel"
    assert seen["json"] == {"cancel_at_cycle_end": 1}
    assert seen["auth"] == (KEY_ID, KEY_SECRET)


def test_rest_client_raises_on_error(env, monkeypatch):
    _enable(env.mp)

    class Resp:
        status_code = 400

        def json(self):
            return {"error": {"description": "bad plan"}}

    monkeypatch.setattr(razorpay_billing.httpx, "request", lambda *a, **k: Resp())
    with pytest.raises(razorpay_billing.RazorpayError):
        razorpay_billing.fetch_subscription("sub_1")


# ---------------------------------------------------------------------------
# Pricing table and currency resolution
# ---------------------------------------------------------------------------

def test_final_prices():
    assert plans.get_regional_price("starter", "INR", "monthly")["amount"] == 3000
    assert plans.get_regional_price("starter", "USD", "monthly")["amount"] == 39
    assert plans.get_regional_price("starter", "AED", "monthly")["amount"] == 149
    assert plans.get_regional_price("starter", "INR", "annual")["amount"] == 30000
    assert plans.get_regional_price("starter", "USD", "annual")["amount"] == 390
    assert plans.get_regional_price("starter", "AED", "annual")["amount"] == 1490
    assert plans.get_regional_price("starter", "INR", "monthly")["amount_minor"] == 300000


def test_annual_is_ten_times_monthly_for_every_currency():
    assert plans.ANNUAL_MULTIPLIER == 10
    for (tier, currency, interval), entry in plans.PRICE_TABLE.items():
        if interval != "annual":
            continue
        monthly = plans.PRICE_TABLE[(tier, currency, "monthly")]["amount"]
        assert entry["amount"] == 10 * monthly, (tier, currency)
    assert {c for (_, c, _) in plans.PRICE_TABLE} == set(plans.SUPPORTED_CURRENCIES)


def test_annual_is_derived_from_monthly(monkeypatch):
    monkeypatch.setitem(plans.REGIONAL_MONTHLY_PRICES, ("starter", "USD"), 45)
    table = plans._build_price_table()
    assert table[("starter", "USD", "annual")]["amount"] == 450


def test_plan_env_var_names():
    assert plans.PRICE_TABLE[("starter", "INR", "monthly")]["plan_env"] == "RAZORPAY_PLAN_STARTER_MONTHLY_INR"
    assert plans.PRICE_TABLE[("starter", "AED", "annual")]["plan_env"] == "RAZORPAY_PLAN_STARTER_ANNUAL_AED"


def test_unknown_price_is_none():
    assert plans.get_regional_price("scale", "INR", "monthly") is None
    assert plans.get_regional_price("starter", "EUR", "monthly") is None
    assert plans.get_regional_price("starter", "INR", "weekly") is None


@pytest.mark.parametrize("country,currency", [
    ("IN", "INR"), ("in", "INR"), ("US", "USD"), ("AE", "AED"), ("GB", "USD"), ("SG", "USD"),
    ("", None), (None, None), ("XX", None), ("T1", None), ("India", None),
])
def test_currency_for_country(country, currency):
    assert plans.currency_for_country(country) == currency


def test_tier_for_plan_id(env):
    _enable(env.mp)
    assert razorpay_billing.tier_for_plan_id("plan_aed_a") == {
        "tier": "starter", "currency": "AED", "interval": "annual", "amount": 1490}
    assert razorpay_billing.tier_for_plan_id("plan_nope") is None
    assert razorpay_billing.tier_for_plan_id(None) is None


def _resolve(env, user_id=1, headers=None, requested=None):
    db = env.Session()
    try:
        return resolve_currency(db, user_id, headers, requested)
    finally:
        db.close()


def test_resolution_default_is_inr(env):
    assert _resolve(env) == ("INR", "default")


def test_resolution_requested_wins_if_valid(env):
    env.q("INSERT INTO companies (user_id, currency) VALUES (1, 'INR')")
    assert _resolve(env, requested="aed") == ("AED", "requested")
    assert _resolve(env, requested="EUR") == ("INR", "company_currency")


def test_resolution_company_currency(env):
    env.q("INSERT INTO companies (user_id, currency, metadata_json) VALUES (1, 'AED', '{\"country\": \"IN\"}')")
    assert _resolve(env, headers={"cf-ipcountry": "US"}) == ("AED", "company_currency")


def test_resolution_company_country_when_currency_unsupported(env):
    env.q("INSERT INTO companies (user_id, currency, metadata_json) VALUES (1, 'EUR', '{\"country\": \"AE\"}')")
    assert _resolve(env, headers={"cf-ipcountry": "US"}) == ("AED", "company_country")


def test_resolution_ip_header_then_default(env):
    env.q("INSERT INTO companies (user_id, currency, metadata_json) VALUES (1, 'EUR', '{}')")
    assert _resolve(env, headers={"cf-ipcountry": "US"}) == ("USD", "ip_country")
    assert _resolve(env, headers={"cf-ipcountry": "DE"}) == ("USD", "ip_country")
    assert _resolve(env, headers={"cf-ipcountry": "XX"}) == ("INR", "default")
    assert _resolve(env, headers={}) == ("INR", "default")


def test_resolution_uses_latest_company(env):
    env.q("INSERT INTO companies (id, user_id, currency) VALUES (1, 1, 'USD'), (2, 1, 'INR')")
    assert _resolve(env) == ("INR", "company_currency")
