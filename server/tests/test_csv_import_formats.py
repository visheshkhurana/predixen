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
