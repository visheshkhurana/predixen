"""
Tests for financial calculations and normalization.
Ensures burn/runway formulas are correct and expenses are properly normalized.
"""
import pytest
from server.ingest.calculations import (
    calculate_net_burn,
    calculate_runway_months,
    determine_burn_status,
    format_burn_display,
    format_runway_display,
    compute_baseline_metrics,
    BurnStatus,
)
from server.ingest.classifier import (
    normalize_label,
    classify_all_rows,
    SignConvention,
    Classification,
    map_expense_bucket,
    ExpenseBucket,
    detect_sign_convention,
    parse_rows_with_hierarchy,
)


class TestExpenseNormalization:
    """Tests for expense normalization (negative -> positive)."""
    
    def test_negative_expense_normalized_to_positive(self):
        """Given expense raw=-1000, stored should be +1000."""
        rows = [{
            'label': 'Operating Expenses',
            'values': {'2025-01': -1000.0}
        }]
        
        result = classify_all_rows(rows)
        classified_rows = result['rows']
        
        assert len(classified_rows) == 1
        row = classified_rows[0]
        assert row['classification'] == 'expense'
        
        period_values = row['values'].get('2025-01', {})
        assert period_values['raw'] == -1000.0
        assert period_values['normalized'] == 1000.0
    
    def test_positive_expense_stays_positive(self):
        """Expenses that are already positive should stay positive."""
        rows = [{
            'label': 'Marketing Costs',
            'values': {'2025-01': 500.0}
        }]
        
        result = classify_all_rows(rows)
        classified_rows = result['rows']
        
        assert len(classified_rows) == 1
        row = classified_rows[0]
        assert row['classification'] == 'expense'
        
        period_values = row['values'].get('2025-01', {})
        assert period_values['normalized'] == 500.0


class TestBurnFormula:
    """Tests for burn calculation: net_burn = expenses - revenue."""
    
    def test_burning_cash(self):
        """Revenue=1000, Expenses=1500 -> net_burn=500 (burning cash)."""
        revenue = 1000.0
        expenses = 1500.0
        
        net_burn = calculate_net_burn(expenses, revenue)
        
        assert net_burn == 500.0
        assert determine_burn_status(net_burn) == BurnStatus.BURNING
    
    def test_profitable(self):
        """Revenue=1500, Expenses=1000 -> net_burn=-500 (profitable)."""
        revenue = 1500.0
        expenses = 1000.0
        
        net_burn = calculate_net_burn(expenses, revenue)
        
        assert net_burn == -500.0
        assert determine_burn_status(net_burn) == BurnStatus.PROFITABLE
    
    def test_breakeven(self):
        """Revenue=1000, Expenses=1000 -> net_burn=0 (breakeven)."""
        revenue = 1000.0
        expenses = 1000.0
        
        net_burn = calculate_net_burn(expenses, revenue)
        
        assert net_burn == 0.0
        assert determine_burn_status(net_burn) == BurnStatus.BREAKEVEN


class TestRunwayCalculation:
    """Tests for runway calculation."""
    
    def test_sustainable_when_profitable(self):
        """When net_burn <= 0, runway should be 'Sustainable'."""
        net_burn = -500.0
        cash_on_hand = 10000.0
        
        runway = calculate_runway_months(net_burn, cash_on_hand)
        burn_status = determine_burn_status(net_burn)
        display = format_runway_display(runway, burn_status)
        
        assert runway is None
        assert display == "Sustainable"
    
    def test_runway_months_when_burning(self):
        """When burning cash, runway = cash_on_hand / net_burn."""
        net_burn = 1000.0
        cash_on_hand = 12000.0
        
        runway = calculate_runway_months(net_burn, cash_on_hand)
        
        assert runway == 12.0
    
    def test_runway_unknown_when_cash_missing(self):
        """When net_burn > 0 and cash_on_hand is missing, runway is unknown."""
        net_burn = 1000.0
        cash_on_hand = None
        
        runway = calculate_runway_months(net_burn, cash_on_hand)
        burn_status = determine_burn_status(net_burn)
        display = format_runway_display(runway, burn_status)
        
        assert runway is None
        assert "Unknown" in display or "missing" in display.lower()
    
    def test_runway_capped_at_36_months(self):
        """Runway display should cap at 36+ months."""
        net_burn = 100.0
        cash_on_hand = 5000.0
        
        runway = calculate_runway_months(net_burn, cash_on_hand)
        burn_status = determine_burn_status(net_burn)
        display = format_runway_display(runway, burn_status)
        
        assert runway == 50.0
        assert "36+" in display


class TestBurnDisplay:
    """Tests for burn display formatting."""
    
    def test_burn_display_when_burning(self):
        """When net_burn > 0, display should show 'Monthly Burn'."""
        net_burn = 500.0
        
        display = format_burn_display(net_burn)
        
        assert display['label'] == 'Monthly Burn'
        assert display['value'] == 500.0
        assert display['is_surplus'] is False
    
    def test_burn_display_when_profitable(self):
        """When net_burn < 0, display should show 'Monthly Surplus'."""
        net_burn = -500.0
        
        display = format_burn_display(net_burn)
        
        assert display['label'] == 'Monthly Surplus'
        assert display['value'] == 500.0
        assert display['is_surplus'] is True
    
    def test_burn_display_breakeven(self):
        """When net_burn = 0, display should show 'Breakeven'."""
        net_burn = 0.0
        
        display = format_burn_display(net_burn)
        
        assert display['label'] == 'Breakeven'
        assert display['value'] == 0.0


