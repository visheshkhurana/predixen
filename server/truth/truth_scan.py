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
        
        # Include all expense components in total_costs, including marketing_expense
        marketing_expense = getattr(latest, 'marketing_expense', None) or 0
        total_costs = latest.cogs + latest.opex + latest.payroll + latest.other_costs + marketing_expense
        gross_profit = latest.revenue - latest.cogs
        
        metrics["gross_margin"] = (gross_profit / latest.revenue * 100) if latest.revenue > 0 else 0
        metrics["operating_margin"] = ((latest.revenue - total_costs) / latest.revenue * 100) if latest.revenue > 0 else 0
        
        net_burn = total_costs - latest.revenue
        metrics["net_burn"] = net_burn
        metrics["is_profitable"] = net_burn < 0
        
        # Use user-entered growth rate if available, otherwise calculate from historical data
        user_entered_growth = getattr(latest, 'mom_growth', None)
        
        if user_entered_growth is not None and user_entered_growth != 0:
            # Prefer user-entered growth rate
            metrics["revenue_growth_mom"] = user_entered_growth
        elif len(financials) >= 2:
            prev = financials[1]
            if prev.revenue > 0:
                metrics["revenue_growth_mom"] = ((latest.revenue - prev.revenue) / prev.revenue) * 100
            else:
                metrics["revenue_growth_mom"] = 0
        else:
            metrics["revenue_growth_mom"] = 0
        
        if len(financials) >= 2:
            prev = financials[1]
            prev_marketing = getattr(prev, 'marketing_expense', None) or 0
            prev_burn = (prev.cogs + prev.opex + prev.payroll + prev.other_costs + prev_marketing) - prev.revenue
            burn_change = net_burn - prev_burn
            metrics["burn_change"] = burn_change
            
            net_new_arr = (latest.revenue - prev.revenue) * 12
            metrics["net_new_arr"] = net_new_arr
        else:
            # Only set growth to 0 if not already set from user input
            if metrics.get("revenue_growth_mom") is None:
                metrics["revenue_growth_mom"] = 0
            metrics["burn_change"] = 0
            metrics["net_new_arr"] = 0
        
        if len(financials) >= 12:
            prev_year = financials[11]
            if prev_year.revenue > 0:
                metrics["revenue_growth_yoy"] = ((latest.revenue - prev_year.revenue) / prev_year.revenue) * 100
            else:
                metrics["revenue_growth_yoy"] = 0
        elif len(financials) >= 2:
            mom_growth = metrics.get("revenue_growth_mom", 0)
            metrics["revenue_growth_yoy"] = ((1 + mom_growth/100) ** 12 - 1) * 100
        else:
            metrics["revenue_growth_yoy"] = 0
        
        net_new_arr = metrics.get("net_new_arr", 0)
        if net_burn > 0:
            if net_new_arr > 0:
                metrics["burn_multiple"] = round(net_burn / net_new_arr, 2)
            else:
                metrics["burn_multiple"] = None
            
            if latest.cash_balance and latest.cash_balance > 0:
                runway_months = latest.cash_balance / net_burn
                metrics["runway_p50"] = round(runway_months, 1)
                metrics["runway_p10"] = round(runway_months * 0.7, 1)
                metrics["runway_p90"] = round(runway_months * 1.4, 1)
            else:
                metrics["runway_p50"] = 0
                metrics["runway_p10"] = 0
                metrics["runway_p90"] = 0
            metrics["runway_sustainable"] = False
        else:
            metrics["burn_multiple"] = 0
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
    
    # CAC, LTV, LTV:CAC, Payback calculations with sensibility checks
    marketing_spend = metrics.get("payroll", 0) * 0.3 + (metrics.get("opex", 0) * 0.4)  # Estimate marketing
    new_customers_per_month = max(1, (metrics.get("customer_count", 150) or 150) * 0.08)  # ~8% new customers
    
    if marketing_spend > 0 and new_customers_per_month > 0:
        cac = marketing_spend / new_customers_per_month
        # CAC floor: minimum $100 for SaaS, max $50k for enterprise
        cac = max(100, min(cac, 50000))
        metrics["cac"] = round(cac, 2)
    else:
        metrics["cac"] = 500  # Reasonable default CAC for SaaS
        cac = 500
    
    # LTV = ARPU * Gross Margin * (1 / Churn Rate)
    arpu = metrics.get("arpu") or 0
    gm_pct = (metrics.get("gross_margin", 65) or 65) / 100
    monthly_churn = (metrics.get("churn_rate_customer", 3.2) or 3.2) / 100
    # Cap customer lifetime at 60 months (5 years) to prevent extreme LTV values
    monthly_churn = max(monthly_churn, 0.0167)  # Minimum 1.67% monthly = 60 month lifetime cap
    
    if arpu > 0 and monthly_churn > 0:
        customer_lifetime_months = min(1 / monthly_churn, 60)  # Cap at 60 months
        ltv = arpu * gm_pct * customer_lifetime_months
        # LTV floor and ceiling for SaaS: $500 - $500k
        ltv = max(500, min(ltv, 500000))
        metrics["ltv"] = round(ltv, 2)
    else:
        metrics["ltv"] = 3000  # Reasonable default LTV
        ltv = 3000
    
    # LTV:CAC Ratio with sensibility bounds
    if cac and cac > 0 and ltv:
        ltv_cac = ltv / cac
        # Cap LTV:CAC between 0.5x and 20x (realistic SaaS range)
        ltv_cac = max(0.5, min(ltv_cac, 20.0))
        metrics["ltv_cac_ratio"] = round(ltv_cac, 2)
    else:
        metrics["ltv_cac_ratio"] = 5.0
    
    # Payback Period (months to recover CAC) with sensibility bounds
    if arpu > 0 and cac:
        payback = cac / (arpu * gm_pct)
        # Cap payback between 3 and 36 months (realistic SaaS range)
        payback = max(3, min(payback, 36))
        metrics["payback_months"] = round(payback, 1)
    else:
        metrics["payback_months"] = 12
    
    # Net Dollar Retention (NDR)
    if metrics.get("net_revenue_retention") is None:
        metrics["net_revenue_retention"] = 108  # Mock 108% NDR
    
    # Expense Breakdown for burn chart
    # Use actual user-entered values - show exactly what user entered
    if financials:
        latest = financials[0]
        
        # Get actual values from FinancialRecord
        cogs_val = latest.cogs or 0
        payroll_val = latest.payroll or 0
        marketing_val = getattr(latest, 'marketing_expense', None) or 0
        operating_val = latest.opex or 0  # User's "operating" expenses
        other_val = latest.other_costs or 0
        
        # Calculate total from actual entered values
        total_expenses = cogs_val + payroll_val + marketing_val + operating_val + other_val
        
        # Show exact user-entered categories matching Data Input form:
        # payroll, marketing, operating, cogs, other
        metrics["expense_breakdown"] = {
            "cogs": cogs_val,
            "payroll": payroll_val,
            "marketing": marketing_val,
            "operating": operating_val,  # User's actual "operating" value
            "other": other_val,          # User's actual "other" value
            "total": total_expenses
        }
    else:
        metrics["expense_breakdown"] = None
    
    # Headcount data - use actual stored value if available
    if financials:
        latest = financials[0]
        # Use actual headcount from FinancialRecord if saved, otherwise estimate from payroll
        stored_headcount = getattr(latest, 'headcount', None)
        if stored_headcount and stored_headcount > 0:
            metrics["headcount"] = stored_headcount
        else:
            # Fallback: estimate from payroll (assume avg salary)
            avg_salary = 8000  # Monthly
            metrics["headcount"] = max(1, int(metrics.get("payroll", 0) / avg_salary))
        
        metrics["planned_hires"] = 0  # Don't assume planned hires - user should enter this
        if metrics["headcount"] > 0 and mrr:
            metrics["revenue_per_employee"] = mrr / metrics["headcount"]
        else:
            metrics["revenue_per_employee"] = None
    else:
        metrics["headcount"] = None
        metrics["planned_hires"] = 0
        metrics["revenue_per_employee"] = None
    
    # Cash flow forecast (12 month projection)
    if financials and len(financials) > 0:
        latest = financials[0]
        monthly_burn = metrics.get("net_burn", 0)
        monthly_rev = metrics.get("monthly_revenue", 0)
        growth_rate = (metrics.get("revenue_growth_mom", 5) or 5) / 100
        
        # Include marketing_expense in total monthly expenses
        marketing_exp = getattr(latest, 'marketing_expense', None) or 0
        base_expenses = latest.cogs + latest.opex + latest.payroll + latest.other_costs + marketing_exp
        
        cash_flow_forecast = []
        current_cash = latest.cash_balance
        for month in range(1, 13):
            projected_revenue = monthly_rev * ((1 + growth_rate) ** month)
            projected_expenses = base_expenses * 1.02 ** month
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
    """
    Calculate data confidence score based on data completeness and quality.
    Score ranges from 0-100 and updates dynamically based on available data.
    """
    score = 0
    
    if has_financials:
        # Base score for having any financial data
        score += 25
        
        # Additional points for having key metrics
        if metrics.get("monthly_revenue", 0) > 0:
            score += 10
        if metrics.get("cash_balance", 0) > 0:
            score += 10
        if metrics.get("revenue_growth_mom") is not None and metrics.get("revenue_growth_mom") != 0:
            score += 5
        
        # Points for expense breakdown completeness
        expense_breakdown = metrics.get("expense_breakdown", {})
        if expense_breakdown:
            expense_fields_filled = sum(1 for v in [
                expense_breakdown.get("cogs", 0),
                expense_breakdown.get("payroll", 0),
                expense_breakdown.get("marketing", 0),
                expense_breakdown.get("operating", 0),
                expense_breakdown.get("other", 0),
            ] if v > 0)
            score += min(15, expense_fields_filled * 3)  # Up to 15 points for all 5 categories
        
        # Points for having gross margin
        if metrics.get("gross_margin") is not None:
            score += 5
    
    if has_transactions:
        score += 15
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
