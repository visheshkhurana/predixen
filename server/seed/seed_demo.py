from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import logging
from server.models.user import User
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.models.customer import CustomerRecord
from server.models.transaction import TransactionRecord
from server.models.truth_scan import TruthScan
from server.models.scenario import Scenario
from server.models.simulation_run import SimulationRun
from server.models.decision import Decision
from server.models.team_member import TeamMember
from server.models.fundraising import CompanyCapTable, FundraisingRound
from server.models.company_source import CompanyAlert
from server.models.conversation import Conversation, ConversationMessage
from server.models.metric_definition import MetricDefinition
from server.models.metric_value import MetricValue
from server.models.company_decision import CompanyScenario, CompanyDecision
from server.models.dashboard import Dashboard, DashboardWidget
from server.models.fundraising import Investor, InvestorPipeline
from server.core.security import get_password_hash

logger = logging.getLogger(__name__)

DEMO_SEED_VERSION = 3


def _ensure_connector_metadata(db: Session, company):
    last_sync = (datetime.now() - timedelta(hours=2)).isoformat()
    connectors = {
        "quickbooks": {
            "connected": True,
            "last_sync": last_sync,
            "records_synced": 847,
            "last_error": None,
        },
        "hubspot": {
            "connected": True,
            "last_sync": last_sync,
            "records_synced": 234,
            "last_error": None,
        },
        "stripe": {
            "connected": True,
            "last_sync": last_sync,
            "records_synced": 1256,
            "last_error": None,
        },
        "razorpayx_payroll": {
            "connected": True,
            "last_sync": last_sync,
            "records_synced": 156,
            "last_error": None,
        },
        "google_sheets": {
            "connected": True,
            "last_sync": last_sync,
            "records_synced": 89,
            "last_error": None,
        },
    }
    metadata = company.metadata_json or {}
    if metadata.get("connectors") != connectors:
        metadata["connectors"] = connectors
        company.metadata_json = metadata
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(company, "metadata_json")
        db.commit()
        logger.info("Updated demo company connector metadata")


def seed_demo_data(db: Session):
    logger.info("Starting demo data seeding...")
    existing = db.query(User).filter(User.email == "demo@predixen.ai").first()
    if existing:
        demo_user = existing
        if demo_user.role != "owner":
            demo_user.role = "owner"
            db.commit()
        company = db.query(Company).filter(Company.user_id == demo_user.id).first()
        if company:
            demo_company = company
            if demo_company.name != "TechFlow Analytics":
                demo_company.name = "TechFlow Analytics"
                demo_company.industry = "saas"
                demo_company.stage = "series_a"
                db.commit()
                logger.info("Reset demo company name to TechFlow Analytics")
            cap_table_exists = db.query(CompanyCapTable).filter(CompanyCapTable.company_id == company.id).first()
            if cap_table_exists:
                logger.info("Demo data v2 already exists, ensuring v3+ data")
                _seed_company_scenarios(db, demo_company)
                _seed_dashboard_widgets(db, demo_company)
                _seed_investors_pipeline(db, demo_company)
                _seed_company_decisions(db, demo_company)
                _ensure_connector_metadata(db, demo_company)
                seed_team_members(db)
                return demo_user
            existing_scenario = db.query(Scenario).filter(Scenario.company_id == company.id).first()
            if existing_scenario:
                _seed_extended_demo_data(db, demo_company, demo_user)
                _ensure_connector_metadata(db, demo_company)
                seed_team_members(db)
                logger.info("Demo data extended successfully")
                return demo_user
        else:
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
    else:
        demo_user = User(
            email="demo@predixen.ai",
            password_hash=get_password_hash("demo123"),
            role="owner"
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
        outputs_json=truth_outputs
    )
    db.add(truth_scan)
    db.commit()
    db.refresh(truth_scan)
    
    scenario = Scenario(
        company_id=demo_company.id,
        name="Current Trajectory",
        inputs_json={
            "pricing_change_pct": 0,
            "growth_uplift_pct": 0,
            "burn_reduction_pct": 0,
            "fundraise_month": None,
            "fundraise_amount": 0,
            "gross_margin_delta_pct": 0
        }
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
            "end_cash_p50": 150000,
            "monthly_burn_p50": 55000,
            "runway_p50": 16.5,
            "runway_p10": 10,
            "runway_p90": 24,
            "survival_12m": 82,
            "survival_18m": 65,
            "default_probability": 0.35
        }
    }
    
    sim_run = SimulationRun(
        scenario_id=scenario.id,
        n_sims=1000,
        outputs_json=sim_outputs,
        data_snapshot_id="demo-snapshot-v1",
        status="completed",
        completed_at=datetime.utcnow()
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
        recommended_actions_json=decisions_output
    )
    db.add(decision)
    db.commit()

    _seed_extended_demo_data(db, demo_company, demo_user)
    
    seed_team_members(db)

    logger.info("Demo data seeding completed successfully")
    return demo_user


def _seed_extended_demo_data(db: Session, demo_company, demo_user):
    _seed_additional_scenarios(db, demo_company)
    _seed_fundraising(db, demo_company)
    _seed_alerts(db, demo_company)
    _seed_conversations(db, demo_company, demo_user)
    _seed_metric_definitions(db, demo_company)
    _seed_company_scenarios(db, demo_company)
    _seed_dashboard_widgets(db, demo_company)
    _seed_investors_pipeline(db, demo_company)
    _seed_company_decisions(db, demo_company)
    logger.info("Extended demo data seeded successfully")


