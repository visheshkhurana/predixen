"""
AI Image Generator — uses OpenAI's gpt-image-1 for image generation.

Generates professional graphics for board decks, reports, and presentations.

Supports styles: professional, infographic, chart, illustration, minimal.
"""
import os
import hashlib
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

STYLE_PREFIXES = {
    "professional": (
        "Create a clean, professional business graphic. Use a modern corporate color palette "
        "(deep blues, whites, subtle grays). Minimal text, high contrast, suitable for board "
        "presentations and investor decks. "
    ),
    "infographic": (
        "Create a modern infographic-style visual. Use clear data hierarchy, icons, and a "
        "structured layout. Use vibrant but professional colors. Include visual metaphors "
        "for data concepts. "
    ),
    "chart": (
        "Create a clean, modern data visualization or chart illustration. Use precise lines, "
        "clear labels, and a professional color scheme. Suitable for financial reports. "
    ),
    "illustration": (
        "Create a modern, flat-design illustration suitable for a tech startup. Use a clean "
        "aesthetic with soft gradients, geometric shapes, and a contemporary color palette. "
    ),
    "minimal": (
        "Create a minimalist graphic with lots of whitespace, simple geometric shapes, and "
        "a very limited color palette (2-3 colors max). Clean and elegant. "
    ),
}

ASPECT_RATIOS = {
    "1:1": "1024x1024",
    "16:9": "1536x1024",
    "4:3": "1536x1024",
    "9:16": "1024x1536",
}


class NanoBananaImageGenerator:
    """
    AI image generator using OpenAI's gpt-image-1 model.
    """

    def __init__(
        self,
        db_session=None,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ):
        self.api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
        self.base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")

        if not self.api_key or not self.base_url:
            raise ValueError(
                "OpenAI AI Integrations not configured. "
                "AI_INTEGRATIONS_OPENAI_API_KEY and AI_INTEGRATIONS_OPENAI_BASE_URL required."
            )

        self.db = db_session
        self.company_id = company_id
        self.user_id = user_id

        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    def _create_audit_log(
        self,
        endpoint: str,
        model: str,
        prompt: str,
        latency_ms: int,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        if self.db is None:
            return None
        try:
            from server.models.llm_audit_log import LLMAuditLog

            def _compute_hash(text: str) -> str:
                return hashlib.sha256(text.encode()).hexdigest()[:16]

            def _truncate(text: str, max_len: int = 1000) -> str:
                return text[:max_len] if len(text) > max_len else text

            redacted_prompt = prompt
            pii_count = 0
            try:
                from server.lib.privacy.pii_redactor import redact_text
                redaction_result = redact_text(prompt, mode="standard")
                redacted_prompt = redaction_result.redacted_text
                pii_count = len(redaction_result.findings)
            except Exception:
                pass

            audit_log = LLMAuditLog(
                company_id=self.company_id,
                user_id=self.user_id,
                endpoint=endpoint,
                model=model,
                prompt_hash=_compute_hash(prompt),
                input_chars_original=len(prompt),
                input_chars_redacted=len(redacted_prompt),
                pii_findings_json={"count": pii_count, "status": status, "error": error_message},
                redacted_prompt_preview=_truncate(redacted_prompt),
                redacted_output_preview="[image_generated]" if status == "success" else "",
                latency_ms=latency_ms,
                tokens_in=0,
                tokens_out=0,
                created_at=datetime.utcnow(),
            )
            self.db.add(audit_log)
            self.db.commit()
            return audit_log.id
        except Exception as e:
            logger.error(f"Failed to create image gen audit log: {e}")
            return None

    def generate_image(
        self,
        prompt: str,
        style: str = "professional",
        aspect_ratio: str = "16:9",
        model: str = "gpt-image-1",
    ) -> Dict[str, Any]:
        """
        Generate an image using OpenAI's gpt-image-1.

        Args:
            prompt: Description of the image to generate
            style: One of 'professional', 'infographic', 'chart', 'illustration', 'minimal'
            aspect_ratio: One of '1:1', '16:9', '4:3', '9:16'
            model: OpenAI model to use

        Returns:
            Dict with 'image_base64', 'mime_type', 'prompt_used', 'style', 'model',
            'latency_ms', 'audit_log_id'
        """
        start_time = time.time()

        style_prefix = STYLE_PREFIXES.get(style, STYLE_PREFIXES["professional"])
        full_prompt = f"{style_prefix}{prompt}"

        size = ASPECT_RATIOS.get(aspect_ratio, "1024x1024")

        request_body = {
            "model": model,
            "prompt": full_prompt,
            "n": 1,
            "size": size,
            "output_format": "png",
        }

        endpoint = "/images/generations"

        try:
            response = self.client.post(endpoint, json=request_body)
            response.raise_for_status()
            data = response.json()

            latency_ms = int((time.time() - start_time) * 1000)

            image_base64 = None
            if data.get("data") and len(data["data"]) > 0:
                image_base64 = data["data"][0].get("b64_json")

            audit_log_id = self._create_audit_log(
                endpoint=endpoint,
                model=model,
                prompt=full_prompt,
                latency_ms=latency_ms,
                status="success" if image_base64 else "no_image",
            )

            if not image_base64:
                return {
                    "image_base64": None,
                    "mime_type": None,
                    "prompt_used": full_prompt,
                    "style": style,
                    "model": model,
                    "latency_ms": latency_ms,
                    "audit_log_id": audit_log_id,
                    "error": "No image was generated. Try a different prompt.",
                }

            return {
                "image_base64": image_base64,
                "mime_type": "image/png",
                "prompt_used": full_prompt,
                "style": style,
                "model": model,
                "latency_ms": latency_ms,
                "audit_log_id": audit_log_id,
            }

        except httpx.HTTPStatusError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_text = e.response.text[:500] if e.response else str(e)
            self._create_audit_log(
                endpoint=endpoint,
                model=model,
                prompt=full_prompt,
                latency_ms=latency_ms,
                status="error",
                error_message=error_text,
            )
            logger.error(f"Image generation error: {e.response.status_code} - {error_text}")
            return {
                "image_base64": None,
                "mime_type": None,
                "prompt_used": full_prompt,
                "style": style,
                "model": model,
                "latency_ms": latency_ms,
                "error": f"Image generation failed: {e.response.status_code}",
            }
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            self._create_audit_log(
                endpoint=endpoint,
                model=model,
                prompt=full_prompt,
                latency_ms=latency_ms,
                status="error",
                error_message=str(e),
            )
            logger.error(f"Image generation request failed: {e}")
            return {
                "image_base64": None,
                "mime_type": None,
                "prompt_used": full_prompt,
                "style": style,
                "model": model,
                "latency_ms": latency_ms,
                "error": f"Image generation failed: {str(e)}",
            }

    def get_available_styles(self) -> List[Dict[str, str]]:
        return [
            {"id": k, "name": k.title(), "description": v.strip()}
            for k, v in STYLE_PREFIXES.items()
        ]

    def get_available_aspect_ratios(self) -> List[Dict[str, str]]:
        return [
            {"id": k, "description": v}
            for k, v in ASPECT_RATIOS.items()
        ]
