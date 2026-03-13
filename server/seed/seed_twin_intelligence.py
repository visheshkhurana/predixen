"""
Seed data for Digital Twin and Intelligence Graph features.
Creates twin events, enriches company state, adds peer companies with
financial records and decisions so both features display meaningful data.
"""

import json
import logging
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

from server.models.twin_event import TwinEvent
from server.models.company_state import CompanyState, compute_snapshot_id
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.models.company_decision import CompanyDecision, CompanyScenario

logger = logging.getLogger(__name__)

SEED_MARKER = "twin_intel_seed_v3"


def seed_twin_intelligence(db: Session, company_id: int = 168):
    demo_ids = _get_demo_company_ids(db)
    all_seeded = all(
        db.query(TwinEvent).filter(
            TwinEvent.company_id == cid,
            TwinEvent.source == SEED_MARKER
        ).first() is not None
        for cid in demo_ids
    )
    if all_seeded:
        logger.info("Twin/Intelligence seed data already exists for all companies, skipping")
        return

    logger.info(f"Seeding Digital Twin & Intelligence Graph data for company {company_id}...")

    demo_company_ids = _get_demo_company_ids(db)
    for cid in demo_company_ids:
        already = db.query(TwinEvent).filter(
            TwinEvent.company_id == cid,
            TwinEvent.source == SEED_MARKER
        ).first()
        if already:
            continue
        _enrich_company_state(db, cid)
        _ensure_financial_records(db, cid)
        _seed_twin_events(db, cid)
        _seed_additional_decisions(db, cid)

    _seed_peer_companies(db)

    db.commit()
    logger.info("Twin/Intelligence seed data complete")


def _get_demo_company_ids(db: Session):
    from server.models.user import User
    demo_user = db.query(User).filter(User.email == "demo@founderconsole.ai").first()
    if not demo_user:
        return [168]
    companies = db.query(Company).filter(Company.user_id == demo_user.id).all()
    return [c.id for c in companies]


def _enrich_company_state(db: Session, company_id: int):
    cs = db.query(CompanyState).filter(CompanyState.company_id == company_id).first()
    if not cs:
        enriched = {
            "cashBalance": 513746,
            "monthlyBurn": 28000,
            "revenueMonthly": 43949,
            "revenueGrowthRate": 10.5,
            "expensesMonthly": 71949,
            "mrr": 43949,
            "arr": 527388,
            "arpu": 150,
            "customers": 293,
            "grossMargin": 72.3,
            "ltv": 4500,
            "cac": 1200,
            "churnRate": 3.2,
            "headcount": 18,
            "customerCount": 293,
            "ndr": 115,
            "burnMultiple": 0.64,
            "paybackPeriod": 8
        }
        cs = CompanyState(
            company_id=company_id,
            environment="user",
            state_json=json.dumps(enriched),
            snapshot_id=compute_snapshot_id(enriched),
            cash_balance=513746,
            monthly_burn=28000,
            revenue_monthly=43949,
            revenue_growth_rate="10.5",
            expenses_monthly=71949,
        )
        db.add(cs)
        db.flush()
        logger.info(f"Created CompanyState for company {company_id}")
        return

    enriched = {
        "cashBalance": 513746,
        "monthlyBurn": 28000,
        "revenueMonthly": 43949,
        "revenueGrowthRate": 10.5,
        "expensesMonthly": 71949,
        "mrr": 43949,
        "arr": 527388,
        "arpu": 150,
        "customers": 293,
        "grossMargin": 72.3,
        "ltv": 4500,
        "cac": 1200,
        "churnRate": 3.2,
        "headcount": 18,
        "customerCount": 293,
        "ndr": 115,
        "burnMultiple": 0.64,
        "paybackPeriod": 8
    }
    cs.state_json = json.dumps(enriched)
    cs.snapshot_id = compute_snapshot_id(enriched)
    cs.cash_balance = 513746
    cs.monthly_burn = 28000
    cs.revenue_monthly = 43949
    cs.revenue_growth_rate = "10.5"
    cs.expenses_monthly = 71949
    cs.updated_at = datetime.utcnow()
    logger.info(f"Enriched CompanyState for company {company_id}")


