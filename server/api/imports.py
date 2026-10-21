"""
Import session API endpoints.
Handles file upload, parsing, verification, and saving of financial data.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import date, datetime
import tempfile
import os
import logging

from server.core.db import get_db
from server.core.security import get_current_user
from server.models import (
    User, Company, ImportSession, FinancialMetricPoint, FinancialRecord
)
from server.ingest.excel_extractor import process_termina_excel
from server.ingest.pdf_extractor import process_termina_pdf
from server.ingest.classifier import classify_all_rows, SignConvention
from server.ingest.calculations import (
    compute_baseline_metrics, calculate_total_revenue, calculate_total_expenses,
    aggregate_expense_breakdown, format_burn_display, format_runway_display,
    calculate_net_burn
)
from server.ingest.benchmarks import get_benchmarks, inject_benchmark_defaults

router = APIRouter(prefix="/imports", tags=["imports"])
logger = logging.getLogger(__name__)


class ImportSessionResponse(BaseModel):
    id: int
    company_id: int
    source_type: str
    filename: Optional[str]
    status: str
    detected_sign_convention: str
    detected_time_granularity: str
    selected_period_mode: str
    selected_period: Optional[date]
    warnings: List[str]
    errors: List[str]
    periods: List[str]
    rows: List[Dict[str, Any]]
    summary: Dict[str, Any]


class VerifyRequest(BaseModel):
    selected_period_mode: str = "latest"
    selected_period: Optional[str] = None
    row_overrides: Optional[Dict[int, Dict[str, Any]]] = None
    cash_on_hand: Optional[float] = None
    revenue_override: Optional[float] = None
    expense_override: Optional[float] = None
    benchmark_opt_in: bool = False


class VerifyResponse(BaseModel):
    baseline: Dict[str, Any]
    expense_breakdown: Dict[str, float]
    burn_display: Dict[str, Any]
    runway_display: str
    warnings: List[str]
    errors: List[str]
    benchmark_injected: List[Dict[str, Any]]


class SaveRequest(BaseModel):
    selected_period: str
    cash_on_hand: Optional[float] = None
    revenue_override: Optional[float] = None
    expense_override: Optional[float] = None
    row_overrides: Optional[Dict[str, Dict[str, Any]]] = None


class SavedBaselineData(BaseModel):
    cashOnHand: Optional[float] = None  # None = cash not provided (never estimated)
    monthlyRevenue: float
    totalMonthlyExpenses: float
    monthlyGrowthRate: Optional[float] = None
    expenseBreakdown: Dict[str, Optional[float]] = {}
    currency: str = "USD"
    asOfDate: Optional[str] = None


class SaveResponse(BaseModel):
    success: bool
    financial_record_id: int
    message: str
    baseline: Optional[SavedBaselineData] = None


def extract_periods_from_rows(rows: List[Dict[str, Any]]) -> List[str]:
    """Extract all unique period keys from classified rows."""
    periods = set()
    for row in rows:
        values = row.get('values', {})
        periods.update(values.keys())
    return sorted(list(periods), reverse=True)


def parse_excel_to_rows(
    file_path: str,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Parse Excel file and convert to row format for classification."""
    result = process_termina_excel(file_path, company_id=company_id, user_id=user_id)
    
    raw_metrics = result.get('raw_metrics', result.get('baseline_data', {}))
    time_series = result.get('time_series', {})
    
    rows = []
    
    # If we have time series data, use that
    if time_series:
        for label, values in time_series.items():
            if isinstance(values, dict):
                rows.append({
                    'label': label,
                    'values': values
                })
    
    # Otherwise, create individual rows for each metric (like PDF extraction)
    if not rows and raw_metrics:
        for key, value in raw_metrics.items():
            if isinstance(value, (int, float)):
                # Convert snake_case to Title Case for labels
                label = key.replace('_', ' ').title()
                rows.append({
                    'label': label,
                    'values': {'latest': value}
                })
    
    return rows


