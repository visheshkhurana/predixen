from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai-graphics"])


class ImageGenerateRequest(BaseModel):
    prompt: str
    style: str = "professional"
    aspect_ratio: str = "16:9"


@router.post("/companies/{company_id}/ai-graphics/generate")
def generate_image(
    company_id: int,
    request: ImageGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)

    from server.lib.llm.image_generator import NanoBananaImageGenerator

    try:
        generator = NanoBananaImageGenerator(
            db_session=db,
            company_id=company_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    result = generator.generate_image(
        prompt=request.prompt,
        style=request.style,
        aspect_ratio=request.aspect_ratio,
    )

    if result.get("error") and not result.get("image_base64"):
        error_msg = result["error"]
        status = 502 if "failed" in error_msg.lower() else 422
        raise HTTPException(status_code=status, detail=error_msg)

    return result


@router.get("/companies/{company_id}/ai-graphics/styles")
def get_available_styles(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)

    from server.lib.llm.image_generator import STYLE_PREFIXES, ASPECT_RATIOS

    return {
        "styles": [
            {"id": k, "name": k.replace("_", " ").title(), "description": v.strip()[:100]}
            for k, v in STYLE_PREFIXES.items()
        ],
        "aspect_ratios": [
            {"id": k, "description": v}
            for k, v in ASPECT_RATIOS.items()
        ],
    }


@router.get("/companies/{company_id}/ai-graphics/suggestions")
def get_graphic_suggestions(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)

    from server.models.truth_scan import TruthScan
    from server.api.simulations import extract_metric_value
    import json as json_mod

    latest_scan = (
        db.query(TruthScan)
        .filter(TruthScan.company_id == company_id)
        .order_by(TruthScan.created_at.desc())
        .first()
    )

    metrics = {}
    if latest_scan and latest_scan.outputs_json:
        raw = latest_scan.outputs_json
        if isinstance(raw, str):
            try:
                raw = json_mod.loads(raw)
            except Exception:
                raw = {}
        if isinstance(raw, dict):
            metrics = raw.get("metrics", raw)

    revenue = extract_metric_value(metrics.get("monthly_revenue"), 0)
    growth = extract_metric_value(metrics.get("revenue_growth"), 0)
    runway = extract_metric_value(metrics.get("runway_months"), 0)

    suggestions = [
        {
            "prompt": f"Growth trajectory chart showing {growth:.1f}% month-over-month revenue growth for a SaaS startup",
            "style": "chart",
            "category": "Growth",
        },
        {
            "prompt": "Professional startup team collaboration illustration for an investor deck cover slide",
            "style": "illustration",
            "category": "Cover",
        },
        {
            "prompt": f"Financial health dashboard visualization with ${revenue:,.0f} MRR and {runway:.0f} months runway",
            "style": "infographic",
            "category": "Metrics",
        },
        {
            "prompt": "Market positioning diagram showing competitive landscape with quadrant analysis",
            "style": "professional",
            "category": "Strategy",
        },
        {
            "prompt": "Fundraising funnel infographic showing stages from pitch to close",
            "style": "infographic",
            "category": "Fundraising",
        },
        {
            "prompt": "Product roadmap timeline with milestones and key deliverables for the next 12 months",
            "style": "minimal",
            "category": "Roadmap",
        },
    ]

    return {"suggestions": suggestions, "company_name": company.name}
