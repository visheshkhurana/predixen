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
scenario delta is 0.

churn_rate=5.0 is passed EXPLICITLY. It used to be the engine default; the
default is now 0 (audit 10-16: a churn nobody entered is an invented input),
and pinning 5.0 here keeps these goldens measuring the same company so the
moves below are attributable to the engine change alone.
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

# Golden p10/p50/p90 per dataset. A move in any of these is a behaviour change
# in the simulator and must be deliberate.
#
# Audit 10-16 moved every row, for two reasons (old values in the comments):
#  - runway is interpolated within the cash-out month instead of rounded UP to
#    the month's end, so in-horizon values drop by up to 1.0 and stop being
#    whole numbers (DS08 3/3/3 -> 2.4/2.7/3.0);
#  - costs now carry cost_sigma noise (a per-path level plus monthly noise),
#    so the cost-dominated datasets get a real spread instead of P10 = P90
#    (DS06, DS11, DS13, DS15) and every RNG stream shifts.
# Rows past the 24-month horizon (DS05, DS12) come from the tail extrapolation
# and moved only by the RNG shift and the cost level (within 0.6 months).
GOLDEN_RUNWAY = {
    "DS01": (8.5, 9.2, 9.9),     # was (9.0, 10.0, 10.0)
    "DS02": (17.9, 20.0, 22.4),  # was (19.0, 20.0, 22.0)
    "DS03": (4.0, 4.7, 5.4),     # was (5.0, 5.0, 6.0)
    "DS04": (4.8, 5.1, 5.4),     # was (5.0, 6.0, 6.0)
    "DS05": (22.3, 24.9, 28.2),  # was (23.0, 24.8, 27.6); 8% margin, not floored (audit 10-15)
    "DS06": (4.1, 4.5, 4.9),     # was (5.0, 5.0, 5.0) -- degenerate
    "DS07": (6.4, 7.6, 9.0),     # was (7.0, 8.0, 9.0)
    "DS08": (2.4, 2.7, 3.0),     # was (3.0, 3.0, 3.0) -- degenerate
    "DS09": (11.7, 12.7, 13.7),  # was (12.0, 13.0, 14.0)
    "DS10": (3.4, 3.9, 4.5),     # was (4.0, 4.0, 5.0)
    "DS11": (5.4, 5.8, 6.1),     # was (6.0, 6.0, 6.0) -- degenerate
    "DS12": (23.8, 26.9, 30.9),  # was (24.2, 26.8, 30.9)
    "DS13": (4.5, 4.7, 4.9),     # was (5.0, 5.0, 5.0) -- degenerate; no revenue, so cost noise is all the spread
    "DS14": (20.5, 23.2, 26.5),  # was (21.0, 24.0, 26.0)
    "DS15": (7.2, 7.5, 7.8),     # was (8.0, 8.0, 8.0) -- degenerate; 0% margin (audit 10-15)
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
        churn_rate=5.0,  # the old implicit default, now explicit (see module docstring)
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
def test_runway_percentiles_are_not_degenerate(ds):
    """Audit 10-16: with default sigmas no dataset collapses to one value."""
    runway = _run(_inputs_from_dataset(ds))["runway"]
    assert runway["p10"] < runway["p90"], runway


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


def test_low_and_negative_margins_are_not_floored():
    """0% and negative margins are real and must be simulated as given.

    The old [10, 95] input clamp ran a 0% (or -56%) margin company at +10%,
    overstating its runway. Lower margin, shorter runway, all the way down.
    """
    ds = [d for d in _datasets() if d["id"] == "DS15"][0]
    means = [
        _run(_inputs_from_dataset(ds, gross_margin=gm))["runway"]["mean"]
        for gm in (10, 0, -56)
    ]
    assert means[0] > means[1] > means[2], means


def test_in_band_margin_is_untouched_by_the_clamp():
    """A change inside [10, 95] must still move the distribution.

    Asserted on `mean`, not on a percentile. The runway percentiles used to be
    quantized to whole months (DS01 at 50% and 55% gross margin both gave
    p50 = 8.0); they are interpolated now, but `mean` is still the more
    sensitive continuous statistic of the same 1000 seeded runs.
    """
    ds = _datasets()[0]
    at_50 = _run(_inputs_from_dataset(ds, gross_margin=50))["runway"]
    at_55 = _run(_inputs_from_dataset(ds, gross_margin=55))["runway"]
    assert at_50["mean"] != at_55["mean"], "a 5-point margin change inside the band had no effect"
