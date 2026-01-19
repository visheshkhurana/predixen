import os
import io
import re
import base64
import json
import logging
from typing import Dict, Any, Optional, List
import pdfplumber
from openai import OpenAI

logger = logging.getLogger(__name__)

MAX_PDF_SIZE_MB = 10
MIN_TEXT_LENGTH = 100  # Minimum characters to consider text extraction successful


def parse_value_from_text(text: str) -> Optional[float]:
    """Parse a numeric value from text, handling $, M, K, %, x suffixes.
    
    Returns the raw value as reported (e.g., "$14.2M" -> 14.2, "60.3%" -> 60.3)
    Does NOT multiply by scale factors - stores in millions as millions.
    """
    if not text:
        return None
    
    text = text.strip()
    
    # Check for percentage
    is_percentage = '%' in text
    
    # Check for 'x' suffix (multiplier/ratio)
    is_ratio = text.lower().endswith('x')
    
    # Check for M/K suffixes - we'll preserve millions as millions
    is_millions = 'm' in text.lower() and not text.lower().endswith('month')
    is_thousands = 'k' in text.lower()
    is_billions = 'b' in text.lower()
    
    # Clean the string to extract just the number
    cleaned = text
    cleaned = re.sub(r'[₹$€£,]', '', cleaned)  # Remove currency symbols
    cleaned = cleaned.replace('%', '')
    cleaned = re.sub(r'[xX]$', '', cleaned)
    cleaned = re.sub(r'[mMkKbB]$', '', cleaned)
    cleaned = cleaned.replace('(', '-').replace(')', '')  # Handle negatives
    cleaned = cleaned.strip()
    
    try:
        value = float(cleaned)
        
        # Apply scale for storage (store in base units)
        if is_millions:
            value = value * 1_000_000
        elif is_thousands:
            value = value * 1_000
        elif is_billions:
            value = value * 1_000_000_000
        
        return value
    except (ValueError, TypeError):
        return None


