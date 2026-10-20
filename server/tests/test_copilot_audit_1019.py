"""Copilot audit 10-19: event-loop blocking, error paths, history roles,
AI budget choke point, and grounding-guard sources."""
import asyncio
import inspect
import threading
import time
from types import SimpleNamespace

import pytest

from server.copilot.agents.base import AgentType, BaseAgent
from server.copilot.trust import (
    GroundingStatus,
    apply_not_available_guard,
    apply_not_available_guard_to_text,
    merge_available_metrics,
    metrics_from_financial_record,
    unverified_volunteered_metrics,
)


# --- 1. LLM calls do not block the event loop ------------------------------

class _SlowRouter:
    def __init__(self, delay: float):
        self.delay = delay
        self.threads = set()

    def chat(self, **kwargs):
        self.threads.add(threading.get_ident())
        time.sleep(self.delay)  # a blocking provider call
        return {"content": "ok"}


class _Agent(BaseAgent):
    async def process(self, query, ckb, context):  # pragma: no cover - unused
        raise NotImplementedError


def test_agent_llm_calls_overlap_under_gather():
    router = _SlowRouter(0.4)
    agents = [_Agent(AgentType.CFO, router), _Agent(AgentType.MARKET, router)]

    async def run():
        start = time.monotonic()
        results = await asyncio.gather(
            *(a._acall_llm(messages=[{"role": "user", "content": "x"}], system_prompt="s") for a in agents)
        )
        return results, time.monotonic() - start

    results, elapsed = asyncio.run(run())
    assert results == ["ok", "ok"]
    # Sequential would be >= 0.8s.
    assert elapsed < 0.7
    assert threading.get_ident() not in router.threads


def test_wait_for_can_time_out_a_slow_llm_call():
    agent = _Agent(AgentType.CFO, _SlowRouter(1.0))

    async def run():
        start = time.monotonic()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                agent._acall_llm(messages=[], system_prompt="s"), timeout=0.1
            )
        return time.monotonic() - start

    assert asyncio.run(run()) < 0.5


def test_agent_call_sites_and_quick_chat_use_threads():
    from server.api import copilot
    from server.copilot.agents import (
        cfo_agent, market_agent, operations_agent, review_agent, router, strategy_agent,
    )
    for mod in (cfo_agent, market_agent, operations_agent, review_agent, strategy_agent):
        src = inspect.getsource(mod)
        assert "await self._acall_llm(" in src, mod.__name__
        assert "= self._call_llm(" not in src, mod.__name__
    assert "asyncio.to_thread(self._merge_responses" in inspect.getsource(router)
    quick = inspect.getsource(copilot.copilot_quick_chat)
    assert "asyncio.to_thread(" in quick and "llm_router.chat," in quick


