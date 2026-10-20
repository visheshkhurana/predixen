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
    "authorization": ("authorization", "Authorization"),
    "cookie": ("cookie", "Cookie"),
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


# Browser JS can read these on cross-origin responses. Without
# Access-Control-Expose-Headers, `headers.get("Retry-After")` is null and
# Chrome logs "Refused to get unsafe header".
CORS_EXPOSE_HEADERS = [
    "X-Request-ID",
    "Retry-After",
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "X-RateLimit-Category",
    "RateLimit-Limit",
    "RateLimit-Remaining",
    "RateLimit-Reset",
]

# Sliding windows for every category except leads (those keep lead_window_limited).
# The database counter is still updated when Postgres is up. This window is what
# enforces the cap when that insert throws, which used to fail open.
_WINDOW_HITS: dict[str, list[float]] = {}
_WINDOW_LOCK = threading.Lock()

# Auth stays on the client IP even if a session cookie is attached. A valid
# token must not open a fresh login bucket.
IP_ONLY_CATEGORIES = frozenset({"auth", "admin_auth", "leads"})
AUTH_COOKIE_NAME = "auth_token"
READ_BURST_WINDOW_SECONDS = 10


def request_path(path: str) -> str:
    """Path the limiter classifies. Express strips /api before FastAPI sees it.

    Both forms are accepted so a direct hit and a proxied hit share a category.
    """
    text = (path or "").split("?", 1)[0]
    if len(text) > 1 and text.endswith("/"):
        text = text[:-1]
    if text.startswith("/api/"):
        text = text[4:] or "/"
    return text or "/"


def user_sub_from_request(request) -> str:
    """JWT `sub` for a rate-limit bucket. Empty when the token is missing or bad.

    Signature and expiry are checked. Revocation is not: a revoked token still
    shares its owner's bucket, which is the stricter outcome. No database.
    """
    token = ""
    headers = getattr(request, "headers", None)
    authorization = _header(headers, "authorization")
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        cookies = getattr(request, "cookies", None)
        raw_cookie = ""
        if isinstance(cookies, dict):
            raw_cookie = cookies.get(AUTH_COOKIE_NAME) or ""
        else:
            getter = getattr(cookies, "get", None)
            if callable(getter):
                try:
                    value = getter(AUTH_COOKIE_NAME, None)
                except TypeError:
                    value = getter(AUTH_COOKIE_NAME)
                if isinstance(value, str):
                    raw_cookie = value
        if not raw_cookie:
            header_cookie = _header(headers, "cookie")
            for part in header_cookie.split(";"):
                name, _, value = part.strip().partition("=")
                if name == AUTH_COOKIE_NAME and value:
                    raw_cookie = value
                    break
        token = raw_cookie.strip()
    if not token or len(token) > 8192:
        return ""
    try:
        from jose import jwt
        from server.core.config import settings

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return ""
    sub = payload.get("sub") if isinstance(payload, dict) else None
    if sub is None:
        return ""
    text = str(sub).strip()
    if not text or len(text) > 64 or any(c.isspace() for c in text):
        return ""
    return text


def _is_email_send(path: str, method: str) -> bool:
    if method not in {"POST", "PUT", "PATCH"}:
        return False
    if path == "/auth/send-verification":
        return True
    if path == "/email-templates/test" or path.startswith("/email-templates/send"):
        return True
    return path.endswith("/digest/send")


def _is_llm(path: str, method: str) -> bool:
    if "strategic-diagnosis" in path:
        return True
    if method not in {"POST", "PUT", "PATCH"}:
        return False
    if path.endswith("/chat") or "/quick-chat" in path:
        return True
    if path == "/llm" or path.startswith("/llm/"):
        return True
    markers = (
        "/simulation-copilot",
        "/generate-image",
        "/ai-graphics",
        "/memo/export",
        "/web-search",
        "/copilot",
    )
    return any(marker in path for marker in markers)


def _is_simulation_run(path: str, method: str) -> bool:
    if method not in {"POST", "PUT", "PATCH"}:
        return False
    if "/truth/run" in path or path.startswith("/truth-scan"):
        return True
    if "/simulation/v2/run" in path:
        return True
    if "/sensitivity-analysis" in path or "/counter-moves" in path:
        return True
    if "/simulate" in path:
        return True
    if path.endswith("/agent-run"):
        return True
    if "/simulation/accuracy/compute" in path or path.endswith("/simulation/calibrate"):
        return True
    return False


