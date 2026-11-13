"""`runway.distribution` is a truncated head of the run, and the payload now says so.

`run_monte_carlo` returns the first `RUNWAY_DISTRIBUTION_LIMIT` runway values of a run
that is `n_simulations` long - 1000 by default - unless the caller passes
`distribution_limit=None`. The public survival endpoint does that and histograms
the full list. The default payload stays a labelled head for every other caller.

These tests pin the label, not the sampling. They assert that the payload states how many
values it carries, out of how many the run made, and whether it is short - and that the
list itself keeps the shape its one existing consumer reads.
"""

from server.simulate.simulation_engine import (
    RUNWAY_DISTRIBUTION_LIMIT,
    SimulationInputs,
    run_monte_carlo,
)


def _inputs(n_simulations: int) -> SimulationInputs:
    return SimulationInputs(
        baseline_revenue=80_000,
        baseline_growth_rate=4.0,
        gross_margin=72.0,
        opex=40_000,
        payroll=55_000,
        other_costs=9_000,
        cash_balance=1_200_000,
        n_simulations=n_simulations,
    )


def test_distribution_is_labelled_with_its_own_size_and_the_run_size():
    runway = run_monte_carlo(_inputs(1000), seed=7)["runway"]

    assert len(runway["distribution"]) == RUNWAY_DISTRIBUTION_LIMIT
    assert runway["distribution_n"] == RUNWAY_DISTRIBUTION_LIMIT
    assert runway["distribution_of_n"] == 1000
    assert runway["distribution_truncated"] is True


def test_the_label_always_counts_the_list_it_is_attached_to():
    # The invariant that stops the label drifting away from the list it describes.
    for n in (250, 1000):
        runway = run_monte_carlo(_inputs(n), seed=7)["runway"]
        assert runway["distribution_n"] == len(runway["distribution"])
        assert runway["distribution_of_n"] == n


def test_a_run_that_fits_inside_the_limit_is_not_labelled_truncated():
    runway = run_monte_carlo(_inputs(50), seed=7)["runway"]

    assert len(runway["distribution"]) == 50
    assert runway["distribution_n"] == 50
    assert runway["distribution_of_n"] == 50
    assert runway["distribution_truncated"] is False


def test_the_boundary_is_the_declared_limit_and_a_single_extra_run_crosses_it():
    # Pins the comparison to the constant rather than to a restated 100, and shows it is
    # `< n` and not `<= n`: the limit itself is complete, one more run is not.
    at_limit = run_monte_carlo(_inputs(RUNWAY_DISTRIBUTION_LIMIT), seed=7)["runway"]
    assert at_limit["distribution_truncated"] is False
    assert at_limit["distribution_n"] == RUNWAY_DISTRIBUTION_LIMIT

    over_limit = run_monte_carlo(_inputs(RUNWAY_DISTRIBUTION_LIMIT + 1), seed=7)["runway"]
    assert over_limit["distribution_truncated"] is True
    assert over_limit["distribution_n"] == RUNWAY_DISTRIBUTION_LIMIT


def test_the_sample_is_the_head_of_the_run_not_a_random_draw_from_it():
    # What kind of sample it is matters to anyone reasoning about bias: the truncated
    # field is the run's first values, so under one seed the first 100 of a 1000-run are
    # the same values as a whole 100-run. A random subsample would not satisfy this.
    full = run_monte_carlo(_inputs(1000), seed=7)["runway"]["distribution"]
    short = run_monte_carlo(_inputs(100), seed=7)["runway"]["distribution"]

    assert full == short


def test_distribution_limit_none_returns_the_whole_run():
    # The public survival histogram asks for this. The default stays truncated.
    runway = run_monte_carlo(_inputs(1000), seed=7, distribution_limit=None)["runway"]

    assert len(runway["distribution"]) == 1000
    assert runway["distribution_n"] == 1000
    assert runway["distribution_of_n"] == 1000
    assert runway["distribution_truncated"] is False
    assert runway["distribution"][:RUNWAY_DISTRIBUTION_LIMIT] == run_monte_carlo(
        _inputs(1000), seed=7
    )["runway"]["distribution"]


def test_distribution_stays_a_list_because_its_existing_consumer_requires_one():
    # The survival endpoint passes this list straight to
    # `_build_histogram(values: list, n_bins=20)`, which does `np.array(values)`.
    # Reshaping the field into a dict would break that consumer.
    for n in (50, 1000):
        distribution = run_monte_carlo(_inputs(n), seed=7)["runway"]["distribution"]
        assert isinstance(distribution, list)
        assert all(isinstance(value, float) for value in distribution)
