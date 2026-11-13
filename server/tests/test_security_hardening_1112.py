"""Input handling and access checks hardened in one pass.

Each block pins one behaviour: outbound connector targets, reflected values on
the feedback page, redirect targets, the website lookup's session requirement,
the QA gate, cross-site cookie writes, the reset-password bucket, and capped
upload reads.
"""

from __future__ import annotations

import asyncio
import io

import pytest
from fastapi import FastAPI, UploadFile, HTTPException
from starlette.testclient import TestClient

from server.core.url_safety import (
    UnsafeTargetError,
    assert_public_host,
    assert_public_url,
    assert_safe_label,
    validate_connector_targets,
)


def _resolver(mapping):
    def resolve(host):
        if host not in mapping:
            raise OSError("unknown host")
        return mapping[host]
    return resolve


PUBLIC = _resolver({"api.example.com": ["93.184.216.34"], "rebind.example.com": ["10.0.0.5"]})


# --- outbound targets -------------------------------------------------------

@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8001/admin",
    "http://localhost/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://10.1.2.3/",
    "http://192.168.0.10/",
    "http://100.64.0.1/",
    "http://0.0.0.0/",
    "http://metadata.google.internal/",
    "http://rebind.example.com/",
    "file:///etc/passwd",
    "gopher://api.example.com/",
    "https://user:pass@api.example.com/",
    "not a url",
])
def test_private_or_malformed_urls_are_refused(url):
    with pytest.raises(UnsafeTargetError):
        assert_public_url(url, resolver=PUBLIC)


def test_public_url_is_accepted():
    assert_public_url("https://api.example.com/v1", resolver=PUBLIC)
    assert_public_url("http://93.184.216.34:8443/x", resolver=PUBLIC)


def test_unresolvable_host_is_refused_unless_allowed():
    with pytest.raises(UnsafeTargetError):
        assert_public_host("nope.example.com", resolver=PUBLIC)
    assert_public_host("nope.example.com", resolver=PUBLIC, allow_unresolved=True)
    # A name that resolves to an internal address is refused either way.
    with pytest.raises(UnsafeTargetError):
        validate_connector_targets({"base_url": "http://rebind.example.com/"}, resolver=PUBLIC)


@pytest.mark.parametrize("label", ["evil.com/#", "a@b", "x:80", "a b", "a\\b", "?x", ""])
def test_hostname_labels_reject_url_syntax(label):
    with pytest.raises(UnsafeTargetError):
        assert_safe_label(label)


@pytest.mark.parametrize("label", ["acme", "acme-co", "acme.myshopify.com", "1234567_SB1"])
def test_hostname_labels_accept_tenant_names(label):
    assert_safe_label(label)


def test_connector_fields_are_checked_and_empty_values_skipped():
    validate_connector_targets({}, None, {"base_url": "", "shop_domain": ""}, resolver=PUBLIC)
    with pytest.raises(UnsafeTargetError):
        validate_connector_targets({"api_key": "k"}, {"endpoint_url": "http://127.0.0.1/"}, resolver=PUBLIC)
    with pytest.raises(UnsafeTargetError):
        validate_connector_targets({"host": "10.0.0.1"}, resolver=PUBLIC)
    with pytest.raises(UnsafeTargetError):
        validate_connector_targets({"shop_domain": "evil.com/#"}, resolver=PUBLIC)


def test_connectors_refuse_internal_targets_at_construction():
    from server.connectors import ConnectorConfig, ConnectorRegistry, load_all_connectors

    load_all_connectors()
    cases = [
        ("rest_api", {"api_key": "k"}, {"endpoint_url": "http://127.0.0.1:8001/companies"}),
        ("keka", {"api_key": "k", "base_url": "http://169.254.169.254/"}, {}),
        ("salesforce", {"access_token": "t", "instance_url": "http://localhost:5432"}, {}),
        ("shopify", {"access_token": "t", "shop_domain": "evil.example/#"}, {}),
    ]
    for provider, creds, settings in cases:
        cls = ConnectorRegistry.get_connector_class(provider)
        assert cls is not None, provider
        with pytest.raises(UnsafeTargetError):
            cls(ConnectorConfig(provider_id=provider, company_id=1, credentials=creds, settings=settings))


def test_connect_route_answers_400_for_unsafe_target():
    import inspect
    from server.api import connectors as api

    src = inspect.getsource(api.connect_provider)
    assert "except UnsafeTargetError" in src
    assert "status_code=400" in src


# --- email tracking -------------------------------------------------------

def _tracking_client():
    from server.api import email_tracking

    app = FastAPI()
    app.include_router(email_tracking.router)
    return TestClient(app, follow_redirects=False)


