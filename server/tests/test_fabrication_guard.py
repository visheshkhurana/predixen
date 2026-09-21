"""Golden + unit tests for the fabrication → NOT_AVAILABLE copilot guard.

These tests are offline (no LLM keys, no database). They prove copilot answers
NOT_AVAILABLE instead of inventing investor-facing numbers.
"""
import asyncio

from server.copilot.trust import (
    GroundingStatus,
    NOT_AVAILABLE_MESSAGE,
    apply_not_available_guard,
    apply_not_available_guard_to_text,
    flatten_output_text,
    missing_requested_metrics,
)
from server.lib.evals.eval_runner import run_fabrication_refusal_eval
from server.lib.evals.golden_datasets import FABRICATION_REFUSAL_TESTS, get_datasets_by_category


def _assert_golden(case: dict) -> None:
    payload = case["input"]
    expected = case["expected"]
    result = apply_not_available_guard(
        payload.get("copilot_output") or {},
        payload.get("grounding_status"),
        user_message=payload.get("user_message", ""),
        available_metrics=payload.get("available_metrics"),
        run_outputs=payload.get("run_outputs"),
    )
    text = flatten_output_text(result.output)
    must_na = expected.get("must_be_not_available", False)
    assert result.refused is must_na, (
        f"{case['id']}: refused={result.refused} reason={result.reason} text={text!r}"
    )
    if must_na:
        assert result.grounding_status == GroundingStatus.NOT_AVAILABLE.value
        assert "NOT_AVAILABLE" in text
    for needle in expected.get("must_contain", []):
        assert needle in text, f"{case['id']}: missing {needle!r} in {text!r}"
    for needle in expected.get("must_not_contain", []):
        assert needle not in text, f"{case['id']}: leaked {needle!r} in {text!r}"


def test_all_fabrication_refusal_goldens():
    cases = get_datasets_by_category("fabrication_refusal")
    assert len(cases) == 7
    assert cases == FABRICATION_REFUSAL_TESTS
    for case in cases:
        _assert_golden(case)


def test_eval_runner_fabrication_suite_is_perfect():
    scored = asyncio.run(run_fabrication_refusal_eval({}, db=None))
    assert scored["overall_score"] == 100
    assert scored["scores"]["fabrication_refusal"]["details"]["successful"] == 7


def test_missing_churn_is_detected():
    missing = missing_requested_metrics(
        "What is our churn?",
        {"monthly_revenue": {"value": 1000}},
        None,
    )
    assert missing == ["churn"]


def test_explicit_zero_is_present_not_missing():
    missing = missing_requested_metrics(
        "What is our churn?",
        {"churn_rate": {"value": 0}},
        None,
    )
    assert missing == []


def test_quick_chat_text_guard_strips_fabricated_runway():
    result = apply_not_available_guard_to_text(
        "You have 11.7 months of runway left.",
        GroundingStatus.NOT_AVAILABLE,
        user_message="How much runway do I have?",
        available_metrics={},
    )
    assert result.refused is True
    assert result.text == NOT_AVAILABLE_MESSAGE
    assert "11.7" not in (result.text or "")


def test_qualitative_answer_about_missing_metric_is_not_refused():
    """No churn data + advice with no figures -> answer passes through."""
    advice = {"executive_summary": [
        "Talk to churned customers, tighten onboarding, and add an annual plan."
    ]}
    result = apply_not_available_guard(
        advice,
        GroundingStatus.NOT_AVAILABLE,
        user_message="How do I reduce churn?",
        available_metrics={"monthly_revenue": {"value": 40000}},
    )
    assert result.refused is False
    assert result.output == advice


def test_survival_question_without_run_passes_when_no_number_is_stated():
    result = apply_not_available_guard_to_text(
        "Survival odds depend on burn and time to next raise; run a simulation to see them.",
        GroundingStatus.NOT_AVAILABLE,
        user_message="What drives my survival odds?",
        available_metrics={"net_burn": {"value": 20000}},
    )
    assert result.refused is False


def test_missing_metric_with_invented_figure_is_still_refused():
    result = apply_not_available_guard_to_text(
        "Your monthly churn is 4.2% which is above benchmark.",
        GroundingStatus.NOT_AVAILABLE,
        user_message="What is my churn?",
        available_metrics={"monthly_revenue": {"value": 40000}},
    )
    assert result.refused is True
    assert result.text == NOT_AVAILABLE_MESSAGE


def test_inr_and_shorthand_figures_count_as_numeric_claims():
    from server.copilot.trust import contains_numeric_financial_claims

    for text in [
        "You have ₹12,00,000 in the bank.",
        "Cash on hand is about 1.2 Cr.",
        "Monthly burn is Rs 4,50,000.",
        "Burn is roughly 45k a month.",
        "ARR is 2.4M.",
    ]:
        assert contains_numeric_financial_claims(text), text
    for text in [
        "Tighten onboarding and add an annual plan.",
        "Talk to your top 5 customers this week.",
    ]:
        assert not contains_numeric_financial_claims(text), text
