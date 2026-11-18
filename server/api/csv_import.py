import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import csv
import io

from server.core.company_access import company_access_clause
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.services.input_provenance import stamp_sync_provenance

router = APIRouter(tags=["csv-import"])

MAX_CSV_SIZE = 5 * 1024 * 1024
MAX_CSV_ROWS = 10_000


COLUMN_MAPPINGS = {
    "date": ["date", "period", "month", "period_end", "period_start", "month_year"],
    "revenue": ["revenue", "total_revenue", "income", "sales", "net_sales", "gross_sales",
                "net_revenue", "total_sales", "revenue_from_operations", "turnover"],
    "expenses": ["expenses", "total_expenses", "costs", "total_costs", "opex", "operating_expenses",
                 "operating_costs", "overheads", "rent_ops", "rent_and_ops", "rent"],
    "marketing": ["marketing", "marketing_spend", "ad_spend", "ads", "advertising",
                  "performance_marketing", "marketing_expenses", "ads_spend"],
    "cogs": ["cogs", "cost_of_goods", "cost_of_goods_sold", "cost_of_sales", "direct_costs",
             "product_cost", "landed_cost"],
    "other_costs": ["other_costs", "other_expenses", "misc_costs", "misc", "miscellaneous", "other"],
    "cash_balance": ["cash", "cash_balance", "cash_on_hand", "bank_balance", "ending_cash",
                     "closing_balance", "closing_cash"],
    "payroll": ["payroll", "salaries", "salary", "wages", "personnel", "staff_costs", "employee_costs"],
    "mrr": ["mrr", "monthly_recurring_revenue"],
    "arr": ["arr", "annual_recurring_revenue"],
    "customers": ["customers", "customer_count", "num_customers"],
    "headcount": ["headcount", "employees", "team_size", "head_count"],
    "burn": ["burn", "net_burn", "burn_rate", "monthly_burn"],
    "gross_margin": ["gross_margin", "gm"],
    "cac": ["cac", "customer_acquisition_cost"],
}

# Month formats founders actually use: 2026-05, May 2026, Oct-2026, Oct-26, 05/2026.
DATE_FORMATS = [
    "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y", "%d-%m-%Y",
    "%Y-%m", "%Y/%m", "%m/%Y", "%m-%Y",
    "%b %Y", "%B %Y", "%b-%Y", "%B-%Y", "%b %y", "%b-%y", "%B %y", "%B-%y",
]


def normalize_header(header: str) -> str:
    """'Net Sales (₹)' -> 'net_sales', 'Rent & Ops' -> 'rent_ops'."""
    h = re.sub(r"\(.*?\)", " ", str(header or "").lower())
    h = re.sub(r"[^a-z0-9]+", "_", h)
    return h.strip("_")


def parse_period(raw: str) -> Optional[datetime]:
    value = re.sub(r"\s+", " ", str(raw or "").strip())
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_amount(raw: Any) -> Optional[float]:
    """'₹25,00,000', 'Rs. 1,200', '(5,000)', '12.5%' -> numbers. Blank or '-' -> None."""
    val = str(raw if raw is not None else "").strip()
    if not val:
        return None
    negative = val.startswith("(") and val.endswith(")")
    val = re.sub(r"(?i)\b(?:inr|usd|aed|rs)\b\.?", "", val)
    val = re.sub(r"[₹$€£,%\s()]", "", val)
    if not val or val == "-":
        return None
    number = float(val)
    return -number if negative else number


def detect_columns(headers: List[str]) -> Dict[str, str]:
    mapping = {}
    normalized: Dict[str, str] = {}
    for h in headers:
        normalized.setdefault(normalize_header(h), h)
    
    for field, aliases in COLUMN_MAPPINGS.items():
        for alias in aliases:
            if alias in normalized:
                mapping[field] = normalized[alias]
                break
    return mapping


class ColumnMappingRequest(BaseModel):
    mappings: Dict[str, str]
    rows: List[Dict[str, Any]]


