"""Keep demo sessions inside their sandbox.

Demo users (per-visitor throwaway accounts and the legacy shared account) may
use the product on their own sample company, but may not reach admin routes or
anything that sends email, invites, shares or touches billing/integrations on
the platform's behalf. The decision is made here, once, rather than in each
endpoint, so a new send endpoint under these prefixes is covered by default.

Only requests that match a rule pay for the user lookup.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

MUTATING = {"POST", "PUT", "PATCH", "DELETE"}

# Any method.
BLOCK_ALL_PREFIXES = (
    "/admin",
    "/auth/admin",
)

# Mutating methods only.
BLOCK_WRITE_PREFIXES = (
    "/auth/change-password",
    "/workspace",          # members and invites
    "/email-templates",
    "/email-tracking",
    "/email",
    "/leads",
    "/billing",
    "/connectors",
    "/integrations",
    "/api-keys",
    "/messaging",
)

# Mutating paths that send something to a third party wherever they live.
BLOCK_WRITE_PATTERN = re.compile(r"/(share|share-[\w-]+|invites?|send|send-[\w-]+|resend)(/|$)")

DENIED = {"detail": "Not available in the demo. Sign up free to use this with your own company."}


def _normalize(path: str) -> str:
    if path.startswith("/api/"):
        path = path[4:]
    return path


def is_blocked_for_demo(method: str, path: str) -> bool:
    p = _normalize(path)
    if any(p == x or p.startswith(x + "/") for x in BLOCK_ALL_PREFIXES):
        return True
    if method.upper() not in MUTATING:
        return False
    if any(p == x or p.startswith(x + "/") or p.startswith(x + "-") for x in BLOCK_WRITE_PREFIXES):
        return True
    return bool(BLOCK_WRITE_PATTERN.search(p))


def _request_user_email(request: Request) -> Optional[str]:
    from server.core.security import AUTH_COOKIE_NAME, decode_token

    token = None
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if not token:
        token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    sub = payload.get("sub")
    if not sub or sub == "master":
        return None
    try:
        uid = int(sub)
    except (TypeError, ValueError):
        return None
    from server.core.db import SessionLocal
    from server.models.user import User

    db = SessionLocal()
    try:
        row = db.query(User.email).filter(User.id == uid).first()
        return row[0] if row else None
    finally:
        db.close()


class DemoGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if is_blocked_for_demo(request.method, request.url.path):
            from server.core.demo_workspace import is_demo_email

            try:
                email = _request_user_email(request)
            except Exception as e:  # never let the guard take the API down
                logger.warning("demo guard lookup failed: %s", e)
                email = None
            if email and is_demo_email(email):
                return JSONResponse(status_code=403, content=DENIED)
        return await call_next(request)
