"""
Benchmark defaults for missing financial data.
Provides industry/stage-specific default values when data is missing.
"""
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class BenchmarkRange:
    """A range of benchmark values with min, max, and midpoint."""
    min_val: float
    max_val: float
    
    @property
    def midpoint(self) -> float:
        return (self.min_val + self.max_val) / 2


@dataclass
class IndustryBenchmarks:
    """Benchmarks for a specific industry/stage combination."""
    industry: str
    stage: str
    growth_rate_mom: BenchmarkRange
    gross_margin: BenchmarkRange
    marketing_pct_revenue: BenchmarkRange
    operating_pct_revenue: BenchmarkRange
    payroll_pct_revenue: Optional[BenchmarkRange] = None


BENCHMARK_DATA: Dict[str, Dict[str, IndustryBenchmarks]] = {
    "saas": {
        "pre_seed": IndustryBenchmarks(
            industry="saas",
            stage="pre_seed",
            growth_rate_mom=BenchmarkRange(0.10, 0.20),
            gross_margin=BenchmarkRange(0.70, 0.85),
            marketing_pct_revenue=BenchmarkRange(0.50, 0.100),
            operating_pct_revenue=BenchmarkRange(0.25, 0.50),
            payroll_pct_revenue=BenchmarkRange(0.30, 0.50),
        ),
        "seed": IndustryBenchmarks(
            industry="saas",
            stage="seed",
            growth_rate_mom=BenchmarkRange(0.08, 0.15),
            gross_margin=BenchmarkRange(0.70, 0.85),
            marketing_pct_revenue=BenchmarkRange(0.40, 0.80),
            operating_pct_revenue=BenchmarkRange(0.20, 0.45),
            payroll_pct_revenue=BenchmarkRange(0.25, 0.45),
        ),
        "series_a": IndustryBenchmarks(
            industry="saas",
            stage="series_a",
            growth_rate_mom=BenchmarkRange(0.05, 0.10),
            gross_margin=BenchmarkRange(0.70, 0.85),
            marketing_pct_revenue=BenchmarkRange(0.30, 0.60),
            operating_pct_revenue=BenchmarkRange(0.15, 0.40),
            payroll_pct_revenue=BenchmarkRange(0.20, 0.40),
        ),
        "series_b_plus": IndustryBenchmarks(
            industry="saas",
            stage="series_b_plus",
            growth_rate_mom=BenchmarkRange(0.03, 0.08),
            gross_margin=BenchmarkRange(0.70, 0.85),
            marketing_pct_revenue=BenchmarkRange(0.25, 0.50),
            operating_pct_revenue=BenchmarkRange(0.10, 0.35),
            payroll_pct_revenue=BenchmarkRange(0.15, 0.35),
        ),
    },
    "marketplace": {
        "pre_seed": IndustryBenchmarks(
            industry="marketplace",
            stage="pre_seed",
            growth_rate_mom=BenchmarkRange(0.05, 0.12),
            gross_margin=BenchmarkRange(0.40, 0.70),
            marketing_pct_revenue=BenchmarkRange(0.40, 0.80),
            operating_pct_revenue=BenchmarkRange(0.20, 0.45),
        ),
        "seed": IndustryBenchmarks(
            industry="marketplace",
            stage="seed",
            growth_rate_mom=BenchmarkRange(0.04, 0.08),
            gross_margin=BenchmarkRange(0.40, 0.70),
            marketing_pct_revenue=BenchmarkRange(0.30, 0.70),
            operating_pct_revenue=BenchmarkRange(0.15, 0.40),
        ),
        "series_a": IndustryBenchmarks(
            industry="marketplace",
            stage="series_a",
            growth_rate_mom=BenchmarkRange(0.03, 0.06),
            gross_margin=BenchmarkRange(0.45, 0.70),
            marketing_pct_revenue=BenchmarkRange(0.25, 0.55),
            operating_pct_revenue=BenchmarkRange(0.12, 0.35),
        ),
        "series_b_plus": IndustryBenchmarks(
            industry="marketplace",
            stage="series_b_plus",
            growth_rate_mom=BenchmarkRange(0.02, 0.05),
            gross_margin=BenchmarkRange(0.50, 0.75),
            marketing_pct_revenue=BenchmarkRange(0.20, 0.45),
            operating_pct_revenue=BenchmarkRange(0.10, 0.30),
        ),
    },
    "d2c": {
        "pre_seed": IndustryBenchmarks(
            industry="d2c",
            stage="pre_seed",
            growth_rate_mom=BenchmarkRange(0.04, 0.10),
            gross_margin=BenchmarkRange(0.35, 0.60),
            marketing_pct_revenue=BenchmarkRange(0.35, 0.70),
            operating_pct_revenue=BenchmarkRange(0.15, 0.35),
        ),
        "seed": IndustryBenchmarks(
            industry="d2c",
            stage="seed",
            growth_rate_mom=BenchmarkRange(0.03, 0.07),
            gross_margin=BenchmarkRange(0.35, 0.60),
            marketing_pct_revenue=BenchmarkRange(0.25, 0.60),
            operating_pct_revenue=BenchmarkRange(0.12, 0.30),
        ),
        "series_a": IndustryBenchmarks(
            industry="d2c",
            stage="series_a",
            growth_rate_mom=BenchmarkRange(0.02, 0.05),
            gross_margin=BenchmarkRange(0.40, 0.60),
            marketing_pct_revenue=BenchmarkRange(0.20, 0.50),
            operating_pct_revenue=BenchmarkRange(0.10, 0.25),
        ),
        "series_b_plus": IndustryBenchmarks(
            industry="d2c",
            stage="series_b_plus",
            growth_rate_mom=BenchmarkRange(0.01, 0.04),
            gross_margin=BenchmarkRange(0.45, 0.65),
            marketing_pct_revenue=BenchmarkRange(0.15, 0.40),
            operating_pct_revenue=BenchmarkRange(0.08, 0.22),
        ),
    },
    "fintech": {
        "pre_seed": IndustryBenchmarks(
            industry="fintech",
            stage="pre_seed",
            growth_rate_mom=BenchmarkRange(0.08, 0.18),
            gross_margin=BenchmarkRange(0.50, 0.80),
            marketing_pct_revenue=BenchmarkRange(0.30, 0.60),
            operating_pct_revenue=BenchmarkRange(0.25, 0.50),
        ),
        "seed": IndustryBenchmarks(
            industry="fintech",
            stage="seed",
            growth_rate_mom=BenchmarkRange(0.06, 0.12),
            gross_margin=BenchmarkRange(0.55, 0.80),
            marketing_pct_revenue=BenchmarkRange(0.25, 0.55),
            operating_pct_revenue=BenchmarkRange(0.20, 0.45),
        ),
        "series_a": IndustryBenchmarks(
            industry="fintech",
            stage="series_a",
            growth_rate_mom=BenchmarkRange(0.04, 0.09),
            gross_margin=BenchmarkRange(0.55, 0.80),
            marketing_pct_revenue=BenchmarkRange(0.20, 0.45),
            operating_pct_revenue=BenchmarkRange(0.15, 0.40),
        ),
        "series_b_plus": IndustryBenchmarks(
            industry="fintech",
            stage="series_b_plus",
            growth_rate_mom=BenchmarkRange(0.03, 0.07),
            gross_margin=BenchmarkRange(0.60, 0.85),
            marketing_pct_revenue=BenchmarkRange(0.15, 0.35),
            operating_pct_revenue=BenchmarkRange(0.12, 0.35),
        ),
    },
    "consumer_sub": {
        "pre_seed": IndustryBenchmarks(
            industry="consumer_sub",
            stage="pre_seed",
            growth_rate_mom=BenchmarkRange(0.06, 0.15),
            gross_margin=BenchmarkRange(0.60, 0.80),
            marketing_pct_revenue=BenchmarkRange(0.40, 0.80),
            operating_pct_revenue=BenchmarkRange(0.20, 0.40),
        ),
        "seed": IndustryBenchmarks(
            industry="consumer_sub",
            stage="seed",
            growth_rate_mom=BenchmarkRange(0.05, 0.10),
            gross_margin=BenchmarkRange(0.60, 0.80),
            marketing_pct_revenue=BenchmarkRange(0.35, 0.70),
            operating_pct_revenue=BenchmarkRange(0.15, 0.35),
        ),
        "series_a": IndustryBenchmarks(
            industry="consumer_sub",
            stage="series_a",
            growth_rate_mom=BenchmarkRange(0.03, 0.07),
            gross_margin=BenchmarkRange(0.65, 0.80),
            marketing_pct_revenue=BenchmarkRange(0.30, 0.55),
            operating_pct_revenue=BenchmarkRange(0.12, 0.30),
        ),
        "series_b_plus": IndustryBenchmarks(
            industry="consumer_sub",
            stage="series_b_plus",
            growth_rate_mom=BenchmarkRange(0.02, 0.05),
            gross_margin=BenchmarkRange(0.65, 0.85),
            marketing_pct_revenue=BenchmarkRange(0.25, 0.45),
            operating_pct_revenue=BenchmarkRange(0.10, 0.25),
        ),
    },
    "services": {
        "pre_seed": IndustryBenchmarks(
            industry="services",
            stage="pre_seed",
            growth_rate_mom=BenchmarkRange(0.03, 0.08),
            gross_margin=BenchmarkRange(0.30, 0.50),
            marketing_pct_revenue=BenchmarkRange(0.10, 0.30),
            operating_pct_revenue=BenchmarkRange(0.10, 0.25),
            payroll_pct_revenue=BenchmarkRange(0.50, 0.70),
        ),
        "seed": IndustryBenchmarks(
            industry="services",
            stage="seed",
            growth_rate_mom=BenchmarkRange(0.02, 0.06),
            gross_margin=BenchmarkRange(0.30, 0.55),
            marketing_pct_revenue=BenchmarkRange(0.08, 0.25),
            operating_pct_revenue=BenchmarkRange(0.08, 0.22),
            payroll_pct_revenue=BenchmarkRange(0.45, 0.65),
        ),
        "series_a": IndustryBenchmarks(
            industry="services",
            stage="series_a",
            growth_rate_mom=BenchmarkRange(0.02, 0.05),
            gross_margin=BenchmarkRange(0.35, 0.55),
            marketing_pct_revenue=BenchmarkRange(0.05, 0.20),
            operating_pct_revenue=BenchmarkRange(0.06, 0.18),
            payroll_pct_revenue=BenchmarkRange(0.40, 0.60),
        ),
        "series_b_plus": IndustryBenchmarks(
            industry="services",
            stage="series_b_plus",
            growth_rate_mom=BenchmarkRange(0.01, 0.04),
            gross_margin=BenchmarkRange(0.40, 0.60),
            marketing_pct_revenue=BenchmarkRange(0.04, 0.15),
            operating_pct_revenue=BenchmarkRange(0.05, 0.15),
            payroll_pct_revenue=BenchmarkRange(0.35, 0.55),
        ),
    },
    "hardware": {
        "pre_seed": IndustryBenchmarks(
            industry="hardware",
            stage="pre_seed",
            growth_rate_mom=BenchmarkRange(0.02, 0.08),
            gross_margin=BenchmarkRange(0.25, 0.45),
            marketing_pct_revenue=BenchmarkRange(0.10, 0.30),
            operating_pct_revenue=BenchmarkRange(0.25, 0.50),
            payroll_pct_revenue=BenchmarkRange(0.30, 0.50),
        ),
        "seed": IndustryBenchmarks(
            industry="hardware",
            stage="seed",
            growth_rate_mom=BenchmarkRange(0.02, 0.06),
            gross_margin=BenchmarkRange(0.30, 0.50),
            marketing_pct_revenue=BenchmarkRange(0.08, 0.25),
            operating_pct_revenue=BenchmarkRange(0.20, 0.45),
            payroll_pct_revenue=BenchmarkRange(0.25, 0.45),
        ),
        "series_a": IndustryBenchmarks(
            industry="hardware",
            stage="series_a",
            growth_rate_mom=BenchmarkRange(0.02, 0.05),
            gross_margin=BenchmarkRange(0.35, 0.55),
            marketing_pct_revenue=BenchmarkRange(0.06, 0.20),
            operating_pct_revenue=BenchmarkRange(0.15, 0.35),
            payroll_pct_revenue=BenchmarkRange(0.20, 0.40),
        ),
        "series_b_plus": IndustryBenchmarks(
            industry="hardware",
            stage="series_b_plus",
            growth_rate_mom=BenchmarkRange(0.01, 0.04),
            gross_margin=BenchmarkRange(0.40, 0.60),
            marketing_pct_revenue=BenchmarkRange(0.05, 0.15),
            operating_pct_revenue=BenchmarkRange(0.10, 0.25),
            payroll_pct_revenue=BenchmarkRange(0.15, 0.35),
        ),
    },
    "healthtech": {
        "pre_seed": IndustryBenchmarks(
            industry="healthtech",
            stage="pre_seed",
            growth_rate_mom=BenchmarkRange(0.04, 0.10),
            gross_margin=BenchmarkRange(0.55, 0.75),
            marketing_pct_revenue=BenchmarkRange(0.20, 0.45),
            operating_pct_revenue=BenchmarkRange(0.25, 0.50),
            payroll_pct_revenue=BenchmarkRange(0.35, 0.55),
        ),
        "seed": IndustryBenchmarks(
            industry="healthtech",
            stage="seed",
            growth_rate_mom=BenchmarkRange(0.03, 0.08),
            gross_margin=BenchmarkRange(0.60, 0.80),
            marketing_pct_revenue=BenchmarkRange(0.15, 0.40),
            operating_pct_revenue=BenchmarkRange(0.20, 0.40),
            payroll_pct_revenue=BenchmarkRange(0.30, 0.50),
        ),
        "series_a": IndustryBenchmarks(
            industry="healthtech",
            stage="series_a",
            growth_rate_mom=BenchmarkRange(0.03, 0.07),
            gross_margin=BenchmarkRange(0.65, 0.80),
            marketing_pct_revenue=BenchmarkRange(0.12, 0.30),
            operating_pct_revenue=BenchmarkRange(0.15, 0.35),
            payroll_pct_revenue=BenchmarkRange(0.25, 0.45),
        ),
        "series_b_plus": IndustryBenchmarks(
            industry="healthtech",
            stage="series_b_plus",
            growth_rate_mom=BenchmarkRange(0.02, 0.05),
            gross_margin=BenchmarkRange(0.65, 0.85),
            marketing_pct_revenue=BenchmarkRange(0.10, 0.25),
            operating_pct_revenue=BenchmarkRange(0.10, 0.25),
            payroll_pct_revenue=BenchmarkRange(0.20, 0.40),
        ),
    },
}


