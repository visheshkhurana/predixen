"""Competition-tracking API: manage competitors a founder watches and collect
signals (news / blog posts / social mentions) about them via web search."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
import re
import json
import logging

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.models.company import Company
from server.models.competitor import Competitor, CompetitorSignal

logger = logging.getLogger(__name__)
router = APIRouter(tags=["competitors"])


# ----------------------------- Schemas -----------------------------
class LinkItem(BaseModel):
    label: Optional[str] = None
    url: str


class CompetitorCreate(BaseModel):
    name: str
    website: Optional[str] = None
    blog_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    x_handle: Optional[str] = None
    other_links: Optional[List[LinkItem]] = None
    description: Optional[str] = None
    notes: Optional[str] = None


class CompetitorUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    blog_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    x_handle: Optional[str] = None
    other_links: Optional[List[LinkItem]] = None
    description: Optional[str] = None
    notes: Optional[str] = None


# ----------------------------- Serializers -----------------------------
def _competitor_dict(c: Competitor, signal_count: int = 0) -> Dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "website": c.website,
        "blog_url": c.blog_url,
        "linkedin_url": c.linkedin_url,
        "x_handle": c.x_handle,
        "other_links": c.other_links or [],
        "description": c.description,
        "notes": c.notes,
        "last_scanned_at": c.last_scanned_at.isoformat() if c.last_scanned_at else None,
        "signal_count": signal_count,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _signal_dict(s: CompetitorSignal) -> Dict[str, Any]:
    return {
        "id": s.id,
        "competitor_id": s.competitor_id,
        "source_type": s.source_type,
        "title": s.title,
        "url": s.url,
        "summary": s.summary,
        "sentiment": s.sentiment,
        "impact": s.impact,
        "published_at": s.published_at.isoformat() if s.published_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# ----------------------------- Web-search scan -----------------------------
def _get_openai_client():
    api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    if not api_key:
        return None
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    """Leniently pull a JSON array out of an LLM response (handles ``` fences)."""
    if not text:
        return []
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        data = json.loads(text[start:end + 1])
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _scan_competitor_web(competitor: Competitor) -> List[Dict[str, Any]]:
    """Use OpenAI's web-search model to gather recent signals about a competitor.

    gpt-4o-search-preview performs real web search. It does NOT accept a
    temperature param, so we don't send one.
    """
    client = _get_openai_client()
    if client is None:
        raise RuntimeError("OpenAI is not configured (set OPENAI_API_KEY)")

    handles = []
    if competitor.website:
        handles.append(f"website {competitor.website}")
    if competitor.blog_url:
        handles.append(f"blog {competitor.blog_url}")
    if competitor.linkedin_url:
        handles.append(f"LinkedIn {competitor.linkedin_url}")
    if competitor.x_handle:
        handles.append(f"X/Twitter {competitor.x_handle}")
    ctx = f" ({'; '.join(handles)})" if handles else ""

    prompt = (
        f'Search the web for the most recent notable updates about the company "{competitor.name}"{ctx}. '
        "Look for product launches, funding, hiring, pricing changes, partnerships, press, "
        "blog posts, and notable LinkedIn/X posts. "
        "Return ONLY a JSON array (no prose, no markdown) of up to 6 items, each with keys: "
        '"title" (str), "url" (the real source URL), '
        '"source_type" (one of "news","blog","linkedin","x","web"), '
        '"summary" (one-sentence factual summary), '
        '"sentiment" (one of "positive","neutral","negative" from the competitor\'s POV), '
        '"impact" (one short sentence on why it matters to a rival founder). '
        "Only include real, recent, verifiable items with real URLs. If you find nothing, return []."
    )

    # Try the full search model, fall back to the mini one (broadly allowed in
    # restricted projects). Both do real web search; neither accepts temperature.
    resp = None
    last_err = None
    for search_model in ("gpt-4o-search-preview", "gpt-4o-mini-search-preview"):
        try:
            resp = client.chat.completions.create(
                model=search_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
            )
            break
        except Exception as e:
            last_err = e
            continue
    if resp is None:
        raise last_err or RuntimeError("No web-search model available")
    content = resp.choices[0].message.content if resp.choices else ""
    items = _extract_json_array(content or "")

    cleaned: List[Dict[str, Any]] = []
    allowed_sources = {"news", "blog", "linkedin", "x", "web"}
    for it in items[:8]:
        if not isinstance(it, dict) or not (it.get("title") or it.get("summary")):
            continue
        st = str(it.get("source_type", "web")).lower()
        cleaned.append({
            "title": (it.get("title") or "")[:500],
            "url": (it.get("url") or "")[:1000] or None,
            "source_type": st if st in allowed_sources else "web",
            "summary": (it.get("summary") or "")[:1000] or None,
            "sentiment": str(it.get("sentiment", "neutral")).lower(),
            "impact": (it.get("impact") or "")[:1000] or None,
        })
    return cleaned


def _dedupe_key(source_type: str, title: str, url: str) -> str:
    return f"{source_type}|{(url or title or '').strip().lower()}"


# ----------------------------- CRUD endpoints -----------------------------
@router.get("/companies/{company_id}/competitors")
def list_competitors(company_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = get_user_company(db, company_id, current_user)
    comps = db.query(Competitor).filter(Competitor.company_id == company.id).order_by(Competitor.created_at.desc()).all()
    result = []
    for c in comps:
        count = db.query(CompetitorSignal).filter(CompetitorSignal.competitor_id == c.id).count()
        result.append(_competitor_dict(c, count))
    return {"competitors": result}


@router.post("/companies/{company_id}/competitors")
def create_competitor(company_id: int, req: CompetitorCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = get_user_company(db, company_id, current_user)
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="Competitor name is required")
    comp = Competitor(
        company_id=company.id,
        name=req.name.strip(),
        website=req.website,
        blog_url=req.blog_url,
        linkedin_url=req.linkedin_url,
        x_handle=req.x_handle,
        other_links=[l.model_dump() for l in req.other_links] if req.other_links else None,
        description=req.description,
        notes=req.notes,
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return _competitor_dict(comp, 0)


@router.put("/companies/{company_id}/competitors/{competitor_id}")
def update_competitor(company_id: int, competitor_id: int, req: CompetitorUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = get_user_company(db, company_id, current_user)
    comp = db.query(Competitor).filter(Competitor.id == competitor_id, Competitor.company_id == company.id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")
    data = req.model_dump(exclude_unset=True)
    if "other_links" in data and data["other_links"] is not None:
        data["other_links"] = [l if isinstance(l, dict) else l.model_dump() for l in req.other_links]
    for k, v in data.items():
        setattr(comp, k, v)
    db.commit()
    db.refresh(comp)
    count = db.query(CompetitorSignal).filter(CompetitorSignal.competitor_id == comp.id).count()
    return _competitor_dict(comp, count)


@router.delete("/companies/{company_id}/competitors/{competitor_id}")
def delete_competitor(company_id: int, competitor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = get_user_company(db, company_id, current_user)
    comp = db.query(Competitor).filter(Competitor.id == competitor_id, Competitor.company_id == company.id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")
    db.query(CompetitorSignal).filter(CompetitorSignal.competitor_id == comp.id).delete()
    db.delete(comp)
    db.commit()
    return {"deleted": True}


@router.get("/companies/{company_id}/competitors/{competitor_id}/signals")
def list_signals(company_id: int, competitor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = get_user_company(db, company_id, current_user)
    comp = db.query(Competitor).filter(Competitor.id == competitor_id, Competitor.company_id == company.id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")
    signals = db.query(CompetitorSignal).filter(
        CompetitorSignal.competitor_id == comp.id
    ).order_by(CompetitorSignal.created_at.desc()).limit(50).all()
    return {"signals": [_signal_dict(s) for s in signals]}


@router.post("/companies/{company_id}/competitors/{competitor_id}/scan")
def scan_competitor(company_id: int, competitor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Run a fresh web scan for one competitor and store new signals."""
    company = get_user_company(db, company_id, current_user)
    comp = db.query(Competitor).filter(Competitor.id == competitor_id, Competitor.company_id == company.id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")

    try:
        found = _scan_competitor_web(comp)
    except Exception as e:
        logger.error(f"Competitor scan failed for {comp.name}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Web scan unavailable: {e}")

    # Dedupe against existing signals for this competitor.
    existing = db.query(CompetitorSignal).filter(CompetitorSignal.competitor_id == comp.id).all()
    seen = {_dedupe_key(s.source_type or "web", s.title or "", s.url or "") for s in existing}

    added = 0
    for item in found:
        key = _dedupe_key(item["source_type"], item.get("title") or "", item.get("url") or "")
        if key in seen:
            continue
        seen.add(key)
        db.add(CompetitorSignal(
            competitor_id=comp.id,
            company_id=company.id,
            source_type=item["source_type"],
            title=item.get("title"),
            url=item.get("url"),
            summary=item.get("summary"),
            sentiment=item.get("sentiment"),
            impact=item.get("impact"),
        ))
        added += 1

    comp.last_scanned_at = datetime.utcnow()
    db.commit()

    signals = db.query(CompetitorSignal).filter(
        CompetitorSignal.competitor_id == comp.id
    ).order_by(CompetitorSignal.created_at.desc()).limit(50).all()
    return {"added": added, "found": len(found), "signals": [_signal_dict(s) for s in signals]}
