from sqlalchemy.orm import Session
from server.models.benchmark import Benchmark

BENCHMARK_DATA = [
    {"industry": "general_saas", "stage": "seed", "metric_name": "revenue_growth_mom", "p25": 5, "p50": 10, "p75": 20, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "seed", "metric_name": "gross_margin", "p25": 60, "p50": 70, "p75": 80, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "seed", "metric_name": "burn_multiple", "p25": 1.5, "p50": 2.5, "p75": 4, "direction": "lower_is_better"},
    {"industry": "general_saas", "stage": "seed", "metric_name": "runway_months", "p25": 12, "p50": 18, "p75": 24, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "seed", "metric_name": "net_revenue_retention", "p25": 90, "p50": 100, "p75": 120, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "seed", "metric_name": "logo_retention_12m", "p25": 75, "p50": 85, "p75": 92, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "seed", "metric_name": "concentration_top5", "p25": 20, "p50": 35, "p75": 50, "direction": "lower_is_better"},
    {"industry": "general_saas", "stage": "seed", "metric_name": "ltv_cac_ratio", "p25": 2, "p50": 3, "p75": 5, "direction": "higher_is_better"},
    
    {"industry": "general_saas", "stage": "series_a", "metric_name": "revenue_growth_mom", "p25": 8, "p50": 12, "p75": 18, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "series_a", "metric_name": "gross_margin", "p25": 65, "p50": 75, "p75": 82, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "series_a", "metric_name": "burn_multiple", "p25": 1.2, "p50": 2, "p75": 3, "direction": "lower_is_better"},
    {"industry": "general_saas", "stage": "series_a", "metric_name": "runway_months", "p25": 15, "p50": 21, "p75": 30, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "series_a", "metric_name": "net_revenue_retention", "p25": 95, "p50": 105, "p75": 125, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "series_a", "metric_name": "logo_retention_12m", "p25": 80, "p50": 88, "p75": 95, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "series_a", "metric_name": "concentration_top5", "p25": 15, "p50": 25, "p75": 40, "direction": "lower_is_better"},
    {"industry": "general_saas", "stage": "series_a", "metric_name": "ltv_cac_ratio", "p25": 2.5, "p50": 4, "p75": 6, "direction": "higher_is_better"},
    
    {"industry": "general_saas", "stage": "unknown_stage", "metric_name": "revenue_growth_mom", "p25": 5, "p50": 10, "p75": 15, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "unknown_stage", "metric_name": "gross_margin", "p25": 55, "p50": 68, "p75": 78, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "unknown_stage", "metric_name": "burn_multiple", "p25": 1.5, "p50": 2.5, "p75": 4, "direction": "lower_is_better"},
    {"industry": "general_saas", "stage": "unknown_stage", "metric_name": "runway_months", "p25": 10, "p50": 15, "p75": 24, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "unknown_stage", "metric_name": "net_revenue_retention", "p25": 85, "p50": 100, "p75": 115, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "unknown_stage", "metric_name": "logo_retention_12m", "p25": 70, "p50": 82, "p75": 90, "direction": "higher_is_better"},
    {"industry": "general_saas", "stage": "unknown_stage", "metric_name": "concentration_top5", "p25": 20, "p50": 35, "p75": 55, "direction": "lower_is_better"},
    {"industry": "general_saas", "stage": "unknown_stage", "metric_name": "ltv_cac_ratio", "p25": 2, "p50": 3, "p75": 5, "direction": "higher_is_better"},
]

def seed_benchmarks(db: Session):
    existing = db.query(Benchmark).first()
    if existing:
        return
    
    for data in BENCHMARK_DATA:
        benchmark = Benchmark(**data)
        db.add(benchmark)
    
    db.commit()