def get_benchmarks(industry: str, stage: str) -> Optional[IndustryBenchmarks]:
    """Get benchmarks for a specific industry/stage combination."""
    industry = industry.lower().replace("-", "_").replace(" ", "_")
    stage = stage.lower().replace("-", "_").replace(" ", "_")
    
    industry_data = BENCHMARK_DATA.get(industry, BENCHMARK_DATA.get("saas"))
    if not industry_data:
        return None
    
    return industry_data.get(stage, industry_data.get("seed"))


def get_default_growth_rate(industry: str, stage: str) -> float:
    """Get default growth rate for missing data."""
    benchmarks = get_benchmarks(industry, stage)
    if benchmarks:
        return benchmarks.growth_rate_mom.midpoint
    return 0.05


def get_default_gross_margin(industry: str, stage: str) -> float:
    """Get default gross margin for missing data."""
    benchmarks = get_benchmarks(industry, stage)
    if benchmarks:
        return benchmarks.gross_margin.midpoint
    return 0.60


def estimate_expense_breakdown(
    total_expenses: float,
    revenue: float,
    industry: str,
    stage: str
) -> Dict[str, float]:
    """
    Estimate expense breakdown based on industry benchmarks.
    Only use when actual breakdown is missing.
    """
    benchmarks = get_benchmarks(industry, stage)
    
    if not benchmarks or revenue <= 0:
        return {
            'cogs': total_expenses * 0.30,
            'marketing': total_expenses * 0.30,
            'payroll': total_expenses * 0.25,
            'operating': total_expenses * 0.15,
        }
    
    marketing_pct = benchmarks.marketing_pct_revenue.midpoint
    operating_pct = benchmarks.operating_pct_revenue.midpoint
    gross_margin = benchmarks.gross_margin.midpoint
    
    cogs_pct = 1 - gross_margin
    
    payroll_pct = 0.30
    if benchmarks.payroll_pct_revenue:
        payroll_pct = benchmarks.payroll_pct_revenue.midpoint
    
    estimated_marketing = revenue * marketing_pct
    estimated_operating = revenue * operating_pct
    estimated_cogs = revenue * cogs_pct
    estimated_payroll = revenue * payroll_pct
    
    total_estimated = estimated_marketing + estimated_operating + estimated_cogs + estimated_payroll
    
    if total_estimated > 0:
        scale = total_expenses / total_estimated
        return {
            'cogs': estimated_cogs * scale,
            'marketing': estimated_marketing * scale,
            'payroll': estimated_payroll * scale,
            'operating': estimated_operating * scale,
        }
    
    return {
        'cogs': total_expenses * 0.30,
        'marketing': total_expenses * 0.30,
        'payroll': total_expenses * 0.25,
        'operating': total_expenses * 0.15,
    }