def provided_csv_input_fields(
    *,
    revenue,
    expenses,
    cogs,
    other_costs,
    cash,
    payroll,
    mrr,
    arr,
    customers,
    headcount,
    burn,
    gross_margin,
    cac,
) -> List[str]:
    """Columns copied off the CSV row. Computed burn, margin, and runway are not included."""
    supplied = {
        "revenue": revenue,
        "opex": expenses,
        "cogs": cogs,
        "other_costs": other_costs,
        "cash_balance": cash,
        "payroll": payroll,
        "mrr": mrr,
        "arr": arr,
        "customers": customers,
        "headcount": headcount,
        "cac": cac,
    }
    fields = [name for name, value in supplied.items() if value is not None]
    if burn is not None:
        fields.append("net_burn")
    if gross_margin is not None:
        fields.append("gross_margin")
    return fields


def with_csv_import_provenance(field_values: Dict[str, Any], provided_fields: List[str]) -> Dict[str, Any]:
    """Attach source csv_import and the UTC sync time for fields the row supplied."""
    stamped = dict(field_values)
    stamped.update(stamp_sync_provenance("csv_import", provided_fields))
    return stamped



def is_spreadsheet_filename(name: Optional[str]) -> bool:
    return (name or "").lower().endswith((".xlsx", ".xls"))


def csv_rows(content: bytes):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = []
    for row in reader:
        rows.append(dict(row))
        if len(rows) > MAX_CSV_ROWS:
            break
    return headers, rows


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def spreadsheet_rows(content: bytes, filename: str):
    """First sheet of an Excel file as CSV-style rows.

    A month-per-row P&L (Month, Revenue, Expenses, ...) saved as .xlsx used to
    go to the Termina extractor, which only understands its own export and
    quietly saved nothing. The header row is the first row with at least two
    non-empty text cells, so a title row above the table is skipped.
    """
    try:
        import pandas as pd
        engine = "xlrd" if filename.lower().endswith(".xls") else "openpyxl"
        frame = pd.read_excel(io.BytesIO(content), sheet_name=0, header=None, engine=engine, dtype=object)
    except Exception:
        raise HTTPException(status_code=400, detail="We couldn't open this spreadsheet. Save it as .xlsx or .csv and try again.")
    grid = [[_cell_text(v) if not (isinstance(v, float) and v != v) else "" for v in row] for row in frame.itertuples(index=False)]
    header_idx = next(
        (i for i, row in enumerate(grid[:20]) if sum(1 for c in row if c and not re.fullmatch(r"[-\d.,()₹$%\s]+", c)) >= 2),
        None,
    )
    if header_idx is None:
        return [], []
    raw_headers = grid[header_idx]
    keep = [i for i, h in enumerate(raw_headers) if h]
    headers = [raw_headers[i] for i in keep]
    rows = []
    for row in grid[header_idx + 1:]:
        values = {headers[n]: (row[i] if i < len(row) else "") for n, i in enumerate(keep)}
        if any(values.values()):
            rows.append(values)
        if len(rows) > MAX_CSV_ROWS:
            break
    return headers, rows

