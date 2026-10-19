"""Pin the HS256 assumption that keeps python-jose's one reachable attack closed.

python-jose 3.5.0 is a direct dependency with a critical advisory and no upstream
fix. Its reachable attack is algorithm confusion: a token that claims an
asymmetric family is verified against the HMAC secret. That needs asymmetric
keys, and this app only ever signs and verifies HS256, so the attack is dormant.

It stays dormant only while nothing signs with another algorithm. Nothing fails
today if someone changes `ALGORITHM`, so these tests make that change fail.
"""
import base64
import json

from jose import jwt as jose_jwt

from server.core.config import settings
from server.core.security import create_access_token, decode_token


def test_tokens_are_signed_with_hs256():
    token = create_access_token({"sub": "1"})

    assert jose_jwt.get_unverified_header(token)["alg"] == "HS256"


def test_the_configured_algorithm_is_hs256():
    assert settings.ALGORITHM == "HS256"


def test_decode_rejects_a_token_signed_with_another_hmac_family():
    # Signed with the app's own secret, so only the algorithm allow-list can
    # reject this. Without the pin, python-jose would accept it.
    token = jose_jwt.encode({"sub": "1"}, settings.SECRET_KEY, algorithm="HS512")

    assert decode_token(token) is None


def test_decode_rejects_an_unsigned_token():
    header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(b'{"sub":"1"}').rstrip(b"=").decode()

    assert decode_token(f"{header}.{body}.") is None
