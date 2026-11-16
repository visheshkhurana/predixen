"""P&L uploads whose label column isn't called "Metric" must still parse."""
import pandas as pd
import pytest

from server.ingest.excel_extractor import (
    _use_label_column_as_index,
    parse_income_statement,
    parse_income_statement_canonical,
)


def _write_pl(path, label_header):
    df = pd.DataFrame({
        label_header: ["Revenue", "Cost of Goods Sold", "Salaries", "Marketing", "Net Income"],
        "Jan 2026": [1_200_000, 400_000, 500_000, 200_000, -10_000],
        "Feb 2026": [1_300_000, 420_000, 510_000, 210_000, 45_000],
    })
    df.to_excel(path, index=False, sheet_name="Income Statement")
    return path


@pytest.mark.parametrize("header", ["Particulars", "Line item", "Account", "Metric"])
def test_any_label_header_is_parsed(tmp_path, header):
    path = _write_pl(tmp_path / "pl.xlsx", header)
    legacy = parse_income_statement(str(path))
    assert legacy["metrics"]["revenue"] == 1_300_000
    canonical = parse_income_statement_canonical(str(path))
    assert canonical["canonical"]["revenue"] == 1_300_000


def test_numeric_first_column_is_left_alone():
    df = pd.DataFrame({"Jan": [1, 2], "Feb": [3, 4]})
    assert list(_use_label_column_as_index(df).index) == [0, 1]


def test_canonical_without_marketing_rows_does_not_crash(tmp_path):
    df = pd.DataFrame({"Particulars": ["Revenue", "Rent"], "Feb 2026": [1000, 200]})
    path = tmp_path / "pl.xlsx"
    df.to_excel(path, index=False, sheet_name="Income Statement")
    out = parse_income_statement_canonical(str(path))
    assert out["canonical"]["revenue"] == 1000
