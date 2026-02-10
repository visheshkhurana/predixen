from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import csv
import io

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.financial import FinancialRecord

router = APIRouter(tags=["csv-import"])


COLUMN_MAPPINGS = {
    "date": ["date", "period", "month", "period_end", "period_start"],
    "revenue": ["revenue", "total_revenue", "income", "sales"],
    "expenses": ["expenses", "total_expenses", "costs", "total_costs", "opex"],
    "cash_balance": ["cash", "cash_balance", "cash_on_hand", "bank_balance"],
    "payroll": ["payroll", "salaries", "wages", "personnel"],
    "mrr": ["mrr", "monthly_recurring_revenue"],
    "arr": ["arr", "annual_recurring_revenue"],
    "customers": ["customers", "customer_count", "num_customers"],
    "headcount": ["headcount", "employees", "team_size", "head_count"],
    "burn": ["burn", "net_burn", "burn_rate", "monthly_burn"],
    "gross_margin": ["gross_margin", "gm"],
    "cac": ["cac", "customer_acquisition_cost"],
}


def detect_columns(headers: List[str]) -> Dict[str, str]:
    mapping = {}
    normalized = {h.lower().strip().replace(" ", "_"): h for h in headers}
    
    for field, aliases in COLUMN_MAPPINGS.items():
        for alias in aliases:
            if alias in normalized:
                mapping[field] = normalized[alias]
                break
    return mapping


class ColumnMappingRequest(BaseModel):
    mappings: Dict[str, str]
    rows: List[Dict[str, Any]]


@router.post("/companies/{company_id}/financials/csv-detect")
async def detect_csv_columns(
    company_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = []
    for row in reader:
        rows.append(dict(row))

    suggested = detect_columns(headers)

    return {
        "headers": headers,
        "suggested_mappings": suggested,
        "preview_rows": rows[:10],
        "all_rows": rows,
        "total_rows": len(rows),
    }


@router.post("/companies/{company_id}/financials/import-csv")
def import_csv_data(
    company_id: int,
    data: ColumnMappingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    mappings = data.mappings
    imported = 0
    errors = []

    for i, row in enumerate(data.rows):
        try:
            date_col = mappings.get("date")
            date_val = None
            if date_col and row.get(date_col):
                raw = str(row[date_col]).strip()
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y", "%b %Y", "%B %Y"]:
                    try:
                        date_val = datetime.strptime(raw, fmt)
                        break
                    except ValueError:
                        continue

            def get_float(field):
                col = mappings.get(field)
                if not col or not row.get(col):
                    return None
                val = str(row[col]).replace(",", "").replace("$", "").replace("%", "").strip()
                if not val or val == "-":
                    return None
                return float(val)

            def get_int(field):
                v = get_float(field)
                return int(v) if v is not None else None

            revenue = get_float("revenue")
            expenses = get_float("expenses")
            cash = get_float("cash_balance")
            payroll = get_float("payroll")
            mrr_val = get_float("mrr")
            arr_val = get_float("arr")
            customers = get_int("customers")
            headcount = get_int("headcount")
            burn = get_float("burn")
            gm = get_float("gross_margin")
            cac = get_float("cac")

            net_burn = burn if burn is not None else (
                (expenses - revenue) if expenses is not None and revenue is not None else None
            )
            runway = None
            if cash is not None and net_burn is not None and net_burn > 0:
                runway = cash / net_burn

            record = FinancialRecord(
                company_id=company_id,
                period_start=date_val,
                period_end=date_val,
                revenue=revenue,
                expenses=expenses,
                cash_balance=cash,
                payroll=payroll,
                mrr=mrr_val,
                arr=arr_val,
                customers=customers,
                headcount=headcount,
                net_burn=net_burn,
                runway_months=runway,
                gross_margin=gm,
                cac=cac,
                source_type="csv_import",
            )
            db.add(record)
            imported += 1
        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    db.commit()

    return {
        "imported": imported,
        "errors": errors,
        "total_rows": len(data.rows),
    }
