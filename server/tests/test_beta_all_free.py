"""Public beta: every feature is free for every account.

CEO decision (Vishesh, 21 Oct 2026). BETA_ALL_FREE in server/core/plans.py is
the revert switch. Paid plan definitions stay as they were. A fresh free user
must get 200, not 403 feature_locked, on Truth Scan run, simulation, Copilot
chat, and quick-chat while the paywall is on.

Run: .venv/bin/python -m pytest server/tests/test_beta_all_free.py -q
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api import billing, copilot
from server.api import truth_scan as truth_scan_api
from server.core.db import get_db
from server.core.plans import (
    BETA_ALL_FREE,
    BETA_EXCLUDED_FEATURES,
    Feature,
    PLAN_DETAILS,
    PlanTier,
    beta_grants_feature,
    _GATED_FREE_PLAN,
    has_feature,
    minimum_plan_for_feature,
)
from server.core.security import AUTH_COOKIE_NAME, create_access_token, get_current_user
from server.core.subscription import PaywallMiddleware, check_feature_access, get_user_subscription
from server.tests.test_llm_redaction_audit import (
    RecordingDB,
    _company,
    _free_user,
    _truth_scan,
    llm_sink as _llm_sink_fixture,
)


def _values(plan: dict) -> dict:
    return {
        "name": plan["name"],
        "price_monthly": plan["price_monthly"],
        "price_annual": plan["price_annual"],
        "tagline": plan["tagline"],
        "max_companies": plan["max_companies"],
        "max_simulations_per_month": plan["max_simulations_per_month"],
        "max_copilot_messages_per_month": plan["max_copilot_messages_per_month"],
        "max_connectors": plan["max_connectors"],
        "features": [feature.value for feature in plan["features"]],
        "highlights": list(plan["highlights"]),
    }


# Frozen the day the beta switch landed. Paid tiers must not move with it.
_PAID_SNAPSHOTS = {
    "starter": {
        "name": "Starter",
        "price_monthly": 29,
        "price_annual": 290,
        "tagline": "For early-stage founders",
        "max_companies": 1,
        "max_simulations_per_month": 50,
        "max_copilot_messages_per_month": 100,
        "max_connectors": 2,
        "features": [
            "dashboard",
            "basic_metrics",
            "csv_upload",
            "manual_data_entry",
            "simulations",
            "copilot",
            "truth_scan",
            "stress_tests",
            "what_if",
            "sensitivity_analysis",
            "export_pdf",
            "benchmarks",
        ],
        "highlights": [
            "1 company",
            "50 simulations / month",
            "100 copilot messages / month",
            "2 data connectors",
            "Truth Scan & Stress Tests",
            "Industry benchmarks",
            "PDF export",
        ],
    },
    "growth": {
        "name": "Growth",
        "price_monthly": 49,
        "price_annual": 490,
        "tagline": "For scaling startups",
        "max_companies": 3,
        "max_simulations_per_month": -1,
        "max_copilot_messages_per_month": -1,
        "max_connectors": 10,
        "features": [
            "dashboard",
            "basic_metrics",
            "csv_upload",
            "manual_data_entry",
            "simulations",
            "simulation_unlimited",
            "copilot",
            "copilot_unlimited",
            "truth_scan",
            "stress_tests",
            "what_if",
            "sensitivity_analysis",
            "data_connectors",
            "fundraising_os",
            "cap_table",
            "board_deck",
            "export_pdf",
            "email_reports",
            "benchmarks",
            "fundraising_readiness",
        ],
        "highlights": [
            "Up to 3 companies",
            "Unlimited simulations",
            "Unlimited copilot",
            "10 data connectors",
            "Fundraising OS & Cap table",
            "Board deck export",
            "Email reports",
            "Fundraising readiness score",
        ],
    },
    "scale": {
        "name": "Scale",
        "price_monthly": 99,
        "price_annual": 990,
        "tagline": "Full power for serious founders",
        "max_companies": -1,
        "max_simulations_per_month": -1,
        "max_copilot_messages_per_month": -1,
        "max_connectors": -1,
        "features": [
            "dashboard",
            "basic_metrics",
            "csv_upload",
            "manual_data_entry",
            "simulations",
            "simulation_unlimited",
            "copilot",
            "copilot_unlimited",
            "truth_scan",
            "stress_tests",
            "what_if",
            "sensitivity_analysis",
            "data_connectors",
            "fundraising_os",
            "cap_table",
            "board_deck",
            "hiring_planner",
            "flight_simulator",
            "document_generator",
            "ai_graphics",
            "digital_twin",
            "cross_company_learning",
            "multi_company",
            "export_pdf",
            "email_reports",
            "benchmarks",
            "fundraising_readiness",
            "investor_room",
        ],
        "highlights": [
            "Unlimited companies",
            "Unlimited everything",
            "All data connectors",
            "Flight Simulator (AI agents)",
            "Hiring Planner",
            "Document Generator",
            "AI Graphics Studio",
            "Digital Twin",
            "Investor Room",
            "Cross-company intelligence",
        ],
    },
}


def test_beta_switch_is_on_and_gated_free_tier_is_kept_for_revert():
    assert BETA_ALL_FREE is True
    assert _GATED_FREE_PLAN["max_companies"] == 1
    assert _GATED_FREE_PLAN["max_simulations_per_month"] == 3
    assert _GATED_FREE_PLAN["max_copilot_messages_per_month"] == 10
    assert _GATED_FREE_PLAN["max_connectors"] == 0
    assert "3 simulations / month" in _GATED_FREE_PLAN["highlights"]
    assert "10 copilot messages / month" in _GATED_FREE_PLAN["highlights"]
    gated = {feature.value for feature in _GATED_FREE_PLAN["features"]}
    assert Feature.TRUTH_SCAN.value not in gated
    assert Feature.SIMULATIONS.value not in gated
    assert Feature.COPILOT.value not in gated
    assert Feature.SIMULATION_UNLIMITED.value not in gated
    assert Feature.COPILOT_UNLIMITED.value not in gated


def test_paid_plan_definitions_unchanged_by_snapshot():
    for tier, expected in _PAID_SNAPSHOTS.items():
        assert _values(PLAN_DETAILS[tier]) == expected


def test_free_plan_grants_scale_features_without_caps_and_billing_highlights_say_beta():
    free = PLAN_DETAILS[PlanTier.FREE]
    scale = PLAN_DETAILS[PlanTier.SCALE]
    held = {feature.value for feature in BETA_EXCLUDED_FEATURES}
    assert held == {"data_connectors", "email_reports", "cross_company_learning"}
    assert [feature.value for feature in free["features"]] == [
        feature.value for feature in scale["features"] if feature.value not in held
    ]
    assert free["features"] is not scale["features"]
    assert free["max_companies"] == -1
    assert free["max_simulations_per_month"] == -1
    assert free["max_copilot_messages_per_month"] == -1
    assert free["max_connectors"] == -1
    assert free["price_monthly"] == 0
    joined = " ".join(free["highlights"]).lower()
    assert "3 simulations" not in joined
    assert "10 copilot" not in joined
    assert "every feature free during public beta" in joined
    assert "no card, no trial" in joined
    for feature in Feature:
        if feature in BETA_EXCLUDED_FEATURES:
            assert not has_feature(PlanTier.FREE, feature), feature
            assert not beta_grants_feature(feature)
            continue
        assert has_feature(PlanTier.FREE, feature), feature
        assert beta_grants_feature(feature)
        assert minimum_plan_for_feature(feature) == PlanTier.FREE
    assert minimum_plan_for_feature(Feature.DATA_CONNECTORS) == PlanTier.GROWTH
    assert minimum_plan_for_feature(Feature.EMAIL_REPORTS) == PlanTier.GROWTH
    assert minimum_plan_for_feature(Feature.CROSS_COMPANY_LEARNING) == PlanTier.SCALE
    assert has_feature(PlanTier.GROWTH, Feature.DATA_CONNECTORS)
    assert has_feature(PlanTier.GROWTH, Feature.EMAIL_REPORTS)
    assert not has_feature(PlanTier.GROWTH, Feature.CROSS_COMPANY_LEARNING)
    assert has_feature(PlanTier.SCALE, Feature.CROSS_COMPANY_LEARNING)

    # The in-app billing page renders these highlights from GET /billing/plans.
    payload = billing.get_plans()
    listed = {plan["id"]: plan for plan in payload["plans"]}
    assert "3 simulations / month" not in listed["free"]["highlights"]
    assert "10 copilot messages / month" not in listed["free"]["highlights"]
    assert listed["free"]["highlights"] == free["highlights"]
    assert listed["free"]["max_simulations_per_month"] == -1
    assert listed["free"]["max_copilot_messages_per_month"] == -1
    assert listed["free"]["max_companies"] == -1
    assert listed["free"]["features"] == [feature.value for feature in free["features"]]
    assert "data_connectors" not in listed["free"]["features"]
    assert "email_reports" not in listed["free"]["features"]
    assert "cross_company_learning" not in listed["free"]["features"]
    assert listed["starter"]["highlights"] == _PAID_SNAPSHOTS["starter"]["highlights"]
    assert listed["growth"]["price_monthly"] == 49
    assert listed["scale"]["price_monthly"] == 99


def _subscription_session():
    """Empty subscriptions table: a user with no row is a fresh free account."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, created_at TIMESTAMP)"
        ))
        conn.execute(text("""
            CREATE TABLE subscriptions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                plan VARCHAR,
                status VARCHAR,
                current_period_end TIMESTAMP,
                trial_start TIMESTAMP,
                trial_end TIMESTAMP,
                stripe_subscription_id VARCHAR,
                created_at TIMESTAMP
            )
        """))
    return sessionmaker(bind=engine)


