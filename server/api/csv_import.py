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

MAX_CSV_SIZE = 5 * 1024 * 1024
MAX_CSV_ROWS = 10_000


COLUMN_MAPPINGS = {
    "date": ["date", "period", "month", "period_end", "period_start"],
    "revenue": ["revenue", "total_revenue", "income", "sales"],
    "expenses": ["expenses", "total_expenses", "costs", "total_costs", "opex", "operating_expenses"],
    "cogs": ["cogs", "cost_of_goods", "cost_of_sales", "direct_costs"],
    "other_costs": ["other_costs", "other_expenses", "misc_costs"],
    "cash_balance": ["cash", "cash_balance", "cash_on_hand", "bank_balance", "ending_cash"],
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
    if len(content) > MAX_CSV_SIZE:
        raise HTTPException(status_code=413, detail=f"CSV file exceeds {MAX_CSV_SIZE // (1024*1024)}MB limit")
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = []
    for row in reader:
        if len(rows) >= MAX_CSV_ROWS:
            raise HTTPException(status_code=413, detail=f"CSV exceeds {MAX_CSV_ROWS} row limit")
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

    if len(data.rows) > MAX_CSV_ROWS:
        raise HTTPException(status_code=413, detail=f"Import exceeds {MAX_CSV_ROWS} row limit")

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

            if date_val is None:
                # period_start/period_end are non-nullable — a bad date would
                # otherwise blow up the whole commit, not just this row
                errors.append({"row": i, "error": f"Unrecognized or missing date: {row.get(date_col, '')!r}"})
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
            expenses = get_float("expenses")  # stored as opex — the model splits costs
            cogs = get_float("cogs")
            other_costs = get_float("other_costs")
            cash = get_float("cash_balance")
            payroll = get_float("payroll")
            mrr_val = get_float("mrr")
            arr_val = get_float("arr")
            customers = get_int("customers")
            headcount = get_int("headcount")
            burn = get_float("burn")
            gm = get_float("gross_margin")
            cac = get_float("cac")

            cost_components = [c for c in (cogs, expenses, payroll, other_costs) if c is not None]
            total_costs = sum(cost_components) if cost_components else None
            net_burn = burn if burn is not None else (
                (total_costs - revenue) if total_costs is not None and revenue is not None else None
            )
            runway = None
            if cash is not None and net_burn is not None and net_burn > 0:
                runway = cash / net_burn
            if gm is None and revenue and cogs is not None:
                gm = round((revenue - cogs) / revenue * 100, 2)

            record = FinancialRecord(
                company_id=company_id,
                period_start=date_val,
                period_end=date_val,
                revenue=revenue,
                cogs=cogs,
                opex=expenses,
                other_costs=other_costs,
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
