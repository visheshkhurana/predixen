import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
from openai import OpenAI

logger = logging.getLogger(__name__)

MAX_EXCEL_SIZE_MB = 20
MIN_METRICS_COUNT = 3  # Minimum metrics to consider extraction successful


def get_openai_client() -> OpenAI:
    """Get OpenAI client with validation."""
    api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    
    if not api_key:
        raise ValueError("OpenAI API key not configured. Please check environment settings.")
    
    return OpenAI(api_key=api_key, base_url=base_url)


EXCEL_EXTRACTION_PROMPT = """Analyze the following Excel spreadsheet data and extract all key financial and operational metrics.
The data is from a financial report (P&L, Income Statement, or similar financial document).

Return the result as a JSON object with these exact keys (use null if not found):

{
  "company_name": "string - the company name if visible",
  "report_date": "string - the date/period of the report (YYYY-MM-DD format if possible)",
  "currency": "string - the currency code (USD, EUR, GBP, INR, etc.)",
  "monthly_revenue": "number - monthly revenue (divide annual by 12 if only annual available)",
  "annual_revenue": "number - annual/yearly revenue if available",
  "cogs": "number - cost of goods sold (monthly if possible)",
  "gross_profit": "number - gross profit",
  "gross_margin": "number - gross margin as percentage (0-100)",
  "operating_income": "number - operating income/EBIT",
  "operating_margin": "number - operating margin as percentage",
  "net_income": "number - net income/profit after tax",
  "total_monthly_expenses": "number - total monthly operating expenses",
  "net_burn": "number - monthly net burn rate",
  "cash_balance": "number - current cash on hand",
  "runway_months": "number - estimated runway in months",
  "yoy_growth": "number - year over year growth rate as percentage",
  "mom_growth": "number - month over month growth rate as percentage",
  "payroll": "number - payroll/personnel expenses",
  "sales_and_marketing": "number - sales & marketing expenses",
  "other_opex": "number - other operating expenses",
  "opex": "number - total operating expenses (excluding COGS)",
  "headcount": "number - employee count",
  "arr": "number - annual recurring revenue",
  "mrr": "number - monthly recurring revenue",
  "customers": "number - total customer count",
  "arpu": "number - average revenue per user/customer",
  "summary": "string - brief 2-3 sentence summary of financial health"
}

Important instructions:
- Extract actual numbers from the data, not formatted strings
- Convert all monetary values to raw numbers (e.g., "$14.2M" becomes 14200000, "₹10L" becomes 1000000)
- Convert percentages to numbers (e.g., 85% becomes 85)
- CRITICAL: All expense values (COGS, payroll, marketing, opex, etc.) must be returned as POSITIVE numbers
- If values appear negative in P&L format (expenses shown as negatives), convert to positive
- Revenue and profit should maintain their natural sign (revenue positive, losses can be negative)
- Look at column headers to identify time periods (dates, months, years)
- Use the most recent period's data when multiple periods are available
- Be precise with the numbers - do not estimate or guess

Here is the spreadsheet data:

"""


def excel_to_text(file_path: str, max_rows: int = 100) -> str:
    """Convert Excel file to text format for AI analysis."""
    try:
        xl = pd.ExcelFile(file_path)
        text_parts = []
        
        for sheet_name in xl.sheet_names[:5]:  # Limit to first 5 sheets
            df = pd.read_excel(xl, sheet_name=sheet_name, nrows=max_rows)
            
            if df.empty:
                continue
            
            text_parts.append(f"\n=== Sheet: {sheet_name} ===\n")
            
            # Convert to string representation
            df_str = df.to_string(index=True, max_rows=max_rows, max_cols=20)
            text_parts.append(df_str)
        
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"Error converting Excel to text: {e}")
        raise ValueError(f"Could not read Excel file: {str(e)}")


