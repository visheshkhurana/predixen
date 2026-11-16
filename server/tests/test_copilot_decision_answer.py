"""Decision-advisor questions must be answered by the model when it works.

"Should I cut ad spend?" routes to the rule-based decision advisor. Its only
model call used to be the router's synthesis, which went to ``raw_response``
(never returned), so the visible answer was the canned "Decision: ... /
Confidence: HIGH" list even with a working LLM. These tests fake the router
and check that the model's answer to the question now leads the executive
summary the copilot page renders, that the simulation numbers are unchanged,
and that the failure path still matches the rule-based fallback.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

import pytest

from server.copilot.agents.base import AgentResponse, AgentType, CompanyKnowledgeBase, ConfidenceLevel
from server.copilot.agents.router import RouterAgent
from server.copilot.llm_availability import AI_UNAVAILABLE_NOTICE
from server.tests.test_copilot_ai_unavailable import _client, _FakeRouter

DECISION_ANSWER = (
    "Not across the board: your ad channel is profitable, so trim only the campaigns "
    "whose CAC exceeds 3 months of gross margin and keep the rest running."
)
QUESTION = "Should I cut ad spend?"


class _RecordingRouter(_FakeRouter):
    """Answers every call with DECISION_ANSWER and records the prompts."""

    def __init__(self) -> None:
        super().__init__(fail=False)
        self.prompts: List[str] = []

    def chat(self, messages: Any = None, **kwargs: Any) -> dict:
        self.calls += 1
        self.prompts.append(" ".join(m.get("content", "") for m in (messages or [])))
        return {"content": DECISION_ANSWER, "model": "fake", "provider": "fake"}


def _ask(monkeypatch: pytest.MonkeyPatch, router: _FakeRouter, message: str = QUESTION) -> dict:
    resp = _client(monkeypatch, router).post("/companies/7/chat", json={"message": message})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_decision_route_leads_with_model_answer(monkeypatch: pytest.MonkeyPatch):
    router = _RecordingRouter()
    body = _ask(monkeypatch, router)

    assert body["decision_advisor"], "expected the decision-advisor route"
    assert body["llm_status"] == "ok"
    assert body["ai_unavailable"] is False
    assert body["ai_notice"] is None

    summary = body["executive_summary"]
    assert summary[0].startswith(DECISION_ANSWER)
    # the rule-based analysis is still there, below the answer
    assert any(line.startswith("Decision:") for line in summary[1:])
    # no canned confidence bullet; confidence lives in the structured fields
    assert not any(line.strip().lower().startswith("confidence:") for line in summary)
    assert body["decision_advisor"]["recommendation"]["confidence"] in {"high", "medium", "low"}
    assert body["decision_advisor"]["recommendation"]["confidence_reasoning"]

    # the founder's actual question was put to the model
    assert any(QUESTION in p for p in router.prompts)


def test_decision_simulations_unchanged_by_model_answer(monkeypatch: pytest.MonkeyPatch):
    ok = _ask(monkeypatch, _RecordingRouter())
    failed = _ask(monkeypatch, _FakeRouter(fail=True))

    assert ok["decision_advisor"]["simulations"] == failed["decision_advisor"]["simulations"]
    assert ok["decision_advisor"]["levers"] == failed["decision_advisor"]["levers"]
    rec_ok, rec_failed = ok["decision_advisor"]["recommendation"], failed["decision_advisor"]["recommendation"]
    for key in ("primary_action", "expected_impact", "alternatives"):
        assert rec_ok[key] == rec_failed[key]


def test_decision_route_failure_keeps_rule_based_fallback(monkeypatch: pytest.MonkeyPatch):
    body = _ask(monkeypatch, _FakeRouter(fail=True))

    assert body["ai_unavailable"] is True
    assert body["llm_status"] == "unavailable"
    assert body["ai_notice"] == AI_UNAVAILABLE_NOTICE
    assert body["confidence"].lower() == "low"
    summary = body["executive_summary"]
    assert summary[0].startswith("Decision:")
    assert DECISION_ANSWER not in " ".join(summary)
    assert any(line.startswith("Confidence: LOW") for line in summary)
    assert body["decision_advisor"]["recommendation"]["confidence"] == "low"


def _advisor_response() -> AgentResponse:
    advisor = {
        "levers": [{"name": "Revenue Acceleration"}],
        "simulations": [
            {"levers_applied": ["Baseline"], "runway": {"p50": 18}, "survival": {"12m": 100, "18m": 100, "24m": 90}},
            {"levers_applied": ["Revenue Acceleration"], "runway": {"p50": 24}, "survival": {"12m": 100, "18m": 100, "24m": 95}},
        ],
        "recommendation": {"primary_action": "Implement Revenue Acceleration", "confidence": "high",
                           "confidence_reasoning": "Complete financial data available"},
    }
    return AgentResponse(
        agent_type=AgentType.DECISION_ADVISOR,
        findings=["Decision: Improve financial position", "Recommendation: Implement Revenue Acceleration",
                  "Confidence: HIGH"],
        structured_output=advisor,
        confidence=ConfidenceLevel.HIGH,
        decision_advisor_output=advisor,
    )


def test_merge_without_question_or_model_keeps_rule_based_summary():
    ckb = CompanyKnowledgeBase(company_id=7, company_name="Acme")
    for agent in (RouterAgent(llm_router=None), RouterAgent(llm_router=_FakeRouter(fail=True))):
        merged = agent._merge_responses([_advisor_response()], ckb, {}, QUESTION)
        assert merged.structured_output["executive_summary"][0] == "Decision: Improve financial position"
        assert "Confidence: HIGH" in merged.structured_output["executive_summary"]
        assert merged.raw_response == RouterAgent.SYNTHESIS_FALLBACK


def test_merge_with_model_answer_leads_and_sets_raw_response():
    ckb = CompanyKnowledgeBase(company_id=7, company_name="Acme")
    merged = RouterAgent(llm_router=_RecordingRouter())._merge_responses(
        [_advisor_response()], ckb, {}, QUESTION
    )
    summary = merged.structured_output["executive_summary"]
    assert summary == [DECISION_ANSWER, "Decision: Improve financial position",
                       "Recommendation: Implement Revenue Acceleration"]
    assert merged.raw_response == DECISION_ANSWER


def test_copilot_page_shows_executive_summary_as_message_text():
    src = (Path(__file__).resolve().parents[2] / "client/src/pages/copilot.tsx").read_text()
    # the chat bubble text is the executive summary, first item first
    assert "response.executive_summary.filter(s => s && typeof s === 'string').join('\\n\\n')" in src
    assert "<DecisionAdvisorPanel advisor={response.decision_advisor} />" in src