@router.post("/companies/{company_id}/financials/csv-detect")
async def detect_csv_columns(
    company_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(
        Company.id == company_id,
        company_access_clause(current_user)
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    content = await file.read()
    if len(content) > MAX_CSV_SIZE:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_CSV_SIZE // (1024*1024)}MB limit")
    if is_spreadsheet_filename(file.filename):
        headers, rows = spreadsheet_rows(content, file.filename or "")
    else:
        headers, rows = csv_rows(content)
    if len(rows) > MAX_CSV_ROWS:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_CSV_ROWS} row limit")

    if not headers or not rows:
        raise HTTPException(
            status_code=400,
            detail="This file has no rows to import. Check it has a header row and at least one month of numbers.",
        )

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
        company_access_clause(current_user)
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
                date_val = parse_period(row[date_col])

            if date_val is None:
                # period_start/period_end are non-nullable — a bad date would
                # otherwise blow up the whole commit, not just this row
                errors.append({"row": i, "error": f"Unrecognized or missing date: {row.get(date_col, '')!r}"})
                continue

            def get_float(field):
                col = mappings.get(field)
                if not col or not row.get(col):
                    return None
                return parse_amount(row[col])

            def get_int(field):
                v = get_float(field)
                return int(v) if v is not None else None

            revenue = get_float("revenue")
            expenses = get_float("expenses")  # stored as opex — the model splits costs
            marketing = get_float("marketing")
            if marketing is not None:
                # No separate column for marketing: it is an operating cost, so it
                # joins opex rather than being dropped from the cost base.
                expenses = (expenses or 0.0) + marketing
            cogs = get_float("cogs")
            other_costs = get_float("other_costs")
            cash = get_float("cash_balance")
            payroll = get_float("payroll")
            mrr_val = get_float("mrr")
            arr_val = get_float("arr")
            customers = get_int("customers")
            headcount = get_int("headcount")
            burn = get_float("burn")
            raw_gm = get_float("gross_margin")
            cac = get_float("cac")

            cost_components = [c for c in (cogs, expenses, payroll, other_costs) if c is not None]
            total_costs = sum(cost_components) if cost_components else None
            net_burn = burn if burn is not None else (
                (total_costs - revenue) if total_costs is not None and revenue is not None else None
            )
            runway = None
            if cash is not None and net_burn is not None and net_burn > 0:
                runway = cash / net_burn
            gm = raw_gm
            if gm is None and revenue and cogs is not None:
                gm = round((revenue - cogs) / revenue * 100, 2)

            provided = provided_csv_input_fields(
                revenue=revenue,
                expenses=expenses,
                cogs=cogs,
                other_costs=other_costs,
                cash=cash,
                payroll=payroll,
                mrr=mrr_val,
                arr=arr_val,
                customers=customers,
                headcount=headcount,
                burn=burn,
                gross_margin=raw_gm,
                cac=cac,
            )
            field_values = with_csv_import_provenance(
                dict(
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
                ),
                provided,
            )
            # Idempotent by period: re-importing a file updates the existing
            # csv_import row for that period instead of duplicating it
            period_key = date_val.date() if isinstance(date_val, datetime) else date_val
            existing = db.query(FinancialRecord).filter(
                FinancialRecord.company_id == company_id,
                FinancialRecord.period_end == period_key,
                FinancialRecord.source_type == "csv_import",
            ).first()
            if existing:
                for k, v in field_values.items():
                    setattr(existing, k, v)
            else:
                db.add(FinancialRecord(
                    company_id=company_id,
                    period_start=date_val,
                    period_end=date_val,
                    **field_values,
                ))
            imported += 1
        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    db.flush()
    if imported:
        from server.services.sample_data import on_real_financials_written
        on_real_financials_written(db, company_id, commit=False)
        db.flush()

    # Recompute month-over-month revenue growth across the company's full
    # history (imports never set mom_growth, which left the baseline growth
    # rate at 0% and skewed every simulation pessimistic).
    all_records = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id,
        FinancialRecord.period_end.isnot(None),
    ).order_by(FinancialRecord.period_end.asc()).all()
    prev_rev = None
    for rec in all_records:
        rev = float(rec.revenue or 0)
        if prev_rev and prev_rev > 0 and rev > 0:
            rec.mom_growth = round((rev / prev_rev - 1) * 100, 2)
        if rev > 0:
            prev_rev = rev

    db.commit()

    # Data confidence and every derived metric come from the *cached* truth
    # scan row, which nothing recomputed after an import. Without this, a
    # founder could upload 12 months of real financials and still see the
    # pre-import "0% confidence / no data" state until they manually re-ran
    # the scan from the Data page.
    truth_scan_id = None
    if imported:
        try:
            from server.truth.truth_scan import compute_truth_scan
            from server.models.truth_scan import TruthScan

            db.refresh(company)
            outputs = compute_truth_scan(company, db)
            scan = TruthScan(company_id=company_id, outputs_json=outputs)
            db.add(scan)
            db.commit()
            db.refresh(scan)
            truth_scan_id = scan.id

            from server.services.activation import maybe_emit_founder_activated
            maybe_emit_founder_activated(
                db,
                user_id=current_user.id,
                company=company,
                source="truth_scan",
                exclude_truth_scan_id=scan.id,
            )

            try:
                from server.utils.websocket_broadcast import broadcast_truth_scan_update_sync
                broadcast_truth_scan_update_sync(
                    company_id=company_id,
                    metrics=outputs.get("metrics", {}),
                    status="completed",
                )
            except Exception:
                pass
        except Exception as e:
            # A failed rescan must not lose an otherwise-successful import.
            db.rollback()
            errors.append({"row": -1, "error": f"Import saved, but confidence rescan failed: {e}"})

    return {
        "imported": imported,
        "errors": errors,
        "total_rows": len(data.rows),
        "truth_scan_id": truth_scan_id,
    }
