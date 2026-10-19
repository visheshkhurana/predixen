"""FounderConsole is free: every user gets every feature, with no plan limits.

Pins the owner decision ("make it fully free to use"):

- a fresh user with no subscriptions row resolves to the Free plan, is active,
  and has every feature (ai_graphics, digital_twin, investor_room, ...);
- every ``max_*`` plan limit is unlimited (-1), including scenarios/simulations;
- the ``check_feature_access`` dependency and ``PaywallMiddleware`` never deny,
  even with ``PAYWALL_ENABLED=true`` in the environment;
- checkout / subscribe / start-trial return 410, while the Stripe webhook and
  the billing portal routes stay registered for legacy paid subscriptions.

Run: .venv/bin/python -m pytest server/tests/test_fully_free.py -q
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import billing
from server.core import plans
from server.core.plans import Feature, PlanTier, PLAN_DETAILS
from server.core.security import get_current_user
from server.core.subscription import (
    PaywallMiddleware,
    check_feature_access,
    get_user_subscription,
)


class _NoRowDB:
    """A db session whose subscriptions table is empty for this user."""

    def execute(self, *args, **kwargs):
        class _R:
            def fetchone(self_inner):
                return None

        return _R()


class _User:
    id = 4242
    is_master = False


def test_fresh_user_is_free_and_active(monkeypatch):
    monkeypatch.delenv("PAYWALL_GRANDFATHER_BEFORE", raising=False)
    sub = get_user_subscription(_NoRowDB(), _User.id)
    assert sub["effective_plan"] == PlanTier.FREE
    assert sub["is_active"] is True
    assert sub["is_trial"] is False


def test_free_plan_has_every_feature():
    assert plans.FREE_FOR_ALL is True
    free = PLAN_DETAILS[PlanTier.FREE]
    assert set(free["features"]) == set(Feature)
    for feature in Feature:
        assert plans.has_feature(PlanTier.FREE, feature), feature
        assert plans.has_feature("free", feature.value), feature
        # A stale or unknown plan string must not lock anyone out either.
        assert plans.has_feature("canceled-legacy", feature), feature
    # The previously Scale-only ones, named explicitly.
    for feature in ("ai_graphics", "digital_twin", "investor_room",
                    "flight_simulator", "document_generator", "hiring_planner"):
        assert plans.has_feature("free", feature)


def test_no_plan_limits():
    for key in ("max_companies", "max_simulations_per_month",
                "max_copilot_messages_per_month", "max_connectors"):
        assert PLAN_DETAILS[PlanTier.FREE][key] == plans.UNLIMITED
        assert plans.get_plan_limit("free", key) == plans.UNLIMITED
        assert plans.get_plan_limit("", key) == plans.UNLIMITED


def test_check_feature_access_never_denies():
    for feature in Feature:
        dep = check_feature_access(feature)
        assert dep(current_user=_User()) is True


def _app_with(router=None, middleware=False):
    app = FastAPI()
    if middleware:
        app.add_middleware(PaywallMiddleware)

        @app.post("/companies/1/ai-graphics")
        def _graphics():
            return {"ok": True}

        @app.post("/scenarios/7/simulate")
        def _simulate():
            return {"ok": True}

    if router is not None:
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: _User()
    return app


def test_paywall_middleware_is_inert_even_when_env_enabled(monkeypatch):
    monkeypatch.setenv("PAYWALL_ENABLED", "true")
    client = TestClient(_app_with(middleware=True))
    assert client.post("/companies/1/ai-graphics").status_code == 200
    assert client.post("/scenarios/7/simulate").status_code == 200


def test_checkout_and_trial_endpoints_are_gone():
    client = TestClient(_app_with(router=billing.router))
    for path in ("/billing/start-trial", "/billing/subscribe/starter",
                 "/billing/subscribe/scale"):
        r = client.post(path, json={"interval": "monthly"})
        assert r.status_code == 410, path
        assert "free" in r.json()["detail"].lower()


def test_plans_endpoint_lists_a_single_free_plan():
    client = TestClient(_app_with(router=billing.router))
    body = client.get("/billing/plans").json()
    assert body["free_mode"] is True
    assert body["payments_enabled"] is False
    assert [p["id"] for p in body["plans"]] == ["free"]
    assert body["plans"][0]["price_monthly"] == 0
    assert "ai_graphics" in body["plans"][0]["features"]


def test_feature_access_endpoint_always_grants():
    client = TestClient(_app_with(router=billing.router))
    body = client.get("/billing/feature-access/ai_graphics").json()
    assert body["has_access"] is True


def test_webhook_and_portal_stay_registered_for_legacy_subscriptions():
    paths = {(r.path, tuple(sorted(r.methods))) for r in billing.router.routes}
    assert ("/billing/webhook", ("POST",)) in paths
    assert ("/billing/portal", ("POST",)) in paths
