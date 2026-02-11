"""
Strategic Web Search Module for Copilot.

Uses Perplexity API for real-time market intelligence, competitor analysis,
industry benchmarks, and current data that the copilot needs for
consultant-grade reasoning.
"""
import os
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

WEB_SEARCH_TRIGGERS = [
    "market", "industry", "benchmark", "competitor", "trend", "average",
    "standard", "best practice", "typical", "compare to", "compared to",
    "sector", "valuation", "funding", "vc", "venture", "series a", "series b",
    "pre-seed", "seed round", "interest rate", "inflation", "economy",
    "regulation", "compliance", "tax", "saas benchmark", "median",
    "percentile", "top quartile", "bottom quartile", "peer", "similar companies",
    "what is a good", "what's a good", "how does my", "am i doing well",
    "news", "latest", "recent", "current market", "2024", "2025", "2026",
    "research", "report", "study", "forecast", "outlook", "prediction",
    "rule of 40", "magic number", "burn multiple", "gross margin benchmark",
    "churn benchmark", "nrr benchmark", "cac benchmark", "ltv benchmark",
    "what should", "optimal", "target", "goal",
    "cogs", "margin", "pricing strategy", "unit economics",
    "tam", "sam", "som", "market size", "addressable market",
    "porter", "five forces", "swot",
    "launch", "new product", "expand", "enter market", "go-to-market",
    "face wash", "skincare", "cosmetic", "fmcg", "consumer product",
    "should i", "is it worth", "feasibility",
]

STRATEGIC_DECISION_PATTERNS = [
    r'\bshould\s+(?:i|we)\s+(?:launch|start|build|create|expand|enter|pivot|add)\b',
    r'\bwhat\s+(?:if|about)\s+(?:launching|starting|building|expanding|entering|adding)\b',
    r'\bis\s+it\s+worth\b',
    r'\bfeasibility\s+of\b',
    r'\bgo[\s-]*to[\s-]*market\b',
    r'\bnew\s+(?:product|market|segment|category|line|vertical)\b',
    r'\blaunch\b.*\b(?:product|service|brand|line)\b',
]


def needs_web_search(message: str, context: Optional[Dict[str, Any]] = None) -> bool:
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in WEB_SEARCH_TRIGGERS):
        return True
    for pattern in STRATEGIC_DECISION_PATTERNS:
        if re.search(pattern, msg_lower):
            return True
    return False


def classify_search_type(message: str) -> str:
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in ["competitor", "compete", "competition", "vs", "versus", "alternative"]):
        return "competitor_analysis"
    if any(kw in msg_lower for kw in ["benchmark", "average", "typical", "median", "percentile", "good"]):
        return "benchmark_lookup"
    if any(kw in msg_lower for kw in ["market size", "tam", "sam", "som", "addressable", "total market"]):
        return "market_sizing"
    if any(kw in msg_lower for kw in ["cogs", "cost of goods", "unit cost", "manufacturing cost"]):
        return "cogs_research"
    if any(kw in msg_lower for kw in ["launch", "new product", "enter market", "go-to-market", "expand into"]):
        return "market_entry"
    if any(kw in msg_lower for kw in ["pricing", "price point", "how to price", "pricing strategy"]):
        return "pricing_research"
    if any(kw in msg_lower for kw in ["trend", "forecast", "outlook", "prediction", "growth rate"]):
        return "trend_analysis"
    return "general_research"


def build_search_query(
    message: str,
    search_type: str,
    company_industry: str = "",
    company_stage: str = "",
    company_name: str = "",
) -> str:
    context_parts = []
    if company_industry and company_industry not in ("N/A", "Not specified"):
        context_parts.append(company_industry)
    if company_stage and company_stage not in ("N/A", "Not specified"):
        context_parts.append(f"{company_stage} stage")
    context_str = " ".join(context_parts) if context_parts else "startup"

    type_suffixes = {
        "competitor_analysis": f"Key competitors, market share, pricing, and differentiation for {context_str}",
        "benchmark_lookup": f"Industry benchmarks and median values for {context_str} companies. Include specific numbers and percentiles.",
        "market_sizing": f"Total addressable market (TAM), serviceable addressable market (SAM), and serviceable obtainable market (SOM). Include market growth rate and key data sources.",
        "cogs_research": f"Typical cost of goods sold (COGS), manufacturing costs, and gross margins. Include per-unit economics where possible.",
        "market_entry": f"Market size, key players, typical margins, customer acquisition costs, barriers to entry, and growth projections.",
        "pricing_research": f"Pricing strategies, typical price points, price elasticity, and competitive pricing landscape.",
        "trend_analysis": f"Current trends, growth projections, and market outlook for 2025-2026.",
        "general_research": f"Provide specific numbers, benchmarks, and data points relevant to {context_str}.",
    }

    suffix = type_suffixes.get(search_type, type_suffixes["general_research"])
    return f"{message}\n\nContext: {suffix}"


