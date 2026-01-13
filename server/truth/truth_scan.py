from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.models.transaction import TransactionRecord
from server.models.customer import CustomerRecord
from server.models.benchmark import Benchmark

def compute_truth_scan(company: Company, db: Session) -> Dict[str, Any]:
    financials = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company.id
    ).order_by(FinancialRecord.period_end.desc()).all()
    
    transactions = db.query(TransactionRecord).filter(
        TransactionRecord.company_id == company.id
    ).all()
    
    customers = db.query(CustomerRecord).filter(
        CustomerRecord.company_id == company.id
    ).all()
    
    metrics = {}
    flags = []
    
    if financials:
        latest = financials[0]
        
        metrics["monthly_revenue"] = latest.revenue
        metrics["cogs"] = latest.cogs
        metrics["opex"] = latest.opex
        metrics["payroll"] = latest.payroll
        metrics["other_costs"] = latest.other_costs
        metrics["cash_balance"] = latest.cash_balance
        
        total_costs = latest.cogs + latest.opex + latest.payroll + latest.other_costs
        gross_profit = latest.revenue - latest.cogs
        
        metrics["gross_margin"] = (gross_profit / latest.revenue * 100) if latest.revenue > 0 else 0
        metrics["operating_margin"] = ((latest.revenue - total_costs) / latest.revenue * 100) if latest.revenue > 0 else 0
        
        net_burn = total_costs - latest.revenue
        metrics["net_burn"] = net_burn
        metrics["is_profitable"] = net_burn < 0
        
        if len(financials) >= 2:
            prev = financials[1]
            if prev.revenue > 0:
                metrics["revenue_growth_mom"] = ((latest.revenue - prev.revenue) / prev.revenue) * 100
            else:
                metrics["revenue_growth_mom"] = 0
            
            prev_burn = (prev.cogs + prev.opex + prev.payroll + prev.other_costs) - prev.revenue
            burn_change = net_burn - prev_burn
            metrics["burn_change"] = burn_change
        else:
            metrics["revenue_growth_mom"] = 0
            metrics["burn_change"] = 0
        
        if net_burn > 0:
            metrics["burn_multiple"] = net_burn / max(1, latest.revenue)
            runway_months = latest.cash_balance / net_burn
            metrics["runway_p50"] = round(runway_months, 1)
            metrics["runway_p10"] = round(runway_months * 0.7, 1)
            metrics["runway_p90"] = round(runway_months * 1.4, 1)
            metrics["runway_sustainable"] = False
        else:
            metrics["burn_multiple"] = 0
            metrics["runway_p50"] = None
            metrics["runway_p10"] = None
            metrics["runway_p90"] = None
            metrics["runway_sustainable"] = True
        
        runway_p50 = metrics.get("runway_p50")
        if runway_p50 is not None and runway_p50 < 6:
            flags.append({
                "severity": "high",
                "title": "Critical Runway",
                "description": "Less than 6 months of runway remaining",
                "metrics_involved": ["runway_p50", "net_burn", "cash_balance"]
            })
        elif runway_p50 is not None and runway_p50 < 12:
            flags.append({
                "severity": "medium",
                "title": "Low Runway",
                "description": "Less than 12 months of runway remaining",
                "metrics_involved": ["runway_p50", "net_burn"]
            })
        
        if metrics.get("gross_margin", 0) < 50:
            flags.append({
                "severity": "medium",
                "title": "Low Gross Margin",
                "description": "Gross margin below 50% benchmark",
                "metrics_involved": ["gross_margin"]
            })
    else:
        metrics["monthly_revenue"] = 0
        metrics["cash_balance"] = 0
        metrics["net_burn"] = 0
        metrics["runway_p50"] = 0
        metrics["runway_p10"] = 0
        metrics["runway_p90"] = 0
        flags.append({
            "severity": "high",
            "title": "No Financial Data",
            "description": "Upload financial data to enable analysis",
            "metrics_involved": []
        })
    
    if transactions:
        customer_revenue = {}
        for txn in transactions:
            cid = txn.customer_id or "unknown"
            customer_revenue[cid] = customer_revenue.get(cid, 0) + txn.amount
        
        total_revenue = sum(customer_revenue.values())
        sorted_customers = sorted(customer_revenue.values(), reverse=True)
        
        if len(sorted_customers) >= 1 and total_revenue > 0:
            metrics["concentration_top1"] = (sorted_customers[0] / total_revenue) * 100
        else:
            metrics["concentration_top1"] = 0
        
        if len(sorted_customers) >= 5 and total_revenue > 0:
            top5_rev = sum(sorted_customers[:5])
            metrics["concentration_top5"] = (top5_rev / total_revenue) * 100
        else:
            metrics["concentration_top5"] = metrics.get("concentration_top1", 0)
        
        if metrics.get("concentration_top5", 0) > 50:
            flags.append({
                "severity": "medium",
                "title": "High Customer Concentration",
                "description": "Top 5 customers represent over 50% of revenue",
                "metrics_involved": ["concentration_top5"]
            })
    else:
        metrics["concentration_top1"] = None
        metrics["concentration_top5"] = None
    
    if customers and transactions:
        customer_ids = set(c.customer_id for c in customers)
        active_customers = set(t.customer_id for t in transactions if t.customer_id)
        
        if len(customer_ids) > 0:
            metrics["logo_retention_12m"] = (len(active_customers & customer_ids) / len(customer_ids)) * 100
        else:
            metrics["logo_retention_12m"] = None
        
        metrics["net_revenue_retention"] = 100
    else:
        metrics["logo_retention_12m"] = None
        metrics["net_revenue_retention"] = None
    
    metrics["ltv"] = None
    metrics["cac"] = None
    metrics["ltv_cac_ratio"] = None
    metrics["payback_months"] = None
    
    data_confidence = compute_data_confidence(metrics, bool(financials), bool(transactions), bool(customers))
    quality_of_growth = compute_quality_of_growth(metrics, data_confidence)
    
    benchmarks = get_benchmarks(db, company.industry or "general_saas", company.stage or "unknown_stage")
    benchmark_comparisons = compare_to_benchmarks(metrics, benchmarks)
    
    return {
        "metrics": metrics,
        "flags": flags,
        "data_confidence_score": data_confidence,
        "quality_of_growth_index": quality_of_growth,
        "benchmark_comparisons": benchmark_comparisons,
        "computed_at": datetime.utcnow().isoformat()
    }

