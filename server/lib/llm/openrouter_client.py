"""
OpenRouter client for accessing Grok (xAI) and other models via Replit AI Integrations.

Uses AI_INTEGRATIONS_OPENROUTER_BASE_URL and AI_INTEGRATIONS_OPENROUTER_API_KEY
environment variables set automatically by the Replit OpenRouter integration.

OpenRouter provides an OpenAI-compatible API, so we use httpx directly.
"""
import os
import hashlib
import time
import logging
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime

import httpx

from server.lib.privacy.pii_redactor import redact_text, RedactionResult
from server.models.llm_audit_log import LLMAuditLog

logger = logging.getLogger(__name__)


OPENROUTER_MODELS = {
    "grok-4.1-fast": "x-ai/grok-4.1-fast",
    "grok-4-fast": "x-ai/grok-4-fast",
    "grok-3-mini": "x-ai/grok-3-mini",
    "grok-3": "x-ai/grok-3",
}

DEFAULT_MODEL = "grok-4.1-fast"


def compute_prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def truncate_preview(text: str, max_length: int = 1000) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


class OpenRouterClient:
    """
    OpenRouter client for Grok (xAI) models with PII redaction and audit logging.

    Grok excels at:
    - News and current events (built by xAI with real-time data access)
    - Trend analysis and social sentiment
    - Fast, cost-effective general reasoning (grok-4.1-fast)
    """

    def __init__(
        self,
        db_session=None,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
        pii_mode: Literal["off", "standard", "strict"] = "standard"
    ):
        self.db = db_session
        self.company_id = company_id
        self.user_id = user_id
        self.pii_mode = pii_mode

        self.base_url = os.environ.get("AI_INTEGRATIONS_OPENROUTER_BASE_URL")
        self.api_key = os.environ.get("AI_INTEGRATIONS_OPENROUTER_API_KEY")

        if not self.base_url or not self.api_key:
            raise ValueError(
                "OpenRouter not configured. "
                "AI_INTEGRATIONS_OPENROUTER_BASE_URL and AI_INTEGRATIONS_OPENROUTER_API_KEY required."
            )

        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    def _resolve_model(self, model: str) -> str:
        if model in OPENROUTER_MODELS:
            return OPENROUTER_MODELS[model]
        if model.startswith("x-ai/"):
            return model
        return OPENROUTER_MODELS.get(DEFAULT_MODEL, "x-ai/grok-4.1-fast")

    def _create_audit_log(
        self,
        endpoint: str,
        model: str,
        original_input: str,
        redaction_result: RedactionResult,
        output: str,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        latency_ms: Optional[int] = None,
    ) -> Optional[LLMAuditLog]:
        if not self.db:
            return None
        try:
            log = LLMAuditLog(
                company_id=self.company_id,
                user_id=self.user_id,
                provider="openrouter",
                model=model,
                endpoint=endpoint,
                prompt_hash=compute_prompt_hash(original_input),
                prompt_preview=truncate_preview(original_input),
                response_preview=truncate_preview(output),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                pii_detected=len(redaction_result.findings) > 0 if redaction_result else False,
                pii_types=[f.get("type", "") if isinstance(f, dict) else getattr(f, "entity_type", "") for f in (redaction_result.findings if redaction_result and redaction_result.findings else [])],
                created_at=datetime.utcnow(),
            )
            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)
            return log
        except Exception as e:
            logger.warning(f"Failed to create audit log: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass
            return None

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Chat completion via OpenRouter (Grok models).

        Returns dict with 'content', 'usage', 'model', 'provider', 'audit_log_id', 'pii_findings'.
        """
        start_time = time.time()
        resolved_model = self._resolve_model(model)

        redaction_result = None
        if self.pii_mode != "off":
            redacted_messages = []
            all_findings = []
            for msg in messages:
                if msg.get("content"):
                    result = redact_text(msg["content"])
                    all_findings.extend(result.findings)
                    redacted_messages.append({**msg, "content": result.redacted_text})
                else:
                    redacted_messages.append(msg)
            redaction_result = RedactionResult(
                redacted_text=redacted_messages[-1].get("content", "") if redacted_messages else "",
                findings=all_findings,
            )
            messages = redacted_messages

        body = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = self.client.post("/chat/completions", json=body)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text[:300]}")
            raise ValueError(f"OpenRouter API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"OpenRouter request failed: {e}")
            raise

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        latency_ms = int((time.time() - start_time) * 1000)

        audit_log = self._create_audit_log(
            endpoint="chat/completions",
            model=resolved_model,
            original_input=messages[-1].get("content", "") if messages else "",
            redaction_result=redaction_result or RedactionResult(redacted_text="", findings=[]),
            output=content,
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            latency_ms=latency_ms,
        )

        return {
            "content": content,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            "model": resolved_model,
            "provider": "openrouter",
            "audit_log_id": audit_log.id if audit_log else None,
            "pii_findings": [
                f if isinstance(f, dict) else {"type": getattr(f, "entity_type", str(f)), "count": 1}
                for f in (redaction_result.findings if redaction_result else [])
            ],
            "latency_ms": latency_ms,
        }

    def close(self):
        self.client.close()


_client_instance: Optional[OpenRouterClient] = None


def get_openrouter_client(
    db_session=None,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
    pii_mode: Literal["off", "standard", "strict"] = "standard",
) -> OpenRouterClient:
    return OpenRouterClient(
        db_session=db_session,
        company_id=company_id,
        user_id=user_id,
        pii_mode=pii_mode,
    )
