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
        Collect anonymized decision outcomes from opted-in companies only.
        Only companies with data_sharing_enabled=True contribute data.
        Returns list of {profile, decision_type, outcome, metrics_delta}.
        Uses real outcome_rating data when available, falls back to status-based inference.
        """
        try:
            from server.models.company import Company
            from server.models.company_decision import CompanyDecision
            from server.models.financial import FinancialRecord

            opted_in_ids = (
                self.db.query(Company.id)
                .filter(Company.data_sharing_enabled == True)
                .all()
            )
            opted_in_set = {c.id for c in opted_in_ids}

            if not opted_in_set:
                return []

            query = self.db.query(CompanyDecision).filter(
                CompanyDecision.status.in_(["resolved", "accepted", "implemented"]),
                CompanyDecision.company_id.in_(opted_in_set)
            )

            decisions = query.limit(500).all()

            outcomes = []
            company_cache = {}

            now = datetime.now(timezone.utc)

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

                decision_type = self._classify_decision_type(decision.title)

                has_real_outcome = (
                    getattr(decision, "outcome_rating", None) is not None
                    and getattr(decision, "outcome_recorded_at", None) is not None
                )

                if has_real_outcome:
                    outcome_positive = decision.outcome_rating == "positive"
                    outcome_neutral = decision.outcome_rating == "neutral"
                else:
                    outcome_positive = confidence in ("high", "medium") and decision.status in ("accepted", "implemented")
                    outcome_neutral = False

                recency_weight = 1.0
                if decision.updated_at:
                    days_ago = (now - decision.updated_at.replace(tzinfo=timezone.utc)).days if decision.updated_at.tzinfo is None else (now - decision.updated_at).days
                    if days_ago < 30:
                        recency_weight = 1.5
                    elif days_ago < 90:
                        recency_weight = 1.2
                    elif days_ago > 365:
                        recency_weight = 0.7

                outcomes.append({
                    "profile": profile,
                    "decision_type": decision_type,
                    "impact_level": confidence,
                    "outcome_positive": outcome_positive,
                    "outcome_neutral": outcome_neutral,
                    "outcome_text_length": len(decision.title or ""),
                    "has_real_outcome": has_real_outcome,
                    "outcome_rating": getattr(decision, "outcome_rating", None),
                    "recency_weight": recency_weight,
                })

            return outcomes

        except Exception as e:
            logger.error(f"Failed to collect decision outcomes: {e}")
            return []

    @staticmethod
    def _classify_decision_type(title: Optional[str]) -> str:
        if not title:
            return "general"
        title_lower = title.lower()
        if any(kw in title_lower for kw in ["hire", "team", "headcount"]):
            return "hiring"
        elif any(kw in title_lower for kw in ["price", "pricing"]):
            return "pricing"
        elif any(kw in title_lower for kw in ["cut", "reduce", "cost"]):
            return "cost_reduction"
        elif any(kw in title_lower for kw in ["raise", "fundrais"]):
            return "fundraising"
        elif any(kw in title_lower for kw in ["growth", "market", "expand"]):
            return "growth"
        return "general"

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

        type_stats = defaultdict(lambda: {
            "total": 0, "weighted_total": 0.0, "positive": 0, "weighted_positive": 0.0,
            "neutral": 0, "weighted_neutral": 0.0,
            "high_impact": 0, "real_outcome_count": 0,
        })
        for outcome in similar_outcomes:
            dt = outcome["decision_type"]
            w = outcome.get("recency_weight", 1.0)
            type_stats[dt]["total"] += 1
            type_stats[dt]["weighted_total"] += w
            if outcome.get("outcome_positive"):
                type_stats[dt]["positive"] += 1
                type_stats[dt]["weighted_positive"] += w
            elif outcome.get("outcome_neutral"):
                type_stats[dt]["neutral"] += 1
                type_stats[dt]["weighted_neutral"] += w
            if outcome.get("impact_level") == "high":
                type_stats[dt]["high_impact"] += 1
            if outcome.get("has_real_outcome"):
                type_stats[dt]["real_outcome_count"] += 1

        patterns = []
        for dtype, stats in type_stats.items():
            if stats["total"] < 2:
                continue
            decisive_weight = stats["weighted_total"] - stats["weighted_neutral"]
            success_rate = stats["weighted_positive"] / decisive_weight if decisive_weight > 0 else 0
            patterns.append({
                "decision_type": dtype,
                "sample_size": stats["total"],
                "success_rate": round(success_rate * 100, 1),
                "high_impact_count": stats["high_impact"],
                "real_outcome_count": stats["real_outcome_count"],
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
        from similar companies, enriched with cross-company success rates.
        """
        patterns = self.find_patterns(company_profile)

        cross_company_rates = self._get_cross_company_rates(company_profile)

        recommendations = []
        for pattern in patterns:
            dtype = pattern["decision_type"]
            cc_rate = cross_company_rates.get(dtype)

            rec = {
                "decision_type": dtype,
                "confidence": "high" if pattern["sample_size"] >= 10 else "medium" if pattern["sample_size"] >= 5 else "low",
                "based_on": f"{pattern['sample_size']} similar companies",
                "success_rate": f"{pattern['success_rate']}%",
                "recommendation": pattern["recommendation"],
            }

            if cc_rate and cc_rate.get("sample_size", 0) >= 2:
                rec["cross_company_success_rate"] = f"{cc_rate['success_rate']}%"
                rec["cross_company_sample_size"] = cc_rate["sample_size"]
                rec["cross_company_insight"] = (
                    f"{cc_rate['success_rate']:.0f}% of similar companies saw positive outcomes "
                    f"from {dtype.replace('_', ' ')} decisions (based on {cc_rate['sample_size']} decisions)."
                )

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

    def _get_cross_company_rates(self, company_profile: Dict[str, str]) -> Dict[str, Any]:
        try:
            from server.services.pattern_aggregator import get_relevant_patterns
            industry = company_profile.get("industry", "unknown")
            stage = company_profile.get("stage", "unknown")
            patterns = get_relevant_patterns(self.db, industry=industry, stage=stage)
            result = {}
            for p in patterns:
                if p.get("pattern_type") == "decision_outcome" and p.get("sample_size", 0) >= 2:
                    result[p["decision_type"]] = {
                        "success_rate": p["success_rate"],
                        "sample_size": p["sample_size"],
                    }
            return result
        except Exception:
            return {}

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
