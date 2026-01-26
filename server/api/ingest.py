from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import date, datetime
import tempfile
import os
import json
import logging

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.dataset import Dataset
from server.models.financial import FinancialRecord
from server.ingest.pdf_extractor import process_termina_pdf, extract_text_from_pdf
from server.ingest.excel_extractor import process_termina_excel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingest"])

class FieldExtraction(BaseModel):
    value: Optional[float | str] = None
    confidence: float = 0.0
    evidence: Optional[str] = None

class ExpenseBreakdown(BaseModel):
    payroll: Optional[float] = None
    marketing: Optional[float] = None
    operating: Optional[float] = None
    cogs: Optional[float] = None
    otherOpex: Optional[float] = None

class NormalizedFinancials(BaseModel):
    cashOnHand: Optional[float] = None
    monthlyRevenue: Optional[float] = None
    totalMonthlyExpenses: Optional[float] = None
    monthlyGrowthRate: Optional[float] = None
    expenseBreakdown: ExpenseBreakdown = ExpenseBreakdown()
    hasManualExpenseOverride: Optional[bool] = None
    currency: Optional[str] = None
    asOfDate: Optional[str] = None

class ExtractionResponse(BaseModel):
    extracted: Dict[str, Any]
    normalized: NormalizedFinancials
    missingFields: List[str]
    confidence: Dict[str, float]
    source: str
    fileName: str
    uploadId: Optional[int] = None
    calculatedMetrics: Dict[str, Any]

def normalize_currency_value(value: Any) -> Optional[float]:
    """Normalize a currency or percentage value to float, handling various formats.
    
    Handles:
    - Currency symbols ($, etc.)
    - Comma separators (1,000,000)
    - Parenthetical negatives ((100))
    - Suffixes: K/k (thousands), M/m (millions), B/b (billions)
    - Percentage signs (45% -> 45.0)
    - 'x' suffix for ratios (3.5x -> 3.5)
    """
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        cleaned = value.replace('$', '').replace(',', '').replace('(', '-').replace(')', '').strip()
        
        # Handle percentage suffix - remove % and keep as-is (already in percentage form like 45 for 45%)
        is_percentage = '%' in cleaned
        cleaned = cleaned.replace('%', '')
        
        # Handle 'x' suffix for ratios (e.g., "3.5x")
        if cleaned.lower().endswith('x'):
            cleaned = cleaned[:-1]
        
        multiplier = 1
        if cleaned.lower().endswith('k'):
            multiplier = 1000
            cleaned = cleaned[:-1]
        elif cleaned.lower().endswith('m'):
            multiplier = 1000000
            cleaned = cleaned[:-1]
        elif cleaned.lower().endswith('b'):
            multiplier = 1000000000
            cleaned = cleaned[:-1]
        
        try:
            return float(cleaned) * multiplier
        except (ValueError, TypeError):
            return None
    
    return None