def _seed_additional_scenarios(db: Session, demo_company):
    existing = db.query(Scenario).filter(
        Scenario.company_id == demo_company.id,
        Scenario.name == "Aggressive Growth"
    ).first()
    if existing:
        return

    scenarios_data = [
        {
            "name": "Aggressive Growth",
            "inputs": {
                "pricing_change_pct": 5,
                "growth_uplift_pct": 25,
                "burn_reduction_pct": -10,
                "fundraise_month": 3,
                "fundraise_amount": 2000000,
                "gross_margin_delta_pct": 2
            },
            "sim_outputs": {
                "runway": {"p10": 8, "p50": 14, "p90": 22},
                "survival": {
                    "12m": 75, "18m": 58, "24m": 42,
                    "curve": [
                        {"month": 0, "probability": 100},
                        {"month": 3, "probability": 96},
                        {"month": 6, "probability": 90},
                        {"month": 9, "probability": 82},
                        {"month": 12, "probability": 75},
                        {"month": 15, "probability": 65},
                        {"month": 18, "probability": 58},
                        {"month": 21, "probability": 48},
                        {"month": 24, "probability": 42}
                    ]
                },
                "bands": {
                    "revenue": [{"month": i, "p10": 45000*(1.08**i), "p50": 45000*(1.15**i), "p90": 45000*(1.22**i)} for i in range(25)],
                    "cash": [{"month": i, "p10": max(30000, 400000-(i*35000)), "p50": max(80000, 550000-(i*28000)), "p90": max(150000, 700000-(i*20000))} for i in range(25)]
                },
                "summary": {"revenue_18m_median": 380000, "cash_18m_median": 120000, "end_cash_p50": 120000, "monthly_burn_p50": 70000, "runway_p50": 14, "runway_p10": 8, "runway_p90": 22, "survival_12m": 75, "survival_18m": 58, "default_probability": 0.42}
            }
        },
        {
            "name": "Cost Optimization",
            "inputs": {
                "pricing_change_pct": 0,
                "growth_uplift_pct": 5,
                "burn_reduction_pct": 20,
                "fundraise_month": None,
                "fundraise_amount": 0,
                "gross_margin_delta_pct": 5
            },
            "sim_outputs": {
                "runway": {"p10": 14, "p50": 22, "p90": 30},
                "survival": {
                    "12m": 92, "18m": 82, "24m": 68,
                    "curve": [
                        {"month": 0, "probability": 100},
                        {"month": 3, "probability": 99},
                        {"month": 6, "probability": 97},
                        {"month": 9, "probability": 95},
                        {"month": 12, "probability": 92},
                        {"month": 15, "probability": 88},
                        {"month": 18, "probability": 82},
                        {"month": 21, "probability": 74},
                        {"month": 24, "probability": 68}
                    ]
                },
                "bands": {
                    "revenue": [{"month": i, "p10": 45000*(1.04**i), "p50": 45000*(1.08**i), "p90": 45000*(1.12**i)} for i in range(25)],
                    "cash": [{"month": i, "p10": max(80000, 550000-(i*20000)), "p50": max(150000, 650000-(i*15000)), "p90": max(250000, 750000-(i*10000))} for i in range(25)]
                },
                "summary": {"revenue_18m_median": 200000, "cash_18m_median": 280000, "end_cash_p50": 280000, "monthly_burn_p50": 44000, "runway_p50": 22, "runway_p10": 14, "runway_p90": 30, "survival_12m": 92, "survival_18m": 82, "default_probability": 0.18}
            }
        },
        {
            "name": "Series A Fundraise",
            "inputs": {
                "pricing_change_pct": 10,
                "growth_uplift_pct": 15,
                "burn_reduction_pct": 0,
                "fundraise_month": 6,
                "fundraise_amount": 5000000,
                "gross_margin_delta_pct": 3
            },
            "sim_outputs": {
                "runway": {"p10": 18, "p50": 28, "p90": 36},
                "survival": {
                    "12m": 95, "18m": 90, "24m": 85,
                    "curve": [
                        {"month": 0, "probability": 100},
                        {"month": 3, "probability": 99},
                        {"month": 6, "probability": 98},
                        {"month": 9, "probability": 97},
                        {"month": 12, "probability": 95},
                        {"month": 15, "probability": 92},
                        {"month": 18, "probability": 90},
                        {"month": 21, "probability": 88},
                        {"month": 24, "probability": 85}
                    ]
                },
                "bands": {
                    "revenue": [{"month": i, "p10": 45000*(1.06**i), "p50": 45000*(1.12**i), "p90": 45000*(1.18**i)} for i in range(25)],
                    "cash": [{"month": i, "p10": max(200000, 800000-(i*15000)), "p50": max(400000, 1200000-(i*10000)), "p90": max(600000, 1600000-(i*5000))} for i in range(25)]
                },
                "summary": {"revenue_18m_median": 320000, "cash_18m_median": 800000, "end_cash_p50": 800000, "monthly_burn_p50": 55000, "runway_p50": 28, "runway_p10": 18, "runway_p90": 36, "survival_12m": 95, "survival_18m": 90, "default_probability": 0.10}
            }
        }
    ]

    for s_data in scenarios_data:
        scenario = Scenario(
            company_id=demo_company.id,
            name=s_data["name"],
            inputs_json=s_data["inputs"]
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)

        sim_run = SimulationRun(
            scenario_id=scenario.id,
            n_sims=1000,
            outputs_json=s_data["sim_outputs"],
            data_snapshot_id="demo-snapshot-v1",
            status="completed",
            completed_at=datetime.utcnow()
        )
        db.add(sim_run)
        db.commit()

    logger.info("Seeded 3 additional scenarios")


def _seed_fundraising(db: Session, demo_company):
    existing = db.query(CompanyCapTable).filter(CompanyCapTable.company_id == demo_company.id).first()
    if existing:
        return

    cap_table = CompanyCapTable(
        company_id=demo_company.id,
        name="Current Cap Table",
        as_of_date=datetime.now().date(),
        currency="USD",
        cap_table_json={
            "common": [
                {"holder": "Founder 1 - Nikita Luther", "shares": 4000000, "percent": 40.0},
                {"holder": "Founder 2 - Vyshesh K", "shares": 3000000, "percent": 30.0}
            ],
            "preferred": [
                {"series": "Pre-Seed", "holder": "Angel Syndicate", "shares": 500000, "percent": 5.0, "liquidation_pref": "1x non-participating"},
                {"series": "Seed", "holder": "Elevation Capital", "shares": 800000, "percent": 8.0, "liquidation_pref": "1x non-participating"},
                {"series": "Seed", "holder": "Blume Ventures", "shares": 500000, "percent": 5.0, "liquidation_pref": "1x non-participating"}
            ],
            "options": {"pool_percent": 12.0, "allocated_percent": 7.5},
            "notes": [
                {"holder": "Y Combinator", "principal": 125000, "conversion_cap": 2000000, "discount": 0},
                {"holder": "Strategic Angel", "principal": 50000, "conversion_cap": 3000000, "discount": 20}
            ],
            "fully_diluted_shares": 10000000
        }
    )
    db.add(cap_table)

    rounds = [
        FundraisingRound(
            company_id=demo_company.id,
            name="Pre-Seed Round",
            target_raise=250000,
            pre_money=1500000,
            post_money=1750000,
            instrument="safe",
            option_pool_refresh_percent=10.0,
            status="closed",
            use_of_funds_json={
                "Engineering": 40,
                "Product": 25,
                "Operations": 20,
                "Marketing": 15
            }
        ),
        FundraisingRound(
            company_id=demo_company.id,
            name="Seed Round",
            target_raise=1500000,
            pre_money=6000000,
            post_money=7500000,
            instrument="equity",
            option_pool_refresh_percent=12.0,
            status="active",
            use_of_funds_json={
                "Engineering": 45,
                "Sales & Marketing": 25,
                "Product": 15,
                "Operations": 10,
                "Legal & Admin": 5
            }
        ),
        FundraisingRound(
            company_id=demo_company.id,
            name="Series A (Planned)",
            target_raise=5000000,
            pre_money=20000000,
            post_money=25000000,
            instrument="equity",
            option_pool_refresh_percent=10.0,
            status="planned",
            use_of_funds_json={
                "Engineering": 35,
                "Sales & Marketing": 30,
                "Product": 15,
                "Customer Success": 10,
                "Operations": 10
            }
        )
    ]
    db.add_all(rounds)
    db.commit()
    logger.info("Seeded fundraising data (cap table + 3 rounds)")


def _seed_alerts(db: Session, demo_company):
    existing = db.query(CompanyAlert).filter(CompanyAlert.company_id == demo_company.id).first()
    if existing:
        return

    now = datetime.utcnow()
    alerts = [
        CompanyAlert(
            company_id=demo_company.id,
            type="runway_warning",
            severity="warning",
            message="Runway has decreased to 16.5 months. Consider cost optimization or fundraising to extend beyond 18 months.",
            rule_json={"metric": "runway_months", "operator": "lt", "threshold": 18, "current_value": 16.5},
            triggered_at=now - timedelta(hours=6),
            status="open"
        ),
        CompanyAlert(
            company_id=demo_company.id,
            type="burn_rate_spike",
            severity="critical",
            message="Monthly burn rate increased 22% over last 3 months ($45K to $55K). Infrastructure costs up 40%.",
            rule_json={"metric": "burn_rate", "operator": "gt", "threshold": 50000, "current_value": 55000},
            triggered_at=now - timedelta(hours=12),
            status="open"
        ),
        CompanyAlert(
            company_id=demo_company.id,
            type="concentration_risk",
            severity="warning",
            message="Top 5 customers represent 32% of revenue. Losing any single enterprise client would impact MRR by 6-8%.",
            rule_json={"metric": "concentration_top5", "operator": "gt", "threshold": 30, "current_value": 32},
            triggered_at=now - timedelta(days=1),
            status="open"
        ),
        CompanyAlert(
            company_id=demo_company.id,
            type="growth_milestone",
            severity="info",
            message="MRR crossed $45,000 milestone. Year-over-year growth rate at 12.5% month-over-month.",
            rule_json={"metric": "mrr", "operator": "gt", "threshold": 45000, "current_value": 45000},
            triggered_at=now - timedelta(days=2),
            status="open"
        ),
        CompanyAlert(
            company_id=demo_company.id,
            type="churn_improvement",
            severity="info",
            message="Net churn rate is negative (-1.2%), indicating expansion revenue exceeds churned revenue.",
            rule_json={"metric": "net_churn_rate", "operator": "lt", "threshold": 0, "current_value": -1.2},
            triggered_at=now - timedelta(days=3),
            status="open"
        ),
        CompanyAlert(
            company_id=demo_company.id,
            type="cac_payback_warning",
            severity="warning",
            message="CAC payback period is 8 months. Target below 6 months for efficient growth.",
            rule_json={"metric": "cac_payback_months", "operator": "gt", "threshold": 6, "current_value": 8},
            triggered_at=now - timedelta(days=5),
            status="open"
        ),
        CompanyAlert(
            company_id=demo_company.id,
            type="data_quality",
            severity="info",
            message="Data confidence score improved from 72% to 78% after latest financial data upload.",
            rule_json={"metric": "data_confidence_score", "operator": "gte", "threshold": 75, "current_value": 78},
            triggered_at=now - timedelta(days=7),
            resolved_at=now - timedelta(days=6),
            status="resolved"
        )
    ]
    db.add_all(alerts)
    db.commit()
    logger.info("Seeded 7 demo alerts")


