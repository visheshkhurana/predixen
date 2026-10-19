"""Plan definitions and feature gating for FounderConsole.

FounderConsole is free: every account gets every feature with no plan limits
(owner decision, 2026-10). The single source of truth is ``FREE_FOR_ALL``
below. ``has_feature`` and ``get_plan_limit`` never deny, whatever plan string
a caller passes, so a stale ``subscriptions`` row cannot lock anyone out.

The Starter/Growth/Scale entries stay in ``PLAN_DETAILS`` only so the Stripe
webhook and price lookups keep working for any subscription bought before the
switch. Nothing sells them any more. Cost/abuse controls (rate limits,
ai_governance budgets) are not plan-based and live elsewhere.
"""
from enum import Enum
from typing import Dict, List, Optional


class PlanTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"
    SCALE = "scale"


class Feature(str, Enum):
    DASHBOARD = "dashboard"
    BASIC_METRICS = "basic_metrics"
    CSV_UPLOAD = "csv_upload"
    MANUAL_DATA_ENTRY = "manual_data_entry"
    SIMULATIONS = "simulations"
    SIMULATION_UNLIMITED = "simulation_unlimited"
    COPILOT = "copilot"
    COPILOT_UNLIMITED = "copilot_unlimited"
    TRUTH_SCAN = "truth_scan"
    STRESS_TESTS = "stress_tests"
    WHAT_IF = "what_if"
    SENSITIVITY_ANALYSIS = "sensitivity_analysis"
    DATA_CONNECTORS = "data_connectors"
    FUNDRAISING_OS = "fundraising_os"
    CAP_TABLE = "cap_table"
    BOARD_DECK = "board_deck"
    HIRING_PLANNER = "hiring_planner"
    FLIGHT_SIMULATOR = "flight_simulator"
    DOCUMENT_GENERATOR = "document_generator"
    AI_GRAPHICS = "ai_graphics"
    DIGITAL_TWIN = "digital_twin"
    CROSS_COMPANY_LEARNING = "cross_company_learning"
    MULTI_COMPANY = "multi_company"
    EXPORT_PDF = "export_pdf"
    EMAIL_REPORTS = "email_reports"
    BENCHMARKS = "benchmarks"
    FUNDRAISING_READINESS = "fundraising_readiness"
    INVESTOR_ROOM = "investor_room"


# -1 means "no limit" everywhere plan limits are read.
UNLIMITED = -1

# Every user gets every feature. Kept as a named constant so the intent is
# greppable and a test can pin it.
FREE_FOR_ALL = True

PLAN_DETAILS: Dict[str, dict] = {
    PlanTier.FREE: {
        "name": "Free",
        "price_monthly": 0,
        "price_annual": 0,
        "tagline": "All features, no credit card",
        "max_companies": UNLIMITED,
        "max_simulations_per_month": UNLIMITED,
        "max_copilot_messages_per_month": UNLIMITED,
        "max_connectors": UNLIMITED,
        "features": list(Feature),
        "highlights": [
            "Every feature unlocked",
            "Unlimited companies",
            "Unlimited simulations",
            "Unlimited copilot",
            "All data connectors",
            "No credit card required",
        ],
    },
    PlanTier.STARTER: {
        "name": "Starter",
        "price_monthly": 29,
        "price_annual": 290,
        "tagline": "For early-stage founders",
        "max_companies": 1,
        "max_simulations_per_month": 50,
        "max_copilot_messages_per_month": 100,
        "max_connectors": 2,
        "features": [
            Feature.DASHBOARD,
            Feature.BASIC_METRICS,
            Feature.CSV_UPLOAD,
            Feature.MANUAL_DATA_ENTRY,
            Feature.SIMULATIONS,
            Feature.COPILOT,
            Feature.TRUTH_SCAN,
            Feature.STRESS_TESTS,
            Feature.WHAT_IF,
            Feature.SENSITIVITY_ANALYSIS,
            Feature.EXPORT_PDF,
            Feature.BENCHMARKS,
        ],
        "highlights": [
            "1 company",
            "50 simulations / month",
            "100 copilot messages / month",
            "2 data connectors",
            "Truth Scan & Stress Tests",
            "Industry benchmarks",
            "PDF export",
        ],
    },
    PlanTier.GROWTH: {
        "name": "Growth",
        "price_monthly": 49,
        "price_annual": 490,
        "tagline": "For scaling startups",
        "max_companies": 3,
        "max_simulations_per_month": -1,
        "max_copilot_messages_per_month": -1,
        "max_connectors": 10,
        "features": [
            Feature.DASHBOARD,
            Feature.BASIC_METRICS,
            Feature.CSV_UPLOAD,
            Feature.MANUAL_DATA_ENTRY,
            Feature.SIMULATIONS,
            Feature.SIMULATION_UNLIMITED,
            Feature.COPILOT,
            Feature.COPILOT_UNLIMITED,
            Feature.TRUTH_SCAN,
            Feature.STRESS_TESTS,
            Feature.WHAT_IF,
            Feature.SENSITIVITY_ANALYSIS,
            Feature.DATA_CONNECTORS,
            Feature.FUNDRAISING_OS,
            Feature.CAP_TABLE,
            Feature.BOARD_DECK,
            Feature.EXPORT_PDF,
            Feature.EMAIL_REPORTS,
            Feature.BENCHMARKS,
            Feature.FUNDRAISING_READINESS,
        ],
        "highlights": [
            "Up to 3 companies",
            "Unlimited simulations",
            "Unlimited copilot",
            "10 data connectors",
            "Fundraising OS & Cap table",
            "Board deck export",
            "Email reports",
            "Fundraising readiness score",
        ],
    },
    PlanTier.SCALE: {
        "name": "Scale",
        "price_monthly": 99,
        "price_annual": 990,
        "tagline": "Full power for serious founders",
        "max_companies": -1,
        "max_simulations_per_month": -1,
        "max_copilot_messages_per_month": -1,
        "max_connectors": -1,
        "features": [
            Feature.DASHBOARD,
            Feature.BASIC_METRICS,
            Feature.CSV_UPLOAD,
            Feature.MANUAL_DATA_ENTRY,
            Feature.SIMULATIONS,
            Feature.SIMULATION_UNLIMITED,
            Feature.COPILOT,
            Feature.COPILOT_UNLIMITED,
            Feature.TRUTH_SCAN,
            Feature.STRESS_TESTS,
            Feature.WHAT_IF,
            Feature.SENSITIVITY_ANALYSIS,
            Feature.DATA_CONNECTORS,
            Feature.FUNDRAISING_OS,
            Feature.CAP_TABLE,
            Feature.BOARD_DECK,
            Feature.HIRING_PLANNER,
            Feature.FLIGHT_SIMULATOR,
            Feature.DOCUMENT_GENERATOR,
            Feature.AI_GRAPHICS,
            Feature.DIGITAL_TWIN,
            Feature.CROSS_COMPANY_LEARNING,
            Feature.MULTI_COMPANY,
            Feature.EXPORT_PDF,
            Feature.EMAIL_REPORTS,
            Feature.BENCHMARKS,
            Feature.FUNDRAISING_READINESS,
            Feature.INVESTOR_ROOM,
        ],
        "highlights": [
            "Unlimited companies",
            "Unlimited everything",
            "All data connectors",
            "Flight Simulator (AI agents)",
            "Hiring Planner",
            "Document Generator",
            "AI Graphics Studio",
            "Digital Twin",
            "Investor Room",
            "Cross-company intelligence",
        ],
    },
}

