"""Admin MRR across Stripe (subscriptions.monthly_price, USD) and Razorpay
(razorpay_subscriptions, INR/AED/USD), with approximate FX. No network."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.core.admin_mrr import compute_platform_mrr
from server.core.config import DEFAULT_USD_PER_CURRENCY, usd_per_currency
from server.models.razorpay_billing import RazorpaySubscription


@pytest.fixture(autouse=True)
def _no_fx_env(monkeypatch):
    for code in DEFAULT_USD_PER_CURRENCY:
        monkeypatch.delenv(f"USD_PER_{code}", raising=False)


def _db(with_razorpay: bool = True):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE subscriptions (
                id INTEGER PRIMARY KEY, user_id INTEGER, plan VARCHAR, status VARCHAR,
                stripe_subscription_id VARCHAR, monthly_price FLOAT, created_at TIMESTAMP
            )
        """))
    if with_razorpay:
        RazorpaySubscription.__table__.create(bind=engine, checkfirst=True)
    return sessionmaker(bind=engine)()


def _sub(db, uid, price, status="active", stripe_id=None):
    db.execute(
        text("INSERT INTO subscriptions (user_id, plan, status, stripe_subscription_id, monthly_price)"
             " VALUES (:u, 'starter', :s, :sid, :p)"),
        {"u": uid, "s": status, "sid": stripe_id, "p": price},
    )


_rz_seq = iter(range(1, 10_000))


def _rz(db, uid, currency, interval, amount, status="active"):
    n = next(_rz_seq)
    db.execute(
        text("""INSERT INTO razorpay_subscriptions
                    (user_id, razorpay_subscription_id, plan, interval, currency, amount, status,
                     created_at, updated_at)
                VALUES (:u, :sid, 'starter', :i, :c, :a, :s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"""),
        {"u": uid, "sid": f"sub_{n}", "i": interval, "c": currency, "a": amount, "s": status},
    )


def test_stripe_only_matches_the_old_sum():
    db = _db()
    _sub(db, 1, 29.0, stripe_id="sub_s1")
    _sub(db, 2, 49.0, stripe_id="sub_s2")
    _sub(db, 3, 99.0, status="canceled", stripe_id="sub_s3")
    out = compute_platform_mrr(db)
    assert out["mrr_usd"] == 78.0
    assert out["breakdown"]["by_currency"] == {"USD": {"native": 78.0, "usd": 78.0, "razorpay_subscriptions": 0}}


def test_missing_razorpay_table_is_not_an_error():
    db = _db(with_razorpay=False)
    _sub(db, 1, 29.0, stripe_id="sub_s1")
    assert compute_platform_mrr(db)["mrr_usd"] == 29.0


def test_inr_and_aed_are_converted_and_annual_is_divided_by_12():
    db = _db()
    rates = usd_per_currency()
    # Razorpay sync writes monthly_price 0 for non-USD subscriptions.
    _sub(db, 1, 0.0)
    _rz(db, 1, "INR", "monthly", 2499)
    _sub(db, 2, 0.0)
    _rz(db, 2, "AED", "annual", 1200)
    out = compute_platform_mrr(db)
    inr = out["breakdown"]["by_currency"]["INR"]
    aed = out["breakdown"]["by_currency"]["AED"]
    assert inr["native"] == 2499.0 and inr["razorpay_subscriptions"] == 1
    assert aed["native"] == 100.0  # 1200 / 12
    assert inr["usd"] == round(2499 * rates["INR"], 2)
    assert aed["usd"] == round(100 * rates["AED"], 2)
    assert out["mrr_usd"] == round(2499 * rates["INR"] + 100 * rates["AED"], 2)
    assert out["breakdown"]["fx_approximate"] is True


def test_usd_razorpay_subscription_is_not_double_counted():
    db = _db()
    # The Razorpay sync wrote the monthly list price ($29) into subscriptions
    # for a USD annual plan; the real annual charge is $290.
    _sub(db, 1, 29.0)
    _rz(db, 1, "USD", "annual", 290)
    # An unrelated Stripe subscriber still counts.
    _sub(db, 2, 49.0, stripe_id="sub_s2")
    out = compute_platform_mrr(db)
    assert out["mrr_usd"] == round(49.0 + 290 / 12, 2)
    assert out["breakdown"]["sources_usd"] == {"subscriptions": 49.0, "razorpay": round(290 / 12, 2)}
    assert out["breakdown"]["by_currency"]["USD"]["native"] == round(49.0 + 290 / 12, 2)


def test_only_active_razorpay_subscriptions_count():
    db = _db()
    for status in ("created", "authenticated", "pending", "halted", "cancelled", "completed"):
        _rz(db, 9, "INR", "monthly", 2499, status=status)
    # Inactive Razorpay rows do not hide this user's other active row.
    _sub(db, 9, 15.0)
    out = compute_platform_mrr(db)
    assert out["mrr_usd"] == 15.0
    assert "INR" not in out["breakdown"]["by_currency"]


def test_fx_env_override_and_bad_values_fall_back(monkeypatch):
    monkeypatch.setenv("USD_PER_INR", "0.02")
    monkeypatch.setenv("USD_PER_AED", "not-a-number")
    rates = usd_per_currency()
    assert rates["INR"] == 0.02
    assert rates["AED"] == DEFAULT_USD_PER_CURRENCY["AED"]
    monkeypatch.setenv("USD_PER_AED", "-1")
    assert usd_per_currency()["AED"] == DEFAULT_USD_PER_CURRENCY["AED"]
    monkeypatch.setenv("USD_PER_USD", "5")
    assert usd_per_currency()["USD"] == 1.0

    db = _db()
    _rz(db, 1, "INR", "monthly", 1000)
    assert compute_platform_mrr(db)["mrr_usd"] == 20.0


def test_unknown_currency_is_reported_but_not_guessed():
    db = _db()
    _rz(db, 1, "EUR", "monthly", 100)
    _sub(db, 2, 10.0, stripe_id="sub_s2")
    out = compute_platform_mrr(db)
    assert out["mrr_usd"] == 10.0
    assert out["breakdown"]["by_currency"]["EUR"] == {"native": 100.0, "usd": None, "razorpay_subscriptions": 1}
    assert out["breakdown"]["unconverted_currencies"] == ["EUR"]


def test_dashboard_endpoint_reports_breakdown():
    from server.api.admin import get_dashboard_metrics
    from server.core.db import Base
    import server.models  # noqa: F401  (register every table)

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from server.models import Company, Scenario, Subscription, TruthScan, User
    from server.models.financial import FinancialRecord

    Base.metadata.create_all(bind=engine, tables=[
        m.__table__ for m in (User, Company, Subscription, Scenario, TruthScan,
                              FinancialRecord, RazorpaySubscription)
    ])
    db = sessionmaker(bind=engine)()
    _sub(db, None, 29.0, stripe_id="sub_s1")
    _rz(db, 5, "INR", "monthly", 1000)
    db.commit()

    out = get_dashboard_metrics(db=db, current_user=None)
    assert out.mrr_source == "subscriptions"
    assert out.mrr == round(29.0 + 1000 * usd_per_currency()["INR"], 2)
    assert out.mrr_breakdown["by_currency"]["INR"]["native"] == 1000.0
