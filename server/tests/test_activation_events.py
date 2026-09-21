"""signup_completed + founder_activated: first-success only, sample excluded."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from server.services.activation import (
    company_is_sample,
    emit_signup_completed,
    maybe_emit_founder_activated,
)


def test_company_is_sample_from_property():
    assert company_is_sample(SimpleNamespace(is_sample=True, metadata_json={})) is True
    assert company_is_sample(SimpleNamespace(is_sample=False, metadata_json={})) is False


def test_company_is_sample_from_metadata_json():
    company = SimpleNamespace(is_sample=False, metadata_json={"is_sample": True})
    assert company_is_sample(company) is True


def test_company_is_sample_treats_missing_company_as_sample():
    assert company_is_sample(None) is True


def test_company_is_sample_ignores_non_dict_metadata():
    company = SimpleNamespace(is_sample=False, metadata_json="nope")
    assert company_is_sample(company) is False


def test_emit_signup_completed_payload():
    with patch("server.services.activation.posthog_capture") as capture:
        assert emit_signup_completed(user_id=7, method="email") is True
        capture.assert_called_once_with(
            "signup_completed",
            "user:7",
            {"method": "email", "user_id": 7},
        )


def test_emit_signup_completed_google():
    with patch("server.services.activation.posthog_capture") as capture:
        emit_signup_completed(user_id=3, method="google")
        assert capture.call_args.args[2]["method"] == "google"


def test_emit_signup_completed_never_raises():
    with patch("server.services.activation.posthog_capture", side_effect=RuntimeError("down")):
        assert emit_signup_completed(user_id=1, method="email") is False


def test_sample_company_never_emits_founder_activated():
    company = SimpleNamespace(id=11, is_sample=True, metadata_json={"is_sample": True})
    db = MagicMock()
    with patch("server.services.activation.posthog_capture") as capture:
        assert (
            maybe_emit_founder_activated(
                db, user_id=1, company=company, source="truth_scan", exclude_truth_scan_id=99
            )
            is False
        )
        capture.assert_not_called()
    db.query.assert_not_called()


def test_sample_metadata_equivalent_never_emits():
    company = SimpleNamespace(id=11, is_sample=False, metadata_json={"is_sample": True})
    with patch("server.services.activation.posthog_capture") as capture:
        assert (
            maybe_emit_founder_activated(
                MagicMock(), user_id=1, company=company, source="simulation"
            )
            is False
        )
        capture.assert_not_called()


def test_real_first_truth_scan_emits_founder_activated():
    company = SimpleNamespace(id=22, is_sample=False, metadata_json={})
    with patch("server.services.activation.has_prior_real_activation", return_value=False):
        with patch("server.services.activation.posthog_capture") as capture:
            emitted = maybe_emit_founder_activated(
                MagicMock(),
                user_id=5,
                company=company,
                source="truth_scan",
                exclude_truth_scan_id=101,
            )
            assert emitted is True
            event, distinct_id, properties = capture.call_args.args
            assert event == "founder_activated"
            assert distinct_id == "user:5"
            assert properties["source"] == "truth_scan"
            assert properties["company_id"] == 22
            assert properties["is_sample"] is False
            assert properties["user_id"] == 5


def test_real_first_simulation_emits_founder_activated():
    company = SimpleNamespace(id=22, is_sample=False, metadata_json={})
    with patch("server.services.activation.has_prior_real_activation", return_value=False):
        with patch("server.services.activation.posthog_capture") as capture:
            maybe_emit_founder_activated(
                MagicMock(),
                user_id=5,
                company=company,
                source="simulation",
                exclude_simulation_run_id=44,
            )
            assert capture.call_args.args[2]["source"] == "simulation"


def test_retry_after_prior_real_success_does_not_emit():
    company = SimpleNamespace(id=22, is_sample=False, metadata_json={})
    with patch("server.services.activation.has_prior_real_activation", return_value=True):
        with patch("server.services.activation.posthog_capture") as capture:
            assert (
                maybe_emit_founder_activated(
                    MagicMock(),
                    user_id=5,
                    company=company,
                    source="truth_scan",
                    exclude_truth_scan_id=102,
                )
                is False
            )
            capture.assert_not_called()


def test_founder_activated_never_raises():
    company = SimpleNamespace(id=22, is_sample=False, metadata_json={})
    with patch("server.services.activation.has_prior_real_activation", side_effect=RuntimeError("db")):
        assert (
            maybe_emit_founder_activated(
                MagicMock(), user_id=5, company=company, source="truth_scan"
            )
            is False
        )


def test_real_company_ids_skip_sample():
    """A #21 sample-data company must not count toward prior activation."""
    from server.services.activation import real_company_ids

    sample = SimpleNamespace(id=1, is_sample=True, metadata_json={"is_sample": True})
    real = SimpleNamespace(id=2, is_sample=False, metadata_json={})
    assert real_company_ids([sample, real]) == [2]


def test_has_prior_only_looks_at_real_company_ids():
    from server.services.activation import has_prior_real_activation

    with patch("server.services.activation._real_company_ids_for_user", return_value=[2]):
        with patch("server.services.activation._has_prior_truth_scan", return_value=False) as scans:
            with patch("server.services.activation._has_prior_simulation", return_value=False):
                assert has_prior_real_activation(MagicMock(), 9, exclude_truth_scan_id=50) is False
                assert scans.call_args.args[1] == [2]