def _ensure_financial_records(db: Session, company_id: int):
    existing = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id
    ).count()
    if existing >= 6:
        return

    now = datetime.utcnow()
    random.seed(company_id + 100)
    mrr = 28000
    cash = 580000

    for month_offset in range(12, 0, -1):
        period = now - timedelta(days=month_offset * 30)
        noise = random.uniform(0.96, 1.04)
        month_mrr = round(mrr * noise)
        revenue = month_mrr
        burn = round(28000 * random.uniform(0.93, 1.07))
        opex = round(burn * 0.42)
        payroll = round(burn * 0.58)
        cogs = round(revenue * random.uniform(0.22, 0.28))
        net_burn = burn - revenue
        cash = max(cash - net_burn, 100000)
        runway = round(cash / burn, 1) if burn > 0 else 36
        headcount = 18 + random.randint(-2, 2)
        customers = max(50, round(month_mrr / random.uniform(100, 180)))
        growth_pct = round((0.08 + random.uniform(-0.02, 0.04)) * 100, 1)

        fr = FinancialRecord(
            company_id=company_id,
            period_start=period.date(),
            period_end=(period + timedelta(days=29)).date(),
            revenue=revenue,
            cogs=cogs,
            opex=opex,
            payroll=payroll,
            cash_balance=round(cash),
            mrr=month_mrr,
            arr=month_mrr * 12,
            gross_profit=revenue - cogs,
            gross_margin=round((1 - cogs / revenue) * 100, 1) if revenue else 0,
            net_burn=net_burn,
            runway_months=round(runway, 1),
            headcount=headcount,
            customers=customers,
            mom_growth=growth_pct,
            ltv=round(month_mrr / max(customers, 1) * random.uniform(22, 32)),
            cac=round(random.uniform(900, 1500)),
            arpu=round(month_mrr / max(customers, 1)),
            source_type="seed",
        )
        db.add(fr)
        mrr = round(mrr * 1.085)

    logger.info(f"Seeded 12 financial records for company {company_id}")


