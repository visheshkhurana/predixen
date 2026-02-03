"""
Company lookup API using Perplexity AI to fetch business details from website.
"""
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/lookup", tags=["lookup"])

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


class WebsiteLookupRequest(BaseModel):
    website: str


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
async def lookup_company_from_website(request: WebsiteLookupRequest):
    """
    Use Perplexity AI to fetch company details from a website URL.
    """
    if not PERPLEXITY_API_KEY:
        raise HTTPException(status_code=500, detail="Perplexity API key not configured")
    
    website = request.website.strip()
    if not website:
        raise HTTPException(status_code=400, detail="Website URL is required")
    
    # Ensure URL has protocol
    if not website.startswith(('http://', 'https://')):
        website = f"https://{website}"
    
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
