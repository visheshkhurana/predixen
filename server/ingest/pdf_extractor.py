import os
import json
import logging
from typing import Dict, Any, Optional
import pdfplumber
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL"),
)

EXTRACTION_PROMPT = """Extract from the following Termina financial report all key financial and operational metrics. 
Return the result as a JSON object with these exact keys (use null if not found):

{
  "company_name": "string - the company name",
  "report_date": "string - the date of the report (YYYY-MM-DD format if possible)",
  "currency": "string - the currency code (USD, EUR, GBP, etc.)",
  "monthly_revenue": "number - current monthly revenue",
  "run_rate_revenue": "number - annualized run rate revenue",
  "cogs": "number - cost of goods sold (monthly)",
  "gross_profit": "number - gross profit (monthly)",
  "gross_margin": "number - gross margin as percentage (0-100)",
  "operating_income": "number - operating income (monthly)",
  "operating_margin": "number - operating margin as percentage",
  "net_burn": "number - monthly net burn rate",
  "cash_balance": "number - current cash on hand",
  "runway_months": "number - estimated runway in months",
  "yoy_growth": "number - year over year growth rate as percentage",
  "mom_growth": "number - month over month growth rate as percentage",
  "payroll": "number - monthly payroll expense",
  "opex": "number - monthly operating expenses (excluding COGS)",
  "headcount": "number - current employee count",
  "arr": "number - annual recurring revenue",
  "mrr": "number - monthly recurring revenue",
  "ndr": "number - net dollar retention as percentage",
  "logo_retention": "number - customer logo retention as percentage",
  "customers": "number - total customer count",
  "arpu": "number - average revenue per user/customer",
  "ltv": "number - customer lifetime value",
  "cac": "number - customer acquisition cost",
  "ltv_cac_ratio": "number - LTV to CAC ratio",
  "summary": "string - brief 2-3 sentence summary of the company's financial health"
}

Important instructions:
- Extract actual numbers, not formatted strings
- Convert percentages to numbers (e.g., 85% becomes 85)
- Use null for any metrics not found in the report
- If a metric can be calculated from other metrics, calculate it
- Be precise with the numbers - do not estimate or guess

Here is the report text:

"""


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using pdfplumber."""
    try:
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            row_text = " | ".join(str(cell) if cell else "" for cell in row)
                            text_parts.append(row_text)
        
        full_text = "\n".join(text_parts)
        
        if not full_text.strip():
            raise ValueError("No text could be extracted from the PDF. The file may contain only images.")
        
        return full_text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise


def extract_metrics_with_openai(pdf_text: str) -> Dict[str, Any]:
    """Use OpenAI to extract financial metrics from PDF text."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst AI that extracts structured data from financial reports. Always respond with valid JSON only, no markdown formatting."
                },
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT + pdf_text[:15000]
                }
            ],
            max_tokens=2000,
            temperature=0.1,
        )
        
        content = response.choices[0].message.content
        
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        metrics = json.loads(content)
        return metrics
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI response as JSON: {e}")
        raise ValueError(f"Failed to parse extracted metrics: {e}")
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        raise


def process_termina_pdf(file_path: str) -> Dict[str, Any]:
    """Process a Termina PDF and extract financial metrics."""
    pdf_text = extract_text_from_pdf(file_path)
    
    metrics = extract_metrics_with_openai(pdf_text)
    
    baseline_data = {
        "monthly_revenue": metrics.get("monthly_revenue") or metrics.get("mrr"),
        "gross_margin": metrics.get("gross_margin"),
        "operating_expenses": metrics.get("opex"),
        "payroll": metrics.get("payroll"),
        "cogs": metrics.get("cogs"),
        "cash_balance": metrics.get("cash_balance"),
        "headcount": metrics.get("headcount"),
        "yoy_growth": metrics.get("yoy_growth"),
        "mom_growth": metrics.get("mom_growth"),
        "runway_months": metrics.get("runway_months"),
        "net_burn": metrics.get("net_burn"),
        "ndr": metrics.get("ndr"),
        "logo_retention": metrics.get("logo_retention"),
        "customers": metrics.get("customers"),
        "arpu": metrics.get("arpu"),
        "ltv": metrics.get("ltv"),
        "cac": metrics.get("cac"),
        "ltv_cac_ratio": metrics.get("ltv_cac_ratio"),
        "arr": metrics.get("arr"),
    }
    
    baseline_data = {k: v for k, v in baseline_data.items() if v is not None}
    
    return {
        "raw_metrics": metrics,
        "baseline_data": baseline_data,
        "company_name": metrics.get("company_name"),
        "report_date": metrics.get("report_date"),
        "currency": metrics.get("currency", "USD"),
        "summary": metrics.get("summary"),
        "extracted_text_length": len(pdf_text),
    }