class TestSignConventionDetection:
    """Tests for detecting sign convention in files."""
    
    def test_accounting_convention_detected(self):
        """Files with negative expenses and positive revenue -> accounting."""
        rows = [
            {'label': 'Revenue', 'values': {'2025-01': 10000.0}},
            {'label': 'Operating Expenses', 'values': {'2025-01': -5000.0}},
            {'label': 'Marketing Costs', 'values': {'2025-01': -2000.0}},
        ]
        
        parsed = parse_rows_with_hierarchy(rows)
        convention = detect_sign_convention(parsed)
        
        assert convention == SignConvention.ACCOUNTING
    
    def test_all_positive_convention_detected(self):
        """Files with all positive values -> all_positive."""
        rows = [
            {'label': 'Revenue', 'values': {'2025-01': 10000.0}},
            {'label': 'Operating Expenses', 'values': {'2025-01': 5000.0}},
            {'label': 'Marketing Costs', 'values': {'2025-01': 2000.0}},
        ]
        
        parsed = parse_rows_with_hierarchy(rows)
        convention = detect_sign_convention(parsed)
        
        assert convention == SignConvention.ALL_POSITIVE


class TestRowClassification:
    """Tests for row classification logic."""
    
    def test_revenue_row_classified_correctly(self):
        """Revenue-like labels should be classified as revenue."""
        rows = [{'label': 'Total Revenue', 'values': {'2025-01': 10000.0}}]
        
        result = classify_all_rows(rows)
        
        assert result['rows'][0]['classification'] == 'revenue'
    
    def test_expense_row_classified_correctly(self):
        """Expense-like labels should be classified as expense."""
        rows = [{'label': 'Operating Expenses', 'values': {'2025-01': 5000.0}}]
        
        result = classify_all_rows(rows)
        
        assert result['rows'][0]['classification'] == 'expense'
    
    def test_derived_row_classified_correctly(self):
        """Derived/KPI labels should be classified as derived."""
        rows = [{'label': 'Gross Profit', 'values': {'2025-01': 5000.0}}]
        
        result = classify_all_rows(rows)
        
        assert result['rows'][0]['classification'] == 'derived'


class TestExpenseBucketMapping:
    """Tests for expense bucket mapping."""
    
    def test_marketing_bucket(self):
        """Marketing-related expenses map to marketing bucket."""
        assert map_expense_bucket("Marketing Expenses") == ExpenseBucket.MARKETING
        assert map_expense_bucket("Advertising Costs") == ExpenseBucket.MARKETING
    
    def test_payroll_bucket(self):
        """Payroll-related expenses map to payroll bucket."""
        assert map_expense_bucket("Payroll") == ExpenseBucket.PAYROLL
        assert map_expense_bucket("Salaries and Wages") == ExpenseBucket.PAYROLL
    
    def test_cogs_bucket(self):
        """COGS-related expenses map to cogs bucket."""
        assert map_expense_bucket("COGS") == ExpenseBucket.COGS
        assert map_expense_bucket("Cost of Goods Sold") == ExpenseBucket.COGS
        assert map_expense_bucket("Payment Processing") == ExpenseBucket.COGS
    
    def test_operating_bucket_default(self):
        """Unknown expenses default to operating bucket."""
        assert map_expense_bucket("Misc Expenses") == ExpenseBucket.OPERATING
        assert map_expense_bucket("Other Costs") == ExpenseBucket.OPERATING


class TestBaselineMetrics:
    """Tests for computing complete baseline metrics."""
    
    def test_compute_baseline_burning_cash(self):
        """Test baseline metrics when company is burning cash."""
        baseline = compute_baseline_metrics(
            revenue=10000.0,
            total_expenses=15000.0,
            cash_on_hand=60000.0,
        )
        
        assert baseline.revenue == 10000.0
        assert baseline.total_expenses == 15000.0
        assert baseline.net_burn == 5000.0
        assert baseline.burn_status == BurnStatus.BURNING
        assert baseline.runway_months == 12.0
    
    def test_compute_baseline_profitable(self):
        """Test baseline metrics when company is profitable."""
        baseline = compute_baseline_metrics(
            revenue=20000.0,
            total_expenses=15000.0,
            cash_on_hand=100000.0,
        )
        
        assert baseline.net_burn == -5000.0
        assert baseline.burn_status == BurnStatus.PROFITABLE
        assert baseline.runway_months is None
    
    def test_compute_baseline_with_missing_cash(self):
        """Test baseline metrics when cash is missing."""
        baseline = compute_baseline_metrics(
            revenue=10000.0,
            total_expenses=15000.0,
            cash_on_hand=None,
        )
        
        assert baseline.net_burn == 5000.0
        assert baseline.runway_months is None
        assert baseline.warnings is not None
        assert len(baseline.warnings) > 0
