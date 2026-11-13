"""POST /ingest/onboarding/extract-deck must not call OpenAI anonymously.

The route used to document that it required no session, so any uploaded PDF,
Excel, or CSV under 20MB reached GPT-4o. An empty body was 422, which proved
the route was mounted and not a 401. Auth has to fail before either extractor.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import ingest as ingest_api


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(ingest_api.router)
    return TestClient(app)


def test_anonymous_pdf_is_401_and_never_calls_openai(monkeypatch):
    calls = []

    def boom(*_a, **_k):
        calls.append("openai")
        raise AssertionError("OpenAI must not run for an anonymous upload")

    monkeypatch.setattr(ingest_api, "extract_onboarding_data_with_openai", boom)
    monkeypatch.setattr(ingest_api, "extract_onboarding_data_with_vision", boom)
    monkeypatch.setattr(ingest_api, "extract_text_from_pdf", lambda _path: "x" * 800)

    pdf = b"%PDF-1.4\n" + (b"Revenue 10000 cash 50000 " * 40)
    resp = _client().post(
        "/ingest/onboarding/extract-deck",
        files={"file": ("deck.pdf", pdf, "application/pdf")},
    )

    assert resp.status_code == 401, resp.text
    assert calls == []


def test_anonymous_spreadsheet_is_401_and_never_calls_openai(monkeypatch):
    calls = []

    def boom(*_a, **_k):
        calls.append("openai")
        raise AssertionError("OpenAI must not run for an anonymous upload")

    monkeypatch.setattr(ingest_api, "extract_onboarding_data_with_openai", boom)
    monkeypatch.setattr(ingest_api, "extract_onboarding_data_with_vision", boom)

    resp = _client().post(
        "/ingest/onboarding/extract-deck",
        files={"file": ("numbers.csv", b"month,revenue\n2026-01,10000\n", "text/csv")},
    )

    assert resp.status_code == 401, resp.text
    assert calls == []