# Trials no longer exist: there is nothing to trial. Kept so old imports work.
TRIAL_DURATION_DAYS = 0
TRIAL_PLAN = PlanTier.FREE


def get_plan_features(plan: str) -> List[str]:
    if FREE_FOR_ALL:
        return list(Feature)
    plan_info = PLAN_DETAILS.get(plan, PLAN_DETAILS[PlanTier.FREE])
    return plan_info["features"]


def has_feature(plan: str, feature: str) -> bool:
    if FREE_FOR_ALL:
        return True
    return feature in get_plan_features(plan)


def get_plan_limit(plan: str, limit_key: str) -> int:
    if FREE_FOR_ALL and limit_key.startswith("max_"):
        return UNLIMITED
    plan_info = PLAN_DETAILS.get(plan, PLAN_DETAILS[PlanTier.FREE])
    return plan_info.get(limit_key, 0)


def minimum_plan_for_feature(feature: str) -> Optional[str]:
    if FREE_FOR_ALL:
        return PlanTier.FREE
    for tier in [PlanTier.STARTER, PlanTier.GROWTH, PlanTier.SCALE]:
        if feature in PLAN_DETAILS[tier]["features"]:
            return tier
    return None


FEATURE_LABELS: Dict[str, str] = {
    Feature.SIMULATIONS: "Monte Carlo Simulations",
    Feature.COPILOT: "AI Copilot",
    Feature.TRUTH_SCAN: "Truth Scan",
    Feature.STRESS_TESTS: "Stress Tests",
    Feature.WHAT_IF: "What-If Analysis",
    Feature.SENSITIVITY_ANALYSIS: "Sensitivity Analysis",
    Feature.DATA_CONNECTORS: "Data Connectors",
    Feature.FUNDRAISING_OS: "Fundraising OS",
    Feature.CAP_TABLE: "Cap Table Management",
    Feature.BOARD_DECK: "Board Deck Export",
    Feature.HIRING_PLANNER: "Hiring Planner",
    Feature.FLIGHT_SIMULATOR: "Flight Simulator",
    Feature.DOCUMENT_GENERATOR: "Document Generator",
    Feature.AI_GRAPHICS: "AI Graphics Studio",
    Feature.DIGITAL_TWIN: "Digital Twin",
    Feature.CROSS_COMPANY_LEARNING: "Cross-Company Intelligence",
    Feature.MULTI_COMPANY: "Multiple Companies",
    Feature.EXPORT_PDF: "PDF Export",
    Feature.EMAIL_REPORTS: "Email Reports",
    Feature.BENCHMARKS: "Industry Benchmarks",
    Feature.FUNDRAISING_READINESS: "Fundraising Readiness Score",
    Feature.INVESTOR_ROOM: "Investor Room",
}