def _seed_twin_events(db: Session, company_id: int):
    now = datetime.utcnow()
    events = [
        {
            "event_type": "state_update",
            "source": SEED_MARKER,
            "payload": {"field": "cash_balance", "old": 480000, "new": 513746, "trigger": "monthly_close"},
            "created_at": now - timedelta(hours=2),
        },
        {
            "event_type": "revenue_update",
            "source": SEED_MARKER,
            "payload": {"mrr": 43949, "change_pct": 8.2, "new_customers": 12, "churned": 3},
            "created_at": now - timedelta(hours=6),
        },
        {
            "event_type": "connector_sync",
            "source": SEED_MARKER,
            "payload": {"connector": "stripe", "records_synced": 847, "duration_ms": 3200, "status": "success"},
            "created_at": now - timedelta(hours=12),
        },
        {
            "event_type": "connector_sync",
            "source": SEED_MARKER,
            "payload": {"connector": "quickbooks", "records_synced": 234, "duration_ms": 1800, "status": "success"},
            "created_at": now - timedelta(hours=13),
        },
        {
            "event_type": "simulation_run",
            "source": SEED_MARKER,
            "payload": {"scenario": "Current Trajectory", "n_sims": 1000, "p50_runway": 18.3, "survival_12m": 0.94},
            "created_at": now - timedelta(hours=18),
        },
        {
            "event_type": "decision_made",
            "source": SEED_MARKER,
            "payload": {"decision": "Hire Senior Backend Engineer", "confidence": "high", "impact": "runway -0.8mo, velocity +40%"},
            "created_at": now - timedelta(days=1),
        },
        {
            "event_type": "truth_scan_complete",
            "source": SEED_MARKER,
            "payload": {"score": 87, "flags": 2, "warnings": 1, "data_quality": "high"},
            "created_at": now - timedelta(days=1, hours=6),
        },
        {
            "event_type": "expense_update",
            "source": SEED_MARKER,
            "payload": {"category": "cloud_infrastructure", "old": 4200, "new": 3800, "savings_pct": 9.5},
            "created_at": now - timedelta(days=1, hours=12),
        },
        {
            "event_type": "fundraising_update",
            "source": SEED_MARKER,
            "payload": {"stage": "series_a", "pipeline_value": 2500000, "investors_contacted": 8, "term_sheets": 1},
            "created_at": now - timedelta(days=2),
        },
        {
            "event_type": "headcount_change",
            "source": SEED_MARKER,
            "payload": {"action": "hire", "role": "Product Designer", "department": "Design", "new_total": 18},
            "created_at": now - timedelta(days=2, hours=8),
        },
        {
            "event_type": "alert_triggered",
            "source": SEED_MARKER,
            "payload": {"alert_type": "burn_spike", "severity": "warning", "burn_change_pct": 12.3, "message": "Monthly burn increased 12.3%"},
            "created_at": now - timedelta(days=3),
        },
        {
            "event_type": "simulation_run",
            "source": SEED_MARKER,
            "payload": {"scenario": "Aggressive Growth", "n_sims": 1000, "p50_runway": 14.1, "survival_12m": 0.82},
            "created_at": now - timedelta(days=3, hours=6),
        },
        {
            "event_type": "data_ingestion",
            "source": SEED_MARKER,
            "payload": {"file": "march_financials.csv", "records": 156, "format": "csv", "validated": True},
            "created_at": now - timedelta(days=4),
        },
        {
            "event_type": "decision_outcome",
            "source": SEED_MARKER,
            "payload": {"decision": "Implement 10% price increase", "outcome": "positive", "mrr_impact": 3200, "churn_impact": 0.4},
            "created_at": now - timedelta(days=4, hours=12),
        },
        {
            "event_type": "connector_sync",
            "source": SEED_MARKER,
            "payload": {"connector": "hubspot", "records_synced": 423, "duration_ms": 2100, "status": "success"},
            "created_at": now - timedelta(days=5),
        },
        {
            "event_type": "revenue_update",
            "source": SEED_MARKER,
            "payload": {"mrr": 40600, "change_pct": 6.1, "new_customers": 9, "churned": 2},
            "created_at": now - timedelta(days=6),
        },
        {
            "event_type": "state_update",
            "source": SEED_MARKER,
            "payload": {"field": "headcount", "old": 16, "new": 17, "trigger": "hire_completed"},
            "created_at": now - timedelta(days=7),
        },
        {
            "event_type": "simulation_run",
            "source": SEED_MARKER,
            "payload": {"scenario": "Cost Optimization", "n_sims": 1000, "p50_runway": 22.7, "survival_12m": 0.97},
            "created_at": now - timedelta(days=8),
        },
        {
            "event_type": "decision_made",
            "source": SEED_MARKER,
            "payload": {"decision": "Switch to annual billing default", "confidence": "medium", "impact": "cash +15%, churn -2%"},
            "created_at": now - timedelta(days=9),
        },
        {
            "event_type": "truth_scan_complete",
            "source": SEED_MARKER,
            "payload": {"score": 82, "flags": 3, "warnings": 2, "data_quality": "good"},
            "created_at": now - timedelta(days=10),
        },
        {
            "event_type": "expense_update",
            "source": SEED_MARKER,
            "payload": {"category": "marketing", "old": 8500, "new": 12000, "change_pct": 41.2},
            "created_at": now - timedelta(days=11),
        },
        {
            "event_type": "connector_sync",
            "source": SEED_MARKER,
            "payload": {"connector": "gusto", "records_synced": 18, "duration_ms": 900, "status": "success"},
            "created_at": now - timedelta(days=12),
        },
        {
            "event_type": "alert_triggered",
            "source": SEED_MARKER,
            "payload": {"alert_type": "mrr_milestone", "severity": "info", "message": "MRR crossed $40K milestone"},
            "created_at": now - timedelta(days=13),
        },
        {
            "event_type": "data_ingestion",
            "source": SEED_MARKER,
            "payload": {"file": "q4_bank_statement.pdf", "records": 89, "format": "pdf", "validated": True},
            "created_at": now - timedelta(days=14),
        },
        {
            "event_type": "revenue_update",
            "source": SEED_MARKER,
            "payload": {"mrr": 38250, "change_pct": 7.8, "new_customers": 11, "churned": 4},
            "created_at": now - timedelta(days=16),
        },
    ]

    for evt in events:
        db.add(TwinEvent(company_id=company_id, **evt))

    logger.info(f"Seeded {len(events)} twin events for company {company_id}")