def _seed_conversations(db: Session, demo_company, demo_user):
    existing = db.query(Conversation).filter(Conversation.company_id == demo_company.id).first()
    if existing:
        return

    now = datetime.utcnow()

    conv1 = Conversation(
        company_id=demo_company.id,
        user_id=demo_user.id,
        title="Runway analysis and cost optimization",
        context_metadata={"topic": "runway", "mode": "EXPLAIN"},
        is_active=True,
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(days=2)
    )
    db.add(conv1)
    db.commit()
    db.refresh(conv1)

    conv1_messages = [
        ConversationMessage(
            conversation_id=conv1.id, role="user",
            content="What's our current runway and how can we extend it?",
            intent_type="EXPLAIN", created_at=now - timedelta(days=2, hours=1)
        ),
        ConversationMessage(
            conversation_id=conv1.id, role="assistant",
            content="Based on your latest Truth Scan data, your current runway is **16.5 months** (P50 estimate from Monte Carlo simulation with 1,000 iterations).\n\nHere's the breakdown:\n- **Monthly Revenue**: $45,000 MRR (growing at 12.5% MoM)\n- **Monthly Burn**: ~$55,000 (including $22,500 payroll, $18,000 opex, $14,500 other)\n- **Cash Balance**: ~$500,000\n\nTo extend runway, I recommend:\n1. **Reduce burn by 15%** - extends runway by 4.2 months to ~20.7 months\n2. **Implement 10% price increase** - adds $4,500/mo MRR with minimal churn risk\n3. **Consider bridge round** - $500-750K extends to 24+ months\n\n*Source: Simulation Run #1, Current Trajectory scenario, data snapshot from latest Truth Scan (confidence: 78%)*",
            intent_type="EXPLAIN", created_at=now - timedelta(days=2, minutes=59)
        ),
        ConversationMessage(
            conversation_id=conv1.id, role="user",
            content="Which costs should we cut first?",
            intent_type="PLAN", created_at=now - timedelta(days=2, minutes=55)
        ),
        ConversationMessage(
            conversation_id=conv1.id, role="assistant",
            content="Based on your expense breakdown, here are the highest-impact cost reduction opportunities:\n\n**Immediate Wins (Week 1-2):**\n1. **Cloud infrastructure optimization** - Your AWS/GCP spend shows 30% underutilized capacity. Rightsizing and reserved instances could save $3,000-4,000/month\n2. **SaaS tool consolidation** - Audit shows 12 active subscriptions with overlap. Consolidating could save $1,500/month\n\n**Medium-term (Month 1-2):**\n3. **Defer non-critical hire** - Pushing the planned junior dev hire by 3 months saves $8,000/month loaded cost\n4. **Renegotiate vendor contracts** - Annual renewals coming up for 3 vendors\n\n**Impact**: These changes together reduce monthly burn from $55K to ~$47K, extending runway from 16.5 to 20+ months.\n\n*Note: Payroll is 50% of expenses - avoid cuts here as it directly impacts product velocity and your 12.5% MoM growth rate.*",
            intent_type="PLAN", created_at=now - timedelta(days=2, minutes=53)
        ),
    ]
    db.add_all(conv1_messages)

    conv2 = Conversation(
        company_id=demo_company.id,
        user_id=demo_user.id,
        title="Fundraising strategy discussion",
        context_metadata={"topic": "fundraising", "mode": "PLAN"},
        is_active=True,
        created_at=now - timedelta(days=5),
        updated_at=now - timedelta(days=5)
    )
    db.add(conv2)
    db.commit()
    db.refresh(conv2)

    conv2_messages = [
        ConversationMessage(
            conversation_id=conv2.id, role="user",
            content="Should we raise a bridge round or wait for Series A?",
            intent_type="COMPARE", created_at=now - timedelta(days=5, hours=1)
        ),
        ConversationMessage(
            conversation_id=conv2.id, role="assistant",
            content="Great question. Let me compare both paths using your simulation data:\n\n**Bridge Round ($500-750K SAFE):**\n- Extends runway to 24+ months\n- Dilution: 8-12% (at current $6M cap)\n- Timeline: 4-6 weeks to close\n- Survival probability at 18m: improves from 65% to 82%\n\n**Wait for Series A ($3-5M):**\n- Need to hit $80K+ MRR first (currently $45K)\n- Timeline: 6-9 months to be \"Series A ready\"\n- Risk: only 65% survival probability at 18 months with current trajectory\n- Better valuation: $15-25M pre-money vs $6M cap on bridge\n\n**My recommendation**: Raise a **small bridge ($500K SAFE)** now to de-risk, then focus on hitting $80K MRR for a strong Series A in 9-12 months. The bridge buys you time without significant dilution.\n\n*Based on: Monte Carlo P50 projections, Current Trajectory scenario*",
            intent_type="COMPARE", created_at=now - timedelta(days=5, minutes=58)
        ),
        ConversationMessage(
            conversation_id=conv2.id, role="user",
            content="What metrics do VCs look for at Series A for SaaS?",
            intent_type="TEACH", created_at=now - timedelta(days=5, minutes=50)
        ),
        ConversationMessage(
            conversation_id=conv2.id, role="assistant",
            content="Here are the key Series A benchmarks for SaaS and how you compare:\n\n| Metric | Target | Your Current | Status |\n|--------|--------|-------------|--------|\n| ARR | $1-2M | $540K | Need 2-3x growth |\n| MoM Growth | 15-20% | 12.5% | Slightly below |\n| Net Retention | >110% | 108% | Close - focus on expansion |\n| Gross Margin | >70% | 75% | Strong |\n| Burn Multiple | <2x | 1.8x | Good |\n| LTV/CAC | >3x | 3.2x | Solid |\n| Rule of 40 | >40 | 35 | Gap to close |\n\n**Priority areas to improve:**\n1. Accelerate MRR growth to 15%+ MoM\n2. Push NRR above 110% through upselling\n3. Get Rule of 40 above 40 (grow faster or reduce burn)\n\nYou're about 6-9 months away from strong Series A metrics. The bridge gives you the runway to get there.",
            intent_type="TEACH", created_at=now - timedelta(days=5, minutes=48)
        ),
    ]
    db.add_all(conv2_messages)

    conv3 = Conversation(
        company_id=demo_company.id,
        user_id=demo_user.id,
        title="Customer retention deep dive",
        context_metadata={"topic": "retention", "mode": "EXPLAIN"},
        is_active=True,
        created_at=now - timedelta(days=10),
        updated_at=now - timedelta(days=10)
    )
    db.add(conv3)
    db.commit()
    db.refresh(conv3)

    conv3_messages = [
        ConversationMessage(
            conversation_id=conv3.id, role="user",
            content="Why is our customer concentration so high?",
            intent_type="EXPLAIN", created_at=now - timedelta(days=10, hours=1)
        ),
        ConversationMessage(
            conversation_id=conv3.id, role="assistant",
            content="Your top 5 customers account for **32% of revenue**, which is flagged as a concentration risk. Here's why:\n\n**Root Causes:**\n1. **Enterprise-heavy mix**: 5 enterprise clients at $5,400/mo avg vs 15 mid-market/SMB at $1,800/mo avg\n2. **Early-stage pattern**: With only 20 customers, each enterprise client naturally has outsized impact\n3. **Landing strategy worked**: Your enterprise clients expanded significantly (108% NRR)\n\n**Risk Assessment:**\n- Losing your largest client would reduce MRR by ~8% ($3,600/mo)\n- Losing any 2 of top 5 would trigger a critical runway alert\n\n**Mitigation Strategy:**\n1. Accelerate mid-market acquisition (currently 3 new customers/month - target 5+)\n2. Multi-thread relationships in top accounts (reduce single-point-of-failure risk)\n3. Build product stickiness through deeper integrations with enterprise workflows\n\nThe good news: your negative net churn (-1.2%) means existing customers are expanding, so focus on diversifying the acquisition funnel.\n\n*Source: Truth Scan metrics, concentration_top5 = 32%, benchmark percentile: 45th*",
            intent_type="EXPLAIN", created_at=now - timedelta(days=10, minutes=58)
        ),
    ]
    db.add_all(conv3_messages)
    db.commit()
    logger.info("Seeded 3 demo conversations with messages")


