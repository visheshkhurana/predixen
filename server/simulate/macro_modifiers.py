"""
Macro-Economic Modifiers for Simulation Engine.

Provides global economic factors that modify revenue and cost projections:
- interest_rate: Affects cost of capital and discount rates
- inflation_rate: Increases costs over time
- market_growth_factor: Scales revenue growth assumptions
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class MacroPreset(str, Enum):
    """Predefined macro-economic scenarios."""
    OPTIMISTIC = "optimistic"
    NEUTRAL = "neutral"
    PESSIMISTIC = "pessimistic"
    STAGFLATION = "stagflation"
    BOOM = "boom"
    CUSTOM = "custom"


class MacroModifiers(BaseModel):
    """Global macro-economic parameters affecting simulations."""
    
    interest_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=0.25,
        description="Annual interest rate (0.05 = 5%)"
    )
    inflation_rate: float = Field(
        default=0.03,
        ge=-0.05,
        le=0.20,
        description="Annual inflation rate (0.03 = 3%)"
    )
    market_growth_factor: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Market growth multiplier (1.0 = normal, 1.2 = 20% faster growth)"
    )
    currency_fx_rate: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="FX rate adjustment for non-USD companies"
    )
    credit_availability: float = Field(
        default=1.0,
        ge=0.0,
        le=1.5,
        description="Credit availability factor (1.0 = normal, 0.5 = tight credit)"
    )
    
    preset: MacroPreset = Field(
        default=MacroPreset.NEUTRAL,
        description="Which preset was used as base"
    )


MACRO_PRESETS: Dict[MacroPreset, MacroModifiers] = {
    MacroPreset.OPTIMISTIC: MacroModifiers(
        interest_rate=0.03,
        inflation_rate=0.02,
        market_growth_factor=1.3,
        currency_fx_rate=1.0,
        credit_availability=1.2,
        preset=MacroPreset.OPTIMISTIC
    ),
    MacroPreset.NEUTRAL: MacroModifiers(
        interest_rate=0.05,
        inflation_rate=0.03,
        market_growth_factor=1.0,
        currency_fx_rate=1.0,
        credit_availability=1.0,
        preset=MacroPreset.NEUTRAL
    ),
    MacroPreset.PESSIMISTIC: MacroModifiers(
        interest_rate=0.08,
        inflation_rate=0.05,
        market_growth_factor=0.7,
        currency_fx_rate=1.0,
        credit_availability=0.6,
        preset=MacroPreset.PESSIMISTIC
    ),
    MacroPreset.STAGFLATION: MacroModifiers(
        interest_rate=0.10,
        inflation_rate=0.08,
        market_growth_factor=0.5,
        currency_fx_rate=1.0,
        credit_availability=0.4,
        preset=MacroPreset.STAGFLATION
    ),
    MacroPreset.BOOM: MacroModifiers(
        interest_rate=0.02,
        inflation_rate=0.02,
        market_growth_factor=1.5,
        currency_fx_rate=1.0,
        credit_availability=1.5,
        preset=MacroPreset.BOOM
    ),
}


def get_preset(preset_name: str) -> MacroModifiers:
    """Get a predefined macro preset by name."""
    try:
        preset = MacroPreset(preset_name.lower())
        return MACRO_PRESETS.get(preset, MACRO_PRESETS[MacroPreset.NEUTRAL])
    except ValueError:
        return MACRO_PRESETS[MacroPreset.NEUTRAL]


def list_presets() -> List[Dict[str, Any]]:
    """List all available macro presets with their configurations."""
    return [
        {
            "id": preset.value,
            "name": preset.value.replace("_", " ").title(),
            "description": _get_preset_description(preset),
            "config": MACRO_PRESETS[preset].model_dump()
        }
        for preset in MacroPreset
        if preset != MacroPreset.CUSTOM
    ]


def _get_preset_description(preset: MacroPreset) -> str:
    """Get human-readable description for a preset."""
    descriptions = {
        MacroPreset.OPTIMISTIC: "Strong economic conditions with low rates and high growth",
        MacroPreset.NEUTRAL: "Normal economic conditions with moderate growth",
        MacroPreset.PESSIMISTIC: "Weak economic conditions with higher rates and slower growth",
        MacroPreset.STAGFLATION: "High inflation combined with low growth and tight credit",
        MacroPreset.BOOM: "Exceptional growth conditions with easy credit",
        MacroPreset.CUSTOM: "User-defined custom parameters",
    }
    return descriptions.get(preset, "")


def apply_macro_to_baseline(
    baseline_metrics: Dict[str, float],
    macro: MacroModifiers,
    horizon_months: int = 24
) -> Dict[str, float]:
    """
    Apply macro-economic modifiers to baseline financial metrics.
    
    Adjusts:
    - Revenue growth: scaled by market_growth_factor
    - Costs: increased by inflation_rate
    - Discount rate: based on interest_rate
    """
    modified = baseline_metrics.copy()
    
    monthly_inflation = (1 + macro.inflation_rate) ** (1/12) - 1
    
    if "burn_rate" in modified:
        inflation_multiplier = (1 + monthly_inflation) ** (horizon_months / 2)
        modified["burn_rate"] = modified["burn_rate"] * inflation_multiplier
    
    if "monthly_revenue" in modified and macro.market_growth_factor != 1.0:
        growth_boost = (macro.market_growth_factor - 1.0) / 12
        if "revenue_growth_rate" in modified:
            modified["revenue_growth_rate"] = modified.get("revenue_growth_rate", 0.05) + growth_boost
    
    modified["discount_rate"] = macro.interest_rate
    modified["inflation_rate"] = macro.inflation_rate
    modified["market_growth_factor"] = macro.market_growth_factor
    
    return modified


def apply_macro_to_projections(
    projections: List[Dict[str, float]],
    macro: MacroModifiers
) -> List[Dict[str, float]]:
    """
    Apply macro modifiers to monthly projection series.
    
    Adjusts each month's values for inflation and market conditions.
    """
    monthly_inflation = (1 + macro.inflation_rate) ** (1/12) - 1
    
    adjusted = []
    for i, month in enumerate(projections):
        adj = month.copy()
        
        inflation_factor = (1 + monthly_inflation) ** i
        if "costs" in adj:
            adj["costs"] = adj["costs"] * inflation_factor
        if "burn" in adj:
            adj["burn"] = adj["burn"] * inflation_factor
        if "opex" in adj:
            adj["opex"] = adj["opex"] * inflation_factor
        
        if "revenue" in adj and i > 0:
            adj["revenue"] = adj["revenue"] * (macro.market_growth_factor ** (i / 12))
        
        adjusted.append(adj)
    
    return adjusted
