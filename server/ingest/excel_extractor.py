import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from server.lib.lazy_imports import pd

logger = logging.getLogger(__name__)

MAX_EXCEL_SIZE_MB = 20
MIN_METRICS_COUNT = 3  # Minimum metrics to consider extraction successful


def format_number_as_words(value: float, currency: str = "USD", is_percentage: bool = False) -> Optional[str]:
    """Convert a numeric value to a word-based representation.
    
    Examples:
        14246988.40 → "14.2 million USD"
        125000 → "125 thousand USD"
        -3600000 → "-3.6 million USD"
        46.62 (percentage) → "46.6%"
    """
    if value is None:
        return None
    
    if is_percentage:
        return f"{value:.1f}%"
    
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    
    if abs_value >= 1_000_000_000:
        formatted = f"{sign}{abs_value / 1_000_000_000:.1f} billion {currency}"
    elif abs_value >= 1_000_000:
        formatted = f"{sign}{abs_value / 1_000_000:.1f} million {currency}"
    elif abs_value >= 1_000:
        formatted = f"{sign}{abs_value / 1_000:.1f} thousand {currency}"
    else:
        formatted = f"{sign}{abs_value:,.2f} {currency}"
    
    return formatted


def create_word_representations(metrics: Dict[str, Any], currency: str = "USD") -> Dict[str, str]:
    """Create word-based representations for all monetary metrics.
    
    Returns a dictionary with keys like 'revenue_words', 'gross_profit_words', etc.
    """
    monetary_fields = {
        'revenue', 'monthly_revenue', 'cogs', 'gross_profit', 'operating_income',
        'net_income', 'sales_and_marketing', 'other_opex', 'payroll', 'opex',
        'net_burn', 'monthly_surplus', 'cash_balance', 'mrr', 'arr', 'ltv', 'cac',
        'arpu', 'net_revenue_india', 'net_revenue_international', 
        'net_revenue_ecommerce', 'net_revenue_other', 'marketing_expense'
    }
    
    percentage_fields = {
        'gross_margin', 'operating_margin', 'mom_growth', 'yoy_growth',
        'revenue_growth_mom', 'ndr'
    }
    
    ratio_fields = {
        'burn_multiple', 'rule_of_40', 'magic_number', 'margin_magic_number',
        'margin_burn_multiple', 'ltv_cac_ratio', 'lifetime_gross_margin',
        'lifetime_operating_margin'
    }
    
    word_representations = {}
    
    for field, value in metrics.items():
        if value is None:
            continue
        
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            continue
        
        if field in monetary_fields:
            word_representations[f"{field}_words"] = format_number_as_words(num_value, currency)
        elif field in percentage_fields:
            word_representations[f"{field}_words"] = format_number_as_words(num_value, currency, is_percentage=True)
        elif field in ratio_fields:
            sign = "-" if num_value < 0 else ""
            word_representations[f"{field}_words"] = f"{sign}{abs(num_value):.2f}x"
    
    return word_representations


def get_openai_client():
    """Get OpenAI client with validation."""
    from openai import OpenAI
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


DEFAULT_INR_TO_USD_RATE = 0.012  # ~83 INR per USD


def detect_currency(df: pd.DataFrame, file_path: str) -> str:
    """Detect currency from sheet metadata or file context.
    
    Note: Many financial exports (like Termina) already normalize values to USD,
    so we default to USD unless explicit INR indicators are found.
    """
    for idx in df.index:
        if isinstance(idx, str):
            idx_lower = idx.lower()
            if '₹' in idx_lower or 'rupee' in idx_lower or '(inr)' in idx_lower:
                return 'INR'
            if '$' in idx_lower or 'dollar' in idx_lower or '(usd)' in idx_lower:
                return 'USD'
    
    for col in df.columns:
        if isinstance(col, str):
            col_lower = col.lower()
            if '₹' in col_lower or '(inr)' in col_lower:
                return 'INR'
            if '$' in col_lower or '(usd)' in col_lower:
                return 'USD'
    
    return 'USD'