def extract_metrics_with_patterns(pdf_text: str) -> Dict[str, Any]:
    """Extract financial metrics using direct text pattern matching.
    
    This is optimized for Tribe Capital Mini Benchmark Scan and similar formats.
    Returns values exactly as stated in the PDF without scaling.
    """
    metrics = {}
    
    # Normalize whitespace and line breaks for easier matching
    text = ' '.join(pdf_text.split())
    
    # Company name - look for common patterns
    company_match = re.search(r'(?:Mini Benchmark Scan|Overview)\s+([A-Z][A-Za-z0-9\s]+?)(?:\s+(?:Key|Revenue|Summary|March|January|February|April|May|June|July|August|September|October|November|December))', text)
    if company_match:
        metrics['company_name'] = company_match.group(1).strip()
    
    # Monthly Revenue: "In March 2025, Revenue was $14.2M"
    revenue_match = re.search(r'(?:In\s+\w+\s+\d{4},\s+)?Revenue\s+was\s+([₹$€£]?[\d.,]+[MKBmkb]?)', text, re.IGNORECASE)
    if revenue_match:
        metrics['monthly_revenue'] = parse_value_from_text(revenue_match.group(1))
    
    # Annual Run Rate: "($171.0M run rate)" or "run rate of $171M"
    run_rate_match = re.search(r'\(?\s*([₹$€£]?[\d.,]+[MKBmkb]?)\s*run\s*rate\)?', text, re.IGNORECASE)
    if run_rate_match:
        metrics['run_rate_revenue'] = parse_value_from_text(run_rate_match.group(1))
        # Also calculate ARR from run rate
        if metrics.get('run_rate_revenue'):
            metrics['arr'] = metrics['run_rate_revenue']
    
    # Gross Margin: "Gross Margin was 60.3%"
    gross_margin_match = re.search(r'Gross\s+Margin\s+(?:was\s+)?(-?[\d.]+)%?', text, re.IGNORECASE)
    if gross_margin_match:
        metrics['gross_margin'] = float(gross_margin_match.group(1))
    
    # Operating Margin: "Operating Margin was 30.6%" or "Operating margin 30.6%"
    op_margin_match = re.search(r'Operating\s+[Mm]argin\s+(?:was\s+)?(-?[\d.]+)%?', text, re.IGNORECASE)
    if op_margin_match:
        metrics['operating_margin'] = float(op_margin_match.group(1))
    
    # Burn Multiple: "Burn Multiple was -0.7x"
    burn_match = re.search(r'Burn\s+Multiple\s+(?:was\s+)?(-?[\d.]+)x?', text, re.IGNORECASE)
    if burn_match:
        metrics['burn_multiple'] = float(burn_match.group(1))
    
    # Revenue CMGR - look for 3/6/12 month growth rates
    # Patterns like "3-month CMGR of 4.2%" or "CMGR (3m): 4.2%"
    cmgr3_match = re.search(r'(?:3[-\s]?month\s+)?CMGR\s*(?:\(3m?\))?\s*(?:of\s+|:\s*|was\s+)?(-?[\d.]+)%?', text, re.IGNORECASE)
    if cmgr3_match:
        metrics['cmgr_3'] = float(cmgr3_match.group(1))
        metrics['mom_growth'] = float(cmgr3_match.group(1))  # Use 3-month as primary
    
    cmgr6_match = re.search(r'6[-\s]?month\s+CMGR\s*(?:of\s+|:\s*|was\s+)?(-?[\d.]+)%?', text, re.IGNORECASE)
    if cmgr6_match:
        metrics['cmgr_6'] = float(cmgr6_match.group(1))
    
    cmgr12_match = re.search(r'12[-\s]?month\s+CMGR\s*(?:of\s+|:\s*|was\s+)?(-?[\d.]+)%?', text, re.IGNORECASE)
    if cmgr12_match:
        metrics['cmgr_12'] = float(cmgr12_match.group(1))
    
    # Operating Income: "Operating Income $4.4M" or "Operating Income was $4.4M"
    op_income_match = re.search(r'Operating\s+Income\s+(?:was\s+)?([₹$€£]?-?[\d.,]+[MKBmkb]?)', text, re.IGNORECASE)
    if op_income_match:
        metrics['operating_income'] = parse_value_from_text(op_income_match.group(1))
    
    # Gross Profit: "Gross Profit $8.6M"
    gross_profit_match = re.search(r'Gross\s+Profit\s+(?:was\s+)?([₹$€£]?-?[\d.,]+[MKBmkb]?)', text, re.IGNORECASE)
    if gross_profit_match:
        metrics['gross_profit'] = parse_value_from_text(gross_profit_match.group(1))
    
    # Cash Balance
    cash_match = re.search(r'(?:Cash\s+Balance|Cash\s+on\s+Hand|Bank\s+Balance)\s*:?\s*([₹$€£]?[\d.,]+[MKBmkb]?)', text, re.IGNORECASE)
    if cash_match:
        metrics['cash_balance'] = parse_value_from_text(cash_match.group(1))
    
    # Net Burn
    burn_rate_match = re.search(r'(?:Net\s+Burn|Monthly\s+Burn)\s*:?\s*([₹$€£]?-?[\d.,]+[MKBmkb]?)', text, re.IGNORECASE)
    if burn_rate_match:
        metrics['net_burn'] = parse_value_from_text(burn_rate_match.group(1))
    
    # Runway
    runway_match = re.search(r'Runway\s*:?\s*(\d+)\s*months?', text, re.IGNORECASE)
    if runway_match:
        metrics['runway_months'] = int(runway_match.group(1))
    
    # Headcount
    headcount_match = re.search(r'(?:Headcount|Employees|Team\s+Size)\s*:?\s*(\d+)', text, re.IGNORECASE)
    if headcount_match:
        metrics['headcount'] = int(headcount_match.group(1))
    
    # YoY Growth: "Year-over-Year Growth 1.6x" or "YoY Growth 60%"
    yoy_match = re.search(r'(?:Y[oe][Yy]|Year[-\s]over[-\s]Year)\s+[Gg]rowth\s*:?\s*(-?[\d.]+)([x%])?', text, re.IGNORECASE)
    if yoy_match:
        value = float(yoy_match.group(1))
        suffix = yoy_match.group(2)
        if suffix and suffix.lower() == 'x':
            # Convert 1.6x to 60%
            metrics['yoy_growth'] = (value - 1) * 100
        else:
            metrics['yoy_growth'] = value
    
    # Currency detection
    if '₹' in pdf_text:
        metrics['currency'] = 'INR'
    elif '€' in pdf_text:
        metrics['currency'] = 'EUR'
    elif '£' in pdf_text:
        metrics['currency'] = 'GBP'
    elif '$' in pdf_text:
        metrics['currency'] = 'USD'
    
    # Report date - look for month year patterns
    date_match = re.search(r'(?:In\s+)?(\w+\s+\d{4})', text)
    if date_match:
        metrics['report_date'] = date_match.group(1)
    
    return metrics