def _seed_metric_definitions(db: Session, demo_company):
    existing = db.query(MetricDefinition).filter(
        MetricDefinition.company_id == demo_company.id,
        MetricDefinition.is_system == True
    ).first()
    if existing:
        return

    now = datetime.utcnow()
    metrics = [
        MetricDefinition(
            company_id=demo_company.id, key="mrr", name="Monthly Recurring Revenue",
            description="Total recurring revenue normalized to a monthly period",
            formula="SUM(active_subscriptions.monthly_amount)", source_connector="stripe",
            grain="monthly", unit="USD", format_type="currency", version=1, status="published",
            is_system=True, tags=["revenue", "saas", "core"], owners=["finance"],
            published_at=now - timedelta(days=30)
        ),
        MetricDefinition(
            company_id=demo_company.id, key="arr", name="Annual Recurring Revenue",
            description="MRR multiplied by 12 for annualized view",
            formula="mrr * 12", source_connector="derived",
            grain="monthly", unit="USD", format_type="currency", version=1, status="published",
            is_system=True, dependencies=["mrr"], tags=["revenue", "saas", "core"], owners=["finance"],
            published_at=now - timedelta(days=30)
        ),
        MetricDefinition(
            company_id=demo_company.id, key="burn_rate", name="Monthly Burn Rate",
            description="Net cash consumed per month (expenses minus revenue)",
            formula="total_expenses - total_revenue", source_connector="quickbooks",
            grain="monthly", unit="USD", format_type="currency", version=1, status="published",
            is_system=True, tags=["expenses", "runway", "core"], owners=["finance"],
            published_at=now - timedelta(days=30)
        ),
        MetricDefinition(
            company_id=demo_company.id, key="runway_months", name="Runway (Months)",
            description="Months of cash remaining at current burn rate",
            formula="cash_balance / burn_rate", source_connector="derived",
            grain="monthly", unit="months", format_type="number", version=1, status="published",
            is_system=True, dependencies=["burn_rate"], tags=["runway", "survival", "core"], owners=["finance"],
            published_at=now - timedelta(days=30)
        ),
        MetricDefinition(
            company_id=demo_company.id, key="gross_margin", name="Gross Margin",
            description="Revenue minus COGS as percentage of revenue",
            formula="(revenue - cogs) / revenue * 100", source_connector="quickbooks",
            grain="monthly", unit="%", format_type="percent", version=1, status="published",
            is_system=True, tags=["profitability", "core"], owners=["finance"],
            published_at=now - timedelta(days=30)
        ),
        MetricDefinition(
            company_id=demo_company.id, key="net_revenue_retention", name="Net Revenue Retention",
            description="Revenue retained from existing customers including expansion",
            formula="(beginning_mrr + expansion - contraction - churn) / beginning_mrr * 100",
            source_connector="stripe", grain="monthly", unit="%", format_type="percent",
            version=1, status="published", is_system=True,
            tags=["retention", "growth", "core"], owners=["customer_success"],
            published_at=now - timedelta(days=30)
        ),
        MetricDefinition(
            company_id=demo_company.id, key="ltv_cac_ratio", name="LTV/CAC Ratio",
            description="Customer lifetime value divided by acquisition cost",
            formula="avg_customer_ltv / avg_cac", source_connector="derived",
            grain="monthly", unit="x", format_type="number", version=1, status="published",
            is_system=True, tags=["unit_economics", "core"], owners=["marketing", "finance"],
            published_at=now - timedelta(days=28)
        ),
        MetricDefinition(
            company_id=demo_company.id, key="cac_payback_months", name="CAC Payback Period",
            description="Months required to recoup customer acquisition cost",
            formula="avg_cac / (arpu * gross_margin_pct)", source_connector="derived",
            grain="monthly", unit="months", format_type="number", version=1, status="published",
            is_system=True, dependencies=["gross_margin"], tags=["unit_economics", "efficiency"],
            owners=["marketing"], published_at=now - timedelta(days=28)
        ),
        MetricDefinition(
            company_id=demo_company.id, key="burn_multiple", name="Burn Multiple",
            description="Net burn divided by net new ARR",
            formula="net_burn / net_new_arr", source_connector="derived",
            grain="monthly", unit="x", format_type="number", version=1, status="published",
            is_system=True, tags=["efficiency", "growth"], owners=["finance"],
            published_at=now - timedelta(days=25)
        ),
        MetricDefinition(
            company_id=demo_company.id, key="magic_number", name="Magic Number",
            description="Sales efficiency metric: net new ARR / prior quarter S&M spend",
            formula="net_new_arr_quarter / prior_quarter_sales_marketing", source_connector="derived",
            grain="quarterly", unit="x", format_type="number", version=1, status="published",
            is_system=True, tags=["efficiency", "sales"], owners=["sales"],
            published_at=now - timedelta(days=25)
        ),
        MetricDefinition(
            company_id=demo_company.id, key="customer_count", name="Active Customers",
            description="Total number of active paying customers",
            formula="COUNT(customers WHERE status='active')", source_connector="stripe",
            grain="monthly", unit="customers", format_type="number", version=1, status="published",
            is_system=True, tags=["customers", "core"], owners=["customer_success"],
            published_at=now - timedelta(days=30)
        ),
        MetricDefinition(
            company_id=demo_company.id, key="gross_churn_rate", name="Gross Churn Rate",
            description="Percentage of MRR lost from churned customers",
            formula="churned_mrr / beginning_mrr * 100", source_connector="stripe",
            grain="monthly", unit="%", format_type="percent", version=1, status="published",
            is_system=True, tags=["retention", "churn"], owners=["customer_success"],
            published_at=now - timedelta(days=28)
        ),
        MetricDefinition(
            company_id=demo_company.id, key="pipeline_velocity", name="Pipeline Velocity",
            description="Speed at which deals move through the sales pipeline",
            formula="(opportunities * avg_deal_size * win_rate) / avg_sales_cycle_days",
            source_connector="hubspot", grain="monthly", unit="USD/day", format_type="currency",
            version=1, status="draft", is_system=False,
            tags=["sales", "pipeline"], owners=["sales"],
        ),
        MetricDefinition(
            company_id=demo_company.id, key="engineering_velocity", name="Engineering Velocity",
            description="Story points completed per sprint per engineer",
            formula="total_story_points / (sprint_count * engineer_count)",
            source_connector=None, grain="monthly", unit="pts/eng", format_type="number",
            version=1, status="draft", is_system=False,
            tags=["engineering", "productivity"], owners=["engineering"],
        ),
        MetricDefinition(
            company_id=demo_company.id, key="nps_score", name="Net Promoter Score",
            description="Customer satisfaction and loyalty indicator",
            formula="(promoters - detractors) / total_respondents * 100",
            source_connector=None, grain="quarterly", unit="score", format_type="number",
            version=1, status="draft", is_system=False,
            tags=["customer_satisfaction", "product"], owners=["product"],
        ),
    ]
    db.add_all(metrics)
    db.commit()

    metric_mrr = db.query(MetricDefinition).filter(
        MetricDefinition.company_id == demo_company.id,
        MetricDefinition.key == "mrr"
    ).first()

    if metric_mrr:
        base_date = datetime.now() - timedelta(days=365)
        mrr_val = 15000
        for i in range(12):
            mrr_val = mrr_val * (1.08 + 0.03 * (i / 12))
            period_start = base_date + timedelta(days=30 * i)
            period_end = period_start + timedelta(days=29)
            mv = MetricValue(
                metric_id=metric_mrr.id,
                company_id=demo_company.id,
                value=round(mrr_val, 2),
                period_start=period_start,
                period_end=period_end,
                metric_version=1,
                raw_event_count=20 + i * 2,
                contributing_connectors=["stripe"]
            )
            db.add(mv)
        db.commit()

    logger.info("Seeded 15 metric definitions + MRR values")


