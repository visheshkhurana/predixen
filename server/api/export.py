"""
Export API endpoints for PDF generation and shareable links.
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging
import io

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.scenario import Scenario
from server.models.simulation_run import SimulationRun

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])


class ShareLinkRequest(BaseModel):
    """Request to create a shareable link."""
    resource_type: str  # scenario, simulation, dashboard
    resource_id: int
    expires_in_days: int = 7
    access_level: str = "view"  # view, comment


class ShareLinkResponse(BaseModel):
    """Response with shareable link details."""
    share_id: str
    share_url: str
    expires_at: str
    access_level: str


class PDFExportRequest(BaseModel):
    """Request to export PDF."""
    resource_type: str  # dashboard, scenario, simulation, report
    resource_id: Optional[int] = None
    include_charts: bool = True
    include_tables: bool = True
    include_summary: bool = True


share_links_cache: Dict[str, Dict[str, Any]] = {}


def generate_share_id(resource_type: str, resource_id: int, user_id: int) -> str:
    """Generate a unique share ID."""
    data = f"{resource_type}-{resource_id}-{user_id}-{uuid.uuid4()}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def verify_resource_ownership(
    db: Session, 
    resource_type: str, 
    resource_id: int, 
    user: User
) -> tuple[bool, Any]:
    """
    Verify that the current user owns or has access to the resource.
    Returns (is_authorized, resource).
    """
    if resource_type == "scenario":
        scenario = db.query(Scenario).filter(Scenario.id == resource_id).first()
        if not scenario:
            return False, None
        company = db.query(Company).filter(Company.id == scenario.company_id).first()
        if not company or company.user_id != user.id:
            return False, scenario
        return True, scenario
    
    elif resource_type == "simulation":
        sim = db.query(SimulationRun).filter(SimulationRun.id == resource_id).first()
        if not sim:
            return False, None
        scenario = db.query(Scenario).filter(Scenario.id == sim.scenario_id).first()
        if not scenario:
            return False, sim
        company = db.query(Company).filter(Company.id == scenario.company_id).first()
        if not company or company.user_id != user.id:
            return False, sim
        return True, sim
    
    elif resource_type == "dashboard":
        company = db.query(Company).filter(Company.id == resource_id).first()
        if not company or company.user_id != user.id:
            return False, company
        return True, company
    
    return False, None


@router.post("/share", response_model=ShareLinkResponse)
async def create_share_link(
    request: ShareLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a shareable link for a resource (scenario, simulation, or dashboard).
    
    Only the resource owner can create share links.
    The link can be shared with collaborators who can view or comment on the resource.
    """
    if request.resource_type not in ["scenario", "simulation", "dashboard"]:
        raise HTTPException(status_code=400, detail="Invalid resource type")
    
    is_authorized, resource = verify_resource_ownership(
        db, request.resource_type, request.resource_id, current_user
    )
    
    if resource is None:
        raise HTTPException(status_code=404, detail=f"{request.resource_type.capitalize()} not found")
    
    if not is_authorized:
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to share this resource"
        )
    
    share_id = generate_share_id(
        request.resource_type, 
        request.resource_id, 
        current_user.id
    )
    expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
    
    share_links_cache[share_id] = {
        "resource_type": request.resource_type,
        "resource_id": request.resource_id,
        "created_by": current_user.id,
        "expires_at": expires_at.isoformat(),
        "access_level": request.access_level,
    }
    
    base_url = "https://founderconsole.replit.app"
    share_url = f"{base_url}/share/{share_id}"
    
    logger.info(f"Share link created: {share_id} for {request.resource_type}/{request.resource_id} by user {current_user.id}")
    
    return ShareLinkResponse(
        share_id=share_id,
        share_url=share_url,
        expires_at=expires_at.isoformat(),
        access_level=request.access_level,
    )