def inject_benchmark_defaults(
    metrics: Dict[str, Any],
    industry: str,
    stage: str,
    required_fields: Optional[list] = None
) -> Dict[str, Any]:
    """
    Inject benchmark defaults for missing required fields.
    Returns a new dict with defaults filled in and source markers.
    """
    result = dict(metrics)
    result.setdefault('_benchmark_injected', [])
    
    benchmarks = get_benchmarks(industry, stage)
    if not benchmarks:
        return result
    
    if required_fields is None:
        required_fields = ['growth_rate_mom', 'gross_margin']
    
    if 'growth_rate_mom' in required_fields and metrics.get('growth_rate_mom') is None:
        result['growth_rate_mom'] = benchmarks.growth_rate_mom.midpoint
        result['_benchmark_injected'].append({
            'field': 'growth_rate_mom',
            'value': result['growth_rate_mom'],
            'source': 'benchmark',
            'confidence': 'low',
            'range': {
                'min': benchmarks.growth_rate_mom.min_val,
                'max': benchmarks.growth_rate_mom.max_val
            }
        })
    
    if 'gross_margin' in required_fields and metrics.get('gross_margin') is None:
        result['gross_margin'] = benchmarks.gross_margin.midpoint
        result['_benchmark_injected'].append({
            'field': 'gross_margin',
            'value': result['gross_margin'],
            'source': 'benchmark',
            'confidence': 'low',
            'range': {
                'min': benchmarks.gross_margin.min_val,
                'max': benchmarks.gross_margin.max_val
            }
        })
    
    return result
