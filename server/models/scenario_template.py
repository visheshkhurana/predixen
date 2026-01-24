from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Float, Boolean
from datetime import datetime
from server.core.db import Base


class ScenarioTemplate(Base):
    __tablename__ = "scenario_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False, default="general")
    icon = Column(String, nullable=True)
    
    pricing_change_pct = Column(Float, default=0)
    growth_uplift_pct = Column(Float, default=0)
    burn_reduction_pct = Column(Float, default=0)
    fundraise_amount = Column(Float, default=0)
    fundraise_month = Column(Integer, nullable=True)
    gross_margin_delta_pct = Column(Float, default=0)
    hiring_headcount_change = Column(Integer, default=0)
    marketing_spend_change_pct = Column(Float, default=0)
    
    assumptions_json = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    
    is_builtin = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    created_by_user_id = Column(Integer, nullable=True)
    
    usage_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


BUILTIN_TEMPLATES = [
    {
        "name": "Baseline",
        "description": "Current trajectory with no changes - your default starting point",
        "category": "general",
        "icon": "Target",
        "pricing_change_pct": 0,
        "growth_uplift_pct": 0,
        "burn_reduction_pct": 0,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": 0,
        "hiring_headcount_change": 0,
        "marketing_spend_change_pct": 0,
        "tags": ["default", "baseline"],
        "assumptions_json": {"notes": "No changes from current trajectory"},
        "is_builtin": True,
    },
    {
        "name": "Aggressive Expansion",
        "description": "High growth strategy with increased investment in sales, marketing, and hiring",
        "category": "growth",
        "icon": "Rocket",
        "pricing_change_pct": 10,
        "growth_uplift_pct": 25,
        "burn_reduction_pct": -20,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": -5,
        "hiring_headcount_change": 10,
        "marketing_spend_change_pct": 50,
        "tags": ["growth", "expansion", "aggressive"],
        "assumptions_json": {
            "notes": "Prioritize market share capture over profitability",
            "risks": ["Higher burn rate", "Execution risk", "May need additional funding"]
        },
        "is_builtin": True,
    },
    {
        "name": "Lean Mode",
        "description": "Maximize runway by cutting non-essential costs while maintaining core operations",
        "category": "efficiency",
        "icon": "Scissors",
        "pricing_change_pct": 0,
        "growth_uplift_pct": -5,
        "burn_reduction_pct": 30,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": 5,
        "hiring_headcount_change": -3,
        "marketing_spend_change_pct": -40,
        "tags": ["efficiency", "cost-cutting", "survival"],
        "assumptions_json": {
            "notes": "Focus on survival and reaching profitability",
            "risks": ["Reduced growth", "Team morale", "Market position loss"]
        },
        "is_builtin": True,
    },
    {
        "name": "Market Entry APAC",
        "description": "Expand into Asia-Pacific markets with localized pricing and partnerships",
        "category": "expansion",
        "icon": "Globe",
        "pricing_change_pct": -15,
        "growth_uplift_pct": 20,
        "burn_reduction_pct": -15,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": -8,
        "hiring_headcount_change": 5,
        "marketing_spend_change_pct": 30,
        "tags": ["expansion", "apac", "international"],
        "assumptions_json": {
            "notes": "Lower pricing for emerging markets, higher customer acquisition costs initially",
            "target_markets": ["India", "Southeast Asia", "Australia"],
            "risks": ["Localization costs", "Regulatory compliance", "Currency risk"]
        },
        "is_builtin": True,
    },
    {
        "name": "Series A Fundraise",
        "description": "Prepare for and execute Series A round with $5M target",
        "category": "fundraising",
        "icon": "DollarSign",
        "pricing_change_pct": 5,
        "growth_uplift_pct": 15,
        "burn_reduction_pct": -10,
        "fundraise_amount": 5000000,
        "fundraise_month": 6,
        "gross_margin_delta_pct": 0,
        "hiring_headcount_change": 8,
        "marketing_spend_change_pct": 25,
        "tags": ["fundraising", "series-a", "growth"],
        "assumptions_json": {
            "notes": "Accelerate growth metrics to hit Series A benchmarks",
            "target_arr": 2000000,
            "target_growth_rate": 15
        },
        "is_builtin": True,
    },
    {
        "name": "Bridge Round",
        "description": "Extend runway with bridge financing while optimizing for next milestone",
        "category": "fundraising",
        "icon": "Banknote",
        "pricing_change_pct": 0,
        "growth_uplift_pct": 5,
        "burn_reduction_pct": 10,
        "fundraise_amount": 1000000,
        "fundraise_month": 3,
        "gross_margin_delta_pct": 2,
        "hiring_headcount_change": 0,
        "marketing_spend_change_pct": -10,
        "tags": ["fundraising", "bridge", "runway-extension"],
        "assumptions_json": {
            "notes": "Balance growth with efficiency to reach next milestone",
            "dilution_estimate": "10-15%"
        },
        "is_builtin": True,
    },
    {
        "name": "Product-Led Growth",
        "description": "Shift to PLG model with freemium tier and self-serve onboarding",
        "category": "strategy",
        "icon": "Zap",
        "pricing_change_pct": -20,
        "growth_uplift_pct": 35,
        "burn_reduction_pct": 5,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": -3,
        "hiring_headcount_change": 2,
        "marketing_spend_change_pct": -20,
        "tags": ["plg", "freemium", "product"],
        "assumptions_json": {
            "notes": "Lower CAC through viral growth, higher volume lower ARPU",
            "conversion_rate": "3-5% free to paid",
            "risks": ["Infrastructure costs", "Support volume", "Feature gating complexity"]
        },
        "is_builtin": True,
    },
    {
        "name": "Enterprise Focus",
        "description": "Pivot toward enterprise customers with higher ACV and longer sales cycles",
        "category": "strategy",
        "icon": "Building2",
        "pricing_change_pct": 50,
        "growth_uplift_pct": -10,
        "burn_reduction_pct": 0,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": 10,
        "hiring_headcount_change": 3,
        "marketing_spend_change_pct": -15,
        "tags": ["enterprise", "b2b", "high-acv"],
        "assumptions_json": {
            "notes": "Longer sales cycles but higher revenue per customer",
            "target_acv": 50000,
            "sales_cycle_months": 6,
            "risks": ["Concentrated revenue", "Longer time to close", "Enterprise feature requirements"]
        },
        "is_builtin": True,
    },
    {
        "name": "Price Increase",
        "description": "Increase pricing by 20% across all tiers to improve unit economics",
        "category": "pricing",
        "icon": "TrendingUp",
        "pricing_change_pct": 20,
        "growth_uplift_pct": -3,
        "burn_reduction_pct": 0,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": 5,
        "hiring_headcount_change": 0,
        "marketing_spend_change_pct": 0,
        "tags": ["pricing", "margin-improvement"],
        "assumptions_json": {
            "notes": "Expect slight churn increase but improved margins",
            "expected_churn_increase": "2-5%"
        },
        "is_builtin": True,
    },
    {
        "name": "Downturn Defense",
        "description": "Prepare for economic downturn with focus on retention and cost efficiency",
        "category": "resilience",
        "icon": "Shield",
        "pricing_change_pct": 0,
        "growth_uplift_pct": -15,
        "burn_reduction_pct": 25,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": 3,
        "hiring_headcount_change": -5,
        "marketing_spend_change_pct": -30,
        "tags": ["downturn", "recession", "defense"],
        "assumptions_json": {
            "notes": "Prioritize customer retention and extend runway",
            "focus_areas": ["Customer success", "Core product", "Cash preservation"],
            "risks": ["Competitive vulnerability", "Team attrition"]
        },
        "is_builtin": True,
    },
]
