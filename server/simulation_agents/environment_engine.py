"""
Environment Engine — simulates external market conditions that evolve over time.

Generates market state for each simulation round including:
- Funding climate
- Market growth
- Competition intensity
- Hiring market tightness
"""

import random
import math
from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class EnvironmentState:
    funding_climate: float = 0.6
    market_growth: float = 0.5
    competition_intensity: float = 0.4
    hiring_market_tightness: float = 0.5
    interest_rates: float = 0.05
    regulatory_risk: float = 0.1

    def to_dict(self) -> Dict[str, float]:
        return {
            "funding_climate": round(self.funding_climate, 3),
            "market_growth": round(self.market_growth, 3),
            "competition_intensity": round(self.competition_intensity, 3),
            "hiring_market_tightness": round(self.hiring_market_tightness, 3),
            "interest_rates": round(self.interest_rates, 4),
            "regulatory_risk": round(self.regulatory_risk, 3),
        }


class EnvironmentEngine:
    def __init__(self, scenario_config: Dict[str, Any] = None):
        config = scenario_config or {}
        self.state = EnvironmentState(
            funding_climate=config.get("initial_funding_climate", 0.6),
            market_growth=config.get("initial_market_growth", 0.5),
            competition_intensity=config.get("initial_competition", 0.4),
            hiring_market_tightness=config.get("initial_hiring_market", 0.5),
        )
        self.volatility = config.get("volatility", 0.1)
        self.trend = config.get("market_trend", "neutral")
        self.history: List[Dict[str, float]] = []
        self.shocks: List[Dict[str, Any]] = []

    def step(self, month: int) -> Dict[str, float]:
        trend_bias = 0.0
        if self.trend == "bull":
            trend_bias = 0.01
        elif self.trend == "bear":
            trend_bias = -0.01

        self.state.funding_climate = self._evolve(
            self.state.funding_climate, trend_bias, 0.1, 0.95
        )
        self.state.market_growth = self._evolve(
            self.state.market_growth, trend_bias * 0.5, 0.05, 0.95
        )
        self.state.competition_intensity = self._evolve(
            self.state.competition_intensity, 0.005, 0.1, 0.9
        )
        self.state.hiring_market_tightness = self._evolve(
            self.state.hiring_market_tightness, 0, 0.15, 0.85
        )

        if random.random() < 0.05:
            shock = self._generate_shock(month)
            if shock:
                self.shocks.append(shock)
                self._apply_shock(shock)

        snapshot = self.state.to_dict()
        snapshot["month"] = month
        self.history.append(snapshot)
        return snapshot

    def _evolve(self, current: float, drift: float, floor: float, ceiling: float) -> float:
        noise = random.gauss(0, self.volatility * 0.3)
        mean_reversion = (0.5 - current) * 0.05
        new_val = current + drift + noise + mean_reversion
        return max(floor, min(ceiling, new_val))

    def _generate_shock(self, month: int) -> Dict[str, Any]:
        shocks = [
            {
                "type": "funding_freeze",
                "description": "Sudden funding market freeze — VCs pulling back",
                "impact": {"funding_climate": -0.2, "hiring_market_tightness": -0.1},
                "probability": 0.3,
            },
            {
                "type": "market_boom",
                "description": "Market boom — increased investor appetite",
                "impact": {"funding_climate": 0.15, "market_growth": 0.1},
                "probability": 0.25,
            },
            {
                "type": "competitor_exit",
                "description": "Major competitor exits market",
                "impact": {"competition_intensity": -0.15, "market_growth": 0.05},
                "probability": 0.15,
            },
            {
                "type": "regulation_change",
                "description": "New regulations impact the sector",
                "impact": {"regulatory_risk": 0.15, "market_growth": -0.05},
                "probability": 0.15,
            },
            {
                "type": "talent_crunch",
                "description": "Tech talent shortage intensifies",
                "impact": {"hiring_market_tightness": 0.2},
                "probability": 0.15,
            },
        ]

        shock = random.choice(shocks)
        if random.random() < shock["probability"]:
            shock["month"] = month
            return shock
        return None

    def _apply_shock(self, shock: Dict[str, Any]):
        for key, delta in shock.get("impact", {}).items():
            if hasattr(self.state, key):
                current = getattr(self.state, key)
                setattr(self.state, key, max(0.05, min(0.95, current + delta)))

    def get_history(self) -> List[Dict[str, float]]:
        return self.history

    def get_shocks(self) -> List[Dict[str, Any]]:
        return [{"month": s["month"], "type": s["type"], "description": s["description"]} for s in self.shocks]
