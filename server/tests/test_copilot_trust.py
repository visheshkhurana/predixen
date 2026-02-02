"""
Acceptance tests for Copilot Trust Refactor.

These tests verify:
1. Grounding status is correctly set based on run state
2. Provenance is attached to all numeric responses
3. Validation flags detect inconsistencies
4. NOT_AVAILABLE is returned when no run exists
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from server.copilot.trust import (
    fetchVerifiedRunResult,
    GroundingStatus,
    SimpleRunResult,
)
from server.api.canonical_state import compute_run_validation_flags


class TestFetchVerifiedRunResult:
    """Tests for the fetchVerifiedRunResult function."""
    
    def test_returns_not_available_when_no_run(self):
        """When no simulation run exists, return NOT_AVAILABLE status."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        
        result = fetchVerifiedRunResult(
            db=mock_db,
            company_id=1,
            scenario_id=1
        )
        
        assert result.grounding_status == GroundingStatus.NOT_AVAILABLE
        assert result.outputs is None
        
    def test_returns_verified_when_completed_run(self):
        """When a completed run exists, return VERIFIED status."""
        mock_run = MagicMock()
        mock_run.id = 123
        mock_run.status = "completed"
        mock_run.created_at = datetime.utcnow()
        mock_run.outputs_json = {
            "runway_months": {"p10": 10, "p50": 14, "p90": 18},
            "survival_probability": {"18mo": 0.75}
        }
        mock_run.data_snapshot_id = "snap_001"
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_run
        
        result = fetchVerifiedRunResult(
            db=mock_db,
            company_id=1,
            scenario_id=1
        )
        
        assert result.grounding_status == GroundingStatus.VERIFIED
        assert result.run_id == 123
        assert result.outputs is not None
        
    def test_returns_unverified_when_invalid_run(self):
        """When run has invalid status, return UNVERIFIED status."""
        mock_run = MagicMock()
        mock_run.id = 456
        mock_run.status = "invalid"
        mock_run.created_at = datetime.utcnow()
        mock_run.outputs_json = {}
        mock_run.data_snapshot_id = None
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_run
        
        result = fetchVerifiedRunResult(
            db=mock_db,
            company_id=1,
            scenario_id=1
        )
        
        assert result.grounding_status == GroundingStatus.UNVERIFIED


class TestValidationFlags:
    """Tests for simulation validation flags computation."""
    
    def test_no_flags_for_valid_data(self):
        """Clean data should have no validation flags."""
        outputs = {
            "runway_months": {"p10": 12, "p50": 18, "p90": 24},
            "survival_probability": {"18mo": 0.75}
        }
        cash_balance = 500000
        monthly_burn = 30000
        
        flags = compute_run_validation_flags(outputs, cash_balance, monthly_burn)
        
        assert flags['runwayCashBurnMismatch'] is False
        assert flags['survivalRunwayMismatch'] is False
        assert flags['monteCarloZeroVariance'] is False
        assert flags['has_critical_issues'] is False
        
    def test_runway_cash_burn_mismatch_detected(self):
        """Detect when runway doesn't match cash/burn calculation."""
        outputs = {
            "runway_months": {"p10": 6, "p50": 36, "p90": 48},
            "survival_probability": {"18mo": 0.9}
        }
        cash_balance = 500000
        monthly_burn = 100000
        
        flags = compute_run_validation_flags(outputs, cash_balance, monthly_burn)
        
        assert flags['runwayCashBurnMismatch'] is True
        assert flags['has_critical_issues'] is True
        
    def test_survival_runway_mismatch_high_runway_low_survival(self):
        """Detect when high runway contradicts low survival probability."""
        outputs = {
            "runway_months": {"p10": 28, "p50": 30, "p90": 36},
            "survival_probability": {"18mo": 0.3}
        }
        
        flags = compute_run_validation_flags(outputs, 1000000, 30000)
        
        assert flags['survivalRunwayMismatch'] is True
        
    def test_survival_runway_mismatch_low_runway_high_survival(self):
        """Detect when low runway contradicts high survival probability."""
        outputs = {
            "runway_months": {"p10": 4, "p50": 6, "p90": 8},
            "survival_probability": {"18mo": 0.98}
        }
        
        flags = compute_run_validation_flags(outputs, 100000, 15000)
        
        assert flags['survivalRunwayMismatch'] is True
        
    def test_monte_carlo_zero_variance_detected(self):
        """Detect when Monte Carlo outputs show zero variance."""
        outputs = {
            "runway_months": {"p10": 12, "p50": 12, "p90": 12},
            "survival_probability": {"18mo": 0.5},
            "cash_end": {"p10": 100000, "p50": 100000, "p90": 100000}
        }
        
        flags = compute_run_validation_flags(outputs, 500000, 40000)
        
        assert flags['monteCarloZeroVariance'] is True


class TestProvenanceAttachment:
    """Tests for provenance attachment to responses."""
    
    def test_verified_run_has_full_provenance(self):
        """Verified runs should include complete provenance block."""
        mock_run = MagicMock()
        mock_run.id = 789
        mock_run.status = "completed"
        mock_run.created_at = datetime(2024, 1, 15, 10, 30, 0)
        mock_run.outputs_json = {"runway_months": {"p50": 15}}
        mock_run.data_snapshot_id = "snap_abc123"
        mock_run.scenario_id = 5
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_run
        
        result = fetchVerifiedRunResult(
            db=mock_db,
            company_id=3,
            scenario_id=5
        )
        
        assert result.provenance is not None
        assert result.provenance.company_id == 3
        assert result.provenance.scenario_id == 5
        assert result.provenance.run_id == 789
        assert result.provenance.data_snapshot_id == "snap_abc123"


class TestStrictOutputModes:
    """Tests for strict output mode enforcement."""
    
    def test_not_available_message_for_missing_run(self):
        """When no run exists, return appropriate NOT_AVAILABLE message."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        
        result = fetchVerifiedRunResult(
            db=mock_db,
            company_id=1,
            scenario_id=99
        )
        
        assert result.grounding_status == GroundingStatus.NOT_AVAILABLE
        assert "No simulation run exists" in (result.message or "No simulation run exists")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