def parse_pdf_to_rows(
    file_path: str,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Parse PDF file and convert to row format for classification."""
    result = process_termina_pdf(file_path, company_id=company_id, user_id=user_id)
    
    raw_metrics = result.get('raw_metrics', result)
    
    rows = []
    
    for key, value in raw_metrics.items():
        if isinstance(value, (int, float)):
            label = key.replace('_', ' ').title()
            rows.append({
                'label': label,
                'values': {'latest': value}
            })
    
    return rows


@router.post("/excel", response_model=ImportSessionResponse)
async def upload_excel(
    company_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and parse an Excel file, returning an import session for verification."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    file_ext = os.path.splitext(file.filename or '')[1].lower()
    if file_ext not in ['.xls', '.xlsx']:
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xls or .xlsx)")
    
    try:
        content = await file.read()
        max_upload_size = 50 * 1024 * 1024
        if len(content) > max_upload_size:
            raise HTTPException(status_code=413, detail="File too large. Maximum upload size is 50MB.")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            rows = parse_excel_to_rows(tmp_path, company_id=company_id, user_id=current_user.id)
            
            classification_result = classify_all_rows(rows)
            
            session = ImportSession(
                company_id=company_id,
                source_type="excel",
                filename=file.filename,
                detected_sign_convention=classification_result['sign_convention'],
                detected_time_granularity="monthly",
                status="parsed",
                warnings=classification_result.get('warnings', []),
                errors=[],
                raw_data={
                    'rows': classification_result['rows'],
                    'summary': classification_result['summary']
                }
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            
            periods = extract_periods_from_rows(classification_result['rows'])
            
            return ImportSessionResponse(
                id=int(session.id),
                company_id=int(session.company_id),
                source_type=str(session.source_type),
                filename=session.filename if session.filename else None,
                status=str(session.status),
                detected_sign_convention=str(session.detected_sign_convention),
                detected_time_granularity=str(session.detected_time_granularity),
                selected_period_mode=str(session.selected_period_mode),
                selected_period=session.selected_period if session.selected_period else None,
                warnings=list(session.warnings) if session.warnings else [],
                errors=list(session.errors) if session.errors else [],
                periods=periods,
                rows=classification_result['rows'],
                summary=classification_result['summary']
            )
            
        finally:
            os.unlink(tmp_path)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Excel file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@router.post("/pdf", response_model=ImportSessionResponse)
async def upload_pdf(
    company_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and parse a PDF file, returning an import session for verification."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    file_ext = os.path.splitext(file.filename or '')[1].lower()
    if file_ext != '.pdf':
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        content = await file.read()
        max_upload_size = 50 * 1024 * 1024
        if len(content) > max_upload_size:
            raise HTTPException(status_code=413, detail="File too large. Maximum upload size is 50MB.")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            rows = parse_pdf_to_rows(tmp_path, company_id=company_id, user_id=current_user.id)
            
            classification_result = classify_all_rows(rows)
            
            session = ImportSession(
                company_id=company_id,
                source_type="pdf",
                filename=file.filename,
                detected_sign_convention=classification_result['sign_convention'],
                detected_time_granularity="monthly",
                status="parsed",
                warnings=classification_result.get('warnings', []),
                errors=[],
                raw_data={
                    'rows': classification_result['rows'],
                    'summary': classification_result['summary']
                }
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            
            periods = extract_periods_from_rows(classification_result['rows'])
            
            return ImportSessionResponse(
                id=int(session.id),
                company_id=int(session.company_id),
                source_type=str(session.source_type),
                filename=session.filename if session.filename else None,
                status=str(session.status),
                detected_sign_convention=str(session.detected_sign_convention),
                detected_time_granularity=str(session.detected_time_granularity),
                selected_period_mode=str(session.selected_period_mode),
                selected_period=session.selected_period if session.selected_period else None,
                warnings=list(session.warnings) if session.warnings else [],
                errors=list(session.errors) if session.errors else [],
                periods=periods,
                rows=classification_result['rows'],
                summary=classification_result['summary']
            )
            
        finally:
            os.unlink(tmp_path)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@router.get("/{session_id}", response_model=ImportSessionResponse)
async def get_import_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get an existing import session."""
    session = db.query(ImportSession).join(Company).filter(
        ImportSession.id == session_id,
        Company.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Import session not found")
    
    raw_data = session.raw_data or {}
    rows = raw_data.get('rows', [])
    periods = extract_periods_from_rows(rows)
    
    return ImportSessionResponse(
        id=int(session.id),
        company_id=int(session.company_id),
        source_type=str(session.source_type),
        filename=session.filename if session.filename else None,
        status=str(session.status),
        detected_sign_convention=str(session.detected_sign_convention),
        detected_time_granularity=str(session.detected_time_granularity),
        selected_period_mode=str(session.selected_period_mode),
        selected_period=session.selected_period if session.selected_period else None,
        warnings=list(session.warnings) if session.warnings else [],
        errors=list(session.errors) if session.errors else [],
        periods=periods,
        rows=rows,
        summary=raw_data.get('summary', {})
    )


@router.post("/{session_id}/verify", response_model=VerifyResponse)
async def verify_import(
    session_id: int,
    request: VerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify and preview computed metrics before saving."""
    session = db.query(ImportSession).join(Company).filter(
        ImportSession.id == session_id,
        Company.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Import session not found")
    
    company = session.company
    raw_data = session.raw_data or {}
    rows = raw_data.get('rows', [])
    
    if request.row_overrides:
        for idx_str, overrides in request.row_overrides.items():
            idx = int(idx_str)
            for row in rows:
                if row.get('index') == idx:
                    row.update(overrides)
    
    periods = extract_periods_from_rows(rows)
    
    if request.selected_period:
        selected_period = request.selected_period
    elif periods:
        selected_period = periods[0]
    else:
        selected_period = "latest"
    
    if request.revenue_override is not None:
        total_revenue = request.revenue_override
    else:
        total_revenue = calculate_total_revenue(rows, selected_period)
    
    if request.expense_override is not None:
        total_expenses = request.expense_override
    else:
        total_expenses = calculate_total_expenses(rows, selected_period)
    
    expense_breakdown = aggregate_expense_breakdown(rows, selected_period)
    
    cash_on_hand = request.cash_on_hand
    
    baseline = compute_baseline_metrics(
        revenue=total_revenue,
        total_expenses=total_expenses,
        cash_on_hand=cash_on_hand,
        expense_breakdown=expense_breakdown
    )
    
    benchmark_injected = []
    if request.benchmark_opt_in:
        industry = company.industry or "saas"
        stage = company.stage or "seed"
        
        metrics = {'growth_rate_mom': baseline.growth_rate_mom}
        injected = inject_benchmark_defaults(metrics, industry, stage)
        benchmark_injected = injected.get('_benchmark_injected', [])
    
    burn_display = format_burn_display(baseline.net_burn)
    runway_display = format_runway_display(baseline.runway_months, baseline.burn_status)
    
    warnings = baseline.warnings or []
    errors = []
    
    if total_revenue == 0:
        errors.append("No revenue selected or found")
    if total_expenses == 0:
        errors.append("No expenses included")
    
    return VerifyResponse(
        baseline={
            'revenue': baseline.revenue,
            'total_expenses': baseline.total_expenses,
            'net_burn': baseline.net_burn,
            'burn_status': baseline.burn_status.value,
            'runway_months': baseline.runway_months,
            'cash_on_hand': baseline.cash_on_hand,
            'growth_rate_mom': baseline.growth_rate_mom,
        },
        expense_breakdown=expense_breakdown,
        burn_display=burn_display,
        runway_display=runway_display,
        warnings=warnings,
        errors=errors,
        benchmark_injected=benchmark_injected
    )


@router.post("/{session_id}/save", response_model=SaveResponse)
async def save_import(
    session_id: int,
    request: SaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save verified import data to FinancialRecord."""
    session = db.query(ImportSession).join(Company).filter(
        ImportSession.id == session_id,
        Company.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Import session not found")
    
    raw_data = session.raw_data or {}
    rows = raw_data.get('rows', [])
    
    if request.row_overrides:
        for idx_str, overrides in request.row_overrides.items():
            idx = int(idx_str)
            for row in rows:
                if row.get('index') == idx:
                    row.update(overrides)
    
    selected_period = request.selected_period
    
    canonical = raw_data.get('canonical', {})
    use_canonical = canonical.get('revenue') is not None and canonical.get('expenses') is not None
    
    if request.revenue_override is not None:
        total_revenue = request.revenue_override
    elif use_canonical:
        total_revenue = canonical.get('revenue', 0)
        logger.info(f"[SAVE] Using canonical revenue: ${total_revenue:,.0f}")
    else:
        total_revenue = calculate_total_revenue(rows, selected_period)
    
    if request.expense_override is not None:
        total_expenses = request.expense_override
    elif use_canonical:
        total_expenses = canonical.get('total_expenses', 0)
        logger.info(f"[SAVE] Using canonical total_expenses: ${total_expenses:,.0f}")
    else:
        total_expenses = calculate_total_expenses(rows, selected_period)
    
    if use_canonical:
        canonical_expenses = canonical.get('expenses', {})
        expense_breakdown = {
            'cogs': canonical_expenses.get('cogs') or 0,
            'marketing': canonical_expenses.get('marketing') or 0,
            'payroll': canonical_expenses.get('payroll') or 0,
            'operating': canonical_expenses.get('operating') or 0,
            'other': canonical_expenses.get('other') or 0,
        }
        logger.info(f"[SAVE] Using canonical expense breakdown: COGS=${expense_breakdown['cogs']:,.0f}, Marketing=${expense_breakdown['marketing']:,.0f}")
    else:
        expense_breakdown = aggregate_expense_breakdown(rows, selected_period)
    
    # Cash is never invented. A blank cash field used to become burn x 12 (or
    # $2M when profitable), which fabricated a 12-month runway. Store null and
    # let readers report runway as unknown / "cash not provided".
    cash_on_hand = request.cash_on_hand
    
    try:
        period_date = datetime.strptime(selected_period, "%Y-%m-%d").date()
    except ValueError:
        period_date = date.today().replace(day=1)
    
    period_end = period_date.replace(day=28)
    
    cogs_amt_abs = abs(expense_breakdown.get('cogs', 0) or 0)
    opex_amt_abs = abs(expense_breakdown.get('operating', 0) or 0)
    payroll_amt_abs = abs(expense_breakdown.get('payroll', 0) or 0)
    marketing_amt_abs = abs(expense_breakdown.get('marketing', 0) or 0)
    other_amt_abs = abs(expense_breakdown.get('other', 0) or 0)
    
    # other_costs holds "other" only: marketing has its own column and every
    # reader adds marketing_expense + other_costs, so folding marketing into
    # other_costs counted it twice. Any part of the total (expense override,
    # canonical total, or row total) that the buckets do not explain goes into
    # other_costs so readers that sum the breakdown honour the total.
    known_buckets = cogs_amt_abs + opex_amt_abs + payroll_amt_abs + marketing_amt_abs
    other_costs_amt = max(other_amt_abs, abs(total_expenses) - known_buckets)
    stored_total = known_buckets + other_costs_amt
    if request.expense_override is not None and stored_total > abs(total_expenses) + 0.5:
        # The user typed a total below what the buckets add up to. Their total
        # wins: scale the buckets so the stored breakdown sums to it (readers
        # derive burn from the breakdown, so a stored scalar alone is ignored).
        scale = abs(total_expenses) / stored_total if stored_total else 0.0
        logger.info(
            f"[SAVE] expense_override ${abs(total_expenses):,.0f} below bucket sum "
            f"${stored_total:,.0f}; scaling buckets by {scale:.4f}"
        )
        cogs_amt_abs *= scale
        opex_amt_abs *= scale
        payroll_amt_abs *= scale
        marketing_amt_abs *= scale
        other_costs_amt *= scale
    signed_net_burn = abs(total_expenses) - abs(total_revenue)
    
    record = FinancialRecord(
        company_id=session.company_id,
        period_start=period_date,
        period_end=period_end,
        revenue=abs(total_revenue),
        cogs=cogs_amt_abs,
        opex=opex_amt_abs,
        payroll=payroll_amt_abs,
        other_costs=other_costs_amt,
        cash_balance=abs(cash_on_hand) if cash_on_hand is not None else None,
        import_session_id=session.id,
        marketing_expense=marketing_amt_abs,
        net_burn=signed_net_burn,
    )
    
    db.add(record)

    from server.services.sample_data import on_real_financials_written
    on_real_financials_written(db, session.company_id, commit=False)
    
    db.execute(
        ImportSession.__table__.update()
        .where(ImportSession.id == session_id)
        .values(status="saved", selected_period=period_date)
    )
    
    db.commit()
    db.refresh(record)
    
    company = db.query(Company).filter(Company.id == session.company_id).first()
    currency = str(company.currency) if company and company.currency else "USD"
    
    
    growth_rate = None
    
    # Echo exactly what was stored so the client baseline matches the record.
    payroll_amt = payroll_amt_abs
    marketing_amt = marketing_amt_abs
    operating_amt = opex_amt_abs
    cogs_amt = cogs_amt_abs
    other_opex = other_costs_amt
    
    baseline_data = SavedBaselineData(
        cashOnHand=abs(cash_on_hand) if cash_on_hand is not None else None,
        monthlyRevenue=abs(total_revenue),
        totalMonthlyExpenses=abs(total_expenses),
        monthlyGrowthRate=growth_rate,
        expenseBreakdown={
            "payroll": payroll_amt if payroll_amt > 0 else None,
            "marketing": marketing_amt if marketing_amt > 0 else None,
            "operating": operating_amt if operating_amt > 0 else None,
            "cogs": cogs_amt if cogs_amt > 0 else None,
            "otherOpex": other_opex if other_opex > 0 else None,
        },
        currency=currency,
        asOfDate=selected_period
    )
    
    return SaveResponse(
        success=True,
        financial_record_id=int(record.id),
        message=f"Financial data saved successfully for period {selected_period}",
        baseline=baseline_data
    )


@router.delete("/{session_id}")
async def delete_import_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an import session."""
    session = db.query(ImportSession).join(Company).filter(
        ImportSession.id == session_id,
        Company.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Import session not found")
    
    db.delete(session)
    db.commit()
    
    return {"success": True, "message": "Import session deleted"}
