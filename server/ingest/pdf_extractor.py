import os
import json
import logging
from typing import Dict, Any, Optional
import pdfplumber
from openai import OpenAI

logger = logging.getLogger(__name__)

MAX_PDF_SIZE_MB = 10

def get_openai_client() -> OpenAI:
    """Get OpenAI client with validation."""
    api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    
    if not api_key:
        raise ValueError("OpenAI API key not configured. Please check environment settings.")
    
    return OpenAI(api_key=api_key, base_url=base_url)

EXTRACTION_PROMPT = """Extract from the following financial report (Tribe Capital Mini Benchmark Scan, Termina report, or similar) all key financial and operational metrics. 
Return the result as a JSON object with these exact keys (use null if not found):

{
  "company_name": "string - the company name",
  "report_date": "string - the date of the report (YYYY-MM-DD format if possible)",
  "currency": "string - the currency code (USD, EUR, GBP, INR, etc.)",
  "monthly_revenue": "number - current monthly revenue in the stated currency",
  "run_rate_revenue": "number - annualized run rate revenue",
  "cogs": "number - cost of goods sold (monthly)",
  "gross_profit": "number - gross profit (monthly)",
  "gross_margin": "number - gross margin as percentage (0-100)",
  "operating_income": "number - operating income (monthly)",
  "operating_margin": "number - operating margin as percentage",
  "total_monthly_expenses": "number - total monthly operating expenses (COGS + Opex + S&M + Other)",
  "net_burn": "number - monthly net burn rate (expenses minus revenue if negative cash flow)",
  "cash_balance": "number - current cash on hand / bank balance",
  "runway_months": "number - estimated runway in months",
  "yoy_growth": "number - year over year growth rate as multiple (e.g., 1.6x becomes 60)",
  "mom_growth": "number - month over month growth rate as percentage (e.g., CMGR)",
  "cmgr_3": "number - 3-month compound monthly growth rate as percentage",
  "cmgr_6": "number - 6-month compound monthly growth rate as percentage",
  "cmgr_12": "number - 12-month compound monthly growth rate as percentage",
  "payroll": "number - monthly payroll/personnel expense",
  "sales_and_marketing": "number - monthly sales & marketing expense",
  "other_opex": "number - monthly other operating expenses",
  "opex": "number - total monthly operating expenses (excluding COGS)",
  "headcount": "number - current employee count",
  "arr": "number - annual recurring revenue",
  "mrr": "number - monthly recurring revenue",
  "ndr": "number - net dollar retention as percentage",
  "logo_retention": "number - customer logo retention as percentage",
  "customers": "number - total customer/user count",
  "monthly_active_users": "number - monthly active users",
  "paid_users": "number - monthly paid users",
  "arpu": "number - average revenue per user/customer",
  "ltv": "number - customer lifetime value",
  "cac": "number - customer acquisition cost",
  "ltv_cac_ratio": "number - LTV to CAC ratio",
  "summary": "string - brief 2-3 sentence summary of the company's financial health"
}

Important instructions:
- Extract actual numbers from the report, not formatted strings
- Convert all monetary values to numbers (e.g., "$14.2M" becomes 14200000)
- Convert percentages to numbers (e.g., 85% becomes 85)
- For YoY growth shown as multipliers (e.g., "1.6x"), convert to percentage (60%)
- Use null for any metrics not found in the report
- Look for metrics in tables, key findings sections, and benchmark tables
- If COGS and Opex are given, calculate total_monthly_expenses = COGS + all Opex items
- If operating margin and revenue are given, calculate operating_income
- Be precise with the numbers - do not estimate or guess
- CRITICAL: All expense values (COGS, payroll, marketing, opex, etc.) must be returned as POSITIVE numbers, even if they appear as negative in the P&L. Revenue should be positive.

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
        client = get_openai_client()
        
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
            timeout=60,
        )
        
        content = response.choices[0].message.content
        
        if not content:
            raise ValueError("OpenAI returned empty response")
        
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        metrics = json.loads(content)
        
        if not isinstance(metrics, dict):
            raise ValueError("OpenAI response is not a valid metrics object")
        
        return metrics
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI response as JSON: {e}")
        raise ValueError(f"AI response was not valid JSON. Please try again.")
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        raise ValueError(f"Failed to analyze PDF: {str(e)}")


def normalize_expense_value(value: Any) -> Optional[float]:
    """Normalize expense value to always be positive."""
    if value is None:
        return None
    try:
        num = float(value)
        return abs(num)  # Expenses are always stored as positive
    except (ValueError, TypeError):
        return None

def process_termina_pdf(file_path: str, max_size_mb: float = MAX_PDF_SIZE_MB) -> Dict[str, Any]:
    """Process a Termina PDF and extract financial metrics."""
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise ValueError(f"PDF file too large ({file_size_mb:.1f}MB). Maximum allowed is {max_size_mb}MB.")
    
    pdf_text = extract_text_from_pdf(file_path)
    
    if len(pdf_text.strip()) < 100:
        raise ValueError("PDF contains insufficient text content for analysis.")
    
    metrics = extract_metrics_with_openai(pdf_text)
    
    if not metrics:
        raise ValueError("Failed to extract any metrics from the PDF.")
    
    # Normalize all expense fields to be positive
    expense_fields = ['cogs', 'opex', 'payroll', 'sales_and_marketing', 'other_opex', 
                      'total_monthly_expenses', 'net_burn', 'operating_expenses']
    for field in expense_fields:
        if field in metrics and metrics[field] is not None:
            metrics[field] = normalize_expense_value(metrics[field])
    
    total_expenses = metrics.get("total_monthly_expenses")
    if not total_expenses:
        cogs = metrics.get("cogs") or 0
        opex = metrics.get("opex") or 0
        sm = metrics.get("sales_and_marketing") or 0
        other = metrics.get("other_opex") or 0
        if cogs or opex or sm or other:
            total_expenses = cogs + opex + sm + other
    
    mom_growth = metrics.get("mom_growth") or metrics.get("cmgr_3") or metrics.get("cmgr_12")
    
    baseline_data = {
        "monthly_revenue": metrics.get("monthly_revenue") or metrics.get("mrr"),
        "total_expenses": total_expenses,
        "gross_margin": metrics.get("gross_margin"),
        "operating_margin": metrics.get("operating_margin"),
        "operating_expenses": metrics.get("opex"),
        "payroll": metrics.get("payroll"),
        "sales_and_marketing": metrics.get("sales_and_marketing"),
        "other_opex": metrics.get("other_opex"),
        "cogs": metrics.get("cogs"),
        "gross_profit": metrics.get("gross_profit"),
        "operating_income": metrics.get("operating_income"),
        "cash_balance": metrics.get("cash_balance"),
        "headcount": metrics.get("headcount"),
        "yoy_growth": metrics.get("yoy_growth"),
        "mom_growth": mom_growth,
        "cmgr_3": metrics.get("cmgr_3"),
        "cmgr_6": metrics.get("cmgr_6"),
        "cmgr_12": metrics.get("cmgr_12"),
        "runway_months": metrics.get("runway_months"),
        "net_burn": metrics.get("net_burn"),
        "ndr": metrics.get("ndr"),
        "logo_retention": metrics.get("logo_retention"),
        "customers": metrics.get("customers"),
        "monthly_active_users": metrics.get("monthly_active_users"),
        "paid_users": metrics.get("paid_users"),
        "arpu": metrics.get("arpu"),
        "ltv": metrics.get("ltv"),
        "cac": metrics.get("cac"),
        "ltv_cac_ratio": metrics.get("ltv_cac_ratio"),
        "arr": metrics.get("arr"),
        "run_rate_revenue": metrics.get("run_rate_revenue"),
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
