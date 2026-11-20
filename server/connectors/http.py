"""Shared HTTP client for connectors: waits and retries when a vendor
rate-limits us.

Before this, every connector treated a 429 like any other error: it logged,
stopped paging and reported a sync with fewer rows than the account has, with
nothing telling the founder the data was cut short. Pipedrive (token budget),
Mixpanel (query limits), HubSpot, Shopify, Xero, QuickBooks and others all
document 429 with a Retry-After header.

`http_client(**kwargs)` takes the same arguments as httpx.AsyncClient and wraps
its transport in RetryTransport:

- 429: retry any method. The vendor refused the request without acting on
  it, so resending a POST (Ramp/Keka token calls, NetSuite SuiteQL) is safe.
- 502/503/504: retry only GET/HEAD, which are safe to repeat.
- Wait for Retry-After (seconds or an HTTP date) when given, else 1s, 2s, 4s
  with jitter; never more than MAX_WAIT per wait or TOTAL_BUDGET per request,
  so a Sync Now click can't hang for minutes.

httpx.AsyncClient is looked up at call time, so tests that monkeypatch it
(with a MockTransport) keep working.
"""

from __future__ import annotations

import asyncio
import email.utils
import logging
import random
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
MAX_WAIT = 20.0
TOTAL_BUDGET = 45.0
RETRY_ANY_METHOD = {429}
RETRY_SAFE_METHOD = {502, 503, 504}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def retry_after_seconds(value: Optional[str], now: Optional[float] = None) -> Optional[float]:
    """Seconds to wait from a Retry-After header: delta-seconds or HTTP-date."""
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    return max(0.0, when.timestamp() - (now if now is not None else time.time()))


class RetryTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        inner: Optional[httpx.AsyncBaseTransport] = None,
        max_retries: int = MAX_RETRIES,
        max_wait: float = MAX_WAIT,
        total_budget: float = TOTAL_BUDGET,
        sleep=asyncio.sleep,
    ) -> None:
        self._inner = inner or httpx.AsyncHTTPTransport()
        self._max_retries = max_retries
        self._max_wait = max_wait
        self._total_budget = total_budget
        self._sleep = sleep

    def _should_retry(self, request: httpx.Request, status: int) -> bool:
        if status in RETRY_ANY_METHOD:
            return True
        return status in RETRY_SAFE_METHOD and request.method.upper() in SAFE_METHODS

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        waited = 0.0
        attempt = 0
        while True:
            response = await self._inner.handle_async_request(request)
            if attempt >= self._max_retries or not self._should_retry(request, response.status_code):
                return response
            wait = retry_after_seconds(response.headers.get("Retry-After"))
            if wait is None:
                wait = (2 ** attempt) + random.uniform(0, 0.5)
            wait = min(wait, self._max_wait)
            if waited + wait > self._total_budget:
                logger.warning(
                    "%s %s: rate limited (%s), retry budget spent; giving up",
                    request.method, request.url.host, response.status_code,
                )
                return response
            await response.aclose()
            logger.info(
                "%s %s: HTTP %s, retrying in %.1fs (attempt %d/%d)",
                request.method, request.url.host, response.status_code, wait, attempt + 1, self._max_retries,
            )
            await self._sleep(wait)
            waited += wait
            attempt += 1

    async def aclose(self) -> None:
        await self._inner.aclose()


def http_client(**kwargs: Any) -> httpx.AsyncClient:
    """httpx.AsyncClient with RetryTransport around its transport."""
    inner = kwargs.pop("transport", None)
    if inner is None:
        # httpx ignores these on the client once a transport is given, so
        # hand them to the transport we build.
        transport_kw = {k: kwargs.pop(k) for k in
                        ("verify", "cert", "http1", "http2", "limits", "trust_env", "proxy", "retries")
                        if k in kwargs}
        inner = httpx.AsyncHTTPTransport(**transport_kw)
    kwargs["transport"] = RetryTransport(inner)
    return httpx.AsyncClient(**kwargs)
