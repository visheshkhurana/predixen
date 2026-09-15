"""Server-side lead_captured: payload shape, best-effort send, always queued."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from server.api.leads import LeadCreate, _emit_lead_captured, _lead_distinct_id, create_lead
from server.services import posthog as posthog_svc


class _FakeUrlOpen:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"status":"ok"}'


def test_distinct_id_is_stable_and_not_the_email():
    a = _lead_distinct_id("Founder@Example.com")
    b = _lead_distinct_id("founder@example.com ")
    assert a == b
    assert a.startswith("lead:")
    assert "founder@example.com" not in a


def test_emit_mirrors_location_source_and_runway():
    data = LeadCreate(
        email="founder@example.com",
        source="runway-calculator",
        plan="runway-calculator",
        runway_months="4",
    )
    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(data, created=True)
        capture.assert_called_once()
        event, distinct_id, properties = capture.call_args.args
        assert event == "lead_captured"
        assert distinct_id == _lead_distinct_id("founder@example.com")
        assert properties["location"] == "runway-calculator"
        assert properties["source"] == "runway-calculator"
        assert properties["runway_months"] == "4"
        assert properties["created"] is True


def test_emit_omits_runway_when_absent():
    data = LeadCreate(email="founder@example.com", source="website")
    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(data, created=False)
        properties = capture.call_args.args[2]
        assert "runway_months" not in properties
        assert properties["location"] == "website"
        assert properties["created"] is False


def test_emit_never_raises():
    data = LeadCreate(email="founder@example.com", source="runway-calculator")
    with patch("server.api.leads.posthog_capture", side_effect=RuntimeError("down")):
        _emit_lead_captured(data, created=True)


def test_capture_posts_event_without_identify():
    captured = {}

    def fake_urlopen(req, timeout=5):
        captured["url"] = req.full_url
        captured["body"] = req.data
        return _FakeUrlOpen(200)

    with patch.object(posthog_svc.urllib.request, "urlopen", side_effect=fake_urlopen):
        assert posthog_svc.capture("lead_captured", "lead:abc", {"location": "runway-calculator"})

    import json

    body = json.loads(captured["body"])
    assert captured["url"].endswith("/capture/")
    assert body["event"] == "lead_captured"
    assert body["distinct_id"] == "lead:abc"
    assert body["properties"]["location"] == "runway-calculator"
    assert body["properties"]["$process_person_profile"] is False
    assert body["properties"]["$lib"] == "founderconsole-server"
    assert "identify" not in body


def test_capture_swallows_network_errors():
    def boom(*args, **kwargs):
        raise TimeoutError("slow")

    with patch.object(posthog_svc.urllib.request, "urlopen", side_effect=boom):
        assert posthog_svc.capture("lead_captured", "lead:abc") is False


def test_create_lead_queues_capture_after_commit():
    data = LeadCreate(
        email="founder@example.com",
        source="runway-calculator",
        runway_months="6",
        runway_date="March 2027",
    )
    background = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None

    result = create_lead(data, background, db)

    assert result["status"] == "ok"
    assert result["created"] is True
    db.commit.assert_called_once()
    queued = [call.args[0] for call in background.add_task.call_args_list]
    assert _emit_lead_captured in queued


def test_create_lead_emits_on_repeat_submission():
    existing = MagicMock()
    data = LeadCreate(email="founder@example.com", source="runway-calculator")
    background = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = existing

    result = create_lead(data, background, db)

    assert result["created"] is False
    queued = [call.args[0] for call in background.add_task.call_args_list]
    assert _emit_lead_captured in queued


def test_create_lead_does_not_emit_when_commit_fails():
    from fastapi import HTTPException
    from sqlalchemy.exc import SQLAlchemyError
    import pytest

    data = LeadCreate(email="founder@example.com", source="runway-calculator")
    background = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None
    db.commit.side_effect = SQLAlchemyError("down")

    with pytest.raises(HTTPException) as exc:
        create_lead(data, background, db)

    assert exc.value.status_code == 503
    background.add_task.assert_not_called()
