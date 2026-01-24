"""
Pre-configured scenario templates for common financial planning use cases.
"""
from typing import Dict, Any, List, Optional


# Template definitions
BASELINE_TEMPLATE = {
    "id": "baseline",
    "name": "Baseline",
    "description": "Continue current trajectory with no major changes. Uses existing growth rates and cost structure.",
    "category": "conservative",
    "inputs": {
        "growth_rate": 0.05,  # 5% MoM growth
        "churn_rate": 0.03,  # 3% monthly churn
        "gross_margin": 0.70,  # 70% gross margin
        "burn_rate_change": 0.0,  # No change to burn
        "headcount_change": 0,  # No hiring changes
        "cac": None,  # Use current CAC
        "price_change": 0.0,  # No price changes
    },
    "events": [],
    "regime_weights": {
        "base": 0.7,
        "downturn": 0.2,
        "breakout": 0.1,
    },
    "tags": ["default", "conservative"],
}

CONSERVATIVE_CUT_TEMPLATE = {
    "id": "conservative_cut",
    "name": "Conservative Cut",
    "description": "Reduce burn rate through cost cuts and slower hiring. Extends runway at the expense of growth.",
    "category": "conservative",
    "inputs": {
        "growth_rate": 0.02,  # Slower 2% growth
        "churn_rate": 0.04,  # Slightly higher churn (less investment in success)
        "gross_margin": 0.72,  # Marginally improved margin
        "burn_rate_change": -0.25,  # 25% reduction in burn
        "headcount_change": -2,  # Reduce by 2
        "cac": None,
        "price_change": 0.0,
    },
    "events": [
        {
            "type": "cost_cut",
            "month": 1,
            "impact_pct": -15,
            "description": "Reduce operating costs by 15%",
        },
        {
            "type": "hiring_freeze",
            "month": 1,
            "duration_months": 6,
            "description": "6-month hiring freeze",
        },
    ],
    "regime_weights": {
        "base": 0.6,
        "downturn": 0.35,
        "breakout": 0.05,
    },
    "tags": ["cost-cutting", "runway-extension", "conservative"],
}

AGGRESSIVE_GROWTH_TEMPLATE = {
    "id": "aggressive_growth",
    "name": "Aggressive Growth",
    "description": "Accelerate growth through increased spend on sales and marketing. Higher burn for faster expansion.",
    "category": "aggressive",
    "inputs": {
        "growth_rate": 0.12,  # 12% MoM growth target
        "churn_rate": 0.025,  # Lower churn with better success investment
        "gross_margin": 0.68,  # Slightly lower margin (scaling costs)
        "burn_rate_change": 0.30,  # 30% increase in burn
        "headcount_change": 5,  # Add 5 people
        "cac": None,  # May increase CAC
        "price_change": 0.0,
    },
    "events": [
        {
            "type": "hiring_plan",
            "month": 1,
            "headcount_change": 3,
            "description": "Hire 3 sales reps",
        },
        {
            "type": "marketing_spend_change",
            "month": 1,
            "impact_pct": 50,
            "description": "Increase marketing spend by 50%",
        },
    ],
    "regime_weights": {
        "base": 0.5,
        "downturn": 0.15,
        "breakout": 0.35,
    },
    "tags": ["growth", "scaling", "aggressive"],
}

FUNDRAISE_TEMPLATE = {
    "id": "fundraise",
    "name": "Fundraise Scenario",
    "description": "Model a successful fundraise with capital injection. Assumes growth acceleration post-funding.",
    "category": "strategic",
    "inputs": {
        "growth_rate": 0.08,  # 8% MoM growth
        "churn_rate": 0.03,
        "gross_margin": 0.70,
        "burn_rate_change": 0.20,  # Post-raise, burn increases
        "headcount_change": 8,  # Significant hiring
        "cac": None,
        "price_change": 0.0,
    },
    "events": [
        {
            "type": "fundraise",
            "month": 3,
            "amount": 5000000,  # $5M raise
            "dilution_pct": 20,
            "description": "$5M Series A at 20% dilution",
        },
        {
            "type": "hiring_plan",
            "month": 4,
            "headcount_change": 5,
            "description": "Post-raise hiring: 5 new employees",
        },
    ],
    "regime_weights": {
        "base": 0.6,
        "downturn": 0.15,
        "breakout": 0.25,
    },
    "tags": ["fundraise", "strategic", "capital"],
}

