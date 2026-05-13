"""
Security Headers Middleware for FounderConsole
Adds CSP, HSTS, X-Frame-Options, and other security headers to all responses.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to every HTTP response."""

    # CSP directives  permissive enough for a React SPA with inline styles,
    # Sentry replay, and common CDN assets, but blocks everything else.
    CSP_POLICY = "; ".join([
        "default-src 'self'",
        "script-src 'self' https://*.sentry.io https://*.sentry-cdn.com",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: blob: https:",
        "connect-src 'self' https://*.sentry.io https://*.ingest.sentry.io https://api.openai.com https://*.replit.dev wss://*.replit.dev https://us.i.posthog.com https://us.posthog.com",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
    ])

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        is_embed = request.url.path.startswith("/embed/")

        # Content Security Policy (relax frame-ancestors for embeddable widgets)
        if is_embed:
            response.headers["Content-Security-Policy"] = self.CSP_POLICY.replace(
                "frame-ancestors 'none'", "frame-ancestors *"
            )
        else:
            response.headers["Content-Security-Policy"] = self.CSP_POLICY

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking (skip for embeddable widget routes)
        if not is_embed:
            response.headers["X-Frame-Options"] = "DENY"

        # Disable old XSS filter (rely on CSP instead)
        response.headers["X-XSS-Protection"] = "0"

        # HSTS  enforce HTTPS for 1 year, include subdomains
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # Prevent caching of sensitive API responses
        if request.url.path.startswith("/api/") or request.url.path.startswith("/auth/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response
