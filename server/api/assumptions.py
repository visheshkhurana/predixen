"""
API endpoints for Assumption Sets management.

Provides CRUD operations for assumption sets and access to strategy templates.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import json

from server.core.db import get_db
from server.core.security import get_current_user
from server.models import User, Company
from server.models.assumption_set import AssumptionSetModel, SimulationCache
from server.simulate.assumptions import (
    AssumptionSet,
    AssumptionSetCreate,
    AssumptionSetUpdate,
    validate_assumption_set
)
from server.simulate.templates import (
    list_templates,
    get_template,
    create_from_template,
    StrategyTemplate
)


router = APIRouter(prefix="/simulator", tags=["simulator"])


def compute_cache_hash(assumptions: Dict, config: Optional[Dict] = None) -> str:
    """Compute a deterministic hash for caching."""
    data = json.dumps(assumptions, sort_keys=True)
    if config:
        data += json.dumps(config, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:64]


@router.post("/assumptions", response_model=Dict[str, Any])
async def create_assumption_set(
    company_id: int,
    request: AssumptionSetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new assumption set for a company.
    
    Can optionally be based on a template with custom overrides.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if request.template_id:
        assumption_set = create_from_template(
            template_id=request.template_id,
            name=request.name,
            overrides=request.model_dump(exclude_unset=True, exclude={"name", "template_id"})
        )
        if not assumption_set:
            raise HTTPException(status_code=400, detail=f"Template '{request.template_id}' not found")
    else:
        assumption_data = {"name": request.name}
        if request.description:
            assumption_data["description"] = request.description
        if request.revenue_growth:
            assumption_data["revenue_growth"] = request.revenue_growth
        if request.churn_rate:
            assumption_data["churn_rate"] = request.churn_rate
        if request.price_change:
            assumption_data["price_change"] = request.price_change
        if request.burn_reduction:
            assumption_data["burn_reduction"] = request.burn_reduction
        if request.headcount_plan:
            assumption_data["headcount_plan"] = request.headcount_plan
        if request.fundraise:
            assumption_data["fundraise"] = request.fundraise
        if request.capex:
            assumption_data["capex"] = request.capex
        if request.custom_fields:
            assumption_data["custom_fields"] = request.custom_fields
        if request.simulation_config:
            assumption_data["simulation_config"] = request.simulation_config
        assumption_set = AssumptionSet(**assumption_data)
    
    errors = validate_assumption_set(assumption_set)
    if errors:
        raise HTTPException(status_code=400, detail={"validation_errors": errors})
    
    assumptions_dict = assumption_set.model_dump()
    cache_hash = compute_cache_hash(assumptions_dict)
    
    db_model = AssumptionSetModel(
        company_id=company_id,
        name=assumption_set.name,
        description=assumption_set.description,
        template_id=request.template_id,
        assumptions_json=assumptions_dict,
        cache_hash=cache_hash,
        created_by=current_user.id
    )
    
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    
    return {
        "id": db_model.id,
        "name": db_model.name,
        "description": db_model.description,
        "template_id": db_model.template_id,
        "cache_hash": db_model.cache_hash,
        "assumptions": assumptions_dict,
        "created_at": db_model.created_at.isoformat() if db_model.created_at else None
    }


@router.get("/assumptions", response_model=List[Dict[str, Any]])
async def list_assumption_sets(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all assumption sets for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    assumption_sets = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.company_id == company_id
    ).order_by(AssumptionSetModel.created_at.desc()).all()
    
    return [
        {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "template_id": a.template_id,
            "cache_hash": a.cache_hash,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None
        }
        for a in assumption_sets
    ]


@router.get("/assumptions/{assumption_id}", response_model=Dict[str, Any])
async def get_assumption_set(
    assumption_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific assumption set with full details."""
    assumption = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.id == assumption_id
    ).first()
    
    if not assumption:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    company = db.query(Company).filter(
        Company.id == assumption.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "id": assumption.id,
        "name": assumption.name,
        "description": assumption.description,
        "template_id": assumption.template_id,
        "cache_hash": assumption.cache_hash,
        "assumptions": assumption.assumptions_json,
        "created_at": assumption.created_at.isoformat() if assumption.created_at else None,
        "updated_at": assumption.updated_at.isoformat() if assumption.updated_at else None
    }


@router.put("/assumptions/{assumption_id}", response_model=Dict[str, Any])
async def update_assumption_set(
    assumption_id: int,
    request: AssumptionSetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing assumption set."""
    assumption = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.id == assumption_id
    ).first()
    
    if not assumption:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    company = db.query(Company).filter(
        Company.id == assumption.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = request.model_dump(exclude_unset=True)
    current_assumptions: Dict[str, Any] = dict(assumption.assumptions_json) if assumption.assumptions_json else {}
    
    for key, value in update_data.items():
        if key in ["name", "description"]:
            setattr(assumption, key, value)
        elif value is not None:
            if hasattr(value, "model_dump"):
                current_assumptions[key] = value.model_dump()
            else:
                current_assumptions[key] = value
    
    assumption_set = AssumptionSet(**current_assumptions)
    errors = validate_assumption_set(assumption_set)
    if errors:
        raise HTTPException(status_code=400, detail={"validation_errors": errors})
    
    setattr(assumption, "assumptions_json", current_assumptions)
    setattr(assumption, "cache_hash", compute_cache_hash(current_assumptions))
    
    db.commit()
    db.refresh(assumption)
    
    return {
        "id": assumption.id,
        "name": assumption.name,
        "description": assumption.description,
        "template_id": assumption.template_id,
        "cache_hash": assumption.cache_hash,
        "assumptions": assumption.assumptions_json,
        "updated_at": assumption.updated_at.isoformat() if assumption.updated_at else None
    }


@router.delete("/assumptions/{assumption_id}")
async def delete_assumption_set(
    assumption_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an assumption set."""
    assumption = db.query(AssumptionSetModel).filter(
        AssumptionSetModel.id == assumption_id
    ).first()
    
    if not assumption:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    company = db.query(Company).filter(
        Company.id == assumption.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete(assumption)
    db.commit()
    
    return {"message": "Assumption set deleted successfully"}


@router.get("/templates", response_model=List[Dict[str, Any]])
async def get_templates(
    category: Optional[str] = Query(None, description="Filter by category: growth, efficiency, survival, balanced")
):
    """
    List all available strategy templates.
    
    Templates are pre-configured assumption sets for common startup strategies.
    """
    templates = list_templates(category=category)
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "category": t.category,
            "tags": t.tags,
            "recommended_for": t.recommended_for
        }
        for t in templates
    ]


@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_template_details(template_id: str):
    """Get full details of a strategy template including assumptions."""
    template = get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "tags": template.tags,
        "recommended_for": template.recommended_for,
        "assumptions": template.assumptions.model_dump()
    }
