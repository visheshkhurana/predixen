"""
Fund Flow Copilot Module

Multi-agent AI system for financial advisory with:
- Router/Orchestrator
- CFO Agent (financial analysis)
- Market Agent (market research)
- Strategy Agent (business strategy)
- Company Knowledge Base (CKB) storage
"""

from .context_pack import build_context_pack
from .ckb_storage import CKBStorage
from .agents import (
    RouterAgent,
    CFOAgent,
    MarketAgent,
    StrategyAgent,
    BaseAgent,
    AgentResponse
)

__all__ = [
    "build_context_pack",
    "CKBStorage",
    "RouterAgent",
    "CFOAgent",
    "MarketAgent",
    "StrategyAgent",
    "BaseAgent",
    "AgentResponse"
]