def _seed_company_scenarios(db: Session, demo_company):
    existing = db.query(CompanyScenario).filter(
        CompanyScenario.company_id == demo_company.id
    ).first()
    if existing:
        return

    now = datetime.utcnow()
    scenarios = [
        CompanyScenario(
            company_id=demo_company.id,
            name="Current Trajectory",
            assumptions_json={
                "tags": ["baseline"],
                "revenue_growth_rate": 0.125,
                "burn_rate_monthly": 55000,
                "starting_cash": 500000,
                "pricing_change_pct": 0,
                "growth_uplift_pct": 0,
                "burn_reduction_pct": 0,
                "fundraise_month": None,
                "fundraise_amount": 0,
                "gross_margin_delta_pct": 0,
            },
            outputs_json={
                "runway": {"p10": 10, "p50": 16.5, "p90": 24},
                "survival": {
                    "12m": 82, "18m": 65, "24m": 45,
                    "curve": [
                        {"month": 0, "probability": 100}, {"month": 3, "probability": 98},
                        {"month": 6, "probability": 94}, {"month": 9, "probability": 88},
                        {"month": 12, "probability": 82}, {"month": 15, "probability": 72},
                        {"month": 18, "probability": 65}, {"month": 21, "probability": 54},
                        {"month": 24, "probability": 45},
                    ],
                },
                "summary": {
                    "end_cash_p50": 85000, "monthly_burn_p50": 55000,
                    "runway_p50": 16.5, "runway_p10": 10, "runway_p90": 24,
                    "survival_12m": 82, "survival_18m": 65,
                    "revenue_18m_median": 180000, "cash_18m_median": 85000,
                    "default_probability": 0.35,
                },
                "bands": {
                    "revenue": [{"month": i, "p10": round(45000*(1.06**i)), "p50": round(45000*(1.125**i)), "p90": round(45000*(1.18**i))} for i in range(25)],
                    "cash": [{"month": i, "p10": max(0, round(500000 - i*42000)), "p50": max(0, round(500000 - i*30000)), "p90": max(0, round(500000 - i*18000))} for i in range(25)],
                },
            },
            created_at=now - timedelta(days=14),
            updated_at=now - timedelta(days=2),
        ),
        CompanyScenario(
            company_id=demo_company.id,
            name="Aggressive Growth",
            assumptions_json={
                "tags": ["growth", "high-risk"],
                "revenue_growth_rate": 0.20,
                "burn_rate_monthly": 70000,
                "starting_cash": 500000,
                "pricing_change_pct": 5,
                "growth_uplift_pct": 25,
                "burn_reduction_pct": -10,
                "fundraise_month": 3,
                "fundraise_amount": 2000000,
                "gross_margin_delta_pct": 2,
            },
            outputs_json={
                "runway": {"p10": 8, "p50": 14, "p90": 22},
                "survival": {
                    "12m": 75, "18m": 58, "24m": 42,
                    "curve": [
                        {"month": 0, "probability": 100}, {"month": 3, "probability": 96},
                        {"month": 6, "probability": 90}, {"month": 9, "probability": 82},
                        {"month": 12, "probability": 75}, {"month": 15, "probability": 65},
                        {"month": 18, "probability": 58}, {"month": 21, "probability": 48},
                        {"month": 24, "probability": 42},
                    ],
                },
                "summary": {
                    "end_cash_p50": 120000, "monthly_burn_p50": 70000,
                    "runway_p50": 14, "runway_p10": 8, "runway_p90": 22,
                    "survival_12m": 75, "survival_18m": 58,
                    "revenue_18m_median": 380000, "cash_18m_median": 120000,
                    "default_probability": 0.42,
                },
                "bands": {
                    "revenue": [{"month": i, "p10": round(45000*(1.08**i)), "p50": round(45000*(1.15**i)), "p90": round(45000*(1.22**i))} for i in range(25)],
                    "cash": [{"month": i, "p10": max(30000, round(400000 - i*35000)), "p50": max(80000, round(550000 - i*28000)), "p90": max(150000, round(700000 - i*20000))} for i in range(25)],
                },
            },
            created_at=now - timedelta(days=12),
            updated_at=now - timedelta(days=3),
        ),
        CompanyScenario(
            company_id=demo_company.id,
            name="Cost Optimization",
            assumptions_json={
                "tags": ["conservative", "efficiency"],
                "revenue_growth_rate": 0.10,
                "burn_rate_monthly": 44000,
                "starting_cash": 500000,
                "pricing_change_pct": 0,
                "growth_uplift_pct": 5,
                "burn_reduction_pct": 20,
                "fundraise_month": None,
                "fundraise_amount": 0,
                "gross_margin_delta_pct": 5,
            },
            outputs_json={
                "runway": {"p10": 14, "p50": 22, "p90": 30},
                "survival": {
                    "12m": 92, "18m": 82, "24m": 68,
                    "curve": [
                        {"month": 0, "probability": 100}, {"month": 3, "probability": 99},
                        {"month": 6, "probability": 97}, {"month": 9, "probability": 95},
                        {"month": 12, "probability": 92}, {"month": 15, "probability": 88},
                        {"month": 18, "probability": 82}, {"month": 21, "probability": 74},
                        {"month": 24, "probability": 68},
                    ],
                },
                "summary": {
                    "end_cash_p50": 280000, "monthly_burn_p50": 44000,
                    "runway_p50": 22, "runway_p10": 14, "runway_p90": 30,
                    "survival_12m": 92, "survival_18m": 82,
                    "revenue_18m_median": 200000, "cash_18m_median": 280000,
                    "default_probability": 0.18,
                },
                "bands": {
                    "revenue": [{"month": i, "p10": round(45000*(1.04**i)), "p50": round(45000*(1.08**i)), "p90": round(45000*(1.12**i))} for i in range(25)],
                    "cash": [{"month": i, "p10": max(80000, round(550000 - i*20000)), "p50": max(150000, round(650000 - i*15000)), "p90": max(250000, round(750000 - i*10000))} for i in range(25)],
                },
            },
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=4),
        ),
        CompanyScenario(
            company_id=demo_company.id,
            name="Series A Fundraise",
            assumptions_json={
                "tags": ["fundraise", "growth"],
                "revenue_growth_rate": 0.15,
                "burn_rate_monthly": 55000,
                "starting_cash": 500000,
                "pricing_change_pct": 10,
                "growth_uplift_pct": 15,
                "burn_reduction_pct": 0,
                "fundraise_month": 6,
                "fundraise_amount": 5000000,
                "gross_margin_delta_pct": 3,
            },
            outputs_json={
                "runway": {"p10": 18, "p50": 28, "p90": 36},
                "survival": {
                    "12m": 95, "18m": 90, "24m": 85,
                    "curve": [
                        {"month": 0, "probability": 100}, {"month": 3, "probability": 99},
                        {"month": 6, "probability": 98}, {"month": 9, "probability": 97},
                        {"month": 12, "probability": 95}, {"month": 15, "probability": 92},
                        {"month": 18, "probability": 90}, {"month": 21, "probability": 88},
                        {"month": 24, "probability": 85},
                    ],
                },
                "summary": {
                    "end_cash_p50": 800000, "monthly_burn_p50": 55000,
                    "runway_p50": 28, "runway_p10": 18, "runway_p90": 36,
                    "survival_12m": 95, "survival_18m": 90,
                    "revenue_18m_median": 320000, "cash_18m_median": 800000,
                    "default_probability": 0.10,
                },
                "bands": {
                    "revenue": [{"month": i, "p10": round(45000*(1.06**i)), "p50": round(45000*(1.12**i)), "p90": round(45000*(1.18**i))} for i in range(25)],
                    "cash": [{"month": i, "p10": max(200000, round(800000 - i*15000)), "p50": max(400000, round(1200000 - i*10000)), "p90": max(600000, round(1600000 - i*5000))} for i in range(25)],
                },
            },
            created_at=now - timedelta(days=8),
            updated_at=now - timedelta(days=1),
        ),
        CompanyScenario(
            company_id=demo_company.id,
            name="Bridge Round",
            assumptions_json={
                "tags": ["fundraise", "bridge"],
                "revenue_growth_rate": 0.125,
                "burn_rate_monthly": 52000,
                "starting_cash": 500000,
                "pricing_change_pct": 0,
                "growth_uplift_pct": 0,
                "burn_reduction_pct": 5,
                "fundraise_month": 2,
                "fundraise_amount": 750000,
                "gross_margin_delta_pct": 0,
            },
            outputs_json={
                "runway": {"p10": 16, "p50": 24, "p90": 30},
                "survival": {
                    "12m": 94, "18m": 85, "24m": 72,
                    "curve": [
                        {"month": 0, "probability": 100}, {"month": 3, "probability": 99},
                        {"month": 6, "probability": 97}, {"month": 9, "probability": 96},
                        {"month": 12, "probability": 94}, {"month": 15, "probability": 90},
                        {"month": 18, "probability": 85}, {"month": 21, "probability": 78},
                        {"month": 24, "probability": 72},
                    ],
                },
                "summary": {
                    "end_cash_p50": 350000, "monthly_burn_p50": 52000,
                    "runway_p50": 24, "runway_p10": 16, "runway_p90": 30,
                    "survival_12m": 94, "survival_18m": 85,
                    "revenue_18m_median": 185000, "cash_18m_median": 350000,
                    "default_probability": 0.15,
                },
                "bands": {
                    "revenue": [{"month": i, "p10": round(45000*(1.06**i)), "p50": round(45000*(1.10**i)), "p90": round(45000*(1.15**i))} for i in range(25)],
                    "cash": [{"month": i, "p10": max(100000, round(1250000 - i*35000)), "p50": max(200000, round(1250000 - i*25000)), "p90": max(350000, round(1250000 - i*18000))} for i in range(25)],
                },
            },
            created_at=now - timedelta(days=7),
            updated_at=now - timedelta(days=2),
        ),
        CompanyScenario(
            company_id=demo_company.id,
            name="Worst Case",
            assumptions_json={
                "tags": ["stress-test", "downside"],
                "revenue_growth_rate": 0.03,
                "burn_rate_monthly": 60000,
                "starting_cash": 500000,
                "pricing_change_pct": -5,
                "growth_uplift_pct": -15,
                "burn_reduction_pct": -5,
                "fundraise_month": None,
                "fundraise_amount": 0,
                "gross_margin_delta_pct": -3,
            },
            outputs_json={
                "runway": {"p10": 5, "p50": 9, "p90": 14},
                "survival": {
                    "12m": 42, "18m": 22, "24m": 10,
                    "curve": [
                        {"month": 0, "probability": 100}, {"month": 3, "probability": 88},
                        {"month": 6, "probability": 72}, {"month": 9, "probability": 55},
                        {"month": 12, "probability": 42}, {"month": 15, "probability": 30},
                        {"month": 18, "probability": 22}, {"month": 21, "probability": 15},
                        {"month": 24, "probability": 10},
                    ],
                },
                "summary": {
                    "end_cash_p50": 0, "monthly_burn_p50": 60000,
                    "runway_p50": 9, "runway_p10": 5, "runway_p90": 14,
                    "survival_12m": 42, "survival_18m": 22,
                    "revenue_18m_median": 85000, "cash_18m_median": 0,
                    "default_probability": 0.78,
                },
                "bands": {
                    "revenue": [{"month": i, "p10": round(45000*(0.98**i)), "p50": round(45000*(1.02**i)), "p90": round(45000*(1.06**i))} for i in range(25)],
                    "cash": [{"month": i, "p10": max(0, round(500000 - i*55000)), "p50": max(0, round(500000 - i*45000)), "p90": max(0, round(500000 - i*32000))} for i in range(25)],
                },
            },
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=1),
        ),
        CompanyScenario(
            company_id=demo_company.id,
            name="Best Case",
            assumptions_json={
                "tags": ["upside", "optimistic"],
                "revenue_growth_rate": 0.20,
                "burn_rate_monthly": 50000,
                "starting_cash": 500000,
                "pricing_change_pct": 15,
                "growth_uplift_pct": 30,
                "burn_reduction_pct": 10,
                "fundraise_month": 4,
                "fundraise_amount": 3000000,
                "gross_margin_delta_pct": 5,
            },
            outputs_json={
                "runway": {"p10": 22, "p50": 36, "p90": 48},
                "survival": {
                    "12m": 98, "18m": 95, "24m": 92,
                    "curve": [
                        {"month": 0, "probability": 100}, {"month": 3, "probability": 100},
                        {"month": 6, "probability": 99}, {"month": 9, "probability": 99},
                        {"month": 12, "probability": 98}, {"month": 15, "probability": 96},
                        {"month": 18, "probability": 95}, {"month": 21, "probability": 93},
                        {"month": 24, "probability": 92},
                    ],
                },
                "summary": {
                    "end_cash_p50": 1500000, "monthly_burn_p50": 50000,
                    "runway_p50": 36, "runway_p10": 22, "runway_p90": 48,
                    "survival_12m": 98, "survival_18m": 95,
                    "revenue_18m_median": 520000, "cash_18m_median": 1500000,
                    "default_probability": 0.05,
                },
                "bands": {
                    "revenue": [{"month": i, "p10": round(45000*(1.10**i)), "p50": round(45000*(1.18**i)), "p90": round(45000*(1.25**i))} for i in range(25)],
                    "cash": [{"month": i, "p10": max(300000, round(1500000 - i*20000)), "p50": max(600000, round(2000000 - i*10000)), "p90": max(1000000, round(2500000 - i*5000))} for i in range(25)],
                },
            },
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(hours=12),
        ),
    ]
    db.add_all(scenarios)
    db.commit()
    logger.info("Seeded 7 CompanyScenario records with simulation outputs")


