from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
from server.models.user import User
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.models.customer import CustomerRecord
from server.models.transaction import TransactionRecord
from server.models.truth_scan import TruthScan
from server.models.scenario import Scenario
from server.models.simulation_run import SimulationRun
from server.models.decision import Decision
from server.core.security import get_password_hash

def seed_demo_data(db: Session):
    existing = db.query(User).filter(User.email == "demo@predixen.ai").first()
    if existing:
        return existing
    
    demo_user = User(
        email="demo@predixen.ai",
        password_hash=get_password_hash("demo123")
    )
    db.add(demo_user)
    db.commit()
    db.refresh(demo_user)
    
    demo_company = Company(
        user_id=demo_user.id,
        name="TechFlow Analytics",
        website="https://techflow.ai",
        industry="general_saas",
        stage="seed",
        currency="USD"
    )
    db.add(demo_company)
    db.commit()
    db.refresh(demo_company)
    
    base_date = datetime.now() - timedelta(days=365)
    revenue = 15000
    expenses = 45000
    cash = 800000
    
    for i in range(12):
        month_date = base_date + timedelta(days=30 * i)
        growth_rate = 1.08 + (0.03 * (i / 12))
        revenue = revenue * growth_rate
        expenses = expenses * 1.02
        cash = cash - (expenses - revenue)
        
        fin_record = FinancialRecord(
            company_id=demo_company.id,
            period_start=month_date.date(),
            period_end=(month_date + timedelta(days=29)).date(),
            revenue=round(revenue, 2),
            cogs=round(revenue * 0.25, 2),
            opex=round(expenses * 0.4, 2),
            payroll=round(expenses * 0.5, 2),
            other_costs=round(expenses * 0.1, 2),
            cash_balance=round(max(cash, 50000), 2)
        )
        db.add(fin_record)
    
    customer_names = [
        "Acme Corp", "GlobalTech", "InnovateCo", "DataDriven Inc", "CloudFirst",
        "ScaleUp Labs", "Digital Ventures", "NextGen Solutions", "TechPioneers", "FutureSoft",
        "SmartBiz", "GrowthHQ", "VelocityTech", "PeakPerformance", "StrategyWorks",
        "InsightHub", "ConnectPro", "StreamLine", "OptimizeNow", "ProgressiveTech"
    ]
    
    for i, name in enumerate(customer_names):
        start_date = base_date + timedelta(days=i * 15)
        
        customer = CustomerRecord(
            company_id=demo_company.id,
            customer_id=f"CUST-{1000 + i}",
            segment="enterprise" if i < 5 else "mid_market" if i < 12 else "smb",
            signup_date=start_date.date(),
            region="North America" if i % 3 == 0 else "Europe" if i % 3 == 1 else "APAC",
            plan="enterprise" if i < 5 else "pro" if i < 12 else "starter"
        )
        db.add(customer)
    
    for i in range(60):
        txn_date = base_date + timedelta(days=i * 6)
        txn = TransactionRecord(
            company_id=demo_company.id,
            txn_date=txn_date.date(),
            customer_id=f"CUST-{1000 + (i % 20)}",
            product="Platform License",
            amount=round(500 + (i * 50) + (100 * (i % 5)), 2),
            cost=round(100 + (i * 10), 2),
            channel="direct" if i % 2 == 0 else "partner"
        )
        db.add(txn)
    
    db.commit()
    
    truth_outputs = {
        "metrics": {
            "mrr": {"value": 45000, "benchmark_percentile": 65},
            "arr": {"value": 540000, "benchmark_percentile": 60},
            "revenue_growth_mom": {"value": 12.5, "benchmark_percentile": 72},
            "gross_margin": {"value": 75.0, "benchmark_percentile": 68},
            "burn_multiple": {"value": 1.8, "benchmark_percentile": 58},
            "runway_months": {"value": 16.5, "benchmark_percentile": 55},
            "net_revenue_retention": {"value": 108, "benchmark_percentile": 70},
            "logo_retention_12m": {"value": 85, "benchmark_percentile": 62},
            "concentration_top5": {"value": 32, "benchmark_percentile": 45},
            "ltv_cac_ratio": {"value": 3.2, "benchmark_percentile": 65},
            "cac_payback_months": {"value": 8, "benchmark_percentile": 55},
            "magic_number": {"value": 0.85, "benchmark_percentile": 60},
            "rule_of_40": {"value": 35, "benchmark_percentile": 52},
            "quick_ratio": {"value": 2.8, "benchmark_percentile": 58},
            "arpu": {"value": 2250, "benchmark_percentile": 70},
            "expansion_rate": {"value": 15, "benchmark_percentile": 65},
            "contraction_rate": {"value": 3, "benchmark_percentile": 72},
            "gross_churn_rate": {"value": 2.5, "benchmark_percentile": 68},
            "net_churn_rate": {"value": -1.2, "benchmark_percentile": 75},
            "customer_count": {"value": 20, "benchmark_percentile": 50},
            "new_customers_mom": {"value": 3, "benchmark_percentile": 55},
            "churned_customers_mom": {"value": 1, "benchmark_percentile": 60},
            "avg_contract_value": {"value": 27000, "benchmark_percentile": 62},
            "sales_efficiency": {"value": 0.65, "benchmark_percentile": 58}
        },
        "data_confidence_score": 78,
        "quality_of_growth_index": 72,
        "benchmark_summary": {
            "above_median_count": 16,
            "below_median_count": 8,
            "top_quartile_count": 5
        },
        "flags": [
            {"type": "warning", "metric": "concentration_top5", "message": "Revenue concentration in top 5 customers is high (32%)"},
            {"type": "positive", "metric": "net_churn_rate", "message": "Negative net churn indicates strong expansion"}
        ]
    }
    
    truth_scan = TruthScan(
        company_id=demo_company.id,
        outputs_json=truth_outputs,
        data_confidence_score=78.0,
        quality_of_growth_index=72.0
    )
    db.add(truth_scan)
    db.commit()
    db.refresh(truth_scan)
    
    scenario = Scenario(
        company_id=demo_company.id,
        name="Current Trajectory",
        pricing_change_pct=0,
        growth_uplift_pct=0,
        burn_reduction_pct=0,
        fundraise_month=None,
        fundraise_amount=0,
        gross_margin_delta_pct=0
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    sim_outputs = {
        "runway": {"p10": 10, "p50": 16.5, "p90": 24},
        "survival": {
            "12m": 82,
            "18m": 65,
            "24m": 48,
            "curve": [
                {"month": 0, "probability": 100},
                {"month": 3, "probability": 98},
                {"month": 6, "probability": 94},
                {"month": 9, "probability": 88},
                {"month": 12, "probability": 82},
                {"month": 15, "probability": 72},
                {"month": 18, "probability": 65},
                {"month": 21, "probability": 55},
                {"month": 24, "probability": 48}
            ]
        },
        "bands": {
            "revenue": [
                {"month": i, "p10": 45000 * (1.05 ** i), "p50": 45000 * (1.10 ** i), "p90": 45000 * (1.15 ** i)}
                for i in range(25)
            ],
            "cash": [
                {"month": i, "p10": max(50000, 500000 - (i * 30000)), "p50": max(100000, 600000 - (i * 25000)), "p90": max(200000, 700000 - (i * 18000))}
                for i in range(25)
            ]
        },
        "summary": {
            "revenue_18m_median": 250000,
            "cash_18m_median": 150000,
            "default_probability": 0.35
        }
    }
    
    sim_run = SimulationRun(
        scenario_id=scenario.id,
        n_sims=1000,
        outputs_json=sim_outputs
    )
    db.add(sim_run)
    db.commit()
    db.refresh(sim_run)
    
    decisions_output = {
        "recommendations": [
            {
                "rank": 1,
                "action_id": "reduce_burn_15",
                "title": "Reduce Burn by 15%",
                "category": "cost_optimization",
                "impact_summary": "Extends runway by 4.2 months, improves survival probability to 78% at 18 months",
                "confidence": 0.85,
                "effort": "medium",
                "timeline": "2-4 weeks",
                "details": {
                    "runway_delta": 4.2,
                    "survival_18m_delta": 13,
                    "suggested_cuts": ["Reduce cloud spend", "Consolidate tools", "Defer non-critical hires"]
                }
            },
            {
                "rank": 2,
                "action_id": "price_increase_10",
                "title": "Implement 10% Price Increase",
                "category": "revenue_optimization",
                "impact_summary": "Increases MRR by $4,500/mo with minimal churn risk given strong NRR",
                "confidence": 0.72,
                "effort": "low",
                "timeline": "1-2 weeks",
                "details": {
                    "mrr_delta": 4500,
                    "expected_churn_impact": -0.5,
                    "target_segment": "enterprise"
                }
            },
            {
                "rank": 3,
                "action_id": "bridge_round",
                "title": "Raise Bridge Round",
                "category": "fundraising",
                "impact_summary": "Secure $500K-$750K bridge to extend runway to 24+ months",
                "confidence": 0.65,
                "effort": "high",
                "timeline": "6-12 weeks",
                "details": {
                    "target_amount": 600000,
                    "runway_extension": 10,
                    "dilution_estimate": "8-12%"
                }
            }
        ],
        "context": {
            "current_runway": 16.5,
            "survival_18m": 65,
            "primary_risk": "cash_runway",
            "growth_trajectory": "healthy"
        }
    }
    
    decision = Decision(
        simulation_run_id=sim_run.id,
        company_id=demo_company.id,
        recommended_actions_json=decisions_output
    )
    db.add(decision)
    db.commit()
    
    return demo_user
