"""HAG-401 — `/events` answered an UNSIGNED request before it checked the signature.

TWO DEFECTS, in one handler, and the second is the one that matters.

  1. `body = await request.json()` was **unguarded**. A malformed body raised out
     of the handler and Starlette answered its bare **500**.
  2. The `url_verification` branch **returned before** `_verify_slack_signature`
     ran. So any anonymous caller who POSTed
     `{"type":"url_verification","challenge":"..."}` got a **200 echoing their own
     input**, with no signature ever checked.

The invariant defect 2 breaks is stated by this repo, in this tree:
`server/api/email_tracking.py` says of its own parse — *"still after the signature
check so an unverified body is never parsed."* And `slack_bot.py` itself already
follows the rule one handler up: `handle_slash_command` verifies and only then
reads its payload.

**Why nothing here posts to the route.** `server/api/slack_bot.py` reads
`SLACK_SIGNING_SECRET`, and the route is publicly reachable at
`POST /api/slack/events` (Express rewrites `^/api` away, `server/index.ts`), so
posting a real body to it is a real delivery. The checks here are therefore of two
kinds, and neither sends a request anywhere:

  * the REAL handler's source is read, and its `try` structure is parsed with
    `ast`, so "the parse is guarded" and "the verify comes first" are measurements
    over the file's own bytes rather than readings of it;
  * a STAND-IN app carries both the old and the new order, so the instrument is
    shown to discriminate instead of merely agreeing with the fix.

The stand-in is the weaker half and is labelled as such: it proves what the two
orders DO, never that the real handler has the new one. That the real handler's
statements sit in that order is the source-and-`ast` half's job.

**The limit, stated plainly:** this file reads source and builds throwaway apps. It
cannot see the real route answer end to end, and it does not exercise HMAC
verification at all - `_verify_slack_signature` is stubbed in the stand-in.
"""

from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

SLACK_BOT = Path(__file__).resolve().parents[2] / "server/api/slack_bot.py"


def source() -> str:
    return SLACK_BOT.read_text(encoding="utf-8")


def handler_body(src: str, marker: str) -> str:
    """The text of one `async def` handler, to the next top-level `@router`."""
    start = src.index(marker)
    nxt = src.find("\n@router", start)
    assert nxt != -1, f"{marker!r} is the last handler in the file — the extractor ran off the end"
    body = src[start:nxt]
    assert len(body) > 200, f"{marker!r} extracted {len(body)} characters, not a handler"
    return body


def code_only(text: str) -> str:
    """`text` with every `#` comment blanked to spaces, columns and length preserved.

    The anchors below name REAL statements, and a handler this size also says the names
    of its own statements in prose: the fix comment in `slack_bot.py` narrates the order
    that used to ship and writes `body = await request.json()` while doing it. A raw
    `.index` over the full text finds the COMMENT first and reports the old order as the
    code's order — reading the file instead of measuring it, which is the defect this
    card is about, one level up. It caught this file: that is why this function exists.
    Blanking comments keeps every offset valid and leaves only code to match.

    LIMIT, stated: this blanks `#` comments, not docstrings. An anchor appearing inside a
    docstring would still be matched. None do; `offset_of` would see two occurrences and
    fail loudly if one ever did.
    """
    lines = text.splitlines(keepends=True)
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError) as exc:
        raise AssertionError(
            f"the extracted handler could not be tokenized ({exc!r}), so the anchor offsets "
            "below cannot be trusted — this test must not fall back to matching raw text, "
            "because raw text is exactly what matched a comment"
        )
    out = list(lines)
    for tok in tokens:
        if tok.type != tokenize.COMMENT:
            continue
        row, col0, col1 = tok.start[0], tok.start[1], tok.end[1]
        out[row - 1] = out[row - 1][:col0] + " " * (col1 - col0) + out[row - 1][col1:]
    return "".join(out)


def offset_of(body: str, needle: str, why: str | None = None) -> int:
    """Where `needle` sits in the handler's CODE, which it must do exactly once.

    Two failures, and they mean different things:
      * absent   — the statement was renamed or removed, so this test cannot see what it
                   claims to be measuring;
      * repeated — the anchor does not name ONE statement, so whichever occurrence
                   `.index` picks is arbitrary. Found the hard way in this very file.
    """
    code = code_only(body)
    n = code.count(needle)
    if n != 1:
        # The count is in EVERY message, `why` or not: a message that hides what was
        # actually measured is how a missing argument once read as a missing anchor.
        raise AssertionError(
            f"the anchor {needle!r} appears {n} time(s) in the code of the extracted handler "
            f"(0 = renamed or removed, >1 = it does not name one statement), so this test cannot "
            f"measure what it claims to" + (f" — {why}" if why else "")
        )
    return code.index(needle)


