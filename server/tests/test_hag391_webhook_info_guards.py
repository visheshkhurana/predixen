"""HAG-391 — the two INFO findings Sentinel filed against #124 at `fafd268d`.

Neither blocked #124 (`PASS-WITH-FINDINGS`, HIGH 0 / MEDIUM 0). They are the
surviving half of the defects #124 fixed, and they are different defects:

  1. `submit_feedback_api` returned a plain dict from its `except`, which is HTTP
     200 -- a row that was never written, reported to its caller as recorded.
     #124 scoped this out on purpose and pinned it here by name; the fix and the
     assertion change together.
  2. `resend_webhook` guards the ENVELOPE (`isinstance(body, dict)`) and not its
     contents, so a signed `{"data": "a string"}` passed the guard and raised
     `AttributeError` on the `.get()` one line down. Sentinel's sentence is
     *"the guard is not sufficient one line below itself"*.

**Why nothing here posts to either endpoint.** Same reason as #124's file, and it
is the dispatch boundary: `server/api/email_tracking.py` reads
`RESEND_WEBHOOK_SECRET`, so reaching the parse means forging a valid Svix
signature, and a valid signed body is a real delivery as far as the handler is
concerned. A test, a curl and a fixture are all the same act. So the checks here
are of two kinds and neither posts anything:

  * the REAL handler's source is read, and its `try` structure is parsed with
    `ast` -- so the claim "that raise is caught by neither guard" is a
    measurement over the file's own bytes rather than a reading of it;
  * a STAND-IN app built in this file measures what an escaping exception does
    over HTTP, and whether the handler's own `except` runs.

The stand-in is the weaker half and is labelled as such: it proves what an
escaping `AttributeError` DOES, never that the real handler raises one. That the
deref sits in an unprotected gap is the source-and-`ast` read's job.

**The limit, stated plainly:** this file reads source and builds throwaway apps.
It cannot see the real handler run end to end, and it does not verify the
signature path at all.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

TRACKING = Path(__file__).resolve().parents[2] / "server/api/email_tracking.py"
CATCHES_EVERYTHING = ("Exception", "BaseException")


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


def catching_line_spans(src: str) -> list[tuple[int, int]]:
    """Line ranges whose statements are inside a `try` that catches Exception.

    A `try`'s `orelse` and `finalbody` are NOT part of this: an exception raised
    in an `else` clause is not caught by that `try`'s handlers, and a `finally`
    does not catch anything. Only `node.body` is walked, which is the half a
    raise can actually be caught from.

    The span is taken from the first statement in the body to the last, so it
    covers every line nested inside the block.
    """
    spans: list[tuple[int, int]] = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Try) or not node.body:
            continue
        catches = any(
            h.type is None
            or (isinstance(h.type, ast.Name) and h.type.id in CATCHES_EVERYTHING)
            or (isinstance(h.type, ast.Tuple) and any(
                isinstance(e, ast.Name) and e.id in CATCHES_EVERYTHING for e in h.type.elts
            ))
            for h in node.handlers
        )
        if not catches:
            continue
        lo = min(s.lineno for s in node.body)
        hi = max(getattr(s, "end_lineno", s.lineno) or s.lineno for s in node.body)
        spans.append((lo, hi))
    return spans


def line_of(src: str, needle: str) -> int:
    """The 1-based line number of a unique `needle` in the file."""
    hits = [n for n, text in enumerate(src.splitlines(), start=1) if needle in text]
    assert len(hits) == 1, f"expected exactly one line carrying {needle!r}, found {hits}"
    return hits[0]


# --------------------------------------------------------------------------
# Finding 2 — the `data` deref, and the gap it sat in
# --------------------------------------------------------------------------


def test_the_data_guard_sits_between_the_assignment_and_the_deref():
    """The fix in its narrowest form: nothing dereferences `data` before it is checked."""
    body = handler_body(source(), "async def resend_webhook(")

    def offset_of(needle: str, why: str) -> int:
        # A missing needle must fail AS THE CLAIM, not as a bare ValueError from
        # `.index` — a failure that reads as a lookup error hides what was being
        # asserted, which is this floor's defect of the day in miniature.
        assert needle in body, why
        return body.index(needle)

    assign = offset_of('data = body.get("data"', "the `data` assignment is gone from the receiver")
    guard = offset_of(
        "isinstance(data, dict)",
        "no isinstance(data, dict) guard in the receiver — `data` is dereferenced unguarded",
    )
    deref = offset_of('data.get("email_id")', "the `data.get(\"email_id\")` deref is gone")
    assert assign < guard < deref, (
        "the isinstance(data, dict) guard must sit between the assignment and the first "
        "dereference — otherwise the AttributeError it exists to prevent is still reachable"
    )

    window = body[guard - 300 : guard + 300]
    assert re.search(r"HTTPException\(\s*status_code=400", window), (
        "the data guard must answer 400: a signed body whose `data` is not an object is the "
        "caller's error, the same as the envelope guard above it, and 400 does not ask for a retry"
    )


def test_the_deref_sits_in_a_gap_no_handler_catches():
    """The defect, measured on the file's own `try` structure rather than read off it.

    This is the assertion that would have caught #124's INFO 3 before it shipped.
    It does not look for a guard; it asks the parser whether ANY `try` in this
    module would have caught a raise on that line. Before HAG-391 the answer was
    no, and the consequence was a 500 for a body that can never succeed.
    """
    src = source()
    target = line_of(src, 'email_id = data.get("email_id") or data.get("id", "")')
    spans = catching_line_spans(src)

    covering = [s for s in spans if s[0] <= target <= s[1]]
    assert covering == [], (
        f"the deref on line {target} is now inside a try that catches Exception "
        f"({covering}), so this test can no longer see the gap it was written for — "
        f"either the fix moved it or this instrument has gone stale"
    )
    assert spans, "no Exception-catching try was found at all — the parser's view of this file is wrong"


def test_the_gap_is_real_by_construction():
    """Non-vacuity for the test above: the instrument fires when a line IS protected.

    Without this, `catching_line_spans` could return [] for a buggy reason and
    `test_the_deref_sits_in_a_gap_no_handler_catches` would pass on a file where
    every line is protected. Same tree, one indentation level, opposite answer.
    """
    protected = "async def f():\n    try:\n        x = 1\n        y = 2\n    except Exception:\n        pass\n"
    exposed = "async def f():\n    x = 1\n    try:\n        y = 2\n    except Exception:\n        pass\n"

    # Located by content, not by a hard-coded line number: a fixture that has to
    # be re-counted by hand every time it is edited is the same hand-counting the
    # instrument exists to replace.
    inside = line_of(protected, "y = 2")
    above = line_of(exposed, "x = 1")

    spans = catching_line_spans(protected)
    assert [s for s in spans if s[0] <= inside <= s[1]], "the parser missed a protected block"

    spans = catching_line_spans(exposed)
    assert spans, "the parser found no try at all in the exposed fixture"
    assert not [s for s in spans if s[0] <= above <= s[1]], (
        f"line {above} sits above the try and must read as exposed, not protected"
    )


# --------------------------------------------------------------------------
# The mechanism, measured on a stand-in app
# --------------------------------------------------------------------------


def test_an_escaping_attribute_error_is_a_500_and_never_reaches_the_handlers_own_except():
    """What the gap cost, measured instead of argued.

    A stand-in only. It shows three things at once, none of which is about the
    real handler: `"a string".get(...)` raises `AttributeError`; a raise that sits
    above the route's `try` answers **500**, which is the code that asks the
    sender to redeliver; and the handler's own `except` — the one that would have
    rolled back and logged — never runs.
    """
    app = FastAPI()
    ran = {"handler_except": False}

    @app.get("/deref-above-try")
    async def above_every_try():
        payload = {"data": "a string"}
        data = payload.get("data", {})
        email_id = data.get("email_id") or data.get("id", "")  # AttributeError, above the try
        try:
            ran["handler_except"] = True
            return {"status": "ok", "email_id": email_id}
        except Exception:
            ran["handler_except"] = True
            return JSONResponse(status_code=500, content={"status": "error"})

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/deref-above-try")

    assert response.status_code == 500, "an escaping AttributeError is not a 500 — the premise moved"
    assert ran["handler_except"] is False, (
        "the handler's own except ran, so the raise was NOT above every try — this stand-in no "
        "longer reproduces the shape it was built for"
    )
    assert "status" not in response.text, (
        "the 500 body carries the handler's error shape, which would mean the handler's own "
        "except produced it; an escaped raise leaves Starlette's bare body instead"
    )


def test_the_two_codes_are_distinguishable_by_a_sender():
    """400 and 500 are not interchangeable, and this is where that is measured.

    A sender that retries on 5xx and not on 4xx is the whole reason the fix picks
    400: it stops the retry loop for a body that can never succeed. The stand-in
    proves only that the two codes arrive as themselves.
    """
    app = FastAPI()

    @app.get("/caller")
    async def caller_error():
        return JSONResponse(status_code=400, content={"status": "error", "message": "caller"})

    @app.get("/ours")
    async def our_error():
        return JSONResponse(status_code=500, content={"status": "error", "message": "ours"})

    client = TestClient(app)
    assert client.get("/caller").status_code == 400
    assert client.get("/ours").status_code == 500


# --------------------------------------------------------------------------
# Finding 1 — the feedback endpoint's failure path
# --------------------------------------------------------------------------


def test_the_feedback_failure_path_is_not_a_200():
    """INFO 1: a dict return is 200, and a 200 for an unwritten row is a false record."""
    body = handler_body(source(), "async def submit_feedback_api(")

    assert 'return {"status": "error"' not in body, (
        "submit_feedback_api still returns a plain dict from its except, which is HTTP 200 — "
        "that reports a row that was never written as recorded"
    )
    assert re.search(r"JSONResponse\(\s*status_code=500", body), "the feedback failure path must answer 5xx"
    assert "db.rollback()" in body and "db.close()" in body, "the rollback/close shape was disturbed"


def test_the_feedback_success_path_is_untouched():
    """The fix is to the failure path only; a written row must still read as written."""
    body = handler_body(source(), "async def submit_feedback_api(")
    assert re.search(r'return \{"status": "ok"\}', body), "the success path changed and was not meant to"


def test_the_comment_that_claimed_the_scoping_is_gone():
    """A stale comment is a false claim, and this file has form.

    The handler used to carry *"the `except` below is left as it is, deliberately."*
    Once that stopped being true the sentence had to be deleted rather than
    reworded around — the same binary rule that closed #115's false docstring.
    """
    body = handler_body(source(), "async def submit_feedback_api(")
    assert "left as it is, deliberately" not in body, (
        "the comment still says the except was left alone; HAG-391 changed it, so the sentence is now false"
    )
