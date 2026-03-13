"""
Founder Intelligence Graph API.

Provides endpoints for cross-company intelligence, similarity matching,
decision pattern discovery, strategy insights, growth benchmarks,
event ingestion pipeline, Digital Twin sync, AI analysis, simulation
recommendations, and network visualization.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import logging

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.services.intelligence_graph import (
    get_company_profile,
    find_similar_companies,
    get_decision_patterns,
    get_strategy_insights,
    get_growth_benchmarks,
    get_intelligence_summary,
    process_graph_event,
    sync_twin_to_graph,
    generate_ai_strategy_insights,
    get_simulation_graph_recommendations,
    get_network_graph_data,
    ensure_graph_indexes,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Intelligence Graph"])


class GraphEventRequest(BaseModel):
    event_type: str
    payload: Dict[str, Any] = {}


class SimRecommendationRequest(BaseModel):
    simulation_result: Optional[Dict[str, Any]] = None


@router.get("/companies/{company_id}/intelligence/summary")
def api_intelligence_summary(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    try:
        return get_intelligence_summary(db, company_id)
    except Exception as e:
        logger.error(f"Intelligence summary error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate intelligence summary")


@router.get("/companies/{company_id}/intelligence/similar")
def api_similar_companies(
    company_id: int,
    min_similarity: float = 0.25,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    try:
        similar = find_similar_companies(db, company_id, min_similarity, limit)
        profile = get_company_profile(db, company_id)
        return {
            "your_profile": profile,
            "similar_companies": similar,
            "count": len(similar),
        }
    except Exception as e:
        logger.error(f"Similar companies error: {e}")
        raise HTTPException(status_code=500, detail="Failed to find similar companies")


@router.get("/companies/{company_id}/intelligence/patterns")
def api_decision_patterns(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    try:
        return get_decision_patterns(db, company_id)
    except Exception as e:
        logger.error(f"Decision patterns error: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze decision patterns")


@router.get("/companies/{company_id}/intelligence/strategies")
def api_strategy_insights(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    try:
        return get_strategy_insights(db, company_id)
    except Exception as e:
        logger.error(f"Strategy insights error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate strategy insights")


@router.get("/companies/{company_id}/intelligence/benchmarks")
def api_growth_benchmarks(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    try:
        return get_growth_benchmarks(db, company_id)
    except Exception as e:
        logger.error(f"Growth benchmarks error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate benchmarks")


@router.post("/companies/{company_id}/intelligence/events")
def api_process_graph_event(
    company_id: int,
    request: GraphEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    try:
        return process_graph_event(db, company_id, request.event_type, request.payload)
    except Exception as e:
        logger.error(f"Graph event processing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process graph event")


@router.post("/companies/{company_id}/intelligence/sync")
def api_sync_twin_to_graph(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    try:
        return sync_twin_to_graph(db, company_id)
    except Exception as e:
        logger.error(f"Twin-to-graph sync error: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync Digital Twin to graph")


@router.get("/companies/{company_id}/intelligence/ai-insights")
def api_ai_strategy_insights(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    try:
        return generate_ai_strategy_insights(db, company_id)
    except Exception as e:
        logger.error(f"AI strategy insights error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate AI insights")


@router.post("/companies/{company_id}/intelligence/recommendations")
def api_simulation_recommendations(
    company_id: int,
    request: SimRecommendationRequest = SimRecommendationRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    try:
        return get_simulation_graph_recommendations(db, company_id, request.simulation_result)
    except Exception as e:
        logger.error(f"Simulation recommendations error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")


@router.get("/companies/{company_id}/intelligence/network")
def api_network_graph(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    try:
        return get_network_graph_data(db, company_id)
    except Exception as e:
        logger.error(f"Network graph error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate network graph")


@router.post("/companies/{company_id}/intelligence/ensure-indexes")
def api_ensure_indexes(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not getattr(current_user, 'is_platform_admin', False):
        raise HTTPException(status_code=403, detail="Admin access required")
    get_user_company(db, company_id, current_user)
    try:
        return ensure_graph_indexes(db)
    except Exception as e:
        logger.error(f"Index creation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create indexes")