def extract_metrics_with_openai(excel_text: str) -> Dict[str, Any]:
    """Use OpenAI to extract financial metrics from Excel text."""
    try:
        client = get_openai_client()
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst AI that extracts structured data from spreadsheets and financial reports. Always respond with valid JSON only, no markdown formatting."
                },
                {
                    "role": "user",
                    "content": EXCEL_EXTRACTION_PROMPT + excel_text[:20000]  # Limit text length
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
        
        logger.info("Successfully extracted metrics using OpenAI")
        return metrics
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI response as JSON: {e}")
        raise ValueError(f"AI response was not valid JSON. Please try again.")
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        raise ValueError(f"Failed to analyze Excel: {str(e)}")


def parse_income_statement(file_path: str) -> Dict[str, Any]:
    """Parse Income Statement sheet from Termina Excel export using structured approach."""
    try:
        xl = pd.ExcelFile(file_path)
        
        sheet_name = None
        for name in xl.sheet_names:
            if "income" in name.lower() and "statement" in name.lower():
                sheet_name = name
                break
        
        if not sheet_name:
            for name in xl.sheet_names:
                if "income" in name.lower() or "p&l" in name.lower() or "profit" in name.lower():
                    sheet_name = name
                    break
        
        if not sheet_name:
            sheet_name = xl.sheet_names[0]
            logger.warning(f"No Income Statement sheet found, using first sheet: {sheet_name}")
        
        df = pd.read_excel(xl, sheet_name=sheet_name)
        
        if df.columns[0] in ['index', 'Index', 'Metric', 'metric', 'Unnamed: 0']:
            df = df.set_index(df.columns[0])
        
        date_columns = []
        for col in df.columns:
            try:
                if isinstance(col, datetime):
                    date_columns.append((col, col))
                elif isinstance(col, str):
                    for fmt in ['%Y-%m', '%Y-%m-%d', '%m/%Y', '%B %Y', '%b %Y']:
                        try:
                            parsed = datetime.strptime(col, fmt)
                            date_columns.append((col, parsed))
                            break
                        except ValueError:
                            continue
            except Exception:
                continue
        
        if not date_columns:
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                latest_col = numeric_cols[-1]
            else:
                raise ValueError("No date or numeric columns found in the spreadsheet")
        else:
            sorted_dates = sorted(date_columns, key=lambda x: x[1])
            latest_col = sorted_dates[-1][0]
        
        metrics = {}
        row_mappings = {
            'revenue': ['Revenue', 'Total Revenue', 'Net Revenue', 'Sales', 'Total Sales'],
            'net_revenue_india': ['Net Revenues (Astrotalk India)', 'Net Revenue India', 'India Revenue'],
            'net_revenue_international': ['Net Revenues (Astrotalk International)', 'Net Revenue International', 'International Revenue'],
            'net_revenue_ecommerce': ['Net Revenues (E-Commerce)', 'E-Commerce Revenue', 'Ecommerce Revenue'],
            'net_revenue_other': ['Net Revenues (Other Experimental Apps)', 'Other Revenue'],
            'cogs': ['COGS', 'Cost of Goods Sold', 'Cost of Revenue', 'Direct Costs'],
            'gross_profit': ['Gross Profit', 'Gross Income', 'Gross Margin'],
            'operating_income': ['Operating Income', 'Operating Profit', 'EBIT'],
            'net_income': ['Net Income', 'Net Profit', 'Profit After Tax'],
            'payroll': ['Payroll', 'Salaries', 'Employee Costs', 'Personnel Expenses'],
            'marketing': ['Marketing', 'Marketing Expenses', 'Sales & Marketing'],
            'opex': ['Operating Expenses', 'OPEX', 'Total Operating Expenses'],
        }
        
        # Expense categories that should always be positive
        expense_categories = {'cogs', 'payroll', 'marketing', 'opex'}
        
        for metric_key, possible_names in row_mappings.items():
            found = False
            for name in possible_names:
                if found:
                    break
                if name in df.index:
                    value = df.loc[name, latest_col]
                    if pd.notna(value):
                        try:
                            raw_value = float(value)
                            if metric_key in expense_categories and raw_value < 0:
                                raw_value = abs(raw_value)
                            metrics[metric_key] = raw_value
                        except (ValueError, TypeError):
                            pass
                    found = True
                    break
                for idx in df.index:
                    if isinstance(idx, str) and name.lower() in idx.lower():
                        value = df.loc[idx, latest_col]
                        if pd.notna(value):
                            try:
                                raw_value = float(value)
                                if metric_key in expense_categories and raw_value < 0:
                                    raw_value = abs(raw_value)
                                metrics[metric_key] = raw_value
                            except (ValueError, TypeError):
                                pass
                        found = True
                        break
        
        if isinstance(latest_col, datetime):
            report_date = latest_col.strftime('%Y-%m-%d')
        elif isinstance(latest_col, str):
            report_date = latest_col
        else:
            report_date = str(latest_col)
        
        if 'revenue' in metrics and 'cogs' in metrics and 'gross_profit' not in metrics:
            metrics['gross_profit'] = metrics['revenue'] - metrics['cogs']
        
        if 'revenue' in metrics and 'gross_profit' in metrics:
            metrics['gross_margin'] = (metrics['gross_profit'] / metrics['revenue']) * 100
        
        return {
            'sheet_name': sheet_name,
            'report_date': report_date,
            'latest_column': str(latest_col),
            'metrics': metrics,
            'available_rows': list(df.index)[:50],
        }
        
    except Exception as e:
        logger.warning(f"Structured parsing failed: {e}")
        return {'metrics': {}, 'error': str(e)}


def generate_ai_summary(metrics: Dict[str, Any]) -> str:
    """Generate AI summary of the extracted metrics."""
    try:
        client = get_openai_client()
        
        metrics_text = "\n".join([f"- {k}: {v:,.2f}" if isinstance(v, float) else f"- {k}: {v}" 
                                   for k, v in metrics.items() if v is not None])
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst. Provide a brief 2-3 sentence summary of the company's financial health based on the metrics provided."
                },
                {
                    "role": "user",
                    "content": f"Summarize these financial metrics:\n{metrics_text}"
                }
            ],
            max_tokens=200,
            temperature=0.3,
            timeout=30,
        )
        
        return response.choices[0].message.content or ""
        
    except Exception as e:
        logger.warning(f"Could not generate AI summary: {e}")
        return ""