def convert_currency(value: float, from_currency: str, to_currency: str = 'USD', 
                     fx_rate: Optional[float] = None) -> float:
    """Convert currency value. Currently supports INR to USD."""
    if from_currency == to_currency:
        return value
    
    if from_currency == 'INR' and to_currency == 'USD':
        rate = fx_rate if fx_rate else DEFAULT_INR_TO_USD_RATE
        return value * rate
    
    if from_currency == 'USD' and to_currency == 'INR':
        rate = fx_rate if fx_rate else (1 / DEFAULT_INR_TO_USD_RATE)
        return value * rate
    
    logger.warning(f"Unsupported currency conversion: {from_currency} to {to_currency}")
    return value


def get_value_from_row(df: pd.DataFrame, row_names: List[str], column: str) -> Optional[float]:
    """Extract value from a row matching any of the given names."""
    for name in row_names:
        if name in df.index:
            value = df.loc[name, column]
            if pd.notna(value):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    pass
        for idx in df.index:
            if isinstance(idx, str):
                idx_stripped = idx.strip()
                if idx_stripped == name or name.lower() in idx_stripped.lower():
                    value = df.loc[idx, column]
                    if pd.notna(value):
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            pass
    return None


def parse_income_statement(file_path: str, fx_rate: Optional[float] = None) -> Dict[str, Any]:
    """Parse Income Statement sheet from Termina Excel export with comprehensive extraction.
    
    Extracts:
    - Revenue and revenue breakdowns
    - COGS, Gross Profit, Sales & Marketing, Other Opex, Operating Income
    - Derived metrics: lifetime_gross_margin, lifetime_operating_margin, rule_of_40, 
      magic_number, burn_multiple, margin_burn_multiple
    - Currency conversion (INR to USD)
    - Month-over-month revenue growth
    """
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
        
        detected_currency = detect_currency(df, file_path)
        logger.info(f"Detected currency: {detected_currency}")
        
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
                prev_col = numeric_cols[-2] if len(numeric_cols) > 1 else None
            else:
                raise ValueError("No date or numeric columns found in the spreadsheet")
        else:
            sorted_dates = sorted(date_columns, key=lambda x: x[1])
            latest_col = sorted_dates[-1][0]
            prev_col = sorted_dates[-2][0] if len(sorted_dates) > 1 else None
        
        logger.info(f"Using latest column: {latest_col}, previous column: {prev_col}")
        
        row_mappings = {
            'revenue': ['Revenue', 'Total Revenue', 'Net Revenue', 'Sales', 'Total Sales'],
            'net_revenue_india': ['    Net Revenues (Astrotalk India)', 'Net Revenues (Astrotalk India)', 'Net Revenue India', 'India Revenue'],
            'net_revenue_international': ['    Net Revenues (Astrotalk International)', 'Net Revenues (Astrotalk International)', 'Net Revenue International', 'International Revenue'],
            'net_revenue_ecommerce': ['    Net Revenues (E-Commerce)', 'Net Revenues (E-Commerce)', 'E-Commerce Revenue', 'Ecommerce Revenue'],
            'net_revenue_other': ['    Net Revenues (Other Experimental Apps)', 'Net Revenues (Other Experimental Apps)', 'Other Revenue'],
            'cogs': ['COGS', 'Cost of Goods Sold', 'Cost of Revenue', 'Direct Costs'],
            'gross_profit': ['Gross Profit', 'Gross Income'],
            'sales_and_marketing': ['Sales And Marketing', 'Sales & Marketing', 'Marketing', 'Marketing Expenses'],
            'other_opex': ['Other Opex', 'Other Operating Expenses', 'General & Admin'],
            'operating_income': ['Operating Income', 'Operating Profit', 'EBIT'],
            'net_income': ['Net Income', 'Net Profit', 'Profit After Tax'],
            'payroll': ['Payroll', 'Salaries', 'Employee Costs', 'Personnel Expenses'],
            'lifetime_gross_margin': ['lifetime_gross_margin', 'Lifetime Gross Margin'],
            'lifetime_operating_margin': ['lifetime_operating_margin', 'Lifetime Operating Margin'],
            'rule_of_40': ['rule_of_40', 'Rule of 40'],
            'magic_number': ['magic_number', 'Magic Number'],
            'margin_magic_number': ['margin_magic_number', 'Margin Magic Number'],
            'burn_multiple': ['burn_multiple', 'Burn Multiple'],
            'margin_burn_multiple': ['margin_burn_multiple', 'Margin Burn Multiple'],
        }
        
        expense_categories = {'cogs', 'sales_and_marketing', 'other_opex', 'payroll'}
        monetary_fields = {'revenue', 'net_revenue_india', 'net_revenue_international', 
                          'net_revenue_ecommerce', 'net_revenue_other', 'cogs', 'gross_profit',
                          'sales_and_marketing', 'other_opex', 'operating_income', 'net_income', 'payroll'}
        
        metrics = {}
        metrics_original = {}
        
        for metric_key, possible_names in row_mappings.items():
            raw_value = get_value_from_row(df, possible_names, latest_col)
            
            if raw_value is not None:
                if metric_key in expense_categories and raw_value < 0:
                    raw_value = abs(raw_value)
                
                metrics_original[metric_key] = raw_value
                
                if metric_key in monetary_fields and detected_currency != 'USD':
                    metrics[metric_key] = convert_currency(raw_value, detected_currency, 'USD', fx_rate)
                else:
                    metrics[metric_key] = raw_value
        
        revenue_prev = None
        if prev_col is not None:
            revenue_prev = get_value_from_row(df, row_mappings['revenue'], prev_col)
        
        revenue_growth_mom = None
        if 'revenue' in metrics_original and revenue_prev and revenue_prev != 0:
            revenue_growth_mom = ((metrics_original['revenue'] - revenue_prev) / revenue_prev) * 100
            metrics['revenue_growth_mom'] = revenue_growth_mom
        
        if 'revenue' in metrics and 'cogs' in metrics and 'gross_profit' not in metrics:
            metrics['gross_profit'] = metrics['revenue'] - metrics['cogs']
        
        if 'revenue' in metrics and 'gross_profit' in metrics:
            computed_gross_margin = (metrics['gross_profit'] / metrics['revenue']) * 100
            if 'lifetime_gross_margin' not in metrics:
                metrics['gross_margin'] = computed_gross_margin
            else:
                metrics['gross_margin'] = metrics['lifetime_gross_margin'] * 100
        
        if 'revenue' in metrics and 'operating_income' in metrics:
            computed_operating_margin = (metrics['operating_income'] / metrics['revenue']) * 100
            if 'lifetime_operating_margin' not in metrics:
                metrics['operating_margin'] = computed_operating_margin
            else:
                metrics['operating_margin'] = metrics['lifetime_operating_margin'] * 100
        
        if 'operating_income' in metrics:
            metrics['monthly_surplus'] = metrics['operating_income']
        
        if isinstance(latest_col, datetime):
            report_date = latest_col.strftime('%Y-%m-%d')
        elif isinstance(latest_col, str):
            report_date = latest_col
        else:
            report_date = str(latest_col)
        
        return {
            'sheet_name': sheet_name,
            'report_date': report_date,
            'latest_column': str(latest_col),
            'previous_column': str(prev_col) if prev_col else None,
            'detected_currency': detected_currency,
            'target_currency': 'USD',
            'fx_rate_used': fx_rate or DEFAULT_INR_TO_USD_RATE if detected_currency == 'INR' else 1.0,
            'metrics': metrics,
            'metrics_original_currency': metrics_original,
            'revenue_prev_month': convert_currency(revenue_prev, detected_currency, 'USD', fx_rate) if revenue_prev else None,
            'available_rows': list(df.index)[:50],
        }
        
    except Exception as e:
        logger.warning(f"Structured parsing failed: {e}")
        import traceback
        logger.warning(traceback.format_exc())
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


