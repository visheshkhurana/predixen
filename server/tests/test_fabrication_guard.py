"""Golden + unit tests for the fabrication → NOT_AVAILABLE copilot guard.

These tests are offline (no LLM keys, no database). They prove copilot answers
NOT_AVAILABLE instead of inventing investor-facing numbers.
"""
import asyncio

import pytest

from server.copilot.trust import (
    GroundingStatus,
    NOT_AVAILABLE_MESSAGE,
    apply_not_available_guard,
    apply_not_available_guard_to_text,
    extract_available_metrics,
    flatten_output_text,
    contains_numeric_financial_claims,
    missing_requested_metrics,
    prose_states_metric_figure,
    requested_metrics,
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
    assert len(cases) == 25
    assert cases == FABRICATION_REFUSAL_TESTS
    for case in cases:
        _assert_golden(case)


def test_eval_runner_fabrication_suite_is_perfect():
    scored = asyncio.run(run_fabrication_refusal_eval({}, db=None))
    assert scored["overall_score"] == 100
    assert scored["scores"]["fabrication_refusal"]["details"]["successful"] == 25


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


def test_estimated_truth_scan_placeholders_are_not_available():
    verified = extract_available_metrics({
        "metrics": {
            "monthly_revenue": 45000,
            "cash_balance": 600000,
            "cac": 500,
            "ltv": 3000,
            "net_revenue_retention": 108,
            "customer_count": 150,
            "_estimated_metrics": [
                "cac", "ltv", "net_revenue_retention", "customer_count",
            ],
        }
    })
    assert "monthly_revenue" in verified
    assert "cash_balance" in verified
    assert "cac" not in verified
    assert "ltv" not in verified
    assert "net_revenue_retention" not in verified
    assert "customer_count" not in verified
    assert missing_requested_metrics(
        "What is our NRR?",
        {"net_revenue_retention": 108, "_estimated_metrics": ["net_revenue_retention"]},
        {"runway_months": {"p50": 11}},
    ) == ["nrr"]


def test_cash_burn_revenue_questions_are_recognized():
    assert "cash" in requested_metrics("What is our cash balance?")
    assert "burn" in requested_metrics("What is our monthly burn?")
    assert "revenue" in requested_metrics("What is our MRR?")


def test_structured_numeric_leaf_is_a_figure():
    result = apply_not_available_guard(
        {
            "executive_summary": ["Snapshot attached."],
            "financials": {"unit_economics": {"cac": 500}},
        },
        GroundingStatus.VERIFIED,
        user_message="What is our CAC?",
        available_metrics={"monthly_revenue": {"value": 10000}},
    )
    assert result.refused is True


@pytest.mark.parametrize(
    "metric,question,answer",
    [
        (
            "customers",
            "How should I work with customers?",
            "Talk to your top 5 customers this week. Step 1 is to ask why they stayed.",
        ),
        (
            "revenue",
            "How should we think about revenue?",
            "Focus on your top 3 revenue drivers. Step 1 is to rank them by gross margin.",
        ),
        (
            "burn",
            "How do I bring burn down?",
            "Cut 2 of your biggest burn items. Step 1 is to list every recurring vendor.",
        ),
    ],
)
def test_qualitative_counting_advice_is_not_a_fabricated_figure(metric, question, answer):
    """Advice can count customers, revenue drivers, or burn items without stating the metric."""
    assert prose_states_metric_figure(answer, metric) is False
    result = apply_not_available_guard(
        {"executive_summary": [answer]},
        GroundingStatus.NOT_AVAILABLE,
        user_message=question,
        available_metrics={},
    )
    assert result.refused is False, result.reason
    assert result.output["executive_summary"] == [answer]


@pytest.mark.parametrize(
    "metric,question,answer,leaked",
    [
        ("revenue", "What is our revenue?", "Revenue reached 50,000 last month.", "50,000"),
        ("revenue", "What is our MRR?", "Your MRR hit 50000.", "50000"),
        ("revenue", "What is our revenue?", "Revenue grew to 50000.", "50000"),
        ("burn", "What is our burn?", "You're burning 40000 a month.", "40000"),
        ("burn", "What is our burn?", "Burn sits at 40000.", "40000"),
        ("customers", "How many customers do we have?", "Customers: about 150.", "150"),
    ],
)
def test_plain_verb_figures_near_metric_words_are_refused(metric, question, answer, leaked):
    """Wide-window fabrications with no currency symbol still refuse.

    contains_numeric_financial_claims stays false for these sentences; the
    digit window is what has to catch them.
    """
    assert contains_numeric_financial_claims(answer) is False
    assert prose_states_metric_figure(answer, metric) is True
    result = apply_not_available_guard_to_text(
        answer,
        GroundingStatus.VERIFIED,
        user_message=question,
        available_metrics={"cash_balance": {"value": 1000}},
    )
    assert result.refused is True
    assert result.text == NOT_AVAILABLE_MESSAGE
    assert leaked not in (result.text or "")


@pytest.mark.parametrize(
    "metric,answer",
    [
        ("burn", "We burned 40000 last quarter."),
        ("customers", "You have 1 customer."),
        ("revenue", "ARR reached 50000."),
    ],
)
def test_metric_inflections_still_state_a_figure(metric, answer):
    assert prose_states_metric_figure(answer, metric) is True


@pytest.mark.parametrize(
    "question,answer,leaked",
    [
        ("How many customers do we have?", "You have 150 customers.", "150"),
        ("What is our revenue?", "Revenue is $50k/month.", "$50k"),
        ("What is our burn?", "Burn is ₹8L per month.", "₹8L"),
        ("What is our monthly burn?", "Monthly burn of 40000.", "40000"),
        ("How many customers do we have?", "You have 5 customers.", "5"),
    ],
)
def test_fabricated_customer_revenue_burn_figures_are_refused(question, answer, leaked):
    """Real headcounts and burn/revenue figures still refuse when the metric is unverified.

    A small headcount ("5 customers") is still a figure. Only ranking and step
    counts ("top 5", "step 1") are advice.
    """
    result = apply_not_available_guard_to_text(
        answer,
        GroundingStatus.VERIFIED,
        user_message=question,
        available_metrics={"cash_balance": {"value": 1000}},
    )
    assert result.refused is True
    assert result.text == NOT_AVAILABLE_MESSAGE
    assert leaked not in (result.text or "")


@pytest.mark.parametrize(
    "question,leaf",
    [
        ("How many customers do we have?", {"customer_count": 150}),
        ("How many active customers do we have?", {"active_customers": 150}),
        ("What is our revenue?", {"monthly_revenue": 50000}),
        ("What is our monthly burn?", {"monthly_burn": 40000}),
        ("What is our burn?", {"burn_rate": 40000}),
    ],
)
def test_structured_customer_revenue_burn_leaves_are_refused(question, leaf):
    """Snake-case numeric leaves are still figures under the wide digit window."""
    result = apply_not_available_guard(
        {"executive_summary": ["Snapshot attached."], "financials": leaf},
        GroundingStatus.VERIFIED,
        user_message=question,
        available_metrics={"cash_balance": {"value": 1000}},
    )
    assert result.refused is True
    assert result.grounding_status == GroundingStatus.NOT_AVAILABLE.value


def test_estimated_nrr_qualitative_advice_still_passes():
    advice = {"executive_summary": [
        "Tighten logo churn and expand seats if you want NRR to move."
    ]}
    result = apply_not_available_guard(
        advice,
        GroundingStatus.VERIFIED,
        user_message="How do I improve NRR?",
        available_metrics={
            "net_revenue_retention": 108,
            "_estimated_metrics": ["net_revenue_retention"],
        },
    )
    assert result.refused is False
    assert result.output == advice