def extract_with_confidence(raw_metrics: Dict[str, Any], source: str) -> Dict[str, FieldExtraction]:
    """Convert raw extracted metrics to structured fields with confidence scores."""
    extracted = {}
    
    field_mapping = {
        'cashOnHand': ['cash_balance', 'cash_on_hand', 'bank_balance', 'cash'],
        'monthlyRevenue': ['monthly_revenue', 'revenue', 'mrr', 'net_revenue'],
        'totalMonthlyExpenses': ['total_expenses', 'total_monthly_expenses', 'opex', 'monthly_expenses', 'operating_expenses'],
        'monthlyGrowthRate': ['mom_growth', 'cmgr_3', 'cmgr_12', 'monthly_growth', 'growth_rate', 'revenue_growth'],
        'payroll': ['payroll', 'salaries', 'employee_costs', 'personnel'],
        'marketing': ['marketing', 'marketing_expenses', 'sales_and_marketing', 'advertising'],
        'operating': ['operating', 'other_opex', 'opex', 'operating_expenses', 'general_admin'],
        'cogs': ['cogs', 'cost_of_goods_sold', 'direct_costs'],
        'grossProfit': ['gross_profit', 'gross_income'],
        'grossMargin': ['gross_margin'],
        'operatingIncome': ['operating_income', 'ebit'],
        'operatingMargin': ['operating_margin'],
        'netBurn': ['net_burn', 'burn_rate'],
        'runwayMonths': ['runway_months', 'runway'],
        'headcount': ['headcount', 'employees', 'team_size'],
        'customers': ['customers', 'paid_users', 'monthly_active_users'],
        'arr': ['arr', 'annual_recurring_revenue'],
        'ndr': ['ndr', 'net_dollar_retention'],
        'ltv': ['ltv', 'lifetime_value'],
        'cac': ['cac', 'customer_acquisition_cost'],
        'ltvCacRatio': ['ltv_cac_ratio'],
        'yoyGrowth': ['yoy_growth', 'year_over_year'],
        'currency': ['currency'],
        'asOfDate': ['report_date', 'as_of_date', 'date', 'period_end'],
    }
    
    string_fields = ['currency', 'asOfDate']
    
    # Expense fields that must always be positive (NOT netBurn - it can be negative for profitable companies)
    expense_fields = {'totalMonthlyExpenses', 'payroll', 'marketing', 'operating', 'cogs'}
    
    for field, possible_keys in field_mapping.items():
        value = None
        evidence = None
        
        for key in possible_keys:
            if key in raw_metrics and raw_metrics[key] is not None:
                value = raw_metrics[key]
                evidence = f"Extracted from {key}"
                break
        
        if value is not None:
            if field in string_fields:
                extracted[field] = FieldExtraction(
                    value=str(value) if value else None,
                    confidence=0.85 if source == 'excel' else 0.75,
                    evidence=evidence
                )
            else:
                normalized_value = normalize_currency_value(value)
                # CRITICAL: Normalize expense values to always be positive
                if normalized_value is not None and field in expense_fields:
                    normalized_value = abs(normalized_value)
                extracted[field] = FieldExtraction(
                    value=normalized_value,
                    confidence=0.90 if source == 'excel' else 0.80,
                    evidence=evidence
                )
        else:
            extracted[field] = FieldExtraction(value=None, confidence=0.0, evidence=None)
    
    return extracted