def _seed_dashboard_widgets(db: Session, demo_company):
    dashboard = db.query(Dashboard).filter(
        Dashboard.company_id == demo_company.id
    ).first()
    if not dashboard:
        dashboard = Dashboard(
            company_id=demo_company.id,
            name="Financial Overview",
            description="Key financial metrics and health indicators",
            is_default=True,
        )
        db.add(dashboard)
        db.commit()
        db.refresh(dashboard)

    existing_widgets = db.query(DashboardWidget).filter(
        DashboardWidget.dashboard_id == dashboard.id
    ).first()
    if existing_widgets:
        return

    widgets = [
        DashboardWidget(
            dashboard_id=dashboard.id,
            widget_type="metric_card",
            metric_key="mrr",
            title="Monthly Recurring Revenue",
            config={"format": "currency", "trend": True, "sparkline": True},
            position={"x": 0, "y": 0, "w": 3, "h": 2},
        ),
        DashboardWidget(
            dashboard_id=dashboard.id,
            widget_type="metric_card",
            metric_key="arr",
            title="Annual Recurring Revenue",
            config={"format": "currency", "trend": True},
            position={"x": 3, "y": 0, "w": 3, "h": 2},
        ),
        DashboardWidget(
            dashboard_id=dashboard.id,
            widget_type="metric_card",
            metric_key="runway_months",
            title="Runway (Months)",
            config={"format": "number", "trend": True, "alert_threshold": 12},
            position={"x": 6, "y": 0, "w": 3, "h": 2},
        ),
        DashboardWidget(
            dashboard_id=dashboard.id,
            widget_type="metric_card",
            metric_key="burn_rate",
            title="Monthly Burn Rate",
            config={"format": "currency", "trend": True, "invert_color": True},
            position={"x": 9, "y": 0, "w": 3, "h": 2},
        ),
        DashboardWidget(
            dashboard_id=dashboard.id,
            widget_type="line_chart",
            metric_key="mrr",
            title="MRR Trend",
            config={"period": "12m", "show_target": True, "target_value": 80000},
            position={"x": 0, "y": 2, "w": 6, "h": 4},
        ),
        DashboardWidget(
            dashboard_id=dashboard.id,
            widget_type="bar_chart",
            metric_key="burn_rate",
            title="Burn Rate by Month",
            config={"period": "6m", "stacked": False},
            position={"x": 6, "y": 2, "w": 6, "h": 4},
        ),
        DashboardWidget(
            dashboard_id=dashboard.id,
            widget_type="metric_card",
            metric_key="gross_margin",
            title="Gross Margin",
            config={"format": "percent", "trend": True},
            position={"x": 0, "y": 6, "w": 3, "h": 2},
        ),
        DashboardWidget(
            dashboard_id=dashboard.id,
            widget_type="metric_card",
            metric_key="net_revenue_retention",
            title="Net Revenue Retention",
            config={"format": "percent", "trend": True, "benchmark": 110},
            position={"x": 3, "y": 6, "w": 3, "h": 2},
        ),
        DashboardWidget(
            dashboard_id=dashboard.id,
            widget_type="metric_card",
            metric_key="ltv_cac_ratio",
            title="LTV/CAC Ratio",
            config={"format": "number", "trend": True, "suffix": "x"},
            position={"x": 6, "y": 6, "w": 3, "h": 2},
        ),
        DashboardWidget(
            dashboard_id=dashboard.id,
            widget_type="metric_card",
            metric_key="customer_count",
            title="Active Customers",
            config={"format": "number", "trend": True},
            position={"x": 9, "y": 6, "w": 3, "h": 2},
        ),
    ]
    db.add_all(widgets)
    db.commit()
    logger.info(f"Seeded {len(widgets)} dashboard widgets for dashboard {dashboard.id}")


