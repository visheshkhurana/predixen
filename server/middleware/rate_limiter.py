"""
Rate limiting middleware for FastAPI application.

Uses PostgreSQL-backed persistent storage with fixed window algorithm.
Stale entries are cleaned up by a background task every 5 minutes.
"""

import os
import asyncio
import ipaddress
import threading
import time
from typing import Tuple, Optional
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

_cleanup_task_started = False

# Two trusted proxies sit in front of this process: Railway's public edge, then
# the Express app. server/index.ts sets `trust proxy` to 1 and proxies /api to
# FastAPI, so FastAPI's TCP peer is Express on loopback, not the visitor.
#
# The edge sets X-Real-IP to the client and replaces a caller-supplied value.
# Express forwards that header unchanged. req.ip is the rightmost
# X-Forwarded-For hop, which on Railway is the shared edge address, so it is
# not the bucket. X-Real-IP is the client only when the socket peer is
# loopback (127.0.0.1, ::1, or IPv4-mapped ::ffff:127.0.0.1) — the Express
# proxy. A direct connection to this process (uvicorn binds every interface)
# can put any address in X-Real-IP, and trusting it opens a fresh bucket per
# request.
#
# Uvicorn's proxy-headers middleware rewrites scope["client"] from
# X-Forwarded-For before the application runs, which hides the loopback peer.
# server.main:asgi_app records the TCP peer on extensions["peer_host"] first.
# Production starts uvicorn with --no-proxy-headers so that record is Express,
# not the forwarded address. socket_host() reads it.
#
# When X-Real-IP is not trusted, take the client from X-Forwarded-For with
# exactly two trusted hops. The chain is the header, left to right, plus the
# socket peer. The two rightmost addresses are the proxies. The client is the
# address immediately before them. A leftmost value the caller wrote is
# untrusted and must not open a new bucket.
TRUSTED_PROXY_HOPS = 2
PEER_HOST_KEY = "peer_host"

# In-process window for POST /leads. The PostgreSQL counter is shared across
# processes when the database is up, and it fails open when it is not. This
# window does not. One replica (railway.json numReplicas) is the production
# shape; the database counter still applies when it succeeds.
_LEAD_HITS: dict[str, list[float]] = {}
_LEAD_LOCK = threading.Lock()

_HEADER_NAMES = {
    "x-real-ip": ("x-real-ip", "X-Real-IP", "X-Real-Ip"),
    "x-forwarded-for": ("x-forwarded-for", "X-Forwarded-For", "X-Forwarded-for"),
}


def _header(headers, name: str) -> str:
    if headers is None:
        return ""
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return ""
    for candidate in _HEADER_NAMES.get(name, (name,)):
        try:
            value = getter(candidate, None)
        except TypeError:
            value = getter(candidate)
        if value:
            return str(value).strip()
    return ""


def _canonical_ip(value: str) -> str:
    text = (value or "").strip()
    if not text or "@" in text:
        return ""
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    if "%" in text:
        text = text.split("%", 1)[0]
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return ""


def _forwarded_ips(value: str) -> list[str]:
    return [ip for ip in (_canonical_ip(part) for part in str(value or "").split(",")) if ip]


def _is_loopback(value: str) -> bool:
    text = _canonical_ip(value)
    if not text:
        return False
    try:
        addr = ipaddress.ip_address(text)
    except ValueError:
        return False
    if addr.is_loopback:
        return True
    # A dual-stack listener reports 127.0.0.1 as ::ffff:127.0.0.1. Python does
    # not treat that as loopback; it is still the Express proxy on this host.
    mapped = getattr(addr, "ipv4_mapped", None)
    return bool(mapped is not None and mapped.is_loopback)


def socket_host(request) -> str:
    """TCP peer, not the address Uvicorn derived from X-Forwarded-For.

    asgi_app stashes the peer before proxy headers run. A request that did not
    pass through that wrapper (tests, a direct TestClient) falls back to
    request.client.host, which is the peer when proxy headers are off.
    """
    scope = getattr(request, "scope", None)
    if isinstance(scope, dict):
        extensions = scope.get("extensions") or {}
        if isinstance(extensions, dict):
            peer = extensions.get(PEER_HOST_KEY)
            if peer:
                return str(peer)
    client = getattr(request, "client", None)
    host = getattr(client, "host", "") if client is not None else ""
    return str(host or "")


def client_ip(headers, client_host: str = "") -> str:
    """Real client address for a rate-limit bucket. Never an email.

    X-Real-IP is trusted only when client_host is loopback (Express).
    Otherwise the bucket is the X-Forwarded-For entry in front of exactly
    two trusted hops. See TRUSTED_PROXY_HOPS above.
    """
    if _is_loopback(client_host):
        raw_real = _header(headers, "x-real-ip")
        if raw_real and "," not in raw_real:
            real = _canonical_ip(raw_real)
            if real:
                return real

    chain = _forwarded_ips(_header(headers, "x-forwarded-for"))
    socket_ip = _canonical_ip(client_host)
    if socket_ip:
        chain.append(socket_ip)
    index = len(chain) - TRUSTED_PROXY_HOPS - 1
    if index >= 0:
        return chain[index]
    if socket_ip:
        return socket_ip
    host = (client_host or "").strip()
    if host and "@" not in host:
        return host[:200]
    return ""


