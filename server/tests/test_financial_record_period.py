"""HAG-275. `_build_financial_record` dated every provider's record to the current month.

`server/api/connectors.py:646` built every connector's `FinancialRecord` with

    period_start=today.replace(day=1)
    period_end=today

regardless of the window the connector actually reported. `period_start` is not decoration:
`truth_scan` keys its facts by it --

    period_key = rec.period_start.strftime("%Y-%m")     # server/services/truth_scan.py:308

-- so **the date is what makes the number monthly**. Two figures from different windows land in
the same bucket, and nothing downstream can tell.

The case that forced the card: Tally's ledger movement is over the last *complete* calendar
month, because a month still in progress reports five days of spend as a month's burn and
overstates runway. Dated to the current month instead, that month's number is five days of burn
standing in for a month of Tally's movement.

The fix is the mechanism the card asks for: a connector states its period in its own report
(the dict `map_to_financials` returns, which the docstring already calls "compatible with
FinancialRecord model"), and the builder uses it. A declaration that cannot be honoured is
refused rather than silently dated to `today`.

Run: .venv/bin/python -m pytest server/tests/test_financial_record_period.py \
        -o addopts="" -p no:cacheprovider -q
"""

import datetime as dt
from typing import Any, Dict, Optional

import pytest

from server.api.connectors import _build_financial_record

# A mid-month "today", so `today.replace(day=1)` and the declared window cannot coincide.
TODAY = dt.date(2026, 10, 14)

# Tally's window: the last complete calendar month.
WINDOW_START = dt.date(2026, 9, 1)
WINDOW_END = dt.date(2026, 9, 30)


def build(financials: Dict[str, Any], today: dt.date = TODAY):
    return _build_financial_record(
        company_id=1,
        provider_id="tally",
        provider_name="Tally",
        financials=financials,
        today=today,
    )


def declared(**extra: Any) -> Dict[str, Any]:
    """A connector reporting the last complete calendar month."""
    base: Dict[str, Any] = {
        "revenue": 100000.0,
        "cogs": 20000.0,
        "opex": 15000.0,
        "period_start": WINDOW_START,
        "period_end": WINDOW_END,
    }
    base.update(extra)
    return base


def test_a_declared_window_is_used_and_not_overwritten_by_today():
    """The defect. The connector states a window; `today` used to win anyway."""
    record = build(declared())

    assert record.period_start == WINDOW_START
    assert record.period_end == WINDOW_END


def test_the_declared_month_is_the_bucket_truth_scan_would_file_it_under():
    """The reason the date is load-bearing, asserted directly against truth_scan's own key.

    `truth_scan.py:308` groups by `period_start.strftime("%Y-%m")`. If the record says
    October, the September figures are read as October's.
    """
    record = build(declared())

    assert record.period_start.strftime("%Y-%m") == "2026-09"
    assert record.period_start.strftime("%Y-%m") != TODAY.strftime("%Y-%m")


@pytest.mark.parametrize(
    "start,end",
    [
        (dt.date(2026, 9, 1), dt.date(2026, 9, 30)),          # date
        (dt.datetime(2026, 9, 1, 0, 0), dt.datetime(2026, 9, 30, 23, 59)),  # datetime
        ("2026-09-01", "2026-09-30"),                          # ISO string
        ("2026-09-01T00:00:00", "2026-09-30T23:59:00"),        # ISO datetime string
    ],
)
def test_the_wire_shape_of_the_declaration_does_not_matter(start, end):
    """Connectors hold these as `datetime`, `date` or JSON strings; all four are normal."""
    record = build(declared(period_start=start, period_end=end))

    assert record.period_start == WINDOW_START
    assert record.period_end == WINDOW_END


def test_an_inverted_window_is_refused_not_written():
    """A refusal the card asks for: an impossible period must not become a row.

    The route turns this into a 400 and rolls back (`connectors.py:554`), so the sync fails
    loudly instead of filing a window that cannot describe its own data.
    """
    with pytest.raises(ValueError):
        build(declared(period_start=dt.date(2026, 9, 30), period_end=dt.date(2026, 9, 1)))


def test_an_unreadable_window_is_refused():
    with pytest.raises(ValueError):
        build(declared(period_start="not a date"))


def test_half_a_window_is_refused():
    """Declaring only one end is a connector bug, not a request for a default."""
    with pytest.raises(ValueError):
        build(declared(period_end=None))


def test_without_a_declaration_the_previous_default_is_unchanged():
    """The fallback every existing connector relies on must not move."""
    record = build({"revenue": 100000.0})

    assert record.period_start == dt.date(2026, 10, 1)
    assert record.period_end == TODAY


def test_the_declared_period_does_not_disturb_the_figures():
    """The period is metadata about the numbers, not an input to them."""
    record = build(declared())

    assert record.revenue == 100000.0
    assert record.cogs == 20000.0
    assert record.gross_profit == 80000.0
    assert record.source_type == "connector_tally"
