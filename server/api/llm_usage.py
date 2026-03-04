from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Optional
from datetime import datetime, timedelta
import logging

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.models.llm_audit_log import LLMAuditLog

logger = logging.getLogger(__name__)
router = APIRouter(tags=["llm-usage"])


@router.get("/companies/{company_id}/llm-usage")
def get_llm_usage(
    company_id: int,
    period: str = Query("30d", pattern="^(7d|30d|90d|all)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)

    query = db.query(LLMAuditLog).filter(LLMAuditLog.company_id == company_id)

    if period != "all":
        days = {"7d": 7, "30d": 30, "90d": 90}[period]
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.filter(LLMAuditLog.created_at >= cutoff)

    logs = query.all()

    total_calls = len(logs)
    total_tokens_in = sum(log.tokens_in or 0 for log in logs)
    total_tokens_out = sum(log.tokens_out or 0 for log in logs)
    total_latency = sum(log.latency_ms or 0 for log in logs)
    avg_latency = total_latency / total_calls if total_calls > 0 else 0

    by_model = {}
    by_provider = {}
    for log in logs:
        model = log.model or "unknown"
        if model not in by_model:
            by_model[model] = {"calls": 0, "tokens_in": 0, "tokens_out": 0, "total_latency_ms": 0}
        by_model[model]["calls"] += 1
        by_model[model]["tokens_in"] += log.tokens_in or 0
        by_model[model]["tokens_out"] += log.tokens_out or 0
        by_model[model]["total_latency_ms"] += log.latency_ms or 0

        provider = _model_to_provider(model)
        if provider not in by_provider:
            by_provider[provider] = {"calls": 0, "tokens_in": 0, "tokens_out": 0}
        by_provider[provider]["calls"] += 1
        by_provider[provider]["tokens_in"] += log.tokens_in or 0
        by_provider[provider]["tokens_out"] += log.tokens_out or 0

    for m in by_model.values():
        m["avg_latency_ms"] = m["total_latency_ms"] / m["calls"] if m["calls"] > 0 else 0
        del m["total_latency_ms"]

    return {
        "period": period,
        "total_calls": total_calls,
        "total_tokens": total_tokens_in + total_tokens_out,
        "total_tokens_in": total_tokens_in,
        "total_tokens_out": total_tokens_out,
        "avg_latency_ms": round(avg_latency),
        "by_model": by_model,
        "by_provider": by_provider,
    }


def _model_to_provider(model: str) -> str:
    if "gpt" in model:
        return "openai"
    elif "claude" in model:
        return "anthropic"
    elif "gemini" in model:
        return "gemini"
    elif "sonar" in model or "perplexity" in model:
        return "perplexity"
    return "unknown"
