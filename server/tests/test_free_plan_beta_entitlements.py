"""Free plan beta entitlements (P0). Spec: PR #196.

Fresh free signups were 403 feature_locked on Truth Scan, simulation and
Copilot because PLAN_DETAILS[FREE] omitted those features. The same entry
already advertised 3 simulations / month and 10 Copilot messages / month,
and nothing enforced the numbers.

This test signs up a free account, enters its own financials, and checks:

- Truth Scan run is 200, and founder_activated fires with is_sample=false
- the 1st simulation is 200; the 4th simulation in the same calendar month
  is plan_limit_reached (not 403 feature_locked, not an outage)
- the simulate v2 flow is 200 while the account is still under that cap
- Copilot messages 1-10 are 200 and the 11th is the same limit refusal
- a feature Free did not gain (data connectors) is still 403 feature_locked
- Starter/Growth/Scale features, prices, limits and the Scale trial are the
  values from main

Run: .venv/bin/python -m pytest server/tests/test_free_plan_beta_entitlements.py -q
"""
from __future__ import annotations

import os
import tempfile
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from server.core.plans import PLAN_DETAILS, TRIAL_DURATION_DAYS, TRIAL_PLAN, Feature, PlanTier


# Frozen from main. A change here is a pricing or packaging change, which
# this P0 does not make.
_PAID_SNAPSHOT = {
    PlanTier.STARTER: {
        "price_monthly": 29,
        "price_annual": 290,
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
    },
    PlanTier.GROWTH: {
        "price_monthly": 49,
        "price_annual": 490,
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
    },
    PlanTier.SCALE: {
        "price_monthly": 99,
        "price_annual": 990,
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
    },
}


def _feature_values(plan: str) -> list[str]:
    return [f.value for f in PLAN_DETAILS[plan]["features"]]


def test_paid_plans_and_free_numeric_limits_match_main():
    free = PLAN_DETAILS[PlanTier.FREE]
    assert free["price_monthly"] == 0
    assert free["price_annual"] == 0
    assert free["max_companies"] == 1
    assert free["max_simulations_per_month"] == 3
    assert free["max_copilot_messages_per_month"] == 10
    assert free["max_connectors"] == 0
    assert _feature_values(PlanTier.FREE) == [
        "dashboard",
        "basic_metrics",
        "csv_upload",
        "manual_data_entry",
        "simulations",
        "copilot",
        "truth_scan",
    ]
    for still_paid in (
        Feature.DATA_CONNECTORS,
        Feature.FUNDRAISING_OS,
        Feature.SIMULATION_UNLIMITED,
        Feature.COPILOT_UNLIMITED,
        Feature.CAP_TABLE,
        Feature.STRESS_TESTS,
    ):
        assert still_paid not in free["features"]

    for tier, expected in _PAID_SNAPSHOT.items():
        live = PLAN_DETAILS[tier]
        for key, value in expected.items():
            if key == "features":
                assert _feature_values(tier) == value, tier
            else:
                assert live[key] == value, (tier, key)

    assert TRIAL_DURATION_DAYS == 30
    assert TRIAL_PLAN == PlanTier.SCALE


def _limit_detail(response) -> dict:
    body = response.json()
    detail = body.get("detail", body)
    assert isinstance(detail, dict), body
    return detail


def _assert_limit(response, limit_key: str):
    assert response.status_code == 402, response.text
    detail = _limit_detail(response)
    assert detail["error"] == "plan_limit_reached"
    assert detail["error"] != "feature_locked"
    assert detail["limit"] == limit_key
    message = detail["message"].lower()
    assert "temporarily unavailable" not in message
    assert "session" not in message
    assert "expired" not in message
    assert response.status_code != 403


