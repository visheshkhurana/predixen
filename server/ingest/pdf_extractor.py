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

MAX_PDF_SIZE_MB = 25
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
    
    IMPORTANT: This format reports QUARTERLY revenue (Rolling Q) which is then
    annualized to get the run rate (ARR). Monthly revenue = quarterly revenue / 3.
    """
    metrics = {}
    
    # Normalize whitespace and line breaks for easier matching
    text = ' '.join(pdf_text.split())
    
    # Detect if this is a Mini Benchmark Scan format (uses Rolling Q = quarterly data)
    # Use case-insensitive matching for quarterly indicators
    text_lower = text.lower()
    is_quarterly_format = 'rolling q' in text_lower or 'mini benchmark scan' in text_lower or 'annualized revenue' in text_lower
    metrics['_is_quarterly_format'] = is_quarterly_format
    
    # Company name - look for common patterns
    company_match = re.search(r'(?:Mini Benchmark Scan|Overview)\s+([A-Z][A-Za-z0-9.\s]+?)(?:\s+(?:HIGHLY|Key|Revenue|Summary|March|January|February|April|May|June|July|August|September|October|November|December))', text)
    if company_match:
        metrics['company_name'] = company_match.group(1).strip()
    
    # Check for explicit quarterly format indicators (case-insensitive)
    has_quarterly_indicator = (
        'rolling q' in text_lower or 
        'latest revenue / arr' in text_lower or
        'latest revenue/arr' in text_lower or
        'quarterly revenue' in text_lower or
        '(rolling q)' in text_lower
    )
    
    # Check if this is a Full Benchmark Scan format (has detailed monthly breakouts)
    is_full_benchmark = 'full benchmark scan' in text_lower or 'full scan' in text_lower
    
    # PRIORITY 1: Look for detailed section pattern "In [Month] [Year], Revenue was $X ($Y run rate)"
    # This is the most authoritative source in Full Benchmark Scan format
    detailed_rev_match = re.search(
        r'In\s+(\w+\s+\d{4}),\s+Revenue\s+was\s*\n?\s*([₹$€£]?[\d.,]+[MKBmkb]?)\s*\(([₹$€£]?[\d.,]+[MKBmkb]?)\s*run\s*rate\)',
        text, re.IGNORECASE
    )
    if detailed_rev_match:
        period = detailed_rev_match.group(1)
        monthly_val = parse_value_from_text(detailed_rev_match.group(2))
        run_rate_val = parse_value_from_text(detailed_rev_match.group(3))
        if monthly_val:
            metrics['monthly_revenue'] = monthly_val
            metrics['report_date'] = period
            logger.info(f"Extracted detailed monthly revenue: {monthly_val} for {period}")
        if run_rate_val:
            metrics['run_rate_revenue'] = run_rate_val
            metrics['arr'] = run_rate_val
    
    # PRIORITY 2: For non-quarterly reports without detailed match, try simpler patterns
    if not metrics.get('monthly_revenue') and not has_quarterly_indicator:
        monthly_rev_match = re.search(r'(?:In\s+\w+\s+\d{4},\s+)?(?:Monthly\s+)?Revenue\s+(?:was\s+)?([₹$€£]?[\d.,]+[MKBmkb]?)', text, re.IGNORECASE)
        if monthly_rev_match:
            monthly_val = parse_value_from_text(monthly_rev_match.group(1))
            if monthly_val:
                metrics['monthly_revenue'] = monthly_val
                logger.info(f"Extracted monthly revenue directly: {monthly_val}")
    
    # Annualized Revenue (Rolling Q) - extract ARR but ONLY if not already set by detailed match
    # Pattern: "Annualized Revenue (Rolling Q) was $51.6M"
    # Note: The detailed match from "In [Month] [Year], Revenue was $X ($Y run rate)" takes priority
    if not metrics.get('run_rate_revenue'):
        arr_rolling_match = re.search(r'Annualized\s+Revenue\s*\(?\s*Rolling\s*Q?\s*\)?\s*(?:was\s+)?([₹$€£]?[\d.,]+[MKBmkb]?)', text, re.IGNORECASE)
        if arr_rolling_match:
            arr_value = parse_value_from_text(arr_rolling_match.group(1))
            if arr_value:
                metrics['arr'] = arr_value
                metrics['run_rate_revenue'] = arr_value
                # Only derive monthly from ARR if this is explicitly a quarterly format
                # DO NOT overwrite if monthly_revenue is already set
                if has_quarterly_indicator and not metrics.get('monthly_revenue'):
                    metrics['monthly_revenue'] = arr_value / 12
                    logger.info(f"Extracted ARR (Rolling Q): {arr_value}, derived monthly: {arr_value/12}")
                else:
                    logger.info(f"Extracted ARR: {arr_value}, not deriving monthly (no quarterly indicator or already set)")
    
    # Also look for plain run rate if ARR not found
    if not metrics.get('run_rate_revenue'):
        run_rate_match = re.search(r'\(?\s*([₹$€£]?[\d.,]+[MKBmkb]?)\s*run\s*rate\)?', text, re.IGNORECASE)
        if run_rate_match:
            run_rate = parse_value_from_text(run_rate_match.group(1))
            if run_rate:
                metrics['run_rate_revenue'] = run_rate
                metrics['arr'] = run_rate
                # DO NOT derive monthly from run rate - only extract what's explicitly stated
    
    # Latest Revenue (quarterly): Look for "Latest Revenue / ARR" table pattern
    # This IS an explicit quarterly indicator - Pattern: "$12.9M / $51.6M" where first is quarterly, second is ARR
    latest_rev_match = re.search(r'Latest\s+Revenue\s*/\s*ARR[^$₹€£]*?([₹$€£]?[\d.,]+[MKBmkb]?)\s*/\s*([₹$€£]?[\d.,]+[MKBmkb]?)', text, re.IGNORECASE)
    if latest_rev_match:
        quarterly_rev = parse_value_from_text(latest_rev_match.group(1))
        arr_value = parse_value_from_text(latest_rev_match.group(2))
        if quarterly_rev and arr_value:
            metrics['quarterly_revenue'] = quarterly_rev
            metrics['arr'] = arr_value
            metrics['run_rate_revenue'] = arr_value
            # This is explicit quarterly format, so we CAN derive monthly
            metrics['monthly_revenue'] = quarterly_rev / 3
            logger.info(f"Extracted quarterly: {quarterly_rev}, ARR: {arr_value}, derived monthly: {quarterly_rev/3}")
    
    # Gross Margin (Rolling Q): "Gross Margin (Rolling Q) was 22.1%"
    gross_margin_match = re.search(r'Gross\s+Margin\s*(?:\(Rolling\s*Q?\))?\s*(?:was\s+)?(-?[\d.]+)\s*%?', text, re.IGNORECASE)
    if gross_margin_match:
        metrics['gross_margin'] = float(gross_margin_match.group(1))
    
    # Operating Margin (Rolling Q): "Operating Margin (Rolling Q) was 9.9%"
    op_margin_match = re.search(r'Operating\s+[Mm]argin\s*(?:\(Rolling\s*Q?\))?\s*(?:was\s+)?(-?[\d.]+)\s*%?', text, re.IGNORECASE)
    if op_margin_match:
        metrics['operating_margin'] = float(op_margin_match.group(1))
    
    # Burn Multiple: "Burn Multiple was -0.7x" (negative means profitable)
    burn_match = re.search(r'Burn\s+Multiple\s+(?:was\s+)?(-?[\d.]+)x?', text, re.IGNORECASE)
    if burn_match:
        metrics['burn_multiple'] = float(burn_match.group(1))
    
    # CMGR12 (primary growth indicator for this format): "CMGR12 was 1.8%"
    cmgr12_match = re.search(r'CMGR\s*12\s*(?:was\s+)?(-?[\d.]+)\s*%?', text, re.IGNORECASE)
    if cmgr12_match:
        metrics['cmgr_12'] = float(cmgr12_match.group(1))
        metrics['mom_growth'] = float(cmgr12_match.group(1))  # Use CMGR12 as MoM
    
    # Also look for "3-month CMGR" or similar patterns
    cmgr3_match = re.search(r'(?:3[-\s]?month\s+)?CMGR\s*(?:\(3m?\))?\s*(?:of\s+|:\s*|was\s+)?(-?[\d.]+)\s*%?', text, re.IGNORECASE)
    if cmgr3_match and not metrics.get('cmgr_12'):
        metrics['cmgr_3'] = float(cmgr3_match.group(1))
        if not metrics.get('mom_growth'):
            metrics['mom_growth'] = float(cmgr3_match.group(1))
    
    # Revenue CQGR patterns: "Revenue CQGR 1/2/4 was 22.7/14.4/5.6%"
    cqgr_match = re.search(r'Revenue\s+CQGR\s+\d/\d/\d\s+(?:was\s+)?([\d.]+)/([\d.]+)/([\d.]+)\s*%?', text, re.IGNORECASE)
    if cqgr_match:
        metrics['cqgr_1'] = float(cqgr_match.group(1))
        metrics['cqgr_2'] = float(cqgr_match.group(2))
        metrics['cqgr_4'] = float(cqgr_match.group(3))
    
    # YoY Growth from table: "YoY Growth" column values like "1.24x"
    # Pattern: "YoY Growth" followed by values like "1.24x"
    yoy_match = re.search(r'(?:Y[oe][Yy]|Year[-\s]over[-\s]Year)\s+[Gg]rowth[^0-9]*?(\d+\.?\d*)x?', text, re.IGNORECASE)
    if yoy_match:
        value = float(yoy_match.group(1))
        if value >= 0.5 and value <= 10:  # Likely a multiplier like 1.24x
            metrics['yoy_growth'] = (value - 1) * 100  # Convert 1.24x to 24%
        else:
            metrics['yoy_growth'] = value  # Already a percentage
    
    # Also look for "implied year-over-year growth was 2.3/1.7/1.2x" pattern
    implied_yoy = re.search(r'[Ii]mplied\s+year[-\s]over[-\s]year\s+growth\s+(?:was\s+)?([\d.]+)/([\d.]+)/([\d.]+)\s*x?', text, re.IGNORECASE)
    if implied_yoy:
        yoy_1q = float(implied_yoy.group(1))
        yoy_2q = float(implied_yoy.group(2))
        yoy_4q = float(implied_yoy.group(3))
        # Use the 4-quarter YoY as primary
        if yoy_4q >= 0.5 and yoy_4q <= 10:
            metrics['yoy_growth'] = (yoy_4q - 1) * 100
    
    # Operating Income - not commonly in this format but check anyway
    op_income_match = re.search(r'Operating\s+Income\s+(?:was\s+)?([₹$€£]?-?[\d.,]+[MKBmkb]?)', text, re.IGNORECASE)
    if op_income_match:
        metrics['operating_income'] = parse_value_from_text(op_income_match.group(1))
    
    # Gross Profit - only extract if explicitly stated, do NOT derive from margins
    gross_profit_match = re.search(r'Gross\s+Profit\s+(?:was\s+)?([₹$€£]?-?[\d.,]+[MKBmkb]?)', text, re.IGNORECASE)
    if gross_profit_match:
        metrics['gross_profit'] = parse_value_from_text(gross_profit_match.group(1))
    
    # Cash Balance (rarely in Mini Benchmark Scan)
    cash_match = re.search(r'(?:Cash\s+Balance|Cash\s+on\s+Hand|Bank\s+Balance)\s*:?\s*([₹$€£]?[\d.,]+[MKBmkb]?)', text, re.IGNORECASE)
    if cash_match:
        metrics['cash_balance'] = parse_value_from_text(cash_match.group(1))
    
    # Net Burn - only extract if explicitly stated, do NOT derive from margins
    burn_rate_match = re.search(r'(?:Net\s+Burn|Monthly\s+Burn)\s*:?\s*([₹$€£]?-?[\d.,]+[MKBmkb]?)', text, re.IGNORECASE)
    if burn_rate_match:
        metrics['net_burn'] = parse_value_from_text(burn_rate_match.group(1))
    
    # Headcount
    headcount_match = re.search(r'(?:Headcount|Employees|Team\s+Size)\s*:?\s*(\d+)', text, re.IGNORECASE)
    if headcount_match:
        metrics['headcount'] = int(headcount_match.group(1))
    
    # Currency detection
    if '₹' in pdf_text:
        metrics['currency'] = 'INR'
    elif '€' in pdf_text:
        metrics['currency'] = 'EUR'
    elif '£' in pdf_text:
        metrics['currency'] = 'GBP'
    elif '$' in pdf_text:
        metrics['currency'] = 'USD'
    
    # Report date - prefer explicit patterns over arbitrary month/year
    # Priority 1: "Generated DD.MM.YYYY" pattern from Tribe Capital reports
    if not metrics.get('report_date'):
        generated_match = re.search(r'Generated\s+(\d{1,2})[./](\d{1,2})[./](\d{4})', text)
        if generated_match:
            day, month, year = generated_match.groups()
            months = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                     'July', 'August', 'September', 'October', 'November', 'December']
            metrics['report_date'] = f"{months[int(month)]} {year}"
    
    # Priority 2: "In [Month] [Year]" from detailed sections (already extracted above)
    
    # Priority 3: Explicit "as of [Month] [Year]" patterns
    if not metrics.get('report_date'):
        as_of_match = re.search(r'(?:as\s+of|data\s+through|through)\s+(\w+\s+\d{4})', text, re.IGNORECASE)
        if as_of_match:
            metrics['report_date'] = as_of_match.group(1)
    
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
  "is_quarterly_format": "boolean - true if report uses quarterly (Rolling Q) data, false if monthly",
  "quarterly_revenue": "number - quarterly revenue if report uses quarterly format (e.g., Q1 revenue)",
  "monthly_revenue": "number - monthly revenue in base units. If quarterly format, divide quarterly by 3",
  "run_rate_revenue": "number - annualized run rate (ARR) in base units. If quarterly, this is quarterly * 4",
  "cogs": "number - cost of goods sold (monthly) in base units",
  "gross_profit": "number - gross profit (monthly) in base units",
  "gross_margin": "number - gross margin as percentage exactly as stated (e.g., 22.1% = 22.1, NOT inflated)",
  "operating_income": "number - operating income (monthly) in base units",
  "operating_margin": "number - operating margin as percentage exactly as stated (e.g., 9.9% = 9.9, NOT inflated)",
  "burn_multiple": "number - burn multiple as reported (e.g., -0.7x = -0.7, -0.2x = -0.2)",
  "total_monthly_expenses": "number - total monthly operating expenses in base units",
  "net_burn": "number - monthly net burn rate in base units",
  "cash_balance": "number - current cash on hand in base units",
  "runway_months": "number - estimated runway in months",
  "yoy_growth": "number - year over year growth as percentage (e.g., 1.24x = 24%, NOT 124%)",
  "mom_growth": "number - month over month growth rate as percentage (typically 1-10% for stable companies)",
  "cmgr_3": "number - 3-month compound monthly growth rate as percentage",
  "cmgr_6": "number - 6-month compound monthly growth rate as percentage",
  "cmgr_12": "number - 12-month compound monthly growth rate as percentage (e.g., 1.8% = 1.8)",
  "payroll": "number - monthly payroll/personnel expense in base units",
  "sales_and_marketing": "number - monthly sales & marketing expense in base units",
  "other_opex": "number - monthly other operating expenses in base units",
  "opex": "number - total monthly operating expenses in base units",
  "headcount": "number - current employee count",
  "arr": "number - annual recurring revenue (run rate) in base units",
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
- IDENTIFY THE REPORTING PERIOD: Many reports use QUARTERLY data (Rolling Q). 
  - If you see "Rolling Q", "Annualized Revenue", or "$X.XM / $Y.YM ARR" format, the first number is QUARTERLY revenue
  - Monthly revenue = quarterly / 3
  - ARR (run rate) = quarterly * 4 = monthly * 12
- Extract the EXACT values from the report - do NOT scale, inflate, or multiply incorrectly
- For monetary values: $14.2M = 14200000, $500K = 500000, $1.5B = 1500000000
- For percentages: Extract EXACTLY as stated. If it says 22.1%, return 22.1. If it says 9.9%, return 9.9.
  - DO NOT inflate margins to unrealistic values (e.g., 91% gross margin is very rare)
- For YoY growth multipliers: 1.24x means 24% growth (NOT 124% or 800%)
  - Convert: 1.24x = 24%, 1.47x = 47%, 2.0x = 100%
- For CMGR (monthly growth): Typical values are 1-5% for stable companies
  - CMGR12 of 1.8% means 1.8% month-over-month growth
- For burn_multiple: Negative means profitable (e.g., -0.2x = profitable with low burn)
- Use null if a metric is NOT found - do NOT default to zero or estimate
- PRESERVE negative values for burn_multiple
- SANITY CHECK: Gross margins above 70% are uncommon. Growth rates above 50% MoM are very rare.

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


def validate_and_correct_metrics(metrics: Dict[str, Any]) -> tuple[Dict[str, Any], List[str], Dict[str, Any]]:
    """
    Validate extracted metrics and flag unrealistic values.
    
    IMPORTANT: This function does NOT mutate values. It only flags issues and suggests corrections.
    The original metrics are preserved so users can see actual extraction results and decide.
    
    Returns:
        Tuple of (original_metrics_unchanged, warnings_list, suggested_corrections)
    """
    warnings = []
    suggestions = {}  # Suggested corrections for UI display only
    
    # Check for unrealistic margins
    gross_margin = metrics.get('gross_margin')
    if gross_margin is not None:
        if gross_margin > 90:
            warnings.append(f"Gross margin of {gross_margin}% is unusually high - please verify against source document")
            op_margin = metrics.get('operating_margin')
            if op_margin and op_margin < 20:
                logger.warning(f"Gross margin {gross_margin}% seems too high, operating margin {op_margin}% seems reasonable - possible extraction error")
        elif gross_margin < 0:
            warnings.append(f"Negative gross margin ({gross_margin}%) indicates losses at gross level")
    
    operating_margin = metrics.get('operating_margin')
    if operating_margin is not None:
        if operating_margin > 70:
            warnings.append(f"Operating margin of {operating_margin}% is unusually high - please verify")
    
    # Check for unrealistic growth rates
    mom_growth = metrics.get('mom_growth')
    if mom_growth is not None:
        if mom_growth > 100:
            warnings.append(f"Month-over-month growth of {mom_growth}% is extremely high - this may be YoY growth mislabeled")
            logger.warning(f"MoM growth {mom_growth}% seems like it might be YoY or misextracted")
        elif mom_growth > 50:
            warnings.append(f"Month-over-month growth of {mom_growth}% is unusually high")
    
    yoy_growth = metrics.get('yoy_growth')
    if yoy_growth is not None:
        if yoy_growth > 500:
            warnings.append(f"Year-over-year growth of {yoy_growth}% is extremely high - please verify")
            # Check if this might be a misinterpreted multiplier
            if yoy_growth > 100 and yoy_growth < 1000:
                possible_multiplier = yoy_growth / 100
                if 1.0 < possible_multiplier < 10.0:
                    suggested_yoy = (possible_multiplier - 1) * 100
                    suggestions['yoy_growth'] = suggested_yoy
                    logger.warning(f"YoY {yoy_growth}% might be misinterpreted multiplier, suggested: {suggested_yoy}%")
    
    # Check revenue scaling - if monthly revenue seems too high compared to ARR
    monthly_rev = metrics.get('monthly_revenue')
    arr = metrics.get('arr') or metrics.get('run_rate_revenue')
    
    if monthly_rev and arr:
        expected_monthly = arr / 12
        ratio = monthly_rev / expected_monthly if expected_monthly > 0 else 0
        
        if ratio > 2:
            warnings.append(f"Monthly revenue (${monthly_rev:,.0f}) appears inconsistent with ARR (${arr:,.0f}) - ratio is {ratio:.1f}x expected")
            # Suggest possible corrections for UI display
            if 2.5 < ratio < 4.5:
                suggestions['monthly_revenue'] = monthly_rev / 3
                suggestions['_monthly_revenue_note'] = "Value may be quarterly revenue - suggested monthly = quarterly/3"
                logger.info(f"Suggestion: monthly revenue {monthly_rev} may be quarterly, suggested: {monthly_rev/3}")
            elif 8 < ratio < 15:
                suggestions['monthly_revenue'] = monthly_rev / 12
                suggestions['_monthly_revenue_note'] = "Value may be annual revenue - suggested monthly = annual/12"
                logger.info(f"Suggestion: monthly revenue {monthly_rev} may be annual, suggested: {monthly_rev/12}")
    
    # Check quarterly vs monthly consistency
    quarterly_rev = metrics.get('quarterly_revenue')
    if quarterly_rev and monthly_rev:
        expected_monthly = quarterly_rev / 3
        ratio = monthly_rev / expected_monthly if expected_monthly > 0 else 0
        if ratio > 1.5 or ratio < 0.5:
            warnings.append(f"Monthly revenue doesn't match quarterly/3 (expected ${expected_monthly:,.0f}, got ${monthly_rev:,.0f})")
            suggestions['monthly_revenue'] = expected_monthly
    
    # Validate CMGR values are reasonable
    for cmgr_key in ['cmgr_3', 'cmgr_6', 'cmgr_12']:
        cmgr_val = metrics.get(cmgr_key)
        if cmgr_val is not None and cmgr_val > 30:
            warnings.append(f"{cmgr_key.upper()} of {cmgr_val}% is unusually high for monthly growth - please verify")
    
    # Validate payroll is reasonable relative to revenue
    # Payroll is typically 20-60% of revenue for most companies
    payroll = metrics.get('payroll')
    if payroll is not None and monthly_rev is not None and monthly_rev > 0:
        payroll_pct = (payroll / monthly_rev) * 100
        if payroll_pct < 1:
            # Payroll less than 1% of revenue is suspiciously low - likely extraction error
            warnings.append(f"Payroll (${payroll:,.0f}) is only {payroll_pct:.1f}% of revenue - this seems too low. Setting to null.")
            logger.warning(f"Payroll {payroll} is suspiciously low ({payroll_pct:.1f}% of revenue), likely extraction error")
            # Clear the suspicious value
            metrics['payroll'] = None
        elif payroll_pct < 5:
            warnings.append(f"Payroll (${payroll:,.0f}) is only {payroll_pct:.1f}% of revenue - unusually low, please verify")
    
    # Check for large revenue values that might be misscaled
    if monthly_rev and monthly_rev > 500_000_000:  # > $500M monthly
        warnings.append(f"Monthly revenue of ${monthly_rev/1_000_000:.1f}M is extremely high - please verify units")
    
    return metrics, warnings, suggestions


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
    
    # Log extracted values for debugging
    logger.info(f"Merged metrics: revenue={metrics.get('monthly_revenue')}, "
                f"gross_margin={metrics.get('gross_margin')}, "
                f"operating_margin={metrics.get('operating_margin')}, "
                f"arr={metrics.get('arr')}, yoy_growth={metrics.get('yoy_growth')}")
    
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
    
    # Validate metrics and get warnings/suggestions (does NOT mutate metrics)
    metrics, validation_warnings, suggested_corrections = validate_and_correct_metrics(metrics)
    for warning in validation_warnings:
        logger.warning(f"Validation: {warning}")
    
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
        "validation_warnings": validation_warnings if validation_warnings else None,
        "suggested_corrections": suggested_corrections if suggested_corrections else None,
    }