def normalize_expense_value(value: Any) -> Optional[float]:
    """Normalize expense value to always be positive."""
    if value is None:
        return None
    try:
        num = float(value)
        return abs(num)
    except (ValueError, TypeError):
        return None


def process_termina_excel(file_path: str, max_size_mb: float = MAX_EXCEL_SIZE_MB) -> Dict[str, Any]:
    """Process a Termina Excel export and extract financial metrics.
    
    Uses a two-stage approach:
    1. Try structured parsing for known formats (faster, works for standard layouts)
    2. Fall back to OpenAI analysis for complex/unknown formats
    """
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise ValueError(f"Excel file too large ({file_size_mb:.1f}MB). Maximum allowed is {max_size_mb}MB.")
    
    extraction_method = "structured"
    
    # Stage 1: Try structured parsing
    parsed = parse_income_statement(file_path)
    metrics = parsed.get('metrics', {})
    
    # Check if we got enough metrics
    if len(metrics) >= MIN_METRICS_COUNT and 'revenue' in metrics:
        logger.info(f"Structured extraction successful ({len(metrics)} metrics), using parsed data")
    else:
        # Stage 2: Fall back to AI extraction
        logger.info(f"Structured extraction found only {len(metrics)} metrics, using AI-based analysis")
        extraction_method = "ai"
        
        try:
            excel_text = excel_to_text(file_path)
            ai_metrics = extract_metrics_with_openai(excel_text)
            
            # Normalize expense fields
            expense_fields = ['cogs', 'opex', 'payroll', 'sales_and_marketing', 'other_opex', 
                              'total_monthly_expenses', 'net_burn']
            for field in expense_fields:
                if field in ai_metrics and ai_metrics[field] is not None:
                    ai_metrics[field] = normalize_expense_value(ai_metrics[field])
            
            # Map AI response to internal format
            metrics = {
                'revenue': ai_metrics.get('monthly_revenue') or ai_metrics.get('mrr'),
                'annual_revenue': ai_metrics.get('annual_revenue') or ai_metrics.get('arr'),
                'cogs': ai_metrics.get('cogs'),
                'gross_profit': ai_metrics.get('gross_profit'),
                'gross_margin': ai_metrics.get('gross_margin'),
                'operating_income': ai_metrics.get('operating_income'),
                'net_income': ai_metrics.get('net_income'),
                'payroll': ai_metrics.get('payroll'),
                'marketing': ai_metrics.get('sales_and_marketing'),
                'opex': ai_metrics.get('opex'),
                'total_expenses': ai_metrics.get('total_monthly_expenses'),
                'net_burn': ai_metrics.get('net_burn'),
                'cash_balance': ai_metrics.get('cash_balance'),
                'runway_months': ai_metrics.get('runway_months'),
                'yoy_growth': ai_metrics.get('yoy_growth'),
                'mom_growth': ai_metrics.get('mom_growth'),
                'headcount': ai_metrics.get('headcount'),
                'customers': ai_metrics.get('customers'),
                'arpu': ai_metrics.get('arpu'),
            }
            # Remove None values
            metrics = {k: v for k, v in metrics.items() if v is not None}
            
            # Store raw AI response
            parsed['ai_metrics'] = ai_metrics
            parsed['report_date'] = ai_metrics.get('report_date') or parsed.get('report_date')
            
        except Exception as e:
            logger.error(f"AI extraction also failed: {e}")
            if not metrics:
                raise ValueError(f"Could not extract data from Excel. Please ensure the file is a valid financial report. Error: {str(e)}")
    
    if not metrics:
        raise ValueError("No financial metrics could be extracted from the spreadsheet.")
    
    if 'revenue' not in metrics:
        logger.warning("Revenue row not found in the spreadsheet")
    
    # Generate summary
    summary = parsed.get('ai_metrics', {}).get('summary') or generate_ai_summary(metrics)
    
    baseline_data = {
        "monthly_revenue": metrics.get("revenue"),
        "gross_margin": metrics.get("gross_margin"),
        "net_burn": metrics.get("net_burn"),
        "cash_balance": metrics.get("cash_balance"),
        "runway_months": metrics.get("runway_months"),
        "yoy_growth": metrics.get("yoy_growth"),
        "mom_growth": metrics.get("mom_growth"),
        "payroll": metrics.get("payroll"),
        "opex": metrics.get("opex"),
        "headcount": metrics.get("headcount"),
        "customers": metrics.get("customers"),
        "cogs": metrics.get("cogs"),
        "gross_profit": metrics.get("gross_profit"),
        "operating_income": metrics.get("operating_income"),
        "net_income": metrics.get("net_income"),
        "total_expenses": metrics.get("total_expenses"),
        "sales_and_marketing": metrics.get("marketing"),
        "arpu": metrics.get("arpu"),
    }
    
    baseline_data = {k: v for k, v in baseline_data.items() if v is not None}
    
    return {
        "source": "excel",
        "sheet_name": parsed.get("sheet_name"),
        "report_date": parsed.get("report_date"),
        "raw_metrics": metrics,
        "baseline_data": baseline_data,
        "summary": summary,
        "extraction_successful": True,
        "extraction_method": extraction_method,
    }
