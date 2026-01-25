from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.models.transaction import TransactionRecord
from server.models.customer import CustomerRecord
from server.models.benchmark import Benchmark


def validate_metrics(metrics: Dict[str, Any], latest_financial: FinancialRecord) -> Dict[str, Any]:
    """
    Validate metrics against sensible ranges and flag anomalies.
    Returns validation results with flags for suspect values.
    """
    validation = {
        "is_valid": True,
        "warnings": [],
        "errors": [],
        "missing_data": []
    }
    
    net_burn = metrics.get("net_burn", 0)
    revenue = latest_financial.revenue if latest_financial else 0
    cash_balance = latest_financial.cash_balance if latest_financial else 0
    
    if net_burn < 0 and abs(net_burn) > 10_000_000 and revenue < 1_000_000:
        validation["warnings"].append({
            "field": "net_burn",
            "message": "Net burn seems unusually high for company size",
            "value": net_burn,
            "threshold": 10_000_000
        })
    
    if revenue < 0:
        validation["errors"].append({
            "field": "revenue",
            "message": "Revenue cannot be negative",
            "value": revenue
        })
        validation["is_valid"] = False
    
    if cash_balance is None or cash_balance == 0:
        validation["missing_data"].append({
            "field": "cash_balance",
            "message": "Cash balance not provided - runway calculations may be inaccurate"
        })
    
    gross_margin = metrics.get("gross_margin", 0)
    if gross_margin > 100:
        validation["warnings"].append({
            "field": "gross_margin",
            "message": "Gross margin exceeds 100% - check COGS data",
            "value": gross_margin
        })
    elif gross_margin < 0:
        validation["warnings"].append({
            "field": "gross_margin",
            "message": "Negative gross margin indicates COGS exceeds revenue",
            "value": gross_margin
        })
    
    burn_multiple = metrics.get("burn_multiple")
    if burn_multiple is None and net_burn > 0:
        validation["missing_data"].append({
            "field": "burn_multiple",
            "message": "Cannot calculate burn multiple - no ARR growth data"
        })
    
    revenue_growth = metrics.get("revenue_growth_yoy", 0)
    if abs(revenue_growth) > 1000:
        validation["warnings"].append({
            "field": "revenue_growth_yoy",
            "message": "Revenue growth appears unusually high - verify data",
            "value": revenue_growth
        })
    
    return validation


