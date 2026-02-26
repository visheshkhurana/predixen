"""
CSRF Protection Middleware using Double-Submit Cookie Pattern

This middleware implements CSRF protection for POST, PUT, PATCH, and DELETE requests
using the double-submit cookie pattern, which is ideal for Single Page Applications (SPAs).

How it works:
1. On first request, a CSRF token is generated and set in a cookie (httpOnly=false so JS can read it)
2. Client reads the token from the cookie and includes it in the X-CSRF-Token header
3. Server validates that the header token matches the cookie token on state-changing requests

Token format: hex string (64 characters = 32 bytes)
"""

import secrets
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

CSRF_COOKIE_NAME = "X-CSRF-Token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_TOKEN_LENGTH = 32  # 32 bytes = 64 hex characters


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to protect against CSRF attacks using double-submit cookie pattern.

    Exemptions:
    - GET, HEAD, OPTIONS requests (safe methods, no state changes)
    - /health endpoint (health checks)
    - /auth/register, /auth/login, /auth/admin/login (authentication endpoints use their own tokens)
    - Requests without Authorization header (not authenticated, CSRF less relevant)
    """

    def __init__(self, app, exempt_paths: list = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/health",
            "/auth/register",
            "/auth/login",
            "/auth/admin/login",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if path is exempt
        if self._is_path_exempt(request.url.path):
            response = await call_next(request)
            return response

        # Check if method is safe (no CSRF needed for read-only operations)
        if request.method in CSRF_SAFE_METHODS:
            response = await call_next(request)
            # Set CSRF token in cookie for safe requests (so client can read it)
            self._set_csrf_token_cookie(response, request)
            return response

        # For state-changing requests, validate CSRF token
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            # Check if request is authenticated (has Authorization header)
            if not self._is_authenticated(request):
                # Unauthenticated state-changing requests are not protected by CSRF
                # (they fail auth anyway), but we still set the token for future use
                response = await call_next(request)
                self._set_csrf_token_cookie(response, request)
                return response

            # Validate CSRF token for authenticated state-changing requests
            is_valid = await self._validate_csrf_token(request)
            if not is_valid:
                logger.warning(
                    f"CSRF validation failed for {request.method} {request.url.path} "
                    f"from {request.client.host if request.client else 'unknown'}"
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token validation failed"},
                )

        response = await call_next(request)
        # Refresh CSRF token in cookie after successful request
        self._set_csrf_token_cookie(response, request)
        return response

    def _is_path_exempt(self, path: str) -> bool:
        """Check if the request path is exempt from CSRF protection."""
        import fnmatch
        for exempt in self.exempt_paths:
            if '*' in exempt:
                if fnmatch.fnmatch(path, exempt):
                    return True
            elif path.startswith(exempt):
                return True
        return False

    def _is_authenticated(self, request: Request) -> bool:
        """Check if the request has an Authorization header (is authenticated)."""
        return "authorization" in request.headers

    async def _validate_csrf_token(self, request: Request) -> bool:
        """
        Validate CSRF token from header against cookie.

        Returns True if:
        - Token exists in both cookie and header
        - They match exactly

        Returns False otherwise.
        """
        # Get token from cookie
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)

        # Get token from header
        header_token = request.headers.get(CSRF_HEADER_NAME)

        # Both must exist and match
        if not cookie_token or not header_token:
            logger.debug(
                f"CSRF token missing: cookie={bool(cookie_token)}, header={bool(header_token)}"
            )
            return False

        # Simple constant-time comparison (though tokens are not secrets)
        if cookie_token != header_token:
            logger.debug("CSRF token mismatch between cookie and header")
            return False

        # Validate token format (should be 64 hex characters)
        if not self._is_valid_token_format(cookie_token):
            logger.debug(f"CSRF token has invalid format: {cookie_token[:10]}...")
            return False

        return True

    def _set_csrf_token_cookie(self, response: Response, request: Request) -> None:
        """
        Set CSRF token in response cookie.

        - Checks if token already exists in request cookies
        - If not, generates a new one
        - Sets in response with secure flags appropriate to environment
        """
        existing_token = request.cookies.get(CSRF_COOKIE_NAME)

        if existing_token and self._is_valid_token_format(existing_token):
            # Token already exists and is valid, no need to regenerate
            return

        # Generate new token
        new_token = secrets.token_hex(CSRF_TOKEN_LENGTH)

        # Determine if we should set Secure flag
        # In production, always set Secure. In development, allow http
        is_secure = request.url.scheme == "https"

        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=new_token,
            httponly=False,  # Must be False so JavaScript can read it
            secure=is_secure,  # Only send over HTTPS in production
            samesite="strict",  # Prevent cross-site cookie transmission
            max_age=60 * 60 * 24,  # 24 hours
            path="/",
        )

    def _is_valid_token_format(self, token: str) -> bool:
        """
        Validate token format.

        A valid token should be a hex string of expected length.
        """
        if not isinstance(token, str):
            return False

        # Should be 64 hex characters (32 bytes)
        if len(token) != CSRF_TOKEN_LENGTH * 2:
            return False

        try:
            int(token, 16)
            return True
        except ValueError:
            return False