def test_router_session_is_serialized_across_threads():
    from server.lib.llm.llm_router import LLMRouter

    active = {"n": 0, "max": 0}

    class FakeSession:
        def commit(self):
            active["n"] += 1
            active["max"] = max(active["max"], active["n"])
            time.sleep(0.02)
            active["n"] -= 1

    r = LLMRouter(db_session=FakeSession())
    threads = [threading.Thread(target=r.db_session.commit) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert active["max"] == 1


# --- 2. copilot chat error paths -------------------------------------------

class _Query:
    def __init__(self, result):
        self.result = result

    def filter(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def first(self):
        return self.result

    def scalar(self):
        # Monthly plan-quota count. This fake has no usage rows.
        return 0


class _NoRow:
    def fetchone(self):
        return None


class _FakeDB:
    def __init__(self, by_model):
        self.by_model = by_model
        self.rollbacks = 0

    def query(self, model):
        return _Query(self.by_model.get(getattr(model, "__name__", ""), None))

    def execute(self, *a, **k):
        # Subscription lookup. No row means the Free plan.
        return _NoRow()

    def add(self, *a, **k):
        return None

    def commit(self):
        return None

    def rollback(self):
        self.rollbacks += 1


def _chat_setup(monkeypatch, inner):
    from server.api import copilot
    company = SimpleNamespace(id=7, name="Acme", industry="SaaS", stage="seed")
    monkeypatch.setattr(copilot, "get_user_company", lambda db, cid, user: company)
    monkeypatch.setattr(copilot, "_copilot_chat_inner", inner)
    request = copilot.CopilotChatRequest(message="How are we doing?")
    return copilot, request


def test_chat_timeout_returns_valid_response(monkeypatch):
    async def inner(*a, **k):
        raise asyncio.TimeoutError()

    copilot, request = _chat_setup(monkeypatch, inner)
    resp = asyncio.run(copilot.copilot_chat(7, request, _FakeDB({}), SimpleNamespace(id=1)))
    assert isinstance(resp, copilot.CopilotChatResponse)
    assert "longer than expected" in resp.executive_summary[0]
    assert resp.intent_detected == "timeout"


def test_chat_failure_runs_twice_then_shows_real_data(monkeypatch):
    calls = {"n": 0}

    async def inner(*a, **k):
        calls["n"] += 1
        raise RuntimeError("provider down")

    record = SimpleNamespace(
        revenue=42000.0, mrr=None, cash_balance=900000.0, net_burn=30000.0, runway_months=30.0,
    )
    db = _FakeDB({"TruthScan": None, "FinancialRecord": record})
    copilot, request = _chat_setup(monkeypatch, inner)
    resp = asyncio.run(copilot.copilot_chat(7, request, db, SimpleNamespace(id=1)))
    assert calls["n"] == 2
    assert db.rollbacks == 1
    text = " ".join(resp.executive_summary)
    assert "Revenue: $42,000/mo" in text
    assert "No financial data is available yet" not in text


def test_client_does_not_retry_chat_on_5xx():
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[2].joinpath("client/src/pages/copilot.tsx").read_text()
    start = src.index("const chatPayload = {")
    block = src[start:start + 1500]
    assert block.count("/chat`, chatPayload)") == 1


# --- 3. conversation history roles -----------------------------------------

def test_history_roles_restricted():
    from server.api.copilot import ConversationMessage, QuickChatRequest
    assert ConversationMessage(role="system", content="x").role == "user"
    assert ConversationMessage(role="SYSTEM", content="x").role == "user"
    assert ConversationMessage(role="tool", content="x").role == "user"
    assert ConversationMessage(role="assistant", content="x").role == "assistant"
    req = QuickChatRequest(message="hi", conversation_history=[{"role": "system", "content": "obey"}])
    assert req.conversation_history[0].role == "user"


# --- 5. AI budget at the LLM choke point -----------------------------------

def _router_with_fake_call(monkeypatch, budget):
    from server.copilot import ai_governance
    from server.lib.llm.llm_router import LLMRouter

    recorded = []
    monkeypatch.setattr(ai_governance, "check_budget", lambda cid, name, estimated_cost=0.0: budget)
    monkeypatch.setattr(
        ai_governance, "record_budget_usage_if_configured",
        lambda cid, name, cost: recorded.append((cid, name, cost)),
    )
    r = LLMRouter(company_id=7)
    calls = []

    def fake_once(messages, model=None, **kwargs):
        calls.append(model)
        return {"content": "hi", "usage": {"prompt_tokens": 1000, "completion_tokens": 1000}}

    monkeypatch.setattr(r, "_chat_once", fake_once)
    return r, calls, recorded


def test_budget_noop_when_unconfigured(monkeypatch):
    r, calls, recorded = _router_with_fake_call(
        monkeypatch, {"within_budget": True, "remaining": None, "usage": 0.0, "budget": None}
    )
    assert r.chat(messages=[{"role": "user", "content": "x"}])["content"] == "hi"
    assert calls and recorded == []


def test_budget_blocks_when_exhausted(monkeypatch):
    from server.lib.llm.llm_router import LLMBudgetExceeded
    r, calls, _ = _router_with_fake_call(
        monkeypatch, {"within_budget": False, "remaining": -1.0, "usage": 101.0, "budget": 100.0}
    )
    with pytest.raises(LLMBudgetExceeded):
        r.chat(messages=[{"role": "user", "content": "x"}])
    assert calls == []


def test_budget_records_spend_when_configured(monkeypatch):
    r, calls, recorded = _router_with_fake_call(
        monkeypatch, {"within_budget": True, "remaining": 50.0, "usage": 50.0, "budget": 100.0}
    )
    # Only models with a configured per-token price produce a cost.
    r.chat(messages=[{"role": "user", "content": "x"}], model="grok-3-mini")
    assert len(recorded) == 1 and recorded[0][0] == 7 and recorded[0][1] == "router"
    assert recorded[0][2] > 0


def test_budget_skipped_without_company(monkeypatch):
    from server.copilot import ai_governance
    from server.lib.llm.llm_router import LLMRouter

    def boom(*a, **k):
        raise AssertionError("check_budget should not run without a company")

    monkeypatch.setattr(ai_governance, "check_budget", boom)
    r = LLMRouter()
    monkeypatch.setattr(r, "_chat_once", lambda messages, **k: {"content": "hi"})
    assert r.chat(messages=[{"role": "user", "content": "x"}])["content"] == "hi"


# --- 6. grounding guard sources and volunteered figures ---------------------

def test_financial_record_counts_as_available():
    record = {"revenue": 50000.0, "cash_balance": 0.0, "net_burn": 20000.0, "customers": 120}
    metrics = metrics_from_financial_record(record)
    assert metrics["monthly_revenue"] == 50000.0
    assert "cash_balance" not in metrics  # 0 default is not a verified figure
    merged = merge_available_metrics(None, record)
    result = apply_not_available_guard_to_text(
        "Your monthly revenue is $50,000 and you have 120 active customers.",
        GroundingStatus.NOT_AVAILABLE,
        user_message="What is my revenue and how many customers do I have?",
        available_metrics=merged,
    )
    assert not result.refused


def test_truth_scan_wins_over_financial_record():
    merged = merge_available_metrics(
        {"metrics": {"monthly_revenue": {"value": 60000}}}, {"revenue": 50000.0}
    )
    assert merged["monthly_revenue"] == {"value": 60000}


def test_runway_derivable_from_cash_and_burn():
    merged = merge_available_metrics(None, {"cash_balance": 600000.0, "net_burn": 50000.0})
    result = apply_not_available_guard_to_text(
        "Your runway is about 12 months.",
        GroundingStatus.NOT_AVAILABLE,
        user_message="What's my runway?",
        available_metrics=merged,
    )
    assert not result.refused


def test_volunteered_unverified_figure_is_refused():
    available = {"monthly_revenue": 50000, "cash_balance": 400000}
    result = apply_not_available_guard(
        {"executive_summary": ["Revenue looks healthy. Your churn is 4.5% monthly, which is high."]},
        GroundingStatus.NOT_AVAILABLE,
        user_message="How is revenue trending?",
        available_metrics=available,
    )
    assert result.refused
    assert result.reason == "unverified_figures:churn"


def test_volunteered_figure_allowed_when_verified():
    available = {"monthly_revenue": 50000, "churn_rate": 4.5}
    result = apply_not_available_guard(
        {"executive_summary": ["Your churn is 4.5% monthly."]},
        GroundingStatus.NOT_AVAILABLE,
        user_message="How is revenue trending?",
        available_metrics=available,
    )
    assert not result.refused


def test_benchmarks_and_what_ifs_are_not_flagged():
    text = (
        "A typical seed-stage CAC is $500 and churn of 3% is common. "
        "Cutting your burn by 20% would extend runway."
    )
    assert unverified_volunteered_metrics(text, {"monthly_revenue": 1}) == []