SEARCH_SYSTEM_PROMPTS = {
    "competitor_analysis": """You are a competitive intelligence analyst. Provide:
1. Top 3-5 competitors with their estimated revenue/funding
2. Key differentiators and weaknesses of each
3. Market positioning map (who serves which segment)
4. Pricing comparison where available
Be specific with numbers. Cite sources.""",

    "benchmark_lookup": """You are a financial benchmarking analyst specializing in startups. Provide:
1. Industry median and top-quartile values for the requested metrics
2. Stage-appropriate benchmarks (seed vs Series A vs Series B)
3. Year-over-year trends in these benchmarks
4. Sources and sample sizes of benchmark data
Always provide specific numbers, not ranges.""",

    "market_sizing": """You are a market research analyst. Provide:
1. TAM (Total Addressable Market) with methodology
2. SAM (Serviceable Addressable Market)
3. SOM (Serviceable Obtainable Market)
4. Market CAGR (compound annual growth rate)
5. Key market drivers and headwinds
Use bottom-up and top-down approaches. Cite data sources.""",

    "cogs_research": """You are a unit economics analyst. Provide:
1. Typical COGS breakdown for the product/service category
2. Manufacturing/production costs per unit
3. Industry average gross margins
4. Economies of scale thresholds
5. Key cost drivers and optimization levers
Be specific with per-unit numbers and percentages.""",

    "market_entry": """You are a market entry strategist. Provide:
1. Market size and growth trajectory
2. Key players and their market share
3. Typical customer acquisition costs (CAC) in this market
4. Average customer lifetime value (LTV)
5. Barriers to entry and regulatory requirements
6. Recommended go-to-market approach
Be specific with numbers and timelines.""",

    "pricing_research": """You are a pricing strategy consultant. Provide:
1. Current market price points for comparable products/services
2. Pricing models used by competitors (subscription, freemium, per-unit, etc.)
3. Price elasticity observations
4. Recommended pricing strategy with rationale
5. Pricing tiers used by successful companies in this space
Be specific with actual dollar amounts.""",

    "trend_analysis": """You are an industry analyst. Provide:
1. Current market trends with data points
2. Growth rate projections for 2025-2027
3. Emerging technologies or shifts
4. Regulatory changes on the horizon
5. Investment activity (funding rounds, M&A)
Use the most recent data available. Cite sources.""",

    "general_research": """You are a business research analyst for startup founders. Provide specific, data-driven answers with numbers, benchmarks, and citations. Focus on actionable intelligence that helps with business decisions. Be concise but thorough.""",
}


async def search_web(
    query: str,
    search_type: str = "general_research",
    company_industry: str = "",
    company_stage: str = "",
    company_name: str = "",
    db_session=None,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        return {"success": False, "error": "Perplexity API key not configured", "content": "", "citations": [], "search_type": search_type}

    search_query = build_search_query(query, search_type, company_industry, company_stage, company_name)
    system_prompt = SEARCH_SYSTEM_PROMPTS.get(search_type, SEARCH_SYSTEM_PROMPTS["general_research"])

    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": search_query},
        ],
        "temperature": 0.2,
        "top_p": 0.9,
        "return_images": False,
        "return_related_questions": False,
        "search_recency_filter": "month",
        "stream": False,
        "max_tokens": 2000,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                PERPLEXITY_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            if response.status_code != 200:
                logger.error(f"Perplexity search error: {response.status_code} - {response.text}")
                return {"success": False, "error": f"API error: {response.status_code}", "content": "", "citations": [], "search_type": search_type}

            data = response.json()
            content = ""
            if data.get("choices") and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "")

            citations = data.get("citations", [])

            return {
                "success": True,
                "content": content,
                "citations": citations[:10],
                "search_type": search_type,
                "query_used": search_query[:200],
                "timestamp": datetime.utcnow().isoformat(),
            }

    except httpx.TimeoutException:
        logger.warning("Perplexity search timed out")
        return {"success": False, "error": "Search timed out", "content": "", "citations": [], "search_type": search_type}
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return {"success": False, "error": str(e), "content": "", "citations": [], "search_type": search_type}


async def search_for_copilot(
    message: str,
    company_industry: str = "",
    company_stage: str = "",
    company_name: str = "",
    db_session=None,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    if not needs_web_search(message):
        return None

    search_type = classify_search_type(message)

    result = await search_web(
        query=message,
        search_type=search_type,
        company_industry=company_industry,
        company_stage=company_stage,
        company_name=company_name,
        db_session=db_session,
        company_id=company_id,
        user_id=user_id,
    )

    if result.get("success") and result.get("content"):
        return result
    return None


def format_web_research_for_prompt(research: Dict[str, Any]) -> str:
    parts = ["--- WEB RESEARCH RESULTS ---"]
    search_type = research.get("search_type", "general_research")
    type_labels = {
        "competitor_analysis": "Competitive Intelligence",
        "benchmark_lookup": "Industry Benchmarks",
        "market_sizing": "Market Size Analysis",
        "cogs_research": "COGS & Unit Economics Research",
        "market_entry": "Market Entry Analysis",
        "pricing_research": "Pricing Intelligence",
        "trend_analysis": "Market Trends",
        "general_research": "Market Research",
    }
    parts.append(f"Research Type: {type_labels.get(search_type, 'Market Research')}")
    parts.append(f"\n{research.get('content', '')}")

    citations = research.get("citations", [])
    if citations:
        parts.append("\nSources:")
        for i, c in enumerate(citations[:5], 1):
            parts.append(f"  [{i}] {c}")

    parts.append("--- END WEB RESEARCH ---")
    return "\n".join(parts)
