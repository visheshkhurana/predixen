"""A ₹15Cr raise must not be cut to ₹10Cr by a dollar-sized cap."""

from server.api.simulations import INPUT_GUARDRAILS, ScenarioCreate


def test_inr_sized_raise_is_kept():
    s = ScenarioCreate(name="Raise ₹15Cr", fundraise_amount=150_000_000)
    assert s.fundraise_amount == 150_000_000


def test_cap_and_floor_still_apply():
    cap = INPUT_GUARDRAILS["fundraise_amount"]["max"]
    assert ScenarioCreate(name="x", fundraise_amount=cap * 10).fundraise_amount == cap
    assert ScenarioCreate(name="x", fundraise_amount=-5).fundraise_amount == 0