def validate_excel_metrics(metrics: Dict[str, Any]) -> tuple:
    """Validate extracted metrics and return warnings/suggestions without mutating.
    
    Returns: (metrics, warnings, suggested_corrections)
    - metrics: Original metrics unchanged
    - warnings: List of warning messages about suspicious values
    - suggested_corrections: Dict of {field: suggested_value} for UI display
    """
    warnings = []
    suggested_corrections = {}
    
    # Check for unrealistic margins (>90% is suspicious)
    gross_margin = metrics.get('gross_margin')
    if gross_margin is not None and gross_margin > 90:
        warnings.append(f"Gross margin {gross_margin:.1f}% is unusually high - please verify")
    
    operating_margin = metrics.get('operating_margin')
    if operating_margin is not None and operating_margin > 90:
        warnings.append(f"Operating margin {operating_margin:.1f}% is unusually high - please verify")
    
    # Check if lifetime margins were not properly converted to percentage in gross_margin
    # Only warn if gross_margin is also in decimal form (< 1), meaning conversion didn't happen
    lifetime_gm = metrics.get('lifetime_gross_margin')
    gross_margin_val = metrics.get('gross_margin')
    if lifetime_gm is not None and 0 < lifetime_gm < 1:
        if gross_margin_val is None or (gross_margin_val is not None and gross_margin_val < 1):
            # Conversion didn't happen - gross_margin should be in percentage form
            warnings.append(f"Lifetime gross margin appears to be in decimal form ({lifetime_gm:.2f}) and was not converted")
    
    # Check for unrealistic MoM growth (>100% is suspicious for established companies)
    mom_growth = metrics.get('mom_growth') or metrics.get('revenue_growth_mom')
    if mom_growth is not None and abs(mom_growth) > 100:
        warnings.append(f"MoM growth {mom_growth:.1f}% seems high - please verify")
    
    # Check for potential quarterly/annual data being treated as monthly
    revenue = metrics.get('revenue')
    if revenue is not None and revenue > 100_000_000:  # >$100M monthly is rare
        warnings.append(f"Monthly revenue ${revenue/1e6:.1f}M is very high - could this be quarterly or annual?")
    
    logger.info(f"Excel validation: {len(warnings)} warnings generated")
    return metrics, warnings, suggested_corrections


