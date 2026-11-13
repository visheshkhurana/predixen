"""HAG-384 — the email-tracking receiver must not answer 500 (or 200) for its own faults.

Three defects on `main`, all pre-existing and all confirmed at both refs in
`sentinel-review-pr77-pass-with-findings-e76c18be.md`:

  1. `resend_webhook` parsed the body ABOVE every `try` in the handler, so a
     signed body that was not a JSON object raised uncaught and answered 500.
     The sibling receiver (`notifications.py:223-228`) answers 400 for the
     identical input, so the two receivers disagreed about whose fault it was.
  2. `resend_webhook`'s `except` returned a plain dict, which is HTTP 200: a
     failed write was reported to Resend as a success, so Resend never
     redelivered and the event was dropped with nothing to show for it.
  3. `submit_feedback_api` had the same parse-above-try shape.

**Why this file does not post to either endpoint, and what it does instead.**
HAG-384's dispatch forbids probing the real webhook routes with valid JSON - by
test, by curl or by fixture - because reaching the parse means forging a valid
Svix signature, and a valid signed body is a real delivery as far as the handler
is concerned. So the checks here are of two kinds, and neither posts anything:

  * the REAL handler's source is read to pin the shape of the guard and the
    order of verification-before-parse;
  * a STAND-IN app built in this file carries the same two return shapes, so the
    HTTP consequence ("a returned dict is 200, a JSONResponse(500) is 500") is
    measured rather than asserted from memory.

The stand-in is the weaker half and is labelled as such: it proves what the two
return shapes DO, never that the real handler returns one of them. That link is
the source read's job. Its limit, stated plainly: this file reads source and
builds one throwaway app, so it cannot see the real handler run end to end.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.testclient import TestClient

TRACKING = Path(__file__).resolve().parents[2] / "server/api/email_tracking.py"


def source() -> str:
    return TRACKING.read_text(encoding="utf-8")


def handler_body(src: str, marker: str) -> str:
    """The text of one `async def` handler, to the next top-level `@router`."""
    start = src.index(marker)
    nxt = src.find("\n@router", start)
    assert nxt != -1, f"{marker!r} is the last handler in the file — the extractor ran off the end"
    body = src[start:nxt]
    assert len(body) > 200, f"{marker!r} extracted {len(body)} characters, not a handler"
    return body


def test_a_malformed_body_raises_the_exception_the_new_guard_catches():
    """The clause has to name the exception that actually occurs.

    This is the one behavioural check about the parse that needs no endpoint and
    no signature: build a real Starlette `Request` over a malformed body and show
    that `await request.json()` raises `ValueError`. `json.JSONDecodeError`
    subclasses it, so `except ValueError` is the clause that matches — and a
    guard written as `except json.JSONDecodeError` would miss the `UnicodeDecodeError`
    sibling, which is also a `ValueError`.
    """
    import anyio

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/email-tracking/webhooks/resend",
        "headers": [(b"content-type", b"application/json")],
    }

    async def receive():
        return {"type": "http.request", "body": b"not json at all", "more_body": False}

    request = Request(scope, receive)
    with pytest.raises(ValueError):
        anyio.run(request.json)


def test_the_receiver_parses_inside_a_guard_and_after_the_signature_check():
    body = handler_body(source(), "async def resend_webhook(")

    parse = body.index("await request.json()")
    verify = body.index("resend_webhook_sig.verify(")
    assert verify < parse, (
        "the body is parsed before the signature is checked — the file's own note at :30 says "
        "verification happens before the body is parsed, and an unverified body must never be read"
    )

    guard = body[parse - 400 : parse + 400]
    assert "try:" in body[:parse], "the parse sits above every try in the handler — the original defect"
    assert re.search(r"except\s+ValueError\s*:", guard), "nothing catches a malformed body"
    assert re.search(r"HTTPException\(\s*status_code=400", guard), "a malformed body must answer 400, not 500"
    assert "isinstance(body, dict)" in guard, (
        "a JSON array or string is a valid parse and still has no .get() — it raised AttributeError "
        "and answered 500 for the same reason"
    )


def test_the_receiver_failure_path_is_not_a_200():
    body = handler_body(source(), "async def resend_webhook(")

    assert 'return {"status": "error"' not in body, (
        "a plain dict return is HTTP 200 — this is the dropped-retry defect: Resend reads 200 as "
        "handled, does not redeliver, and the event is lost silently"
    )
    assert re.search(r"JSONResponse\(\s*status_code=500", body), "the failure path must answer 5xx"
    assert "db.rollback()" in body and "db.close()" in body, "the rollback/close shape was disturbed"


def test_the_feedback_handler_got_the_same_parse_guard():
    body = handler_body(source(), "async def submit_feedback_api(")

    parse = body.index("await request.json()")
    assert "try:" in body[:parse], "the parse at the feedback endpoint still sits above the try"
    guard = body[parse - 400 : parse + 400]
    assert re.search(r"except\s+ValueError\s*:", guard)
    assert re.search(r"HTTPException\(\s*status_code=400", guard)
    assert "isinstance(body, dict)" in guard


def test_a_returned_dict_is_200_and_a_jsonresponse_500_is_not():
    """The mechanism behind defect 2, measured instead of remembered.

    A stand-in app only. It shows what the two return shapes do over HTTP; that
    the real handler now uses the second one is the source read's claim above.
    """
    app = FastAPI()

    @app.get("/dict")
    async def as_dict():
        return {"status": "error", "message": "the old shape"}

    @app.get("/json")
    async def as_json():
        return JSONResponse(status_code=500, content={"status": "error", "message": "the new shape"})

    client = TestClient(app)
    old, new = client.get("/dict"), client.get("/json")
    assert old.status_code == 200, "a dict return is no longer 200 — defect 2's premise has moved"
    assert old.json()["status"] == "error", "the old shape reported an error in the body, not the status"
    assert new.status_code == 500, "JSONResponse(500) did not answer 500"
    assert new.json()["status"] == "error", "the body contract changed; only the status was meant to"


def test_no_handler_in_this_file_returns_a_bare_error_dict():
    """The class, not just the two sites: nothing here may report a fault as a 200.

    `submit_feedback_api` is the deliberate exception and it is asserted by name,
    not excused by a loose pattern — it is a browser-facing form endpoint with no
    redelivery to preserve, and changing its status would change the contract its
    caller reads. HAG-384 scoped it out; this test is where that scoping is
    recorded so it is a decision rather than an oversight.
    """
    src = source()
    offenders = [
        m for m in re.finditer(r'\n[ \t]*return \{"status": "error"', src)
    ]
    assert len(offenders) == 1, (
        f"{len(offenders)} bare error-dict returns in {TRACKING.name}, expected exactly 1 "
        f"(submit_feedback_api, the scoped-out endpoint)"
    )
    feedback = src.index("async def submit_feedback_api(")
    assert offenders[0].start() > feedback, "the remaining bare error dict is not the feedback endpoint"
