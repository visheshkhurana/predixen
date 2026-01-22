"""
Centralized OpenAI Client with PII redaction and audit logging.
All OpenAI API calls should go through this module.
"""
import hashlib
import time
import os
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from openai import OpenAI

from server.lib.privacy.pii_redactor import redact_text, redact_object, RedactionResult
from server.models.llm_audit_log import LLMAuditLog


client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


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
        self.client = client
    
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
        model: str = "gpt-4o",
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
        model: str = "gpt-4o",
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
