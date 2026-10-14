"""Verify Resend webhook signatures.

Resend signs webhooks with Svix. The signed content is
``{id}.{timestamp}.{raw body}``. The key is the base64 payload of the
``whsec_...`` secret from the Resend dashboard. ``svix-signature`` (or the
Standard Webhooks alias ``webhook-signature``) holds space-separated
``v1,<base64 hmac-sha256>`` entries.

Both receivers call ``require_valid_signature`` before parsing the body or
writing a row:

- secret unset → 503. This is fail-closed in production, and also outside it:
  ``NODE_ENV`` defaults to development when unset, so a production-only check
  would accept a forged event on a misconfigured deploy.
- secret set and the signature is missing, wrong, or outside the timestamp
  tolerance → 401
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import logging
import os
import time
from typing import Mapping, Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Svix default. Reject timestamps further than this from now, in either direction.
TOLERANCE_SECONDS = 5 * 60

_SVIX_ID = ("svix-id", "webhook-id")
_SVIX_TIMESTAMP = ("svix-timestamp", "webhook-timestamp")
_SVIX_SIGNATURE = ("svix-signature", "webhook-signature")


def webhook_secret() -> str:
    return (os.environ.get("RESEND_WEBHOOK_SECRET") or "").strip()


def is_production() -> bool:
    """Same resolution as ``server.core.config``: NODE_ENV, then ENVIRONMENT.

    Read on each request so a missing secret fails closed in production even
    when the process started before the variable was set, and so tests can
    flip the environment without rebuilding the cached Settings object.
    """
    node_env = (os.getenv("NODE_ENV") or "").strip()
    if node_env:
        return node_env == "production"
    return (os.getenv("ENVIRONMENT") or "development").strip() == "production"


def _header(headers: Mapping[str, str], names: tuple[str, ...]) -> str:
    lowered = {str(key).lower(): value for key, value in headers.items()}
    for name in names:
        value = lowered.get(name)
        if value:
            return str(value).strip()
    return ""


def _secret_bytes(secret: str) -> bytes:
    raw = secret[len("whsec_"):] if secret.startswith("whsec_") else secret
    try:
        key = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("RESEND_WEBHOOK_SECRET is not valid base64") from exc
    if not key:
        raise ValueError("RESEND_WEBHOOK_SECRET decoded to an empty key")
    return key


def sign(secret: str, msg_id: str, timestamp: str, body: bytes) -> str:
    signed = f"{msg_id}.{timestamp}.".encode() + body
    digest = hmac.new(_secret_bytes(secret), signed, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _signatures_match(candidate: str, expected: str) -> bool:
    if len(candidate) != len(expected):
        return False
    return hmac.compare_digest(candidate, expected)


def verify(
    secret: str,
    headers: Mapping[str, str],
    body: bytes,
    now: Optional[float] = None,
) -> bool:
    """True when the headers carry a valid, fresh v1 signature for ``body``."""
    msg_id = _header(headers, _SVIX_ID)
    timestamp = _header(headers, _SVIX_TIMESTAMP)
    signature_header = _header(headers, _SVIX_SIGNATURE)
    if not (msg_id and timestamp and signature_header):
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    current = time.time() if now is None else now
    if abs(current - ts) > TOLERANCE_SECONDS:
        return False
    try:
        expected = sign(secret, msg_id, timestamp, body)
    except (ValueError, TypeError):
        logger.error("[resend-webhook] RESEND_WEBHOOK_SECRET is not valid base64")
        return False
    for part in signature_header.split():
        version, separator, candidate = part.partition(",")
        if separator != "," or version != "v1":
            continue
        if _signatures_match(candidate, expected):
            return True
    return False


def require_valid_signature(headers: Mapping[str, str], body: bytes) -> None:
    """Raise before the caller parses the body or writes a row.

    A missing secret is refused in every environment (503). That is what
    "fail closed in production" requires: ``NODE_ENV`` / ``ENVIRONMENT``
    default to development when unset, so a production-only check would
    accept a forged event on a misconfigured deploy. A missing, wrong, or
    stale signature is 401 whenever a secret is configured.
    """
    secret = webhook_secret()
    if not secret:
        logger.error(
            "[resend-webhook] RESEND_WEBHOOK_SECRET is not set; refusing webhook (production=%s)",
            is_production(),
        )
        raise HTTPException(
            status_code=503,
            detail="RESEND_WEBHOOK_SECRET is not configured",
        )
    if not verify(secret, headers, body):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
