"""Copilot must say so when no model answered.

When every LLM call fails (no key, 401, timeout, outage) the agents fall back
to rule-based output. POST /companies/{id}/chat used to return that fallback
as confidence "high" / grounding_status "VERIFIED". These tests fake the LLM
router (success vs failure) and check the response is labelled honestly, and
that the success path is unchanged. Same for /quick-chat.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import copilot as copilot_api
from server.copilot.llm_availability import (
    AI_UNAVAILABLE_NOTICE,
    TrackedLLMRouter,
    downgrade_confidence_lines,
    downgrade_decision_advisor,
)
from server.copilot.trust import GroundingStatus
from server.core.db import get_db
from server.core.security import get_current_user

from server.tests.test_copilot_pii_mode import _Session

LLM_ANSWER = "Keep ad spend flat: CAC payback is 4 months on your verified numbers."


class _FakeRouter:
    """Stands in for LLMRouter. ``fail`` makes every model call raise."""

    def __init__(self, fail: bool):
        self.fail = fail
        self.calls = 0

    def chat(self, messages: Any = None, **kwargs: Any) -> dict:
        self.calls += 1
        if self.fail:
            raise RuntimeError("Client error '401 Unauthorized' for url 'https://api.example.test'")
        return {"content": LLM_ANSWER, "model": "fake", "provider": "fake"}

    def smart_chat(self, **kwargs: Any) -> dict:
        return self.chat()

    def web_search(self, **kwargs: Any) -> dict:
        return {"content": "", "citations": []}


async def _no_web_research(**kwargs: Any) -> None:
    return None


def _company() -> Any:
    return SimpleNamespace(
        id=7, user_id=1, name="Acme", industry="D2C", stage="seed", currency="INR",
        metadata_json={}, website=None, description=None,
    )


def _truth_scan() -> Any:
    return SimpleNamespace(
        id=3,
        company_id=7,
        created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        outputs_json={
            "metrics": {
                "monthly_revenue": 500000,
                "cash_balance": 4000000,
                "net_burn": -50000,
                "runway_months": None,
            }
        },
    )


def _client(monkeypatch: pytest.MonkeyPatch, router: _FakeRouter) -> TestClient:
    monkeypatch.setattr("server.lib.llm.llm_router.get_llm_router", lambda **kw: router)
    monkeypatch.setattr("server.copilot.web_search.search_for_copilot", _no_web_research)
    monkeypatch.setattr("server.copilot.ckb_storage.CKBStorage.save_ckb", lambda self, ckb: True)
    # Pretend the latest simulation run is verified, which is what made the
    # canned fallback come back as grounding_status=VERIFIED.
    monkeypatch.setattr(
        copilot_api,
        "fetchVerifiedRunResult",
        lambda **kw: SimpleNamespace(
            grounding_status=GroundingStatus.VERIFIED, provenance=None, outputs=None, run_id=None,
        ),
    )
    monkeypatch.setattr(
        copilot_api,
        "apply_not_available_guard",
        lambda output, status, **kw: SimpleNamespace(refused=False, output=output, grounding_status=status),
    )

    db = _Session(_company(), _truth_scan())
    # A run exists for the company, so the endpoint takes the provenance path.
    orig_query = db.query

    def query(model: Any):
        if getattr(model, "__name__", "") == "SimulationRun":
            from server.tests.test_copilot_pii_mode import _Query
            return _Query(SimpleNamespace(id=5, scenario_id=9, status="completed", created_at=None))
        return orig_query(model)

    db.query = query  # type: ignore[assignment]
    user = SimpleNamespace(id=1, email="founder@example.com", is_email_verified=True, is_active=True)

    app = FastAPI()
    app.include_router(copilot_api.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


@pytest.mark.parametrize("message", ["Should I cut ad spend?", "How much runway do we have?"])
def test_chat_labels_rule_based_fallback_when_llm_fails(monkeypatch: pytest.MonkeyPatch, message: str):
    router = _FakeRouter(fail=True)
    resp = _client(monkeypatch, router).post("/companies/7/chat", json={"message": message})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert router.calls > 0, "expected the agents to try the model"
    assert body["ai_unavailable"] is True
    assert body["llm_status"] == "unavailable"
    assert body["ai_notice"] == AI_UNAVAILABLE_NOTICE
    assert body["confidence"].lower() == "low"
    assert body["grounding_status"] != "VERIFIED"
    for line in body["executive_summary"]:
        assert "Confidence: HIGH" not in line
    advisor = body.get("decision_advisor")
    if advisor:
        assert advisor["recommendation"]["confidence"] == "low"
        # computed simulation numbers are kept
        assert "simulations" in advisor


def test_chat_success_path_is_unchanged(monkeypatch: pytest.MonkeyPatch):
    router = _FakeRouter(fail=False)
    resp = _client(monkeypatch, router).post(
        "/companies/7/chat", json={"message": "How much runway do we have?"}
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert router.calls > 0
    assert body["ai_unavailable"] is False
    assert body["ai_notice"] is None
    assert body["llm_status"] == "ok"
    assert body["grounding_status"] == "VERIFIED"
    assert LLM_ANSWER in body["executive_summary"][0]


def _quick_client(monkeypatch: pytest.MonkeyPatch, router: _FakeRouter) -> TestClient:
    client = _client(monkeypatch, router)
    monkeypatch.setattr("server.copilot.context_pack.build_context_pack", lambda company, db: {})
    monkeypatch.setattr("server.copilot.business_context.build_business_context", lambda company, db: {})
    monkeypatch.setattr("server.copilot.business_context.format_context_for_prompt", lambda ctx: "")
    monkeypatch.setattr(copilot_api, "_build_data_summary", lambda ctx: "Revenue: 500000")
    monkeypatch.setattr(copilot_api, "_guard_available_metrics", lambda db, cid, ts: {})
    monkeypatch.setattr(
        copilot_api,
        "apply_not_available_guard_to_text",
        lambda text, status, **kw: SimpleNamespace(refused=False, text=text, output={}),
    )
    return client


def test_quick_chat_says_ai_unavailable_when_llm_fails(monkeypatch: pytest.MonkeyPatch):
    router = _FakeRouter(fail=True)
    resp = _quick_client(monkeypatch, router).post(
        "/companies/7/quick-chat", json={"message": "Should I cut ad spend?"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ai_unavailable"] is True
    assert "unavailable" in body["response"].lower()


def test_quick_chat_success_path_is_unchanged(monkeypatch: pytest.MonkeyPatch):
    router = _FakeRouter(fail=False)
    resp = _quick_client(monkeypatch, router).post(
        "/companies/7/quick-chat", json={"message": "Should I cut ad spend?"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ai_unavailable"] is False
    assert body["response"] == LLM_ANSWER


def test_tracker_status_transitions():
    ok, bad = _FakeRouter(fail=False), _FakeRouter(fail=True)
    t = TrackedLLMRouter(ok)
    assert t.status == "not_used"
    t.chat(messages=[])
    assert t.status == "ok"

    t = TrackedLLMRouter(bad)
    with pytest.raises(RuntimeError):
        t.chat(messages=[])
    assert t.status == "unavailable"
    assert "401" in (t.last_error or "")

    class _Mixed:
        n = 0

        def chat(self, **kw):
            self.n += 1
            if self.n == 1:
                raise RuntimeError("timeout")
            return {"content": "x"}

    t = TrackedLLMRouter(_Mixed())
    with pytest.raises(RuntimeError):
        t.chat()
    t.chat()
    assert t.status == "partial"

    # empty content (smart_chat's swallowed-error shape) is not a success
    class _Empty:
        def smart_chat(self, **kw):
            return {"content": "", "error": "boom"}

    t = TrackedLLMRouter(_Empty())
    t.smart_chat()
    assert t.status == "unavailable"


def test_downgrade_helpers_keep_numbers():
    lines = ["Decision: X", "Baseline survival (18m): 100%", "Confidence: HIGH"]
    out = downgrade_confidence_lines(lines)
    assert out[:2] == lines[:2]
    assert out[2].startswith("Confidence: LOW")

    advisor = {"simulations": [{"runway": {"p50": 18}}], "recommendation": {"confidence": "high", "confidence_reasoning": "Complete data"}}
    out = downgrade_decision_advisor(advisor)
    assert out["recommendation"]["confidence"] == "low"
    assert "Complete data" in out["recommendation"]["confidence_reasoning"]
    assert out["simulations"] == advisor["simulations"]
    assert advisor["recommendation"]["confidence"] == "high"  # input not mutated


def test_copilot_page_renders_ai_unavailable_notice():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2] / "client/src/pages/copilot.tsx").read_text()
    assert "ai_unavailable?: boolean" in src
    assert "structuredResponse?.ai_notice" in src
    assert "from '@/components/ui/alert'" in src
