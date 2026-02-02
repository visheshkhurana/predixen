"""Web search client using Perplexity API for company research."""
import os
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


async def search_company_info(company_name: str, website: Optional[str] = None) -> Dict[str, Any]:
    """
    Search for company information using Perplexity API.
    
    Args:
        company_name: Name of the company to search for
        website: Optional company website for more accurate results
        
    Returns:
        Dictionary containing company information and citations
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    
    if not api_key:
        return {
            "success": False,
            "error": "PERPLEXITY_API_KEY not configured",
            "description": None,
            "citations": []
        }
    
    search_query = f"Tell me about the company {company_name}"
    if website:
        search_query += f" with website {website}"
    
    search_query += """. Provide a concise business summary including:
1. What the company does (product/service)
2. Target market and customers
3. Business model
4. Key value proposition
5. Industry/sector
Keep the summary under 200 words and focus on factual information."""
    
    payload = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [
            {
                "role": "system",
                "content": "You are a business analyst providing concise company summaries. Focus on factual, verifiable information. Write in third person."
            },
            {
                "role": "user",
                "content": search_query
            }
        ],
        "temperature": 0.2,
        "top_p": 0.9,
        "return_images": False,
        "return_related_questions": False,
        "search_recency_filter": "month",
        "stream": False,
        "max_tokens": 500
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
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
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "description": None,
                    "citations": []
                }
            
            data = response.json()
            
            content = ""
            if data.get("choices") and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "")
            
            citations = data.get("citations", [])
            
            return {
                "success": True,
                "description": content,
                "citations": citations,
                "model": data.get("model"),
                "usage": data.get("usage")
            }
            
    except httpx.TimeoutException:
        logger.error("Perplexity API timeout")
        return {
            "success": False,
            "error": "Request timeout",
            "description": None,
            "citations": []
        }
    except Exception as e:
        logger.error(f"Perplexity API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "description": None,
            "citations": []
        }
