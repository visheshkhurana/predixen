"""
Perplexity AI client for web search with citations.
Used for real-time data, news, market research, and factual queries.
"""
import os
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


PERPLEXITY_MODELS = {
    "sonar-small": "sonar",
    "sonar": "sonar",
    "sonar-pro": "sonar-pro",
    "sonar-large": "sonar-pro",
    "sonar-huge": "sonar-pro",
    "sonar-reasoning": "sonar-reasoning-pro",
    "sonar-reasoning-pro": "sonar-reasoning-pro",
    "sonar-deep-research": "sonar-deep-research",
}

DEFAULT_MODEL = "sonar"


class PerplexityClient:
    """
    Perplexity AI client for web search with citations.
    
    Specializes in:
    - Real-time data and news
    - Market research and competitor analysis
    - Factual queries requiring web search
    - Current pricing and product information
    
    Models:
    - sonar-small: Fast, cost-effective for most queries
    - sonar-large: More detailed responses
    - sonar-huge: Most capable for complex research
    """
    
    def __init__(
        self,
        db_session=None,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
        pii_mode: str = "standard"
    ):
        self.api_key = os.environ.get("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai"
        
        if not self.api_key:
            raise ValueError(
                "Perplexity API key not configured. "
                "Set PERPLEXITY_API_KEY environment variable."
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
            timeout=60.0
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
        error_message: Optional[str] = None,
        citations: Optional[List[str]] = None
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
                input_chars_original=len(original_input),
                input_chars_redacted=len(redaction_result.redacted_text),
                pii_findings_json={
                    "count": len(redaction_result.findings),
                    "status": status,
                    "error": error_message,
                    "citations_count": len(citations) if citations else 0
                },
                redacted_prompt_preview=truncate_preview(redaction_result.redacted_text),
                redacted_output_preview=truncate_preview(response_preview),
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                created_at=datetime.utcnow()
            )
            self.db.add(audit_log)
            self.db.commit()
            return audit_log.id
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            return None
    
    def search(
        self,
        query: str,
        model: str = "sonar-small",
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        search_domain_filter: Optional[List[str]] = None,
        search_recency_filter: Optional[str] = None,
        return_citations: bool = True,
        return_related_questions: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform a web search query with Perplexity.
        
        Args:
            query: The search query
            model: Model to use (sonar-small, sonar-large, sonar-huge)
            system_prompt: Optional system instruction
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            search_domain_filter: List of domains to restrict search to
            search_recency_filter: Recency filter (day, week, month, year)
            return_citations: Whether to return source citations
            return_related_questions: Whether to return related questions
            **kwargs: Additional arguments
        
        Returns:
            Dict with 'content', 'citations', 'usage', 'model', 'provider'
        """
        start_time = datetime.utcnow()
        
        redaction_result = redact_text(query, mode=self.pii_mode)
        redacted_query = redaction_result.redacted_text
        
        model_id = PERPLEXITY_MODELS.get(model, PERPLEXITY_MODELS[DEFAULT_MODEL])
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": redacted_query})
        
        request_body = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1
        }
        
        if search_domain_filter:
            request_body["search_domain_filter"] = search_domain_filter
        
        if search_recency_filter:
            request_body["search_recency_filter"] = search_recency_filter
        
        request_body["return_images"] = False
        request_body["return_related_questions"] = return_related_questions
        
        endpoint = "/chat/completions"
        
        try:
            response = self.client.post(endpoint, json=request_body)
            response.raise_for_status()
            data = response.json()
            
            content = ""
            if data.get("choices"):
                choice = data["choices"][0]
                content = choice.get("message", {}).get("content", "")
            
            citations = data.get("citations", [])
            
            usage = data.get("usage", {})
            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            audit_log_id = self._create_audit_log(
                endpoint=endpoint,
                model=model_id,
                original_input=query,
                redaction_result=redaction_result,
                response_preview=content,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                citations=citations
            )
            
            return {
                "content": content,
                "citations": citations if return_citations else [],
                "usage": {
                    "prompt_tokens": tokens_in,
                    "completion_tokens": tokens_out,
                    "total_tokens": tokens_in + tokens_out
                },
                "model": model_id,
                "provider": "perplexity",
                "audit_log_id": audit_log_id,
                "pii_findings": len(redaction_result.findings)
            }
            
        except httpx.HTTPStatusError as e:
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self._create_audit_log(
                endpoint=endpoint,
                model=model_id,
                original_input=query,
                redaction_result=redaction_result,
                response_preview="",
                latency_ms=latency_ms,
                tokens_in=0,
                tokens_out=0,
                status="error",
                error_message=str(e)
            )
            logger.error(f"Perplexity API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Perplexity request failed: {e}")
            raise
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "sonar-small",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        search_recency_filter: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Multi-turn chat with web search context.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            search_recency_filter: Recency filter
            **kwargs: Additional arguments
        
        Returns:
            Dict with 'content', 'citations', 'usage', 'model', 'provider'
        """
        start_time = datetime.utcnow()
        
        combined_input = "\n".join([m.get("content", "") for m in messages])
        redaction_result = redact_text(combined_input, mode=self.pii_mode)
        
        redacted_messages = []
        for msg in messages:
            content = msg.get("content", "")
            msg_redaction = redact_text(content, mode=self.pii_mode)
            redacted_messages.append({**msg, "content": msg_redaction.redacted_text})
        
        model_id = PERPLEXITY_MODELS.get(model, PERPLEXITY_MODELS[DEFAULT_MODEL])
        
        request_body = {
            "model": model_id,
            "messages": redacted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1
        }
        
        if search_recency_filter:
            request_body["search_recency_filter"] = search_recency_filter
        
        endpoint = "/chat/completions"
        
        try:
            response = self.client.post(endpoint, json=request_body)
            response.raise_for_status()
            data = response.json()
            
            content = ""
            if data.get("choices"):
                choice = data["choices"][0]
                content = choice.get("message", {}).get("content", "")
            
            citations = data.get("citations", [])
            
            usage = data.get("usage", {})
            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            audit_log_id = self._create_audit_log(
                endpoint=endpoint,
                model=model_id,
                original_input=combined_input,
                redaction_result=redaction_result,
                response_preview=content,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                citations=citations
            )
            
            return {
                "content": content,
                "citations": citations,
                "usage": {
                    "prompt_tokens": tokens_in,
                    "completion_tokens": tokens_out,
                    "total_tokens": tokens_in + tokens_out
                },
                "model": model_id,
                "provider": "perplexity",
                "audit_log_id": audit_log_id,
                "pii_findings": len(redaction_result.findings)
            }
            
        except httpx.HTTPStatusError as e:
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self._create_audit_log(
                endpoint=endpoint,
                model=model_id,
                original_input=combined_input,
                redaction_result=redaction_result,
                response_preview="",
                latency_ms=latency_ms,
                tokens_in=0,
                tokens_out=0,
                status="error",
                error_message=str(e)
            )
            logger.error(f"Perplexity API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Perplexity request failed: {e}")
            raise


def get_perplexity_client(
    db_session=None,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
    pii_mode: str = "standard"
) -> Optional[PerplexityClient]:
    """Factory function to create a Perplexity client."""
    try:
        return PerplexityClient(
            db_session=db_session,
            company_id=company_id,
            user_id=user_id,
            pii_mode=pii_mode
        )
    except ValueError:
        return None


def is_perplexity_available() -> bool:
    """Check if Perplexity API is configured."""
    return bool(os.environ.get("PERPLEXITY_API_KEY"))
