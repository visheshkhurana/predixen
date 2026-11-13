"""The public contact form delivers to our inbox and nowhere else."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import contact as contact_api


@pytest.fixture(autouse=True)
def _fresh_bucket():
    contact_api._CONTACT_HITS.clear()
    yield
    contact_api._CONTACT_HITS.clear()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(contact_api.router)
    return TestClient(app)


def _body(**kw):
    base = {
        "name": "Asha Rao",
        "email": "asha@brand.in",
        "subject": "Sales",
        "message": "We run a Shopify brand and want a demo.",
    }
    base.update(kw)
    return base


def _ok_send():
    return AsyncMock(return_value={"success": True})


def test_delivers_to_inbox_with_reply_to_visitor(monkeypatch):
    monkeypatch.setenv("CONTACT_INBOX", "team@founderconsole.ai")
    sent = _ok_send()
    with patch("server.email.service.send_email", sent):
        res = _client().post("/contact", json=_body())
    assert res.status_code == 200
    kwargs = sent.call_args.kwargs
    assert kwargs["to"] == "team@founderconsole.ai"
    assert kwargs["headers"] == {"Reply-To": "asha@brand.in"}
    assert kwargs["subject"] == "[Contact] Sales from Asha Rao"


def test_fields_are_escaped():
    sent = _ok_send()
    with patch("server.email.service.send_email", sent):
        _client().post("/contact", json=_body(name="<b>x</b>", message="<script>alert(1)</script> hello"))
    body = sent.call_args.kwargs["html_content"]
    assert "<script>" not in body and "<b>x</b>" not in body
    assert "&lt;script&gt;" in body


def test_subject_must_come_from_the_list():
    sent = _ok_send()
    with patch("server.email.service.send_email", sent):
        res = _client().post("/contact", json=_body(subject="Hi\r\nBcc: a@b.c"))
    assert res.status_code == 422
    sent.assert_not_called()


def test_honeypot_is_silently_dropped():
    sent = _ok_send()
    with patch("server.email.service.send_email", sent):
        res = _client().post("/contact", json=_body(website="http://spam.example"))
    assert res.status_code == 200
    sent.assert_not_called()


def test_failed_delivery_is_reported():
    sent = AsyncMock(return_value={"success": False, "error": "resend down"})
    with patch("server.email.service.send_email", sent):
        res = _client().post("/contact", json=_body())
    assert res.status_code == 502


def test_rate_limited_per_client():
    sent = _ok_send()
    client = _client()
    with patch("server.email.service.send_email", sent):
        codes = [client.post("/contact", json=_body()).status_code for _ in range(contact_api.CONTACT_RATE_LIMIT + 1)]
    assert codes[:-1] == [200] * contact_api.CONTACT_RATE_LIMIT
    assert codes[-1] == 429
