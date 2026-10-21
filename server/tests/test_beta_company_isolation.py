"""Company isolation still holds on routes the public beta opens.

A user of company A gets 403 or 404 on company B for simulation, Truth Scan,
and Copilot, with the paywall on and the spend guard mounted. Opening the
feature does not open the tenant.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import (
    ai_graphics,
    board_export,
    companies,
    competitors,
    copilot,
    datasets,
    doc_generator,
    simulations,
)
from server.api import truth_scan as truth_scan_api
from server.core.db import get_db
from server.core.security import AUTH_COOKIE_NAME, create_access_token, get_current_user
from server.core.spend_guard import SpendGuardMiddleware
from server.core.subscription import PaywallMiddleware
from server.tests.test_beta_all_free import _subscription_session
from server.tests.test_llm_redaction_audit import _company, _free_user, llm_sink as _llm_sink_fixture


class _Rows:
    def __init__(self, rows):
        self.rows = list(rows)

    def filter(self, *args, **kwargs):
        matched = [row for row in self.rows if all(_holds(row, clause) for clause in args)]
        return _Rows(matched)

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return list(self.rows)


def _holds(row, clause) -> bool:
    left = getattr(clause, "left", None)
    right = getattr(clause, "right", None)
    key = getattr(left, "key", None)
    if not key:
        return False
    value = getattr(right, "value", None)
    return getattr(row, key, None) == value


class TenantDB:
    """Company B belongs to user 2. Filters on id and user_id are honored."""

    def __init__(self):
        self.company = _company(owner_id=2, company_id=2)
        self.scenario = SimpleNamespace(id=9, company_id=2, name="Foreign", inputs_json={})
        self.added = []

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Company":
            return _Rows([self.company])
        if name == "Scenario":
            return _Rows([self.scenario])
        return _Rows([])

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


@pytest.fixture
def opened_app(monkeypatch):
    monkeypatch.setenv("PAYWALL_ENABLED", "true")
    monkeypatch.setenv("PAYWALL_GRANDFATHER_BEFORE", "")
    monkeypatch.setattr("server.core.subscription.SessionLocal", _subscription_session())
    monkeypatch.setattr(
        "server.api.copilot.run_monte_carlo",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("simulation ran")),
    )
    monkeypatch.setattr(
        "server.api.simulations.run_enhanced_monte_carlo",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("simulation ran")),
    )
    monkeypatch.setattr(
        "server.api.truth_scan.compute_truth_scan",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("truth scan ran")),
    )
    monkeypatch.setattr(
        "server.api.datasets.process_termina_pdf",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("termina pdf ran")),
    )

    async def _web_search_ran(*args, **kwargs):
        raise AssertionError("web search ran")

    monkeypatch.setattr("server.api.companies.search_company_info", _web_search_ran)
    monkeypatch.setattr(
        "server.lib.llm.llm_router.LLMRouter.chat",
        lambda self, *args, **kwargs: (_ for _ in ()).throw(AssertionError("digest llm ran")),
    )
    monkeypatch.setattr(
        "server.core.spend_guard.user_may_charge_company",
        lambda user_id, company_id: False,
    )

    sinks = _llm_sink_fixture.__wrapped__(monkeypatch)
    stranger = _free_user(1)
    db = TenantDB()
    app = FastAPI()
    app.add_middleware(PaywallMiddleware)
    app.add_middleware(SpendGuardMiddleware)
    app.include_router(copilot.router)
    app.include_router(truth_scan_api.router)
    app.include_router(simulations.router)
    app.include_router(ai_graphics.router)
    app.include_router(doc_generator.router)
    app.include_router(board_export.router)
    app.include_router(datasets.router)
    app.include_router(companies.router)
    app.include_router(competitors.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: stranger
    client = TestClient(app)
    client.cookies.set(AUTH_COOKIE_NAME, create_access_token({"sub": "1"}))
    return client, db, sinks


def test_company_a_cannot_use_company_b_sim_truth_scan_or_copilot(opened_app):
    client, db, sinks = opened_app
    cases = [
        ("/companies/2/simulate", {}),
        ("/scenarios/9/simulate", {}),
        ("/companies/2/truth/run", None),
        ("/companies/2/chat", {"message": "What is my runway?"}),
        ("/companies/2/quick-chat", {"message": "What is my runway?"}),
        ("/companies/2/ai-graphics/generate", {"prompt": "runway chart"}),
        ("/companies/2/doc-generator/generate", {"doc_type": "investor-update"}),
        ("/companies/2/board-export/generate", {"templateId": "board-pack"}),
    ]
    for path, payload in cases:
        if payload is None:
            response = client.post(path)
        else:
            response = client.post(path, json=payload)
        assert response.status_code in (403, 404), (path, response.status_code, response.text)
        assert "feature_locked" not in response.text

    pdf = client.post(
        "/companies/2/datasets/termina-pdf",
        files={"file": ("deck.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert pdf.status_code in (403, 404), pdf.text
    assert "feature_locked" not in pdf.text

    web = client.post("/companies/2/web-search")
    assert web.status_code in (403, 404), web.text
    assert "feature_locked" not in web.text

    digest = client.get("/companies/2/competitors/digest")
    assert digest.status_code in (403, 404), digest.text
    assert "feature_locked" not in digest.text
    assert db.added == []
    sink, other = sinks
    assert sink == [] and other == []
