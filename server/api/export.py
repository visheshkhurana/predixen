"""
Export API endpoints for PDF generation and shareable links.
"""

import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Response
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


@router.post("/share", response_model=ShareLinkResponse)
async def create_share_link(
    request: ShareLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a shareable link for a resource (scenario, simulation, or dashboard).
    
    The link can be shared with collaborators who can view or comment on the resource.
    """
    if request.resource_type == "scenario":
        resource = db.query(Scenario).filter(Scenario.id == request.resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="Scenario not found")
    elif request.resource_type == "simulation":
        resource = db.query(SimulationRun).filter(SimulationRun.id == request.resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="Simulation not found")
    elif request.resource_type == "dashboard":
        resource = db.query(Company).filter(Company.id == request.resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="Company not found")
    else:
        raise HTTPException(status_code=400, detail="Invalid resource type")
    
    share_id = generate_share_id(request.resource_type, request.resource_id, current_user.id)
    expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
    
    share_links_cache[share_id] = {
        "resource_type": request.resource_type,
        "resource_id": request.resource_id,
        "created_by": current_user.id,
        "expires_at": expires_at.isoformat(),
        "access_level": request.access_level,
    }
    
    base_url = "https://predixen.replit.app"
    share_url = f"{base_url}/share/{share_id}"
    
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
            raise HTTPException(status_code=404, detail="Resource not found")
        return {
            "type": "scenario",
            "data": {
                "id": resource.id,
                "name": resource.name,
                "inputs": resource.inputs_json,
                "created_at": resource.created_at.isoformat() if resource.created_at else None,
            },
            "access_level": share_data["access_level"],
        }
    
    elif resource_type == "simulation":
        resource = db.query(SimulationRun).filter(SimulationRun.id == resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        return {
            "type": "simulation",
            "data": {
                "id": resource.id,
                "scenario_id": resource.scenario_id,
                "results": resource.results_json,
                "created_at": resource.created_at.isoformat() if resource.created_at else None,
            },
            "access_level": share_data["access_level"],
        }
    
    elif resource_type == "dashboard":
        resource = db.query(Company).filter(Company.id == resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        return {
            "type": "dashboard",
            "data": {
                "id": resource.id,
                "name": resource.name,
                "metrics": resource.metadata_json,
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
    """
    if share_id not in share_links_cache:
        raise HTTPException(status_code=404, detail="Share link not found")
    
    share_data = share_links_cache[share_id]
    if share_data["created_by"] != current_user.id:
        raise HTTPException(status_code=403, detail="You can only revoke your own share links")
    
    del share_links_cache[share_id]
    
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
    
    Note: This is a placeholder implementation. In production, this would use
    a PDF generation library like ReportLab, WeasyPrint, or a headless browser
    to render HTML to PDF.
    """
    content_parts = []
    title = "Predixen Report"
    
    if request.resource_type == "dashboard":
        company = db.query(Company).filter(Company.id == request.resource_id).first()
        if company:
            title = f"Dashboard Report - {company.name}"
            content_parts.append(f"Company: {company.name}")
            if request.include_summary:
                content_parts.append("\n=== Key Metrics ===")
                metrics = company.metadata_json or {}
                for key, value in metrics.items():
                    content_parts.append(f"  {key}: {value}")
    
    elif request.resource_type == "scenario":
        scenario = db.query(Scenario).filter(Scenario.id == request.resource_id).first()
        if scenario:
            title = f"Scenario Report - {scenario.name}"
            content_parts.append(f"Scenario: {scenario.name}")
            if request.include_summary:
                content_parts.append("\n=== Scenario Inputs ===")
                inputs = scenario.inputs_json or {}
                for key, value in inputs.items():
                    content_parts.append(f"  {key}: {value}")
    
    elif request.resource_type == "simulation":
        sim = db.query(SimulationRun).filter(SimulationRun.id == request.resource_id).first()
        if sim:
            title = f"Simulation Report"
            content_parts.append("Simulation Results")
            if request.include_summary:
                results = sim.results_json or {}
                content_parts.append("\n=== Results Summary ===")
                if "summary" in results:
                    for key, value in results["summary"].items():
                        content_parts.append(f"  {key}: {value}")
    
    report_content = f"""
PREDIXEN INTELLIGENCE OS
========================
{title}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

{chr(10).join(content_parts)}

---
This report was generated by Predixen Intelligence OS.
For the most up-to-date information, please visit the platform.
"""
    
    pdf_buffer = io.BytesIO()
    pdf_buffer.write(report_content.encode('utf-8'))
    pdf_buffer.seek(0)
    
    filename = f"predixen_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Note": "PDF generation placeholder - would use PDF library in production"
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
    content = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "sections": [],
    }
    
    if resource_type == "dashboard":
        company = db.query(Company).filter(Company.id == resource_id).first()
        if company:
            content["title"] = f"Dashboard - {company.name}"
            content["sections"] = [
                {"type": "header", "content": company.name},
                {"type": "metrics", "content": company.metadata_json or {}},
            ]
    
    elif resource_type == "scenario":
        scenario = db.query(Scenario).filter(Scenario.id == resource_id).first()
        if scenario:
            content["title"] = f"Scenario - {scenario.name}"
            content["sections"] = [
                {"type": "header", "content": scenario.name},
                {"type": "inputs", "content": scenario.inputs_json or {}},
            ]
    
    elif resource_type == "simulation":
        sim = db.query(SimulationRun).filter(SimulationRun.id == resource_id).first()
        if sim:
            content["title"] = "Simulation Report"
            content["sections"] = [
                {"type": "header", "content": "Monte Carlo Simulation Results"},
                {"type": "results", "content": sim.results_json or {}},
            ]
    
    return content
