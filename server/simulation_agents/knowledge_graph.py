"""
Knowledge Graph — builds a graph representation of company entities and relationships
for agent context during simulations.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def build_company_graph(db: Session, company_id: int) -> Dict[str, Any]:
    from server.models import Company, CompanyState, FinancialRecord
    from server.models.company_decision import CompanyDecision
    from sqlalchemy import desc

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return {"nodes": [], "edges": [], "entities": {}}

    nodes = []
    edges = []

    nodes.append({
        "id": f"company_{company_id}",
        "type": "company",
        "label": company.name,
        "data": {
            "industry": company.industry,
            "stage": company.stage,
            "founded": company.founded_year if hasattr(company, 'founded_year') else None,
        },
    })

    cs = db.query(CompanyState).filter(CompanyState.company_id == company_id).first()
    financials = {}
    if cs:
        try:
            state_json = json.loads(cs.state_json) if cs.state_json else {}
        except (json.JSONDecodeError, TypeError):
            state_json = {}

        financials = {
            "cash_balance": cs.cash_balance or 0,
            "monthly_burn": cs.monthly_burn or 0,
            "revenue_monthly": cs.revenue_monthly or 0,
            "growth_rate": float(cs.revenue_growth_rate) if cs.revenue_growth_rate else 0,
            "expenses_monthly": cs.expenses_monthly or 0,
        }
        financials.update({
            k: v for k, v in state_json.items()
            if k in ("grossMargin", "gross_margin", "headcount", "customers", "churn_rate",
                      "cac", "ltv", "arpu", "nrr", "arr")
        })

        metric_keys = ["revenue", "burn", "runway", "growth", "margin"]
        for mk in metric_keys:
            node_id = f"metric_{company_id}_{mk}"
            nodes.append({"id": node_id, "type": "metric", "label": mk, "data": {}})
            edges.append({"source": f"company_{company_id}", "target": node_id, "type": "HAS_METRIC"})

    records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(desc(FinancialRecord.period_start))
        .limit(6)
        .all()
    )

    team_data = _extract_team_data(db, company_id, financials)
    if team_data.get("headcount", 0) > 0:
        nodes.append({"id": f"team_{company_id}", "type": "team", "label": "Team", "data": team_data})
        edges.append({"source": f"company_{company_id}", "target": f"team_{company_id}", "type": "HAS_TEAM"})

    decisions = (
        db.query(CompanyDecision)
        .filter(CompanyDecision.company_id == company_id)
        .order_by(desc(CompanyDecision.created_at))
        .limit(10)
        .all()
    )
    for d in decisions:
        node_id = f"decision_{d.id}"
        nodes.append({
            "id": node_id,
            "type": "decision",
            "label": d.title,
            "data": {"status": d.status, "type": d.decision_type if hasattr(d, 'decision_type') else "strategic"},
        })
        edges.append({"source": f"company_{company_id}", "target": node_id, "type": "MADE_DECISION"})

    nodes.append({"id": f"market_{company_id}", "type": "market", "label": "Market", "data": {
        "industry": company.industry,
    }})
    edges.append({"source": f"company_{company_id}", "target": f"market_{company_id}", "type": "OPERATES_IN"})

    return {
        "nodes": nodes,
        "edges": edges,
        "entities": {
            "company": {"id": company_id, "name": company.name, "industry": company.industry, "stage": company.stage},
            "financials": financials,
            "team": team_data,
            "history": [_record_to_dict(r) for r in records],
            "decisions": [{"id": d.id, "title": d.title, "status": d.status} for d in decisions],
        },
    }


def get_related_entities(graph: Dict[str, Any], entity_id: str) -> List[Dict[str, Any]]:
    related = []
    for edge in graph.get("edges", []):
        if edge["source"] == entity_id:
            target = next((n for n in graph["nodes"] if n["id"] == edge["target"]), None)
            if target:
                related.append({**target, "relationship": edge["type"]})
        elif edge["target"] == entity_id:
            source = next((n for n in graph["nodes"] if n["id"] == edge["source"]), None)
            if source:
                related.append({**source, "relationship": edge["type"]})
    return related


def _extract_team_data(db: Session, company_id: int, financials: Dict) -> Dict[str, Any]:
    headcount = 0
    for key in ("headcount", "team_size", "employees"):
        if key in financials and financials[key]:
            headcount = int(financials[key])
            break
    return {"headcount": headcount}


def _record_to_dict(r) -> Dict[str, Any]:
    return {
        "period": r.period_start.isoformat() if r.period_start else None,
        "revenue": r.revenue,
        "expenses": r.total_expenses,
        "net_burn": r.net_burn,
        "runway": r.runway_months,
        "growth": r.mom_growth,
    }
