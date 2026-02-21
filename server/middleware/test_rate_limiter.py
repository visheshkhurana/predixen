"""
Unit tests for rate limiting middleware.

Tests the token bucket algorithm and middleware behavior under various conditions.
Run with: pytest server/middleware/test_rate_limiter.py
"""

import asyncio
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from server.middleware.rate_limiter import TokenBucket, RateLimiterMiddleware


class TestTokenBucket:
    """Test the TokenBucket implementation."""

    def test_bucket_initialization(self):
        """Test token bucket initializes with correct capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.capacity == 10
        assert bucket.tokens == 10
        assert bucket.refill_rate == 1.0

    def test_bucket_allows_requests_within_limit(self):
        """Test bucket allows requests when tokens are available."""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        # Should allow 5 requests
        for i in range(5):
            assert bucket.is_allowed() is True
        # Should deny 6th request
        assert bucket.is_allowed() is False

    def test_bucket_denies_requests_exceeding_limit(self):
        """Test bucket denies requests when no tokens available."""
        bucket = TokenBucket(capacity=1, refill_rate=1.0)
        assert bucket.is_allowed() is True
        assert bucket.is_allowed() is False
        assert bucket.is_allowed() is False

    def test_bucket_refills_over_time(self):
        """Test bucket refills tokens based on time passed."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)  # 1 token per second
        # Consume all tokens
        for _ in range(10):
            bucket.is_allowed()
        assert bucket.is_allowed() is False

        # Simulate 1 second passing
        import time
        original_time = bucket.last_refill
        bucket.last_refill = original_time - 1.1  # 1.1 seconds ago

        # Should now have 1 token
        assert bucket.is_allowed() is True
        assert bucket.is_allowed() is False

    def test_bucket_respects_capacity(self):
        """Test bucket never exceeds capacity even with long idle time."""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        # Consume all tokens
        for _ in range(5):
            bucket.is_allowed()

        # Simulate 100 seconds passing
        bucket.last_refill -= 100
        # Should still be capped at 5, not 105
        for i in range(5):
            assert bucket.is_allowed() is True
        assert bucket.is_allowed() is False

    def test_get_retry_after(self):
        """Test retry_after calculation."""
        bucket = TokenBucket(capacity=1, refill_rate=1.0)
        # Consume the token
        bucket.is_allowed()
        # Should need 1 second for next token
        retry = bucket.get_retry_after()
        assert retry >= 1


