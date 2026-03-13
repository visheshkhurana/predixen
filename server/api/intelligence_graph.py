"""
Founder Intelligence Graph API.

Provides endpoints for cross-company intelligence, similarity matching,
decision pattern discovery, strategy insights, and growth benchmarks.
"""
from fastapi import APIRouter, Depends, HTTPException
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
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Intelligence Graph"])


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
