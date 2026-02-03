from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import httpx
import os
import json
import logging
from datetime import datetime, timedelta
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User

router = APIRouter(tags=["benchmark_search"])
logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
BENCHMARK_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_HOURS = 24


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


def get_cache_key(industry: str, stage: str) -> str:
    return f"{industry.lower().strip()}_{stage.lower().strip()}"


def is_cache_valid(cache_entry: Dict[str, Any]) -> bool:
    if "timestamp" not in cache_entry:
        return False
    cache_time = datetime.fromisoformat(cache_entry["timestamp"])
    return datetime.now() - cache_time < timedelta(hours=CACHE_TTL_HOURS)


async def search_benchmarks_with_perplexity(industry: str, stage: str) -> Dict[str, Any]:
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Perplexity API key not configured")
    
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
        "model": "llama-3.1-sonar-small-128k-online",
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


async def parse_benchmarks_with_ai(perplexity_response: Dict[str, Any], industry: str, stage: str) -> BenchmarkSearchResponse:
    content = perplexity_response.get("choices", [{}])[0].get("message", {}).get("content", "")
    citations = perplexity_response.get("citations", [])
    
    openai_api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    
    if not openai_api_key:
        return parse_benchmarks_fallback(content, citations, industry, stage)
    
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
        }},
        // ... more metrics
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

If a metric is not found in the data, use reasonable industry defaults.
Only return valid JSON, no other text."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a data parser. Return only valid JSON."},
                    {"role": "user", "content": parse_prompt}
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"}
            }
        )
        
        if response.status_code != 200:
            logger.warning(f"OpenAI parsing failed, using fallback: {response.status_code}")
            return parse_benchmarks_fallback(content, citations, industry, stage)
        
        result = response.json()
        parsed_content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        
        try:
            parsed_data = json.loads(parsed_content)
            benchmarks = [
                BenchmarkData(
                    metric_name=b["metric_name"],
                    p25=float(b["p25"]),
                    p50=float(b["p50"]),
                    p75=float(b["p75"]),
                    direction=b.get("direction", "higher_is_better"),
                    source=citations[0] if citations else None,
                    confidence=b.get("confidence", "medium")
                )
                for b in parsed_data.get("benchmarks", [])
            ]
            
            return BenchmarkSearchResponse(
                industry=industry,
                stage=stage,
                benchmarks=benchmarks,
                sources=citations[:5],
                last_updated=datetime.now().isoformat(),
                is_cached=False
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"JSON parsing failed: {e}")
            return parse_benchmarks_fallback(content, citations, industry, stage)


def parse_benchmarks_fallback(content: str, citations: List[str], industry: str, stage: str) -> BenchmarkSearchResponse:
    default_benchmarks = [
        BenchmarkData(metric_name="revenue_growth_mom", p25=5, p50=10, p75=20, direction="higher_is_better", confidence="low"),
        BenchmarkData(metric_name="gross_margin", p25=60, p50=70, p75=80, direction="higher_is_better", confidence="low"),
        BenchmarkData(metric_name="burn_multiple", p25=4, p50=2.5, p75=1.5, direction="lower_is_better", confidence="low"),
        BenchmarkData(metric_name="runway_months", p25=12, p50=18, p75=24, direction="higher_is_better", confidence="low"),
        BenchmarkData(metric_name="ltv_cac_ratio", p25=2, p50=3, p75=5, direction="higher_is_better", confidence="low"),
        BenchmarkData(metric_name="churn_rate", p25=8, p50=5, p75=3, direction="lower_is_better", confidence="low"),
        BenchmarkData(metric_name="net_revenue_retention", p25=90, p50=100, p75=120, direction="higher_is_better", confidence="low"),
        BenchmarkData(metric_name="cac_payback_months", p25=18, p50=12, p75=8, direction="lower_is_better", confidence="low"),
    ]
    
    return BenchmarkSearchResponse(
        industry=industry,
        stage=stage,
        benchmarks=default_benchmarks,
        sources=citations[:5] if citations else ["Default SaaS benchmarks"],
        last_updated=datetime.now().isoformat(),
        is_cached=False
    )


@router.post("/benchmarks/search", response_model=BenchmarkSearchResponse)
async def search_industry_benchmarks(
    request: BenchmarkSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cache_key = get_cache_key(request.industry, request.stage)
    
    if cache_key in BENCHMARK_CACHE and is_cache_valid(BENCHMARK_CACHE[cache_key]):
        cached = BENCHMARK_CACHE[cache_key]
        return BenchmarkSearchResponse(
            industry=cached["industry"],
            stage=cached["stage"],
            benchmarks=[BenchmarkData(**b) for b in cached["benchmarks"]],
            sources=cached["sources"],
            last_updated=cached["last_updated"],
            is_cached=True
        )
    
    try:
        perplexity_response = await search_benchmarks_with_perplexity(request.industry, request.stage)
        result = await parse_benchmarks_with_ai(perplexity_response, request.industry, request.stage)
        
        BENCHMARK_CACHE[cache_key] = {
            "industry": result.industry,
            "stage": result.stage,
            "benchmarks": [b.model_dump() for b in result.benchmarks],
            "sources": result.sources,
            "last_updated": result.last_updated,
            "timestamp": datetime.now().isoformat()
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Benchmark search failed: {e}")
        return parse_benchmarks_fallback("", [], request.industry, request.stage)


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
    current_user: User = Depends(get_current_user)
):
    BENCHMARK_CACHE.clear()
    return {"message": "Benchmark cache cleared", "cleared_at": datetime.now().isoformat()}
