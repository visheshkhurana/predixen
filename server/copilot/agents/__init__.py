"""
Fund Flow Copilot Multi-Agent System

This module implements a multi-agent architecture with:
- Router/Orchestrator: Routes work to specialist agents
- CFO Agent: Financial extraction and analysis
- Market Agent: Market research and competitor analysis
- Strategy Agent: Business strategy and GTM recommendations
"""

from .base import BaseAgent, AgentResponse
from .router import RouterAgent
from .cfo_agent import CFOAgent
from .market_agent import MarketAgent
from .strategy_agent import StrategyAgent

__all__ = [
    "BaseAgent",
    "AgentResponse", 
    "RouterAgent",
    "CFOAgent",
    "MarketAgent",
    "StrategyAgent"
]