def guarded_parse_lines(src: str, func_name: str) -> list[int]:
    """Line numbers of `await request.json()` calls that sit inside a ValueError-catching try."""
    out: list[int] = []
    for fn in ast.walk(ast.parse(src)):
        if not (isinstance(fn, ast.AsyncFunctionDef) and fn.name == func_name):
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.Try):
                continue
            catches = any(
                h.type is None
                or (isinstance(h.type, ast.Name) and h.type.id in ("ValueError", "Exception", "BaseException"))
                or (isinstance(h.type, ast.Tuple) and any(
                    isinstance(e, ast.Name) and e.id in ("ValueError", "Exception", "BaseException")
                    for e in h.type.elts
                ))
                for h in node.handlers
            )
            if not catches:
                continue
            for stmt in node.body:
                for sub in ast.walk(stmt):
                    if (isinstance(sub, ast.Await)
                            and isinstance(sub.value, ast.Call)
                            and getattr(sub.value.func, "attr", "") == "json"):
                        out.append(sub.lineno)
    return out


# --------------------------------------------------------------------------
# The order — the invariant this file broke
# --------------------------------------------------------------------------


def test_the_signature_is_verified_before_the_body_is_parsed():
    """Defect 2, in its narrowest form: nothing parses the body before the HMAC check."""
    body = handler_body(source(), "async def handle_slack_events(")

    verify = offset_of(
        body,
        "_verify_slack_signature(body_bytes, timestamp, signature)",
        "the signature check is gone from handle_slack_events — the body is read with nothing "
        "establishing it came from Slack",
    )
    parse = offset_of(
        body,
        "body = await request.json()",
        "the `body = await request.json()` call is gone from handle_slack_events",
    )
    assert verify < parse, (
        "the signature must be verified BEFORE the body is parsed. Every statement between the "
        "top of the handler and this check runs on input no one has authenticated yet."
    )


def test_the_url_verification_branch_is_reached_only_after_verification():
    """Defect 2 proper: the branch that ANSWERS the caller must come after the check.

    A guard that exists but sits below the early `return` is not a guard. This is the
    assertion that would have caught the defect, because it does not ask whether a
    check exists — it asks where it sits relative to the branch that responds.
    """
    body = handler_body(source(), "async def handle_slack_events(")

    verify = offset_of(
        body,
        "_verify_slack_signature(body_bytes, timestamp, signature)",
        "the signature check is gone from handle_slack_events",
    )
    answer = offset_of(
        body,
        'return JSONResponse({"challenge": body.get("challenge")})',
        "the url_verification early return is gone — this test can no longer see the branch it "
        "was written for",
    )
    assert verify < answer, (
        "the url_verification branch returns the caller's own challenge BEFORE the signature is "
        "checked, so an anonymous POST of {\"type\":\"url_verification\",\"challenge\":\"...\"} gets "
        "a 200 with no signature ever verified"
    )


def test_the_parse_is_guarded():
    """Defect 1, measured on the file's own `try` structure rather than read off it."""
    src = source()
    assert guarded_parse_lines(src, "handle_slack_events"), (
        "no `await request.json()` inside a ValueError-catching try was found in "
        "handle_slack_events — the parse is unguarded, so a malformed body raises out of the "
        "handler and Starlette answers its bare 500"
    )


def test_the_parse_guard_instrument_is_not_vacuous():
    """Non-vacuity for the test above: the same instrument, one indent level apart.

    Without this, `guarded_parse_lines` could return [] for a buggy reason - a filename
    typo, a wrong function name - and the guard test would fail for a reason that has
    nothing to do with the guard. The fixtures differ only in whether the parse sits
    inside the try.
    """
    inside = "async def h(request):\n    try:\n        body = await request.json()\n    except ValueError:\n        pass\n"
    outside = "async def h(request):\n    body = await request.json()\n    try:\n        x = 1\n    except ValueError:\n        pass\n"
    assert guarded_parse_lines(inside, "h"), "the instrument missed a parse that IS guarded"
    assert not guarded_parse_lines(outside, "h"), (
        "the instrument called a parse guarded when it sits ABOVE the try — it is measuring the "
        "wrong thing"
    )