def format_currency(value: float) -> Dict[str, Any]:
    """
    Format a currency value with appropriate unit abbreviation.
    Returns both raw value and formatted string.
    """
    if value is None:
        return {"raw": None, "formatted": "N/A", "unit": None}
    
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    
    if abs_value >= 1_000_000:
        return {
            "raw": value,
            "formatted": f"{sign}${abs_value / 1_000_000:.1f}M",
            "unit": "millions"
        }
    elif abs_value >= 1_000:
        return {
            "raw": value,
            "formatted": f"{sign}${abs_value / 1_000:.1f}K",
            "unit": "thousands"
        }
    else:
        return {
            "raw": value,
            "formatted": f"{sign}${abs_value:.0f}",
            "unit": "dollars"
        }


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
    
    # Get extracted data from company metadata (from PDF upload during onboarding)
    extracted_metrics = {}
    extracted_financials = {}
    if company.metadata_json and isinstance(company.metadata_json, dict):
        extracted_metrics = company.metadata_json.get("extracted_metrics", {})
        extracted_financials = company.metadata_json.get("extracted_financials", {})
    
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
            
            net_new_arr = (latest.revenue - prev.revenue) * 12
            metrics["net_new_arr"] = net_new_arr
        else:
            # Use extracted metrics as fallback when only one data point exists
            extracted_growth_mom = extracted_metrics.get("revenue_growth_mom")
            extracted_cmgr = extracted_metrics.get("cmgr")
            if extracted_growth_mom is not None:
                metrics["revenue_growth_mom"] = extracted_growth_mom
            elif extracted_cmgr is not None:
                metrics["revenue_growth_mom"] = extracted_cmgr
            else:
                metrics["revenue_growth_mom"] = None  # Use None instead of 0 to indicate missing
            metrics["burn_change"] = 0
            metrics["net_new_arr"] = 0
        
        if len(financials) >= 12:
            prev_year = financials[11]
            if prev_year.revenue > 0:
                metrics["revenue_growth_yoy"] = ((latest.revenue - prev_year.revenue) / prev_year.revenue) * 100
            else:
                metrics["revenue_growth_yoy"] = 0
        elif len(financials) >= 2:
            mom_growth = metrics.get("revenue_growth_mom", 0) or 0
            metrics["revenue_growth_yoy"] = ((1 + mom_growth/100) ** 12 - 1) * 100
        else:
            # Use extracted YoY growth if available (converted from multiplier to percentage)
            extracted_yoy = extracted_metrics.get("revenue_growth_yoy")
            if extracted_yoy is not None:
                # If stored as multiplier (e.g., 1.24), convert to percentage
                if extracted_yoy > 0 and extracted_yoy < 10:
                    metrics["revenue_growth_yoy"] = (extracted_yoy - 1) * 100
                else:
                    metrics["revenue_growth_yoy"] = extracted_yoy
            else:
                metrics["revenue_growth_yoy"] = None  # Use None instead of 0 to indicate missing
        
        net_new_arr = metrics.get("net_new_arr", 0)
        if net_burn > 0:
            if net_new_arr > 0:
                metrics["burn_multiple"] = round(net_burn / net_new_arr, 2)
            else:
                # Use extracted burn multiple if available
                extracted_burn_multiple = extracted_metrics.get("burn_multiple")
                if extracted_burn_multiple is not None:
                    metrics["burn_multiple"] = extracted_burn_multiple
                else:
                    metrics["burn_multiple"] = None
            
            if latest.cash_balance and latest.cash_balance > 0:
                runway_months = latest.cash_balance / net_burn
                metrics["runway_p50"] = round(runway_months, 1)
                metrics["runway_p10"] = round(runway_months * 0.7, 1)
                metrics["runway_p90"] = round(runway_months * 1.4, 1)
            else:
                metrics["runway_p50"] = None  # Use None instead of 0
                metrics["runway_p10"] = None
                metrics["runway_p90"] = None
            metrics["runway_sustainable"] = False
        else:
            # Company is profitable - use extracted burn multiple if available, or 0
            extracted_burn_multiple = extracted_metrics.get("burn_multiple")
            if extracted_burn_multiple is not None:
                metrics["burn_multiple"] = extracted_burn_multiple
            else:
                metrics["burn_multiple"] = 0  # 0 burn multiple for profitable companies
            metrics["runway_p50"] = None
            metrics["runway_p10"] = None
            metrics["runway_p90"] = None
            metrics["runway_sustainable"] = True
        
        metrics["data_validation"] = validate_metrics(metrics, latest)
        
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
        # No FinancialRecord exists - use extracted_financials from PDF if available
        if extracted_financials:
            monthly_rev = extracted_financials.get("monthly_revenue")
            cash = extracted_financials.get("cash_balance")
            burn = extracted_financials.get("net_burn")
            
            metrics["monthly_revenue"] = monthly_rev
            metrics["cash_balance"] = cash
            
            # Compute net_burn if not directly provided
            if burn is not None:
                metrics["net_burn"] = burn
            else:
                opex = extracted_financials.get("opex", 0) or 0
                payroll = extracted_financials.get("payroll", 0) or 0
                other = extracted_financials.get("other_costs", 0) or 0
                gross_margin_pct = extracted_financials.get("gross_margin_pct", 70) or 70
                
                if monthly_rev:
                    cogs = monthly_rev * (1 - gross_margin_pct / 100)
                    total_costs = cogs + opex + payroll + other
                    burn = total_costs - monthly_rev
                    metrics["net_burn"] = burn
                else:
                    # Pre-revenue: burn is just total expenses
                    total_costs = opex + payroll + other
                    if total_costs > 0:
                        metrics["net_burn"] = total_costs
                    else:
                        metrics["net_burn"] = None
            
            # Compute margins
            gm = extracted_financials.get("gross_margin_pct")
            om = extracted_financials.get("operating_margin_pct")
            metrics["gross_margin"] = gm
            metrics["operating_margin"] = om
            
            # Compute runway if we have cash and burn
            if cash is not None and metrics.get("net_burn") is not None and metrics["net_burn"] > 0:
                runway = cash / metrics["net_burn"]
                metrics["runway_p50"] = runway
                metrics["runway_p10"] = runway * 0.6  # Conservative estimate
                metrics["runway_p90"] = runway * 1.4  # Optimistic estimate
            else:
                metrics["runway_p50"] = None
                metrics["runway_p10"] = None
                metrics["runway_p90"] = None
            
            # Use extracted computed metrics
            metrics["revenue_growth_mom"] = extracted_metrics.get("revenue_growth_mom")
            
            # Convert YoY growth from multiplier to percentage if needed (same logic as financials branch)
            extracted_yoy = extracted_metrics.get("revenue_growth_yoy")
            if extracted_yoy is not None:
                # If value looks like a multiplier (e.g., 1.24 = 24% growth), convert it
                if extracted_yoy > 0 and extracted_yoy < 10:
                    metrics["revenue_growth_yoy"] = (extracted_yoy - 1) * 100
                else:
                    metrics["revenue_growth_yoy"] = extracted_yoy
            else:
                metrics["revenue_growth_yoy"] = None
                
            metrics["burn_multiple"] = extracted_metrics.get("burn_multiple")
            metrics["burn_change"] = 0
            metrics["net_new_arr"] = 0
            
            flags.append({
                "severity": "medium",
                "title": "PDF Data Only",
                "description": "Metrics based on PDF extraction. Connect integrations for real-time data.",
                "metrics_involved": []
            })
        else:
            # No financial data at all
            metrics["monthly_revenue"] = None
            metrics["cash_balance"] = None
            metrics["net_burn"] = None
            metrics["runway_p50"] = None
            metrics["runway_p10"] = None
            metrics["runway_p90"] = None
            metrics["gross_margin"] = None
            metrics["operating_margin"] = None
            metrics["revenue_growth_mom"] = None
            metrics["burn_change"] = 0
            metrics["net_new_arr"] = 0
            
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
        # Use extracted concentration if available
        extracted_top5 = extracted_metrics.get("concentration_top5")
        if extracted_top5 is not None:
            metrics["concentration_top5"] = extracted_top5
            metrics["concentration_top1"] = None  # Individual values not available
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
    
    # Unit Economics Calculations
    # Calculate MRR/ARR from monthly revenue
    mrr = metrics.get("monthly_revenue", 0)
    metrics["mrr"] = mrr
    metrics["arr"] = mrr * 12
    
    # ARPU: Average Revenue Per User (using customer count if available)
    customer_count = len(customers) if customers else None
    if customer_count and customer_count > 0 and mrr:
        metrics["arpu"] = mrr / customer_count
        metrics["customer_count"] = customer_count
    else:
        # Mock values for demo if no customer data
        metrics["arpu"] = mrr / 150 if mrr else None  # Assume 150 customers
        metrics["customer_count"] = 150 if mrr else None
    
    # Churn Rate calculation (mock if no data)
    if customers and len(customers) > 0:
        churned = sum(1 for c in customers if getattr(c, 'churned', False))
        metrics["churn_rate_customer"] = (churned / len(customers)) * 100
        metrics["churn_rate_revenue"] = metrics["churn_rate_customer"] * 1.2  # Revenue churn usually higher
    else:
        # Mock values for demo
        metrics["churn_rate_customer"] = 3.2  # 3.2% monthly churn
        metrics["churn_rate_revenue"] = 4.1  # 4.1% revenue churn
    
    # CAC, LTV, LTV:CAC, Payback calculations
    marketing_spend = metrics.get("payroll", 0) * 0.3 + (metrics.get("opex", 0) * 0.4)  # Estimate marketing
    new_customers_per_month = max(1, (metrics.get("customer_count", 150) or 150) * 0.08)  # ~8% new customers
    
    if marketing_spend > 0 and new_customers_per_month > 0:
        cac = marketing_spend / new_customers_per_month
        metrics["cac"] = round(cac, 2)
    else:
        metrics["cac"] = 5000  # Mock CAC
        cac = 5000
    
    # LTV = ARPU * Gross Margin * (1 / Churn Rate)
    arpu = metrics.get("arpu") or 0
    gm_pct = (metrics.get("gross_margin", 65) or 65) / 100
    monthly_churn = (metrics.get("churn_rate_customer", 3.2) or 3.2) / 100
    
    if arpu > 0 and monthly_churn > 0:
        customer_lifetime_months = 1 / monthly_churn
        ltv = arpu * gm_pct * customer_lifetime_months
        metrics["ltv"] = round(ltv, 2)
    else:
        metrics["ltv"] = 25000  # Mock LTV
        ltv = 25000
    
    # LTV:CAC Ratio
    if cac and cac > 0 and ltv:
        metrics["ltv_cac_ratio"] = round(ltv / cac, 2)
    else:
        metrics["ltv_cac_ratio"] = 5.0
    
    # Payback Period (months to recover CAC)
    if arpu > 0 and cac:
        metrics["payback_months"] = round(cac / (arpu * gm_pct), 1)
    else:
        metrics["payback_months"] = 12
    
    # Net Dollar Retention (NDR)
    if metrics.get("net_revenue_retention") is None:
        metrics["net_revenue_retention"] = 108  # Mock 108% NDR
    
    # Expense Breakdown for burn chart
    if financials:
        latest = financials[0]
        total_expenses = latest.cogs + latest.opex + latest.payroll + latest.other_costs
        metrics["expense_breakdown"] = {
            "cogs": latest.cogs,
            "payroll": latest.payroll,
            "marketing": latest.opex * 0.4,  # Estimate marketing from opex
            "rd": latest.opex * 0.3,  # R&D estimate
            "ga": latest.opex * 0.3 + latest.other_costs,  # G&A
            "total": total_expenses
        }
    else:
        metrics["expense_breakdown"] = None
    
    # Headcount data (mock if not available)
    if financials:
        # Estimate headcount from payroll (assume avg salary)
        avg_salary = 8000  # Monthly
        metrics["headcount"] = max(1, int(metrics.get("payroll", 0) / avg_salary))
        metrics["planned_hires"] = max(0, int(metrics["headcount"] * 0.15))  # 15% growth
        if metrics["headcount"] > 0 and mrr:
            metrics["revenue_per_employee"] = mrr / metrics["headcount"]
        else:
            metrics["revenue_per_employee"] = None
    else:
        metrics["headcount"] = 25
        metrics["planned_hires"] = 4
        metrics["revenue_per_employee"] = mrr / 25 if mrr else None
    
    # Cash flow forecast (12 month projection)
    if financials and len(financials) > 0:
        latest = financials[0]
        monthly_burn = metrics.get("net_burn", 0)
        monthly_rev = metrics.get("monthly_revenue", 0)
        growth_rate = (metrics.get("revenue_growth_mom", 5) or 5) / 100
        
        cash_flow_forecast = []
        current_cash = latest.cash_balance
        for month in range(1, 13):
            projected_revenue = monthly_rev * ((1 + growth_rate) ** month)
            projected_expenses = (latest.cogs + latest.opex + latest.payroll + latest.other_costs) * 1.02 ** month
            net_flow = projected_revenue - projected_expenses
            current_cash += net_flow
            cash_flow_forecast.append({
                "month": month,
                "inflow": round(projected_revenue),
                "outflow": round(projected_expenses),
                "net": round(net_flow),
                "cash_balance": round(current_cash)
            })
        metrics["cash_flow_forecast"] = cash_flow_forecast
    else:
        metrics["cash_flow_forecast"] = None
    
    # Flag for unit economics alerts
    ltv_cac = metrics.get("ltv_cac_ratio", 0)
    if ltv_cac and ltv_cac < 3:
        flags.append({
            "severity": "medium",
            "title": "Low LTV:CAC Ratio",
            "description": f"LTV:CAC ratio of {ltv_cac:.1f}x is below the 3x benchmark",
            "metrics_involved": ["ltv_cac_ratio", "cac", "ltv"]
        })
    
    churn = metrics.get("churn_rate_customer", 0)
    if churn and churn > 5:
        flags.append({
            "severity": "medium",
            "title": "High Customer Churn",
            "description": f"Monthly churn rate of {churn:.1f}% exceeds 5% threshold",
            "metrics_involved": ["churn_rate_customer"]
        })
    
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
    
    burn_mult = metrics.get("burn_multiple")
    if burn_mult is None or burn_mult <= 0:
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
