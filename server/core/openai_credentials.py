"""One place that decides which OpenAI credential to use, and what each endpoint accepts.

Two credentials can be present: the Replit AI-Integrations key, which only works
against its own proxy, and a plain ``OPENAI_API_KEY``, which talks to
api.openai.com directly. Every OpenAI call site in the onboarding path used to
answer this for itself; the extractor factories only ever read the integration
key, so a plain-key deployment failed PDF and Excel uploads.
"""
import os
from typing import Any, Dict, Optional, Tuple

MISSING_KEY_MESSAGE = (
    "OpenAI API key not configured. "
    "Set AI_INTEGRATIONS_OPENAI_API_KEY or OPENAI_API_KEY."
)


def resolve_openai_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Return ``(api_key, base_url)``. The integration key brings its proxy URL.

    A plain key must not inherit the integration base URL: the integration key
    is scoped to its proxy and a plain key sent there would be rejected.
    """
    integration_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    if integration_key:
        return integration_key, os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")

    plain_key = os.environ.get("OPENAI_API_KEY")
    return (plain_key, None) if plain_key else (None, None)


def missing_key_error() -> ValueError:
    return ValueError(MISSING_KEY_MESSAGE)


def is_missing_key_error(exc: BaseException) -> bool:
    """True for the one failure a caller must not swallow: no credential at all.

    Falling back to pattern-only metrics on a missing key turns a configuration
    error into an empty result, which is how a broken deployment stays invisible.
    """
    return "OpenAI API key not configured" in str(exc)


def chat_sampling_params(
    base_url: Optional[str], *, max_tokens: int, temperature: float
) -> Dict[str, Any]:
    """Sampling kwargs for a GPT-5 Chat Completions call on this endpoint.

    The integration proxy accepts ``max_tokens`` and a custom temperature.
    api.openai.com rejects both for GPT-5: it wants ``max_completion_tokens``
    and only the default temperature. ``max_completion_tokens`` also counts
    reasoning tokens, so the direct path doubles the budget to leave room for
    them inside the same cap.
    """
    if base_url:
        return {"max_tokens": max_tokens, "temperature": temperature}
    return {"max_completion_tokens": max(max_tokens * 2, 1024)}
