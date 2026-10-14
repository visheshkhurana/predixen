"""Monte Carlo runway p10/p50/p90, asserted on real output, per QA dataset.

HAG-182 condition (a). Before this file the suite asserted **zero** Monte Carlo
values, which is exactly why HAG-178 (churn_rate declared and never read),
HAG-179 (the [10, 95] clamp applied to the sampled margin instead of the input)
and HAG-180 (the 999 "survived to horizon" sentinel mixed into mean/std/min/max)
all shipped and stayed shipped.

The runner's Monte Carlo is deterministic -- qa-lab/runner/qa_runner.py sets
MC_SEED = 42 and MC_ITERATIONS = 1000 (lines 39-40) -- so golden percentile
values are stable, not flaky. Verified: two consecutive runs of all 15 datasets
produce byte-identical tables.

The dataset mapping below mirrors qa-lab/runner/qa_runner.py exactly on the
baseline path (seed_financial_record applies the scale multiplier to revenue,
opex, payroll, other_costs and cash_balance, but NOT to grossMarginPct). Every
scenario delta is 0 and no churn_rate is passed, so the declared default of 5.0
applies -- which is the whole point of the HAG-178 assertion.
"""

import json
from pathlib import Path

import pytest

from server.simulate.enhanced_monte_carlo import (
    EnhancedSimulationInputs,
    SimulationConfig,
    run_enhanced_monte_carlo,
)

MC_SEED = 42
MC_ITERATIONS = 1000

# Mirrors qa-lab/runner/qa_runner.py:42-48.
SCALE_MULTIPLIERS = {
    "UNITS": 1,
    "THOUSANDS": 1000,
    "MILLIONS": 1000000,
    "CRORES": 10000000,
    "LAKHS": 100000,
}

DATASETS_PATH = Path(__file__).resolve().parents[2] / "qa-lab" / "datasets" / "all-datasets.json"

# Golden p10/p50/p90 per dataset, measured with the three fixes applied. A move
# in any of these is a behaviour change in the simulator and must be deliberate.
GOLDEN_RUNWAY = {
    "DS01": (9.0, 10.0, 10.0),
    "DS02": (19.0, 20.0, 22.0),
    "DS03": (5.0, 5.0, 6.0),
    "DS04": (5.0, 6.0, 6.0),
    "DS05": (26.9, 30.2, 35.4),
    "DS06": (5.0, 5.0, 5.0),
    "DS07": (7.0, 8.0, 9.0),
    "DS08": (3.0, 3.0, 3.0),
    "DS09": (12.0, 13.0, 14.0),
    "DS10": (4.0, 4.0, 5.0),
    "DS11": (6.0, 6.0, 6.0),
    "DS12": (24.2, 26.8, 30.9),
    "DS13": (5.0, 5.0, 5.0),
    "DS14": (21.0, 24.0, 26.0),
    "DS15": (9.0, 9.0, 9.0),
}


def _datasets():
    with DATASETS_PATH.open() as fh:
        return json.load(fh)


def _inputs_from_dataset(ds, **overrides):
    """The runner's baseline construction, scenario deltas all 0."""
    b = ds["baselineInputs"]
    m = SCALE_MULTIPLIERS.get(ds["amountScale"], 1)
    kwargs = dict(
        baseline_revenue=b["monthlyRevenue"] * m,
        baseline_growth_rate=0,
        gross_margin=b["grossMarginPct"],
        opex=b["opex"] * m,
        payroll=b["payroll"] * m,
        other_costs=b["otherCosts"] * m,
        cash_balance=b["cashBalance"] * m,
    )
    kwargs.update(overrides)
    return EnhancedSimulationInputs(**kwargs)


def _run(inputs):
    return run_enhanced_monte_carlo(
        inputs,
        SimulationConfig(iterations=MC_ITERATIONS, horizon_months=24, seed=MC_SEED),
    )


@pytest.mark.parametrize("ds", _datasets(), ids=lambda d: d["id"])
def test_runway_percentiles_match_golden(ds):
    out = _run(_inputs_from_dataset(ds))
    runway = out["runway"]
    assert (
        runway["p10"],
        runway["p50"],
        runway["p90"],
    ) == GOLDEN_RUNWAY[ds["id"]], f"{ds['id']} {ds['companyName']} runway percentiles moved"