def test_the_offset_instrument_reads_code_and_not_prose():
    """Non-vacuity for `code_only`, pinned because it already failed once in this file.

    The first version of `offset_of` indexed raw handler text, and the fix's own comment
    writes `body = await request.json()` while describing the order that used to ship. The
    check therefore resolved to the COMMENT and reported the pre-fix order — the test
    failed for a reason opposite to the code's real state. That is the defect this card is
    about, one level up, and it is measured here rather than asserted about.
    """
    handler = (
        "async def h(request):\n"
        "    # prose: the old order was body = await request.json() and then a check\n"
        "    if not _verify_slack_signature(b, t, s):\n"
        "        raise HTTPException(status_code=401)\n"
        "    body = await request.json()\n"
        "    return body\n"
    )
    anchor = "body = await request.json()"
    assert handler.count(anchor) == 2, "the fixture no longer contains the prose occurrence"
    assert code_only(handler).count(anchor) == 1, (
        "the masking left the prose occurrence matchable, so an anchor can still be found in a "
        "comment — the failure this function exists to prevent"
    )
    off = offset_of(handler, anchor)
    assert off == handler.rindex(anchor), (
        "the anchor resolved to the comment rather than the statement — the exact failure that "
        "made this test file report the reverse of what the code does"
    )
    assert off > offset_of(handler, "if not _verify_slack_signature(b, t, s)"), (
        "the two offsets are not in the same coordinate system, so every ordering assertion in "
        "this file would be meaningless"
    )


def test_a_repeated_anchor_fails_and_the_message_names_the_count():
    """A message that hides what was measured once read as a missing anchor. Pinned."""
    twice = (
        "async def h(request):\n"
        "    body = await request.json()\n"
        "    body = await request.json()\n"
    )
    with pytest.raises(AssertionError) as err:
        offset_of(twice, "body = await request.json()", "the parse is gone")
    assert "appears 2 time(s)" in str(err.value), (
        f"the count is not in the failure message: {err.value}"
    )
    assert "the parse is gone" in str(err.value), (
        "the call site's explanation was dropped from the message, so the reader loses why the "
        "anchor mattered"
    )
    with pytest.raises(AssertionError) as err2:
        offset_of(twice, "body = await request.form()", "the form read is gone")
    assert "appears 0 time(s)" in str(err2.value), (
        f"an absent anchor is not reported as absent: {err2.value}"
    )


def test_the_body_shape_is_checked_before_the_first_deref():
    """`isinstance(body, dict)` guards the `body.get` immediately below it.

    A signed body that is not an object - `[1,2,3]` - would otherwise raise
    AttributeError at the handler's top level, where nothing catches it.
    """
    body = handler_body(source(), "async def handle_slack_events(")

    parse = offset_of(body, "body = await request.json()", "the parse is gone")
    guard = offset_of(
        body,
        "isinstance(body, dict)",
        "no `isinstance(body, dict)` guard — the body is dereferenced as a mapping with nothing "
        "establishing that it is one",
    )
    deref = offset_of(body, 'body.get("type")', "the `body.get(\"type\")` deref is gone")
    assert parse < guard < deref, (
        "the isinstance(body, dict) guard must sit between the parse and the first dereference"
    )


def test_the_sibling_handler_states_the_same_invariant():
    """Non-vacuity from the file itself: `handle_slash_command` already obeys the rule.

    If this ever stops being true, the "the route was the odd one out" argument loses
    its basis and the fix should be re-decided rather than left standing on a
    precedent that no longer exists.
    """
    body = handler_body(source(), "async def handle_slash_command(")
    verify = offset_of(
        body,
        "_verify_slack_signature(body, timestamp, signature)",
        "handle_slash_command no longer verifies a signature — the precedent this fix cites is gone",
    )
    reads = offset_of(body, "await request.form()", "handle_slash_command no longer reads a payload")
    assert verify < reads, (
        "the sibling handler now reads its payload before verifying, so it no longer demonstrates "
        "the order this fix restores"
    )


# --------------------------------------------------------------------------
# The mechanism, measured on a stand-in that carries BOTH orders
# --------------------------------------------------------------------------


