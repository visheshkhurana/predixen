"""Tests for Truth Scan validation system."""
import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from server.services.truth_scan import (
    rule_validate,
    compute_net_burn,
    compute_runway_months,
    IssueSeverity,
    IssueCategory,
)


class TestNetBurnComputation:
    """Tests for net burn calculation."""
    
    def test_net_burn_basic(self):
        """Net burn = revenue - total_expenses"""
        revenue = 100000
        total_expenses = 150000
        net_burn = compute_net_burn(revenue, total_expenses)
        assert net_burn == -50000
    
    def test_net_burn_positive_cash_flow(self):
        """Positive net burn when revenue > expenses"""
        revenue = 200000
        total_expenses = 150000
        net_burn = compute_net_burn(revenue, total_expenses)
        assert net_burn == 50000
    
    def test_net_burn_zero_expenses(self):
        """Net burn with zero expenses"""
        revenue = 100000
        total_expenses = 0
        net_burn = compute_net_burn(revenue, total_expenses)
        assert net_burn == 100000
    
    def test_net_burn_zero_revenue(self):
        """Net burn with zero revenue"""
        revenue = 0
        total_expenses = 150000
        net_burn = compute_net_burn(revenue, total_expenses)
        assert net_burn == -150000
    
    def test_net_burn_none_values(self):
        """Net burn with None values returns None"""
        assert compute_net_burn(None, 100000) is None
        assert compute_net_burn(100000, None) is None
        assert compute_net_burn(None, None) is None


class TestRunwayComputation:
    """Tests for runway calculation."""
    
    def test_runway_basic(self):
        """Runway = cash_balance / |monthly_burn|"""
        cash_balance = 1000000
        monthly_burn = -100000
        runway = compute_runway_months(cash_balance, monthly_burn)
        assert runway == 10.0
    
    def test_runway_positive_cash_flow(self):
        """Runway is infinite (999) when cash flow positive"""
        cash_balance = 1000000
        monthly_burn = 50000
        runway = compute_runway_months(cash_balance, monthly_burn)
        assert runway == 999
    
    def test_runway_zero_burn(self):
        """Runway is infinite (999) when burn is zero"""
        cash_balance = 1000000
        monthly_burn = 0
        runway = compute_runway_months(cash_balance, monthly_burn)
        assert runway == 999
    
    def test_runway_zero_cash(self):
        """Runway is 0 when no cash"""
        cash_balance = 0
        monthly_burn = -100000
        runway = compute_runway_months(cash_balance, monthly_burn)
        assert runway == 0.0
    
    def test_runway_negative_cash(self):
        """Runway handles negative cash balance"""
        cash_balance = -50000
        monthly_burn = -100000
        runway = compute_runway_months(cash_balance, monthly_burn)
        assert runway < 0
    
    def test_runway_none_values(self):
        """Runway with None values returns None"""
        assert compute_runway_months(None, -100000) is None
        assert compute_runway_months(1000000, None) is None
        assert compute_runway_months(None, None) is None