DOWNTURN_TEMPLATE = {
    "id": "downturn",
    "name": "Market Downturn",
    "description": "Model a market downturn with reduced growth and higher churn. Stress test for adverse conditions.",
    "category": "stress_test",
    "inputs": {
        "growth_rate": -0.02,  # Negative growth
        "churn_rate": 0.06,  # Double normal churn
        "gross_margin": 0.65,  # Compressed margins
        "burn_rate_change": 0.0,  # Costs don't immediately adjust
        "headcount_change": 0,
        "cac": None,
        "price_change": -0.10,  # 10% price pressure
    },
    "events": [
        {
            "type": "churn_initiative",
            "month": 3,
            "impact_pct": -15,  # Try to reduce churn
            "description": "Customer success initiative to stem churn",
        },
        {
            "type": "cost_cut",
            "month": 4,
            "impact_pct": -20,
            "description": "Emergency cost reduction measures",
        },
    ],
    "regime_weights": {
        "base": 0.2,
        "downturn": 0.75,
        "breakout": 0.05,
    },
    "tags": ["stress-test", "downturn", "risk"],
}

EXPANSION_REVENUE_TEMPLATE = {
    "id": "expansion_focus",
    "name": "Expansion Revenue Focus",
    "description": "Focus on expanding existing customers rather than new acquisition. Higher NRR, lower CAC spend.",
    "category": "strategic",
    "inputs": {
        "growth_rate": 0.06,
        "churn_rate": 0.02,  # Very low churn
        "gross_margin": 0.75,  # Better margins on expansion
        "burn_rate_change": -0.10,  # Lower spend
        "headcount_change": 2,  # Add CS headcount
        "cac": None,  # Lower CAC (less new sales)
        "price_change": 0.05,  # 5% price increase for upgrades
    },
    "events": [
        {
            "type": "expansion_revenue",
            "month": 2,
            "impact_pct": 25,  # 25% boost to expansion
            "description": "Launch upsell program",
        },
    ],
    "regime_weights": {
        "base": 0.65,
        "downturn": 0.2,
        "breakout": 0.15,
    },
    "tags": ["expansion", "nrr", "customer-success"],
}

PRICING_INCREASE_TEMPLATE = {
    "id": "pricing_increase",
    "name": "Pricing Increase",
    "description": "Implement a price increase across the customer base. Higher ARPU with potential churn impact.",
    "category": "strategic",
    "inputs": {
        "growth_rate": 0.04,  # Slightly slower new customer growth
        "churn_rate": 0.045,  # Some churn from price increase
        "gross_margin": 0.75,  # Better margins
        "burn_rate_change": 0.0,
        "headcount_change": 0,
        "cac": None,
        "price_change": 0.15,  # 15% price increase
    },
    "events": [
        {
            "type": "pricing_change",
            "month": 2,
            "impact_pct": 15,
            "description": "15% price increase for new customers",
        },
        {
            "type": "pricing_change",
            "month": 4,
            "impact_pct": 10,
            "description": "10% price increase for existing customers",
            "decay_rate": 0.1,
            "decay_type": "exponential",
        },
    ],
    "regime_weights": {
        "base": 0.7,
        "downturn": 0.2,
        "breakout": 0.1,
    },
    "tags": ["pricing", "revenue", "strategic"],
}

MARKET_ENTRY_APAC_TEMPLATE = {
    "id": "market_entry_apac",
    "name": "Market Entry APAC",
    "description": "Expand into Asia-Pacific markets with localized pricing and regional partnerships.",
    "category": "aggressive",
    "inputs": {
        "growth_rate": 0.10,  # Strong growth from new market
        "churn_rate": 0.035,  # Slightly higher as you learn the market
        "gross_margin": 0.62,  # Lower margins in new markets
        "burn_rate_change": 0.25,  # Investment required
        "headcount_change": 5,  # Regional team
        "cac": None,
        "price_change": -0.15,  # Lower pricing for emerging markets
    },
    "events": [
        {
            "type": "market_entry",
            "month": 2,
            "region": "apac",
            "description": "Launch in India and Southeast Asia",
        },
        {
            "type": "hiring_plan",
            "month": 3,
            "headcount_change": 3,
            "description": "Hire regional sales and support team",
        },
        {
            "type": "marketing_spend_change",
            "month": 2,
            "impact_pct": 40,
            "description": "Regional marketing campaign launch",
        },
    ],
    "regime_weights": {
        "base": 0.5,
        "downturn": 0.2,
        "breakout": 0.3,
    },
    "tags": ["expansion", "apac", "international", "aggressive"],
}