def consume_windows(
    key: str,
    windows: list,
    *,
    now: float,
    store: Optional[dict] = None,
) -> Tuple[bool, int, int, int]:
    """Take one hit from every window, or take none.

    windows is (name, limit, seconds), minute window first.
    Returns (allowed, remaining, retry_after, applied_limit).
    A rejected call does not count. `remaining` is the tightest window after the hit.
    """
    bucket = _WINDOW_HITS if store is None else store
    with _WINDOW_LOCK:
        prepared = []
        for name, limit, window in windows:
            limit = int(limit)
            window = float(window)
            bucket_key = f"{key}|{name}"
            hits = [seen for seen in bucket.get(bucket_key, []) if now - seen < window]
            if len(hits) >= limit:
                bucket[bucket_key] = hits
                retry = 1
                if hits:
                    retry = max(1, int(window - (now - min(hits))) + 1)
                return False, 0, retry, limit
            prepared.append((bucket_key, hits, limit))
        for bucket_key, hits, _limit in prepared:
            hits.append(now)
            bucket[bucket_key] = hits
        remaining = min(limit - len(hits) for _key, hits, limit in prepared)
        return True, remaining, 0, int(windows[0][1])


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
    - Auth endpoints (login, register, forgot-password, reset-password), per IP
    - Admin auth endpoints (stricter), per IP
    - Public lead capture (POST /leads), per IP, tighter than the general cap
    - Email sends, LLM/copilot, and simulation/truth runs, per user when signed in
    - Uploads, per user when signed in
    - Authenticated reads, per user, with a short burst window
    - Everything else (anonymous traffic and ordinary writes), per user or IP
    - Health check endpoints (no limit)

    Anonymous and abuse-prone routes stay strict. A signed-in read does not
    spend the anonymous 60/min bucket: a page fires about 10-20 calls, and
    moving through several pages a minute used to 429 /companies, truth/latest,
    metrics/computed, and baseline.
    """

    AUTH_PATHS = {"/auth/login", "/auth/register", "/auth/forgot-password", "/auth/reset-password"}
    ADMIN_AUTH_PATHS = {"/auth/admin/login"}
    UPLOAD_MARKERS = ("/csv-import", "/upload")
    HEALTH_PATHS = {"/health", "/"}
    # Express strips the /api prefix before FastAPI sees the request.
    # request_path() folds /api/leads onto /leads. The number is a class
    # constant. Lead capture does not read an environment variable.
    LEAD_PATHS = {"/leads"}
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
        rate_limit_read: int = 480,
        rate_limit_read_burst: int = 120,
        rate_limit_llm: int = 20,
        rate_limit_email: int = 5,
        clock=None,
    ):
        super().__init__(app)

        self.rate_limit_auth = int(os.getenv("RATE_LIMIT_AUTH", str(rate_limit_auth)))
        self.rate_limit_admin_login = int(os.getenv("RATE_LIMIT_ADMIN_LOGIN", str(rate_limit_admin_login)))
        self.rate_limit_api = int(os.getenv("RATE_LIMIT_API", str(rate_limit_api)))
        self.rate_limit_upload = int(os.getenv("RATE_LIMIT_UPLOAD", str(rate_limit_upload)))
        self.rate_limit_simulation = int(os.getenv("RATE_LIMIT_SIMULATION", str(rate_limit_simulation)))
        self.rate_limit_read = int(os.getenv("RATE_LIMIT_READ", str(rate_limit_read)))
        self.rate_limit_read_burst = int(os.getenv("RATE_LIMIT_READ_BURST", str(rate_limit_read_burst)))
        self.rate_limit_llm = int(os.getenv("RATE_LIMIT_LLM", str(rate_limit_llm)))
        self.rate_limit_email = int(os.getenv("RATE_LIMIT_EMAIL", str(rate_limit_email)))
        self.read_burst_window = READ_BURST_WINDOW_SECONDS
        self._clock = clock or time.monotonic

        logger.info(
            f"Rate limiter initialized - Auth: {self.rate_limit_auth}/min, "
            f"API: {self.rate_limit_api}/min, Read: {self.rate_limit_read}/min "
            f"(burst {self.rate_limit_read_burst}/{self.read_burst_window}s), "
            f"Upload: {self.rate_limit_upload}/min, "
            f"Simulation: {self.rate_limit_simulation}/min, "
            f"LLM: {self.rate_limit_llm}/min, Email: {self.rate_limit_email}/min"
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

    def _bucket_key(self, request: Request, category: str) -> str:
        ip = self._get_identifier(request) or "unknown"
        if category in IP_ONLY_CATEGORIES:
            return ip
        user = user_sub_from_request(request)
        if user:
            return f"user:{user}"
        return ip

    def _rate_headers(self, limit, remaining, category: str, retry_after: int) -> dict:
        reset = retry_after if retry_after else self.WINDOW_SECONDS
        return {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Category": category,
            "RateLimit-Limit": str(limit),
            "RateLimit-Remaining": str(max(0, remaining)),
            "RateLimit-Reset": str(reset),
        }

    def _too_many(self, identifier: str, category: str, limit, retry_after: int) -> JSONResponse:
        per = "minute"
        if category == "read" and int(limit) == int(self.rate_limit_read_burst):
            per = f"{self.read_burst_window} seconds"
        logger.warning(
            f"Rate limit exceeded: {identifier} ({category}), "
            f"retry_after={retry_after}s, limit={limit}/{per}"
        )
        headers = self._rate_headers(limit, 0, category, retry_after)
        headers["Retry-After"] = str(retry_after)
        return JSONResponse(
            status_code=429,
            content={
                "detail": f"Rate limit exceeded. Maximum {limit} requests per {per}.",
                "retry_after": retry_after,
            },
            headers=headers,
        )

    def _get_category(self, request: Request) -> Tuple[str, int]:
        path = request_path(request.url.path)
        method = (request.method or "GET").upper()

        if path in self.HEALTH_PATHS:
            return ("health", float("inf"))

        if method == "POST" and path in self.LEAD_PATHS:
            return ("leads", self.LEAD_RATE_LIMIT)

        if path in self.ADMIN_AUTH_PATHS:
            return ("admin_auth", self.rate_limit_admin_login)

        if _is_email_send(path, method):
            return ("email", self.rate_limit_email)

        if path in self.AUTH_PATHS:
            return ("auth", self.rate_limit_auth)

        if _is_llm(path, method):
            return ("llm", self.rate_limit_llm)

        if _is_simulation_run(path, method):
            return ("simulation", self.rate_limit_simulation)

        if any(marker in path for marker in self.UPLOAD_MARKERS):
            return ("upload", self.rate_limit_upload)

        # Signed-in reads get their own bucket. Anonymous GETs stay on the
        # strict IP/api cap so an open endpoint cannot spend the read budget.
        if method in {"GET", "HEAD", "OPTIONS"} and user_sub_from_request(request):
            return ("read", self.rate_limit_read)

        return ("api", self.rate_limit_api)

    def _windows_for(self, category: str, limit: int) -> list:
        windows = [(f"{category}:minute", int(limit), float(self.WINDOW_SECONDS))]
        if category == "read":
            windows.append(
                (f"{category}:burst", int(self.rate_limit_read_burst), float(self.read_burst_window))
            )
        return windows

    def _consume(self, bucket_key: str, category: str, limit: int) -> Tuple[bool, int, int, int]:
        now = float(self._clock())
        return consume_windows(
            bucket_key,
            self._windows_for(category, limit),
            now=now,
        )

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

        category, limit = self._get_category(request)

        if limit == float('inf'):
            try:
                return await call_next(request)
            except BaseException as exc:
                logger.error(f"Middleware error: {exc}")
                return JSONResponse(status_code=500, content={"detail": "Internal server error"})

        identifier = self._bucket_key(request, category)

        # Count leads before the database and before the route. The consent
        # 400 is the string create_lead raises after its own counter, and a
        # body that fails validation never enters that function. Either way
        # this cap has to answer first. The database counter fails open, which
        # dropped the limit whenever the insert threw.
        if category == "leads":
            blocked, retry_after = lead_window_limited(identifier, limit=int(limit))
            if blocked:
                return self._too_many(identifier, category, limit, retry_after)
            remaining = int(limit)
        else:
            # In-process window first. A database error used to fail open for
            # every category except leads, so login and reads had no cap when
            # Postgres was down. A rejected call is not counted.
            allowed, remaining, retry_after, applied_limit = self._consume(identifier, category, int(limit))
            if not allowed:
                return self._too_many(identifier, category, applied_limit, retry_after)

        try:
            allowed, db_remaining, retry_after = self._check_rate_limit(identifier, category, int(limit))
            remaining = min(remaining, db_remaining)
        except Exception as e:
            logger.error(f"Rate limit DB error, allowing request: {e}")
            allowed, retry_after = True, 0

        if not allowed:
            return self._too_many(identifier, category, limit, retry_after)

        try:
            response = await call_next(request)
        except BaseException as exc:
            logger.error(f"Middleware error: {exc}")
            response = JSONResponse(status_code=500, content={"detail": "Internal server error"})

        for name, value in self._rate_headers(limit, remaining, category, 0).items():
            response.headers[name] = value

        return response


def get_rate_limiter_middleware(
    rate_limit_auth: Optional[int] = None,
    rate_limit_api: Optional[int] = None,
    rate_limit_upload: Optional[int] = None,
    rate_limit_simulation: Optional[int] = None,
    rate_limit_read: Optional[int] = None,
    rate_limit_read_burst: Optional[int] = None,
    rate_limit_llm: Optional[int] = None,
    rate_limit_email: Optional[int] = None,
) -> RateLimiterMiddleware:
    """Factory function to create rate limiter middleware."""
    def middleware_factory(app):
        return RateLimiterMiddleware(
            app,
            rate_limit_auth=rate_limit_auth or 5,
            rate_limit_api=rate_limit_api or 60,
            rate_limit_upload=rate_limit_upload or 10,
            rate_limit_simulation=rate_limit_simulation or 10,
            rate_limit_read=rate_limit_read or 480,
            rate_limit_read_burst=rate_limit_read_burst or 120,
            rate_limit_llm=rate_limit_llm or 20,
            rate_limit_email=rate_limit_email or 5,
        )
    return middleware_factory
