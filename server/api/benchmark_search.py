from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
import httpx
import os
import json
import logging
import re
from collections import OrderedDict
from datetime import datetime, timedelta
from server.core.db import get_db
from server.core.security import get_current_user
from server.api.admin import require_platform_admin
from server.models.user import User

router = APIRouter(tags=["benchmark_search"])
logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
# Bounded LRU: keys are normalized user input, so an unbounded dict grows
# with every distinct industry string anyone types.
BENCHMARK_CACHE: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
CACHE_TTL_HOURS = 24
CACHE_MAX_ENTRIES = 128
_KEY_MAX_LEN = 64

GENERIC_DEFAULTS_SOURCE = "Generic SaaS defaults (not industry-specific)"


class BenchmarkSearchRequest(BaseModel):
    industry: str
    stage: str = "seed"
    metrics: Optional[List[str]] = None


class BenchmarkData(BaseModel):
    metric_name: str
    p25: float
    p50: float
    p75: float
    direction: str
    source: Optional[str] = None
    confidence: str = "medium"


class BenchmarkSearchResponse(BaseModel):
    industry: str
    stage: str
    benchmarks: List[BenchmarkData]
    sources: List[str]
    last_updated: str
    is_cached: bool = False
    # True when live research failed and these are generic SaaS defaults,
    # not benchmarks for the requested industry/stage.
    is_fallback: bool = False
    note: Optional[str] = None


def _normalize_key_part(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")
    return value[:_KEY_MAX_LEN]


def get_cache_key(industry: str, stage: str) -> str:
    return f"{_normalize_key_part(industry)}|{_normalize_key_part(stage)}"


def cache_get(key: str) -> Optional[Dict[str, Any]]:
    entry = BENCHMARK_CACHE.get(key)
    if entry is None:
        return None
    if not is_cache_valid(entry):
        BENCHMARK_CACHE.pop(key, None)
        return None
    BENCHMARK_CACHE.move_to_end(key)
    return entry


def cache_put(key: str, entry: Dict[str, Any]) -> None:
    BENCHMARK_CACHE[key] = entry
    BENCHMARK_CACHE.move_to_end(key)
    while len(BENCHMARK_CACHE) > CACHE_MAX_ENTRIES:
        BENCHMARK_CACHE.popitem(last=False)


def is_cache_valid(cache_entry: Dict[str, Any]) -> bool:
    if "timestamp" not in cache_entry:
        return False
    cache_time = datetime.fromisoformat(cache_entry["timestamp"])
    return datetime.now() - cache_time < timedelta(hours=CACHE_TTL_HOURS)


async def search_benchmarks_with_perplexity(industry: str, stage: str) -> Dict[str, Any]:
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        # Not a client error -- a missing optional integration. Raise a plain
        # exception so the endpoint's generic handler returns the default
        # benchmark set instead of surfacing a 500 to the founder.
        raise RuntimeError("Perplexity API key not configured")
    
    search_query = f"""Find the latest SaaS industry benchmarks for {industry} companies at {stage} stage. 
I need the following metrics with their 25th, 50th (median), and 75th percentile values:
1. Monthly revenue growth rate (%)
2. Gross margin (%)
3. Burn multiple (net burn / net new ARR)
4. Cash runway (months)
5. LTV to CAC ratio
6. Monthly churn rate (%)
7. Net revenue retention (%)
8. CAC payback period (months)

Please provide actual benchmark data from recent reports (2024-2025) from sources like:
- OpenView SaaS Benchmarks
- Bessemer Cloud Index
- KeyBanc SaaS Survey
- ChartMogul Benchmarks
- SaaS Capital reports

Format each metric with p25, p50, p75 values. Indicate whether higher or lower is better for each metric."""

    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a financial analyst specializing in SaaS metrics and benchmarks. Provide accurate, data-driven benchmark information with specific percentile values. Always cite your sources."
            },
            {
                "role": "user",
                "content": search_query
            }
        ],
        "temperature": 0.1,
        "top_p": 0.9,
        "return_related_questions": False,
        "search_recency_filter": "year",
        "stream": False
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            PERPLEXITY_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=502, detail="Failed to fetch benchmarks from search")
        
        return response.json()


