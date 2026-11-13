"""Rate-limit categories must match the paths FastAPI actually sees.

Ported from #138. Express strips /api before proxying, so the old
"/api/scenarios/.../simulate" rule never matched a real request and every
simulation and paid-LLM call fell into the general 60/min bucket.
"""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request

from server.middleware.rate_limiter import RateLimiterMiddleware


def _category(path: str, method: str = "POST"):
    mw = RateLimiterMiddleware(FastAPI(), rate_limit_simulation=10, rate_limit_api=60, rate_limit_llm=20)
    req = Mock(spec=Request)
    req.url.path = path
    req.method = method
    return mw._get_category(req)


@pytest.mark.parametrize(
    "path",
    [
        "/scenarios/42/simulate",
        "/api/scenarios/42/simulate",
        "/simulations/run",
        "/simulations/sensitivity",
        "/companies/7/simulate",
        "/companies/7/simulate-enhanced",
        "/companies/7/simulate-multi",
        "/companies/7/simulate-scenarios-enhanced",
        "/companies/7/sensitivity-analysis",
        "/api/companies/7/sensitivity-analysis/",
    ],
)
def test_simulation_posts_get_the_simulation_bucket(path):
    assert _category(path) == ("simulation", 10)


@pytest.mark.parametrize(
    "path",
    [
        "/companies/7/chat",
        "/api/companies/7/chat",
        "/companies/7/quick-chat",
        "/companies/7/doc-generator/generate",
        "/companies/7/competitors/3/scan",
        "/lookup/company-from-website",
        "/api/lookup/company-from-website",
        "/simulation-copilot/narrative/7",
        "/simulation-copilot/prompt/7",
        "/explain-simulation",
        "/llm/chat",
        "/llm/smart-chat",
    ],
)
def test_llm_posts_get_a_stricter_bucket(path):
    category, limit = _category(path)
    assert category == "llm"
    assert limit < 60


@pytest.mark.parametrize(
    "path,method,expected",
    [
        ("/simulations/jobs/abc", "GET", "api"),  # job polling must not burn the simulation cap
        ("/simulations/jobs", "GET", "api"),
        ("/companies/7/chat", "GET", "api"),
        ("/companies/7/chat/feedback", "POST", "api"),
        ("/simulation-copilot/validate", "POST", "api"),
        ("/companies/7", "POST", "api"),
        ("/auth/login", "POST", "auth"),
        ("/leads", "POST", "leads"),
        ("/csv-import/upload", "POST", "upload"),
        ("/health", "GET", "health"),
    ],
)
def test_other_requests_keep_their_bucket(path, method, expected):
    assert _category(path, method)[0] == expected


def test_llm_limit_is_configurable(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_LLM", "5")
    mw = RateLimiterMiddleware(FastAPI())
    assert mw.rate_limit_llm == 5
