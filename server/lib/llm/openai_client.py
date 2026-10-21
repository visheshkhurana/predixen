"""
Centralized OpenAI Client with PII redaction and audit logging.
All OpenAI API calls should go through this module.
"""
import hashlib
import time
import os
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime

from server.lib.privacy.pii_redactor import redact_text, redact_object, RedactionResult
from server.models.llm_audit_log import LLMAuditLog


def get_openai_client():
    """Get OpenAI client with Replit AI Integrations configuration."""
    from openai import OpenAI
    api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    
    if not api_key:
        return None
    
    return OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)


_client = None

def _get_client():
    global _client
    if _client is None:
        _client = get_openai_client()
    return _client


def compute_prompt_hash(text: str) -> str:
    """Compute SHA256 hash of the redacted prompt."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def truncate_preview(text: str, max_length: int = 1000) -> str:
    """Truncate text to max length for preview storage."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


class AuditedOpenAIClient:
    """OpenAI client wrapper with PII redaction and audit logging."""
    
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
        self.client = _get_client()
        if self.client is None:
            raise ValueError("OpenAI API key not configured. Set AI_INTEGRATIONS_OPENAI_API_KEY or OPENAI_API_KEY environment variable.")
    
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
        model: str = "gpt-5",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make a chat completion request with PII redaction and audit logging.
        
        Returns:
            Dict with 'content', 'usage', 'model', and 'audit_log_id'
        """
        original_messages = messages.copy()
        original_input = "\n".join([m.get("content", "") for m in messages])
        
        redacted_messages = []
        all_findings = []
        
        for msg in messages:
            content = msg.get("content", "")
            redaction = redact_text(content, self.pii_mode)
            redacted_messages.append({
                **msg,
                "content": redaction.redacted_text
            })
            all_findings.extend(redaction.findings)
        
        redacted_input = "\n".join([m.get("content", "") for m in redacted_messages])
        combined_redaction = RedactionResult(
            redacted_text=redacted_input,
            findings=all_findings
        )
        
        start_time = time.time()
        
        try:
            request_kwargs = {
                "model": model,
                "messages": redacted_messages,
                "temperature": temperature,
                **kwargs
            }
            
            if max_tokens:
                request_kwargs["max_tokens"] = max_tokens
            
            if response_format:
                request_kwargs["response_format"] = response_format
            
            response = self.client.chat.completions.create(**request_kwargs)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            output_content = response.choices[0].message.content or ""
            usage = response.usage
            
            audit_log = self._create_audit_log(
                endpoint="chat.completions",
                model=model,
                original_input=original_input,
                redaction_result=combined_redaction,
                output=output_content,
                tokens_in=usage.prompt_tokens if usage else None,
                tokens_out=usage.completion_tokens if usage else None,
                latency_ms=latency_ms
            )
            
            return {
                "content": output_content,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0
                },
                "model": response.model,
                "audit_log_id": str(audit_log.id) if audit_log else None,
                "pii_findings": combined_redaction.findings
            }
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            
            self._create_audit_log(
                endpoint="chat.completions",
                model=model,
                original_input=original_input,
                redaction_result=combined_redaction,
                output=f"ERROR: {str(e)}",
                latency_ms=latency_ms
            )
            raise
    
    def vision_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = "gpt-5",
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make a vision completion request with PII redaction and audit logging.
        Text content is redacted; images are passed through.
        """
        original_text_parts = []
        redacted_messages = []
        all_findings = []
        
        for msg in messages:
            content = msg.get("content")
            
            if isinstance(content, str):
                redaction = redact_text(content, self.pii_mode)
                redacted_messages.append({
                    **msg,
                    "content": redaction.redacted_text
                })
                original_text_parts.append(content)
                all_findings.extend(redaction.findings)
            elif isinstance(content, list):
                redacted_content = []
                for item in content:
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        redaction = redact_text(text, self.pii_mode)
                        redacted_content.append({
                            "type": "text",
                            "text": redaction.redacted_text
                        })
                        original_text_parts.append(text)
                        all_findings.extend(redaction.findings)
                    else:
                        redacted_content.append(item)
                
                redacted_messages.append({
                    **msg,
                    "content": redacted_content
                })
            else:
                redacted_messages.append(msg)
        
        original_input = "\n".join(original_text_parts)
        redacted_input = "\n".join([
            m.get("content") if isinstance(m.get("content"), str) else "[MULTIMODAL_CONTENT]"
            for m in redacted_messages
        ])
        
        combined_redaction = RedactionResult(
            redacted_text=redacted_input,
            findings=all_findings
        )
        
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=redacted_messages,
                max_tokens=max_tokens,
                **kwargs
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            output_content = response.choices[0].message.content or ""
            usage = response.usage
            
            audit_log = self._create_audit_log(
                endpoint="chat.completions.vision",
                model=model,
                original_input=original_input,
                redaction_result=combined_redaction,
                output=output_content,
                tokens_in=usage.prompt_tokens if usage else None,
                tokens_out=usage.completion_tokens if usage else None,
                latency_ms=latency_ms
            )
            
            return {
                "content": output_content,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0
                },
                "model": response.model,
                "audit_log_id": str(audit_log.id) if audit_log else None,
                "pii_findings": combined_redaction.findings
            }
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            
            self._create_audit_log(
                endpoint="chat.completions.vision",
                model=model,
                original_input=original_input,
                redaction_result=combined_redaction,
                output=f"ERROR: {str(e)}",
                latency_ms=latency_ms
            )
            raise

    @property
    def chat(self):
        """SDK-compatible entry the simulation engine already calls.

        ``llm_client.chat.completions.create(...)`` redacts message text and
        writes an llm_audit_logs row, then returns the raw provider response
        so callers keep reading ``response.choices[0].message.content``.
        Image content parts are not redacted; text parts inside them are.
        """
        return _AuditedChatNamespace(self)


