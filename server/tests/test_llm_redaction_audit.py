"""Paid-plan LLM paths must redact founder PII and write llm_audit_logs.

Covers the main copilot chat, quick-chat, and simulation_v2. Every provider
call is mocked. Nothing in this module opens a socket.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import copilot, simulation_v2
from server.core.db import get_db
from server.core.plans import PlanTier
from server.core.security import get_current_user
from server.lib.llm.openai_client import AuditedOpenAIClient
from server.models.llm_audit_log import LLMAuditLog
from server.services.simulation.engine import SimulationEngine

EMAIL = "founder@secret.co"
PHONE = "415-555-0199"
PII_MESSAGE = f"What is my revenue? Email {EMAIL} or call {PHONE}"


class _Query:
    def __init__(self, one=None, many=None):
        self._one = one
        self._many = [] if many is None else many

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def first(self):
        return self._one

    def all(self):
        return list(self._many)


class RecordingDB:
    """Session stand-in that records llm_audit_logs rows and answers lookups."""

    def __init__(self, company=None, truth_scan=None):
        self.company = company
        self.truth_scan = truth_scan
        self.added = []
        self.closed = False

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Company":
            return _Query(self.company)
        if name == "TruthScan":
            return _Query(self.truth_scan)
        return _Query(None)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        return None

    def rollback(self):
        return None

    def refresh(self, obj):
        return None

    def close(self):
        self.closed = True

    def expire(self, *args, **kwargs):
        return None


class _FakeUsage:
    prompt_tokens = 11
    completion_tokens = 7
    total_tokens = 18


class _FakeResponse:
    def __init__(self, content):
        message = SimpleNamespace(content=content)
        self.choices = [SimpleNamespace(message=message)]
        self.usage = _FakeUsage()
        self.model = "gpt-5"


class _FakeCompletions:
    def __init__(self, sink):
        self.sink = sink

    def create(self, **kwargs):
        self.sink.append(kwargs)
        return _FakeResponse("Revenue is steady. No new figures.")


class _FakeChat:
    def __init__(self, sink):
        self.completions = _FakeCompletions(sink)


class _FakeOpenAI:
    def __init__(self, sink):
        self.chat = _FakeChat(sink)


def _free_user(user_id: int = 1):
    """A founder on the free plan. Copilot must still redact and audit."""
    return SimpleNamespace(
        id=user_id,
        email=f"free-{user_id}@example.com",
        is_email_verified=True,
        is_platform_admin=False,
        role="user",
        plan=PlanTier.FREE.value,
        subscriptions=[SimpleNamespace(plan=PlanTier.FREE.value, status="active")],
    )


def _company(owner_id: int, company_id: int):
    return SimpleNamespace(
        id=company_id,
        user_id=owner_id,
        name="Northwind",
        industry="SaaS",
        stage="seed",
        currency="USD",
        metadata_json={},
    )


def _truth_scan(company_id: int):
    return SimpleNamespace(
        id=company_id,
        company_id=company_id,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        outputs_json={
            "metrics": {
                "monthly_revenue": {"value": 42000},
                "cash_balance": {"value": 250000},
                "net_burn": {"value": 18000},
            }
        },
    )


def _client(db, user) -> TestClient:
    app = FastAPI()
    app.include_router(copilot.router)
    app.include_router(simulation_v2.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _payload_blob(calls) -> str:
    return json.dumps(calls, default=str)


def _assert_pii_redacted(calls):
    blob = _payload_blob(calls)
    assert EMAIL not in blob, blob
    assert PHONE not in blob, blob
    assert "[REDACTED_EMAIL]" in blob
    assert "[REDACTED_PHONE]" in blob


def _audit_logs(db) -> list:
    return [obj for obj in db.added if isinstance(obj, LLMAuditLog)]


@pytest.fixture
def llm_sink(monkeypatch):
    sink = []
    other = []
    monkeypatch.setattr(
        "server.lib.llm.openai_client._get_client",
        lambda: _FakeOpenAI(sink),
    )

    def _disabled(*args, **kwargs):
        raise ValueError("provider disabled in test")

    monkeypatch.setattr("server.lib.llm.gemini_client.GeminiClient.__init__", _disabled)
    monkeypatch.setattr("server.lib.llm.perplexity_client.PerplexityClient.__init__", _disabled)
    monkeypatch.setattr("server.lib.llm.openrouter_client.OpenRouterClient.__init__", _disabled)

    def _anthropic(self, messages=None, system=None, **kwargs):
        other.append({"messages": messages, "system": system, **kwargs})
        return {
            "content": "Synthesized from the company data.",
            "usage": {"prompt_tokens": 4, "completion_tokens": 4},
            "model": "claude-sonnet-4-5",
        }

    monkeypatch.setattr(
        "server.lib.llm.anthropic_client.AuditedAnthropicClient.chat_completion",
        _anthropic,
    )
    monkeypatch.setattr(
        "server.copilot.ai_governance.check_budget",
        lambda *a, **k: {"within_budget": True, "remaining": None, "usage": 0.0, "budget": None},
    )

    async def _no_search(*args, **kwargs):
        return None

    monkeypatch.setattr("server.copilot.web_search.search_for_copilot", _no_search)
    monkeypatch.setattr(
        "server.copilot.context_pack.build_context_pack",
        lambda company, db: {
            "company": {
                "name": company.name,
                "industry": company.industry,
                "stage": company.stage,
                "currency": company.currency,
            },
            "truth_scan": {
                "metrics": {"monthly_revenue": {"value": 42000}},
                "computed_at": "2026-01-01",
            },
            "metrics": {"monthly_revenue": 42000},
        },
    )
    monkeypatch.setattr(
        "server.copilot.business_context.build_business_context",
        lambda company, db: {"data_gaps": []},
    )
    monkeypatch.setattr(
        "server.copilot.business_context.format_context_for_prompt",
        lambda ctx: "",
    )
    return sink, other


def test_free_plan_chat_and_quick_chat_redact_and_audit(llm_sink):
    sink, other = llm_sink
    user = _free_user(1)
    assert user.plan == PlanTier.FREE.value
    company = _company(owner_id=1, company_id=1)
    db = RecordingDB(company=company, truth_scan=_truth_scan(1))
    client = _client(db, user)

    chat = client.post("/companies/1/chat", json={"message": PII_MESSAGE})
    assert chat.status_code == 200, chat.text
    quick = client.post(
        "/companies/1/quick-chat",
        json={
            "message": PII_MESSAGE,
            "conversation_history": [
                {"role": "user", "content": f"Call me at {PHONE}. My email is {EMAIL}."}
            ],
        },
    )
    assert quick.status_code == 200, quick.text

    _assert_pii_redacted(sink + other)
    logs = _audit_logs(db)
    # One row from chat (the CFO call) and one from quick-chat.
    assert len(logs) >= 2
    for log in logs:
        preview = log.redacted_prompt_preview or ""
        assert EMAIL not in preview
        assert PHONE not in preview
        assert log.user_id == user.id
        assert log.company_id == company.id
        assert log.pii_mode == "standard"


def test_user_cannot_chat_or_quick_chat_another_company(llm_sink):
    sink, other = llm_sink
    owner = _free_user(2)
    stranger = _free_user(1)
    company_b = _company(owner_id=owner.id, company_id=2)
    db = RecordingDB(company=company_b, truth_scan=_truth_scan(2))
    client = _client(db, stranger)

    chat = client.post("/companies/2/chat", json={"message": PII_MESSAGE})
    quick = client.post("/companies/2/quick-chat", json={"message": PII_MESSAGE})
    assert chat.status_code in (403, 404), chat.text
    assert quick.status_code in (403, 404), quick.text
    assert sink == [] and other == []
    assert _audit_logs(db) == []


def test_simulation_v2_call_is_redacted_and_audited(llm_sink, monkeypatch):
    sink, _other = llm_sink
    user = _free_user(3)
    company = _company(owner_id=user.id, company_id=4)
    db = RecordingDB(company=company)
    monkeypatch.setattr(simulation_v2, "SessionLocal", lambda: db)

    async def _one_audited_call(self, *args, **kwargs):
        assert isinstance(self.llm_client, AuditedOpenAIClient)
        self.llm_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Simulate the company."},
                {"role": "user", "content": f"Founder email {EMAIL} phone {PHONE}"},
            ],
            temperature=0.7,
            max_tokens=50,
            response_format={"type": "json_object"},
        )
        raise RuntimeError("stopped after the audited call")

    monkeypatch.setattr(SimulationEngine, "run_simulation", _one_audited_call)

    client = _client(db, user)
    response = client.post("/simulation/v2/run", json={"total_rounds": 6})
    assert response.status_code == 200, response.text
    assert db.closed is True

    _assert_pii_redacted(sink)
    logs = _audit_logs(db)
    assert len(logs) == 1
    assert EMAIL not in (logs[0].redacted_prompt_preview or "")
    assert PHONE not in (logs[0].redacted_prompt_preview or "")
    assert logs[0].company_id == company.id
    assert logs[0].user_id == user.id
    assert logs[0].endpoint == "chat.completions"
    assert any(finding.get("type") == "email" for finding in (logs[0].pii_findings_json or []))
