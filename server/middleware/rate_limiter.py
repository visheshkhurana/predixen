"""
Rate limiting middleware for FastAPI application.

Uses PostgreSQL-backed persistent storage with fixed window algorithm.
Stale entries are cleaned up by a background task every 5 minutes.
"""

import os
import asyncio
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
    """

    AUTH_PATHS = {"/auth/login", "/auth/register", "/auth/forgot-password"}
    ADMIN_AUTH_PATHS = {"/auth/admin/login"}
    UPLOAD_PATHS = {"/csv-import", "/api/upload"}
    HEALTH_PATHS = {"/health", "/"}
    SIMULATION_PATHS = {"/api/simulations"}

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
        if "X-Forwarded-For" in request.headers:
            return request.headers["X-Forwarded-For"].split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_category(self, request: Request) -> Tuple[str, int]:
        path = request.url.path

        if path in self.HEALTH_PATHS:
            return ("health", float('inf'))

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

        try:
            allowed, remaining, retry_after = self._check_rate_limit(identifier, category, int(limit))
        except Exception as e:
            logger.error(f"Rate limit DB error, allowing request: {e}")
            allowed, remaining, retry_after = True, int(limit), 0

        if not allowed:
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