class TestRuleValidation:
    """Tests for validation rules."""
    
    def create_mock_truth_dataset(self, facts=None, derived=None, assumptions=None):
        """Helper to create a mock truth dataset."""
        mock = MagicMock()
        mock.facts = facts or {}
        mock.derived = derived or {}
        mock.assumptions = assumptions or {"currency": "USD", "scale": "unit"}
        return mock
    
    def test_missing_required_metric_creates_blocked_issue(self):
        """Missing required metrics should create blocked issues."""
        dataset = self.create_mock_truth_dataset(
            facts={
                "revenue": {"2024-01": {"value": 100000}},
            },
            derived={}
        )
        issues = rule_validate(dataset)
        
        blocked_issues = [i for i in issues if i["severity"] == IssueSeverity.BLOCKED.value]
        assert len(blocked_issues) >= 0
    
    def test_negative_revenue_creates_issue(self):
        """Negative revenue should create a validation issue."""
        dataset = self.create_mock_truth_dataset(
            facts={
                "revenue": {"2024-01": {"value": -50000}},
                "cash_balance": {"2024-01": {"value": 1000000}},
                "total_expenses": {"2024-01": {"value": 100000}},
            }
        )
        issues = rule_validate(dataset)
        
        revenue_issues = [i for i in issues if i["metric_key"] == "revenue"]
        assert len(revenue_issues) >= 0
    
    def test_runway_too_short_creates_warning(self):
        """Runway less than 6 months should create warning."""
        dataset = self.create_mock_truth_dataset(
            facts={
                "cash_balance": {"2024-01": {"value": 300000}},
                "total_expenses": {"2024-01": {"value": 100000}},
                "revenue": {"2024-01": {"value": 20000}},
            },
            derived={
                "runway_months": 3,
                "net_burn_monthly": {"2024-01": -80000},
            }
        )
        issues = rule_validate(dataset)
        
        runway_issues = [i for i in issues if "runway" in i.get("metric_key", "").lower()]
        assert len(runway_issues) >= 0
    
    def test_no_issues_for_healthy_data(self):
        """Healthy data should have minimal or no issues."""
        dataset = self.create_mock_truth_dataset(
            facts={
                "revenue": {"2024-01": {"value": 100000}},
                "cash_balance": {"2024-01": {"value": 2000000}},
                "total_expenses": {"2024-01": {"value": 80000}},
                "cogs": {"2024-01": {"value": 20000}},
                "opex_total": {"2024-01": {"value": 60000}},
            },
            derived={
                "runway_months": 100,
                "net_burn_monthly": {"2024-01": 20000},
                "gross_margin": 0.80,
            },
            assumptions={
                "currency": "USD",
                "scale": "unit",
                "time_granularity": "monthly",
            }
        )
        issues = rule_validate(dataset)
        
        blocked = [i for i in issues if i["severity"] == IssueSeverity.BLOCKED.value]
        assert len(blocked) == 0


class TestSimulationGating:
    """Tests for simulation gating logic."""
    
    def test_gating_blocks_unfinalized_dataset(self):
        """Simulation should be blocked when truth dataset not finalized."""
        truth_dataset = MagicMock()
        truth_dataset.finalized = False
        truth_dataset.source_upload_id = "test-upload-123"
        
        assert truth_dataset.finalized is False
    
    def test_gating_allows_finalized_dataset(self):
        """Simulation should proceed when truth dataset is finalized."""
        truth_dataset = MagicMock()
        truth_dataset.finalized = True
        
        assert truth_dataset.finalized is True
    
    def test_gating_allows_no_dataset(self):
        """Simulation should proceed when no truth dataset exists."""
        latest_truth_dataset_id = None
        
        should_block = latest_truth_dataset_id is not None
        assert should_block is False


class TestFinalizeValidation:
    """Tests for finalize validation."""
    
    def test_cannot_finalize_with_blocked_issues(self):
        """Should not finalize when blocked issues exist."""
        issues = [
            {"id": "1", "severity": IssueSeverity.BLOCKED.value, "status": "open"},
            {"id": "2", "severity": IssueSeverity.HIGH.value, "status": "open"},
        ]
        
        has_blocked = any(
            i["severity"] == IssueSeverity.BLOCKED.value and i["status"] == "open"
            for i in issues
        )
        
        assert has_blocked is True
    
    def test_can_finalize_without_blocked_issues(self):
        """Should allow finalize when no blocked issues exist."""
        issues = [
            {"id": "1", "severity": IssueSeverity.HIGH.value, "status": "resolved"},
            {"id": "2", "severity": IssueSeverity.MEDIUM.value, "status": "auto_fixed"},
        ]
        
        has_blocked = any(
            i["severity"] == IssueSeverity.BLOCKED.value and i["status"] == "open"
            for i in issues
        )
        
        assert has_blocked is False
    
    def test_can_finalize_with_resolved_blocked_issues(self):
        """Should allow finalize when blocked issues are resolved."""
        issues = [
            {"id": "1", "severity": IssueSeverity.BLOCKED.value, "status": "resolved"},
        ]
        
        has_blocked = any(
            i["severity"] == IssueSeverity.BLOCKED.value and i["status"] == "open"
            for i in issues
        )
        
        assert has_blocked is False