PEER_COMPANIES = [
    {
        "name": "DataPulse Analytics",
        "industry": "saas",
        "stage": "series_a",
        "mrr_start": 35000,
        "growth": 0.09,
        "burn": 32000,
        "cash": 620000,
        "headcount": 22,
    },
    {
        "name": "CloudStack Platform",
        "industry": "saas",
        "stage": "series_a",
        "mrr_start": 52000,
        "growth": 0.07,
        "burn": 45000,
        "cash": 880000,
        "headcount": 28,
    },
    {
        "name": "MetricFlow AI",
        "industry": "saas",
        "stage": "seed",
        "mrr_start": 12000,
        "growth": 0.15,
        "burn": 18000,
        "cash": 340000,
        "headcount": 8,
    },
    {
        "name": "RevenueLens",
        "industry": "saas",
        "stage": "series_a",
        "mrr_start": 41000,
        "growth": 0.11,
        "burn": 38000,
        "cash": 720000,
        "headcount": 20,
    },
    {
        "name": "FinOps Central",
        "industry": "saas",
        "stage": "series_b",
        "mrr_start": 95000,
        "growth": 0.06,
        "burn": 75000,
        "cash": 2100000,
        "headcount": 55,
    },
    {
        "name": "Vaultstream",
        "industry": "fintech",
        "stage": "series_a",
        "mrr_start": 28000,
        "growth": 0.12,
        "burn": 35000,
        "cash": 490000,
        "headcount": 15,
    },
    {
        "name": "GrowthPilot",
        "industry": "saas",
        "stage": "seed",
        "mrr_start": 8000,
        "growth": 0.18,
        "burn": 15000,
        "cash": 220000,
        "headcount": 6,
    },
    {
        "name": "StackBridge",
        "industry": "saas",
        "stage": "series_a",
        "mrr_start": 60000,
        "growth": 0.05,
        "burn": 52000,
        "cash": 950000,
        "headcount": 32,
    },
]

DECISION_TEMPLATES = [
    {
        "title": "Expand enterprise sales team",
        "context": "Current pipeline shows 3x more enterprise leads than our team can handle. Adding 2 AEs could capture $180K additional ARR within 6 months.",
        "status": "accepted",
        "confidence": "high",
        "tags": ["hiring", "sales", "growth"],
    },
    {
        "title": "Migrate infrastructure to multi-cloud",
        "context": "Single cloud dependency creates risk. Multi-cloud reduces downtime risk by 60% and could save 15% on infrastructure costs through competition.",
        "status": "completed",
        "confidence": "medium",
        "tags": ["infrastructure", "cost_reduction", "risk"],
    },
    {
        "title": "Launch product-led growth motion",
        "context": "Self-serve signups could reduce CAC by 40%. Requires 2 months of engineering investment to build onboarding flow and usage-based billing.",
        "status": "proposed",
        "confidence": "high",
        "tags": ["product", "growth", "pricing"],
    },
    {
        "title": "Negotiate annual contracts with top 20 customers",
        "context": "Converting monthly to annual billing for top accounts would improve cash position by $240K and reduce churn risk.",
        "status": "decided",
        "confidence": "high",
        "tags": ["pricing", "retention", "cash_flow"],
    },
    {
        "title": "Reduce AWS spend through reserved instances",
        "context": "Current on-demand spending is $4,200/mo. Reserved instances commitment would save 35% ($1,470/mo) with 1-year lock-in.",
        "status": "completed",
        "confidence": "high",
        "tags": ["cost_reduction", "infrastructure"],
    },
    {
        "title": "Hire VP of Engineering",
        "context": "Engineering team has grown to 8 ICs without dedicated leadership. VP hire would improve velocity 30% through better architecture decisions and team management.",
        "status": "accepted",
        "confidence": "medium",
        "tags": ["hiring", "engineering", "leadership"],
    },
    {
        "title": "Implement usage-based pricing tier",
        "context": "Top 15% of customers use 60% of resources but pay the same as mid-tier. Usage-based pricing could increase ARPU 25% without losing customers.",
        "status": "proposed",
        "confidence": "medium",
        "tags": ["pricing", "revenue", "product"],
    },
    {
        "title": "Open developer API program",
        "context": "20+ customer requests for API access. Developer program could drive ecosystem growth and create new revenue stream ($5K-15K/mo from API fees).",
        "status": "proposed",
        "confidence": "low",
        "tags": ["product", "growth", "ecosystem"],
    },
]