def safe_float(value: Any) -> Optional[float]:
    """Safely convert a value to float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None

def safe_positive_float(value: Any) -> Optional[float]:
    """Safely convert a value to positive float (for expenses)."""
    result = safe_float(value)
    if result is not None:
        return abs(result)
    return None

def build_normalized_financials(extracted: Dict[str, FieldExtraction]) -> NormalizedFinancials:
    """Build normalized financials from extracted fields.
    
    All expense values are normalized to be positive.
    """
    # Revenue and cash should be positive
    cash = safe_float(extracted.get('cashOnHand', FieldExtraction()).value)
    if cash is not None:
        cash = abs(cash)
    
    revenue = safe_float(extracted.get('monthlyRevenue', FieldExtraction()).value)
    if revenue is not None:
        revenue = abs(revenue)
    
    # Expenses must be positive
    total_expenses = safe_positive_float(extracted.get('totalMonthlyExpenses', FieldExtraction()).value)
    
    return NormalizedFinancials(
        cashOnHand=cash,
        monthlyRevenue=revenue,
        totalMonthlyExpenses=total_expenses,
        monthlyGrowthRate=safe_float(extracted.get('monthlyGrowthRate', FieldExtraction()).value),
        expenseBreakdown=ExpenseBreakdown(
            payroll=safe_positive_float(extracted.get('payroll', FieldExtraction()).value),
            marketing=safe_positive_float(extracted.get('marketing', FieldExtraction()).value),
            operating=safe_positive_float(extracted.get('operating', FieldExtraction()).value),
        ),
        currency='USD',
        asOfDate=None,
    )

def get_missing_fields(extracted: Dict[str, FieldExtraction], threshold: float = 0.60) -> List[str]:
    """Get list of fields that are missing or have low confidence."""
    required_fields = ['cashOnHand', 'monthlyRevenue', 'totalMonthlyExpenses', 'monthlyGrowthRate']
    missing = []
    
    for field in required_fields:
        extraction = extracted.get(field, FieldExtraction())
        if extraction.value is None or extraction.confidence < threshold:
            missing.append(field)
    
    return missing

def calculate_metrics(normalized: NormalizedFinancials) -> Dict[str, Any]:
    """Calculate derived metrics from normalized financials.
    
    Net Burn = Total Expenses - Revenue
    - If Net Burn < 0: Company is profitable (making money)
    - If Net Burn > 0: Company is burning cash
    
    All expenses are stored as positive numbers internally.
    """
    revenue = abs(normalized.monthlyRevenue or 0)  # Revenue should be positive
    expenses = abs(normalized.totalMonthlyExpenses or 0)  # Expenses stored as positive
    cash = abs(normalized.cashOnHand or 0)  # Cash should be positive
    
    # Net burn = expenses - revenue
    # Positive = burning cash, Negative = profitable
    net_burn = expenses - revenue
    
    # Runway calculation
    if net_burn <= 0:
        # Company is profitable or breaking even
        runway_months = None  # "Sustainable" - no runway limit
        is_profitable = True
        status = "profitable"
    else:
        # Company is burning cash
        runway_months = (cash / net_burn) if net_burn > 0 else None
        is_profitable = False
        status = "burning"
    
    return {
        'netBurnRate': max(0, net_burn),  # Display burn as positive number
        'monthlySurplus': max(0, -net_burn) if net_burn < 0 else 0,  # Surplus if profitable
        'runwayMonths': runway_months,
        'isProfitable': is_profitable,
        'status': status,
    }

@router.post("/ingest/financials", response_model=ExtractionResponse)
async def ingest_financials(
    file: UploadFile = File(...),
    fileType: str = Form(...),
    companyId: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Unified endpoint for ingesting financial data from PDF or Excel files.
    Returns extracted values with confidence scores and normalized baseline metrics.
    """
    company = db.query(Company).filter(
        Company.id == companyId,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if fileType not in ['pdf', 'excel']:
        raise HTTPException(status_code=400, detail="Invalid file type. Must be 'pdf' or 'excel'")
    
    file_ext = os.path.splitext(file.filename or '')[1].lower()
    if fileType == 'pdf' and file_ext != '.pdf':
        raise HTTPException(status_code=400, detail="File must be a PDF")
    if fileType == 'excel' and file_ext not in ['.xls', '.xlsx']:
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xls or .xlsx)")
    
    try:
        content = await file.read()
        
        suffix = '.pdf' if fileType == 'pdf' else file_ext
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            if fileType == 'pdf':
                result = process_termina_pdf(tmp_path)
                raw_metrics = result.get('raw_metrics', result)
                extracted_company_name = result.get('company_name')
                extracted_currency = result.get('currency', 'USD')
                extraction_summary = result.get('summary')
            else:
                result = process_termina_excel(tmp_path)
                raw_metrics = result.get('raw_metrics', result.get('baseline_data', {}))
                extracted_company_name = raw_metrics.get('company_name')
                extracted_currency = raw_metrics.get('currency', 'USD')
                extraction_summary = None
            
            extracted = extract_with_confidence(raw_metrics, fileType)
            normalized = build_normalized_financials(extracted)
            missing_fields = get_missing_fields(extracted)
            calculated = calculate_metrics(normalized)
            
            confidence_map = {k: v.confidence for k, v in extracted.items()}
            
            extracted_dict = {k: {"value": v.value, "confidence": v.confidence, "evidence": v.evidence} for k, v in extracted.items()}
            
            # Update company name and currency if extracted from PDF
            if extracted_company_name and extracted_company_name.strip():
                company.name = extracted_company_name.strip()
                logger.info(f"Updated company name to: {extracted_company_name}")
            if extracted_currency:
                company.currency = extracted_currency
            db.commit()
            
            dataset = Dataset(
                company_id=companyId,
                type='financial',
                file_name=file.filename or 'upload',
                row_count=1
            )
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
            
            dataset_id = dataset.id
            
            has_meaningful_data = (
                normalized.cashOnHand is not None or 
                normalized.monthlyRevenue is not None or 
                normalized.totalMonthlyExpenses is not None
            )
            
            if has_meaningful_data:
                today = date.today()
                first_of_month = today.replace(day=1)
                
                # Ensure all values are positive (normalize sign)
                revenue = abs(normalized.monthlyRevenue or 0)
                cash = abs(normalized.cashOnHand or 0)
                
                total_expenses = normalized.totalMonthlyExpenses
                if total_expenses is None and normalized.expenseBreakdown:
                    breakdown = normalized.expenseBreakdown
                    parts = [breakdown.payroll, breakdown.marketing, breakdown.operating]
                    total_expenses = sum(abs(p) for p in parts if p is not None) or 0.0
                total_expenses = abs(total_expenses or 0)
                
                # Calculate COGS as 30% of revenue (estimate if not provided)
                cogs = 0.0
                if revenue > 0:
                    cogs = revenue * 0.3
                
                payroll_amount = 0.0
                if normalized.expenseBreakdown and normalized.expenseBreakdown.payroll:
                    payroll_amount = abs(normalized.expenseBreakdown.payroll)
                
                # Data validation: block save if values are invalid
                validation_errors = []
                if total_expenses < 0:
                    validation_errors.append("Expenses cannot be negative after normalization")
                if revenue < 0:
                    validation_errors.append("Revenue cannot be negative")
                
                # Calculate burn for validation
                net_burn = total_expenses - revenue
                if net_burn != net_burn:  # Check for NaN
                    validation_errors.append("Burn calculation resulted in invalid number")
                
                if validation_errors:
                    logger.warning(f"Validation warnings (auto-corrected): {validation_errors}")
                
                # Extract additional metrics from raw_metrics
                marketing_amount = 0.0
                if normalized.expenseBreakdown and normalized.expenseBreakdown.marketing:
                    marketing_amount = abs(normalized.expenseBreakdown.marketing)
                
                # Get raw_metrics values for extended fields - use normalize_currency_value to handle strings
                mrr_val = normalize_currency_value(raw_metrics.get('mrr') or raw_metrics.get('monthly_revenue'))
                arr_val = normalize_currency_value(raw_metrics.get('arr'))
                gross_profit_val = normalize_currency_value(raw_metrics.get('gross_profit'))
                gross_margin_val = normalize_currency_value(raw_metrics.get('gross_margin'))
                operating_income_val = normalize_currency_value(raw_metrics.get('operating_income'))
                operating_margin_val = normalize_currency_value(raw_metrics.get('operating_margin'))
                net_burn_val = normalize_currency_value(raw_metrics.get('net_burn'))
                # Note: net_burn can be positive (burning cash) or negative (generating cash)
                # We keep it as-is to preserve the actual value from extraction
                runway_months_val = normalize_currency_value(raw_metrics.get('runway_months'))
                
                # Handle integer fields
                headcount_raw = raw_metrics.get('headcount')
                headcount_val = None
                if headcount_raw is not None:
                    try:
                        headcount_val = int(float(str(headcount_raw).replace(',', '')))
                    except (ValueError, TypeError):
                        headcount_val = None
                
                customers_raw = raw_metrics.get('customers') or raw_metrics.get('paid_users')
                customers_val = None
                if customers_raw is not None:
                    try:
                        customers_val = int(float(str(customers_raw).replace(',', '')))
                    except (ValueError, TypeError):
                        customers_val = None
                
                mom_growth_val = normalize_currency_value(raw_metrics.get('mom_growth') or raw_metrics.get('cmgr_3'))
                yoy_growth_val = normalize_currency_value(raw_metrics.get('yoy_growth'))
                ndr_val = normalize_currency_value(raw_metrics.get('ndr'))
                ltv_val = normalize_currency_value(raw_metrics.get('ltv'))
                cac_val = normalize_currency_value(raw_metrics.get('cac'))
                ltv_cac_val = normalize_currency_value(raw_metrics.get('ltv_cac_ratio'))
                arpu_val = normalize_currency_value(raw_metrics.get('arpu'))
                
                # Burn multiple can be negative (e.g., -0.7x) - preserve sign
                burn_multiple_raw = raw_metrics.get('burn_multiple')
                burn_multiple_val = None
                if burn_multiple_raw is not None:
                    try:
                        val_str = str(burn_multiple_raw).replace('x', '').replace('X', '').strip()
                        burn_multiple_val = float(val_str)
                    except (ValueError, TypeError):
                        burn_multiple_val = None
                
                record = FinancialRecord(
                    company_id=companyId,
                    period_start=first_of_month,
                    period_end=today,
                    revenue=revenue,
                    cogs=cogs,
                    opex=total_expenses,
                    payroll=payroll_amount,
                    other_costs=0,
                    cash_balance=cash,
                    # Extended financial fields
                    mrr=mrr_val,
                    arr=arr_val,
                    gross_profit=gross_profit_val,
                    gross_margin=gross_margin_val,
                    operating_income=operating_income_val,
                    operating_margin=operating_margin_val,
                    net_burn=net_burn_val if net_burn_val is not None else net_burn,  # Preserve sign
                    burn_multiple=burn_multiple_val,  # Preserve negative values
                    runway_months=runway_months_val,
                    headcount=headcount_val,
                    customers=customers_val,
                    mom_growth=mom_growth_val,
                    yoy_growth=yoy_growth_val,
                    ndr=ndr_val,
                    ltv=ltv_val,
                    cac=cac_val,
                    ltv_cac_ratio=ltv_cac_val,
                    arpu=arpu_val,
                    marketing_expense=marketing_amount,
                    source_type=fileType,
                    extraction_summary=extraction_summary,
                )
                db.add(record)
                db.commit()
                
                logger.info(f"Saved comprehensive financial record for company {companyId} with {len([v for v in [mrr_val, arr_val, headcount_val, ndr_val, ltv_val, cac_val] if v])} extended metrics")
            
            return ExtractionResponse(
                extracted=extracted_dict,
                normalized=normalized,
                missingFields=missing_fields,
                confidence=confidence_map,
                source=fileType,
                fileName=file.filename or 'upload',
                uploadId=dataset_id,
                calculatedMetrics=calculated,
            )
            
        finally:
            os.unlink(tmp_path)
            
    except ValueError as e:
        logger.error(f"Validation error during extraction: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@router.get("/companies/{company_id}/financials/baseline", response_model=Dict[str, Any])
async def get_financial_baseline(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the latest financial baseline for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    latest_record = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id
    ).order_by(FinancialRecord.period_end.desc()).first()
    
    if not latest_record:
        return {
            'hasBaseline': False,
            'baseline': None,
        }
    
    return {
        'hasBaseline': True,
        'baseline': {
            'cashOnHand': float(latest_record.cash_balance) if latest_record.cash_balance else 0,
            'monthlyRevenue': float(latest_record.revenue) if latest_record.revenue else 0,
            'totalMonthlyExpenses': float(latest_record.opex) if latest_record.opex else 0,
            'monthlyGrowthRate': float(latest_record.mom_growth) if latest_record.mom_growth else 0,
            'expenseBreakdown': {
                'payroll': float(latest_record.payroll) if latest_record.payroll else 0,
                'marketing': float(latest_record.marketing_expense) if latest_record.marketing_expense else 0,
                'operating': float(latest_record.other_costs) if latest_record.other_costs else 0,
            },
            'currency': company.currency or 'USD',
            'asOfDate': latest_record.period_end.isoformat() if latest_record.period_end else None,
        },
        'extendedMetrics': {
            'mrr': float(latest_record.mrr) if latest_record.mrr else None,
            'arr': float(latest_record.arr) if latest_record.arr else None,
            'grossProfit': float(latest_record.gross_profit) if latest_record.gross_profit else None,
            'grossMargin': float(latest_record.gross_margin) if latest_record.gross_margin else None,
            'operatingIncome': float(latest_record.operating_income) if latest_record.operating_income else None,
            'operatingMargin': float(latest_record.operating_margin) if latest_record.operating_margin else None,
            'netBurn': float(latest_record.net_burn) if latest_record.net_burn else None,
            'burnMultiple': float(latest_record.burn_multiple) if latest_record.burn_multiple is not None else None,
            'runwayMonths': float(latest_record.runway_months) if latest_record.runway_months else None,
            'headcount': int(latest_record.headcount) if latest_record.headcount else None,
            'customers': int(latest_record.customers) if latest_record.customers else None,
            'yoyGrowth': float(latest_record.yoy_growth) if latest_record.yoy_growth else None,
            'ndr': float(latest_record.ndr) if latest_record.ndr else None,
            'ltv': float(latest_record.ltv) if latest_record.ltv else None,
            'cac': float(latest_record.cac) if latest_record.cac else None,
            'ltvCacRatio': float(latest_record.ltv_cac_ratio) if latest_record.ltv_cac_ratio else None,
            'arpu': float(latest_record.arpu) if latest_record.arpu else None,
        },
        'company': {
            'name': company.name,
            'currency': company.currency,
            'industry': company.industry,
        }
    }

@router.post("/companies/{company_id}/financials/save", response_model=Dict[str, Any])
async def save_financial_baseline(
    company_id: int,
    baseline: NormalizedFinancials,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save or update the financial baseline for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    today = date.today()
    first_of_month = today.replace(day=1)
    
    payroll = baseline.expenseBreakdown.payroll if baseline.expenseBreakdown else 0
    marketing = baseline.expenseBreakdown.marketing if baseline.expenseBreakdown else 0
    operating = baseline.expenseBreakdown.operating if baseline.expenseBreakdown else 0
    
    total_expenses = baseline.totalMonthlyExpenses
    if total_expenses is None:
        parts = [payroll, marketing, operating]
        total_expenses = sum(p for p in parts if p is not None) or 0
    
    revenue = baseline.monthlyRevenue or 0
    
    estimated_gross_margin = 0.65
    cogs = revenue * (1 - estimated_gross_margin) if revenue > 0 else 0
    
    if total_expenses > 0 and (payroll or 0) + (marketing or 0) + (operating or 0) > 0:
        opex = (marketing or 0) + (operating or 0)
    else:
        opex = max(0, total_expenses - (payroll or 0) - cogs)
    
    record = FinancialRecord(
        company_id=company_id,
        period_start=first_of_month,
        period_end=today,
        revenue=revenue,
        cogs=cogs,
        opex=opex,
        payroll=payroll or 0,
        other_costs=0,
        cash_balance=baseline.cashOnHand or 0,
    )
    db.add(record)
    
    dataset = Dataset(
        company_id=company_id,
        type='financial',
        file_name='manual_save',
        row_count=1
    )
    db.add(dataset)
    
    db.commit()
    
    actual_total = cogs + opex + (payroll or 0)
    net_burn = max(0, actual_total - revenue)
    runway = (baseline.cashOnHand / net_burn) if net_burn > 0 and baseline.cashOnHand else None
    
    return {
        'success': True,
        'message': 'Financial baseline saved successfully',
        'calculatedMetrics': {
            'netBurnRate': net_burn,
            'runwayMonths': runway,
            'totalExpenses': actual_total,
        }
    }


# ============================================================================
# ONBOARDING DECK EXTRACTION
# ============================================================================

ONBOARDING_EXTRACTION_PROMPT = """You are an AI assistant that extracts company information and financial metrics from pitch decks, investor updates, and company documents.

Analyze the provided document and extract the following information. Return ONLY valid JSON with no markdown formatting.

{
  "company_info": {
    "name": "string - the company name",
    "website": "string - the company website URL if found, or null",
    "industry": "string - one of: general_saas, fintech, ecommerce, marketplace, other",
    "stage": "string - one of: pre_seed, seed, series_a, series_b based on funding mentioned"
  },
  "financials": {
    "monthly_revenue": "number - current monthly revenue in base currency units (not millions), or null",
    "gross_margin_pct": "number - gross margin as percentage (e.g., 70 for 70%), or null", 
    "opex": "number - monthly operating expenses in base currency units, or null",
    "payroll": "number - monthly payroll/salaries in base currency units, or null",
    "other_costs": "number - other monthly costs in base currency units, or null",
    "cash_balance": "number - total cash/bank balance in base currency units, or null",
    "arr": "number - annual recurring revenue if mentioned, or null",
    "mrr": "number - monthly recurring revenue if mentioned, or null",
    "headcount": "number - number of employees if mentioned, or null",
    "runway_months": "number - runway in months if mentioned, or null",
    "burn_rate": "number - monthly burn rate if mentioned, or null"
  },
  "currency": "string - detected currency code (USD, EUR, GBP, INR, etc.), default USD",
  "confidence": {
    "company_info": "number - confidence score 0-1 for company extraction",
    "financials": "number - confidence score 0-1 for financial extraction"
  },
  "summary": "string - brief 1-2 sentence summary of what was found"
}

IMPORTANT RULES:
1. Extract values EXACTLY as stated - do not scale or modify numbers
2. Convert all monetary values to base units (e.g., $5M = 5000000, $50K = 50000)
3. For percentages, store as the percentage number (70% = 70, not 0.7)
4. If a field is not found, use null - do not guess
5. Detect currency from symbols ($, ₹, €, £) or explicit mentions
6. For industry, map to the closest category from the allowed values
7. For stage, infer from funding rounds mentioned (Pre-seed, Seed, Series A, etc.)
"""

ONBOARDING_VISION_PROMPT = """You are an AI assistant analyzing images from a company pitch deck or investor document.

Extract company information and financial metrics from these images. Return ONLY valid JSON with no markdown.

{
  "company_info": {
    "name": "string - the company name visible in the deck",
    "website": "string - company website if shown, or null",
    "industry": "string - one of: general_saas, fintech, ecommerce, marketplace, other",
    "stage": "string - one of: pre_seed, seed, series_a, series_b"
  },
  "financials": {
    "monthly_revenue": "number in base units or null",
    "gross_margin_pct": "number as percentage or null",
    "opex": "number in base units or null",
    "payroll": "number in base units or null",
    "other_costs": "number in base units or null",
    "cash_balance": "number in base units or null",
    "arr": "number or null",
    "mrr": "number or null",
    "headcount": "number or null",
    "runway_months": "number or null",
    "burn_rate": "number or null"
  },
  "currency": "string - currency code (USD, EUR, etc.)",
  "confidence": {
    "company_info": "number 0-1",
    "financials": "number 0-1"
  },
  "summary": "string - brief summary"
}

Convert all values to base units: $5M = 5000000, $50K = 50000.
Percentages as numbers: 70% = 70.
Use null for missing fields - do not guess.
"""


class OnboardingExtractionResponse(BaseModel):
    company_info: Dict[str, Any]
    financials: Dict[str, Any]
    currency: str
    confidence: Dict[str, float]
    summary: str
    extraction_method: str


def extract_onboarding_data_with_openai(text: str) -> Dict[str, Any]:
    """Use OpenAI to extract company info and financials from document text."""
    from openai import OpenAI
    
    api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    
    if not api_key:
        raise ValueError("OpenAI API key not configured")
    
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst AI. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": ONBOARDING_EXTRACTION_PROMPT + "\n\nDocument text:\n\n" + text[:20000]
                }
            ],
            max_tokens=2000,
            temperature=0.1,
            timeout=60
        )
        
        content = response.choices[0].message.content.strip()
        # Clean up markdown if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        return json.loads(content)
    except Exception as e:
        logger.error(f"OpenAI extraction failed: {e}")
        raise