def _seed_investors_pipeline(db: Session, demo_company):
    existing = db.query(Investor).filter(Investor.company_id == demo_company.id).first()
    if existing:
        return

    series_a_round = db.query(FundraisingRound).filter(
        FundraisingRound.company_id == demo_company.id,
        FundraisingRound.name.ilike("%Series A%")
    ).first()
    if not series_a_round:
        return

    investors_data = [
        {
            "name": "Elevation Capital",
            "type": "vc",
            "geography": "India / Southeast Asia",
            "stage_focus": "Seed to Series B",
            "thesis_tags": ["SaaS", "Fintech", "AI/ML"],
            "contact": {"partner": "Ravi Adusumalli", "email": "ravi@elevationcap.com"},
            "stage": "dd",
            "probability": 0.65,
            "notes": "Strong interest after product demo. Requested detailed financial model and customer references."
        },
        {
            "name": "Sequoia Capital India",
            "type": "vc",
            "geography": "India",
            "stage_focus": "Seed to Growth",
            "thesis_tags": ["Enterprise SaaS", "Developer Tools", "AI"],
            "contact": {"partner": "Shailendra Singh", "email": "ss@sequoiacap.com"},
            "stage": "meeting",
            "probability": 0.40,
            "notes": "Initial meeting went well. Follow-up scheduled to discuss market sizing and competitive landscape."
        },
        {
            "name": "Blume Ventures",
            "type": "vc",
            "geography": "India",
            "stage_focus": "Pre-Seed to Series A",
            "thesis_tags": ["Fintech", "SaaS", "Deep Tech"],
            "contact": {"partner": "Karthik Reddy", "email": "karthik@blume.vc"},
            "stage": "term_sheet",
            "probability": 0.80,
            "notes": "Term sheet received. $2M at $18M pre-money. Negotiating board seat and pro-rata rights."
        },
        {
            "name": "Accel Partners",
            "type": "vc",
            "geography": "Global",
            "stage_focus": "Series A to Growth",
            "thesis_tags": ["SaaS", "Infrastructure", "AI"],
            "contact": {"partner": "Prashanth Prakash", "email": "prashanth@accel.com"},
            "stage": "contacted",
            "probability": 0.20,
            "notes": "Warm intro via existing portfolio founder. Sent deck and executive summary."
        },
        {
            "name": "Nexus Venture Partners",
            "type": "vc",
            "geography": "India / US",
            "stage_focus": "Seed to Series B",
            "thesis_tags": ["Enterprise", "Data Analytics", "Fintech"],
            "contact": {"partner": "Sameer Brij Verma", "email": "sameer@nexusvp.com"},
            "stage": "meeting",
            "probability": 0.35,
            "notes": "Second meeting completed. Interested in unit economics and path to profitability."
        },
        {
            "name": "Better Capital",
            "type": "angel",
            "geography": "India",
            "stage_focus": "Pre-Seed to Seed",
            "thesis_tags": ["Fintech", "SaaS", "Creator Economy"],
            "contact": {"partner": "Vaibhav Domkundwar", "email": "vaibhav@bettercapital.in"},
            "stage": "committed",
            "probability": 0.95,
            "notes": "Committed $250K. Will participate in the round alongside lead investor."
        },
        {
            "name": "Matrix Partners India",
            "type": "vc",
            "geography": "India",
            "stage_focus": "Series A to B",
            "thesis_tags": ["SaaS", "Consumer Tech", "Fintech"],
            "contact": {"partner": "Vikram Vaidyanathan", "email": "vikram@matrixpartners.in"},
            "stage": "sourced",
            "probability": 0.10,
            "notes": "Identified as potential investor. Planning warm intro through mutual connection."
        },
        {
            "name": "Lightspeed India",
            "type": "vc",
            "geography": "India / Southeast Asia",
            "stage_focus": "Seed to Growth",
            "thesis_tags": ["Enterprise SaaS", "Consumer", "Fintech"],
            "contact": {"partner": "Dev Khare", "email": "dev@lsvp.com"},
            "stage": "passed",
            "probability": 0.0,
            "notes": "Passed due to portfolio conflict with existing investment in financial analytics space."
        },
    ]

    now = datetime.utcnow()
    for i, inv_data in enumerate(investors_data):
        investor = Investor(
            company_id=demo_company.id,
            name=inv_data["name"],
            type=inv_data["type"],
            geography=inv_data["geography"],
            stage_focus=inv_data["stage_focus"],
            thesis_tags=inv_data["thesis_tags"],
            contact_json=inv_data["contact"],
        )
        db.add(investor)
        db.flush()

        pipeline = InvestorPipeline(
            round_id=series_a_round.id,
            investor_id=investor.id,
            stage=inv_data["stage"],
            probability=inv_data["probability"],
            last_contacted_at=now - timedelta(days=i * 3 + 1),
            notes=inv_data["notes"],
        )
        db.add(pipeline)

    db.commit()
    logger.info("Seeded 8 investors with pipeline entries")


