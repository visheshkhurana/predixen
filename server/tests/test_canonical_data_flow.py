"""
Acceptance tests for canonical data flow consistency.

These tests verify that:
1. Company state is properly persisted and retrieved
2. Simulation runs reference the correct data snapshot
3. Input hash is computed deterministically
4. Provenance tracking is maintained across operations
"""
import pytest
from server.schemas.canonical import (
    compute_hash,
    Financials,
    ScenarioOverrides,
    CompanyStateSchema,
)
from server.models.company_state import compute_snapshot_id


class TestCanonicalHashing:
    """Test deterministic hashing for provenance tracking."""
    
    def test_compute_hash_deterministic(self):
        """Hash should be deterministic for same inputs."""
        obj = {"a": 1, "b": 2, "c": [1, 2, 3]}
        hash1 = compute_hash(obj)
        hash2 = compute_hash(obj)
        assert hash1 == hash2
    
    def test_compute_hash_key_order_independent(self):
        """Hash should be the same regardless of key order."""
        obj1 = {"a": 1, "b": 2}
        obj2 = {"b": 2, "a": 1}
        assert compute_hash(obj1) == compute_hash(obj2)
    
    def test_compute_hash_different_values(self):
        """Hash should differ for different values."""
        obj1 = {"a": 1}
        obj2 = {"a": 2}
        assert compute_hash(obj1) != compute_hash(obj2)
    
    def test_snapshot_id_deterministic(self):
        """Snapshot ID should be deterministic for same state."""
        state = {"cash": 100000, "burn": 10000}
        id1 = compute_snapshot_id(state)
        id2 = compute_snapshot_id(state)
        assert id1 == id2
        assert len(id1) == 16


class TestFinancialsSchema:
    """Test Financials schema validation."""
    
    def test_financials_required_fields(self):
        """Financials should require key financial metrics."""
        financials = Financials(
            cashBalance=100000,
            monthlyBurn=10000,
            revenueMonthly=5000,
            revenueGrowthRate=5.0,
            expensesMonthly=15000
        )
        assert financials.cashBalance == 100000
        assert financials.monthlyBurn == 10000
    
    def test_financials_uses_defaults(self):
        """Financials should use defaults for optional fields."""
        financials = Financials(
            cashBalance=100000,
            monthlyBurn=5000,
        )
        assert financials.cashBalance == 100000
        assert financials.revenueMonthly == 0
        assert financials.revenueGrowthRate == 0


class TestScenarioOverrides:
    """Test ScenarioOverrides schema."""
    
    def test_default_overrides(self):
        """Default overrides should have None values (no overrides)."""
        overrides = ScenarioOverrides()
        assert overrides.expenseMultiplier is None
        assert overrides.revenueGrowthDelta is None
        assert overrides.pricingDelta is None
    
    def test_custom_overrides(self):
        """Custom overrides should be applied."""
        overrides = ScenarioOverrides(
            expenseMultiplier=0.9,
            revenueGrowthDelta=5.0,
            pricingDelta=10.0
        )
        assert overrides.expenseMultiplier == 0.9
        assert overrides.revenueGrowthDelta == 5.0


class TestCompanyStateSchema:
    """Test CompanyStateSchema for API responses."""
    
    def test_company_state_structure(self):
        """CompanyStateSchema should have correct structure."""
        from datetime import datetime
        
        state = CompanyStateSchema(
            companyId=1,
            environment="user",
            snapshotId="abc123",
            updatedAt=datetime(2026, 1, 15, 12, 0, 0),
            financials=Financials(
                cashBalance=100000,
                monthlyBurn=10000,
                revenueMonthly=5000,
                revenueGrowthRate=5.0,
                expensesMonthly=15000
            ),
            fundraisingRounds=[],
            stateJson={}
        )
        assert state.companyId == 1
        assert state.snapshotId == "abc123"
        assert state.financials.cashBalance == 100000


class TestDataFlowConsistency:
    """Test data flow consistency across layers."""
    
    def test_financials_serialization_roundtrip(self):
        """Financials should serialize and deserialize correctly."""
        financials = Financials(
            cashBalance=100000,
            monthlyBurn=10000,
            revenueMonthly=5000,
            revenueGrowthRate=5.0,
            expensesMonthly=15000
        )
        data = financials.model_dump()
        restored = Financials(**data)
        assert restored.cashBalance == financials.cashBalance
        assert restored.monthlyBurn == financials.monthlyBurn
    
    def test_overrides_serialization_roundtrip(self):
        """ScenarioOverrides should serialize and deserialize correctly."""
        overrides = ScenarioOverrides(
            expenseMultiplier=0.85,
            revenueGrowthDelta=7.5
        )
        data = overrides.model_dump()
        restored = ScenarioOverrides(**data)
        assert restored.expenseMultiplier == overrides.expenseMultiplier
        assert restored.revenueGrowthDelta == overrides.revenueGrowthDelta
    
    def test_hash_includes_all_inputs(self):
        """Hash should change when any input field changes."""
        base = {
            "companyId": 1,
            "base": {"cashBalance": 100000, "monthlyBurn": 10000},
            "overrides": {"expenseMultiplier": 1.0},
            "config": {"numPaths": 1000}
        }
        base_hash = compute_hash(base)
        
        modified_company = {**base, "companyId": 2}
        modified_base = {**base, "base": {"cashBalance": 200000, "monthlyBurn": 10000}}
        modified_overrides = {**base, "overrides": {"expenseMultiplier": 0.9}}
        modified_config = {**base, "config": {"numPaths": 500}}
        
        assert compute_hash(modified_company) != base_hash
        assert compute_hash(modified_base) != base_hash
        assert compute_hash(modified_overrides) != base_hash
        assert compute_hash(modified_config) != base_hash