@pytest.mark.parametrize("ds", _datasets(), ids=lambda d: d["id"])
def test_runway_percentiles_are_ordered_and_positive(ds):
    runway = _run(_inputs_from_dataset(ds))["runway"]
    assert 0 < runway["p10"] <= runway["p50"] <= runway["p90"]


@pytest.mark.parametrize("ds", _datasets(), ids=lambda d: d["id"])
def test_sentinel_accounting_adds_up(ds):
    """HAG-180: the 999 mass is reported, not hidden inside an average."""
    out = _run(_inputs_from_dataset(ds))
    runway = out["runway"]
    slice_999s = sum(1 for x in out["distributions"]["runway"] if x == 999)

    # The reported count is over all iterations; the distribution is truncated
    # to the first 500, so it can only ever be a lower bound.
    assert runway["sustainableRuns"] >= slice_999s
    assert runway["sustainableRate"] == pytest.approx(
        runway["sustainableRuns"] / MC_ITERATIONS * 100, abs=0.05
    )
    # mean/std_dev/min/max are computed over the runs that ran out of cash, so
    # the 999 code never enters them.
    if runway["sustainableRuns"]:
        assert runway["max"] <= 240, "999 leaked into max"
        assert runway["mean"] < 999, "999 leaked into mean"
    else:
        assert runway["sustainableRuns"] == 0
        assert slice_999s == 0


# --- HAG-178: churn_rate is read, and the delta is additive in percentage points


def test_declared_churn_rate_shortens_runway():
    """The regression that shipped: churn_rate was declared and never read."""
    ds = _datasets()[0]
    with_churn = _run(_inputs_from_dataset(ds, churn_rate=5.0))["runway"]
    without_churn = _run(_inputs_from_dataset(ds, churn_rate=0.0))["runway"]
    assert with_churn["p50"] < without_churn["p50"], (
        "churn_rate had no effect on runway: the declared default is still being ignored"
    )


def test_churn_delta_is_percentage_points_not_relative_percent():
    """churn_change_pct adds to the churn LEVEL (see GuidedScenarioSlider.tsx)."""
    ds = _datasets()[0]
    delta = _run(_inputs_from_dataset(ds, churn_rate=5.0, churn_change_pct=5.0))["runway"]
    level = _run(_inputs_from_dataset(ds, churn_rate=10.0, churn_change_pct=0.0))["runway"]
    assert (delta["p10"], delta["p50"], delta["p90"]) == (
        level["p10"],
        level["p50"],
        level["p90"],
    )


# --- HAG-179: the clamp is on the INPUT margin, not on each sampled margin


def test_margin_above_band_is_clamped_at_the_input():
    """100% gross margin clamps to 95 and behaves exactly as 95 does."""
    ds = [d for d in _datasets() if d["id"] == "DS14"][0]
    at_100 = _run(_inputs_from_dataset(ds, gross_margin=100))["runway"]
    at_95 = _run(_inputs_from_dataset(ds, gross_margin=95))["runway"]
    assert (at_100["p10"], at_100["p50"], at_100["p90"]) == (
        at_95["p10"],
        at_95["p50"],
        at_95["p90"],
    )


def test_margin_below_band_is_clamped_at_the_input():
    """0% gross margin clamps to 10 and behaves exactly as 10 does."""
    ds = [d for d in _datasets() if d["id"] == "DS15"][0]
    at_0 = _run(_inputs_from_dataset(ds, gross_margin=0))["runway"]
    at_10 = _run(_inputs_from_dataset(ds, gross_margin=10))["runway"]
    assert (at_0["p10"], at_0["p50"], at_0["p90"]) == (at_10["p10"], at_10["p50"], at_10["p90"])


def test_in_band_margin_is_untouched_by_the_clamp():
    """A change inside [10, 95] must still move the distribution.

    Asserted on `mean`, not on a percentile. The runway percentiles are
    quantized to whole months on this dataset (DS01 at 50% and 55% gross margin
    both give p50 = 8.0), so a one-point percentile difference would be
    asserting rounding, not sensitivity. `mean` is a continuous statistic of
    the same 1000 seeded runs.
    """
    ds = _datasets()[0]
    at_50 = _run(_inputs_from_dataset(ds, gross_margin=50))["runway"]
    at_55 = _run(_inputs_from_dataset(ds, gross_margin=55))["runway"]
    assert at_50["mean"] != at_55["mean"], "a 5-point margin change inside the band had no effect"
