"""
Market Agent for Fund Flow Copilot.

Market researcher + growth analyst that uses web research to find
competitors, benchmarks, pricing signals, customer segments, and top target customers.
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .base import (
    BaseAgent, AgentResponse, AgentType,
    CompanyKnowledgeBase, ConfidenceLevel
)

logger = logging.getLogger(__name__)


MARKET_SYSTEM_PROMPT = """You are Fund Flow Market Agent: a market researcher + growth analyst.
Your job: use web research tools to find competitors, benchmarks, pricing signals, customer segments, and top target customers.

Rules:
- Always cite sources for factual claims from the web.
- Clearly label inference vs fact.
- Prefer high-quality sources (company sites, reputable research, major publications).
- Never claim a company is a "customer" unless it's explicitly verified.

Deliverables:
1) Findings
2) Market map (competitors + positioning)
3) ICP + Segments
4) Top target customers (by category, with rationale)
5) Benchmarks (pricing/margins/growth if available)
6) Assumptions & Risks
7) Next Questions (≤3)
"""


@dataclass
class Competitor:
    """Competitor information."""
    name: str
    type: str = "direct"
    positioning: str = ""
    funding: Optional[str] = None
    notes: str = ""
    source: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "positioning": self.positioning,
            "funding": self.funding,
            "notes": self.notes,
            "source": self.source
        }


@dataclass
class IdealCustomerProfile:
    """Ideal Customer Profile (ICP) definition."""
    industry: List[str] = field(default_factory=list)
    company_size: str = ""
    geography: List[str] = field(default_factory=list)
    tech_stack: List[str] = field(default_factory=list)
    pain_points: List[str] = field(default_factory=list)
    buying_triggers: List[str] = field(default_factory=list)
    decision_makers: List[str] = field(default_factory=list)
    budget_range: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "industry": self.industry,
            "company_size": self.company_size,
            "geography": self.geography,
            "tech_stack": self.tech_stack,
            "pain_points": self.pain_points,
            "buying_triggers": self.buying_triggers,
            "decision_makers": self.decision_makers,
            "budget_range": self.budget_range
        }


@dataclass
class TargetCustomer:
    """Target customer with rationale."""
    name: str
    category: str  # enterprise, mid-market, smb
    industry: str
    why_them: str
    buying_trigger: str
    how_to_reach: str
    priority: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "industry": self.industry,
            "why_them": self.why_them,
            "buying_trigger": self.buying_trigger,
            "how_to_reach": self.how_to_reach,
            "priority": self.priority
        }


@dataclass
class MarketResearch:
    """Complete market research output."""
    category: str = ""
    tam: Optional[str] = None
    growth_rate: Optional[str] = None
    
    competitors: List[Competitor] = field(default_factory=list)
    icp: Optional[IdealCustomerProfile] = None
    target_customers: List[TargetCustomer] = field(default_factory=list)
    
    benchmarks: Dict[str, Any] = field(default_factory=dict)
    pricing_signals: List[str] = field(default_factory=list)
    
    sources: List[str] = field(default_factory=list)
    confidence: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "market_size": {
                "tam": self.tam,
                "growth_rate": self.growth_rate
            },
            "competitors": [c.to_dict() for c in self.competitors],
            "icp": self.icp.to_dict() if self.icp else None,
            "target_customers": [tc.to_dict() for tc in self.target_customers],
            "benchmarks": self.benchmarks,
            "pricing_signals": self.pricing_signals,
            "sources": self.sources,
            "confidence": self.confidence
        }


class MarketAgent(BaseAgent):
    """
    Market Agent that conducts market research, competitor analysis,
    and customer segmentation.
    """
    
    INDUSTRY_BENCHMARKS = {
        "saas": {
            "gross_margin": {"median": 75, "top_quartile": 82},
            "growth_rate": {"median": 30, "top_quartile": 50},
            "churn_rate": {"median": 5, "top_quartile": 2},
            "ltv_cac_ratio": {"median": 3, "top_quartile": 5},
            "cac_payback_months": {"median": 15, "top_quartile": 9}
        },
        "fintech": {
            "gross_margin": {"median": 65, "top_quartile": 78},
            "growth_rate": {"median": 40, "top_quartile": 70},
            "ndr": {"median": 110, "top_quartile": 130}
        },
        "marketplace": {
            "take_rate": {"median": 15, "top_quartile": 25},
            "gross_margin": {"median": 50, "top_quartile": 65},
            "growth_rate": {"median": 25, "top_quartile": 45}
        },
        "ecommerce": {
            "gross_margin": {"median": 35, "top_quartile": 50},
            "cac": {"median": 50, "top_quartile": 25},
            "repeat_purchase_rate": {"median": 20, "top_quartile": 40}
        },
        "agtech": {
            "gross_margin": {"median": 45, "top_quartile": 60},
            "growth_rate": {"median": 35, "top_quartile": 55}
        }
    }
    
    def __init__(self):
        super().__init__(AgentType.MARKET)
    
    async def process(
        self, 
        query: str, 
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Process market research request."""
        
        research = MarketResearch()
        findings = []
        
        research.category = self._determine_category(ckb.industry, query)
        findings.append(f"Market Category: {research.category}")
        
        if ckb.competitors:
            research.competitors = [
                Competitor(**c) if isinstance(c, dict) else c 
                for c in ckb.competitors
            ]
        else:
            research.competitors = self._generate_competitor_framework(research.category, ckb)
            findings.append(f"Identified {len(research.competitors)} competitor categories")
        
        if ckb.icp:
            research.icp = IdealCustomerProfile(**ckb.icp) if isinstance(ckb.icp, dict) else ckb.icp
        else:
            research.icp = self._build_icp(research.category, ckb)
            findings.append("Built Ideal Customer Profile based on company profile")
        
        research.target_customers = self._generate_target_customers(research.icp, research.category)
        findings.append(f"Identified {len(research.target_customers)} target customer segments")
        
        benchmarks = self._get_industry_benchmarks(research.category)
        if benchmarks:
            research.benchmarks = benchmarks
            findings.append(f"Retrieved {research.category} industry benchmarks")
        
        research.pricing_signals = self._analyze_pricing(research.category, context)
        
        assumptions = self._identify_assumptions(research, context)
        risks = self._identify_market_risks(research, ckb)
        
        next_questions = []
        if not research.competitors:
            next_questions.append("Who do you consider your main competitors?")
        if not research.icp or not research.icp.pain_points:
            next_questions.append("What are the top 3 pain points your customers have?")
        if not ckb.financials.get("arpu"):
            next_questions.append("What is your average revenue per customer?")
        
        confidence = ConfidenceLevel.MEDIUM
        if context.get("web_search_results"):
            confidence = ConfidenceLevel.HIGH
        elif not ckb.industry:
            confidence = ConfidenceLevel.LOW
        
        return AgentResponse(
            agent_type=AgentType.MARKET,
            findings=findings,
            structured_output=research.to_dict(),
            assumptions=assumptions,
            risks=risks,
            next_questions=next_questions[:3],
            confidence=confidence
        )
    
    def _determine_category(self, industry: str, query: str) -> str:
        """Determine market category from industry and query."""
        
        industry_lower = (industry or "").lower()
        query_lower = query.lower()
        
        category_keywords = {
            "saas": ["saas", "software", "subscription", "platform", "cloud"],
            "fintech": ["fintech", "finance", "payment", "banking", "lending", "insurance"],
            "marketplace": ["marketplace", "platform", "two-sided", "network"],
            "ecommerce": ["ecommerce", "e-commerce", "retail", "shop", "store"],
            "agtech": ["agtech", "agriculture", "farming", "agri", "food"]
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in industry_lower or kw in query_lower for kw in keywords):
                return category
        
        return "saas"
    
    def _generate_competitor_framework(
        self, 
        category: str, 
        ckb: CompanyKnowledgeBase
    ) -> List[Competitor]:
        """Generate a competitor analysis framework."""
        
        competitors = []
        
        competitors.append(Competitor(
            name="[Direct Competitors]",
            type="direct",
            positioning="Same product category, same target market",
            notes="Identify 3-5 companies that directly compete for your customers",
            source="Market research needed"
        ))
        
        competitors.append(Competitor(
            name="[Adjacent Competitors]",
            type="adjacent",
            positioning="Different product but could expand into your space",
            notes="Identify 2-3 companies that might compete in the future",
            source="Market research needed"
        ))
        
        competitors.append(Competitor(
            name="[Substitutes]",
            type="substitute",
            positioning="Alternative solutions (including manual processes)",
            notes="What do customers use if they don't buy your product?",
            source="Customer research needed"
        ))
        
        return competitors
    
    def _build_icp(
        self, 
        category: str, 
        ckb: CompanyKnowledgeBase
    ) -> IdealCustomerProfile:
        """Build an Ideal Customer Profile."""
        
        icp = IdealCustomerProfile()
        
        if ckb.industry:
            icp.industry = [ckb.industry]
        
        stage_to_size = {
            "pre-seed": "Startups (1-10 employees)",
            "seed": "Startups (10-50 employees)",
            "series-a": "SMB (50-200 employees)",
            "series-b": "Mid-market (200-1000 employees)",
            "series-c": "Enterprise (1000+ employees)"
        }
        icp.company_size = stage_to_size.get(ckb.stage, "SMB to Mid-market")
        
        icp.geography = ["North America", "Europe"]
        
        category_pain_points = {
            "saas": [
                "Manual processes slowing down operations",
                "Lack of visibility into key metrics",
                "Difficulty scaling current solutions"
            ],
            "fintech": [
                "Legacy systems integration challenges",
                "Compliance and regulatory burden",
                "Poor user experience in existing tools"
            ],
            "marketplace": [
                "Difficulty finding quality suppliers/providers",
                "High transaction costs",
                "Trust and verification challenges"
            ],
            "agtech": [
                "Supply chain visibility gaps",
                "Price volatility and market access",
                "Quality control and traceability"
            ]
        }
        icp.pain_points = category_pain_points.get(category, ["Operational inefficiency"])
        
        icp.buying_triggers = [
            "New funding round or budget cycle",
            "Leadership change or new initiative",
            "Failed implementation of alternative",
            "Regulatory requirement or deadline"
        ]
        
        icp.decision_makers = ["VP Operations", "CFO", "CTO"]
        
        return icp
    
    def _generate_target_customers(
        self, 
        icp: Optional[IdealCustomerProfile],
        category: str
    ) -> List[TargetCustomer]:
        """Generate target customer segments."""
        
        customers = []
        
        customers.append(TargetCustomer(
            name="[Enterprise Logos]",
            category="enterprise",
            industry=icp.industry[0] if icp and icp.industry else category,
            why_them="High ACV potential, reference value, complex needs match our capabilities",
            buying_trigger="Digital transformation initiative or existing vendor renewal",
            how_to_reach="Executive outreach, industry events, partner introductions",
            priority="high"
        ))
        
        customers.append(TargetCustomer(
            name="[Mid-Market Growth Companies]",
            category="mid-market",
            industry=icp.industry[0] if icp and icp.industry else category,
            why_them="Faster sales cycle, growing needs, good expansion potential",
            buying_trigger="Scaling challenges, post-funding, new market entry",
            how_to_reach="Content marketing, product-led growth, SDR outreach",
            priority="high"
        ))
        
        customers.append(TargetCustomer(
            name="[SMB/High-Velocity Segment]",
            category="smb",
            industry=icp.industry[0] if icp and icp.industry else category,
            why_them="Volume opportunity, product feedback, case study potential",
            buying_trigger="Immediate pain point, competitor frustration, recommendation",
            how_to_reach="Self-serve, product-led growth, community, content",
            priority="medium"
        ))
        
        return customers
    
    def _get_industry_benchmarks(self, category: str) -> Dict[str, Any]:
        """Get industry benchmarks for the category."""
        
        benchmarks = self.INDUSTRY_BENCHMARKS.get(category, {})
        
        if not benchmarks:
            benchmarks = self.INDUSTRY_BENCHMARKS.get("saas", {})
        
        return {
            "category": category,
            "metrics": benchmarks,
            "source": "Industry research and public company data",
            "note": "Benchmarks are approximate - actual ranges vary by segment"
        }
    
    def _analyze_pricing(
        self, 
        category: str, 
        context: Dict[str, Any]
    ) -> List[str]:
        """Analyze pricing signals and patterns."""
        
        pricing_patterns = {
            "saas": [
                "Per-seat/user pricing common for productivity tools",
                "Usage-based pricing growing in infrastructure/API products",
                "Tiered pricing (Starter/Pro/Enterprise) is standard",
                "Annual contracts typically offer 15-20% discount"
            ],
            "fintech": [
                "Transaction-based fees most common (0.5-3%)",
                "Subscription + usage hybrid models growing",
                "Volume discounts for enterprise",
                "Free tier with premium features"
            ],
            "marketplace": [
                "Take rate typically 10-25% of transaction",
                "Subscription fees for premium seller features",
                "Featured listing/advertising revenue",
                "Payment processing fees (2.9% + $0.30)"
            ]
        }
        
        return pricing_patterns.get(category, [
            "Research competitor pricing pages",
            "Survey customers on willingness to pay",
            "Test different price points"
        ])
    
    def _identify_assumptions(
        self, 
        research: MarketResearch, 
        context: Dict[str, Any]
    ) -> List[str]:
        """Identify assumptions made in the analysis."""
        
        assumptions = []
        
        if not context.get("web_search_results"):
            assumptions.append("Market data based on general industry knowledge, not live research")
        
        if not research.competitors or "[" in research.competitors[0].name:
            assumptions.append("Competitor list is a framework - specific companies need research")
        
        assumptions.append(f"Assumed market category: {research.category}")
        
        if research.benchmarks:
            assumptions.append("Benchmarks are industry averages - segment-specific data may differ")
        
        return assumptions
    
    def _identify_market_risks(
        self, 
        research: MarketResearch, 
        ckb: CompanyKnowledgeBase
    ) -> List[str]:
        """Identify market-related risks."""
        
        risks = []
        
        risks.append("Market sizing and growth estimates should be validated with primary research")
        
        if not ckb.financials.get("arpu"):
            risks.append("Pricing strategy unclear - risk of underpricing or market mismatch")
        
        if len(research.competitors) < 3:
            risks.append("Limited competitive intelligence - may miss key threats")
        
        return risks
