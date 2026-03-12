"""
Cross-Company Decision Pattern Engine.

Analyzes aggregate decision outcomes across companies to identify
patterns — which decisions led to positive outcomes for similar
company profiles. All data is anonymized.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


COMPANY_PROFILE_FIELDS = ["stage", "industry", "employee_range", "revenue_range"]


def _classify_revenue_range(revenue: float) -> str:
    if revenue <= 0:
        return "pre_revenue"
    elif revenue < 10000:
        return "early_revenue"
    elif revenue < 100000:
        return "growing"
    elif revenue < 1000000:
        return "scaling"
    return "mature"


def _classify_employee_range(headcount: int) -> str:
    if headcount <= 5:
        return "founding_team"
    elif headcount <= 15:
        return "small"
    elif headcount <= 50:
        return "mid"
    elif headcount <= 200:
        return "growth"
    return "enterprise"


def build_company_profile(company_data: Dict[str, Any]) -> Dict[str, str]:
    """Build an anonymized company profile for pattern matching."""
    revenue = company_data.get("revenue", 0)
    headcount = company_data.get("headcount", 0)

    return {
        "stage": company_data.get("stage", "unknown"),
        "industry": company_data.get("industry", "unknown").lower(),
        "revenue_range": _classify_revenue_range(revenue),
        "employee_range": _classify_employee_range(headcount),
    }


def compute_similarity(profile_a: Dict[str, str], profile_b: Dict[str, str]) -> float:
    """Compute similarity score between two company profiles (0.0 to 1.0)."""
    matches = 0
    total = len(COMPANY_PROFILE_FIELDS)

    for field in COMPANY_PROFILE_FIELDS:
        val_a = profile_a.get(field, "")
        val_b = profile_b.get(field, "")
        if val_a and val_b and val_a == val_b:
            matches += 1

    return matches / total if total > 0 else 0.0


class DecisionPatternEngine:
    """
    Engine that identifies decision patterns from aggregate company data.

    All analysis is performed on anonymized profiles — no company names,
    no specific revenue numbers, no identifiable information is exposed.
    """

    def __init__(self, db: Session):
        self.db = db

    def collect_decision_outcomes(self) -> List[Dict[str, Any]]:
        """
        Collect anonymized decision outcomes from all companies.
        Returns list of {profile, decision_type, outcome, metrics_delta}.
        """
        try:
            from server.models.company import Company
            from server.models.company_decision import CompanyDecision
            from server.models.financial import FinancialRecord

            decisions = (
                self.db.query(CompanyDecision)
                .filter(CompanyDecision.status.in_(["resolved", "accepted", "implemented"]))
                .limit(500)
                .all()
            )

            outcomes = []
            company_cache = {}

            for decision in decisions:
                cid = decision.company_id
                if cid not in company_cache:
                    company = self.db.query(Company).filter(Company.id == cid).first()
                    if not company:
                        continue

                    latest_fin = (
                        self.db.query(FinancialRecord)
                        .filter(FinancialRecord.company_id == cid)
                        .order_by(FinancialRecord.period_start.desc())
                        .first()
                    )

                    company_cache[cid] = build_company_profile({
                        "stage": getattr(company, "stage", "unknown") or "unknown",
                        "industry": getattr(company, "industry", "unknown") or "unknown",
                        "revenue": float(latest_fin.revenue or 0) if latest_fin else 0,
                        "headcount": int(latest_fin.headcount or 0) if latest_fin and hasattr(latest_fin, 'headcount') else 0,
                    })

                profile = company_cache[cid]

                confidence = getattr(decision, "confidence", "medium") or "medium"

                decision_type = "general"
                title_lower = (decision.title or "").lower()
                if any(kw in title_lower for kw in ["hire", "team", "headcount"]):
                    decision_type = "hiring"
                elif any(kw in title_lower for kw in ["price", "pricing"]):
                    decision_type = "pricing"
                elif any(kw in title_lower for kw in ["cut", "reduce", "cost"]):
                    decision_type = "cost_reduction"
                elif any(kw in title_lower for kw in ["raise", "fundrais"]):
                    decision_type = "fundraising"
                elif any(kw in title_lower for kw in ["growth", "market", "expand"]):
                    decision_type = "growth"

                outcome_positive = confidence in ("high", "medium") and decision.status in ("accepted", "implemented")

                outcomes.append({
                    "profile": profile,
                    "decision_type": decision_type,
                    "impact_level": confidence,
                    "outcome_positive": outcome_positive,
                    "outcome_text_length": len(decision.title or ""),
                })

            return outcomes

        except Exception as e:
            logger.error(f"Failed to collect decision outcomes: {e}")
            return []

    def find_patterns(
        self,
        company_profile: Dict[str, str],
        min_similarity: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Find decision patterns from similar companies.
        Returns anonymized pattern insights.
        """
        all_outcomes = self.collect_decision_outcomes()
        if not all_outcomes:
            return self._get_default_patterns(company_profile)

        similar_outcomes = []
        for outcome in all_outcomes:
            similarity = compute_similarity(company_profile, outcome["profile"])
            if similarity >= min_similarity:
                similar_outcomes.append({**outcome, "similarity": similarity})

        if len(similar_outcomes) < 3:
            return self._get_default_patterns(company_profile)

        type_stats = defaultdict(lambda: {"total": 0, "positive": 0, "high_impact": 0})
        for outcome in similar_outcomes:
            dt = outcome["decision_type"]
            type_stats[dt]["total"] += 1
            if outcome.get("outcome_positive"):
                type_stats[dt]["positive"] += 1
            if outcome.get("impact_level") == "high":
                type_stats[dt]["high_impact"] += 1

        patterns = []
        for dtype, stats in type_stats.items():
            if stats["total"] < 2:
                continue
            success_rate = stats["positive"] / stats["total"] if stats["total"] > 0 else 0
            patterns.append({
                "decision_type": dtype,
                "sample_size": stats["total"],
                "success_rate": round(success_rate * 100, 1),
                "high_impact_count": stats["high_impact"],
                "recommendation": self._pattern_recommendation(dtype, success_rate, company_profile),
            })

        patterns.sort(key=lambda p: (p["success_rate"], p["sample_size"]), reverse=True)
        return patterns[:5]

    def get_recommendations(
        self,
        company_profile: Dict[str, str],
        current_challenges: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get actionable recommendations based on decision patterns
        from similar companies.
        """
        patterns = self.find_patterns(company_profile)

        recommendations = []
        for pattern in patterns:
            rec = {
                "decision_type": pattern["decision_type"],
                "confidence": "high" if pattern["sample_size"] >= 10 else "medium" if pattern["sample_size"] >= 5 else "low",
                "based_on": f"{pattern['sample_size']} similar companies",
                "success_rate": f"{pattern['success_rate']}%",
                "recommendation": pattern["recommendation"],
            }
            recommendations.append(rec)

        if current_challenges:
            challenge_recs = self._challenge_specific_recs(
                current_challenges, company_profile
            )
            recommendations.extend(challenge_recs)

        return recommendations

    def _pattern_recommendation(
        self,
        decision_type: str,
        success_rate: float,
        profile: Dict[str, str],
    ) -> str:
        stage = profile.get("stage", "unknown")
        rev_range = profile.get("revenue_range", "unknown")

        recs = {
            "hiring": (
                f"Companies at {stage} stage in the {rev_range} range that invested in hiring "
                f"saw {success_rate*100:.0f}% positive outcomes. "
                "Consider structured hiring plans with clear ROI metrics per role."
            ),
            "pricing": (
                f"Pricing changes had a {success_rate*100:.0f}% success rate among similar companies. "
                "Test price increases with a small cohort before full rollout."
            ),
            "cost_reduction": (
                f"Cost optimization decisions succeeded {success_rate*100:.0f}% of the time. "
                "Focus on vendor renegotiation and non-critical spend before headcount changes."
            ),
            "fundraising": (
                f"Fundraising decisions had {success_rate*100:.0f}% positive outcomes. "
                "Ensure 6+ months runway before starting the process."
            ),
            "growth": (
                f"Growth initiatives succeeded {success_rate*100:.0f}% of the time. "
                "Prioritize channels with proven unit economics before scaling."
            ),
        }

        return recs.get(
            decision_type,
            f"This type of decision had a {success_rate*100:.0f}% success rate among similar companies."
        )

    def _get_default_patterns(
        self, profile: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Return default patterns based on industry benchmarks when insufficient data."""
        stage = profile.get("stage", "seed")
        industry = profile.get("industry", "saas")

        defaults = [
            {
                "decision_type": "cost_reduction",
                "sample_size": 0,
                "success_rate": 75.0,
                "high_impact_count": 0,
                "recommendation": "Cost optimization is the highest-leverage move for early-stage companies. "
                                  "Focus on extending runway before growth investments.",
                "source": "industry_benchmark",
            },
            {
                "decision_type": "pricing",
                "sample_size": 0,
                "success_rate": 70.0,
                "high_impact_count": 0,
                "recommendation": "Most startups underprice. A 10-20% price increase typically sees "
                                  "less than 5% churn — a significant net revenue gain.",
                "source": "industry_benchmark",
            },
            {
                "decision_type": "hiring",
                "sample_size": 0,
                "success_rate": 60.0,
                "high_impact_count": 0,
                "recommendation": "Hire for revenue-generating roles first (sales, customer success) "
                                  "before support functions. Each hire should have a clear revenue target.",
                "source": "industry_benchmark",
            },
        ]

        return defaults

    def _challenge_specific_recs(
        self,
        challenges: List[str],
        profile: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        recs = []
        for challenge in challenges:
            ch = challenge.lower()
            if "churn" in ch:
                recs.append({
                    "decision_type": "retention",
                    "confidence": "medium",
                    "based_on": "industry best practices",
                    "success_rate": "N/A",
                    "recommendation": "Deploy customer health scoring and proactive outreach. "
                                      "Companies that implemented structured CS programs reduced churn by 20-30%.",
                })
            elif "runway" in ch:
                recs.append({
                    "decision_type": "runway_extension",
                    "confidence": "high",
                    "based_on": "industry best practices",
                    "success_rate": "N/A",
                    "recommendation": "Implement immediate cost optimization: vendor renegotiation, "
                                      "hiring pause, and focus on revenue-generating activities only.",
                })
        return recs
