"""The run payload the /scenarios Runway Distribution chart draws from.

HAG-246. Until this was fixed, the chart at `client/src/pages/scenarios.tsx`
drew its bars from `Array.from({ length: 1000 }, () => p50 + (Math.random() -
0.5) * (p90 - p10))` -- 1,000 fabricated values, re-randomised on every render,
under the label "Distribution across all Monte Carlo runs". Two things were
wrong with that, and only one of them was the randomness.

The engine does return the real per-path runway values, so the chart can draw
the truth instead of a rectangle. This file pins the three facts that fix
depends on, against real engine output rather than against the source text:

1. `distributions.runway` is on the run payload the client actually fetches
   (`GET /scenarios/{id}/simulation/latest` returns `**outputs`, and
   `simulation_engine.py` is a different engine this page does not call).
2. It is a **sample, not the whole ensemble** -- capped at 500 paths however
   many the run made -- so no label may say "all runs". `config.iterations`
   carries the true count and is what the copy binds to (HAG-245).
3. Runs that never ran out of cash within the horizon carry the 999 sentinel
   (HAG-180), not a large month count. That mass is the thing the old chart
   hid and the reason the finding was graded HIGH, so it is asserted here:
   the sentinel value is exactly 999, and the count of them in the returned
   sample matches the engine's own `runway.sustainableRuns` proportion.

The worst case of the old code is pinned too. Its spread term was
`(p90 - p10 || 6)`, and `p90 - p10` is 0 for a zero-variance run, which is
falsy in JavaScript -- so `|| 6` fired and the chart drew a 6-month-wide bell
around a value the engine computes with no spread at all. DS13 and DS15 are
both zero-variance, and `test_a_zero_variance_run_really_is_a_single_point`
holds them there.
"""

import json
from pathlib import Path

import pytest

from server.simulate.enhanced_monte_carlo import (
    EnhancedSimulationInputs,
    SimulationConfig,
    run_enhanced_monte_carlo,
)

SENTINEL_SURVIVED = 999
DISTRIBUTION_CAP = 500

DATASETS_PATH = (
    Path(__file__).resolve().parents[2] / "qa-lab" / "datasets" / "all-datasets.json"
)
SCALE_MULTIPLIERS = {
    "UNITS": 1,
    "THOUSANDS": 1000,
    "MILLIONS": 1000000,
    "CRORES": 10000000,
    "LAKHS": 100000,
}


def _inputs_from_dataset(ds):
    b = ds["baselineInputs"]
    m = SCALE_MULTIPLIERS.get(ds["amountScale"], 1)
    return EnhancedSimulationInputs(
        baseline_revenue=b["monthlyRevenue"] * m,
        baseline_growth_rate=0,
        gross_margin=b["grossMarginPct"],
        opex=b["opex"] * m,
        payroll=b["payroll"] * m,
        other_costs=b["otherCosts"] * m,
        cash_balance=b["cashBalance"] * m,
    )


def _run(inputs, iterations):
    return run_enhanced_monte_carlo(
        inputs, SimulationConfig(iterations=iterations, horizon_months=24, seed=42)
    )


def _datasets():
    with DATASETS_PATH.open() as fh:
        return json.load(fh)