def test_feedback_page_escapes_reflected_values():
    client = _tracking_client()
    payload = '"><script>alert(1)</script>'
    res = client.get("/email-tracking/feedback", params={"email_id": payload, "email": "a@b.c", "campaign": "x'y"})
    assert res.status_code == 200
    assert "<script>alert(1)</script>" not in res.text
    assert "%22%3E%3Cscript%3E" in res.text
    assert "x'y" not in res.text


@pytest.mark.parametrize("dest,expected", [
    ("https://evil.example/phish", "https://founderconsole.ai"),
    ("//evil.example/", "https://founderconsole.ai"),
    ("/\\evil.example", "https://founderconsole.ai"),
    ("javascript:alert(1)", "https://founderconsole.ai"),
    ("https://founderconsole.ai.evil.example/", "https://founderconsole.ai"),
    ("https://user@founderconsole.ai/", "https://founderconsole.ai"),
    ("http://founderconsole.ai/", "https://founderconsole.ai"),
    ("https://founderconsole.ai/pricing", "https://founderconsole.ai/pricing"),
    ("/onboarding?x=1", "/onboarding?x=1"),
    ("", "https://founderconsole.ai"),
])
def test_welcome_redirect_only_goes_to_our_site(dest, expected):
    from server.api.email_tracking import safe_redirect_target

    assert safe_redirect_target(dest) == expected


# --- website lookup -------------------------------------------------------

def test_website_lookup_requires_a_session(monkeypatch):
    from server.api import company_lookup
    from server.core.db import get_db

    monkeypatch.setattr(company_lookup, "PERPLEXITY_API_KEY", "test-key")
    app = FastAPI()
    app.include_router(company_lookup.router)
    def _db():
        yield None

    app.dependency_overrides[get_db] = _db
    res = TestClient(app).post("/lookup/company-from-website", json={"website": "example.com"})
    assert res.status_code == 401


# --- QA gate --------------------------------------------------------------

class _User:
    def __init__(self, email, verified):
        self.email = email
        self.is_email_verified = verified
        self._is_master_user = False


def test_qa_gate_requires_verified_owner(monkeypatch):
    from server.api.qa import require_qa_access
    from server.core.config import settings

    monkeypatch.setattr(settings, "ADMIN_MASTER_EMAIL", "owner@example.com")
    with pytest.raises(HTTPException) as exc:
        require_qa_access(_User("owner@example.com", False))
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException):
        require_qa_access(_User("someone@example.com", True))
    user = _User("owner@example.com", True)
    assert require_qa_access(user) is user


# --- cross-site cookie writes --------------------------------------------

def _csrf_client():
    from server.middleware.csrf_protection import CSRFProtectionMiddleware

    app = FastAPI()

    @app.post("/thing")
    def thing():
        return {"ok": True}

    app.add_middleware(CSRFProtectionMiddleware, exempt_paths=["/health"])
    return TestClient(app)


def test_cross_site_cookie_post_is_refused():
    client = _csrf_client()
    client.cookies.set("auth_token", "session")
    res = client.post("/thing", headers={"Sec-Fetch-Site": "cross-site"})
    assert res.status_code == 403


def test_same_origin_cookie_post_still_works():
    client = _csrf_client()
    client.cookies.set("auth_token", "session")
    assert client.post("/thing", headers={"Sec-Fetch-Site": "same-origin"}).status_code == 200
    assert client.post("/thing").status_code == 200


def test_cross_site_without_session_cookie_is_unaffected():
    client = _csrf_client()
    assert client.post("/thing", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 200


# --- rate limit bucket ----------------------------------------------------

def test_reset_password_is_in_the_auth_bucket():
    from server.middleware.rate_limiter import RateLimiterMiddleware

    assert "/auth/reset-password" in RateLimiterMiddleware.AUTH_PATHS


# --- capped upload reads --------------------------------------------------

def test_upload_read_is_capped():
    from server.core.uploads import read_upload_capped

    small = UploadFile(file=io.BytesIO(b"x" * 10), filename="a.csv")
    assert asyncio.run(read_upload_capped(small, max_bytes=10)) == b"x" * 10
    big = UploadFile(file=io.BytesIO(b"x" * 11), filename="a.csv")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_upload_capped(big, max_bytes=10))
    assert exc.value.status_code == 413


def test_salesforce_pagination_stays_on_the_instance():
    import inspect
    from server.connectors import salesforce

    src = inspect.getsource(salesforce)
    assert 'next_url.startswith("/") and not next_url.startswith("//")' in src
