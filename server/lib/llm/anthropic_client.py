"""
Centralized Anthropic Client with PII redaction and audit logging.
Uses Replit AI Integrations for Anthropic access (no API key required).
"""
import hashlib
import time
import os
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
import httpx

from server.lib.privacy.pii_redactor import redact_text, RedactionResult
from server.models.llm_audit_log import LLMAuditLog


ANTHROPIC_MODELS = {
    "claude-opus-4-5": "claude-opus-4-5",
    "claude-sonnet-4-5": "claude-sonnet-4-5",
    "claude-haiku-4-5": "claude-haiku-4-5",
    "claude-opus-4-1": "claude-opus-4-1",
}

DEFAULT_MODEL = "claude-sonnet-4-5"


def compute_prompt_hash(text: str) -> str:
    """Compute SHA256 hash of the redacted prompt."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def truncate_preview(text: str, max_length: int = 1000) -> str:
    """Truncate text to max length for preview storage."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


class AuditedAnthropicClient:
    """Anthropic client wrapper with PII redaction and audit logging."""
    
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
        self.api_key = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY", "")
        self.base_url = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    
    def _create_audit_log(
        self,
        endpoint: str,
        model: str,
        original_input: str,
        redaction_result: RedactionResult,
        output: str,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        latency_ms: Optional[int] = None
    ) -> Optional[LLMAuditLog]:
        """Create an audit log entry."""
        if not self.db:
            return None
        
        try:
            redacted_output = redact_text(output, self.pii_mode)
            
            audit_log = LLMAuditLog(
                company_id=self.company_id,
                user_id=self.user_id,
                endpoint=endpoint,
                model=model,
                pii_mode=self.pii_mode,
                prompt_hash=compute_prompt_hash(redaction_result.redacted_text),
                input_chars_original=len(original_input),
                input_chars_redacted=len(redaction_result.redacted_text),
                pii_findings_json=redaction_result.findings,
                redacted_prompt_preview=truncate_preview(redaction_result.redacted_text),
                redacted_output_preview=truncate_preview(redacted_output.redacted_text),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms
            )
            self.db.add(audit_log)
            self.db.commit()
            return audit_log
        except Exception as e:
            print(f"Error creating audit log: {e}")
            return None
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        system: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make a chat completion request with PII redaction and audit logging.
        
        Returns:
            Dict with 'content', 'usage', 'model', and 'audit_log_id'
        """
        original_messages = messages.copy()
        original_input = "\n".join([m.get("content", "") for m in messages])
        if system:
            original_input = f"[SYSTEM] {system}\n{original_input}"
        
        redacted_messages = []
        all_findings = []
        
        for msg in messages:
            content = msg.get("content", "")
            redaction = redact_text(content, self.pii_mode)
            redacted_messages.append({
                "role": msg.get("role", "user"),
                "content": redaction.redacted_text
            })
            all_findings.extend(redaction.findings)
        
        redacted_system = None
        if system:
            system_redaction = redact_text(system, self.pii_mode)
            redacted_system = system_redaction.redacted_text
            all_findings.extend(system_redaction.findings)
        
        redacted_input = "\n".join([m.get("content", "") for m in redacted_messages])
        if redacted_system:
            redacted_input = f"[SYSTEM] {redacted_system}\n{redacted_input}"
        
        combined_redaction = RedactionResult(
            redacted_text=redacted_input,
            findings=all_findings
        )
        
        start_time = time.time()
        
        try:
            request_body = {
                "model": ANTHROPIC_MODELS.get(model, model),
                "messages": redacted_messages,
                "max_tokens": max_tokens,
            }
            
            if redacted_system:
                request_body["system"] = redacted_system
            
            if temperature != 1.0:
                request_body["temperature"] = temperature
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/v1/messages",
                    json=request_body,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            output_content = ""
            if data.get("content") and len(data["content"]) > 0:
                for block in data["content"]:
                    if block.get("type") == "text":
                        output_content += block.get("text", "")
            
            usage = data.get("usage", {})
            tokens_in = usage.get("input_tokens", 0)
            tokens_out = usage.get("output_tokens", 0)
            
            audit_log = self._create_audit_log(
                endpoint="messages",
                model=model,
                original_input=original_input,
                redaction_result=combined_redaction,
                output=output_content,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms
            )
            
            return {
                "content": output_content,
                "usage": {
                    "prompt_tokens": tokens_in,
                    "completion_tokens": tokens_out,
                    "total_tokens": tokens_in + tokens_out
                },
                "model": data.get("model", model),
                "audit_log_id": str(audit_log.id) if audit_log else None,
                "pii_findings": combined_redaction.findings,
                "provider": "anthropic"
            }
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            
            self._create_audit_log(
                endpoint="messages",
                model=model,
                original_input=original_input,
                redaction_result=combined_redaction,
                output=f"ERROR: {str(e)}",
                latency_ms=latency_ms
            )
            raise


def get_audited_anthropic_client(
    db_session=None,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
    pii_mode: Literal["off", "standard", "strict"] = "standard"
) -> AuditedAnthropicClient:
    """Factory function to create an audited Anthropic client."""
    return AuditedAnthropicClient(
        db_session=db_session,
        company_id=company_id,
        user_id=user_id,
        pii_mode=pii_mode
    )
