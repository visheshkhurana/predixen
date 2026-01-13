"""
API endpoints for scenario templates.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from server.core.db import get_db
from server.models.company import Company
from server.models.scenario import Scenario
from server.templates import (
    get_template,
    get_all_templates,
)
from server.templates.scenarios import get_templates_by_category, get_template_summary

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/")
def list_templates():
    """
    List all available scenario templates.
    """
    return {
        "templates": get_template_summary(),
        "categories": ["conservative", "aggressive", "strategic", "stress_test"],
    }


@router.get("/{template_id}")
def get_template_details(template_id: str):
    """
    Get full details of a scenario template.
    """
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    
    return template


@router.get("/category/{category}")
def get_templates_for_category(category: str):
    """
    Get templates by category.
    """
    templates = get_templates_by_category(category)
    return {"category": category, "templates": templates}


@router.post("/companies/{company_id}/apply/{template_id}")
def apply_template(
    company_id: int,
    template_id: str,
    name_override: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Apply a template to create a new scenario for a company.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    
    # Create scenario from template
    scenario_name = name_override or f"{template['name']} Scenario"
    
    scenario = Scenario(
        company_id=company_id,
        name=scenario_name,
        description=template["description"],
        inputs_json={
            "drivers": template["inputs"],
            "events": template["events"],
            "regime_weights": template["regime_weights"],
        },
        tags=template.get("tags", []),
        version=1,
    )
    
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    return {
        "message": f"Created scenario from template: {template['name']}",
        "scenario_id": scenario.id,
        "scenario_name": scenario_name,
        "template_id": template_id,
    }


@router.post("/companies/{company_id}/bulk-apply")
def apply_multiple_templates(
    company_id: int,
    template_ids: List[str],
    db: Session = Depends(get_db),
):
    """
    Apply multiple templates to create comparison scenarios.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    created = []
    errors = []
    
    for template_id in template_ids:
        template = get_template(template_id)
        if not template:
            errors.append(f"Template not found: {template_id}")
            continue
        
        scenario = Scenario(
            company_id=company_id,
            name=f"{template['name']} Scenario",
            description=template["description"],
            inputs_json={
                "drivers": template["inputs"],
                "events": template["events"],
                "regime_weights": template["regime_weights"],
            },
            tags=template.get("tags", []),
            version=1,
        )
        
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        
        created.append({
            "scenario_id": scenario.id,
            "template_id": template_id,
            "name": scenario.name,
        })
    
    return {
        "created": created,
        "errors": errors,
        "total_created": len(created),
    }
