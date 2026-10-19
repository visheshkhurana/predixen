"""The public survival histogram must cover the run it claims to summarise.

`run_monte_carlo` still returns a 100-value head by default. This endpoint used
to bin that head and label the chart `n_simulations: 1000`, so the bars summed
to 100. It now asks for the full distribution.
"""

from unittest.mock import patch

from server.api.survival_simulator import SurvivalSimRequest, run_survival_simulation
from server.simulate.simulation_engine import RUNWAY_DISTRIBUTION_LIMIT


class _NoDB:
    def __enter__(self):
        raise RuntimeError("no database in this test")

    def __exit__(self, *exc):
        return False


def _run():
    req = SurvivalSimRequest(
        cash_on_hand=500_000,
        monthly_revenue=25_000,
        monthly_expenses=45_000,
        growth_rate=8,
    )
    with patch("server.api.survival_simulator.SessionLocal", lambda: _NoDB()):
        return run_survival_simulation(req)


def test_histogram_counts_sum_to_the_labelled_run_size():
    data = _run()
    counted = sum(bin_["count"] for bin_ in data["histogram"])
    assert data["n_simulations"] == 1000
    assert counted == data["n_simulations"]
    assert counted != RUNWAY_DISTRIBUTION_LIMIT
