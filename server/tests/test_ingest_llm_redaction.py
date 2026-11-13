"""Ingest, extractor, and competitor LLM calls redact PII and write audit rows.

Every provider call is mocked. Nothing in this module opens a socket.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from server.api import competitors, ingest
from server.core.openai_credentials import is_missing_key_error
from server.ingest import excel_extractor, pdf_extractor
from server.models.llm_audit_log import LLMAuditLog

EMAIL = "founder@secret.co"
PHONE = "415-555-0199"
PII = f"Founder {EMAIL} phone {PHONE}"


class _Query:
    def __init__(self, one=None):
        self._one = one

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._one


class RecordingDB:
    def __init__(self, company=None):
        self.company = company
        self.added = []
        self.closed = False

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Company":
            return _Query(self.company)
        return _Query(None)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        self.closed = True


class _FakeResponse:
    def __init__(self, content):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]
        self.usage = SimpleNamespace(prompt_tokens=4, completion_tokens=3, total_tokens=7)
        self.model = "gpt-5"


def _install_openai(monkeypatch, sink, content='{"company_name": "Acme"}', raise_error=None):
    class _Completions:
        def create(self, **kwargs):
            sink.append(kwargs)
            if raise_error is not None:
                raise raise_error
            return _FakeResponse(content)

    class _OpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.chat = SimpleNamespace(completions=_Completions())

    monkeypatch.setattr("openai.OpenAI", _OpenAI)
    return _OpenAI


def _session(monkeypatch, company=None):
    db = RecordingDB(company=company)
    monkeypatch.setattr("server.core.db.SessionLocal", lambda: db)
    return db


def _clear_keys(monkeypatch):
    for name in (
        "AI_INTEGRATIONS_OPENAI_API_KEY",
        "AI_INTEGRATIONS_OPENAI_BASE_URL",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def _plain_key(monkeypatch):
    _clear_keys(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")


def _blob(calls) -> str:
    return json.dumps(calls, default=str)


def _assert_pii_redacted(calls):
    blob = _blob(calls)
    assert EMAIL not in blob, blob
    assert PHONE not in blob, blob
    assert "[REDACTED_EMAIL]" in blob
    assert "[REDACTED_PHONE]" in blob


def _logs(db):
    return [obj for obj in db.added if isinstance(obj, LLMAuditLog)]


def _assert_audit(db, company_id, user_id):
    logs = _logs(db)
    assert len(logs) >= 1
    assert db.closed is True
    for log in logs:
        preview = log.redacted_prompt_preview or ""
        assert EMAIL not in preview
        assert PHONE not in preview
        assert log.company_id == company_id
        assert log.user_id == user_id
        assert any(finding.get("type") == "email" for finding in (log.pii_findings_json or []))
    return logs


@pytest.fixture(autouse=True)
def _reset_openai_client_cache():
    import server.lib.llm.openai_client as openai_client

    previous = openai_client._client
    openai_client._client = None
    yield
    openai_client._client = previous


def test_pdf_text_extraction_redacts_and_audits(monkeypatch):
    sink = []
    _plain_key(monkeypatch)
    _install_openai(monkeypatch, sink)
    db = _session(monkeypatch)

    result = pdf_extractor.extract_metrics_with_openai(PII, company_id=42, user_id=7)

    assert result == {"company_name": "Acme"}
    _assert_pii_redacted(sink)
    _assert_audit(db, 42, 7)
    assert _logs(db)[0].endpoint == "chat.completions"


def test_pdf_vision_redacts_text_and_passes_images_through(monkeypatch):
    sink = []
    _plain_key(monkeypatch)
    _install_openai(monkeypatch, sink)
    db = _session(monkeypatch)
    monkeypatch.setattr(pdf_extractor, "VISION_EXTRACTION_PROMPT", f"Read this deck. {PII}")
    images = ["aaaa", "bbbb"]

    result = pdf_extractor.extract_metrics_with_vision(images, company_id=42, user_id=7)

    assert result == {"company_name": "Acme"}
    _assert_pii_redacted(sink)
    _assert_audit(db, 42, 7)
    assert _logs(db)[0].endpoint == "chat.completions.vision"
    image_parts = [
        item
        for call in sink
        for message in call["messages"]
        if isinstance(message.get("content"), list)
        for item in message["content"]
        if isinstance(item, dict) and item.get("type") == "image_url"
    ]
    assert [part["image_url"]["url"] for part in image_parts] == [
        "data:image/png;base64,aaaa",
        "data:image/png;base64,bbbb",
    ]
    assert all(part["image_url"]["detail"] == "high" for part in image_parts)


def test_excel_text_extraction_redacts_and_audits(monkeypatch):
    sink = []
    _plain_key(monkeypatch)
    _install_openai(monkeypatch, sink)
    db = _session(monkeypatch)

    result = excel_extractor.extract_metrics_with_openai(PII, company_id=11, user_id=4)

    assert result == {"company_name": "Acme"}
    _assert_pii_redacted(sink)
    _assert_audit(db, 11, 4)


def test_excel_summary_redacts_and_audits(monkeypatch):
    sink = []
    _plain_key(monkeypatch)
    _install_openai(monkeypatch, sink, content="Cash is healthy.")
    db = _session(monkeypatch)

    summary = excel_extractor.generate_ai_summary(
        {"revenue": 10.0, "note": PII}, company_id=11, user_id=4
    )

    assert summary == "Cash is healthy."
    _assert_pii_redacted(sink)
    _assert_audit(db, 11, 4)


def test_onboarding_text_extraction_redacts_and_audits(monkeypatch):
    sink = []
    _plain_key(monkeypatch)
    _install_openai(monkeypatch, sink, content='{"summary": "ok"}')
    db = _session(monkeypatch)

    result = ingest.extract_onboarding_data_with_openai(PII, company_id=5, user_id=9)

    assert result == {"summary": "ok"}
    _assert_pii_redacted(sink)
    _assert_audit(db, 5, 9)


def test_onboarding_vision_redacts_text_and_passes_images_through(monkeypatch):
    sink = []
    _plain_key(monkeypatch)
    _install_openai(monkeypatch, sink, content='{"summary": "ok"}')
    db = _session(monkeypatch)
    monkeypatch.setattr(ingest, "ONBOARDING_VISION_PROMPT", f"Images of a deck. {PII}")
    images = ["cccc"]

    result = ingest.extract_onboarding_data_with_vision(images, company_id=5, user_id=9)

    assert result == {"summary": "ok"}
    _assert_pii_redacted(sink)
    logs = _assert_audit(db, 5, 9)
    assert logs[0].endpoint == "chat.completions.vision"
    image_parts = [
        item
        for call in sink
        for message in call["messages"]
        if isinstance(message.get("content"), list)
        for item in message["content"]
        if isinstance(item, dict) and item.get("type") == "image_url"
    ]
    assert image_parts == [
        {
            "type": "image_url",
            "image_url": {"url": "data:image/png;base64,cccc", "detail": "high"},
        }
    ]


def test_competitor_scan_redacts_and_audits(monkeypatch):
    sink = []
    _plain_key(monkeypatch)
    _install_openai(
        monkeypatch,
        sink,
        content='[{"title": "Launch", "url": "https://example.com/p", "source_type": "news", "summary": "Shipped", "sentiment": "positive", "threat_level": "low", "impact": "Watch"}]',
    )
    db = _session(monkeypatch)
    competitor = SimpleNamespace(
        name=f"Acme {EMAIL}",
        website=None,
        blog_url=None,
        linkedin_url=None,
        x_handle=PHONE,
        company_id=19,
    )

    found = competitors._scan_competitor_web(competitor, user_id=6)

    assert found[0]["title"] == "Launch"
    assert found[0]["source_type"] == "news"
    _assert_pii_redacted(sink)
    _assert_audit(db, 19, 6)
    assert sink[0]["model"] == "gpt-4o-search-preview"
    assert "temperature" not in sink[0]
    assert sink[0]["max_tokens"] == 1500


def test_provider_error_still_closes_the_audit_session(monkeypatch):
    sink = []
    _plain_key(monkeypatch)
    _install_openai(monkeypatch, sink, raise_error=RuntimeError("provider down"))
    db = _session(monkeypatch)

    with pytest.raises(ValueError, match="provider down"):
        pdf_extractor.extract_metrics_with_openai(PII, company_id=42, user_id=7)

    assert db.closed is True
    _assert_pii_redacted(sink)
    logs = _logs(db)
    assert len(logs) == 1
    assert logs[0].company_id == 42
    assert EMAIL not in (logs[0].redacted_prompt_preview or "")


def test_pdf_missing_key_keeps_the_error_and_closes_the_session(monkeypatch):
    _clear_keys(monkeypatch)
    db = _session(monkeypatch)

    with pytest.raises(ValueError) as excinfo:
        pdf_extractor.extract_metrics_with_openai("a report")

    assert is_missing_key_error(excinfo.value)
    assert "AI_INTEGRATIONS_OPENAI_API_KEY" in str(excinfo.value)
    assert "OPENAI_API_KEY" in str(excinfo.value)
    assert db.closed is True
    assert _logs(db) == []


def test_onboarding_missing_key_is_unchanged_and_opens_no_session(monkeypatch):
    _clear_keys(monkeypatch)
    opened = []

    def _opened():
        opened.append("session")
        return RecordingDB()

    monkeypatch.setattr("server.core.db.SessionLocal", _opened)

    with pytest.raises(ValueError) as excinfo:
        ingest.extract_onboarding_data_with_openai("a document")

    message = str(excinfo.value)
    assert "AI_INTEGRATIONS_OPENAI_API_KEY" in message
    assert "OPENAI_API_KEY" in message
    assert "Failed to" not in message
    assert opened == []


def test_competitor_missing_key_is_unchanged_and_opens_no_session(monkeypatch):
    _clear_keys(monkeypatch)
    opened = []
    monkeypatch.setattr("server.core.db.SessionLocal", lambda: opened.append("session"))

    with pytest.raises(RuntimeError, match="OpenAI is not configured \\(set OPENAI_API_KEY\\)"):
        competitors._scan_competitor_web(SimpleNamespace(name="Acme", company_id=1))

    assert opened == []


def test_excel_summary_missing_key_returns_empty_and_closes_the_session(monkeypatch):
    _clear_keys(monkeypatch)
    db = _session(monkeypatch)

    assert excel_extractor.generate_ai_summary({"revenue": 1.0}) == ""
    assert db.closed is True


def test_onboarding_audit_scope_uses_the_users_company_and_closes(monkeypatch):
    company = SimpleNamespace(id=15, user_id=4)
    db = _session(monkeypatch, company=company)

    assert ingest._known_audit_scope(SimpleNamespace(id=4)) == (15, 4)
    assert db.closed is True


def test_onboarding_audit_scope_closes_when_the_lookup_fails(monkeypatch):
    broken = RecordingDB()

    def query(model):
        raise RuntimeError("db down")

    broken.query = query
    monkeypatch.setattr("server.core.db.SessionLocal", lambda: broken)

    assert ingest._known_audit_scope(SimpleNamespace(id=4)) == (None, 4)
    assert broken.closed is True


def test_process_termina_pdf_forwards_company_id(monkeypatch, tmp_path):
    seen = {}

    def _fake(text, company_id=None, user_id=None):
        seen["company_id"] = company_id
        seen["user_id"] = user_id
        return {"monthly_revenue": 10}

    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(pdf_extractor, "extract_text_from_pdf", lambda _path: "x" * 200)
    monkeypatch.setattr(pdf_extractor, "extract_metrics_with_patterns", lambda _text: {})
    monkeypatch.setattr(pdf_extractor, "extract_metrics_with_openai", _fake)

    pdf_extractor.process_termina_pdf(str(pdf), company_id=7, user_id=3)

    assert seen == {"company_id": 7, "user_id": 3}


def test_process_termina_excel_forwards_company_id_to_the_summary(monkeypatch, tmp_path):
    seen = {}

    def _spy(metrics, company_id=None, user_id=None):
        seen["company_id"] = company_id
        seen["user_id"] = user_id
        return "summary"

    book = tmp_path / "report.xlsx"
    book.write_bytes(b"not a real workbook")
    monkeypatch.setattr(
        excel_extractor,
        "parse_income_statement",
        lambda _path: {
            "metrics": {"revenue": 1.0, "cogs": 1.0, "opex": 1.0, "payroll": 1.0},
            "ai_metrics": {},
        },
    )
    monkeypatch.setattr(excel_extractor, "generate_ai_summary", _spy)

    excel_extractor.process_termina_excel(
        str(book), use_canonical=False, company_id=8, user_id=2
    )

    assert seen == {"company_id": 8, "user_id": 2}