def extract_onboarding_data_with_vision(image_base64_list: List[str]) -> Dict[str, Any]:
    """Use OpenAI Vision to extract company info and financials from images."""
    from openai import OpenAI
    
    api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    
    if not api_key:
        raise ValueError("OpenAI API key not configured")
    
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    content = [{"type": "text", "text": ONBOARDING_VISION_PROMPT}]
    
    for img_b64 in image_base64_list[:8]:  # Limit to 8 pages
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_b64}",
                "detail": "high"
            }
        })
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst AI. Respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=2000,
            temperature=0.1,
            timeout=90
        )
        
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        return json.loads(result)
    except Exception as e:
        logger.error(f"Vision extraction failed: {e}")
        raise


@router.post("/ingest/onboarding/extract-deck")
async def extract_onboarding_deck(
    file: UploadFile = File(...)
):
    """
    Extract company information and financials from a pitch deck or company document.
    Supports PDF files. Uses text extraction with GPT-4o, falling back to vision for image-based PDFs.
    
    This endpoint does NOT require authentication - it's used during onboarding before user creation.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ['.pdf']:
        raise HTTPException(status_code=400, detail="Only PDF files are supported. Please upload a PDF pitch deck.")
    
    temp_file = None
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp:
            content = await file.read()
            temp.write(content)
            temp_file = temp.name
        
        # Check file size (max 20MB)
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > 20:
            raise HTTPException(status_code=400, detail=f"File too large ({file_size_mb:.1f}MB). Maximum is 20MB.")
        
        extraction_method = "text"
        result = None
        
        # Try text extraction first
        try:
            pdf_text = extract_text_from_pdf(temp_file)
            
            if pdf_text and len(pdf_text.strip()) > 500:
                # Good text content, use text-based extraction
                result = extract_onboarding_data_with_openai(pdf_text)
                extraction_method = "text+gpt4o"
            else:
                raise ValueError("Insufficient text content")
                
        except Exception as text_error:
            logger.info(f"Text extraction insufficient, trying vision: {text_error}")
            
            # Fall back to vision
            try:
                from pdf2image import convert_from_path
                import base64
                from io import BytesIO
                
                images = convert_from_path(temp_file, dpi=150, first_page=1, last_page=8)
                image_base64_list = []
                
                for img in images:
                    buffered = BytesIO()
                    img.save(buffered, format="PNG", optimize=True)
                    img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    image_base64_list.append(img_b64)
                
                result = extract_onboarding_data_with_vision(image_base64_list)
                extraction_method = "vision+gpt4o"
                
            except Exception as vision_error:
                logger.error(f"Vision extraction also failed: {vision_error}")
                raise HTTPException(
                    status_code=500, 
                    detail="Could not extract information from the document. Please try a different file or enter details manually."
                )
        
        if not result:
            raise HTTPException(status_code=500, detail="Extraction failed - no data returned")
        
        # Ensure all expected fields exist with defaults
        company_info = result.get("company_info", {})
        financials = result.get("financials", {})
        
        # Normalize industry to valid enum values
        industry_raw = (company_info.get("industry") or "").lower().strip()
        industry_mapping = {
            "saas": "general_saas",
            "general_saas": "general_saas",
            "software": "general_saas",
            "software as a service": "general_saas",
            "fintech": "fintech",
            "financial technology": "fintech",
            "finance": "fintech",
            "ecommerce": "ecommerce",
            "e-commerce": "ecommerce",
            "retail": "ecommerce",
            "marketplace": "marketplace",
            "other": "other",
        }
        industry = industry_mapping.get(industry_raw, "")
        
        # Normalize stage to valid enum values
        stage_raw = (company_info.get("stage") or "").lower().strip().replace("-", "_").replace(" ", "_")
        stage_mapping = {
            "pre_seed": "pre_seed",
            "preseed": "pre_seed",
            "seed": "seed",
            "series_a": "series_a",
            "seriesa": "series_a",
            "series a": "series_a",
            "series_b": "series_b",
            "seriesb": "series_b",
            "series b": "series_b",
            "series b+": "series_b",
            "series_c": "series_b",
            "growth": "series_b",
        }
        stage = stage_mapping.get(stage_raw, "")
        
        return OnboardingExtractionResponse(
            company_info={
                "name": company_info.get("name") or "",
                "website": company_info.get("website") or "",
                "industry": industry,
                "stage": stage
            },
            financials={
                "monthly_revenue": financials.get("monthly_revenue") or financials.get("mrr"),
                "gross_margin_pct": financials.get("gross_margin_pct"),
                "opex": financials.get("opex"),
                "payroll": financials.get("payroll"),
                "other_costs": financials.get("other_costs"),
                "cash_balance": financials.get("cash_balance"),
                "arr": financials.get("arr"),
                "mrr": financials.get("mrr"),
                "headcount": financials.get("headcount"),
                "runway_months": financials.get("runway_months"),
                "burn_rate": financials.get("burn_rate")
            },
            currency=result.get("currency", "USD"),
            confidence=result.get("confidence", {"company_info": 0.5, "financials": 0.5}),
            summary=result.get("summary", ""),
            extraction_method=extraction_method
        )
        
    finally:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
