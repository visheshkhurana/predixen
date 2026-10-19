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
    def create(self, **kwargs):
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


def test_no_key_names_both_variables(fake_openai):
    with pytest.raises(ValueError) as excinfo:
        ingest.extract_onboarding_data_with_openai("a document")

    message = str(excinfo.value)
    assert "AI_INTEGRATIONS_OPENAI_API_KEY" in message
    assert "OPENAI_API_KEY" in message
