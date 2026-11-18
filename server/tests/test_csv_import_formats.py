"""CSV import reads the files Indian D2C founders actually export."""

from datetime import datetime

import pytest

from server.api.csv_import import detect_columns, normalize_header, parse_amount, parse_period


@pytest.mark.parametrize("raw,expected", [
    ("2026-05", (2026, 5)),
    ("2026-05-01", (2026, 5)),
    ("May 2026", (2026, 5)),
    ("Oct-2026", (2026, 10)),
    ("Oct-26", (2026, 10)),
    ("October 2026", (2026, 10)),
    ("05/2026", (2026, 5)),
])
def test_month_formats(raw, expected):
    d = parse_period(raw)
    assert d is not None and (d.year, d.month) == expected


def test_unparseable_date_is_none():
    assert parse_period("last month") is None
    assert parse_period("") is None


@pytest.mark.parametrize("raw,expected", [
    ("₹25,00,000", 2_500_000.0),
    ("Rs. 1,200", 1200.0),
    ("INR 3,40,000", 340_000.0),
    ("(5,000)", -5000.0),
    ("12.5%", 12.5),
    ("$1,000", 1000.0),
])
def test_amounts(raw, expected):
    assert parse_amount(raw) == expected


def test_blank_amounts():
    assert parse_amount("") is None
    assert parse_amount("-") is None
    assert parse_amount(None) is None


def test_headers_with_currency_and_symbols_map():
    headers = ["Month", "Net Sales (₹)", "Cost of Goods", "Ad Spend", "Salaries", "Rent & Ops", "Misc", "Bank Balance"]
    m = detect_columns(headers)
    assert m == {
        "date": "Month",
        "revenue": "Net Sales (₹)",
        "cogs": "Cost of Goods",
        "marketing": "Ad Spend",
        "payroll": "Salaries",
        "expenses": "Rent & Ops",
        "other_costs": "Misc",
        "cash_balance": "Bank Balance",
    }
    assert normalize_header("Net Sales (₹)") == "net_sales"


def test_plain_headers_still_map():
    m = detect_columns(["month", "revenue", "cogs", "marketing", "payroll", "opex", "other_costs", "cash_balance", "headcount"])
    assert m["marketing"] == "marketing" and m["expenses"] == "opex" and m["date"] == "month"


def _xlsx(rows):
    import io
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_month_per_row_excel_reads_like_a_csv():
    from server.api.csv_import import spreadsheet_rows, detect_columns
    content = _xlsx([
        ["Monthly P&L FY26"],
        [],
        ["Month", "Revenue (₹)", "COGS", "Ad spend", "Cash"],
        [datetime(2026, 9, 1), 1200000, 480000, 300000, 9000000],
        ["Oct-2026", "13,50,000", 520000, 310000, 8600000],
    ])
    headers, rows = spreadsheet_rows(content, "pl.xlsx")
    assert headers == ["Month", "Revenue (₹)", "COGS", "Ad spend", "Cash"]
    assert rows[0]["Month"] == "2026-09-01" and rows[0]["Revenue (₹)"] == "1200000"
    assert len(rows) == 2
    mapping = detect_columns(headers)
    assert mapping.get("date") == "Month" and mapping.get("revenue") == "Revenue (₹)"
    assert parse_period(rows[1]["Month"]) is not None
    assert parse_amount(rows[1]["Revenue (₹)"]) == 1_350_000


def test_unreadable_spreadsheet_is_a_clear_400():
    from fastapi import HTTPException
    from server.api.csv_import import spreadsheet_rows
    with pytest.raises(HTTPException) as e:
        spreadsheet_rows(b"not a spreadsheet", "x.xlsx")
    assert e.value.status_code == 400


def test_cash_in_bank_header_maps_to_cash():
    from server.api.csv_import import detect_columns
    assert detect_columns(["Month", "Cash in bank"]).get("cash_balance") == "Cash in bank"
    assert detect_columns(["Month", "Cash at Bank (₹)"]).get("cash_balance") == "Cash at Bank (₹)"
