"""NetSuite OAuth 2.0 client credentials (M2M), the replacement for TBA.

https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_162790605110.html
No network: httpx MockTransport.
"""

import asyncio
import urllib.parse

import httpx
import jwt
import pytest
from cryptography import x509

from server.connectors import netsuite_m2m as m2m
from server.connectors.base import ConnectorConfig
from server.connectors.netsuite import NetSuiteConnector

PRIVATE, CERT, EXPIRES = m2m.generate_keypair()


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def mock_http(monkeypatch):
    state = {"handler": None, "requests": []}
    orig = httpx.AsyncClient

    def dispatch(request):
        state["requests"].append(request)
        return state["handler"](request)

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(dispatch)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    return state


def _m2m(**extra):
    creds = {"account_id": "1234567_SB1", "client_id": "cid", "certificate_id": "kid-1", "private_key": PRIVATE}
    creds.update(extra)
    return NetSuiteConnector(ConnectorConfig(provider_id="netsuite", company_id=1, credentials=creds))


def test_hosts_are_lowercase_with_hyphens():
    assert m2m.account_host("1234567_SB1") == "1234567-sb1"
    assert m2m.token_url("1234567_SB1") == \
        "https://1234567-sb1.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token"
    assert _m2m()._base_url.startswith("https://1234567-sb1.suitetalk.api.netsuite.com/")


def test_certificate_is_ec_p256_and_signs_the_assertion():
    cert = x509.load_pem_x509_certificate(CERT.encode())
    assert cert.public_key().curve.name == "secp256r1"
    assert (cert.not_valid_after_utc - cert.not_valid_before_utc).days <= 730
    token = m2m.build_assertion("1234567_SB1", "cid", "kid-1", PRIVATE, now=1_700_000_000)
    header = jwt.get_unverified_header(token)
    assert header == {"alg": "ES256", "typ": "JWT", "kid": "kid-1"}
    claims = jwt.decode(token, cert.public_key(), algorithms=["ES256"],
                        audience=m2m.token_url("1234567_SB1"), options={"verify_exp": False})
    assert claims["iss"] == "cid" and claims["scope"] == ["rest_webservices"]
    assert 0 < claims["exp"] - claims["iat"] <= 3600 and claims["jti"]


def test_sign_in_trades_assertion_for_bearer_and_reuses_it(mock_http):
    calls = {"token": 0}

    def handler(req):
        if req.url.path.endswith("/oauth2/v1/token"):
            calls["token"] += 1
            body = dict(urllib.parse.parse_qsl(req.content.decode()))
            assert body["grant_type"] == "client_credentials"
            assert body["client_assertion_type"] == m2m.CLIENT_ASSERTION_TYPE
            assert jwt.get_unverified_header(body["client_assertion"])["kid"] == "kid-1"
            return httpx.Response(200, json={"access_token": "AT", "expires_in": 3600, "token_type": "bearer"})
        assert req.headers["authorization"] == "Bearer AT"
        if req.url.path.endswith("/query/v1/suiteql"):
            return httpx.Response(200, json={"items": [], "hasMore": False})
        return httpx.Response(200, json={"items": []})

    mock_http["handler"] = handler
    conn = _m2m()
    assert conn.uses_m2m and not conn.uses_tba
    assert _run(conn.authenticate())
    _run(conn._suiteql("SELECT id FROM account"))
    assert calls["token"] == 1  # second request reused the 60-minute token
    assert not any("oauth_signature" in r.headers.get("authorization", "") for r in mock_http["requests"])


@pytest.mark.parametrize("error,text", [
    ("invalid_client", "Client ID and certificate"),
    ("invalid_grant", "revoked or expired"),
    ("unauthorized_client", "Machine to Machine"),
])
def test_token_errors_are_readable(mock_http, error, text):
    mock_http["handler"] = lambda req: httpx.Response(400, json={"error": error})
    conn = _m2m()
    assert not _run(conn.authenticate())
    assert text in conn.auth_error


def test_missing_key_or_ids_explain_what_to_do():
    conn = _m2m(private_key="")
    assert not _run(conn.authenticate()) and "certificate" in conn.auth_error
    conn = NetSuiteConnector(ConnectorConfig(provider_id="netsuite", company_id=1, credentials={"account_id": "1"}))
    assert not _run(conn.authenticate()) and "Certificate ID" in conn.auth_error


def test_tba_still_works_when_no_certificate(mock_http):
    seen = []

    def handler(req):
        seen.append(req.headers["authorization"])
        return httpx.Response(200, json={"items": []})

    mock_http["handler"] = handler
    conn = NetSuiteConnector(ConnectorConfig(provider_id="netsuite", company_id=1, credentials={
        "account_id": "1234567", "consumer_key": "ck", "consumer_secret": "cs", "token_id": "tk", "token_secret": "ts"}))
    assert _run(conn.authenticate())
    assert seen[0].startswith("OAuth realm=")


def test_connect_attaches_stored_key_and_ignores_browser_key(monkeypatch):
    from server.api import connectors as api
    monkeypatch.setattr(api, "decrypt_credentials", lambda blob: {"pem": "STORED-" + blob})

    class Co:
        metadata_json = {"connector_keys": {"netsuite": {"private_key": "enc", "certificate": CERT}}}

    creds = {"account_id": "1", "client_id": "cid", "certificate_id": "kid", "private_key": "from-browser"}
    api._attach_netsuite_key(Co(), creds)
    assert creds["private_key"] == "STORED-enc"

    tba = {"account_id": "1", "consumer_key": "ck", "private_key": "from-browser"}
    api._attach_netsuite_key(Co(), tba)
    assert "private_key" not in tba