class TestRateLimiterMiddleware:
    """Test the rate limiter middleware."""

    def test_middleware_initialization(self):
        """Test middleware initializes with correct limits."""
        app = FastAPI()
        middleware = RateLimiterMiddleware(
            app,
            rate_limit_auth=3,
            rate_limit_api=30,
            rate_limit_upload=5,
        )
        assert middleware.rate_limit_auth == 3
        assert middleware.rate_limit_api == 30
        assert middleware.rate_limit_upload == 5

    def test_get_identifier_from_client_ip(self):
        """Test identifier extraction from client IP."""
        app = FastAPI()
        middleware = RateLimiterMiddleware(app)

        # Mock request with client IP
        mock_request = Mock(spec=Request)
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {}

        identifier = middleware._get_identifier(mock_request)
        assert identifier == "192.168.1.1"

    def test_get_identifier_from_x_forwarded_for(self):
        """Test identifier extraction from X-Forwarded-For header."""
        app = FastAPI()
        middleware = RateLimiterMiddleware(app)

        # Mock request with X-Forwarded-For
        mock_request = Mock(spec=Request)
        mock_request.client.host = "10.0.0.1"
        mock_request.headers = {"X-Forwarded-For": "203.0.113.42, 198.51.100.2"}

        identifier = middleware._get_identifier(mock_request)
        assert identifier == "203.0.113.42"

    def test_category_detection_auth(self):
        """Test auth endpoint category detection."""
        app = FastAPI()
        middleware = RateLimiterMiddleware(
            app,
            rate_limit_auth=5,
            rate_limit_api=60,
        )

        mock_request = Mock(spec=Request)
        mock_request.url.path = "/auth/login"

        category, limit = middleware._get_category(mock_request)
        assert category == "auth"
        assert limit == 5

    def test_category_detection_upload(self):
        """Test upload endpoint category detection."""
        app = FastAPI()
        middleware = RateLimiterMiddleware(
            app,
            rate_limit_api=60,
            rate_limit_upload=10,
        )

        mock_request = Mock(spec=Request)
        mock_request.url.path = "/csv-import/upload"

        category, limit = middleware._get_category(mock_request)
        assert category == "upload"
        assert limit == 10

    def test_category_detection_api(self):
        """Test default API endpoint category detection."""
        app = FastAPI()
        middleware = RateLimiterMiddleware(
            app,
            rate_limit_api=60,
        )

        mock_request = Mock(spec=Request)
        mock_request.url.path = "/companies"

        category, limit = middleware._get_category(mock_request)
        assert category == "api"
        assert limit == 60

    def test_category_detection_health(self):
        """Test health endpoint has no limit."""
        app = FastAPI()
        middleware = RateLimiterMiddleware(app)

        for path in ["/health", "/"]:
            mock_request = Mock(spec=Request)
            mock_request.url.path = path

            category, limit = middleware._get_category(mock_request)
            assert category == "health"
            assert limit == float('inf')

    def test_bucket_creation_and_reuse(self):
        """Test buckets are created and reused correctly."""
        app = FastAPI()
        middleware = RateLimiterMiddleware(app, rate_limit_api=10)

        # Create first bucket
        bucket1 = middleware._get_or_create_bucket("user1", "api", 10)
        # Get same bucket
        bucket2 = middleware._get_or_create_bucket("user1", "api", 10)

        assert bucket1 is bucket2

    @pytest.mark.asyncio
    async def test_health_endpoint_no_rate_limit(self):
        """Test health endpoints bypass rate limiting."""
        app = FastAPI()

        @app.get("/health")
        def health():
            return {"status": "ok"}

        app.add_middleware(RateLimiterMiddleware)

        client = TestClient(app)

        # Should not be rate limited even with many requests
        for i in range(10):
            response = client.get("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self):
        """Test rate limit is enforced on non-health endpoints."""
        app = FastAPI()

        @app.get("/api/test")
        def test_endpoint():
            return {"ok": True}

        # Add middleware with very strict limit for testing
        app.add_middleware(RateLimiterMiddleware, rate_limit_api=2)

        client = TestClient(app)

        # First 2 requests should succeed
        for i in range(2):
            response = client.get("/api/test")
            assert response.status_code == 200

        # 3rd request should be rate limited
        response = client.get("/api/test")
        assert response.status_code == 429
        assert "rate limit exceeded" in response.json()["detail"].lower()
        assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_rate_limit_response_format(self):
        """Test rate limit response has correct format."""
        app = FastAPI()

        @app.get("/api/test")
        def test_endpoint():
            return {"ok": True}

        app.add_middleware(RateLimiterMiddleware, rate_limit_api=1)

        client = TestClient(app)

        # Exhaust limit
        client.get("/api/test")
        response = client.get("/api/test")

        assert response.status_code == 429
        data = response.json()
        assert "detail" in data
        assert "retry_after" in data
        assert isinstance(data["retry_after"], int)
        assert response.headers.get("Retry-After") is not None

    def test_different_ips_have_separate_limits(self):
        """Test different IPs have independent rate limit buckets."""
        app = FastAPI()
        middleware = RateLimiterMiddleware(app, rate_limit_api=1)

        # Create buckets for two different IPs
        bucket1 = middleware._get_or_create_bucket("192.168.1.1", "api", 1)
        bucket2 = middleware._get_or_create_bucket("192.168.1.2", "api", 1)

        # Both should allow 1 request
        assert bucket1.is_allowed() is True
        assert bucket2.is_allowed() is True

        # Both should now be rate limited
        assert bucket1.is_allowed() is False
        assert bucket2.is_allowed() is False

    def test_cleanup_removes_idle_buckets(self):
        """Test cleanup removes buckets with no activity."""
        app = FastAPI()
        middleware = RateLimiterMiddleware(app)

        # Create a bucket
        bucket = middleware._get_or_create_bucket("user1", "api", 10)
        bucket.last_refill = 0  # Set to very old timestamp

        # Manually trigger many requests to trigger cleanup
        middleware._request_count = 999
        middleware._cleanup_old_buckets()

        # Bucket should be removed after cleanup
        assert "user1" not in middleware.buckets


class TestEnvironmentVariables:
    """Test environment variable configuration."""

    @patch.dict("os.environ", {
        "RATE_LIMIT_AUTH": "10",
        "RATE_LIMIT_API": "100",
        "RATE_LIMIT_UPLOAD": "20",
    })
    def test_load_from_env_vars(self):
        """Test rate limits load from environment variables."""
        # Need to reload the module to pick up env vars
        from server.middleware.rate_limiter import RateLimiterMiddleware
        app = FastAPI()

        # Don't pass parameters - should use env vars
        middleware = RateLimiterMiddleware(app)
        assert middleware.rate_limit_auth == 10
        assert middleware.rate_limit_api == 100
        assert middleware.rate_limit_upload == 20

    def test_defaults_without_env_vars(self):
        """Test default rate limits are used without env vars."""
        app = FastAPI()
        # Don't set env vars, don't pass parameters
        with patch.dict("os.environ", {}, clear=True):
            middleware = RateLimiterMiddleware(app)
            assert middleware.rate_limit_auth == 5
            assert middleware.rate_limit_api == 60
            assert middleware.rate_limit_upload == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