@pytest.mark.parametrize("ds", _datasets(), ids=lambda d: d["id"])
def test_run_payload_carries_a_real_runway_sample(ds):
    """The chart's data source is on the payload, and it is the engine's own run.

    Not "there is an array here" -- the sample has to agree with the summary
    statistics computed from the full ensemble, or the chart would be drawing
    something other than the run it is labelled with.
    """
    out = _run(_inputs_from_dataset(ds), 1000)
    sample = out["distributions"]["runway"]
    summary = out["runway"]

    assert isinstance(sample, list)
    assert len(sample) == DISTRIBUTION_CAP
    assert all(isinstance(v, (int, float)) for v in sample)
    assert out["config"]["iterations"] == 1000

    # Every sampled path lies inside the ensemble's own min..max. The summary
    # is rounded to 1dp (`round(..., 1)` at enhanced_monte_carlo.py:379-380)
    # while the sample is raw, so the bound carries half an ulp of slack --
    # DS14's sample max is 36.2488 against a reported max of 36.2.
    assert min(sample) >= summary["min"] - 0.05
    assert max(sample) <= summary["max"] + 0.05
    # And its median tracks the reported median. A 500-path prefix sample of
    # independent paths is close, not identical -- hence a tolerance rather
    # than equality, so this does not become a flaky test.
    assert abs(sorted(sample)[len(sample) // 2] - summary["p50"]) <= 2.0 + 0.05 * abs(summary["p50"])


@pytest.mark.parametrize("iterations", [100, 500, 1000, 5000])
def test_the_sample_is_capped_and_the_true_count_is_separate(iterations):
    """A 5,000-path run returns 500 values. No label may say "all runs".

    This is the truncation the chart inherits. It is a prefix sample of
    independent paths, so it is unbiased -- but it is not the ensemble, and
    `config.iterations` is the only field that says how many runs were made.
    """
    ds = _datasets()[0]
    out = _run(_inputs_from_dataset(ds), iterations)
    sample = out["distributions"]["runway"]

    assert len(sample) == min(iterations, DISTRIBUTION_CAP)
    assert out["config"]["iterations"] == iterations

    # Two different flavours of "how many": the sample the chart plots and the
    # ensemble the run made. They are not interchangeable on screen.
    assert len(sample) != out["config"]["iterations"] or iterations <= DISTRIBUTION_CAP


@pytest.mark.parametrize("ds_id", ["DS13", "DS15"])
def test_a_zero_variance_run_really_is_a_single_point(ds_id):
    """The regression this file exists for: no invented spread.

    DS13 has no revenue and DS15 has a zero gross margin, so the engine
    reports `stdDev = 0.0` and every one of the 500 sampled paths is the same
    number. The old chart expression was

        p50 + (Math.random() - 0.5) * (p90 - p10 || 6)

    and `p90 - p10` is 0 here, which is falsy in JavaScript, so `|| 6` fired:
    the chart drew a 6-month-wide bell around a value the engine computes with
    zero variance. Months 2-8 for DS13 and 6-12 for DS15, none of it real.

    That fallback is the reason this is asserted rather than assumed. If
    someone re-adds a spread floor to make the chart "look better", this fails.
    """
    ds = next(d for d in _datasets() if d["id"] == ds_id)
    out = _run(_inputs_from_dataset(ds), 1000)
    sample = out["distributions"]["runway"]
    summary = out["runway"]

    assert summary["stdDev"] == 0
    assert summary["p10"] == summary["p90"]
    assert len(set(sample)) == 1, f"{ds_id} should be a single point, got {len(set(sample))}"
    # The width the old code would have substituted, for the record.
    assert summary["p90"] - summary["p10"] == 0


def test_the_survived_to_horizon_mass_is_the_999_sentinel_and_is_counted():
    """A cash-flow-positive company's sample is mostly 999s, and says so.

    Every QA dataset runs out of cash, so this uses a deliberately healthy
    input. Without the sentinel branch the chart would plot a 999-month bar and
    flatten everything else; with the old shim it plotted neither the 999s nor
    the real paths, but a uniform rectangle from p10 to p90.
    """
    healthy = EnhancedSimulationInputs(
        baseline_revenue=500_000,
        baseline_growth_rate=0,
        gross_margin=80,
        opex=50_000,
        payroll=50_000,
        other_costs=10_000,
        cash_balance=2_000_000,
    )
    out = _run(healthy, 1000)
    sample = out["distributions"]["runway"]

    sentinels = [v for v in sample if v == SENTINEL_SURVIVED]
    ended = [v for v in sample if v < SENTINEL_SURVIVED]

    assert sentinels, "a cash-flow-positive company must produce 999 sentinels"
    assert len(sentinels) + len(ended) == len(sample)

    # The sentinel is the only value above the engine's own 240-month runway
    # cap, so ">= 900" and "== 999" partition the sample identically and the
    # page's existing isRunwaySustainable convention stays consistent.
    assert max(ended) <= 240

    # And the count the engine reports agrees with the sample's proportion.
    reported_rate = out["runway"]["sustainableRate"] / 100
    sample_rate = len(sentinels) / len(sample)
    assert abs(reported_rate - sample_rate) < 0.10