@router.get("/share/{share_id}")
async def get_shared_resource(
    share_id: str,
    db: Session = Depends(get_db)
):
    """
    Access a shared resource via share link.
    
    Returns the resource data if the link is valid and not expired.
    Note: This endpoint is intentionally accessible without authentication
    to allow sharing with external collaborators.
    """
    if share_id not in share_links_cache:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    
    share_data = share_links_cache[share_id]
    
    expires_at = datetime.fromisoformat(share_data["expires_at"])
    if datetime.utcnow() > expires_at:
        del share_links_cache[share_id]
        raise HTTPException(status_code=410, detail="Share link has expired")
    
    resource_type = share_data["resource_type"]
    resource_id = share_data["resource_id"]
    
    if resource_type == "scenario":
        resource = db.query(Scenario).filter(Scenario.id == resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource no longer exists")
        return {
            "type": "scenario",
            "data": {
                "id": resource.id,
                "name": resource.name,
                "description": resource.description,
                "inputs": resource.inputs_json,
                "created_at": resource.created_at.isoformat() if resource.created_at else None,
            },
            "access_level": share_data["access_level"],
        }
    
    elif resource_type == "simulation":
        resource = db.query(SimulationRun).filter(SimulationRun.id == resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource no longer exists")
        return {
            "type": "simulation",
            "data": {
                "id": resource.id,
                "scenario_id": resource.scenario_id,
                "n_sims": resource.n_sims,
                "status": resource.status,
                "outputs": resource.outputs_json,
                "created_at": resource.created_at.isoformat() if resource.created_at else None,
            },
            "access_level": share_data["access_level"],
        }
    
    elif resource_type == "dashboard":
        resource = db.query(Company).filter(Company.id == resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource no longer exists")
        return {
            "type": "dashboard",
            "data": {
                "id": resource.id,
                "name": resource.name,
                "industry": resource.industry,
            },
            "access_level": share_data["access_level"],
        }
    
    raise HTTPException(status_code=400, detail="Invalid resource type")


@router.delete("/share/{share_id}")
async def revoke_share_link(
    share_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Revoke a shareable link.
    Only the creator of the share link can revoke it.
    """
    if share_id not in share_links_cache:
        raise HTTPException(status_code=404, detail="Share link not found")
    
    share_data = share_links_cache[share_id]
    if share_data["created_by"] != current_user.id:
        raise HTTPException(status_code=403, detail="You can only revoke your own share links")
    
    del share_links_cache[share_id]
    logger.info(f"Share link revoked: {share_id} by user {current_user.id}")
    
    return {"success": True, "message": "Share link revoked"}


@router.post("/pdf")
async def export_pdf(
    request: PDFExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a PDF export of a dashboard, scenario, or simulation report.
    
    Returns a downloadable PDF file.
    
    Note: This implementation generates a structured text report.
    In production, this would use a PDF generation library like ReportLab,
    WeasyPrint, or a headless browser to render HTML to PDF.
    """
    if request.resource_id:
        is_authorized, resource = verify_resource_ownership(
            db, request.resource_type, request.resource_id, current_user
        )
        
        if resource is None:
            raise HTTPException(status_code=404, detail="Resource not found")
        
        if not is_authorized:
            raise HTTPException(
                status_code=403, 
                detail="You don't have permission to export this resource"
            )
    
    content_parts = []
    title = "FounderConsole Report"
    
    if request.resource_type == "dashboard" and request.resource_id:
        company = db.query(Company).filter(Company.id == request.resource_id).first()
        if company:
            title = f"Dashboard Report - {company.name}"
            content_parts.append(f"Company: {company.name}")
            content_parts.append(f"Industry: {company.industry or 'Not specified'}")
            if request.include_summary:
                content_parts.append("\n=== Key Metrics ===")
                content_parts.append("(Metrics would be populated from real-time data)")
    
    elif request.resource_type == "scenario" and request.resource_id:
        scenario = db.query(Scenario).filter(Scenario.id == request.resource_id).first()
        if scenario:
            title = f"Scenario Report - {scenario.name}"
            content_parts.append(f"Scenario: {scenario.name}")
            content_parts.append(f"Description: {scenario.description or 'No description'}")
            if request.include_summary and scenario.inputs_json:
                content_parts.append("\n=== Scenario Inputs ===")
                inputs = scenario.inputs_json
                for key, value in inputs.items():
                    content_parts.append(f"  {key}: {value}")
    
    elif request.resource_type == "simulation" and request.resource_id:
        sim = db.query(SimulationRun).filter(SimulationRun.id == request.resource_id).first()
        if sim:
            title = f"Simulation Report (Run #{sim.id})"
            content_parts.append(f"Simulation ID: {sim.id}")
            content_parts.append(f"Iterations: {sim.n_sims}")
            content_parts.append(f"Status: {sim.status}")
            if request.include_summary and sim.outputs_json:
                content_parts.append("\n=== Results Summary ===")
                outputs = sim.outputs_json
                if isinstance(outputs, dict):
                    for key, value in outputs.items():
                        if key != "trajectories":  # Skip large data
                            content_parts.append(f"  {key}: {value}")
    
    report_content = f"""
================================================================================
                         FOUNDERCONSOLE
================================================================================

{title}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
Exported by: {current_user.email}

--------------------------------------------------------------------------------

{chr(10).join(content_parts)}

--------------------------------------------------------------------------------

This report was generated by FounderConsole.
For the most up-to-date information, please visit the platform.

================================================================================
"""
    
    pdf_buffer = io.BytesIO()
    pdf_buffer.write(report_content.encode('utf-8'))
    pdf_buffer.seek(0)
    
    safe_title = title.replace(" ", "_").replace("-", "_")[:30]
    filename = f"founderconsole_{safe_title}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Content-Note": "Text format - PDF generation requires additional libraries"
        }
    )


@router.get("/pdf/preview/{resource_type}/{resource_id}")
async def preview_pdf_content(
    resource_type: str,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Preview the content that would be included in a PDF export.
    """
    is_authorized, resource = verify_resource_ownership(
        db, resource_type, resource_id, current_user
    )
    
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    if not is_authorized:
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to preview this resource"
        )
    
    content = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "sections": [],
    }
    
    if resource_type == "dashboard":
        content["title"] = f"Dashboard - {resource.name}"
        content["sections"] = [
            {"type": "header", "content": resource.name},
            {"type": "info", "content": {"industry": resource.industry}},
        ]
    
    elif resource_type == "scenario":
        content["title"] = f"Scenario - {resource.name}"
        content["sections"] = [
            {"type": "header", "content": resource.name},
            {"type": "inputs", "content": resource.inputs_json or {}},
        ]
    
    elif resource_type == "simulation":
        content["title"] = f"Simulation Run #{resource.id}"
        content["sections"] = [
            {"type": "header", "content": f"Monte Carlo Simulation ({resource.n_sims} iterations)"},
            {"type": "status", "content": resource.status},
            {"type": "results", "content": resource.outputs_json or {}},
        ]
    
    return content