def _seed_peer_companies(db: Session):
    now = datetime.utcnow()
    random.seed(42)

    from server.models.user import User
    demo_user = db.query(User).filter(User.email == "demo@founderconsole.ai").first()
    owner_id = demo_user.id if demo_user else 1

    for peer in PEER_COMPANIES:
        existing = db.query(Company).filter(Company.name == peer["name"]).first()
        if existing:
            company = existing
        else:
            company = Company(
                name=peer["name"],
                industry=peer["industry"],
                stage=peer["stage"],
                user_id=owner_id,
                created_at=now - timedelta(days=90),
            )
            db.add(company)
            db.flush()

        existing_records = db.query(FinancialRecord).filter(
            FinancialRecord.company_id == company.id
        ).count()
        if existing_records >= 12:
            _seed_peer_decisions(db, company.id, now)
            continue

        mrr = peer["mrr_start"]
        cash = peer["cash"]
        for month_offset in range(12, 0, -1):
            period = now - timedelta(days=month_offset * 30)
            noise = random.uniform(0.95, 1.05)
            month_mrr = round(mrr * noise)
            revenue = month_mrr
            burn = round(peer["burn"] * random.uniform(0.92, 1.08))
            opex = round(burn * 0.45)
            payroll = round(burn * 0.55)
            cogs = round(revenue * random.uniform(0.2, 0.3))
            net_burn = burn - revenue
            cash = max(cash - net_burn, 50000)
            runway = round(cash / burn, 1) if burn > 0 else 36
            headcount = peer["headcount"] + random.randint(-1, 1)
            customers = max(20, round(month_mrr / random.uniform(80, 200)))
            growth_pct = round((peer["growth"] + random.uniform(-0.03, 0.03)) * 100, 1)

            fr = FinancialRecord(
                company_id=company.id,
                period_start=period.date(),
                period_end=(period + timedelta(days=29)).date(),
                revenue=revenue,
                cogs=cogs,
                opex=opex,
                payroll=payroll,
                cash_balance=round(cash),
                mrr=month_mrr,
                arr=month_mrr * 12,
                gross_profit=revenue - cogs,
                gross_margin=round((1 - cogs / revenue) * 100, 1) if revenue else 0,
                net_burn=net_burn,
                runway_months=round(runway, 1),
                headcount=headcount,
                customers=customers,
                mom_growth=growth_pct,
                ltv=round(month_mrr / max(customers, 1) * random.uniform(20, 35)),
                cac=round(random.uniform(800, 2000)),
                arpu=round(month_mrr / max(customers, 1)),
                source_type="seed",
            )
            db.add(fr)
            mrr = round(mrr * (1 + peer["growth"]))

        cs_data = {
            "cashBalance": round(cash),
            "monthlyBurn": peer["burn"],
            "revenueMonthly": mrr,
            "revenueGrowthRate": round(peer["growth"] * 100, 1),
            "expensesMonthly": peer["burn"] + mrr,
            "mrr": mrr,
            "arr": mrr * 12,
            "headcount": peer["headcount"],
        }
        existing_state = db.query(CompanyState).filter(
            CompanyState.company_id == company.id
        ).first()
        if not existing_state:
            state = CompanyState(
                company_id=company.id,
                environment="user",
                state_json=json.dumps(cs_data),
                snapshot_id=compute_snapshot_id(cs_data),
                cash_balance=round(cash),
                monthly_burn=peer["burn"],
                revenue_monthly=mrr,
                revenue_growth_rate=str(round(peer["growth"] * 100, 1)),
                expenses_monthly=peer["burn"] + mrr,
            )
            db.add(state)

        _seed_peer_decisions(db, company.id, now)

    logger.info(f"Seeded {len(PEER_COMPANIES)} peer companies with financial history")


