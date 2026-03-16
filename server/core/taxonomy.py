INDUSTRY_ALIASES = {
    "general_saas": "saas",
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
    "other": "saas",
    "unknown": "saas",
}

STAGE_ALIASES = {
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
