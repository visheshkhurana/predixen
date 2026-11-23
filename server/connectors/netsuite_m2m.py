"""
NetSuite OAuth 2.0 client credentials (machine-to-machine) sign-in.

NetSuite is retiring Token-Based Authentication (OAuth 1.0a) for new
integrations; OAuth 2.0 M2M replaces it for unattended syncs.

How it works:
- FounderConsole makes one EC P-256 key pair per company. The private key is
  stored encrypted with the company's connector data; the founder downloads
  only the public X.509 certificate.
- In NetSuite the admin creates an integration record with "Client
  Credentials (Machine to Machine) Grant" and "REST Web Services", then maps
  it under Setup > Integration > Manage Authentication > OAuth 2.0 Client
  Credentials (M2M) Setup, uploading that certificate. NetSuite returns a
  Certificate ID.
- Each sync signs a short JWT (alg ES256, kid = Certificate ID, iss = Client
  ID, aud = token URL, exp <= 60 min after iat) and trades it for a 60-minute
  access token at the token endpoint. There is no refresh token; a new
  assertion is signed when the token runs out.

Docs: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_162730264820.html
      https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_162790605110.html
      https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_162755359851.html
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Tuple

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

ASSERTION_ALG = "ES256"  # NetSuite accepts PS256/384/512 and ES256/384/512, not RS256
ASSERTION_TTL_SECONDS = 300  # well under NetSuite's 60-minute cap
SCOPES = ["rest_webservices"]
CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
# NetSuite certificates for M2M may be valid for up to two years; stay inside it.
CERT_VALID_DAYS = 720


def account_host(account_id: str) -> str:
    """'1234567_SB1' -> '1234567-sb1' (NetSuite hostnames are lowercase, '-' not '_')."""
    return account_id.strip().lower().replace("_", "-")


def token_url(account_id: str) -> str:
    return f"https://{account_host(account_id)}.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token"


def generate_keypair(common_name: str = "FounderConsole NetSuite") -> Tuple[str, str, datetime]:
    """Return (private key PEM, self-signed certificate PEM, certificate expiry)."""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name[:64])])
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=CERT_VALID_DAYS)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(expires)
        .sign(key, hashes.SHA256())
    )
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return private_pem, cert.public_bytes(serialization.Encoding.PEM).decode(), expires


def build_assertion(account_id: str, client_id: str, certificate_id: str, private_key_pem: str,
                    now: float | None = None) -> str:
    issued = int(now if now is not None else time.time())
    return jwt.encode(
        {
            "iss": client_id,
            "scope": SCOPES,
            "aud": token_url(account_id),
            "iat": issued,
            "exp": issued + ASSERTION_TTL_SECONDS,
            "jti": str(uuid.uuid4()),
        },
        private_key_pem,
        algorithm=ASSERTION_ALG,
        headers={"typ": "JWT", "kid": certificate_id},
    )