def _seed_company_decisions(db: Session, demo_company):
    existing = db.query(CompanyDecision).filter(CompanyDecision.company_id == demo_company.id).first()
    if existing:
        return

    decisions_data = [
        {
            "title": "Hire 3 Senior Engineers for AI Team",
            "context": "Current team is stretched thin across multiple projects. AI copilot features require dedicated ML engineers. Monthly burn will increase by ~$45K but expected to accelerate product development by 3x.",
            "options": [
                {"label": "Hire all 3 now", "impact": "Fastest product velocity, highest burn increase"},
                {"label": "Hire 2 now, 1 in Q2", "impact": "Balanced approach, moderate burn increase"},
                {"label": "Hire 1 senior + 2 mid-level", "impact": "Lower cost, but slower ramp-up"}
            ],
            "recommendation": {
                "choice": "Hire 2 now, 1 in Q2",
                "reasoning": "Simulation shows this option extends runway to 18+ months while achieving 80% of the velocity gain. The staged approach reduces risk if fundraising timeline slips.",
                "simulation_impact": {"runway_delta": -2.5, "survival_18m_delta": -5, "revenue_impact": "+15% ARR growth"}
            },
            "status": "in_progress",
            "owner": "CTO",
            "tags": ["hiring", "engineering", "burn-rate"],
            "confidence": "high",
        },
        {
            "title": "Expand to US Market in Q2",
            "context": "Strong product-market fit in India. US expansion could 3x TAM but requires $200K+ investment in GTM, compliance, and local team. Several enterprise prospects have shown interest.",
            "options": [
                {"label": "Full US launch Q2", "impact": "High investment, fastest market entry"},
                {"label": "Soft launch with 3 pilot customers", "impact": "Lower risk, validated approach"},
                {"label": "Defer to Q3 post-fundraise", "impact": "Wait for more runway, but lose momentum"}
            ],
            "recommendation": {
                "choice": "Soft launch with 3 pilot customers",
                "reasoning": "Monte Carlo shows that a pilot approach preserves 22+ months of runway while validating US demand. Full launch pre-fundraise carries 35% risk of runway crunch.",
                "simulation_impact": {"runway_delta": -1.5, "survival_18m_delta": -3, "revenue_impact": "+$50K MRR in 6 months"}
            },
            "status": "proposed",
            "owner": "CEO",
            "tags": ["expansion", "go-to-market", "international"],
            "confidence": "medium",
        },
        {
            "title": "Switch from Monthly to Annual Billing Default",
            "context": "Currently 70% of customers on monthly plans. Annual billing would improve cash flow predictability and reduce churn. Risk of lower conversion rate on landing page.",
            "options": [
                {"label": "Default annual with monthly option", "impact": "Improved cash flow, potential conversion drop"},
                {"label": "Offer 20% annual discount", "impact": "Incentivize annual without forcing"},
                {"label": "Keep monthly default", "impact": "No change, continue current trajectory"}
            ],
            "recommendation": {
                "choice": "Offer 20% annual discount",
                "reasoning": "Analysis of similar SaaS companies shows 20% discount drives 40-50% annual adoption without hurting conversion. Expected to improve net cash position by $80K over 12 months.",
                "simulation_impact": {"runway_delta": 1.8, "survival_18m_delta": 4, "revenue_impact": "Neutral ARR, +$80K cash"}
            },
            "status": "decided",
            "owner": "Head of Product",
            "tags": ["pricing", "cash-flow", "retention"],
            "confidence": "high",
        },
        {
            "title": "Reduce Cloud Infrastructure Costs by 30%",
            "context": "Monthly cloud spend is $12K and growing. Analysis shows 40% of compute is over-provisioned. Migration to reserved instances and right-sizing could save $3.6K/month.",
            "options": [
                {"label": "Full optimization sprint (2 weeks)", "impact": "30% savings, engineering time trade-off"},
                {"label": "Quick wins only (3 days)", "impact": "15% savings, minimal disruption"},
                {"label": "Defer until post-fundraise", "impact": "No savings, no disruption"}
            ],
            "recommendation": {
                "choice": "Full optimization sprint (2 weeks)",
                "reasoning": "The $43K annual savings extends runway by 1.5 months. Engineering capacity is available in the next sprint. ROI payback period is under 2 weeks.",
                "simulation_impact": {"runway_delta": 1.5, "survival_18m_delta": 3, "revenue_impact": "None - pure cost savings"}
            },
            "status": "completed",
            "owner": "DevOps Lead",
            "tags": ["cost-optimization", "infrastructure", "runway"],
            "confidence": "high",
        },
        {
            "title": "Launch Enterprise Tier at $2,500/month",
            "context": "Three enterprise prospects requesting features like SSO, audit logs, and dedicated support. Current highest plan is $499/month. Enterprise tier would require 4-6 weeks of engineering.",
            "options": [
                {"label": "Launch enterprise tier immediately", "impact": "Revenue upside, engineering focus shift"},
                {"label": "Custom pricing for 3 prospects first", "impact": "Validate willingness to pay before building"},
                {"label": "Wait for Series A resources", "impact": "Lose prospects, but preserve engineering focus"}
            ],
            "recommendation": {
                "choice": "Custom pricing for 3 prospects first",
                "reasoning": "Validating with 3 committed customers de-risks the investment. If 2+ convert at $2K+/month, the enterprise tier ROI is confirmed. Simulation shows this adds $5K-7.5K MRR with 90% confidence.",
                "simulation_impact": {"runway_delta": 2.0, "survival_18m_delta": 6, "revenue_impact": "+$5K-7.5K MRR"}
            },
            "status": "in_progress",
            "owner": "Head of Sales",
            "tags": ["pricing", "enterprise", "revenue"],
            "confidence": "medium",
        },
    ]

    now = datetime.utcnow()
    for i, d in enumerate(decisions_data):
        decision = CompanyDecision(
            company_id=demo_company.id,
            title=d["title"],
            context=d["context"],
            options_json=d["options"],
            recommendation_json=d["recommendation"],
            status=d["status"],
            owner=d["owner"],
            tags=d["tags"],
            confidence=d["confidence"],
            created_at=now - timedelta(days=(len(decisions_data) - i) * 5),
        )
        db.add(decision)

    db.commit()
    logger.info("Seeded 5 company decisions")


def seed_team_members(db: Session):
    existing_team = db.query(TeamMember).first()
    if existing_team:
        return
    team_members = [
        TeamMember(
            name="Sarah Chen", email="sarah.chen@predixen.ai", role="Senior Frontend Engineer",
            type="full_time", department="Engineering", status="active", start_date="2024-03-15",
            skills=["React", "TypeScript", "Next.js", "Tailwind CSS", "GraphQL"],
            github_url="https://github.com/sarahchen", linkedin_url="https://linkedin.com/in/sarahchen"
        ),
        TeamMember(
            name="Marcus Johnson", email="marcus.j@predixen.ai", role="Backend Developer",
            type="full_time", department="Engineering", status="active", start_date="2024-01-10",
            skills=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
            github_url="https://github.com/marcusj", linkedin_url="https://linkedin.com/in/marcusjohnson"
        ),
        TeamMember(
            name="Priya Patel", email="priya.p@predixen.ai", role="DevOps Engineer",
            type="contractor", department="Engineering", status="active", start_date="2024-06-01",
            skills=["AWS", "Terraform", "Kubernetes", "CI/CD", "Monitoring"],
            github_url="https://github.com/priyap"
        ),
        TeamMember(
            name="Alex Rivera", email="alex.r@predixen.ai", role="QA Engineer",
            type="full_time", department="QA", status="active", start_date="2024-04-20",
            skills=["Playwright", "Cypress", "Test Automation", "API Testing", "Performance Testing"],
            linkedin_url="https://linkedin.com/in/alexrivera"
        ),
        TeamMember(
            name="Jordan Kim", email="jordan.k@predixen.ai", role="UI/UX Designer",
            type="contractor", department="Design", status="interviewing",
            skills=["Figma", "User Research", "Prototyping", "Design Systems", "Accessibility"],
            linkedin_url="https://linkedin.com/in/jordankim"
        ),
    ]
    db.add_all(team_members)
    db.commit()
    logger.info("Seeded 5 team members")
