"""
Company lookup API using Perplexity AI to fetch business details from website.
"""
import os
import re
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from server.core.security import get_current_user
from server.models.user import User
from typing import Optional

router = APIRouter(prefix="/lookup", tags=["lookup"])

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# Each lookup spends a paid Perplexity call, so it is capped per user on top of
# the per-IP API limit. In-process (one Railway replica); a restart resets it.
LOOKUP_RATE_LIMIT = int(os.environ.get("COMPANY_LOOKUP_RATE_LIMIT", "10"))
LOOKUP_RATE_WINDOW_SECONDS = 3600

# A registrable hostname: dot-separated labels and an alphabetic (or punycode) TLD.
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:(?!-)[a-z0-9-]{1,63}(?<!-)\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})$"
)


class _SlidingWindowLimiter:
    """Per-key sliding window, in process."""

    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key, limit: int, window: float) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            if len(self._hits) > 10000:
                for stale in [k for k, q in self._hits.items() if not q or now - q[-1] >= window]:
                    self._hits.pop(stale, None)
            return True

    def reset(self):
        with self._lock:
            self._hits.clear()


_lookup_limiter = _SlidingWindowLimiter()


def normalize_website(raw: str) -> str:
    """Return an http(s) URL on a real domain, or raise HTTPException(400).

    The value is interpolated into an LLM prompt, so anything that is not a
    website (free text, credentials, a bare word like "localhost") is refused.
    """
    website = (raw or "").strip()
    if not website:
        raise HTTPException(status_code=400, detail="Website URL is required")
    if any(ch.isspace() for ch in website) or any(ord(ch) < 0x20 for ch in website):
        raise HTTPException(status_code=400, detail="Website URL is not valid")
    if not website.lower().startswith(("http://", "https://")):
        website = f"https://{website}"
    try:
        parts = urlsplit(website)
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError:
        raise HTTPException(status_code=400, detail="Website URL is not valid")
    if (
        parts.scheme.lower() not in ("http", "https")
        or parts.username
        or parts.password
        or not _DOMAIN_RE.match(host)
    ):
        raise HTTPException(status_code=400, detail="Website URL is not valid")
    return website


class WebsiteLookupRequest(BaseModel):
    website: str = Field(..., max_length=253)


class CompanyDetails(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    business_model: Optional[str] = None
    stage: Optional[str] = None
    founded: Optional[str] = None
    headquarters: Optional[str] = None
    key_products: Optional[str] = None
    target_market: Optional[str] = None


class WebsiteLookupResponse(BaseModel):
    success: bool
    company: Optional[CompanyDetails] = None
    summary: Optional[str] = None
    error: Optional[str] = None


@router.post("/company-from-website", response_model=WebsiteLookupResponse)
async def lookup_company_from_website(
    request: WebsiteLookupRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Use Perplexity AI to fetch company details from a website URL.
    """
    website = normalize_website(request.website)

    if not _lookup_limiter.allow(
        getattr(current_user, "id", None), LOOKUP_RATE_LIMIT, LOOKUP_RATE_WINDOW_SECONDS
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many company lookups. Please try again later.",
            headers={"Retry-After": str(LOOKUP_RATE_WINDOW_SECONDS)},
        )

    if not PERPLEXITY_API_KEY:
        raise HTTPException(status_code=500, detail="Perplexity API key not configured")

    prompt = f"""Analyze the company website at {website} and provide the following information in a structured format:

1. Company Name: The official company name
2. Description: A brief 2-3 sentence description of what the company does
3. Industry: The primary industry (choose from: fintech, general_saas, ecommerce, healthtech, edtech, proptech, marketplace, consumer, enterprise, other)
4. Business Model: How the company makes money (e.g., SaaS subscription, marketplace fees, transaction fees, etc.)
5. Stage: The company's growth stage (choose from: pre_seed, seed, series_a, series_b, growth)
6. Founded: Year the company was founded (if available)
7. Headquarters: Location of headquarters (if available)
8. Key Products/Services: Main products or services offered
9. Target Market: Who are their primary customers

Please provide accurate, factual information based on what you can find about this company. If you cannot find certain information, indicate "Unknown".

Format your response as:
NAME: [company name]
DESCRIPTION: [description]
INDUSTRY: [industry]
BUSINESS_MODEL: [business model]
STAGE: [stage]
FOUNDED: [year]
HEADQUARTERS: [location]
KEY_PRODUCTS: [products/services]
TARGET_MARKET: [target market]
SUMMARY: [A brief 1-paragraph executive summary about the company]"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                PERPLEXITY_API_URL,
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a business analyst specializing in researching companies. Provide accurate, factual information about companies based on their websites and public information."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
            )
            
            if response.status_code != 200:
                return WebsiteLookupResponse(
                    success=False,
                    error=f"Perplexity API error: {response.status_code}"
                )
            
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Parse the structured response
            company = CompanyDetails()
            summary = ""
            
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith("NAME:"):
                    company.name = line.replace("NAME:", "").strip()
                elif line.startswith("DESCRIPTION:"):
                    company.description = line.replace("DESCRIPTION:", "").strip()
                elif line.startswith("INDUSTRY:"):
                    industry = line.replace("INDUSTRY:", "").strip().lower()
                    # Map to our industry values
                    industry_map = {
                        "fintech": "fintech",
                        "saas": "general_saas",
                        "general_saas": "general_saas",
                        "ecommerce": "ecommerce",
                        "e-commerce": "ecommerce",
                        "healthtech": "healthtech",
                        "health tech": "healthtech",
                        "edtech": "edtech",
                        "education": "edtech",
                        "proptech": "proptech",
                        "real estate": "proptech",
                        "marketplace": "marketplace",
                        "consumer": "consumer",
                        "enterprise": "enterprise",
                    }
                    company.industry = industry_map.get(industry, "other")
                elif line.startswith("BUSINESS_MODEL:"):
                    company.business_model = line.replace("BUSINESS_MODEL:", "").strip()
                elif line.startswith("STAGE:"):
                    stage = line.replace("STAGE:", "").strip().lower().replace(" ", "_")
                    stage_map = {
                        "pre_seed": "pre_seed",
                        "pre-seed": "pre_seed",
                        "seed": "seed",
                        "series_a": "series_a",
                        "series a": "series_a",
                        "series_b": "series_b",
                        "series b": "series_b",
                        "growth": "growth",
                        "series_c": "growth",
                        "series c": "growth",
                    }
                    company.stage = stage_map.get(stage, "seed")
                elif line.startswith("FOUNDED:"):
                    company.founded = line.replace("FOUNDED:", "").strip()
                elif line.startswith("HEADQUARTERS:"):
                    company.headquarters = line.replace("HEADQUARTERS:", "").strip()
                elif line.startswith("KEY_PRODUCTS:"):
                    company.key_products = line.replace("KEY_PRODUCTS:", "").strip()
                elif line.startswith("TARGET_MARKET:"):
                    company.target_market = line.replace("TARGET_MARKET:", "").strip()
                elif line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
            
            return WebsiteLookupResponse(
                success=True,
                company=company,
                summary=summary or company.description
            )
            
    except httpx.TimeoutException:
        return WebsiteLookupResponse(
            success=False,
            error="Request timed out. Please try again."
        )
    except Exception as e:
        return WebsiteLookupResponse(
            success=False,
            error=f"Failed to fetch company details: {str(e)}"
        )
