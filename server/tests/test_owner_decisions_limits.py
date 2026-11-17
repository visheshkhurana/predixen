"""Free plan gets one data connector; Copilot fallbacks do not spend quota."""
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.core import plan_usage
from server.core.plans import PlanTier


def _company(*connected, disconnected=()):
    connectors = {p: {"connected": True} for p in connected}
    connectors.update({p: {"connected": False} for p in disconnected})
    return SimpleNamespace(id=1, metadata_json={"connectors": connectors})


@pytest.fixture
def paid(monkeypatch):
    monkeypatch.setattr(plan_usage, "_payments_enabled", lambda: True)
    monkeypatch.setattr("server.core.security.is_master_user", lambda u: False)

    def use_plan(plan):
        monkeypatch.setattr(plan_usage, "get_user_subscription", lambda db, uid: {"effective_plan": plan})
    return use_plan


USER = SimpleNamespace(id=7)


def test_free_can_connect_first_connector(paid):
    paid(PlanTier.FREE)
    plan_usage.enforce_connector_limit(None, USER, _company(), "shopify")


def test_free_second_connector_is_402_with_upgrade_message(paid):
    paid(PlanTier.FREE)
    with pytest.raises(HTTPException) as e:
        plan_usage.enforce_connector_limit(None, USER, _company("shopify"), "razorpay")
    assert e.value.status_code == 402
    d = e.value.detail
    assert d["error"] == "plan_limit_reached"
    assert d["limit"] == "max_connectors"
    assert (d["used"], d["max"]) == (1, 1)
    assert "1 data connector," in d["message"]


def test_reconnecting_an_existing_connector_is_allowed(paid):
    paid(PlanTier.FREE)
    plan_usage.enforce_connector_limit(None, USER, _company("shopify"), "shopify")


def test_disconnected_entries_do_not_count(paid):
    paid(PlanTier.FREE)
    plan_usage.enforce_connector_limit(None, USER, _company(disconnected=("shopify",)), "razorpay")


def test_starter_allows_two_and_scale_unlimited(paid):
    paid(PlanTier.STARTER)
    plan_usage.enforce_connector_limit(None, USER, _company("shopify"), "razorpay")
    with pytest.raises(HTTPException):
        plan_usage.enforce_connector_limit(None, USER, _company("shopify", "razorpay"), "meta_ads")
    paid(PlanTier.SCALE)
    plan_usage.enforce_connector_limit(None, USER, _company(*[f"p{i}" for i in range(40)]), "x")


def test_connector_limit_off_while_payments_off(monkeypatch):
    monkeypatch.setattr(plan_usage, "_payments_enabled", lambda: False)
    plan_usage.enforce_connector_limit(None, USER, _company("a", "b", "c"), "d")


@pytest.fixture
def quota_db(monkeypatch):
    import server.models  # noqa: F401
    from server.models.analytics_event import AnalyticsEvent
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    AnalyticsEvent.__table__.create(engine)
    monkeypatch.setattr(plan_usage, "_payments_enabled", lambda: True)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db, AnalyticsEvent
    db.close()
    engine.dispose()


def _reserve(db, Event, company_id=1):
    db.add(Event(event_name=plan_usage.PLAN_QUOTA_COPILOT, user_id=7, company_id=company_id,
                 meta_json={}, created_at=datetime.utcnow()))
    db.commit()


def test_release_gives_back_one_copilot_message(quota_db):
    db, Event = quota_db
    _reserve(db, Event)
    _reserve(db, Event)
    assert plan_usage.monthly_usage(db, 7, plan_usage.PLAN_QUOTA_COPILOT) == 2
    plan_usage.release_monthly_quota(db, 7, plan_usage.PLAN_QUOTA_COPILOT, company_id=1)
    db.expire_all()
    assert plan_usage.monthly_usage(db, 7, plan_usage.PLAN_QUOTA_COPILOT) == 1


def test_release_with_nothing_reserved_is_a_no_op(quota_db):
    db, _ = quota_db
    plan_usage.release_monthly_quota(db, 7, plan_usage.PLAN_QUOTA_COPILOT)
    assert plan_usage.monthly_usage(db, 7, plan_usage.PLAN_QUOTA_COPILOT) == 0


def test_copilot_refund_only_when_ai_unavailable(monkeypatch):
    from server.api import copilot
    calls = []
    monkeypatch.setattr(plan_usage, "release_monthly_quota", lambda *a, **k: calls.append((a, k)))
    copilot._refund_copilot_quota_if_unavailable(None, USER, 1, {"ai_unavailable": False})
    copilot._refund_copilot_quota_if_unavailable(None, USER, 1, SimpleNamespace(ai_unavailable=False))
    assert calls == []
    copilot._refund_copilot_quota_if_unavailable(None, USER, 1, SimpleNamespace(ai_unavailable=True))
    copilot._refund_copilot_quota_if_unavailable(None, USER, 1, {"ai_unavailable": True})
    assert len(calls) == 2
