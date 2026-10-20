"""LLM audit rows hash and preview redacted text, and they actually persist.

The model call is mocked. Nothing in this file opens a socket.
"""

from __future__ import annotations

import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.lib.privacy.pii_redactor import redact_text
from server.models.llm_audit_log import LLMAuditLog

EMAIL = "founder@example.com"
PHONE = "415-555-0199"
RAW = f"Email {EMAIL} or call {PHONE} about runway."
ECHO = f"I will reach {EMAIL} at {PHONE}."


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _redacted(text: str, mode: str = "standard") -> str:
    return redact_text(text, mode).redacted_text


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    LLMAuditLog.__table__.create(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def db(session_factory):
    session = session_factory()
    yield session
    session.close()


def _mock_http(payload: dict) -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    response.text = ""
    client = MagicMock()
    client.post.return_value = response
    return client


def _row(session) -> LLMAuditLog:
    session.expire_all()
    rows = session.query(LLMAuditLog).all()
    assert len(rows) == 1, f"expected one audit row, found {len(rows)}"
    return rows[0]


def _assert_redacted_prompt(row: LLMAuditLog, raw: str, mode: str = "standard") -> None:
    redacted = _redacted(raw, mode)
    assert redacted != raw
    assert row.prompt_hash == _hash(redacted)
    assert row.prompt_hash != _hash(raw)
    assert len(row.prompt_hash) == 64
    assert row.redacted_prompt_preview == redacted
    assert row.input_chars_original == len(raw)
    assert row.input_chars_redacted == len(redacted)
    assert row.input_chars_original != row.input_chars_redacted
    stored = " ".join(
        [
            row.prompt_hash,
            row.redacted_prompt_preview or "",
            row.redacted_output_preview or "",
            json.dumps(row.pii_findings_json),
        ]
    )
    assert EMAIL not in stored
    assert PHONE not in stored


def test_gemini_audit_hashes_redacted_prompt(db, monkeypatch):
    monkeypatch.setenv("AI_INTEGRATIONS_GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("AI_INTEGRATIONS_GEMINI_BASE_URL", "https://gemini.invalid")
    http = _mock_http(
        {
            "candidates": [{"content": {"parts": [{"text": ECHO}]}}],
            "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 7},
        }
    )
    with patch("server.lib.llm.gemini_client.httpx.Client", return_value=http):
        from server.lib.llm.gemini_client import GeminiClient

        client = GeminiClient(db_session=db, company_id=7, user_id=9, pii_mode="standard")
        result = client.chat_completion(
            messages=[{"role": "user", "content": RAW}],
            model="gemini-2.5-flash",
        )

    assert result["audit_log_id"] is not None
    sent = json.dumps(http.post.call_args.kwargs["json"])
    assert EMAIL not in sent and PHONE not in sent
    row = _row(db)
    _assert_redacted_prompt(row, RAW)
    assert row.redacted_output_preview == _redacted(ECHO)
    assert row.endpoint.startswith("/models/")
    assert row.model == "gemini-2.5-flash"
    assert row.company_id == 7
    assert row.user_id == 9


def test_perplexity_search_audit_hashes_redacted_prompt(db, monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
    http = _mock_http(
        {
            "choices": [{"message": {"content": ECHO}}],
            "citations": ["https://example.invalid/source"],
            "usage": {"prompt_tokens": 8, "completion_tokens": 4},
        }
    )
    with patch("server.lib.llm.perplexity_client.httpx.Client", return_value=http):
        from server.lib.llm.perplexity_client import PerplexityClient

        client = PerplexityClient(db_session=db, pii_mode="standard")
        result = client.search(RAW, model="sonar")

    assert result["audit_log_id"] is not None
    sent = json.dumps(http.post.call_args.kwargs["json"])
    assert EMAIL not in sent and PHONE not in sent
    row = _row(db)
    _assert_redacted_prompt(row, RAW)
    assert row.redacted_output_preview == _redacted(ECHO)
    assert row.endpoint == "/chat/completions"
    assert row.model == "sonar"


def test_perplexity_chat_audit_hashes_redacted_prompt(db, monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
    http = _mock_http(
        {
            "choices": [{"message": {"content": ECHO}}],
            "citations": [],
            "usage": {"prompt_tokens": 8, "completion_tokens": 4},
        }
    )
    with patch("server.lib.llm.perplexity_client.httpx.Client", return_value=http):
        from server.lib.llm.perplexity_client import PerplexityClient

        client = PerplexityClient(db_session=db, pii_mode="standard")
        result = client.chat([{"role": "user", "content": RAW}], model="sonar")

    assert result["audit_log_id"] is not None
    row = _row(db)
    _assert_redacted_prompt(row, RAW)
    assert row.redacted_output_preview == _redacted(ECHO)


def test_image_generator_audit_hashes_redacted_prompt(db, monkeypatch):
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "https://openai.invalid")
    http = _mock_http({"data": [{"b64_json": "aW1hZ2U="}]})
    with patch("server.lib.llm.image_generator.httpx.Client", return_value=http):
        from server.lib.llm.image_generator import STYLE_PREFIXES, NanoBananaImageGenerator

        client = NanoBananaImageGenerator(db_session=db, company_id=3, user_id=4)
        result = client.generate_image(RAW, style="professional", aspect_ratio="1:1")

    assert result["audit_log_id"] is not None
    assert result["image_base64"] == "aW1hZ2U="
    sent = json.dumps(http.post.call_args.kwargs["json"])
    assert EMAIL not in sent and PHONE not in sent
    full_prompt = f"{STYLE_PREFIXES['professional']}{RAW}"
    row = _row(db)
    _assert_redacted_prompt(row, full_prompt)
    assert row.redacted_output_preview == "[image_generated]"
    assert row.model == "gpt-image-1"
    assert row.company_id == 3
    assert row.user_id == 4
    assert EMAIL not in (row.redacted_prompt_preview or "")
    assert PHONE not in (row.redacted_prompt_preview or "")


def test_openrouter_audit_row_persists_redacted(db, session_factory, monkeypatch):
    monkeypatch.setenv("AI_INTEGRATIONS_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("AI_INTEGRATIONS_OPENROUTER_BASE_URL", "https://openrouter.invalid")
    system = f"Help the founder at {EMAIL}."
    user = f"Call {PHONE} about runway."
    raw = f"{system}\n{user}"
    redacted = "\n".join([_redacted(system), _redacted(user)])
    http = _mock_http(
        {
            "choices": [{"message": {"content": ECHO}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17},
        }
    )
    with patch("server.lib.llm.openrouter_client.httpx.Client", return_value=http):
        from server.lib.llm.openrouter_client import OpenRouterClient

        client = OpenRouterClient(db_session=db, company_id=1, user_id=2, pii_mode="standard")
        result = client.chat_completion(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            model="grok-4.1-fast",
        )

    assert result["audit_log_id"] is not None
    sent = json.dumps(http.post.call_args.kwargs["json"])
    assert EMAIL not in sent and PHONE not in sent

    row = _row(db)
    assert row.prompt_hash == _hash(redacted)
    assert row.prompt_hash != _hash(raw)
    assert row.redacted_prompt_preview == redacted
    assert row.input_chars_original == len(raw)
    assert row.input_chars_redacted == len(redacted)
    assert row.redacted_output_preview == _redacted(ECHO)
    assert row.endpoint == "chat/completions"
    assert row.model == "x-ai/grok-4.1-fast"
    assert row.pii_mode == "standard"
    assert row.tokens_in == 12
    assert row.tokens_out == 5
    stored = " ".join(
        [
            row.prompt_hash,
            row.redacted_prompt_preview or "",
            row.redacted_output_preview or "",
            json.dumps(row.pii_findings_json),
        ]
    )
    assert EMAIL not in stored
    assert PHONE not in stored

    fresh = session_factory()
    try:
        saved = fresh.query(LLMAuditLog).one()
        assert saved.id == row.id
        assert saved.prompt_hash == row.prompt_hash
        assert saved.redacted_prompt_preview == redacted
        assert EMAIL not in (saved.redacted_prompt_preview or "")
        assert PHONE not in (saved.redacted_prompt_preview or "")
        assert saved.input_chars_original == len(raw)
    finally:
        fresh.close()


def test_image_generator_redaction_failure_never_sends_or_stores_raw_prompt(db, monkeypatch):
    """A redaction error must refuse the call. The raw prompt is not sent or stored."""
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "https://openai.invalid")
    secret = "board-leak@example.com"
    prompt = f"Investor slide for {secret}"
    http = _mock_http({"data": [{"b64_json": "aW1hZ2U="}]})

    def _boom(*_args, **_kwargs):
        raise RuntimeError("redactor down")

    with patch("server.lib.llm.image_generator.httpx.Client", return_value=http), patch(
        "server.lib.privacy.pii_redactor.redact_text", side_effect=_boom
    ):
        from server.lib.llm.image_generator import NanoBananaImageGenerator

        client = NanoBananaImageGenerator(db_session=db, company_id=3, user_id=4)
        result = client.generate_image(prompt, style="minimal", aspect_ratio="1:1")

    assert http.post.call_count == 0
    assert secret not in json.dumps(http.mock_calls, default=str)
    body = json.dumps(result)
    assert secret not in body
    assert prompt not in body
    assert result["image_base64"] is None
    assert result["prompt_used"] is None
    assert "redaction failed" in (result.get("error") or "")

    db.expire_all()
    rows = db.query(LLMAuditLog).all()
    assert rows == []
    pending = " ".join(json.dumps(obj.__dict__, default=str) for obj in db.new)
    assert secret not in pending
    assert prompt not in pending


def test_smart_chat_redacts_query_and_context_before_gemini(db, monkeypatch):
    """POST /llm/smart-chat must not send or audit a raw email from the query or context."""
    from types import SimpleNamespace

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from server.api import llm as llm_api
    from server.core.db import get_db
    from server.core.security import get_current_user
    from server.lib.llm.gemini_client import truncate_preview
    from server.lib.llm.intent_classifier import CLASSIFIER_SYSTEM_PROMPT

    query_email = "founder.query@example.com"
    context_email = "ada.context@example.com"
    query = f"Summarize the board notes for {query_email}"
    context = f"The founder inbox is {context_email} and the round is quiet."

    monkeypatch.setenv("AI_INTEGRATIONS_GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("AI_INTEGRATIONS_GEMINI_BASE_URL", "https://gemini.invalid")
    for key in (
        "PERPLEXITY_API_KEY",
        "OPENAI_API_KEY",
        "AI_INTEGRATIONS_OPENAI_API_KEY",
        "AI_INTEGRATIONS_OPENAI_BASE_URL",
        "ANTHROPIC_API_KEY",
        "AI_INTEGRATIONS_ANTHROPIC_API_KEY",
        "AI_INTEGRATIONS_ANTHROPIC_BASE_URL",
        "AI_INTEGRATIONS_OPENROUTER_API_KEY",
        "AI_INTEGRATIONS_OPENROUTER_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    classification = json.dumps(
        {
            "primary_intent": "general_chat",
            "confidence": 0.91,
            "secondary_intent": None,
            "requires_web_search": False,
            "requires_real_time": False,
            "complexity": "low",
            "reasoning": "simple question",
        }
    )
    http = _mock_http(
        {
            "candidates": [{"content": {"parts": [{"text": classification}]}}],
            "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 7},
        }
    )

    raw_classifier = f"{CLASSIFIER_SYSTEM_PROMPT}\nContext: {context}\n\nQuery: {query}"
    redacted_classifier = _redacted(raw_classifier)
    redacted_query = _redacted(query)
    assert query_email not in redacted_classifier
    assert context_email not in redacted_classifier
    assert redacted_classifier != raw_classifier

    app = FastAPI()
    app.include_router(llm_api.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=9)

    with patch("server.lib.llm.gemini_client.httpx.Client", return_value=http):
        response = TestClient(app).post(
            "/llm/smart-chat",
            json={"query": query, "context": context},
        )

    assert response.status_code == 200, response.text
    assert query_email not in response.text
    assert context_email not in response.text

    payloads = [json.dumps(call.kwargs.get("json", {})) for call in http.post.call_args_list]
    assert len(payloads) >= 2
    sent = "\n".join(payloads)
    assert query_email not in sent
    assert context_email not in sent
    classifier_payloads = [body for body in payloads if "Context:" in body]
    assert len(classifier_payloads) == 1
    assert _redacted(context) in classifier_payloads[0]
    assert _redacted(query) in sent

    db.expire_all()
    rows = db.query(LLMAuditLog).all()
    by_hash = {row.prompt_hash: row for row in rows}
    classifier_row = by_hash.get(_hash(redacted_classifier))
    assert classifier_row is not None
    assert classifier_row.prompt_hash != _hash(raw_classifier)
    assert classifier_row.redacted_prompt_preview == truncate_preview(redacted_classifier)
    assert classifier_row.pii_mode == "standard"
    assert query_email not in (classifier_row.redacted_prompt_preview or "")
    assert context_email not in (classifier_row.redacted_prompt_preview or "")

    query_row = by_hash.get(_hash(redacted_query))
    assert query_row is not None
    assert query_row.prompt_hash != _hash(query)
    assert query_row.redacted_prompt_preview == redacted_query
    assert query_email not in (query_row.redacted_prompt_preview or "")

    for row in rows:
        stored = " ".join(
            [
                row.prompt_hash,
                row.redacted_prompt_preview or "",
                row.redacted_output_preview or "",
                json.dumps(row.pii_findings_json),
            ]
        )
        assert query_email not in stored
        assert context_email not in stored
        assert row.prompt_hash != _hash(raw_classifier)
        assert row.prompt_hash != _hash(query)
