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
