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

class NormalizedFinancials(BaseModel):
    cashOnHand: Optional[float] = None
    monthlyRevenue: Optional[float] = None
    totalMonthlyExpenses: Optional[float] = None
    monthlyGrowthRate: Optional[float] = None
    expenseBreakdown: ExpenseBreakdown = ExpenseBreakdown()
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
    """Normalize a currency value to float, handling various formats."""
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        cleaned = value.replace('$', '').replace(',', '').replace('(', '-').replace(')', '').strip()
        
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
        'totalMonthlyExpenses': ['total_expenses', 'opex', 'monthly_expenses', 'operating_expenses'],
        'monthlyGrowthRate': ['mom_growth', 'monthly_growth', 'growth_rate', 'revenue_growth'],
        'payroll': ['payroll', 'salaries', 'employee_costs', 'personnel'],
        'marketing': ['marketing', 'marketing_expenses', 'advertising'],
        'operating': ['operating', 'opex', 'operating_expenses', 'general_admin'],
        'currency': ['currency'],
        'asOfDate': ['report_date', 'as_of_date', 'date', 'period_end'],
    }
    
    for field, possible_keys in field_mapping.items():
        value = None
        evidence = None
        
        for key in possible_keys:
            if key in raw_metrics and raw_metrics[key] is not None:
                value = raw_metrics[key]
                evidence = f"Extracted from {key}"
                break
        
        if value is not None:
            if field in ['currency', 'asOfDate']:
                extracted[field] = FieldExtraction(
                    value=str(value) if value else None,
                    confidence=0.85 if source == 'excel' else 0.75,
                    evidence=evidence
                )
            else:
                normalized_value = normalize_currency_value(value)
                extracted[field] = FieldExtraction(
                    value=normalized_value,
                    confidence=0.90 if source == 'excel' else 0.75,
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

def build_normalized_financials(extracted: Dict[str, FieldExtraction]) -> NormalizedFinancials:
    """Build normalized financials from extracted fields."""
    return NormalizedFinancials(
        cashOnHand=safe_float(extracted.get('cashOnHand', FieldExtraction()).value),
        monthlyRevenue=safe_float(extracted.get('monthlyRevenue', FieldExtraction()).value),
        totalMonthlyExpenses=safe_float(extracted.get('totalMonthlyExpenses', FieldExtraction()).value),
        monthlyGrowthRate=safe_float(extracted.get('monthlyGrowthRate', FieldExtraction()).value),
        expenseBreakdown=ExpenseBreakdown(
            payroll=safe_float(extracted.get('payroll', FieldExtraction()).value),
            marketing=safe_float(extracted.get('marketing', FieldExtraction()).value),
            operating=safe_float(extracted.get('operating', FieldExtraction()).value),
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
    """Calculate derived metrics from normalized financials."""
    revenue = normalized.monthlyRevenue or 0
    expenses = normalized.totalMonthlyExpenses or 0
    cash = normalized.cashOnHand or 0
    
    net_burn = max(0, expenses - revenue)
    runway_months = (cash / net_burn) if net_burn > 0 else None
    
    return {
        'netBurnRate': net_burn,
        'runwayMonths': runway_months,
        'isProfitable': revenue >= expenses,
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
            else:
                result = process_termina_excel(tmp_path)
                raw_metrics = result.get('raw_metrics', result.get('baseline_data', {}))
            
            extracted = extract_with_confidence(raw_metrics, fileType)
            normalized = build_normalized_financials(extracted)
            missing_fields = get_missing_fields(extracted)
            calculated = calculate_metrics(normalized)
            
            confidence_map = {k: v.confidence for k, v in extracted.items()}
            
            extracted_dict = {k: {"value": v.value, "confidence": v.confidence, "evidence": v.evidence} for k, v in extracted.items()}
            
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
                
                total_expenses = normalized.totalMonthlyExpenses
                if total_expenses is None and normalized.expenseBreakdown:
                    breakdown = normalized.expenseBreakdown
                    parts = [breakdown.payroll, breakdown.marketing, breakdown.operating]
                    total_expenses = sum(p for p in parts if p is not None) or 0.0
                
                cogs = 0.0
                if normalized.monthlyRevenue:
                    cogs = normalized.monthlyRevenue * 0.3
                
                record = FinancialRecord(
                    company_id=companyId,
                    period_start=first_of_month,
                    period_end=today,
                    revenue=normalized.monthlyRevenue or 0,
                    cogs=cogs,
                    opex=total_expenses or 0,
                    payroll=normalized.expenseBreakdown.payroll or 0 if normalized.expenseBreakdown else 0,
                    other_costs=0,
                    cash_balance=normalized.cashOnHand or 0,
                )
                db.add(record)
                db.commit()
            
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

@router.get("/api/companies/{company_id}/financials/baseline", response_model=Dict[str, Any])
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
            'monthlyGrowthRate': 0,
            'expenseBreakdown': {
                'payroll': float(latest_record.payroll) if latest_record.payroll else 0,
                'marketing': 0,
                'operating': float(latest_record.other_costs) if latest_record.other_costs else 0,
            },
            'currency': 'USD',
            'asOfDate': latest_record.period_end.isoformat() if latest_record.period_end else None,
        }
    }

@router.post("/api/companies/{company_id}/financials/save", response_model=Dict[str, Any])
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
    
    total_expenses = baseline.totalMonthlyExpenses
    if total_expenses is None and baseline.expenseBreakdown:
        breakdown = baseline.expenseBreakdown
        parts = [breakdown.payroll, breakdown.marketing, breakdown.operating]
        total_expenses = sum(p for p in parts if p is not None) or 0
    
    cogs = 0
    if baseline.monthlyRevenue:
        cogs = baseline.monthlyRevenue * 0.3
    
    record = FinancialRecord(
        company_id=company_id,
        period_start=first_of_month,
        period_end=today,
        revenue=baseline.monthlyRevenue or 0,
        cogs=cogs,
        opex=total_expenses or 0,
        payroll=baseline.expenseBreakdown.payroll or 0,
        other_costs=baseline.expenseBreakdown.operating or 0,
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
    
    net_burn = max(0, (total_expenses or 0) - (baseline.monthlyRevenue or 0))
    runway = (baseline.cashOnHand / net_burn) if net_burn > 0 and baseline.cashOnHand else None
    
    return {
        'success': True,
        'message': 'Financial baseline saved successfully',
        'calculatedMetrics': {
            'netBurnRate': net_burn,
            'runwayMonths': runway,
        }
    }
