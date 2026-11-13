"""Tokens minted by the old python-jose code path still verify under PyJWT.

The fixtures below were produced by python-jose 3.5.0 with exactly what
``create_access_token`` used to do: ``jose.jwt.encode(claims, SECRET_KEY,
algorithm="HS256")`` with datetime ``exp``/``iat`` and a ``jti``. Sessions
issued before the switch must keep working until they expire.
"""
import jwt
import pytest

from server.core import security
from server.core.config import settings

FIXTURE_SECRET = "jose-interop-fixture-secret-not-a-real-key-0123456789"

# exp = 2100-01-01, iat = 2026-11-12
JOSE_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiI0MiIsImVtYWlsIjoiZm91bmRlckBleGFtcGxlLmNvbSIsImV4cCI6NDEwMjQ0NDgwMCwiaWF0IjoxNzk0NDQxNjAwLCJqdGkiOiI3YjBlMGE4ZS01ZjBjLTRjNTUtOWEzOS0yYTFmMGI2ZjZhMTEifQ."
    "ney5s7bOKO_usZttJQ4QV_Dh-2KkqlMvS7PNQ_J7CyQ"
)
# Same claims, exp = 2026-01-01 (already expired)
JOSE_EXPIRED_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiI0MiIsImVtYWlsIjoiZm91bmRlckBleGFtcGxlLmNvbSIsImV4cCI6MTc2NzIyNTYwMCwiaWF0IjoxNzY3MTM5MjAwLCJqdGkiOiI3YjBlMGE4ZS01ZjBjLTRjNTUtOWEzOS0yYTFmMGI2ZjZhMTEifQ."
    "1BkIAmSibvaCZNKRsdmTv_eP2E918MTh4LiLJG1wKG0"
)


@pytest.fixture
def fixture_secret(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", FIXTURE_SECRET)


def test_jose_minted_token_verifies(fixture_secret):
    payload = security.decode_token(JOSE_TOKEN)
    assert payload == {
        "sub": "42",
        "email": "founder@example.com",
        "exp": 4102444800,
        "iat": 1794441600,
        "jti": "7b0e0a8e-5f0c-4c55-9a39-2a1f0b6f6a11",
    }


def test_jose_minted_expired_token_rejected(fixture_secret):
    assert security.decode_token(JOSE_EXPIRED_TOKEN) is None
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(JOSE_EXPIRED_TOKEN, FIXTURE_SECRET, algorithms=["HS256"])


def test_jose_minted_token_rejected_with_wrong_secret(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", FIXTURE_SECRET + "-other")
    assert security.decode_token(JOSE_TOKEN) is None


def test_new_tokens_keep_the_same_wire_format(fixture_secret):
    token = security.create_access_token({"sub": "42"})
    header = jwt.get_unverified_header(token)
    assert header == {"alg": "HS256", "typ": "JWT"}
    payload = security.decode_token(token)
    assert payload["sub"] == "42"
    assert isinstance(payload["exp"], int) and isinstance(payload["iat"], int)
    assert payload["jti"]


def test_tampered_token_rejected(fixture_secret):
    head, body, sig = JOSE_TOKEN.split(".")
    flipped = sig[:-2] + ("AA" if sig[-2:] != "AA" else "BB")
    assert security.decode_token(f"{head}.{body}.{flipped}") is None