PRODUCT_LED_GROWTH_TEMPLATE = {
    "id": "plg",
    "name": "Product-Led Growth",
    "description": "Shift to PLG model with freemium tier. Lower CAC through viral growth, higher volume.",
    "category": "strategic",
    "inputs": {
        "growth_rate": 0.15,  # Strong organic growth
        "churn_rate": 0.04,  # Higher churn on free tier
        "gross_margin": 0.68,  # Infrastructure costs
        "burn_rate_change": 0.05,  # Slightly higher
        "headcount_change": 2,  # Product and eng focus
        "cac": None,  # Significantly lower CAC
        "price_change": -0.20,  # Free tier introduction
    },
    "events": [
        {
            "type": "product_launch",
            "month": 2,
            "description": "Launch freemium tier",
        },
        {
            "type": "marketing_spend_change",
            "month": 2,
            "impact_pct": -30,
            "description": "Reduce paid marketing, focus on product",
        },
        {
            "type": "expansion_revenue",
            "month": 4,
            "impact_pct": 20,
            "description": "Self-serve upgrade path optimization",
        },
    ],
    "regime_weights": {
        "base": 0.55,
        "downturn": 0.15,
        "breakout": 0.30,
    },
    "tags": ["plg", "freemium", "product", "strategic"],
}

ENTERPRISE_FOCUS_TEMPLATE = {
    "id": "enterprise_focus",
    "name": "Enterprise Focus",
    "description": "Pivot toward enterprise customers with higher ACV and longer sales cycles.",
    "category": "strategic",
    "inputs": {
        "growth_rate": 0.03,  # Slower but larger deals
        "churn_rate": 0.015,  # Very low enterprise churn
        "gross_margin": 0.80,  # Higher margins
        "burn_rate_change": 0.10,  # Investment in sales
        "headcount_change": 3,  # Enterprise sales team
        "cac": None,  # Higher CAC but worth it
        "price_change": 0.50,  # 50% higher pricing
    },
    "events": [
        {
            "type": "hiring_plan",
            "month": 1,
            "headcount_change": 2,
            "description": "Hire enterprise account executives",
        },
        {
            "type": "product_launch",
            "month": 3,
            "description": "Launch enterprise features (SSO, audit logs)",
        },
    ],
    "regime_weights": {
        "base": 0.65,
        "downturn": 0.25,
        "breakout": 0.10,
    },
    "tags": ["enterprise", "b2b", "high-acv", "strategic"],
}

LEAN_PROFITABILITY_TEMPLATE = {
    "id": "lean_profitability",
    "name": "Path to Profitability",
    "description": "Focus on reaching profitability within 12 months through efficiency gains.",
    "category": "conservative",
    "inputs": {
        "growth_rate": 0.02,  # Modest growth
        "churn_rate": 0.025,  # Focus on retention
        "gross_margin": 0.78,  # Margin optimization
        "burn_rate_change": -0.35,  # Significant cost reduction
        "headcount_change": -4,  # Restructuring
        "cac": None,
        "price_change": 0.10,  # Slight price increase
    },
    "events": [
        {
            "type": "cost_cut",
            "month": 1,
            "impact_pct": -25,
            "description": "Operating expense reduction",
        },
        {
            "type": "churn_initiative",
            "month": 2,
            "impact_pct": -20,
            "description": "Customer success focus to reduce churn",
        },
    ],
    "regime_weights": {
        "base": 0.70,
        "downturn": 0.25,
        "breakout": 0.05,
    },
    "tags": ["profitability", "efficiency", "conservative", "runway"],
}

# All templates in a list
ALL_TEMPLATES = [
    BASELINE_TEMPLATE,
    CONSERVATIVE_CUT_TEMPLATE,
    AGGRESSIVE_GROWTH_TEMPLATE,
    FUNDRAISE_TEMPLATE,
    DOWNTURN_TEMPLATE,
    EXPANSION_REVENUE_TEMPLATE,
    PRICING_INCREASE_TEMPLATE,
    MARKET_ENTRY_APAC_TEMPLATE,
    PRODUCT_LED_GROWTH_TEMPLATE,
    ENTERPRISE_FOCUS_TEMPLATE,
    LEAN_PROFITABILITY_TEMPLATE,
]


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Get a template by ID."""
    for template in ALL_TEMPLATES:
        if template["id"] == template_id:
            return template.copy()
    return None


def get_all_templates() -> List[Dict[str, Any]]:
    """Get all available templates."""
    return [t.copy() for t in ALL_TEMPLATES]


def get_templates_by_category(category: str) -> List[Dict[str, Any]]:
    """Get templates by category."""
    return [t.copy() for t in ALL_TEMPLATES if t["category"] == category]


def get_template_summary() -> List[Dict[str, str]]:
    """Get summary of all templates for UI display."""
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
            "tags": t.get("tags", []),
        }
        for t in ALL_TEMPLATES
    ]
