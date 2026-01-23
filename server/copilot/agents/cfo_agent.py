"""
CFO Agent for Fund Flow Copilot.

Rigorous finance analyst + FP&A lead that extracts financials from documents,
normalizes currencies, validates consistency, computes key metrics,
and produces finance-grade summaries for decision-making.
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .base import (
    BaseAgent, AgentResponse, AgentType,
    CompanyKnowledgeBase, ConfidenceLevel
)

logger = logging.getLogger(__name__)


CFO_SYSTEM_PROMPT = """You are Fund Flow CFO Agent: a rigorous finance analyst + FP&A lead.
Your job: extract financials from user documents, normalize currencies, validate consistency, compute key metrics, and produce a finance-grade summary for decision-making.

Rules:
- Do not invent numbers. If data is missing, mark it missing.
- Use clear units and human-readable formats (USD 12.3M, USD 450K/mo).
- Provide confidence flags (High/Med/Low) depending on extraction quality.
- Prefer reconciled statements: P&L, Balance Sheet, Cash Flow (if available).
- If only partial data exists, still compute what you can (margins, growth, burn).

Extract:
• Revenue (by period, by stream if available)
• COGS, Gross Profit, Gross Margin
• Operating expenses (by category if available)
• EBITDA / Operating Profit / Net Income
• Cash balance, Debt, Working Capital notes
• Burn rate, runway, cashflow from ops/investing/financing (if present)
• Headcount, ARPU, CAC, LTV, churn (if present)

Normalization:
- Convert all to USD (default). If FX tool is unavailable, label "USD approx" and state assumed rate.
- Convert big numbers to abbreviations: K/M/B.
- Keep original currency values in a "source_values" section if possible.

