"""Verify Resend webhook signatures (Resend signs with Svix).

Without this, anyone could POST fake email.opened / email.clicked events to
/api/notifications/resend-webhook and rewrite the open/click classification.

Signed content is ``{svix-id}.{svix-timestamp}.{raw body}``; the key is the
base64 part of the ``whsec_...`` secret from the Resend dashboard; the
``svix-signature`` header holds space-separated ``v1,<base64 hmac-sha256>``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import time
from typing import Mapping, Optional

logger = logging.getLogger(__name__)

TOLERANCE_SECONDS = 5 * 60


def webhook_secret() -> str:
    return (os.environ.get("RESEND_WEBHOOK_SECRET") or "").strip()


def _secret_bytes(secret: str) -> bytes:
    raw = secret[len("whsec_"):] if secret.startswith("whsec_") else secret
    return base64.b64decode(raw)


def sign(secret: str, msg_id: str, timestamp: str, body: bytes) -> str:
    signed = f"{msg_id}.{timestamp}.".encode() + body
    digest = hmac.new(_secret_bytes(secret), signed, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def verify(
    secret: str,
    headers: Mapping[str, str],
    body: bytes,
    now: Optional[float] = None,
) -> bool:
    """True when the Svix headers carry a valid, fresh signature for body."""
    msg_id = headers.get("svix-id") or ""
    timestamp = headers.get("svix-timestamp") or ""
    signature_header = headers.get("svix-signature") or ""
    if not (msg_id and timestamp and signature_header):
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    now = time.time() if now is None else now
    if abs(now - ts) > TOLERANCE_SECONDS:
        return False
    try:
        expected = sign(secret, msg_id, timestamp, body)
    except (ValueError, TypeError):
        logger.error("[resend-webhook] RESEND_WEBHOOK_SECRET is not valid base64")
        return False
    for part in signature_header.split():
        version, _, candidate = part.partition(",")
        if version == "v1" and hmac.compare_digest(candidate, expected):
            return True
    return False
