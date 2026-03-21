"""
Simulation Report — compiles agent simulation results into presentation-ready format.
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def generate_report(simulation_result: Dict[str, Any]) -> Dict[str, Any]:
    summary = simulation_result.get("summary", {})
    events = simulation_result.get("events", [])
    recommendations = simulation_result.get("recommendations", [])
    timeline = simulation_result.get("timeline", [])

    survival = summary.get("survivalProbability", 0)
    if survival >= 80:
        overall_rating = "strong"
        rating_label = "Strong Position"
        rating_color = "green"
    elif survival >= 60:
        overall_rating = "moderate"
        rating_label = "Moderate Risk"
        rating_color = "yellow"
    elif survival >= 40:
        overall_rating = "at_risk"
        rating_label = "At Risk"
        rating_color = "orange"
    else:
        overall_rating = "critical"
        rating_label = "Critical"
        rating_color = "red"

    turning_points = _identify_turning_points(timeline, events)

    agent_summary = _summarize_agent_behavior(simulation_result.get("agentStates", []))

    return {
        "overallRating": overall_rating,
        "ratingLabel": rating_label,
        "ratingColor": rating_color,
        "survivalProbability": summary.get("survivalProbability", 0),
        "fundingProbability": summary.get("fundingProbability", 0),
        "headline": _generate_headline(summary, overall_rating),
        "keyMetrics": {
            "finalCash": summary.get("finalCash", 0),
            "finalRunway": summary.get("finalRunway", 0),
            "finalRevenue": summary.get("finalRevenue", 0),
            "totalEvents": summary.get("totalEvents", 0),
            "riskEvents": summary.get("riskEvents", 0),
        },
        "turningPoints": turning_points,
        "agentSummary": agent_summary,
        "topRecommendations": recommendations[:3],
        "shareData": {
            "survivalProbability": summary.get("survivalProbability", 0),
            "topRisk": simulation_result.get("keyRisks", [{}])[0].get("description", "None identified") if simulation_result.get("keyRisks") else "None identified",
            "topRecommendation": recommendations[0]["title"] if recommendations else "Stay the course",
        },
    }


def _generate_headline(summary: Dict[str, Any], rating: str) -> str:
    survival = summary.get("survivalProbability", 0)
    if rating == "strong":
        return f"Your startup has a {survival:.0f}% survival probability — strong fundamentals detected"
    elif rating == "moderate":
        return f"Survival probability is {survival:.0f}% — some risks need attention"
    elif rating == "at_risk":
        return f"Warning: {survival:.0f}% survival probability — action needed to improve trajectory"
    else:
        return f"Critical: Only {survival:.0f}% survival probability — immediate intervention recommended"


def _identify_turning_points(
    timeline: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    points = []
    for i in range(1, len(timeline)):
        prev = timeline[i - 1]
        curr = timeline[i]

        if prev["survival"] and not curr["survival"]:
            points.append({
                "month": curr["month"],
                "type": "cash_exhaustion",
                "description": "Cash runs out — company enters survival mode",
                "severity": "critical",
            })

        if prev["cash_balance"] > 0 and curr["cash_balance"] > 0:
            cash_change = (curr["cash_balance"] - prev["cash_balance"]) / max(abs(prev["cash_balance"]), 1)
            if cash_change < -0.3:
                points.append({
                    "month": curr["month"],
                    "type": "cash_decline",
                    "description": f"Sharp cash decline of {abs(cash_change)*100:.0f}%",
                    "severity": "warning",
                })
            elif cash_change > 0.5:
                points.append({
                    "month": curr["month"],
                    "type": "cash_infusion",
                    "description": f"Major cash increase of {cash_change*100:.0f}% — possible funding event",
                    "severity": "positive",
                })

        if prev.get("runway_months", 999) > 6 and curr.get("runway_months", 0) <= 6:
            points.append({
                "month": curr["month"],
                "type": "runway_critical",
                "description": "Runway drops below 6 months — entering danger zone",
                "severity": "danger",
            })

    danger_events = [e for e in events if e["severity"] == "danger"]
    for e in danger_events[:3]:
        points.append({
            "month": e["month"],
            "type": e["eventType"],
            "description": e["description"],
            "severity": "danger",
        })

    points.sort(key=lambda p: p["month"])
    return points[:10]


def _summarize_agent_behavior(agent_states: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not agent_states:
        return {}

    summary = {}
    agent_types = ["founder", "investor", "customer", "team", "market"]

    for atype in agent_types:
        sentiments = []
        confidences = []
        for state_record in agent_states:
            agents = state_record.get("agents", {})
            if atype in agents:
                agent_data = agents[atype]
                sentiments.append(agent_data.get("sentiment", "neutral"))
                confidences.append(agent_data.get("confidence", 0.5))

        if sentiments:
            final_sentiment = sentiments[-1]
            avg_confidence = sum(confidences) / len(confidences)
            trend = "stable"
            if len(confidences) > 3:
                early = sum(confidences[:3]) / 3
                late = sum(confidences[-3:]) / 3
                if late > early + 0.1:
                    trend = "improving"
                elif late < early - 0.1:
                    trend = "declining"

            summary[atype] = {
                "finalSentiment": final_sentiment,
                "averageConfidence": round(avg_confidence, 2),
                "trend": trend,
            }

    return summary
