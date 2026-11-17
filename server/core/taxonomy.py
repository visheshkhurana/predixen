INDUSTRY_ALIASES = {
    "general_saas": "saas",
    # AI products: no AI-specific benchmark set yet, so they compare against
    # software. Kept as its own value so it can get one later.
    "ai": "saas",
    "ai-ml": "saas",
    "ecommerce": "marketplace",
    "healthcare": "healthtech",
    "edtech": "saas",
    "agritech": "hardware",
    "deeptech": "hardware",
    "climate": "hardware",
    "media": "consumer_sub",
    "logistics": "services",
    "real_estate": "fintech",
    "food": "d2c",
    # Onboarding values matching the /for/agency and /for/startup pages.
    # Agencies benchmark against professional services; "early-stage /
    # pre-revenue" says nothing about the business model, so it uses the
    # generic SaaS fallback (the same as "other").
    "agency": "services",
    "startup": "saas",
    "other": "saas",
    "unknown": "saas",
}

STAGE_ALIASES = {
    # Bootstrapped brands (common in Indian D2C) compare with seed-stage peers.
    "bootstrapped": "seed",
    "series_c": "series_b_plus",
    "pre_series_a": "seed",
    "series_b": "series_b_plus",
    "growth": "series_b_plus",
    "pre_ipo": "series_b_plus",
    "public": "series_b_plus",
    "unknown_stage": "seed",
    "unknown": "seed",
}


def normalize_industry(industry: str) -> str:
    key = (industry or "").strip().lower()
    return INDUSTRY_ALIASES.get(key, key)


def normalize_stage(stage: str) -> str:
    key = (stage or "").strip().lower()
    return STAGE_ALIASES.get(key, key)
