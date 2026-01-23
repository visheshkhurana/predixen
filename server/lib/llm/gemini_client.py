"""
Gemini LLM client wrapper with PII redaction and audit logging.
Uses Replit AI Integrations for Gemini access.
"""
import os
import json
import hashlib
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx

from server.lib.privacy.pii_redactor import redact_text, RedactionResult
from server.models.llm_audit_log import LLMAuditLog

logger = logging.getLogger(__name__)


def compute_prompt_hash(text: str) -> str:
    """Compute SHA256 hash of the redacted prompt."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def truncate_preview(text: str, max_length: int = 1000) -> str:
    """Truncate text to max length for preview storage."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


class GeminiClient:
    """
    Gemini client using Replit AI Integrations.
    
    Supported models:
    - gemini-2.5-flash: Fast, good for general tasks
    - gemini-2.5-pro: Advanced reasoning and coding
    - gemini-3-flash-preview: Latest hybrid reasoning model
    - gemini-3-pro-preview: Most powerful for agentic workflows
    """
    
    def __init__(
        self,
        db_session=None,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
        pii_mode: str = "standard"
    ):
        self.api_key = os.environ.get("AI_INTEGRATIONS_GEMINI_API_KEY")
        self.base_url = os.environ.get("AI_INTEGRATIONS_GEMINI_BASE_URL")
        
        if not self.api_key or not self.base_url:
            raise ValueError(
                "Gemini AI Integrations not configured. "
                "AI_INTEGRATIONS_GEMINI_API_KEY and AI_INTEGRATIONS_GEMINI_BASE_URL required."
            )
        
        self.db = db_session
        self.company_id = company_id
        self.user_id = user_id
        self.pii_mode = pii_mode
        
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=120.0
        )
    
    def _create_audit_log(
        self,
        endpoint: str,
        model: str,
        original_input: str,
        redaction_result: RedactionResult,
        response_preview: str,
        latency_ms: int,
        tokens_in: int,
        tokens_out: int,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> Optional[int]:
        """Create an audit log entry."""
        if self.db is None:
            return None
            
        try:
            audit_log = LLMAuditLog(
                company_id=self.company_id,
                user_id=self.user_id,
                endpoint=endpoint,
                model=model,
                prompt_hash=compute_prompt_hash(original_input),
                redacted_prompt_preview=truncate_preview(redaction_result.redacted_text),
                pii_entities_detected=redaction_result.entities_detected,
                pii_entities_redacted=redaction_result.entities_redacted,
                response_preview=truncate_preview(response_preview),
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                status=status,
                error_message=error_message,
                created_at=datetime.utcnow()
            )
            self.db.add(audit_log)
            self.db.commit()
            return audit_log.id
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            return None
    
    def _convert_messages_to_gemini_format(
        self, 
        messages: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Convert OpenAI/Anthropic style messages to Gemini format.
        Returns (contents, system_instruction)
        """
        contents = []
        system_instruction = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_instruction = content
                continue
            
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })
        
        return contents, system_instruction
    
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make a chat completion request to Gemini.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Gemini model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            company_id: Optional company ID for audit logging
            user_id: Optional user ID for audit logging
            **kwargs: Additional arguments
        
        Returns:
            Dict with 'content', 'usage', 'model', 'provider', 'audit_log_id', 'pii_findings'
        """
        start_time = datetime.utcnow()
        
        combined_input = "\n".join([m.get("content", "") for m in messages])
        redaction_result = redact_text(combined_input, mode=self.pii_mode)
        
        redacted_messages = []
        for msg in messages:
            content = msg.get("content", "")
            msg_redaction = redact_text(content, mode=self.pii_mode)
            redacted_messages.append({**msg, "content": msg_redaction.redacted_text})
        
        contents, system_instruction = self._convert_messages_to_gemini_format(redacted_messages)
        
        request_body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        if system_instruction:
            request_body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        endpoint = f"/models/{model}:generateContent"
        
        try:
            response = self.client.post(endpoint, json=request_body)
            response.raise_for_status()
            data = response.json()
            
            content = ""
            if data.get("candidates"):
                candidate = data["candidates"][0]
                if candidate.get("content", {}).get("parts"):
                    content = candidate["content"]["parts"][0].get("text", "")
            
            usage_metadata = data.get("usageMetadata", {})
            tokens_in = usage_metadata.get("promptTokenCount", 0)
            tokens_out = usage_metadata.get("candidatesTokenCount", 0)
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            audit_log_id = self._create_audit_log(
                endpoint=endpoint,
                model=model,
                original_input=combined_input,
                redaction_result=redaction_result,
                response_preview=content,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out
            )
            
            return {
                "content": content,
                "usage": {
                    "prompt_tokens": tokens_in,
                    "completion_tokens": tokens_out,
                    "total_tokens": tokens_in + tokens_out
                },
                "model": model,
                "provider": "gemini",
                "audit_log_id": audit_log_id,
                "pii_findings": redaction_result.entities_detected
            }
            
        except httpx.HTTPStatusError as e:
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self._create_audit_log(
                endpoint=endpoint,
                model=model,
                original_input=combined_input,
                redaction_result=redaction_result,
                response_preview="",
                latency_ms=latency_ms,
                tokens_in=0,
                tokens_out=0,
                status="error",
                error_message=str(e)
            )
            logger.error(f"Gemini API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Gemini request failed: {e}")
            raise
    
    def stream_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        **kwargs
    ):
        """
        Stream a chat completion from Gemini.
        
        Yields chunks of text as they arrive.
        """
        redacted_messages = []
        for msg in messages:
            content = msg.get("content", "")
            msg_redaction = redact_text(content, mode=self.pii_mode)
            redacted_messages.append({**msg, "content": msg_redaction.redacted_text})
        
        contents, system_instruction = self._convert_messages_to_gemini_format(redacted_messages)
        
        request_body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        if system_instruction:
            request_body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        endpoint = f"/models/{model}:streamGenerateContent?alt=sse"
        
        with self.client.stream("POST", endpoint, json=request_body) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data.get("candidates"):
                            candidate = data["candidates"][0]
                            if candidate.get("content", {}).get("parts"):
                                text = candidate["content"]["parts"][0].get("text", "")
                                if text:
                                    yield text
                    except json.JSONDecodeError:
                        continue
