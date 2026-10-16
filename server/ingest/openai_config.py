"""Resolve the OpenAI credentials the ingest extractors use.

Matches server/replit_integrations/chat/routes.ts: the Replit AI-integration
key wins when present, otherwise the plain OPENAI_API_KEY that production
sets. The integration base URL is honoured only when it is set, so a plain
OpenAI key is never sent to a stale Replit proxy URL that happens to be blank.
"""
import os
from typing import Optional, Tuple


def resolve_openai_config() -> Tuple[Optional[str], Optional[str]]:
    api_key = (
        os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or None
    )
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL") or None
    return api_key, base_url