@pytest.fixture
def free_client(monkeypatch):
    """App slice on sqlite, paywall on, email and LLM calls stubbed."""
    fd, path = tempfile.mkstemp(prefix="free-plan-", suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    import server.models  # noqa: F401 - register every mapper the routers touch
    from server.models.analytics_event import AnalyticsEvent
    from server.models.benchmark import Benchmark
    from server.models.company import Company
    from server.models.company_state import CompanyState
    from server.models.customer import CustomerRecord
    from server.models.financial import FinancialRecord, ImportSession
    from server.models.login_history import LoginHistory
    from server.models.metric_snapshot import MetricSnapshot
    from server.models.scenario import Scenario
    from server.models.session_revocation import RevokedAccessToken, UserSessionCutoff
    from server.models.simulation_run import SimulationRun
    from server.models.subscription import Subscription
    from server.models.transaction import TransactionRecord
    from server.models.truth_scan import TruthScan
    from server.models.user import EmailVerificationToken, RefreshToken, User

    tables = [
        User.__table__,
        RefreshToken.__table__,
        EmailVerificationToken.__table__,
        LoginHistory.__table__,
        RevokedAccessToken.__table__,
        UserSessionCutoff.__table__,
        Company.__table__,
        CompanyState.__table__,
        ImportSession.__table__,
        FinancialRecord.__table__,
        TransactionRecord.__table__,
        CustomerRecord.__table__,
        Benchmark.__table__,
        TruthScan.__table__,
        Scenario.__table__,
        SimulationRun.__table__,
        Subscription.__table__,
        AnalyticsEvent.__table__,
        MetricSnapshot.__table__,
    ]
    User.metadata.create_all(engine, tables=tables)
    # Production adds these with a migration; the paywall SELECT names them.
    # Without the columns the middleware errors and fails open, which would
    # hide a missing feature.
    with engine.begin() as conn:
        conn.exec_driver_sql("ALTER TABLE subscriptions ADD COLUMN trial_start TIMESTAMP")
        conn.exec_driver_sql("ALTER TABLE subscriptions ADD COLUMN trial_end TIMESTAMP")
    Session = sessionmaker(bind=engine)

    monkeypatch.setenv("PAYWALL_ENABLED", "true")
    monkeypatch.delenv("PAYWALL_GRANDFATHER_BEFORE", raising=False)
    monkeypatch.setattr("server.core.subscription.SessionLocal", Session)

    captured: list[tuple] = []

    def _capture(event, distinct_id, properties=None):
        captured.append((event, distinct_id, dict(properties or {})))
        return True

    monkeypatch.setattr("server.services.activation.posthog_capture", _capture)
    monkeypatch.setattr(
        "server.utils.websocket_broadcast.broadcast_truth_scan_update_sync",
        lambda *a, **k: False,
    )
    monkeypatch.setattr(
        "server.utils.websocket_broadcast.broadcast_metric_update_sync",
        lambda *a, **k: False,
    )

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("server.email.service.send_email_verification", _noop)
    monkeypatch.setattr("server.email.service.send_slack_signup_notification", _noop)
    monkeypatch.setattr("server.email.onboarding_sequence.enroll_new_signup", _noop)

    from server.services.simulation.types import (
        SimulationConfig,
        SimulationResult,
        SimulationStatus,
    )

    class _Engine:
        def __init__(self, llm_client, model="gpt-5-mini"):
            self.llm_client = llm_client

        async def run_simulation(
            self,
            initial_state,
            scenario_params,
            total_rounds=24,
            progress_callback=None,
            event_callback=None,
        ):
            return SimulationResult(
                simulation_id="sim_test",
                config=SimulationConfig(
                    simulation_id="sim_test",
                    total_rounds=total_rounds,
                    initial_state=initial_state,
                    agents=[],
                ),
                final_state=initial_state,
                status=SimulationStatus.COMPLETED,
                rounds=[],
                all_actions=[],
                report={"summary": "ok"},
            )

    monkeypatch.setattr("server.api.simulation_v2.SimulationEngine", _Engine)
    monkeypatch.setattr("server.api.simulation_v2.get_openai_client", lambda: object())

    from server.api.copilot import CopilotChatResponse

    async def _copilot_ok(*args, **kwargs):
        return CopilotChatResponse(
            executive_summary=["Runway looks fine for a first pass."],
            company_snapshot=["Northwind"],
            assumptions=[],
            risks=[],
            next_questions=["What is my runway?"],
            confidence="High",
        )

    monkeypatch.setattr("server.api.copilot._copilot_chat_inner", _copilot_ok)

    from server.api import auth, companies, copilot, simulation_v2, simulations, truth_scan
    from server.core.db import get_db
    from server.core.subscription import PaywallMiddleware

    app = FastAPI()
    app.add_middleware(PaywallMiddleware)
    app.include_router(auth.router)
    app.include_router(companies.router)
    app.include_router(truth_scan.router)
    app.include_router(simulations.router)
    app.include_router(simulation_v2.router)
    app.include_router(copilot.router)

    @app.post("/connectors/probe")
    def connectors_probe():
        return {"ok": True}

    def _db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)
    try:
        yield client, Session, captured
    finally:
        client.close()
        engine.dispose()
        os.remove(path)