def _auth_cookie(user_id: int = 1) -> dict:
    return {AUTH_COOKIE_NAME: create_access_token({"sub": str(user_id)})}


@pytest.fixture
def subscription_db(monkeypatch):
    Session = _subscription_session()
    monkeypatch.setenv("PAYWALL_ENABLED", "true")
    monkeypatch.setenv("PAYWALL_GRANDFATHER_BEFORE", "")
    monkeypatch.setattr("server.core.subscription.SessionLocal", Session)
    return Session


def test_fresh_free_user_subscription_is_the_free_plan(subscription_db):
    db = subscription_db()
    try:
        sub = get_user_subscription(db, 1)
    finally:
        db.close()
    assert sub["plan"] == PlanTier.FREE
    assert sub["effective_plan"] == PlanTier.FREE
    assert sub["status"] == "none"
    assert sub["grandfathered"] is False


def test_require_feature_returns_access_for_every_feature(subscription_db):
    """check_feature_access is the per-endpoint require_feature path."""
    app = FastAPI()

    def _allow(feature: str):
        def endpoint(_ok=Depends(check_feature_access(feature))):
            return {"ok": True, "feature": feature}
        return endpoint

    for feature in Feature:
        app.add_api_route(
            f"/locked/{feature.value}",
            _allow(feature.value),
            methods=["POST"],
        )

    user = SimpleNamespace(id=1, is_master=False, email="free@example.com")
    app.dependency_overrides[get_db] = lambda: subscription_db()
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    for feature in Feature:
        response = client.post(f"/locked/{feature.value}")
        if feature in BETA_EXCLUDED_FEATURES:
            assert response.status_code == 403, response.text
            assert response.json()["detail"]["error"] == "feature_locked"
            continue
        assert response.status_code == 200, response.text
        assert "feature_locked" not in response.text


