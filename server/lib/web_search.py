"""Web search client using AI for company research."""
import os
import httpx
import logging
from typing import Optional, Dict, Any
from openai import OpenAI

logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


def _get_company_prompt(company_name: str, website: Optional[str] = None) -> str:
    """Generate the prompt for company research."""
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
    
    return search_query


async def _search_with_perplexity(company_name: str, website: Optional[str] = None) -> Dict[str, Any]:
    """Search using Perplexity API (real-time web search)."""
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    
    if not api_key:
        return {"success": False, "error": "not_configured"}
    
    search_query = _get_company_prompt(company_name, website)
    
    payload = {
        "model": "sonar",
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
                return {"success": False, "error": f"API error: {response.status_code}"}
            
            data = response.json()
            
            content = ""
            if data.get("choices") and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "")
            
            citations = data.get("citations", [])
            
            return {
                "success": True,
                "description": content,
                "citations": citations,
                "source": "perplexity"
            }
            
    except httpx.TimeoutException:
        return {"success": False, "error": "timeout"}
    except Exception as e:
        logger.error(f"Perplexity API error: {e}")
        return {"success": False, "error": str(e)}


def _search_with_openai(company_name: str, website: Optional[str] = None) -> Dict[str, Any]:
    """Search using OpenAI API (uses model's training knowledge)."""
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    
    if not base_url or not api_key:
        return {"success": False, "error": "OpenAI not configured"}
    
    try:
        client = OpenAI(base_url=base_url, api_key=api_key)
        
        search_query = _get_company_prompt(company_name, website)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a business analyst providing concise company summaries. 
Focus on factual, verifiable information. Write in third person.
If you don't have reliable information about a company, say so clearly.
Do not make up information."""
                },
                {
                    "role": "user",
                    "content": search_query
                }
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        content = response.choices[0].message.content if response.choices else ""
        
        return {
            "success": True,
            "description": content,
            "citations": [],
            "source": "openai",
            "note": "Generated from AI knowledge (not real-time web search)"
        }
        
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return {"success": False, "error": str(e)}


async def search_company_info(company_name: str, website: Optional[str] = None) -> Dict[str, Any]:
    """
    Search for company information using available AI providers.
    
    Tries Perplexity first (real-time web search), falls back to OpenAI.
    
    Args:
        company_name: Name of the company to search for
        website: Optional company website for more accurate results
        
    Returns:
        Dictionary containing company information and citations
    """
    result = await _search_with_perplexity(company_name, website)
    
    if result.get("success"):
        return result
    
    if result.get("error") == "not_configured":
        logger.info("Perplexity not configured, falling back to OpenAI")
        openai_result = _search_with_openai(company_name, website)
        return openai_result
    
    return {
        "success": False,
        "error": result.get("error", "Unknown error"),
        "description": None,
        "citations": []
    }