async def parse_benchmarks_with_ai(
    perplexity_response: Dict[str, Any],
    industry: str,
    stage: str,
    user_id: Optional[int] = None,
) -> BenchmarkSearchResponse:
    content = perplexity_response.get("choices", [{}])[0].get("message", {}).get("content", "")
    citations = perplexity_response.get("citations", [])
    
    parse_prompt = f"""Parse the following benchmark data into a structured JSON format.
Extract the percentile values (p25, p50, p75) for each metric.

Raw benchmark data:
{content}

Return a JSON object with this exact structure:
{{
    "benchmarks": [
        {{
            "metric_name": "revenue_growth_mom",
            "p25": <number>,
            "p50": <number>,
            "p75": <number>,
            "direction": "higher_is_better" or "lower_is_better",
            "confidence": "high" or "medium" or "low"
        }}
    ]
}}

Expected metrics (use these exact names):
- revenue_growth_mom (Monthly revenue growth %)
- gross_margin (Gross margin %)
- burn_multiple (Burn multiple ratio)
- runway_months (Cash runway in months)
- ltv_cac_ratio (LTV:CAC ratio)
- churn_rate (Monthly churn %)
- net_revenue_retention (NRR %)
- cac_payback_months (CAC payback in months)

Only include a metric when the raw data above states its values. Do not
invent, estimate or fill in defaults for metrics that are missing.
Only return valid JSON, no other text."""

    try:
        from server.lib.llm.llm_router import LLMRouter, TaskType

        llm = LLMRouter(user_id=user_id)
        result = await asyncio.to_thread(
            llm.chat,
            messages=[
                {"role": "system", "content": "You are a data parser. Return only valid JSON."},
                {"role": "user", "content": parse_prompt},
            ],
            task_type=TaskType.DATA_PROCESSING,
            temperature=0,
            max_tokens=2048,
        )
        parsed_data = _extract_json_object(result.get("content") or "")
        benchmarks = []
        for b in parsed_data.get("benchmarks", []) or []:
            try:
                benchmarks.append(BenchmarkData(
                    metric_name=str(b["metric_name"]),
                    p25=float(b["p25"]),
                    p50=float(b["p50"]),
                    p75=float(b["p75"]),
                    direction=b.get("direction", "higher_is_better"),
                    source=citations[0] if citations else None,
                    confidence=b.get("confidence", "medium"),
                ))
            except (KeyError, TypeError, ValueError):
                continue
    except Exception as e:
        logger.warning(f"Benchmark parsing failed, using generic defaults: {e}")
        return parse_benchmarks_fallback(content, citations, industry, stage)

    if not benchmarks:
        return parse_benchmarks_fallback(content, citations, industry, stage)

    return BenchmarkSearchResponse(
        industry=industry,
        stage=stage,
        benchmarks=benchmarks,
        sources=citations[:5],
        last_updated=datetime.now().isoformat(),
        is_cached=False,
    )


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


