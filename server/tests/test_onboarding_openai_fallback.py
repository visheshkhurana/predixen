"""Onboarding extraction must work with a plain OPENAI_API_KEY, not only the
Replit AI-Integrations key — and must not send a plain key to the integration proxy.
"""
import pytest

from server.api import ingest


class _FakeMessage:
    content = '{"summary": "ok"}'


class _FakeChoice:
    message = _FakeMessage()


class _FakeResponse:
    choices = [_FakeChoice()]


class _FakeCompletions:
    last_kwargs = None

    def create(self, **kwargs):
        # Record what was actually sent: a fake that accepts any keyword cannot
        # catch a parameter api.openai.com would reject with a 400.
        type(self).last_kwargs = kwargs
        return _FakeResponse()


class _FakeChat:
    completions = _FakeCompletions()


class _FakeOpenAI:
    last_kwargs = None

    def __init__(self, **kwargs):
        _FakeOpenAI.last_kwargs = kwargs
        self.chat = _FakeChat()


@pytest.fixture
def fake_openai(monkeypatch):
    _FakeOpenAI.last_kwargs = None
    _FakeCompletions.last_kwargs = None
    monkeypatch.setattr("openai.OpenAI", _FakeOpenAI)
    for name in (
        "AI_INTEGRATIONS_OPENAI_API_KEY",
        "AI_INTEGRATIONS_OPENAI_BASE_URL",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    return _FakeOpenAI


def test_document_extraction_uses_a_plain_openai_key(fake_openai, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-plain")

    result = ingest.extract_onboarding_data_with_openai("a document")

    assert result == {"summary": "ok"}
    assert fake_openai.last_kwargs["api_key"] == "sk-plain"


def test_plain_key_does_not_inherit_the_integration_base_url(fake_openai, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-plain")
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "https://integrations.example/v1")

    ingest.extract_onboarding_data_with_openai("a document")

    assert "base_url" not in fake_openai.last_kwargs


def test_integration_key_keeps_its_base_url(fake_openai, monkeypatch):
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_API_KEY", "integration-key")
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "https://integrations.example/v1")

    ingest.extract_onboarding_data_with_openai("a document")

    assert fake_openai.last_kwargs["api_key"] == "integration-key"
    assert fake_openai.last_kwargs["base_url"] == "https://integrations.example/v1"


def test_integration_key_wins_over_a_plain_key(fake_openai, monkeypatch):
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_API_KEY", "integration-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-plain")

    ingest.extract_onboarding_data_with_openai("a document")

    assert fake_openai.last_kwargs["api_key"] == "integration-key"


def test_vision_extraction_uses_a_plain_openai_key(fake_openai, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-plain")
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "https://integrations.example/v1")

    result = ingest.extract_onboarding_data_with_vision(["ZmFrZQ=="])

    assert result == {"summary": "ok"}
    assert fake_openai.last_kwargs["api_key"] == "sk-plain"
    assert "base_url" not in fake_openai.last_kwargs


def test_direct_document_call_sends_only_params_openai_accepts(fake_openai, monkeypatch):
    """GPT-5 on api.openai.com rejects max_tokens and a non-default temperature."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-plain")

    ingest.extract_onboarding_data_with_openai("a document")

    kwargs = _FakeCompletions.last_kwargs
    assert kwargs["model"] == "gpt-5"
    assert kwargs["max_completion_tokens"] == 4000
    assert "max_tokens" not in kwargs
    assert "temperature" not in kwargs
    assert kwargs["timeout"] == 60


def test_direct_vision_call_sends_only_params_openai_accepts(fake_openai, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-plain")

    ingest.extract_onboarding_data_with_vision(["ZmFrZQ=="])

    kwargs = _FakeCompletions.last_kwargs
    assert kwargs["model"] == "gpt-5"
    assert kwargs["max_completion_tokens"] == 4000
    assert "max_tokens" not in kwargs
    assert "temperature" not in kwargs
    assert kwargs["timeout"] == 90


def test_proxy_call_keeps_its_original_params(fake_openai, monkeypatch):
    """The proxy accepts these, and the direct-path fix must not change it."""
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_API_KEY", "integration-key")
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "https://integrations.example/v1")

    ingest.extract_onboarding_data_with_openai("a document")

    kwargs = _FakeCompletions.last_kwargs
    assert kwargs["max_tokens"] == 2000
    assert kwargs["temperature"] == 0.1
    assert "max_completion_tokens" not in kwargs


def test_no_key_names_both_variables(fake_openai):
    with pytest.raises(ValueError) as excinfo:
        ingest.extract_onboarding_data_with_openai("a document")

    message = str(excinfo.value)
    assert "AI_INTEGRATIONS_OPENAI_API_KEY" in message
    assert "OPENAI_API_KEY" in message


# --- Sentinel F1: the PDF/Excel factories only ever read the integration key ---


def test_pdf_extractor_client_uses_a_plain_key_without_a_base_url(fake_openai, monkeypatch):
    from server.ingest import pdf_extractor

    monkeypatch.setenv("OPENAI_API_KEY", "sk-plain")
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "https://integrations.example/v1")

    pdf_extractor.get_openai_client()

    assert fake_openai.last_kwargs["api_key"] == "sk-plain"
    assert "base_url" not in fake_openai.last_kwargs


def test_excel_extractor_client_uses_a_plain_key(fake_openai, monkeypatch):
    from server.ingest import excel_extractor

    monkeypatch.setenv("OPENAI_API_KEY", "sk-plain")

    excel_extractor.get_openai_client()

    assert fake_openai.last_kwargs["api_key"] == "sk-plain"


def test_extractor_client_without_a_key_names_both_variables(fake_openai):
    from server.ingest import excel_extractor, pdf_extractor

    for factory in (pdf_extractor.get_openai_client, excel_extractor.get_openai_client):
        with pytest.raises(ValueError) as excinfo:
            factory()
        message = str(excinfo.value)
        assert "AI_INTEGRATIONS_OPENAI_API_KEY" in message
        assert "OPENAI_API_KEY" in message


def test_missing_key_is_not_swallowed_by_a_pattern_only_pdf_result(
    fake_openai, monkeypatch, tmp_path
):
    """A pattern match must not turn a missing credential into a success."""
    from server.core.openai_credentials import missing_key_error
    from server.ingest import pdf_extractor

    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    monkeypatch.setattr(pdf_extractor, "extract_text_from_pdf", lambda _path: "x" * 500)
    monkeypatch.setattr(
        pdf_extractor, "extract_metrics_with_patterns", lambda _text: {"revenue": 1.0}
    )

    def no_key(_text):
        raise missing_key_error()

    monkeypatch.setattr(pdf_extractor, "extract_metrics_with_openai", no_key)

    with pytest.raises(ValueError) as excinfo:
        pdf_extractor.process_termina_pdf(str(pdf))
    assert "AI_INTEGRATIONS_OPENAI_API_KEY" in str(excinfo.value)


def test_missing_key_is_not_swallowed_by_a_partial_excel_result(
    fake_openai, monkeypatch, tmp_path
):
    from server.core.openai_credentials import missing_key_error
    from server.ingest import excel_extractor

    book = tmp_path / "report.xlsx"
    book.write_bytes(b"fake")
    monkeypatch.setattr(
        excel_extractor, "parse_income_statement_canonical", lambda _path: {"success": False}
    )
    monkeypatch.setattr(
        excel_extractor, "parse_income_statement", lambda _path: {"metrics": {"revenue": 1.0}}
    )
    monkeypatch.setattr(excel_extractor, "excel_to_text", lambda _path: "text")

    def no_key(_text):
        raise missing_key_error()

    monkeypatch.setattr(excel_extractor, "extract_metrics_with_openai", no_key)

    with pytest.raises(ValueError) as excinfo:
        excel_extractor.process_termina_excel(str(book))
    assert "AI_INTEGRATIONS_OPENAI_API_KEY" in str(excinfo.value)
