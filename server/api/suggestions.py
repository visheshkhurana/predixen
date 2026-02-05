"""
API endpoints for Metric Suggestions.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from server.core.db import get_db
from server.core.security import get_current_user
from server.models import User, Company
from server.metrics.suggestions.service import SuggestionService
from server.metrics.suggestions.capability import CapabilityDiscovery

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


def _get_company_or_404(company_id: int, user: User, db: Session) -> Company:
    """Get company and verify user has access."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


class GenerateRequest(BaseModel):
    data_source_id: Optional[int] = None
    adapter_key: Optional[str] = None
    force_refresh: bool = False


class AcceptRequest(BaseModel):
    auto_compute: bool = False


class DismissRequest(BaseModel):
    reason: Optional[str] = None


@router.post("/generate")
async def generate_suggestions(
    request: GenerateRequest,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate metric suggestions for a company based on connected data sources.
    Runs capability discovery if needed and applies deterministic rules.
    """
    _get_company_or_404(company_id, current_user, db)
    
    service = SuggestionService(db)
    
    suggestions = service.generate_suggestions(
        company_id=company_id,
        data_source_id=request.data_source_id,
        adapter_key=request.adapter_key,
        force_refresh=request.force_refresh,
    )
    
    return {
        "generated_count": len(suggestions),
        "suggestions": suggestions,
    }


@router.get("")
async def list_suggestions(
    company_id: int,
    status: Optional[str] = Query(None, description="Filter by status: new, accepted, dismissed, blocked"),
    category: Optional[str] = Query(None, description="Filter by category: Finance, Growth, Sales, Product"),
    data_source_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List metric suggestions for a company with optional filters.
    """
    _get_company_or_404(company_id, current_user, db)
    
    service = SuggestionService(db)
    
    suggestions = service.list_suggestions(
        company_id=company_id,
        status=status,
        category=category,
        data_source_id=data_source_id,
    )
    
    return suggestions


@router.get("/{suggestion_id}")
async def get_suggestion(
    suggestion_id: int,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single suggestion by ID."""
    _get_company_or_404(company_id, current_user, db)
    
    service = SuggestionService(db)
    suggestion = service.get_suggestion(suggestion_id, company_id)
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    return suggestion


@router.post("/{suggestion_id}/accept")
async def accept_suggestion(
    suggestion_id: int,
    request: AcceptRequest,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accept a suggestion and create the corresponding metric.
    Optionally triggers automatic computation.
    """
    _get_company_or_404(company_id, current_user, db)
    
    service = SuggestionService(db)
    
    try:
        result = service.accept_suggestion(
            suggestion_id=suggestion_id,
            company_id=company_id,
            user_id=current_user.id,
            auto_compute=request.auto_compute,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{suggestion_id}/dismiss")
async def dismiss_suggestion(
    suggestion_id: int,
    request: DismissRequest,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dismiss a suggestion (won't be shown again unless regenerated).
    """
    _get_company_or_404(company_id, current_user, db)
    
    service = SuggestionService(db)
    
    try:
        result = service.dismiss_suggestion(
            suggestion_id=suggestion_id,
            company_id=company_id,
            user_id=current_user.id,
            reason=request.reason,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{suggestion_id}/explain")
async def explain_suggestion(
    suggestion_id: int,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed explanation for a suggestion including:
    - Why it was suggested
    - What data fields are used
    - Dependencies required
    - Compiled SQL preview (for aggregate metrics)
    """
    _get_company_or_404(company_id, current_user, db)
    
    service = SuggestionService(db)
    
    try:
        explanation = service.explain_suggestion(suggestion_id, company_id)
        return explanation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/capabilities/list")
async def list_capabilities(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all discovered capabilities for a company.
    """
    _get_company_or_404(company_id, current_user, db)
    
    capabilities = CapabilityDiscovery.get_all_capabilities(db, company_id)
    
    return {
        "adapters": list(capabilities.keys()),
        "capabilities": capabilities,
    }


@router.post("/capabilities/discover")
async def discover_capabilities(
    adapter_key: str,
    company_id: int,
    data_source_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually trigger capability discovery for an adapter.
    """
    _get_company_or_404(company_id, current_user, db)
    
    capabilities = CapabilityDiscovery.discover_for_adapter(
        adapter_key=adapter_key,
        config={},
        db=db,
        company_id=company_id,
        data_source_id=data_source_id,
    )
    
    return {
        "adapter_key": adapter_key,
        "capabilities": capabilities,
    }