class _AuditedChatNamespace:
    def __init__(self, audited: AuditedOpenAIClient):
        self.completions = _AuditedCompletions(audited)


class _AuditedCompletions:
    def __init__(self, audited: AuditedOpenAIClient):
        self._audited = audited

    def create(self, **kwargs):
        messages = list(kwargs.get("messages") or [])
        model = kwargs.get("model", "gpt-5")
        original_parts = []
        redacted_messages = []
        all_findings = []
        multimodal = False

        for msg in messages:
            if not isinstance(msg, dict):
                redacted_messages.append(msg)
                original_parts.append("")
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                multimodal = True
                redacted_content = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text") if isinstance(item.get("text"), str) else ""
                        redaction = redact_text(text, self._audited.pii_mode)
                        updated_item = dict(item)
                        updated_item["text"] = redaction.redacted_text
                        redacted_content.append(updated_item)
                        original_parts.append(text)
                        all_findings.extend(redaction.findings)
                    else:
                        # Image and other non-text parts go to the provider unchanged.
                        redacted_content.append(item)
                updated = dict(msg)
                updated["content"] = redacted_content
                redacted_messages.append(updated)
            elif isinstance(content, str):
                redaction = redact_text(content, self._audited.pii_mode)
                updated = dict(msg)
                updated["content"] = redaction.redacted_text
                redacted_messages.append(updated)
                original_parts.append(content)
                all_findings.extend(redaction.findings)
            else:
                redacted_messages.append(dict(msg))
                original_parts.append("")

        original_input = "\n".join(original_parts)
        redacted_parts = []
        for message in redacted_messages:
            if not isinstance(message, dict):
                redacted_parts.append("")
                continue
            content = message.get("content", "")
            if isinstance(content, str):
                redacted_parts.append(content)
            elif isinstance(content, list):
                for item in content:
                    if (
                        isinstance(item, dict)
                        and item.get("type") == "text"
                        and isinstance(item.get("text"), str)
                    ):
                        redacted_parts.append(item["text"])
            else:
                redacted_parts.append("")
        redacted_input = "\n".join(redacted_parts)
        combined = RedactionResult(redacted_text=redacted_input, findings=all_findings)
        call_kwargs = dict(kwargs)
        call_kwargs["messages"] = redacted_messages
        endpoint = "chat.completions.vision" if multimodal else "chat.completions"

        start_time = time.time()
        try:
            response = self._audited.client.chat.completions.create(**call_kwargs)
            latency_ms = int((time.time() - start_time) * 1000)
            output_content = ""
            try:
                output_content = response.choices[0].message.content or ""
            except Exception:
                output_content = ""
            usage = getattr(response, "usage", None)
            self._audited._create_audit_log(
                endpoint=endpoint,
                model=model,
                original_input=original_input,
                redaction_result=combined,
                output=output_content,
                tokens_in=getattr(usage, "prompt_tokens", None) if usage else None,
                tokens_out=getattr(usage, "completion_tokens", None) if usage else None,
                latency_ms=latency_ms,
            )
            return response
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            self._audited._create_audit_log(
                endpoint=endpoint,
                model=model,
                original_input=original_input,
                redaction_result=combined,
                output=f"ERROR: {str(e)}",
                latency_ms=latency_ms,
            )
            raise


def get_audited_client(
    db_session=None,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
    pii_mode: Literal["off", "standard", "strict"] = "standard"
) -> AuditedOpenAIClient:
    """Factory function to create an audited OpenAI client."""
    return AuditedOpenAIClient(
        db_session=db_session,
        company_id=company_id,
        user_id=user_id,
        pii_mode=pii_mode
    )


def _close_db(db) -> None:
    if db is None:
        return
    try:
        db.close()
    except Exception:
        pass


@contextmanager
def open_audited_openai(
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
    pii_mode: Literal["off", "standard", "strict"] = "standard",
    provider_client=None,
):
    """Open ``get_audited_client`` and close its DB session on every exit.

    The session closes in ``finally``, including when the provider call or
    the missing-key check raises. Callers that already know which SDK client
    to use (competitors keeps its own missing-key error and base URL) pass
    ``provider_client``. Otherwise the client is built from
    ``resolve_openai_credentials``, so a plain key does not inherit the
    integration proxy URL.

    ``get_audited_client`` caches a process-wide SDK client. The cache is
    restored before this helper returns so the call does not pin it.
    """
    from openai import OpenAI
    from server.core.db import SessionLocal
    from server.core.openai_credentials import missing_key_error, resolve_openai_credentials

    global _client
    previous_client = _client
    db = None
    try:
        db = SessionLocal()
        _client = None
        try:
            try:
                audited = get_audited_client(
                    db_session=db,
                    company_id=company_id,
                    user_id=user_id,
                    pii_mode=pii_mode,
                )
            except ValueError as exc:
                if "OpenAI API key not configured" in str(exc):
                    raise missing_key_error() from None
                raise
        finally:
            _client = previous_client

        if provider_client is not None:
            audited.client = provider_client
        else:
            api_key, base_url = resolve_openai_credentials()
            if not api_key:
                raise missing_key_error()
            audited.client = (
                OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
            )
        yield audited
    finally:
        _close_db(db)
