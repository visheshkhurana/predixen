"""Client pii_mode cannot turn redaction off.

POST /companies/{id}/chat must redact emails even when the body asks for
pii_mode="off" or an unknown mode. The text handed to the LLM and the
llm_audit_logs row both store the redacted form.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import copilot as copilot_api
from server.api.copilot import PrivacySettings
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.llm_audit_log import LLMAuditLog

RAW_EMAIL = "jane.doe@example.com"
REDACTED = "[REDACTED_EMAIL]"
MESSAGE = f"How much runway do we have? Contact {RAW_EMAIL}"


class _Query:
    def __init__(self, value: Any):
        self.value = value

    def filter(self, *args: Any, **kwargs: Any) -> "_Query":
        return self

    def order_by(self, *args: Any, **kwargs: Any) -> "_Query":
        return self

    def join(self, *args: Any, **kwargs: Any) -> "_Query":
        return self

    def limit(self, *args: Any, **kwargs: Any) -> "_Query":
        return self

    def first(self) -> Any:
        if isinstance(self.value, list):
            return self.value[0] if self.value else None
        return self.value

    def all(self) -> list:
        if self.value is None:
            return []
        if isinstance(self.value, list):
            return list(self.value)
        return [self.value]


class _Session:
    """Enough of a Session for chat plus the audit rows the LLM client inserts."""

    def __init__(self, company: Any, truth_scan: Any):
        self.company = company
        self.truth_scan = truth_scan
        self.added: list = []

    def query(self, model: Any) -> _Query:
        name = getattr(model, "__name__", "")
        if name == "Company":
            return _Query(self.company)
        if name == "TruthScan":
            return _Query(self.truth_scan)
        if name == "LLMAuditLog":
            return _Query(list(self.added))
        return _Query(None)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def refresh(self, obj: Any) -> None:
        return None

    def expire(self, *args: Any, **kwargs: Any) -> None:
        return None


class _Usage:
    prompt_tokens = 12
    completion_tokens = 6
    total_tokens = 18


class _Completion:
    def __init__(self, captured: list):
        self.captured = captured

    def create(self, **kwargs: Any) -> Any:
        self.captured.append(kwargs)
        message = SimpleNamespace(content="Runway is about 18 months on the verified metrics.")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=_Usage(), model="gpt-5")


class _FakeOpenAI:
    def __init__(self, captured: list):
        self.chat = SimpleNamespace(completions=_Completion(captured))


class _FakeHttpResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "content": [{"type": "text", "text": "Runway is about 18 months on the verified metrics."}],
            "usage": {"input_tokens": 4, "output_tokens": 4},
            "model": "claude-sonnet-4-5",
        }


class _FakeHttpClient:
    def __init__(self, captured: list, *args: Any, **kwargs: Any):
        self.captured = captured

    def __enter__(self) -> "_FakeHttpClient":
        return self

    def __exit__(self, *args: Any) -> bool:
        return False

    def post(self, url: str, json: Any = None, headers: Any = None, **kwargs: Any) -> _FakeHttpResponse:
        self.captured.append({"url": url, "json": json})
        return _FakeHttpResponse()

    def close(self) -> None:
        return None


def _llm_text(openai_calls: list, http_calls: list) -> str:
    parts: list[str] = []
    for call in openai_calls:
        for msg in call.get("messages") or []:
            content = msg.get("content")
            if isinstance(content, str):
                parts.append(content)
    for call in http_calls:
        body = call.get("json") or {}
        system = body.get("system")
        if isinstance(system, str):
            parts.append(system)
        for msg in body.get("messages") or []:
            content = msg.get("content")
            if isinstance(content, str):
                parts.append(content)
    return "\n".join(parts)


@pytest.mark.parametrize("raw", ["off", "OFF", "", "   ", None, "bogus"])
def test_privacy_settings_coerces_unsafe_pii_mode(raw: Any):
    assert PrivacySettings(pii_mode=raw).pii_mode == "standard"


def test_privacy_settings_keeps_strict_and_standard():
    assert PrivacySettings(pii_mode="strict").pii_mode == "strict"
    assert PrivacySettings(pii_mode=" STANDARD ").pii_mode == "standard"


@pytest.mark.parametrize("pii_mode", ["off", "bogus"])
def test_chat_redacts_email_when_client_pii_mode_is_not_allowed(pii_mode: str, monkeypatch: pytest.MonkeyPatch):
    openai_calls: list = []
    http_calls: list = []

    monkeypatch.setattr(
        "server.lib.llm.openai_client._get_client",
        lambda: _FakeOpenAI(openai_calls),
    )
    monkeypatch.setattr(
        "httpx.Client",
        lambda *args, **kwargs: _FakeHttpClient(http_calls, *args, **kwargs),
    )
    monkeypatch.setattr(
        "server.copilot.ckb_storage.CKBStorage.save_ckb",
        lambda self, ckb: True,
    )
    # The audit row stores a 1000-character preview of the prompt. Keep the
    # system prompt and business context short so that preview still includes
    # the user message the redactor rewrote.
    monkeypatch.setattr("server.copilot.agents.cfo_agent.CFO_SYSTEM_PROMPT", "Advisor.")
    monkeypatch.setattr(
        "server.copilot.business_context.format_context_for_prompt",
        lambda ctx: "",
    )

    company = SimpleNamespace(
        id=7,
        user_id=1,
        name="Acme",
        industry="SaaS",
        stage="seed",
        currency="USD",
        metadata_json={},
        website=None,
        description=None,
    )
    truth_scan = SimpleNamespace(
        id=3,
        company_id=7,
        created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        outputs_json={
            "metrics": {
                "monthly_revenue": 50000,
                "cash_balance": 400000,
                "net_burn": 20000,
                "runway_months": 20,
            }
        },
    )
    db = _Session(company, truth_scan)
    user = SimpleNamespace(id=1, email="founder@example.com", is_email_verified=True, is_active=True)

    app = FastAPI()
    app.include_router(copilot_api.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    resp = TestClient(app).post(
        "/companies/7/chat",
        json={"message": MESSAGE, "privacy": {"pii_mode": pii_mode}},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["pii_mode"] == "standard"
    assert RAW_EMAIL not in resp.text

    handed_to_llm = _llm_text(openai_calls, http_calls)
    assert openai_calls or http_calls, "expected the chat endpoint to call the LLM"
    assert REDACTED in handed_to_llm
    assert RAW_EMAIL not in handed_to_llm

    rows = [row for row in db.query(LLMAuditLog).all() if isinstance(row, LLMAuditLog)]
    assert rows, "expected an llm_audit_log row"
    previews = [(row.redacted_prompt_preview or "") for row in rows]
    assert any(REDACTED in preview for preview in previews)
    assert all(RAW_EMAIL not in preview for preview in previews)
    assert all(row.pii_mode in ("standard", "strict") for row in rows)