Validation checks:
- Period alignment (FY vs calendar, months/quarters)
- Totals vs line items consistency
- Repeated/duplicated extraction artifacts
- Common OCR errors (commas/decimals, INR crore/lakh conversions)
"""


@dataclass 
class FinancialMetrics:
    """Extracted and computed financial metrics."""
    currency_base: str = "USD"
    periods: List[str] = field(default_factory=list)
    
    revenue: Optional[float] = None
    revenue_growth_mom: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    
    cogs: Optional[float] = None
    gross_profit: Optional[float] = None
    gross_margin: Optional[float] = None
    
    opex: Optional[float] = None
    payroll: Optional[float] = None
    marketing: Optional[float] = None
    other_costs: Optional[float] = None
    
    ebitda: Optional[float] = None
    operating_income: Optional[float] = None
    operating_margin: Optional[float] = None
    net_income: Optional[float] = None
    
    cash_balance: Optional[float] = None
    debt: Optional[float] = None
    working_capital: Optional[float] = None
    
    burn_rate: Optional[float] = None
    runway_months: Optional[float] = None
    
    headcount: Optional[int] = None
    arpu: Optional[float] = None
    cac: Optional[float] = None
    ltv: Optional[float] = None
    ltv_cac_ratio: Optional[float] = None
    churn_rate: Optional[float] = None
    
    mrr: Optional[float] = None
    arr: Optional[float] = None
    ndr: Optional[float] = None
    
    data_gaps: List[str] = field(default_factory=list)
    confidence: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "currency_base": self.currency_base,
            "periods": self.periods,
            "pnl": {
                "revenue": self.revenue,
                "revenue_growth_mom": self.revenue_growth_mom,
                "revenue_growth_yoy": self.revenue_growth_yoy,
                "cogs": self.cogs,
                "gross_profit": self.gross_profit,
                "gross_margin": self.gross_margin,
                "opex": self.opex,
                "payroll": self.payroll,
                "marketing": self.marketing,
                "other_costs": self.other_costs,
                "ebitda": self.ebitda,
                "operating_income": self.operating_income,
                "operating_margin": self.operating_margin,
                "net_income": self.net_income
            },
            "balance_sheet": {
                "cash_balance": self.cash_balance,
                "debt": self.debt,
                "working_capital": self.working_capital
            },
            "unit_economics": {
                "headcount": self.headcount,
                "arpu": self.arpu,
                "cac": self.cac,
                "ltv": self.ltv,
                "ltv_cac_ratio": self.ltv_cac_ratio,
                "churn_rate": self.churn_rate,
                "mrr": self.mrr,
                "arr": self.arr,
                "ndr": self.ndr
            },
            "cashflow": {
                "burn_rate": self.burn_rate,
                "runway_months": self.runway_months
            },
            "data_gaps": self.data_gaps,
            "confidence": self.confidence
        }


class CFOAgent(BaseAgent):
    """
    CFO Agent that handles financial extraction, normalization,
    validation, and metric computation.
    
    Uses GPT-4o via LLM Router for financial analysis (best at structured data).
    """
    
    FX_RATES = {
        "INR": 83.0,
        "EUR": 0.92,
        "GBP": 0.79,
        "CAD": 1.36,
        "AUD": 1.53,
        "JPY": 149.0,
        "CNY": 7.24
    }
    
    def __init__(self, llm_router=None):
        super().__init__(AgentType.CFO, llm_router)
    
    async def process(
        self, 
        query: str, 
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Process financial analysis request."""
        
        findings = []
        metrics = FinancialMetrics(currency_base=ckb.currency or "USD")
        
        extracted_data = context.get("extracted_financials")
        if extracted_data:
            metrics = self._process_extracted_data(extracted_data, ckb.currency)
            findings.extend(self._generate_financial_findings(metrics))
        
        truth_scan = context.get("truth_scan")
        if truth_scan:
            metrics = self._enrich_from_truth_scan(metrics, truth_scan)
            findings.append("Enriched with Truth Scan data")
        
        if not extracted_data and not truth_scan:
            if ckb.financials:
                metrics = self._load_from_ckb(ckb.financials)
                findings.append("Using existing financial data from knowledge base")
            else:
                metrics.data_gaps.append("No financial data available - upload documents or run Truth Scan")
                metrics.confidence = "low"
        
        derived = self._compute_derived_metrics(metrics)
        findings.extend(derived)
        
        assumptions = self._identify_assumptions(metrics, context)
        risks = self._identify_risks(metrics)
        
        next_questions = []
        if metrics.data_gaps:
            next_questions.append(f"Can you provide: {', '.join(metrics.data_gaps[:3])}?")
        if isinstance(metrics.runway_months, (int, float)) and metrics.runway_months < 12:
            next_questions.append("What are your fundraising plans?")
        if not metrics.cac or not metrics.ltv:
            next_questions.append("What are your customer acquisition costs and lifetime value?")
        
        confidence = ConfidenceLevel.HIGH if metrics.confidence == "high" else \
                     ConfidenceLevel.MEDIUM if metrics.confidence == "medium" else \
                     ConfidenceLevel.LOW
        
        llm_insights = await self._generate_llm_insights(query, metrics, ckb, context)
        if llm_insights:
            findings.append(llm_insights)
        
        return AgentResponse(
            agent_type=AgentType.CFO,
            findings=findings,
            structured_output={"financials": metrics.to_dict()},
            assumptions=assumptions,
            risks=risks,
            next_questions=next_questions[:3],
            confidence=confidence,
            raw_response=llm_insights or ""
        )
    
    def _process_extracted_data(
        self, 
        data: Dict[str, Any], 
        target_currency: str
    ) -> FinancialMetrics:
        """Process extracted financial data from documents."""
        
        metrics = FinancialMetrics(currency_base=target_currency)
        source_currency = data.get("currency", "USD")
        
        def convert(value: Optional[float]) -> Optional[float]:
            if value is None:
                return None
            if source_currency == target_currency:
                return value
            if source_currency in self.FX_RATES:
                return value / self.FX_RATES[source_currency]
            return value
        
        metrics.revenue = convert(data.get("revenue"))
        metrics.cogs = convert(data.get("cogs"))
        metrics.gross_profit = convert(data.get("gross_profit"))
        metrics.gross_margin = data.get("gross_margin")
        
        metrics.opex = convert(data.get("opex"))
        metrics.payroll = convert(data.get("payroll"))
        metrics.marketing = convert(data.get("marketing"))
        metrics.other_costs = convert(data.get("other_costs"))
        
        metrics.operating_income = convert(data.get("operating_income"))
        metrics.operating_margin = data.get("operating_margin")
        metrics.net_income = convert(data.get("net_income"))
        
        metrics.cash_balance = convert(data.get("cash_balance"))
        metrics.burn_rate = convert(data.get("burn_rate"))
        metrics.runway_months = data.get("runway_months")
        
        metrics.headcount = data.get("headcount")
        metrics.arpu = convert(data.get("arpu"))
        metrics.cac = convert(data.get("cac"))
        metrics.ltv = convert(data.get("ltv"))
        metrics.churn_rate = data.get("churn_rate")
        
        metrics.mrr = convert(data.get("mrr"))
        metrics.arr = convert(data.get("arr"))
        
        metrics.periods = data.get("periods", [])
        
        for field in ["revenue", "gross_margin", "cash_balance", "burn_rate"]:
            if getattr(metrics, field) is None:
                metrics.data_gaps.append(field)
        
        if len(metrics.data_gaps) > 3:
            metrics.confidence = "low"
        elif len(metrics.data_gaps) > 0:
            metrics.confidence = "medium"
        else:
            metrics.confidence = "high"
        
        return metrics
    
    def _enrich_from_truth_scan(
        self, 
        metrics: FinancialMetrics, 
        truth_scan: Dict[str, Any]
    ) -> FinancialMetrics:
        """Enrich metrics with Truth Scan data."""
        
        ts_metrics = truth_scan.get("metrics", {})
        
        if metrics.revenue is None:
            metrics.revenue = ts_metrics.get("monthly_revenue")
        if metrics.gross_margin is None:
            metrics.gross_margin = ts_metrics.get("gross_margin")
        if metrics.operating_margin is None:
            metrics.operating_margin = ts_metrics.get("operating_margin")
        if metrics.burn_rate is None:
            metrics.burn_rate = ts_metrics.get("net_burn")
        if metrics.cash_balance is None:
            metrics.cash_balance = ts_metrics.get("cash_balance")
        if metrics.runway_months is None:
            runway_val = ts_metrics.get("runway_months")
            if isinstance(runway_val, (int, float)):
                metrics.runway_months = runway_val
        
        if ts_metrics.get("revenue_growth_mom"):
            metrics.revenue_growth_mom = ts_metrics.get("revenue_growth_mom")
        
        updated_gaps = [g for g in metrics.data_gaps if getattr(metrics, g) is None]
        metrics.data_gaps = updated_gaps
        
        return metrics
    
    def _load_from_ckb(self, financials: Dict[str, Any]) -> FinancialMetrics:
        """Load metrics from Company Knowledge Base."""
        
        metrics = FinancialMetrics()
        pnl = financials.get("pnl", {})
        balance = financials.get("balance_sheet", {})
        cashflow = financials.get("cashflow", {})
        unit_econ = financials.get("unit_economics", {})
        
        metrics.revenue = pnl.get("revenue")
        metrics.gross_margin = pnl.get("gross_margin")
        metrics.operating_margin = pnl.get("operating_margin")
        metrics.cash_balance = balance.get("cash_balance")
        metrics.burn_rate = cashflow.get("burn_rate")
        runway_val = cashflow.get("runway_months")
        if isinstance(runway_val, (int, float)):
            metrics.runway_months = runway_val
        metrics.arpu = unit_econ.get("arpu")
        metrics.cac = unit_econ.get("cac")
        metrics.ltv = unit_econ.get("ltv")
        
        metrics.confidence = financials.get("confidence", "medium")
        
        return metrics
    
    def _compute_derived_metrics(self, metrics: FinancialMetrics) -> List[str]:
        """Compute derived metrics and return insights."""
        
        insights = []
        
        if isinstance(metrics.revenue, (int, float)) and isinstance(metrics.cogs, (int, float)) and metrics.revenue > 0:
            metrics.gross_profit = metrics.revenue - metrics.cogs
            metrics.gross_margin = (metrics.gross_profit / metrics.revenue) * 100
            insights.append(f"Gross Margin: {metrics.gross_margin:.1f}%")
        
        if isinstance(metrics.revenue, (int, float)) and isinstance(metrics.opex, (int, float)) and metrics.revenue > 0:
            cogs_val = metrics.cogs if isinstance(metrics.cogs, (int, float)) else 0
            metrics.operating_income = metrics.revenue - cogs_val - metrics.opex
            metrics.operating_margin = (metrics.operating_income / metrics.revenue) * 100
            insights.append(f"Operating Margin: {metrics.operating_margin:.1f}%")
        
        if isinstance(metrics.cash_balance, (int, float)) and isinstance(metrics.burn_rate, (int, float)) and metrics.burn_rate > 0:
            metrics.runway_months = metrics.cash_balance / metrics.burn_rate
            insights.append(f"Runway: {metrics.runway_months:.1f} months")
        
        if isinstance(metrics.ltv, (int, float)) and isinstance(metrics.cac, (int, float)) and metrics.cac > 0:
            metrics.ltv_cac_ratio = metrics.ltv / metrics.cac
            insights.append(f"LTV/CAC Ratio: {metrics.ltv_cac_ratio:.1f}x")
        
        if isinstance(metrics.mrr, (int, float)) and metrics.mrr:
            metrics.arr = metrics.mrr * 12
            insights.append(f"ARR: {self.format_currency(metrics.arr, metrics.currency_base)}")
        
        return insights
    
    def _generate_financial_findings(self, metrics: FinancialMetrics) -> List[str]:
        """Generate key financial findings."""
        
        findings = []
        
        if isinstance(metrics.revenue, (int, float)) and metrics.revenue:
            findings.append(f"Monthly Revenue: {self.format_currency(metrics.revenue, metrics.currency_base)}")
        
        if isinstance(metrics.gross_margin, (int, float)):
            status = "healthy" if metrics.gross_margin > 50 else "needs improvement" if metrics.gross_margin > 30 else "concerning"
            findings.append(f"Gross Margin: {metrics.gross_margin:.1f}% ({status})")
        
        if isinstance(metrics.burn_rate, (int, float)) and metrics.burn_rate:
            findings.append(f"Monthly Burn: {self.format_currency(metrics.burn_rate, metrics.currency_base)}")
        
        if isinstance(metrics.runway_months, (int, float)):
            status = "comfortable" if metrics.runway_months > 18 else "adequate" if metrics.runway_months > 12 else "urgent"
            findings.append(f"Runway: {metrics.runway_months:.0f} months ({status})")
        
        return findings
    
    def _identify_assumptions(
        self, 
        metrics: FinancialMetrics, 
        context: Dict[str, Any]
    ) -> List[str]:
        """Identify assumptions made in the analysis."""
        
        assumptions = []
        
        source_currency = (context.get("extracted_financials") or {}).get("currency")
        if source_currency and source_currency != metrics.currency_base:
            rate = self.FX_RATES.get(source_currency, 1.0)
            assumptions.append(f"Currency converted from {source_currency} to USD at approx rate {rate}")
        
        if metrics.data_gaps:
            assumptions.append(f"Missing data: {', '.join(metrics.data_gaps)}")
        
        if not context.get("extracted_financials") and not context.get("truth_scan"):
            assumptions.append("Using previously stored financial data")
        
        return assumptions
    
    def _is_number(self, val: Any) -> bool:
        """Check if a value is a valid number (int or float)."""
        return isinstance(val, (int, float)) and not isinstance(val, bool)
    
    def _identify_risks(self, metrics: FinancialMetrics) -> List[str]:
        """Identify financial risks."""
        
        risks = []
        
        if self._is_number(metrics.runway_months):
            if metrics.runway_months < 6:
                risks.append("CRITICAL: Less than 6 months runway - immediate fundraising needed")
            elif metrics.runway_months < 12:
                risks.append("WARNING: Less than 12 months runway - start fundraising process")
        
        if self._is_number(metrics.gross_margin) and metrics.gross_margin < 30:
            risks.append("Low gross margin may limit growth investment capacity")
        
        if self._is_number(metrics.ltv_cac_ratio) and metrics.ltv_cac_ratio < 3:
            risks.append("LTV/CAC ratio below 3x indicates inefficient customer acquisition")
        
        if self._is_number(metrics.churn_rate) and metrics.churn_rate > 5:
            risks.append(f"Monthly churn of {metrics.churn_rate}% is above healthy threshold")
        
        if self._is_number(metrics.burn_rate) and self._is_number(metrics.revenue) and metrics.revenue > 0:
            burn_multiple = metrics.burn_rate / metrics.revenue
            if burn_multiple > 2:
                risks.append(f"Burn multiple of {burn_multiple:.1f}x is high - focus on efficiency")
        
        return risks
    
    async def _generate_llm_insights(
        self,
        query: str,
        metrics: FinancialMetrics,
        ckb: "CompanyKnowledgeBase",
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Generate LLM-powered financial insights using GPT-4o."""
        if not self.llm_router:
            return None
        
        metrics_summary = []
        if self._is_number(metrics.revenue):
            metrics_summary.append(f"Monthly Revenue: {self.format_currency(metrics.revenue, metrics.currency_base)}")
        if self._is_number(metrics.gross_margin):
            metrics_summary.append(f"Gross Margin: {float(metrics.gross_margin):.1f}%")
        if self._is_number(metrics.burn_rate):
            metrics_summary.append(f"Monthly Burn: {self.format_currency(metrics.burn_rate, metrics.currency_base)}")
        if self._is_number(metrics.runway_months):
            metrics_summary.append(f"Runway: {float(metrics.runway_months):.1f} months")
        if self._is_number(metrics.ltv_cac_ratio):
            metrics_summary.append(f"LTV/CAC: {float(metrics.ltv_cac_ratio):.1f}x")
        if self._is_number(metrics.churn_rate):
            metrics_summary.append(f"Monthly Churn: {float(metrics.churn_rate):.1f}%")
        
        if not metrics_summary:
            return None
        
        prompt = f"""Based on the following financial metrics for {ckb.company_name} ({ckb.industry or 'startup'}):

{chr(10).join(metrics_summary)}

User question: {query}

Provide a brief, actionable financial insight (2-3 sentences) focused on the most important financial implication. Be specific and data-driven."""
        
        try:
            response = self._call_llm(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=CFO_SYSTEM_PROMPT,
                task_type="financial_analysis",
                temperature=0.5
            )
            return response
        except Exception as e:
            self.logger.warning(f"LLM insight generation failed: {e}")
            return None
