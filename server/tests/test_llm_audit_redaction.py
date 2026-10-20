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
