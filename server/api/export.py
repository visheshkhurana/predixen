"""
Export API endpoints for PDF generation.
"""

from datetime import datetime
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


class PDFExportRequest(BaseModel):
    """Request to export PDF."""
    resource_type: str  # dashboard, scenario, simulation, report
    resource_id: Optional[int] = None
    include_charts: bool = True
    include_tables: bool = True
    include_summary: bool = True


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