def _build(order: str) -> TestClient:
    """A stand-in with the handler's shape under the old order or the new one.

    `_verify_slack_signature` is stubbed to fail, which is what it does for an
    unsigned request AND for one signed with the wrong key - the two cases are
    indistinguishable from the handler's side.
    """
    app = FastAPI()

    @app.post("/events")
    async def handle(request: Request):
        body_bytes = await request.body()
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        if order == "before":
            body = await request.json()
            if body.get("type") == "url_verification":
                return JSONResponse({"challenge": body.get("challenge")})
            if not _verify(body_bytes, timestamp, signature):
                raise HTTPException(status_code=401, detail="Invalid Slack signature")
        else:
            if not _verify(body_bytes, timestamp, signature):
                raise HTTPException(status_code=401, detail="Invalid Slack signature")
            try:
                body = await request.json()
            except ValueError:
                raise HTTPException(status_code=400, detail="Malformed JSON body")
            if body.get("type") == "url_verification":
                return JSONResponse({"challenge": body.get("challenge")})

        return JSONResponse({"ok": True})

    return TestClient(app, raise_server_exceptions=False)


def _verify(body: bytes, timestamp: str, signature: str) -> bool:
    return False


UNSIGNED_CHALLENGE = b'{"type":"url_verification","challenge":"probe"}'
MALFORMED = b"{not json at all"


def test_the_instrument_discriminates_between_the_two_orders():
    """The whole finding in one test, and the reason the stand-in exists.

    Under the order that shipped, an unsigned url_verification is answered **200**
    with the caller's own challenge, and a malformed body is a **500**. Under the
    fixed order both are refused. If the old order ever stops producing a 200 here,
    this instrument has gone stale and the tests above mean nothing.
    """
    before = _build("before").post("/events", content=UNSIGNED_CHALLENGE,
                                   headers={"Content-Type": "application/json"})
    assert before.status_code == 200, (
        f"the old order answered {before.status_code}, not 200 — this stand-in no longer "
        "reproduces the defect it was built for"
    )
    assert b"probe" in before.content, "the 200 did not echo the caller's challenge — wrong probe"

    after = _build("after").post("/events", content=UNSIGNED_CHALLENGE,
                                 headers={"Content-Type": "application/json"})
    assert after.status_code == 401, (
        f"an unsigned url_verification still gets {after.status_code} under the fixed order"
    )

    old_malformed = _build("before").post("/events", content=MALFORMED,
                                          headers={"Content-Type": "application/json"})
    assert old_malformed.status_code == 500, (
        f"the old order answered {old_malformed.status_code} for a malformed body, not 500"
    )
    new_malformed = _build("after").post("/events", content=MALFORMED,
                                        headers={"Content-Type": "application/json"})
    assert new_malformed.status_code == 401, (
        "an unverified malformed body must be refused by the signature check before the parse is "
        "ever reached"
    )


def test_a_signed_url_verification_still_works():
    """The behaviour risk of this fix, measured rather than assumed.

    Slack signs its `url_verification` request like any other, so requiring a
    signature must NOT break the handshake. If it did, the fix would trade an
    anonymous echo for a Slack app that never installs - a worse outcome than the
    defect. The stand-in verifies this time, which is the only difference.
    """
    app = FastAPI()
    # Explicit rather than clever: this stands in for `_verify_slack_signature`
    # answering YES, which is the only difference from the stand-in above.
    signature_is_valid = True

    @app.post("/events")
    async def handle(request: Request):
        if not signature_is_valid:
            raise HTTPException(status_code=401, detail="Invalid Slack signature")
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(status_code=400, detail="Malformed JSON body")
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Body must be a JSON object")
        if body.get("type") == "url_verification":
            return JSONResponse({"challenge": body.get("challenge")})
        return JSONResponse({"ok": True})

    client = TestClient(app, raise_server_exceptions=False)
    ok = client.post("/events", content=UNSIGNED_CHALLENGE,
                     headers={"Content-Type": "application/json"})
    assert ok.status_code == 200, (
        f"a SIGNED url_verification now gets {ok.status_code} — the fix has broken Slack's install "
        "handshake"
    )
    assert ok.json() == {"challenge": "probe"}, "the challenge was not echoed back to Slack"


def test_a_signed_malformed_body_is_a_400_and_not_a_500():
    """Non-vacuity for the parse guard: it must be REACHABLE, or it is decoration.

    Only a caller whose signature verified can get here, so this is not a lever an
    anonymous caller can pull - but an unreachable `except` would be a branch that
    no test and no caller can ever exercise, and this file has form for guards that
    do not cover the line below them.
    """
    app = FastAPI()

    @app.post("/events")
    async def handle(request: Request):
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(status_code=400, detail="Malformed JSON body")
        return JSONResponse({"ok": True})

    client = TestClient(app, raise_server_exceptions=False)
    r = client.post("/events", content=MALFORMED, headers={"Content-Type": "application/json"})
    assert r.status_code == 400, (
        f"a malformed body answered {r.status_code}; unguarded it was a bare 500 from Starlette"
    )
