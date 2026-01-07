from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.dataset import Dataset
from server.models.financial import FinancialRecord
from server.models.transaction import TransactionRecord
from server.models.customer import CustomerRecord
from server.ingest.parsers import parse_csv, detect_column_mapping, parse_financial_records, parse_transaction_records, parse_customer_records
from server.ingest.pdf_extractor import process_termina_pdf
from server.ingest.excel_extractor import process_termina_excel
import tempfile
import os

router = APIRouter(tags=["datasets"])

class ManualBaseline(BaseModel):
    monthly_revenue: float
    gross_margin_pct: float
    opex: float
    payroll: float
    other_costs: float
    cash_balance: float

class DatasetResponse(BaseModel):
    id: int
    type: str
    file_name: str
    row_count: int
    detected_mapping: Optional[Dict[str, str]] = None
    
    class Config:
        from_attributes = True

@router.post("/companies/{company_id}/datasets/upload", response_model=DatasetResponse)
async def upload_dataset(
    company_id: int,
    dataset_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if dataset_type not in ["financial", "transactions", "customers"]:
        raise HTTPException(status_code=400, detail="Invalid dataset type")
    
    content = await file.read()
    content_str = content.decode("utf-8")
    
    df = parse_csv(content_str)
    mapping = detect_column_mapping(df, dataset_type)
    
    dataset = Dataset(
        company_id=company_id,
        type=dataset_type,
        file_name=file.filename or "upload.csv",
        row_count=len(df)
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    if dataset_type == "financial":
        records = parse_financial_records(df, mapping)
        for rec in records:
            if rec["period_start"] and rec["period_end"]:
                fr = FinancialRecord(company_id=company_id, **rec)
                db.add(fr)
    elif dataset_type == "transactions":
        records = parse_transaction_records(df, mapping)
        for rec in records:
            if rec["txn_date"]:
                tr = TransactionRecord(company_id=company_id, **rec)
                db.add(tr)
    elif dataset_type == "customers":
        records = parse_customer_records(df, mapping)
        for rec in records:
            if rec["customer_id"]:
                cr = CustomerRecord(company_id=company_id, **rec)
                db.add(cr)
    
    db.commit()
    
    return DatasetResponse(
        id=dataset.id,
        type=dataset.type,
        file_name=dataset.file_name,
        row_count=dataset.row_count,
        detected_mapping=mapping
    )

@router.post("/companies/{company_id}/datasets/manual_baseline", response_model=Dict[str, Any])
def manual_baseline(
    company_id: int,
    baseline: ManualBaseline,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    from datetime import date
    today = date.today()
    first_of_month = today.replace(day=1)
    
    cogs = baseline.monthly_revenue * (1 - baseline.gross_margin_pct / 100)
    
    record = FinancialRecord(
        company_id=company_id,
        period_start=first_of_month,
        period_end=today,
        revenue=baseline.monthly_revenue,
        cogs=cogs,
        opex=baseline.opex,
        payroll=baseline.payroll,
        other_costs=baseline.other_costs,
        cash_balance=baseline.cash_balance
    )
    db.add(record)
    
    dataset = Dataset(
        company_id=company_id,
        type="financial",
        file_name="manual_baseline",
        row_count=1
    )
    db.add(dataset)
    
    db.commit()
    
    return {"success": True, "message": "Manual baseline saved"}


@router.post("/companies/{company_id}/datasets/termina-pdf", response_model=Dict[str, Any])
async def upload_termina_pdf(
    company_id: int,
    file: UploadFile = File(...),
    save_as_baseline: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a Termina PDF report and extract financial metrics using AI."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    try:
        content = await file.read()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            result = process_termina_pdf(tmp_path)
        finally:
            os.unlink(tmp_path)
        
        baseline = result.get("baseline_data", {})
        monthly_revenue = baseline.get("monthly_revenue")
        
        if save_as_baseline and baseline and monthly_revenue and monthly_revenue > 0:
            from datetime import date
            today = date.today()
            first_of_month = today.replace(day=1)
            
            monthly_revenue = baseline.get("monthly_revenue", 0) or 0
            gross_margin = baseline.get("gross_margin", 70) or 70
            cogs = monthly_revenue * (1 - gross_margin / 100)
            
            record = FinancialRecord(
                company_id=company_id,
                period_start=first_of_month,
                period_end=today,
                revenue=monthly_revenue,
                cogs=cogs,
                opex=baseline.get("operating_expenses", 0) or 0,
                payroll=baseline.get("payroll", 0) or 0,
                other_costs=baseline.get("net_burn", 0) or 0,
                cash_balance=baseline.get("cash_balance", 0) or 0
            )
            db.add(record)
            
            dataset = Dataset(
                company_id=company_id,
                type="financial",
                file_name=f"termina_{file.filename}",
                row_count=1
            )
            db.add(dataset)
            db.commit()
        
        return {
            "success": True,
            "company_name": result.get("company_name"),
            "report_date": result.get("report_date"),
            "currency": result.get("currency"),
            "summary": result.get("summary"),
            "metrics": result.get("raw_metrics"),
            "baseline_saved": save_as_baseline,
            "extracted_fields": len(result.get("baseline_data", {}))
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@router.post("/companies/{company_id}/datasets/termina-excel", response_model=Dict[str, Any])
async def upload_termina_excel(
    company_id: int,
    file: UploadFile = File(...),
    save_as_baseline: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a Termina Excel export and extract financial metrics."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    ext = file.filename.lower().split(".")[-1]
    if ext not in ["xlsx", "xls"]:
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted")
    
    try:
        content = await file.read()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            result = process_termina_excel(tmp_path)
        finally:
            os.unlink(tmp_path)
        
        baseline = result.get("baseline_data", {})
        monthly_revenue = baseline.get("monthly_revenue")
        
        if save_as_baseline and baseline and monthly_revenue and monthly_revenue > 0:
            from datetime import date
            today = date.today()
            first_of_month = today.replace(day=1)
            
            monthly_revenue = baseline.get("monthly_revenue", 0) or 0
            gross_margin = baseline.get("gross_margin", 70) or 70
            cogs = baseline.get("cogs") or (monthly_revenue * (1 - gross_margin / 100))
            
            record = FinancialRecord(
                company_id=company_id,
                period_start=first_of_month,
                period_end=today,
                revenue=monthly_revenue,
                cogs=cogs,
                opex=baseline.get("opex", 0) or 0,
                payroll=baseline.get("payroll", 0) or 0,
                other_costs=baseline.get("net_burn", 0) or 0,
                cash_balance=baseline.get("cash_balance", 0) or 0
            )
            db.add(record)
            
            dataset = Dataset(
                company_id=company_id,
                type="financial",
                file_name=f"termina_{file.filename}",
                row_count=1
            )
            db.add(dataset)
            db.commit()
        
        return {
            "success": True,
            "sheet_name": result.get("sheet_name"),
            "report_date": result.get("report_date"),
            "summary": result.get("summary"),
            "metrics": result.get("raw_metrics"),
            "baseline_saved": save_as_baseline,
            "extracted_fields": len(result.get("baseline_data", {}))
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process Excel file: {str(e)}")
