"""Copilot follow-up questions speak the language of the business."""

from server.api.copilot import _generate_followups

SAAS_WORDS = ("MRR", "ARR", "Series A", "churn")


def test_d2c_brand_gets_d2c_questions():
    for message in ["how is my growth", "hello", "what about churn and cac", "simulate something"]:
        followups = _generate_followups(message, {"company": {"industry": "d2c", "currency": "INR"}})
        assert len(followups) == 3
        assert not any(w.lower() in f.lower() for f in followups for w in SAAS_WORDS), followups


def test_food_alias_counts_as_goods():
    followups = _generate_followups("compare me to benchmarks", {"company": {"industry": "food"}})
    assert any("D2C" in f or "ROAS" in f or "order" in f for f in followups), followups


def test_saas_keeps_saas_questions():
    followups = _generate_followups("what about churn", {"company": {"industry": "saas"}})
    assert any("churn" in f.lower() or "lifetime" in f.lower() or "retention" in f.lower() for f in followups)