def lead_window_limited(
    key: str,
    *,
    limit: int = 8,
    window: float = 60.0,
    now: Optional[float] = None,
    store: Optional[dict] = None,
) -> Tuple[bool, int]:
    """True when this key is over the lead window. A rejected call does not count.

    The database counter fails open. This one is what makes the 9th POST in a
    minute a 429 when Postgres is down, and when the handler never runs because
    body validation already failed.
    """
    bucket = _LEAD_HITS if store is None else store
    stamp = time.monotonic() if now is None else now
    with _LEAD_LOCK:
        hits = [seen for seen in bucket.get(key, []) if stamp - seen < window]
        if len(hits) >= limit:
            bucket[key] = hits
            retry = 1
            if hits:
                retry = max(1, int(window - (stamp - hits[0])) + 1)
            return True, retry
        hits.append(stamp)
        bucket[key] = hits
        return False, 0


def _get_engine():
    from server.core.db import engine
    return engine


async def _cleanup_stale_entries():
    """Background task that deletes rate_limit rows older than 10 minutes every 5 minutes."""
    while True:
        try:
            await asyncio.sleep(300)
            engine = _get_engine()
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
            with engine.connect() as conn:
                result = conn.execute(
                    text("DELETE FROM rate_limits WHERE window_start < :cutoff"),
                    {"cutoff": cutoff}
                )
                deleted = result.rowcount
                conn.commit()
                if deleted > 0:
                    logger.debug(f"Cleaned up {deleted} stale rate limit entries")
        except Exception as e:
            logger.warning(f"Rate limit cleanup error: {e}")


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using PostgreSQL-backed fixed window algorithm.

    Supports different rate limits for different endpoint categories:
    - Auth endpoints (login, register, forgot-password)
    - Admin auth endpoints (stricter)
    - Upload endpoints (file uploads)
    - Simulation endpoints (expensive Monte Carlo)
    - General API endpoints
    - Health check endpoints (no limit)
    - Public lead capture (POST /leads), tighter than the general API cap
    """

    AUTH_PATHS = {"/auth/login", "/auth/register", "/auth/forgot-password"}
    ADMIN_AUTH_PATHS = {"/auth/admin/login"}
    UPLOAD_PATHS = {"/csv-import", "/api/upload"}
    HEALTH_PATHS = {"/health", "/"}
    SIMULATION_PATHS = {"/api/simulations"}
    # Express strips the /api prefix before FastAPI sees the request. Both
    # forms are listed so a direct hit and a proxied hit share this cap.
    # The number is a class constant. Lead capture does not read an environment variable.
    LEAD_PATHS = {"/leads", "/api/leads"}
    LEAD_RATE_LIMIT = 8

    WINDOW_SECONDS = 60

    def __init__(
        self,
        app,
        rate_limit_auth: int = 5,
        rate_limit_api: int = 60,
        rate_limit_upload: int = 10,
        rate_limit_admin_login: int = 3,
        rate_limit_simulation: int = 10,
    ):
        super().__init__(app)

        self.rate_limit_auth = int(os.getenv("RATE_LIMIT_AUTH", str(rate_limit_auth)))
        self.rate_limit_admin_login = int(os.getenv("RATE_LIMIT_ADMIN_LOGIN", str(rate_limit_admin_login)))
        self.rate_limit_api = int(os.getenv("RATE_LIMIT_API", str(rate_limit_api)))
        self.rate_limit_upload = int(os.getenv("RATE_LIMIT_UPLOAD", str(rate_limit_upload)))
        self.rate_limit_simulation = int(os.getenv("RATE_LIMIT_SIMULATION", str(rate_limit_simulation)))

        logger.info(
            f"Rate limiter initialized - Auth: {self.rate_limit_auth}/min, "
            f"API: {self.rate_limit_api}/min, Upload: {self.rate_limit_upload}/min, "
            f"Simulation: {self.rate_limit_simulation}/min"
        )

    def _start_cleanup_task(self):
        global _cleanup_task_started
        if not _cleanup_task_started:
            _cleanup_task_started = True
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(_cleanup_stale_entries())
                logger.info("Rate limit cleanup task started (every 5 minutes)")
            except RuntimeError:
                logger.warning("Could not start rate limit cleanup task - no event loop")

    def _get_identifier(self, request: Request) -> str:
        # Same derivation as lead capture. X-Real-IP only from a loopback
        # peer; otherwise the X-Forwarded-For slot in front of two trusted hops.
        return client_ip(request.headers, socket_host(request)) or "unknown"

    def _too_many(self, identifier: str, category: str, limit, retry_after: int) -> JSONResponse:
        logger.warning(
            f"Rate limit exceeded: {identifier} ({category}), "
            f"retry_after={retry_after}s, limit={limit}/min"
        )
        return JSONResponse(
            status_code=429,
            content={
                "detail": f"Rate limit exceeded. Maximum {limit} requests per minute.",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    def _get_category(self, request: Request) -> Tuple[str, int]:
        path = request.url.path

        if path in self.HEALTH_PATHS:
            return ("health", float('inf'))

        lead_path = path.rstrip("/") or path
        if request.method == "POST" and lead_path in self.LEAD_PATHS:
            return ("leads", self.LEAD_RATE_LIMIT)

        if path in self.ADMIN_AUTH_PATHS:
            return ("admin_auth", self.rate_limit_admin_login)

        if path in self.AUTH_PATHS:
            return ("auth", self.rate_limit_auth)

        if path in self.SIMULATION_PATHS:
            return ("simulation", self.rate_limit_simulation)
        if "/simulate" in path and path.startswith("/api/scenarios"):
            return ("simulation", self.rate_limit_simulation)

        if any(upload_path in path for upload_path in self.UPLOAD_PATHS):
            return ("upload", self.rate_limit_upload)

        return ("api", self.rate_limit_api)

    def _check_rate_limit(self, key: str, endpoint: str, limit: int) -> Tuple[bool, int, int]:
        """
        Atomically check and update rate limit in PostgreSQL.

        Uses INSERT ... ON CONFLICT DO UPDATE to handle concurrency safely.
        The CASE expression resets the window if expired, otherwise increments.
        RETURNING gives us the post-update count for accurate remaining calculation.

        Returns:
            (allowed, remaining, retry_after_seconds)
        """
        engine = _get_engine()
        now = datetime.now(timezone.utc)
        window_cutoff = now - timedelta(seconds=self.WINDOW_SECONDS)

        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    INSERT INTO rate_limits (key, endpoint, request_count, window_start)
                    VALUES (:key, :endpoint, 1, :now)
                    ON CONFLICT (key, endpoint) DO UPDATE SET
                        request_count = CASE
                            WHEN rate_limits.window_start < :cutoff THEN 1
                            ELSE rate_limits.request_count + 1
                        END,
                        window_start = CASE
                            WHEN rate_limits.window_start < :cutoff THEN :now
                            ELSE rate_limits.window_start
                        END
                    RETURNING request_count, window_start
                """),
                {"key": key, "endpoint": endpoint, "now": now, "cutoff": window_cutoff}
            ).fetchone()
            conn.commit()

            request_count, window_start = row[0], row[1]

            # SQLite and some drivers return the timestamp as text. Reading
            # tzinfo on a str throws, and the caller then fails open.
            if isinstance(window_start, str):
                window_start = datetime.fromisoformat(window_start)
            if window_start.tzinfo is None:
                window_start = window_start.replace(tzinfo=timezone.utc)

            if request_count > limit:
                elapsed = (now - window_start).total_seconds()
                retry_after = max(1, int(self.WINDOW_SECONDS - elapsed) + 1)
                return (False, 0, retry_after)

            return (True, limit - request_count, 0)

    async def dispatch(self, request: Request, call_next):
        self._start_cleanup_task()

        if request.url.path in self.HEALTH_PATHS:
            try:
                return await call_next(request)
            except BaseException as exc:
                logger.error(f"Middleware error: {exc}")
                return JSONResponse(status_code=500, content={"detail": "Internal server error"})

        identifier = self._get_identifier(request)
        category, limit = self._get_category(request)

        if limit == float('inf'):
            try:
                return await call_next(request)
            except BaseException as exc:
                logger.error(f"Middleware error: {exc}")
                return JSONResponse(status_code=500, content={"detail": "Internal server error"})

        # Count every POST /leads before the database and before the route
        # reads the body. Consent-true and consent-false share this key. A
        # 400 from create_lead, and a 422 from Pydantic, both happen only
        # after this counter has already recorded the request. The database
        # counter fails open, so the in-process window is what answers when
        # the insert throws.
        if category == "leads":
            logger.info("lead bucket key=%s", identifier)
            blocked, retry_after = lead_window_limited(identifier, limit=int(limit))
            if blocked:
                return self._too_many(identifier, category, limit, retry_after)

        try:
            allowed, remaining, retry_after = self._check_rate_limit(identifier, category, int(limit))
        except Exception as e:
            logger.error(f"Rate limit DB error, allowing request: {e}")
            allowed, remaining, retry_after = True, int(limit), 0

        if not allowed:
            return self._too_many(identifier, category, limit, retry_after)

        try:
            response = await call_next(request)
        except BaseException as exc:
            logger.error(f"Middleware error: {exc}")
            response = JSONResponse(status_code=500, content={"detail": "Internal server error"})

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Category"] = category

        return response


def get_rate_limiter_middleware(
    rate_limit_auth: Optional[int] = None,
    rate_limit_api: Optional[int] = None,
    rate_limit_upload: Optional[int] = None,
    rate_limit_simulation: Optional[int] = None,
) -> RateLimiterMiddleware:
    """Factory function to create rate limiter middleware."""
    def middleware_factory(app):
        return RateLimiterMiddleware(
            app,
            rate_limit_auth=rate_limit_auth or 5,
            rate_limit_api=rate_limit_api or 60,
            rate_limit_upload=rate_limit_upload or 10,
            rate_limit_simulation=rate_limit_simulation or 10,
        )
    return middleware_factory
