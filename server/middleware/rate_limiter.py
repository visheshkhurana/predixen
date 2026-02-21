"""
Rate limiting middleware for FastAPI application.

Implements token bucket algorithm with in-memory storage for rate limiting.
No external dependencies required (uses Python standard library only).
"""

import time
import os
from typing import Dict, Tuple, Optional
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket implementation for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens in the bucket
            refill_rate: Tokens per second to refill
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def is_allowed(self) -> bool:
        """Check if request is allowed and consume a token if available."""
        current_time = time.time()
        time_passed = current_time - self.last_refill

        # Add tokens based on time passed
        tokens_to_add = time_passed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = current_time

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    def get_retry_after(self) -> int:
        """Calculate seconds until next token is available."""
        if self.tokens >= 1:
            return 0

        time_to_next_token = (1 - self.tokens) / self.refill_rate
        return max(1, int(time_to_next_token) + 1)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm.

    Supports different rate limits for different endpoint categories:
    - Auth endpoints (login, register, admin/login)
    - Upload endpoints (file uploads)
    - General API endpoints
    - Health check endpoints (no limit)

    Rate limits can be configured via environment variables or constructor parameters.
    """

    # Endpoint category patterns
    AUTH_PATHS = {"/auth/login", "/auth/register"}
    ADMIN_AUTH_PATHS = {"/auth/admin/login"}  # Stricter rate limiting for admin
    UPLOAD_PATHS = {"/csv-import", "/api/upload"}  # Endpoints containing upload operations
    HEALTH_PATHS = {"/health", "/"}

    def __init__(
        self,
        app,
        rate_limit_auth: int = 5,  # requests per minute
        rate_limit_api: int = 60,  # requests per minute
        rate_limit_upload: int = 10,  # requests per minute
        rate_limit_admin_login: int = 3,  # requests per minute (stricter)
    ):
        """
        Initialize rate limiter middleware.

        Args:
            app: FastAPI application
            rate_limit_auth: Auth requests per minute (default: 5)
            rate_limit_api: API requests per minute (default: 60)
            rate_limit_upload: Upload requests per minute (default: 10)
            rate_limit_admin_login: Admin login requests per minute (default: 3)
        """
        super().__init__(app)

        # Load from environment variables if set, otherwise use parameters
        self.rate_limit_auth = int(
            os.getenv("RATE_LIMIT_AUTH", str(rate_limit_auth))
        )
        self.rate_limit_admin_login = int(
            os.getenv("RATE_LIMIT_ADMIN_LOGIN", str(rate_limit_admin_login))
        )
        self.rate_limit_api = int(
            os.getenv("RATE_LIMIT_API", str(rate_limit_api))
        )
        self.rate_limit_upload = int(
            os.getenv("RATE_LIMIT_UPLOAD", str(rate_limit_upload))
        )

        # Store token buckets per identifier (IP or user)
        # Structure: {identifier: {category: TokenBucket}}
        self.buckets: Dict[str, Dict[str, TokenBucket]] = defaultdict(dict)

        logger.info(
            f"Rate limiter initialized - Auth: {self.rate_limit_auth}/min, "
            f"API: {self.rate_limit_api}/min, Upload: {self.rate_limit_upload}/min"
        )

    def _get_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting (IP address or user ID).

        Priority: user_id from token > X-Forwarded-For > client.host
        """
        # Try to get user_id from token if authenticated
        try:
            # Check for Authorization header and extract user context
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                # Could decode JWT here, but using IP for now is simpler
                # and works for public/private distinction
                pass
        except Exception:
            pass

        # Use X-Forwarded-For for load balanced environments, fallback to client IP
        if "X-Forwarded-For" in request.headers:
            return request.headers["X-Forwarded-For"].split(",")[0].strip()

        return request.client.host if request.client else "unknown"

    def _get_category(self, request: Request) -> Tuple[str, int]:
        """
        Determine rate limit category and get the limit.

        Returns:
            Tuple of (category_name, limit_per_minute)
        """
        path = request.url.path

        # Check health endpoints first (no limit)
        if path in self.HEALTH_PATHS:
            return ("health", float('inf'))

        # Check admin auth endpoints (stricter limit)
        if path in self.ADMIN_AUTH_PATHS:
            return ("admin_auth", self.rate_limit_admin_login)

        # Check auth endpoints
        if path in self.AUTH_PATHS:
            return ("auth", self.rate_limit_auth)

        # Check upload endpoints
        if any(upload_path in path for upload_path in self.UPLOAD_PATHS):
            return ("upload", self.rate_limit_upload)

        # Default to API limit
        return ("api", self.rate_limit_api)

    def _get_or_create_bucket(
        self, identifier: str, category: str, limit: int
    ) -> TokenBucket:
        """Get existing bucket or create new one."""
        if category not in self.buckets[identifier]:
            # Convert requests per minute to requests per second
            refill_rate = limit / 60.0
            self.buckets[identifier][category] = TokenBucket(
                capacity=limit,
                refill_rate=refill_rate
            )
        return self.buckets[identifier][category]

    def _cleanup_old_buckets(self):
        """
        Periodically clean up buckets for identifiers with no activity.
        Called on every request - only actually cleans every N requests to avoid overhead.
        """
        # Simple cleanup every 1000 requests (can be tuned)
        if not hasattr(self, '_request_count'):
            self._request_count = 0

        self._request_count += 1

        if self._request_count % 1000 == 0:
            current_time = time.time()
            # Remove buckets that haven't been accessed in 1 hour
            identifiers_to_remove = []

            for identifier, categories in self.buckets.items():
                for category, bucket in categories.items():
                    # Simple heuristic: if last_refill is > 1 hour old
                    if current_time - bucket.last_refill > 3600:
                        identifiers_to_remove.append(identifier)
                        break

            for identifier in identifiers_to_remove:
                del self.buckets[identifier]

            if identifiers_to_remove:
                logger.debug(
                    f"Cleaned up {len(identifiers_to_remove)} inactive rate limit buckets"
                )

    async def dispatch(self, request: Request, call_next):
        """Process request through rate limiter."""
        # Skip rate limiting for health checks
        if request.url.path in self.HEALTH_PATHS:
            return await call_next(request)

        # Get identifier and category
        identifier = self._get_identifier(request)
        category, limit = self._get_category(request)

        # Check if limit is infinite (health endpoints)
        if limit == float('inf'):
            return await call_next(request)

        # Get or create bucket
        bucket = self._get_or_create_bucket(identifier, category, int(limit))

        # Check if request is allowed
        if not bucket.is_allowed():
            retry_after = bucket.get_retry_after()

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

        # Perform cleanup occasionally
        self._cleanup_old_buckets()

        # Process request
        response = await call_next(request)

        # Add rate limit info headers for visibility
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Category"] = category

        return response


def get_rate_limiter_middleware(
    rate_limit_auth: Optional[int] = None,
    rate_limit_api: Optional[int] = None,
    rate_limit_upload: Optional[int] = None,
) -> RateLimiterMiddleware:
    """
    Factory function to create rate limiter middleware.

    Uses environment variables if provided, otherwise uses defaults.

    Args:
        rate_limit_auth: Auth limit in requests/minute (default: 5)
        rate_limit_api: API limit in requests/minute (default: 60)
        rate_limit_upload: Upload limit in requests/minute (default: 10)

    Returns:
        Middleware class (not instance) for FastAPI.add_middleware()
    """
    def middleware_factory(app):
        return RateLimiterMiddleware(
            app,
            rate_limit_auth=rate_limit_auth or 5,
            rate_limit_api=rate_limit_api or 60,
            rate_limit_upload=rate_limit_upload or 10,
        )

    return middleware_factory
