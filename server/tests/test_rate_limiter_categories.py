"""Rate-limit categories must match the paths FastAPI actually sees.

Express strips /api before proxying, so /api/... and /... both have to work.
"""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request

from server.middleware.rate_limiter import RateLimiterMiddleware


def _category(path: str):
    mw = RateLimiterMiddleware(FastAPI(), rate_limit_simulation=10, rate_limit_api=60)
    req = Mock(spec=Request)
    req.url.path = path
    return mw._get_category(req)


@pytest.mark.parametrize(
    "path",
    [
        "/simulations",
        "/api/simulations",
        "/scenarios/42/simulate",
        "/api/scenarios/42/simulate",
        "/companies/7/simulate-enhanced",
        "/companies/7/simulate-multi",
    ],
)
def test_simulation_paths_get_the_simulation_bucket(path):
    assert _category(path)[0] == "simulation"


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
        "/explain-simulation",
    ],
)
def test_llm_paths_get_a_stricter_bucket(path):
    category, limit = _category(path)
    assert category == "llm"
    assert limit < 60


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/auth/login", "auth"),
        ("/api/auth/login", "auth"),
        ("/api/health", "health"),
        ("/csv-import/upload", "upload"),
        ("/companies/7", "api"),
        ("/companies/7/chat/feedback", "api"),
    ],
)
def test_other_categories_unchanged(path, expected):
    assert _category(path)[0] == expected