def test_fresh_free_account_can_scan_simulate_and_chat_within_limits(free_client):
    client, Session, captured = free_client
    from server.core.security import AUTH_COOKIE_NAME
    from server.models.financial import FinancialRecord
    from server.models.subscription import Subscription

    signup = client.post(
        "/auth/register",
        json={
            "email": "free-beta@example.com",
            "password": "free-plan-1",
            "name": "Free Founder",
        },
    )
    assert signup.status_code == 200, signup.text
    token = signup.json()["access_token"]
    user_id = signup.json()["user_id"]
    client.cookies.set(AUTH_COOKIE_NAME, token)
    headers = {"Authorization": f"Bearer {token}"}

    db = Session()
    assert db.query(Subscription).filter(Subscription.user_id == user_id).count() == 0
    db.close()

    # Paywall is on: a feature Free did not gain is still locked.
    locked = client.post("/connectors/probe", headers=headers)
    assert locked.status_code == 403, locked.text
    assert _limit_detail(locked)["error"] == "feature_locked"

    company = client.post(
        "/companies",
        json={"name": "Northwind", "industry": "saas", "stage": "seed"},
        headers=headers,
    )
    assert company.status_code == 200, company.text
    company_id = company.json()["id"]

    db = Session()
    db.add(FinancialRecord(
        company_id=company_id,
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
        revenue=8000,
        cogs=1600,
        opex=12000,
        payroll=18000,
        other_costs=2000,
        cash_balance=500000,
    ))
    db.commit()
    db.close()

    scan = client.post(f"/companies/{company_id}/truth/run", headers=headers)
    assert scan.status_code == 200, scan.text
    assert scan.json().get("metrics", {}).get("monthly_revenue") == 8000
    activated = [c for c in captured if c[0] == "founder_activated"]
    assert len(activated) == 1
    assert activated[0][2]["is_sample"] is False
    assert activated[0][2]["company_id"] == company_id

    scenario = client.post(
        f"/companies/{company_id}/scenarios",
        json={"name": "Hire 5 engineers"},
        headers=headers,
    )
    assert scenario.status_code == 200, scenario.text
    scenario_id = scenario.json()["id"]

    def simulate():
        return client.post(
            f"/scenarios/{scenario_id}/simulate",
            json={"n_sims": 100, "seed": 1},
            headers=headers,
        )

    first = simulate()
    assert first.status_code == 200, first.text
    assert "feature_locked" not in first.text

    # v2 is the /simulate page. It shares the 3/month cap and must not 403.
    v2 = client.post("/simulation/v2/run", json={"total_rounds": 6}, headers=headers)
    assert v2.status_code == 200, v2.text
    assert "feature_locked" not in v2.text

    second = simulate()
    assert second.status_code == 200, second.text

    fourth = simulate()
    _assert_limit(fourth, "max_simulations_per_month")
    assert _limit_detail(fourth)["max"] == 3
    assert _limit_detail(fourth)["used"] == 3

    for n in range(1, 11):
        chat = client.post(
            f"/companies/{company_id}/chat",
            json={"message": f"What is my runway? ({n})"},
            headers=headers,
        )
        assert chat.status_code == 200, chat.text
        assert "feature_locked" not in chat.text

    eleventh = client.post(
        f"/companies/{company_id}/chat",
        json={"message": "What is my runway? (11)"},
        headers=headers,
    )
    _assert_limit(eleventh, "max_copilot_messages_per_month")
    assert _limit_detail(eleventh)["max"] == 10
    assert _limit_detail(eleventh)["used"] == 10