def parse_benchmarks_fallback(content: str, citations: List[str], industry: str, stage: str) -> BenchmarkSearchResponse:
    default_benchmarks = [
        BenchmarkData(metric_name="revenue_growth_mom", p25=5, p50=10, p75=20, direction="higher_is_better", source=GENERIC_DEFAULTS_SOURCE, confidence="low"),
        BenchmarkData(metric_name="gross_margin", p25=60, p50=70, p75=80, direction="higher_is_better", source=GENERIC_DEFAULTS_SOURCE, confidence="low"),
        BenchmarkData(metric_name="burn_multiple", p25=4, p50=2.5, p75=1.5, direction="lower_is_better", source=GENERIC_DEFAULTS_SOURCE, confidence="low"),
        BenchmarkData(metric_name="runway_months", p25=12, p50=18, p75=24, direction="higher_is_better", source=GENERIC_DEFAULTS_SOURCE, confidence="low"),
        BenchmarkData(metric_name="ltv_cac_ratio", p25=2, p50=3, p75=5, direction="higher_is_better", source=GENERIC_DEFAULTS_SOURCE, confidence="low"),
        BenchmarkData(metric_name="churn_rate", p25=8, p50=5, p75=3, direction="lower_is_better", source=GENERIC_DEFAULTS_SOURCE, confidence="low"),
        BenchmarkData(metric_name="net_revenue_retention", p25=90, p50=100, p75=120, direction="higher_is_better", source=GENERIC_DEFAULTS_SOURCE, confidence="low"),
        BenchmarkData(metric_name="cac_payback_months", p25=18, p50=12, p75=8, direction="lower_is_better", source=GENERIC_DEFAULTS_SOURCE, confidence="low"),
    ]
    
    return BenchmarkSearchResponse(
        industry=industry,
        stage=stage,
        benchmarks=default_benchmarks,
        sources=[GENERIC_DEFAULTS_SOURCE],
        last_updated=datetime.now().isoformat(),
        is_cached=False,
        is_fallback=True,
        note=(
            f"Live benchmarks for {industry} ({stage}) are unavailable right now. "
            "These are generic SaaS defaults, not figures for this industry."
        ),
    )


@router.post("/benchmarks/search", response_model=BenchmarkSearchResponse)
async def search_industry_benchmarks(
    request: BenchmarkSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cache_key = get_cache_key(request.industry, request.stage)

    cached = cache_get(cache_key)
    if cached is not None:
        return BenchmarkSearchResponse(
            industry=cached["industry"],
            stage=cached["stage"],
            benchmarks=[BenchmarkData(**b) for b in cached["benchmarks"]],
            sources=cached["sources"],
            last_updated=cached["last_updated"],
            is_cached=True
        )

    # Cache hits are free; only a miss spends Perplexity + LLM calls.
    from server.core.llm_rate_limit import check_llm_rate_limit
    check_llm_rate_limit(current_user.id)

    try:
        perplexity_response = await search_benchmarks_with_perplexity(request.industry, request.stage)
        result = await parse_benchmarks_with_ai(
            perplexity_response, request.industry, request.stage, user_id=current_user.id
        )
    except Exception as e:
        logger.error(f"Benchmark search failed: {e}")
        return parse_benchmarks_fallback("", [], request.industry, request.stage)

    # Generic defaults are never cached as if they were this industry's data.
    if not result.is_fallback:
        cache_put(cache_key, {
            "industry": result.industry,
            "stage": result.stage,
            "benchmarks": [b.model_dump() for b in result.benchmarks],
            "sources": result.sources,
            "last_updated": result.last_updated,
            "timestamp": datetime.now().isoformat()
        })

    return result


@router.get("/benchmarks/industries")
async def get_supported_industries(
    current_user: User = Depends(get_current_user)
):
    return {
        "industries": [
            {"id": "saas", "name": "SaaS / Software"},
            {"id": "fintech", "name": "Fintech"},
            {"id": "ecommerce", "name": "E-commerce"},
            {"id": "healthtech", "name": "Healthcare Tech"},
            {"id": "marketplace", "name": "Marketplace"},
            {"id": "edtech", "name": "Education Tech"},
            {"id": "proptech", "name": "Real Estate Tech"},
            {"id": "devtools", "name": "Developer Tools"},
        ],
        "stages": [
            {"id": "pre_seed", "name": "Pre-Seed"},
            {"id": "seed", "name": "Seed"},
            {"id": "series_a", "name": "Series A"},
            {"id": "series_b", "name": "Series B"},
            {"id": "growth", "name": "Growth Stage"},
        ]
    }


@router.delete("/benchmarks/cache")
async def clear_benchmark_cache(
    current_user: User = Depends(require_platform_admin)
):
    BENCHMARK_CACHE.clear()
    return {"message": "Benchmark cache cleared", "cleared_at": datetime.now().isoformat()}