def _seed_peer_decisions(db: Session, company_id: int, now: datetime):
    existing = db.query(CompanyDecision).filter(
        CompanyDecision.company_id == company_id
    ).count()
    if existing >= 3:
        return

    random.seed(company_id)
    chosen = random.sample(DECISION_TEMPLATES, min(4, len(DECISION_TEMPLATES)))
    for i, tmpl in enumerate(chosen):
        dec = CompanyDecision(
            company_id=company_id,
            title=tmpl["title"],
            context=tmpl["context"],
            status=tmpl["status"],
            confidence=tmpl["confidence"],
            tags=tmpl["tags"],
            options_json=[
                {"label": "Proceed", "description": "Execute this decision"},
                {"label": "Defer", "description": "Revisit next quarter"},
            ],
            recommendation_json={
                "action": "proceed",
                "rationale": tmpl["context"][:100],
                "confidence": tmpl["confidence"],
            },
            created_at=now - timedelta(days=random.randint(5, 45)),
        )
        db.add(dec)


def _seed_additional_decisions(db: Session, company_id: int):
    existing = db.query(CompanyDecision).filter(
        CompanyDecision.company_id == company_id
    ).count()
    if existing >= 10:
        return

    now = datetime.utcnow()
    extra_decisions = [
        {
            "title": "Accelerate Series A fundraise timeline",
            "context": "Market conditions favorable with 3 interested VCs. Accelerating by 2 months could capture better terms before rate changes.",
            "status": "decided",
            "confidence": "high",
            "tags": ["fundraising", "strategy", "timing"],
        },
        {
            "title": "Build SOC 2 compliance framework",
            "context": "Enterprise pipeline blocked by 4 deals ($320K ARR) requiring SOC 2. 3-month project with $25K audit cost.",
            "status": "accepted",
            "confidence": "high",
            "tags": ["compliance", "enterprise", "investment"],
        },
        {
            "title": "Launch customer success team",
            "context": "Churn is 3.2% monthly, above SaaS median of 2%. Dedicated CS team of 2 could reduce churn to <2% and protect $160K ARR.",
            "status": "proposed",
            "confidence": "medium",
            "tags": ["hiring", "retention", "churn"],
        },
        {
            "title": "Implement automated billing reconciliation",
            "context": "Manual reconciliation takes 20 hours/month and has 2% error rate. Automation reduces to 2 hours with 0.1% error rate.",
            "status": "completed",
            "confidence": "high",
            "tags": ["automation", "operations", "cost_reduction"],
        },
        {
            "title": "Partner with accounting firms for distribution",
            "context": "Channel partnerships with 5 accounting firms could add 50 qualified leads/quarter at 60% lower CAC than direct sales.",
            "status": "proposed",
            "confidence": "low",
            "tags": ["partnerships", "distribution", "growth"],
        },
    ]

    for i, d in enumerate(extra_decisions):
        dec = CompanyDecision(
            company_id=company_id,
            title=d["title"],
            context=d["context"],
            status=d["status"],
            confidence=d["confidence"],
            tags=d["tags"],
            options_json=[
                {"label": "Proceed", "description": "Execute this decision"},
                {"label": "Defer", "description": "Revisit later"},
                {"label": "Reject", "description": "Not aligned with priorities"},
            ],
            recommendation_json={
                "action": "proceed" if d["confidence"] != "low" else "evaluate",
                "rationale": d["context"][:120],
                "confidence": d["confidence"],
            },
            created_at=now - timedelta(days=i * 5 + 3),
        )
        db.add(dec)

    logger.info(f"Seeded additional decisions for company {company_id}")
