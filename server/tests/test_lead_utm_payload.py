"""Lead and signup payloads carry first-touch campaign parameters.

leads stores utm_source, utm_medium, and utm_campaign. The other keys are
accepted so they are not a 422, and they ride on the PostHog event. A second
submit does not replace a campaign already on the row. Nothing here logs an IP.
"""

import logging
from unittest.mock import MagicMock, patch

from server.api.auth import RegisterRequest
from server.api.leads import LeadCreate, _emit_lead_captured, create_lead
from server.models.lead import Lead
from server.services.activation import emit_signup_completed


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _Request:
    def __init__(self):
        self.headers = _Headers({"host": "founderconsole.ai"})
        self.url = type("U", (), {"hostname": "founderconsole.ai"})()
        self.client = type("C", (), {"host": "203.0.113.50"})()


def _consented(**overrides) -> LeadCreate:
    payload = dict(
        email="founder@example.com",
        source="runway-calculator",
        source_page="/tools/runway-calculator",
        consent=True,
    )
    payload.update(overrides)
    return LeadCreate(**payload)


def test_lead_payload_truncates_campaign_fields_and_drops_non_strings():
    data = LeadCreate(
        email="founder@example.com",
        utm_source="  google  ",
        utm_medium="x" * 250,
        utm_campaign="",
        utm_content=12,
        utm_term=" runway ",
        fbclid=" fb ",
        gclid=None,
    )
    assert data.utm_source == "google"
    assert data.utm_medium == "x" * 200
    assert data.utm_campaign is None
    assert data.utm_content is None
    assert data.utm_term == "runway"
    assert data.fbclid == "fb"
    assert data.gclid is None


def test_create_lead_stores_three_columns_and_does_not_log_the_ip(caplog):
    data = _consented(
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="spring",
        utm_content="ad",
        utm_term="runway",
        fbclid="fb-1",
        gclid="gc-1",
    )
    background = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None

    with caplog.at_level(logging.DEBUG):
        result = create_lead(data, background, _Request(), db)

    assert result == {"status": "ok"}
    lead = db.add.call_args.args[0]
    assert isinstance(lead, Lead)
    assert lead.utm_source == "google"
    assert lead.utm_medium == "cpc"
    assert lead.utm_campaign == "spring"
    assert "fbclid" not in lead.__dict__
    assert "203.0.113.50" not in caplog.text
    assert "fb-1" not in caplog.text


def test_create_lead_keeps_the_first_campaign_on_the_row():
    existing = MagicMock()
    existing.utm_source = "newsletter"
    existing.utm_medium = None
    existing.utm_campaign = ""
    existing.consent_status = "pending"
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = existing

    create_lead(
        _consented(
            email="again@example.com",
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="spring",
        ),
        MagicMock(),
        _Request(),
        db,
    )

    assert existing.utm_source == "newsletter"
    assert existing.utm_medium == "cpc"
    assert existing.utm_campaign == "spring"
    db.add.assert_not_called()


def test_lead_captured_includes_attribution_and_drops_an_address():
    data = _consented(
        utm_source="founder@example.com",
        utm_medium="cpc",
        fbclid="fb-1",
    )
    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(data, created=True, host="founderconsole.ai")
    properties = capture.call_args.args[2]
    assert "utm_source" not in properties
    assert properties["utm_medium"] == "cpc"
    assert properties["fbclid"] == "fb-1"
    assert "gclid" not in properties
    assert "203.0.113.50" not in str(properties)


def test_utm_term_email_never_reaches_lead_columns():
    """utm_term=jane@x.com is dropped before it can be written to a leads column."""
    address = "jane@x.com"
    data = _consented(
        utm_term=address,
        utm_source=address,
        utm_medium=address,
        utm_campaign=address,
    )
    assert data.utm_term is None
    assert data.utm_source is None
    assert data.utm_medium is None
    assert data.utm_campaign is None

    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None
    create_lead(data, MagicMock(), _Request(), db)

    lead = db.add.call_args.args[0]
    assert isinstance(lead, Lead)
    assert lead.utm_source is None
    assert lead.utm_medium is None
    assert lead.utm_campaign is None
    assert address not in str(lead.__dict__)


def test_signup_event_drops_utm_term_email():
    """utm_term=jane@x.com must not be a property on the activation signup event."""
    with patch("server.services.activation.posthog_capture") as capture:
        assert emit_signup_completed(
            user_id=7,
            method="email",
            attribution={"utm_term": "jane@x.com", "utm_source": "newsletter"},
        )
    properties = capture.call_args.args[2]
    assert properties["method"] == "email"
    assert properties["user_id"] == 7
    assert properties["utm_source"] == "newsletter"
    assert "utm_term" not in properties
    assert "jane@x.com" not in str(properties)


def test_signup_payload_is_on_signup_completed_and_not_required():
    req = RegisterRequest(
        email="founder@example.com",
        password="correcthorse1",
        utm_source=" google ",
        utm_medium="cpc",
        utm_campaign="y" * 250,
        fbclid="fb-9",
        gclid=15,
    )
    assert req.utm_source == "google"
    assert req.utm_campaign == "y" * 200
    assert req.fbclid == "fb-9"
    assert req.gclid is None

    with patch("server.services.activation.posthog_capture") as capture:
        assert emit_signup_completed(
            user_id=7,
            method="email",
            attribution={
                "utm_source": req.utm_source,
                "utm_medium": req.utm_medium,
                "utm_campaign": req.utm_campaign,
                "utm_content": req.utm_content,
                "utm_term": req.utm_term,
                "fbclid": req.fbclid,
                "gclid": req.gclid,
                "ip_address": "203.0.113.50",
            },
        )
    properties = capture.call_args.args[2]
    assert properties["method"] == "email"
    assert properties["user_id"] == 7
    assert properties["utm_source"] == "google"
    assert properties["utm_medium"] == "cpc"
    assert properties["utm_campaign"] == "y" * 200
    assert properties["fbclid"] == "fb-9"
    assert "ip_address" not in properties
    assert "203.0.113.50" not in str(properties)

    with patch("server.services.activation.posthog_capture") as capture:
        emit_signup_completed(user_id=7, method="email")
    assert capture.call_args.args[2] == {"method": "email", "user_id": 7}