def compute_data_confidence(metrics: Dict, has_financials: bool, has_transactions: bool, has_customers: bool) -> int:
    score = 0
    
    if has_financials:
        score += 40
        if metrics.get("revenue_growth_mom") is not None:
            score += 10
        if metrics.get("cash_balance", 0) > 0:
            score += 10
    
    if has_transactions:
        score += 20
        if metrics.get("concentration_top5") is not None:
            score += 5
    
    if has_customers:
        score += 10
        if metrics.get("logo_retention_12m") is not None:
            score += 5
    
    return min(100, score)

def compute_quality_of_growth(metrics: Dict, confidence: int) -> int:
    score = 50
    
    growth = metrics.get("revenue_growth_mom", 0)
    if growth >= 15:
        score += 15
    elif growth >= 10:
        score += 10
    elif growth >= 5:
        score += 5
    elif growth < 0:
        score -= 10
    
    gm = metrics.get("gross_margin", 0)
    if gm >= 70:
        score += 15
    elif gm >= 60:
        score += 10
    elif gm >= 50:
        score += 5
    else:
        score -= 5
    
    burn_mult = metrics.get("burn_multiple", 0)
    if burn_mult <= 0:
        score += 10
    elif burn_mult <= 1.5:
        score += 8
    elif burn_mult <= 2.5:
        score += 5
    elif burn_mult > 4:
        score -= 10
    
    conc = metrics.get("concentration_top5")
    if conc is not None:
        if conc > 60:
            score -= 15
        elif conc > 40:
            score -= 5
    
    if confidence < 60:
        score -= 10
    
    return max(0, min(100, score))

def get_benchmarks(db: Session, industry: str, stage: str) -> List[Benchmark]:
    benchmarks = db.query(Benchmark).filter(
        Benchmark.industry == industry,
        Benchmark.stage == stage
    ).all()
    
    if not benchmarks:
        benchmarks = db.query(Benchmark).filter(
            Benchmark.industry == "general_saas",
            Benchmark.stage == "unknown_stage"
        ).all()
    
    return benchmarks

def compare_to_benchmarks(metrics: Dict, benchmarks: List[Benchmark]) -> List[Dict[str, Any]]:
    comparisons = []
    
    metric_mapping = {
        "revenue_growth_mom": "revenue_growth_mom",
        "gross_margin": "gross_margin",
        "burn_multiple": "burn_multiple",
        "runway_p50": "runway_months",
        "net_revenue_retention": "net_revenue_retention",
        "logo_retention_12m": "logo_retention_12m",
        "concentration_top5": "concentration_top5",
        "ltv_cac_ratio": "ltv_cac_ratio",
    }
    
    for benchmark in benchmarks:
        for metric_key, bench_name in metric_mapping.items():
            if benchmark.metric_name == bench_name:
                value = metrics.get(metric_key)
                if value is not None:
                    if value >= benchmark.p75:
                        position = "above_p75"
                    elif value >= benchmark.p50:
                        position = "above_p50"
                    elif value >= benchmark.p25:
                        position = "above_p25"
                    else:
                        position = "below_p25"
                    
                    comparisons.append({
                        "metric": metric_key,
                        "value": value,
                        "p25": benchmark.p25,
                        "p50": benchmark.p50,
                        "p75": benchmark.p75,
                        "position": position,
                        "direction": benchmark.direction
                    })
    
    return comparisons