def get_openai_client() -> OpenAI:
    """Get OpenAI client with validation."""
    api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    
    if not api_key:
        raise ValueError("OpenAI API key not configured. Please check environment settings.")
    
    return OpenAI(api_key=api_key, base_url=base_url)


def pdf_to_images(file_path: str, max_pages: int = 5) -> List[str]:
    """Convert PDF pages to base64-encoded images for vision API."""
    try:
        from pdf2image import convert_from_path
        from PIL import Image
        
        images = convert_from_path(
            file_path, 
            first_page=1, 
            last_page=max_pages,
            dpi=150  # Balance quality and size
        )
        
        base64_images = []
        for img in images:
            # Resize if too large
            if img.width > 1500 or img.height > 1500:
                ratio = min(1500 / img.width, 1500 / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            base64_images.append(base64.b64encode(buffer.getvalue()).decode('utf-8'))
        
        return base64_images
    except Exception as e:
        logger.error(f"Error converting PDF to images: {e}")
        raise ValueError(f"Could not convert PDF to images: {str(e)}")


EXTRACTION_PROMPT = """Extract from the following financial report (Tribe Capital Mini Benchmark Scan, Termina report, or similar) all key financial and operational metrics. 
Return the result as a JSON object with these exact keys (use null if not found):

{
  "company_name": "string - the company name",
  "report_date": "string - the date of the report (YYYY-MM-DD format if possible)",
  "currency": "string - the currency code (USD, EUR, GBP, INR, etc.)",
  "monthly_revenue": "number - current monthly revenue in base units (e.g., $14.2M = 14200000)",
  "run_rate_revenue": "number - annualized run rate revenue in base units",
  "cogs": "number - cost of goods sold (monthly) in base units",
  "gross_profit": "number - gross profit (monthly) in base units",
  "gross_margin": "number - gross margin as percentage (e.g., 60.3% = 60.3)",
  "operating_income": "number - operating income (monthly) in base units",
  "operating_margin": "number - operating margin as percentage (e.g., 30.6% = 30.6)",
  "burn_multiple": "number - burn multiple as reported (e.g., -0.7x = -0.7)",
  "total_monthly_expenses": "number - total monthly operating expenses in base units",
  "net_burn": "number - monthly net burn rate in base units",
  "cash_balance": "number - current cash on hand in base units",
  "runway_months": "number - estimated runway in months",
  "yoy_growth": "number - year over year growth as percentage (e.g., 1.6x = 60, 60% = 60)",
  "mom_growth": "number - month over month growth rate as percentage",
  "cmgr_3": "number - 3-month compound monthly growth rate as percentage",
  "cmgr_6": "number - 6-month compound monthly growth rate as percentage",
  "cmgr_12": "number - 12-month compound monthly growth rate as percentage",
  "payroll": "number - monthly payroll/personnel expense in base units",
  "sales_and_marketing": "number - monthly sales & marketing expense in base units",
  "other_opex": "number - monthly other operating expenses in base units",
  "opex": "number - total monthly operating expenses in base units",
  "headcount": "number - current employee count",
  "arr": "number - annual recurring revenue in base units",
  "mrr": "number - monthly recurring revenue in base units",
  "ndr": "number - net dollar retention as percentage",
  "logo_retention": "number - customer logo retention as percentage",
  "customers": "number - total customer/user count",
  "monthly_active_users": "number - monthly active users",
  "paid_users": "number - monthly paid users",
  "arpu": "number - average revenue per user/customer in base units",
  "ltv": "number - customer lifetime value in base units",
  "cac": "number - customer acquisition cost in base units",
  "ltv_cac_ratio": "number - LTV to CAC ratio as a decimal",
  "summary": "string - brief 2-3 sentence summary of the company's financial health"
}

CRITICAL INSTRUCTIONS - EXTRACT EXACTLY AS STATED:
- Extract the EXACT values from the report without additional calculation or scaling
- For monetary values: $14.2M = 14200000, $500K = 500000, $1.5B = 1500000000
- For percentages: 60.3% = 60.3, 30.6% = 30.6, 4.2% = 4.2 (keep the number, not decimal)
- For multiples/ratios: -0.7x = -0.7, 3.5x = 3.5 (keep the sign and value)
- For YoY growth as multiplier: 1.6x = 60 (convert to percentage growth)
- Use null if a metric is NOT found - do NOT default to zero
- PRESERVE negative values (like negative burn multiple) - do not clamp to zero
- All expense values should be POSITIVE numbers, but burn_multiple can be negative
- Do NOT estimate or calculate values that aren't explicitly stated

"""

VISION_EXTRACTION_PROMPT = """Analyze this financial report image and extract all key financial and operational metrics.
Return the result as a JSON object with these exact keys (use null if not found):

{
  "company_name": "string - the company name",
  "report_date": "string - the date of the report (YYYY-MM-DD format if possible)",
  "currency": "string - the currency code (USD, EUR, GBP, INR, etc.)",
  "monthly_revenue": "number - current monthly revenue",
  "run_rate_revenue": "number - annualized run rate revenue",
  "cogs": "number - cost of goods sold (monthly)",
  "gross_profit": "number - gross profit (monthly)",
  "gross_margin": "number - gross margin as percentage (0-100)",
  "operating_income": "number - operating income (monthly)",
  "operating_margin": "number - operating margin as percentage",
  "total_monthly_expenses": "number - total monthly operating expenses",
  "net_burn": "number - monthly net burn rate",
  "cash_balance": "number - current cash on hand",
  "runway_months": "number - estimated runway in months",
  "yoy_growth": "number - year over year growth rate as percentage",
  "mom_growth": "number - month over month growth rate as percentage",
  "payroll": "number - monthly payroll expense",
  "sales_and_marketing": "number - monthly sales & marketing expense",
  "other_opex": "number - other operating expenses",
  "opex": "number - total operating expenses (excluding COGS)",
  "headcount": "number - employee count",
  "arr": "number - annual recurring revenue",
  "mrr": "number - monthly recurring revenue",
  "customers": "number - total customer count",
  "arpu": "number - average revenue per user",
  "ltv": "number - customer lifetime value",
  "cac": "number - customer acquisition cost",
  "summary": "string - brief summary of financial health"
}

Instructions:
- Extract actual numbers, convert formatted values (e.g., "$14.2M" becomes 14200000)
- Convert percentages to numbers (e.g., 85% becomes 85)
- All expenses should be POSITIVE numbers
- Return valid JSON only, no markdown formatting
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
        return full_text
    except Exception as e:
        logger.warning(f"Text extraction failed with pdfplumber: {e}")
        return ""


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
                    "content": EXTRACTION_PROMPT + "Here is the report text:\n\n" + pdf_text[:15000]
                }
            ],
            max_tokens=2000,
            temperature=0.1,
            timeout=60,
        )
        
        content = response.choices[0].message.content
        
        if not content:
            raise ValueError("OpenAI returned empty response")
        
        # Clean up markdown formatting if present
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


def extract_metrics_with_vision(image_base64_list: List[str]) -> Dict[str, Any]:
    """Use OpenAI Vision to extract financial metrics from PDF images."""
    try:
        client = get_openai_client()
        
        # Build content with images
        content = [{"type": "text", "text": VISION_EXTRACTION_PROMPT}]
        
        for img_b64 in image_base64_list[:5]:  # Limit to 5 pages
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}",
                    "detail": "high"
                }
            })
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst AI that extracts structured data from financial report images. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=2000,
            temperature=0.1,
            timeout=90,
        )
        
        response_content = response.choices[0].message.content
        
        if not response_content:
            raise ValueError("OpenAI Vision returned empty response")
        
        # Clean up markdown formatting if present
        if response_content.startswith("```"):
            response_content = response_content.split("```")[1]
            if response_content.startswith("json"):
                response_content = response_content[4:]
        response_content = response_content.strip()
        
        metrics = json.loads(response_content)
        
        if not isinstance(metrics, dict):
            raise ValueError("Vision response is not a valid metrics object")
        
        logger.info("Successfully extracted metrics using OpenAI Vision")
        return metrics
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Vision response as JSON: {e}")
        raise ValueError(f"AI Vision response was not valid JSON. Please try again.")
    except Exception as e:
        logger.error(f"Error calling OpenAI Vision API: {e}")
        raise ValueError(f"Failed to analyze PDF with vision: {str(e)}")


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
    """Process a Termina PDF and extract financial metrics.
    
    Uses a three-stage approach:
    1. Try direct pattern extraction using pdfplumber (most accurate for known formats)
    2. Use OpenAI to fill in any missing fields
    3. Fall back to OpenAI Vision for scanned/image-based PDFs
    """
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise ValueError(f"PDF file too large ({file_size_mb:.1f}MB). Maximum allowed is {max_size_mb}MB.")
    
    extraction_method = "pattern"
    
    # Stage 1: Try text extraction with pdfplumber
    pdf_text = extract_text_from_pdf(file_path)
    
    # Stage 2: Try pattern-based extraction first (most accurate for known formats)
    pattern_metrics = {}
    ai_metrics = {}
    
    if len(pdf_text.strip()) >= MIN_TEXT_LENGTH:
        logger.info(f"Text extraction successful ({len(pdf_text)} chars)")
        
        # First, try pattern extraction for known formats (Mini Benchmark Scan, etc.)
        pattern_metrics = extract_metrics_with_patterns(pdf_text)
        logger.info(f"Pattern extraction found {len(pattern_metrics)} metrics: {list(pattern_metrics.keys())}")
        
        # Then use OpenAI to fill in any missing fields
        try:
            ai_metrics = extract_metrics_with_openai(pdf_text)
            extraction_method = "pattern+ai"
        except Exception as e:
            logger.warning(f"AI extraction failed: {e}")
            if not pattern_metrics:
                extraction_method = "vision"
    else:
        logger.info(f"Insufficient text extracted ({len(pdf_text.strip())} chars), using vision-based analysis")
        extraction_method = "vision"
    
    # Merge pattern and AI metrics (pattern takes priority for accuracy)
    metrics = {**ai_metrics, **pattern_metrics}  # pattern_metrics override ai_metrics
    
    # Stage 3: Fall back to vision if we still have no metrics
    if not metrics:
        try:
            image_list = pdf_to_images(file_path)
            if not image_list:
                raise ValueError("Could not convert any PDF pages to images")
            
            metrics = extract_metrics_with_vision(image_list)
            extraction_method = "vision"
        except Exception as e:
            logger.error(f"Vision extraction also failed: {e}")
            raise ValueError(f"Could not extract data from PDF. Please ensure the file is a valid financial report. Error: {str(e)}")
    
    if not metrics:
        raise ValueError("Failed to extract any metrics from the PDF.")
    
    # Normalize expense fields to be positive (but NOT net_burn - it can be negative for profitable companies)
    expense_fields = ['cogs', 'opex', 'payroll', 'sales_and_marketing', 'other_opex', 
                      'total_monthly_expenses', 'operating_expenses']
    for field in expense_fields:
        if field in metrics and metrics[field] is not None:
            metrics[field] = normalize_expense_value(metrics[field])
    
    # Calculate total expenses if not provided
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
        "burn_multiple": metrics.get("burn_multiple"),  # Preserve negative values
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
    
    # Remove None values
    baseline_data = {k: v for k, v in baseline_data.items() if v is not None}
    
    return {
        "raw_metrics": metrics,
        "baseline_data": baseline_data,
        "company_name": metrics.get("company_name"),
        "report_date": metrics.get("report_date"),
        "currency": metrics.get("currency", "USD"),
        "summary": metrics.get("summary"),
        "extracted_text_length": len(pdf_text),
        "extraction_method": extraction_method,
    }
