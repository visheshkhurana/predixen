"""Track whether the copilot's model calls actually succeeded.

The specialist agents swallow provider errors (no key, 401, timeout, outage)
and fall back to rule-based output, so the chat endpoint used to return a
canned analysis labelled ``confidence: high`` / ``grounding_status: VERIFIED``
even when no model answered the founder's question. ``TrackedLLMRouter``
wraps the real router, counts successful and failed model calls, and lets the
endpoint label the response honestly.
"""
from __future__ import annotations

import re
import threading
from typing import Any, Dict, Optional

AI_UNAVAILABLE_NOTICE = (
    "The AI assistant is unavailable right now. Below is a rule-based summary "
    "of your numbers, not an answer to your question. Try again in a few minutes."
)

AI_PARTIAL_NOTICE = (
    "Part of the AI analysis failed, so some of this answer is a rule-based "
    "summary of your numbers rather than a model's answer. Try again in a few "
    "minutes for a full answer."
)

LLM_STATUS_OK = "ok"
LLM_STATUS_PARTIAL = "partial"
LLM_STATUS_UNAVAILABLE = "unavailable"
LLM_STATUS_NOT_USED = "not_used"

_CONFIDENCE_LINE = re.compile(r"^\s*confidence\s*:\s*\w+\s*$", re.IGNORECASE)


def _has_content(result: Any) -> bool:
    if isinstance(result, dict):
        content = result.get("content")
        return isinstance(content, str) and bool(content.strip())
    return result is not None


class TrackedLLMRouter:
    """Proxy around an LLM router that records model-call outcomes.

    Only text-generation calls (``chat``, ``smart_chat``) count; everything
    else is passed straight through. Agent calls run in worker threads, so the
    counters are guarded by a lock.
    """

    _TRACKED = ("chat", "smart_chat")

    def __init__(self, inner: Any):
        self._inner = inner
        self._lock = threading.Lock()
        self.successes = 0
        self.failures = 0
        self.last_error: Optional[str] = None

    def _record(self, ok: bool, error: Optional[BaseException] = None) -> None:
        with self._lock:
            if ok:
                self.successes += 1
            else:
                self.failures += 1
                if error is not None:
                    self.last_error = f"{type(error).__name__}: {error}"[:300]

    def _wrap(self, name: str):
        fn = getattr(self._inner, name)

        def call(*args: Any, **kwargs: Any) -> Any:
            try:
                result = fn(*args, **kwargs)
            except Exception as e:  # recorded, then re-raised unchanged
                self._record(False, e)
                raise
            # smart_chat reports some failures as {"content": "", "error": ...}
            # instead of raising; an empty answer is not a model answer either.
            self._record(_has_content(result))
            return result

        return call

    def __getattr__(self, name: str) -> Any:
        if name in self._TRACKED:
            return self._wrap(name)
        return getattr(self._inner, name)

    @property
    def status(self) -> str:
        with self._lock:
            if self.successes == 0 and self.failures == 0:
                return LLM_STATUS_NOT_USED
            if self.successes == 0:
                return LLM_STATUS_UNAVAILABLE
            if self.failures > 0:
                return LLM_STATUS_PARTIAL
            return LLM_STATUS_OK


def downgrade_confidence_lines(lines: Any, label: str = "LOW (rule-based, AI unavailable)") -> Any:
    """Rewrite "Confidence: HIGH" style lines produced by rule-based agents."""
    if not isinstance(lines, list):
        return lines
    return [
        f"Confidence: {label}" if isinstance(s, str) and _CONFIDENCE_LINE.match(s) else s
        for s in lines
    ]


def downgrade_decision_advisor(advisor: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Mark the decision advisor's rule-based recommendation as low confidence.

    Simulation numbers are left intact: they are computed from the founder's
    own data. Only the claim that they answer the question confidently goes.
    """
    if not isinstance(advisor, dict):
        return advisor
    out = dict(advisor)
    rec = out.get("recommendation")
    if isinstance(rec, dict):
        rec = dict(rec)
        rec["confidence"] = "low"
        reason = rec.get("confidence_reasoning") or ""
        note = "AI assistant unavailable: rule-based recommendation, not a model's answer to your question"
        rec["confidence_reasoning"] = f"{note}; {reason}" if reason else note
        out["recommendation"] = rec
    return out