def aggregate_rows_by_keywords(df: pd.DataFrame, column: str, keywords: List[str], 
                                exclude_keywords: Optional[List[str]] = None) -> tuple:
    """
    Aggregate values from ALL rows that match any of the keywords.
    
    Returns: (total_value, matched_rows: List[str])
    """
    exclude_keywords = exclude_keywords or []
    total = 0.0
    matched_rows = []
    
    for idx in df.index:
        if not isinstance(idx, str):
            continue
        
        idx_lower = idx.strip().lower()
        
        excluded = any(excl.lower() in idx_lower for excl in exclude_keywords)
        if excluded:
            continue
        
        matched = any(kw.lower() in idx_lower for kw in keywords)
        if matched:
            try:
                value = df.loc[idx, column]
                if pd.notna(value):
                    num_value = float(value)
                    if num_value < 0:
                        num_value = abs(num_value)
                    total += num_value
                    matched_rows.append(idx.strip())
            except (ValueError, TypeError):
                continue
    
    return (total if matched_rows else None, matched_rows)


def parse_income_statement_canonical(file_path: str, fx_rate: Optional[float] = None) -> Dict[str, Any]:
    """
    Parse Income Statement with PROPER marketing aggregation and canonical model.
    
    Key differences from parse_income_statement():
    1. Aggregates ALL marketing-related rows (not just picks one)
    2. Sets payroll=None when not found (with warning)
    3. Returns canonical NormalizedMonthlyFinancials structure
    4. Includes full traceability (sources)
    """
    from server.models.canonical_financials import (
        NormalizedMonthlyFinancials, Period, ExpenseBreakdown, SourceReference,
        MARKETING_KEYWORDS, PAYROLL_KEYWORDS, COGS_KEYWORDS, OPERATING_KEYWORDS,
        OTHER_OPEX_KEYWORDS, REVENUE_KEYWORDS, run_validation
    )
    
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
        
        if len(df.columns) > 0 and df.columns[0] in ['index', 'Index', 'Metric', 'metric', 'Unnamed: 0']:
            df = df.set_index(df.columns[0])
        
        detected_currency = detect_currency(df, file_path)
        logger.info(f"[CANONICAL] Detected currency: {detected_currency}")
        
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
                latest_date = datetime.now()
            else:
                raise ValueError("No date or numeric columns found in the spreadsheet")
        else:
            sorted_dates = sorted(date_columns, key=lambda x: x[1])
            latest_col = sorted_dates[-1][0]
            latest_date = sorted_dates[-1][1]
        
        logger.info(f"[CANONICAL] Using latest column: {latest_col}")
        
        sources = {}
        
        revenue_val, revenue_rows = aggregate_rows_by_keywords(
            df, latest_col, REVENUE_KEYWORDS,
            exclude_keywords=[
                'net revenues (', 'net revenue india', 'net revenue international', 
                'net revenue ecommerce', 'net revenue other', 'revenue (',
                'sales and marketing', 'sales & marketing', 'marketing expense',
                'operating income', 'operating profit', 'net income', 'other income',
                'gross income', 'income tax', 'interest income'
            ]
        )
        if revenue_val is None:
            all_rev, all_rev_rows = aggregate_rows_by_keywords(df, latest_col, ['revenue', 'sales', 'income'])
            if all_rev:
                revenue_val = all_rev
                revenue_rows = all_rev_rows
        sources['revenue'] = SourceReference(sheet=sheet_name, row_labels=revenue_rows, column=str(latest_col))
        
        cogs_val, cogs_rows = aggregate_rows_by_keywords(df, latest_col, COGS_KEYWORDS)
        sources['cogs'] = SourceReference(sheet=sheet_name, row_labels=cogs_rows, column=str(latest_col), raw_value=cogs_val)
        
        marketing_val, marketing_rows = aggregate_rows_by_keywords(
            df, latest_col, MARKETING_KEYWORDS,
            exclude_keywords=['cogs', 'payroll', 'salary']
        )
        sources['marketing'] = SourceReference(sheet=sheet_name, row_labels=marketing_rows, column=str(latest_col), raw_value=marketing_val)
        logger.info(f"[CANONICAL] Marketing aggregation: ${marketing_val:,.0f} from {len(marketing_rows)} rows: {marketing_rows}")
        
        payroll_val, payroll_rows = aggregate_rows_by_keywords(df, latest_col, PAYROLL_KEYWORDS)
        sources['payroll'] = SourceReference(sheet=sheet_name, row_labels=payroll_rows, column=str(latest_col), raw_value=payroll_val)
        if not payroll_rows:
            logger.info("[CANONICAL] PAYROLL_NOT_FOUND - No payroll rows detected, setting to null")
        
        operating_val, operating_rows = aggregate_rows_by_keywords(
            df, latest_col, OPERATING_KEYWORDS,
            exclude_keywords=['operating income', 'operating profit', 'operating margin', 'marketing', 'payroll', 'cogs']
        )
        sources['operating'] = SourceReference(sheet=sheet_name, row_labels=operating_rows, column=str(latest_col), raw_value=operating_val)
        
        other_val, other_rows = aggregate_rows_by_keywords(
            df, latest_col, OTHER_OPEX_KEYWORDS,
            exclude_keywords=['operating income', 'cogs', 'marketing', 'payroll']
        )
        sources['other'] = SourceReference(sheet=sheet_name, row_labels=other_rows, column=str(latest_col), raw_value=other_val)
        
        def convert_if_needed(val):
            if val is None:
                return None
            if detected_currency != 'USD':
                return convert_currency(val, detected_currency, 'USD', fx_rate)
            return val
        
        period = Period(
            year=latest_date.year,
            month=latest_date.month,
            label=latest_date.strftime('%b %Y')
        )
        
        financials = NormalizedMonthlyFinancials(
            period=period,
            revenue=convert_if_needed(revenue_val) or 0,
            expenses=ExpenseBreakdown(
                cogs=convert_if_needed(cogs_val),
                marketing=convert_if_needed(marketing_val),
                payroll=convert_if_needed(payroll_val),
                operating=convert_if_needed(operating_val),
                other=convert_if_needed(other_val),
            ),
            sources=sources,
            currency='USD',
            detected_currency=detected_currency,
            fx_rate_used=fx_rate if detected_currency != 'USD' else None
        )
        
        financials.compute_derived_metrics()
        financials = run_validation(financials)
        
        logger.info(f"[CANONICAL] Results: revenue=${financials.revenue:,.0f}, totalExp=${financials.total_expenses:,.0f}, netBurn=${financials.net_burn:,.0f}, isProfitable={financials.is_profitable}")
        
        return {
            'success': True,
            'canonical': financials.to_dict(),
            'sheet_name': sheet_name,
            'available_rows': list(df.index)[:100],
            'extraction_method': 'canonical_structured'
        }
        
    except Exception as e:
        logger.error(f"[CANONICAL] Parsing failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'success': False, 'error': str(e)}


def process_termina_excel(file_path: str, max_size_mb: float = MAX_EXCEL_SIZE_MB, use_canonical: bool = True) -> Dict[str, Any]:
    """Process a Termina Excel export and extract financial metrics.
    
    Uses a two-stage approach:
    1. Try structured parsing for known formats (faster, works for standard layouts)
    2. Fall back to OpenAI analysis for complex/unknown formats
    
    When use_canonical=True (default), uses the new canonical model with proper
    marketing aggregation and payroll null handling.
    """
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise ValueError(f"Excel file too large ({file_size_mb:.1f}MB). Maximum allowed is {max_size_mb}MB.")
    
    extraction_method = "structured"
    canonical_result = None
    
    if use_canonical:
        canonical_result = parse_income_statement_canonical(file_path)
        if canonical_result.get('success'):
            logger.info("[CANONICAL] Using canonical extraction")
            extraction_method = "canonical"
    
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
    
    # Validate extracted metrics (warn-only, no mutation)
    validated_metrics, validation_warnings, suggested_corrections = validate_excel_metrics(metrics)
    
    # Generate summary
    summary = parsed.get('ai_metrics', {}).get('summary') or generate_ai_summary(metrics)
    
    baseline_data = {
        "monthly_revenue": metrics.get("revenue"),
        "gross_margin": metrics.get("gross_margin"),
        "operating_margin": metrics.get("operating_margin"),
        "net_burn": metrics.get("net_burn"),
        "monthly_surplus": metrics.get("monthly_surplus"),
        "cash_balance": metrics.get("cash_balance"),
        "runway_months": metrics.get("runway_months"),
        "yoy_growth": metrics.get("yoy_growth"),
        "mom_growth": metrics.get("mom_growth") or metrics.get("revenue_growth_mom"),
        "payroll": metrics.get("payroll"),
        "opex": metrics.get("opex"),
        "headcount": metrics.get("headcount"),
        "customers": metrics.get("customers"),
        "cogs": metrics.get("cogs"),
        "gross_profit": metrics.get("gross_profit"),
        "operating_income": metrics.get("operating_income"),
        "net_income": metrics.get("net_income"),
        "total_expenses": metrics.get("total_expenses"),
        "sales_and_marketing": metrics.get("sales_and_marketing") or metrics.get("marketing"),
        "other_opex": metrics.get("other_opex"),
        "arpu": metrics.get("arpu"),
        "burn_multiple": metrics.get("burn_multiple"),
        "rule_of_40": metrics.get("rule_of_40"),
        "magic_number": metrics.get("magic_number"),
        "margin_magic_number": metrics.get("margin_magic_number"),
        "margin_burn_multiple": metrics.get("margin_burn_multiple"),
        "lifetime_gross_margin": metrics.get("lifetime_gross_margin"),
        "lifetime_operating_margin": metrics.get("lifetime_operating_margin"),
        "net_revenue_india": metrics.get("net_revenue_india"),
        "net_revenue_international": metrics.get("net_revenue_international"),
        "net_revenue_ecommerce": metrics.get("net_revenue_ecommerce"),
        "net_revenue_other": metrics.get("net_revenue_other"),
    }
    
    baseline_data = {k: v for k, v in baseline_data.items() if v is not None}
    
    target_currency = parsed.get("target_currency", "USD")
    detected_currency = parsed.get("detected_currency", "USD")
    
    word_representations = create_word_representations(baseline_data, target_currency)
    
    original_word_representations = {}
    if detected_currency != target_currency and parsed.get("metrics_original_currency"):
        original_word_representations = create_word_representations(
            parsed.get("metrics_original_currency", {}), 
            detected_currency
        )
        for key, value in original_word_representations.items():
            word_representations[f"original_{key}"] = value
    
    baseline_data_with_words = {**baseline_data, **word_representations}
    
    result = {
        "source": "excel",
        "sheet_name": parsed.get("sheet_name"),
        "report_date": parsed.get("report_date"),
        "detected_currency": detected_currency,
        "target_currency": target_currency,
        "fx_rate_used": parsed.get("fx_rate_used"),
        "raw_metrics": metrics,
        "metrics_original_currency": parsed.get("metrics_original_currency", {}),
        "baseline_data": baseline_data_with_words,
        "word_representations": word_representations,
        "summary": summary,
        "extraction_successful": True,
        "extraction_method": extraction_method,
        "validation_warnings": validation_warnings,
        "suggested_corrections": suggested_corrections,
    }
    
    if canonical_result and canonical_result.get('success'):
        canonical = canonical_result['canonical']
        result['canonical'] = canonical
        
        result['baseline_data']['monthly_revenue'] = canonical.get('revenue')
        result['baseline_data']['cogs'] = canonical['expenses'].get('cogs')
        result['baseline_data']['sales_and_marketing'] = canonical['expenses'].get('marketing')
        result['baseline_data']['other_opex'] = canonical['expenses'].get('other')
        
        if canonical['expenses'].get('payroll') is None:
            result['baseline_data']['payroll'] = None
        else:
            result['baseline_data']['payroll'] = canonical['expenses'].get('payroll')
        
        result['baseline_data']['total_expenses'] = canonical.get('total_expenses')
        result['baseline_data']['net_burn'] = canonical.get('net_burn')
        result['baseline_data']['is_profitable'] = canonical.get('is_profitable')
        result['baseline_data']['runway_months'] = canonical.get('runway_months')
        
        result['validation_warnings'] = canonical.get('validation', {}).get('warnings', [])
        result['validation_errors'] = canonical.get('validation', {}).get('errors', [])
        result['sources'] = canonical.get('sources', {})
        
        logger.info(f"[CANONICAL] Merged canonical data into result: revenue=${canonical.get('revenue'):,.0f}, marketing=${canonical['expenses'].get('marketing') or 0:,.0f}")
    
    return result
