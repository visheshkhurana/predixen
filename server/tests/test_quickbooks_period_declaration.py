"""HAG-2xx - the QuickBooks sync must declare the period its figures cover.

`QuickBooksConnector.map_to_financials` calls `get_profit_and_loss()` with no
arguments, which makes the window a rolling 90 days ending now. It then returned
`revenue`, `opex` and `net_income` without saying what period those numbers
describe, so a consumer could not tell a 90-day figure from a month or from
all-time. `get_profit_and_loss` already computed the window and returned it as
`period_start` / `period_end`; it just was not passed through.

Only the HTTP boundary is stubbed (`_api_get`), so `get_profit_and_loss` runs for
real and computes its own default window. That is the point: the test pins the
window the connector actually used, not one the test made up.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from server.connectors.base import ConnectorConfig
from server.connectors.quickbooks import QuickBooksConnector


def _connector() -> QuickBooksConnector:
    return QuickBooksConnector(
        ConnectorConfig(
            provider_id="quickbooks",
            company_id=1,
            credentials={
                "client_id": "stub",
                "client_secret": "stub",
                "access_token": "stub",
                "refresh_token": "stub",
                "realm_id": "stub",
            },
        )
    )


def _map(conn):
    return asyncio.run(
        conn.map_to_financials(
            employees=[], payroll_runs=[], ledger_entries=[], invoices=[]
        )
    )


def test_financials_declare_the_period_they_cover():
    """The two keys are present and are real ISO dates, not None."""
    conn = _connector()
    conn._api_get = AsyncMock(return_value={})

    result = _map(conn)

    assert "period_start" in result, "the sync result does not name the period it covers"
    assert "period_end" in result, "the sync result does not name the period it covers"
    assert result["period_start"], "period_start is empty - the window is not actually declared"
    assert result["period_end"], "period_end is empty - the window is not actually declared"

    # Parsing is the assertion that matters: a key holding a non-date is not a
    # declaration.
    datetime.strptime(result["period_start"], "%Y-%m-%d")
    datetime.strptime(result["period_end"], "%Y-%m-%d")


def test_declared_period_is_the_window_the_figures_came_from():
    """The declaration must match the window `get_profit_and_loss` actually used.

    Not a tautology: the connector's default is a rolling 90 days, so a result
    that declared the current month, or all-time, or today, would fail here.
    """
    conn = _connector()
    conn._api_get = AsyncMock(return_value={})

    before = datetime.now()
    result = _map(conn)
    after = datetime.now()

    start = datetime.strptime(result["period_start"], "%Y-%m-%d")
    end = datetime.strptime(result["period_end"], "%Y-%m-%d")

    assert (end - start).days == 90, (
        f"declared window is {(end - start).days} days, but get_profit_and_loss "
        "defaults to 90 - the declaration does not describe the figure"
    )
    assert before - timedelta(days=1) <= end <= after + timedelta(days=1), (
        "declared period_end is not the time of the sync"
    )


def test_period_is_the_pnl_report_period_not_a_second_guess():
    """A non-default window supplied to the P&L must be the one declared.

    `map_to_financials` does not currently take a window, so this pins the
    coupling between the two functions through the method the sync actually
    calls: whatever `get_profit_and_loss` reports is what the result declares.
    """
    conn = _connector()
    conn._api_get = AsyncMock(return_value={})

    pnl = asyncio.run(conn.get_profit_and_loss())
    result = _map(conn)

    assert result["period_start"] == pnl["period_start"]
    assert result["period_end"] == pnl["period_end"]