def test_billing_feature_access_is_open_for_a_fresh_free_user(subscription_db):
    app = FastAPI()
    app.include_router(billing.router)
    user = SimpleNamespace(id=1, is_master=False, email="free@example.com")
    app.dependency_overrides[get_db] = lambda: subscription_db()
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    for feature in Feature:
        response = client.get(f"/billing/feature-access/{feature.value}")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["current_plan"] == PlanTier.FREE
        if feature in BETA_EXCLUDED_FEATURES:
            assert body["has_access"] is False
            continue
        assert body["has_access"] is True
        assert "feature_locked" not in response.text


def test_fresh_free_user_gets_200_on_truth_scan_simulation_chat_and_quick_chat(
    subscription_db, monkeypatch
):
    """Paywall on, no subscription row. These four must not 403."""
    # Call the underlying setup, not the pytest fixture wrapper.
    _llm_sink_fixture.__wrapped__(monkeypatch)
    monkeypatch.setattr(
        "server.services.activation.posthog_capture",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        "server.utils.websocket_broadcast.broadcast_truth_scan_update_sync",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        "server.api.copilot.run_monte_carlo",
        lambda inputs, seed=None, **kwargs: {
            "runway": {"p50": 18.0},
            "n_simulations": getattr(inputs, "n_simulations", 1),
        },
    )

    import server.core.subscription as subscription_mod

    looked_up = []
    warnings = []
    original_lookup = subscription_mod.get_user_subscription

    def _lookup(db, user_id):
        result = original_lookup(db, user_id)
        looked_up.append(result)
        return result

    def _warning(msg, *args, **kwargs):
        rendered = msg % args if args else str(msg)
        warnings.append(rendered)

    monkeypatch.setattr(subscription_mod, "get_user_subscription", _lookup)
    monkeypatch.setattr(subscription_mod.logger, "warning", _warning)

    user = _free_user(1)
    company = _company(owner_id=1, company_id=1)
    db = RecordingDB(company=company, truth_scan=_truth_scan(1))

    app = FastAPI()
    app.add_middleware(PaywallMiddleware)
    app.include_router(copilot.router)
    app.include_router(truth_scan_api.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    @app.post("/simulator/ping")
    def _flight_simulator_ping():
        return {"ok": True}

    client = TestClient(app)
    client.cookies.set(AUTH_COOKIE_NAME, _auth_cookie(1)[AUTH_COOKIE_NAME])

    truth = client.post("/companies/1/truth/run")
    simulation = client.post("/companies/1/simulate", json={})
    chat = client.post("/companies/1/chat", json={"message": "What is my runway?"})
    quick = client.post("/companies/1/quick-chat", json={"message": "What is my runway?"})
    flight = client.post("/simulator/ping")

    for response in (truth, simulation, chat, quick, flight):
        assert response.status_code == 200, response.text
        assert "feature_locked" not in response.text

    assert looked_up, "paywall did not resolve the free account"
    assert all(row["effective_plan"] == PlanTier.FREE for row in looked_up)
    assert all(row["status"] == "none" for row in looked_up)
    assert not any("Paywall middleware error" in item for item in warnings)


def test_free_user_paywall_still_locks_data_connectors(subscription_db):
    """data_connectors stays on Growth. The beta switch does not open it."""
    app = FastAPI()
    app.add_middleware(PaywallMiddleware)

    @app.post("/connectors/ping")
    def _connectors():
        return {"ok": True}

    user = SimpleNamespace(id=1, is_master=False, email="free@example.com")
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    client.cookies.set(AUTH_COOKIE_NAME, _auth_cookie(1)[AUTH_COOKIE_NAME])
    response = client.post("/connectors/ping")
    assert response.status_code == 403, response.text
    assert response.json()["detail"]["error"] == "feature_locked"
    assert response.json()["detail"]["feature"] == Feature.DATA_CONNECTORS.value


def test_growth_plan_still_opens_data_connectors(subscription_db, monkeypatch):
    monkeypatch.setattr(
        "server.core.subscription.get_user_subscription",
        lambda db, user_id: {"effective_plan": PlanTier.GROWTH, "plan": PlanTier.GROWTH},
    )
    app = FastAPI()

    def _allow(feature: str):
        def endpoint(_ok=Depends(check_feature_access(feature))):
            return {"ok": True}
        return endpoint

    app.add_api_route("/locked/data_connectors", _allow(Feature.DATA_CONNECTORS.value), methods=["POST"])
    app.add_api_route(
        "/locked/cross_company_learning",
        _allow(Feature.CROSS_COMPANY_LEARNING.value),
        methods=["POST"],
    )
    user = SimpleNamespace(id=1, is_master=False, email="growth@example.com")
    app.dependency_overrides[get_db] = lambda: subscription_db()
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    assert client.post("/locked/data_connectors").status_code == 200
    locked = client.post("/locked/cross_company_learning")
    assert locked.status_code == 403
    assert locked.json()["detail"]["error"] == "feature_locked"
