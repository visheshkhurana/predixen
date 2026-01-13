import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
from openai import OpenAI

logger = logging.getLogger(__name__)

MAX_EXCEL_SIZE_MB = 20

def get_openai_client() -> OpenAI:
    """Get OpenAI client with validation."""
    api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    
    if not api_key:
        raise ValueError("OpenAI API key not configured. Please check environment settings.")
    
    return OpenAI(api_key=api_key, base_url=base_url)


def parse_income_statement(file_path: str) -> Dict[str, Any]:
    """Parse Income Statement sheet from Termina Excel export."""
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
        
        # Expense categories that should always be positive (take abs of negative values)
        # NOTE: operating_income and net_income are NOT included - they can be negative (losses)
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
                            # Normalize expenses: P&L convention often has expenses as negative
                            # We store all expenses as positive internally
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
                                # Normalize expenses: P&L convention often has expenses as negative
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
        logger.error(f"Error parsing Excel file: {e}")
        raise ValueError(f"Failed to parse Excel file: {str(e)}")


def generate_ai_summary(metrics: Dict[str, Any]) -> str:
    """Generate AI summary of the extracted metrics."""
    try:
        client = get_openai_client()
        
        metrics_text = "\n".join([f"- {k}: {v:,.2f}" if isinstance(v, float) else f"- {k}: {v}" 
                                   for k, v in metrics.items()])
        
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


def process_termina_excel(file_path: str, max_size_mb: float = MAX_EXCEL_SIZE_MB) -> Dict[str, Any]:
    """Process a Termina Excel export and extract financial metrics."""
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise ValueError(f"Excel file too large ({file_size_mb:.1f}MB). Maximum allowed is {max_size_mb}MB.")
    
    parsed = parse_income_statement(file_path)
    metrics = parsed.get('metrics', {})
    
    if not metrics:
        raise ValueError("No financial metrics could be extracted from the spreadsheet.")
    
    if 'revenue' not in metrics:
        raise ValueError("Revenue row not found in the spreadsheet. Please check the file format.")
    
    summary = generate_ai_summary(metrics)
    
    baseline_data = {
        "monthly_revenue": metrics.get("revenue"),
        "gross_margin": metrics.get("gross_margin"),
        "net_burn": metrics.get("net_burn"),
        "cash_balance": metrics.get("cash_balance"),
        "runway_months": metrics.get("runway_months"),
        "yoy_growth": metrics.get("yoy_growth"),
        "payroll": metrics.get("payroll"),
        "opex": metrics.get("opex"),
        "headcount": metrics.get("headcount"),
        "customers": metrics.get("customers"),
        "cogs": metrics.get("cogs"),
        "gross_profit": metrics.get("gross_profit"),
        "operating_income": metrics.get("operating_income"),
        "net_income": metrics.get("net_income"),
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
    }
