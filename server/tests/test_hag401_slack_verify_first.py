"""HAG-401 — `/events` answered an UNSIGNED request before it checked the signature.

TWO DEFECTS, in one handler, and the second is the one that matters.

  1. `body = await request.json()` was **unguarded**. A malformed body raised out
     of the handler and Starlette answered its bare **500**.
  2. The `url_verification` branch **returned before** `_verify_slack_signature`
     ran. So any caller who POSTed
     `{"type":"url_verification","challenge":"..."}` got a **200 echoing their own
     input**, with no signature ever checked.

The invariant defect 2 breaks is stated by this repo, in this tree.
`server/api/email_tracking.py` says of its own parse, verbatim at `:30`:

    # Verification happens before the body is parsed and before get_db().

and does it: `:38` verifies the signature, `:41` calls `await request.json()`.
`slack_bot.py` itself follows the rule one handler up: `handle_slash_command`
verifies at `:330` and only then reads its payload at `:333`.

**THE SHAPE.** The handler now branches on whether signature headers are present
at all. Headers present -> verify, then parse, then answer; a real event is
unchanged and still requires a signature. Headers absent -> the handshake is
answered and NOTHING ELSE is; every other unsigned request is refused. That
branch is deliberate: whether Slack SIGNS the `url_verification` handshake is not
established, and the install handshake happens once, so a 401 there is
unrecoverable in a way an echo is not. The echo returns the string the caller
supplied, so it is not a lever.

**WHY NOTHING HERE POSTS TO THE ROUTE.** `server/api/slack_bot.py` reads
`SLACK_SIGNING_SECRET`, and the route is publicly reachable at
`POST /api/slack/events` (Express rewrites `^/api` away, `server/index.ts`), so
posting a real body to it is a real delivery. The checks here are therefore of two
kinds, and neither sends a request anywhere:

  * the REAL handler's source is read, and its `try` structure is parsed with
    `ast`, so "the parse is guarded" and "the verify comes first" are measurements
    over the file's own bytes rather than readings of it;
  * a STAND-IN app carries the pre-fix shape and the new one, so the instrument is
    shown to discriminate instead of merely agreeing with the fix.

**The stand-in is the weaker half and is labelled as such.** Its verifier is a
boolean STUB, not HMAC, so it measures the SHAPE of the two orders - which request
reaches which branch - and never whether Slack signs the handshake. That claim is
not testable here. The handler's own comment says so rather than calling it
measured. The limit, stated plainly: this file reads source and builds throwaway
apps; it cannot see the real route answer end to end, and it does not exercise
HMAC verification at all.
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

# The two branch openings, used to split the handler into readable sections.
SIGNED_OPEN = "if signature and timestamp:"
UNSIGNED_OPEN = "# No signature headers at all."

CHALLENGE_RETURN = 'return JSONResponse({"challenge": body.get("challenge")})'
VERIFY_CALL = "_verify_slack_signature(body_bytes, timestamp, signature)"
PARSE = "body = await request.json()"
SHAPE_GUARD = "isinstance(body, dict)"
REFUSE = 'raise HTTPException(status_code=401, detail="Invalid Slack signature")'


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


def events_handler() -> str:
    return handler_body(source(), "async def handle_slack_events(")


def _split(h: str, marker: str) -> str:
    """The section of `h` starting at `marker`, which must occur exactly once.

    Exactly-once is asserted rather than assumed: a section boundary that matches
    twice would silently measure the wrong half of the handler, and this file has
    already been bitten once by an anchor that matched prose.
    """
    n = h.count(marker)
    assert n == 1, f"the branch marker {marker!r} appears {n} time(s), not once"
    return h[h.index(marker):]


def signed_branch(h: str) -> str:
    return _split(h, SIGNED_OPEN).split(UNSIGNED_OPEN)[0]


def unsigned_branch(h: str) -> str:
    return _split(h, UNSIGNED_OPEN)


def code_only(text: str) -> str:
    """`text` with every `#` comment blanked to spaces, columns and length preserved.

    The anchors below name REAL statements, and a handler this size also says the names
    of its own statements in prose: an earlier comment in `slack_bot.py` narrated the
    order that used to ship and wrote `body = await request.json()` while doing it. A
    raw `.index` over the full text finds the COMMENT first and reports the old order as
    the code's order — reading the file instead of measuring it, which is the defect this
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


def offset_of(section: str, needle: str, why: str | None = None) -> int:
    """Where `needle` sits in a section's CODE, which it must do exactly once.

    Two failures, and they mean different things:
      * absent   — the statement was renamed or removed, so this test cannot see what it
                   claims to be measuring;
      * repeated — the anchor does not name ONE statement, so whichever occurrence
                   `.index` picks is arbitrary. Found the hard way in this very file.

    NOTE on scope: since the handler now has two parse sites, callers pass a BRANCH
    rather than the whole handler whenever the anchor is one of the duplicated
    statements. Passing the whole handler here would fail loudly on the count, which is
    the intended behaviour rather than an inconvenience.
    """
    code = code_only(section)
    n = code.count(needle)
    if n != 1:
        # The count is in EVERY message, `why` or not: a message that hides what was
        # actually measured is how a missing argument once read as a missing anchor.
        raise AssertionError(
            f"the anchor {needle!r} appears {n} time(s) in the code of the extracted section "
            f"(0 = renamed or removed, >1 = it does not name one statement), so this test cannot "
            f"measure what it claims to" + (f" — {why}" if why else "")
        )
    return code.index(needle)


def _parses_in(fn: ast.AST) -> list[int]:
    out: list[int] = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.Await)
                and isinstance(node.value, ast.Call)
                and getattr(node.value.func, "attr", "") == "json"):
            out.append(node.lineno)
    return out


def _catches_value_error(node: ast.Try) -> bool:
    return any(
        h.type is None
        or (isinstance(h.type, ast.Name) and h.type.id in ("ValueError", "Exception", "BaseException"))
        or (isinstance(h.type, ast.Tuple) and any(
            isinstance(e, ast.Name) and e.id in ("ValueError", "Exception", "BaseException")
            for e in h.type.elts
        ))
        for h in node.handlers
    )


def _handler_node(src: str, func_name: str) -> ast.AsyncFunctionDef:
    for fn in ast.walk(ast.parse(src)):
        if isinstance(fn, ast.AsyncFunctionDef) and fn.name == func_name:
            return fn
    raise AssertionError(f"{func_name!r} is not in the file — the extractor looked at the wrong thing")


def all_parse_lines(src: str, func_name: str) -> list[int]:
    """Every `await request.json()` in the handler, guarded or not."""
    return sorted(_parses_in(_handler_node(src, func_name)))


def guarded_parse_lines(src: str, func_name: str) -> list[int]:
    """Line numbers of `await request.json()` calls that sit inside a ValueError-catching try."""
    fn = _handler_node(src, func_name)
    out: list[int] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Try) or not _catches_value_error(node):
            continue
        for stmt in node.body:
            for sub in ast.walk(stmt):
                if (isinstance(sub, ast.Await)
                        and isinstance(sub.value, ast.Call)
                        and getattr(sub.value.func, "attr", "") == "json"):
                    out.append(sub.lineno)
    return sorted(out)


# --------------------------------------------------------------------------
# The order — the invariant this file broke
# --------------------------------------------------------------------------


def test_the_signed_path_verifies_before_it_parses():
    """Defect 2, in its narrowest form: nothing parses the body before the HMAC check.

    Scoped to the signed branch, which is the only one where a signature exists to
    check. The unsigned branch has no headers to verify, so it answers the handshake
    and refuses everything else — asserted separately below.
    """
    signed = signed_branch(events_handler())

    verify = offset_of(
        signed, VERIFY_CALL,
        "the signature check is gone from the signed path — the body is read with nothing "
        "establishing it came from Slack",
    )
    parse = offset_of(signed, PARSE, "the parse is gone from the signed path")
    assert verify < parse, (
        "the signature must be verified BEFORE the body is parsed. Every statement between the "
        "top of the signed branch and this check runs on input no one has authenticated yet."
    )


def test_the_signed_path_answers_the_handshake_only_after_verification():
    """Defect 2 proper: the branch that ANSWERS the caller must come after the check.

    A guard that exists but sits below the early `return` is not a guard. This is the
    assertion that would have caught the defect, because it does not ask whether a
    check exists — it asks where it sits relative to the branch that responds.
    """
    signed = signed_branch(events_handler())

    verify = offset_of(signed, VERIFY_CALL, "the signature check is gone from the signed path")
    answer = offset_of(
        signed, CHALLENGE_RETURN,
        "the url_verification early return is gone from the signed path — this test can no "
        "longer see the branch it was written for",
    )
    assert verify < answer, (
        "on the signed path the url_verification branch returns the caller's own challenge "
        "BEFORE the signature is checked"
    )


def test_the_unsigned_path_refuses_everything_that_is_not_the_handshake():
    """The restructure, measured: the echo is reachable ONLY for `url_verification`.

    The unsigned branch exists so an unsigned handshake cannot 401 the install. That
    is only safe if the branch answers NOTHING ELSE — so the challenge return must
    come before the refusal, and no other exit may sit beside it.
    """
    unsigned = unsigned_branch(events_handler())

    answer = offset_of(
        unsigned, CHALLENGE_RETURN,
        "the unsigned branch no longer answers the handshake — Slack's install path is broken",
    )
    refuse = offset_of(unsigned, REFUSE, "the unsigned branch no longer refuses non-handshakes")
    assert answer < refuse, (
        "the unsigned branch must echo the challenge and then refuse everything else; if the "
        "refusal sits above the echo, no unsigned request is answered at all"
    )

    code = code_only(unsigned)
    assert "logger.info" not in code, (
        "the unsigned branch logs an event, so it is acting on an unverified body rather than "
        "only answering the handshake"
    )
    assert code.count("return") == 1, (
        f"the unsigned branch has {code.count('return')} return statements; it must have exactly "
        "one — the challenge — so that no other path can answer an unsigned caller"
    )


def test_every_parse_in_the_handler_is_guarded():
    """Defect 1, measured on the file's own `try` structure rather than read off it.

    There are now TWO parse sites, one per branch, so the guard must cover BOTH. The
    assertion is set-equality rather than a non-empty check: a `try` added around one
    parse and forgotten around the other would leave the unguarded one a bare 500.
    """
    src = source()
    guarded = guarded_parse_lines(src, "handle_slack_events")
    every = all_parse_lines(src, "handle_slack_events")

    assert every, (
        "no `await request.json()` was found in handle_slack_events at all — this test is "
        "looking at the wrong function"
    )
    assert len(every) == 2, (
        f"{len(every)} parse sites found (lines {every}); the handler is expected to have one "
        "per branch, so this test is measuring a shape it was not written for"
    )
    assert guarded == every, (
        f"unguarded parse(s) at line(s) {sorted(set(every) - set(guarded))}: a malformed body "
        "raises out of the handler and Starlette answers its bare 500"
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
    # Compare COUNTS, not line numbers: the parse sits on a different line in each fixture,
    # so comparing the values would fail on a difference that is not the one under test.
    assert len(all_parse_lines(inside, "h")) == len(all_parse_lines(outside, "h")) == 1, (
        "the unguarded counter does not see the parse in both fixtures, so the set-equality in "
        "the test above cannot distinguish them — it would pass because it found nothing at all"
    )


def test_the_offset_instrument_reads_code_and_not_prose():
    """Non-vacuity for `code_only`, pinned because it already failed once in this file.

    The first version of `offset_of` indexed raw handler text, and a comment wrote
    `body = await request.json()` while describing the order that used to ship. The
    check therefore resolved to the COMMENT and reported the pre-fix order — the test
    failed for a reason opposite to the code's real state. That is the defect this card
    is about, one level up, and it is measured here rather than asserted about.
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


def test_the_branch_split_is_exact():
    """Non-vacuity for the branch extractor, which every ordering test above depends on.

    A marker that occurs twice would make `signed_branch` and `unsigned_branch` measure
    the same text, and every `verify < parse` assertion in this file would be comparing
    an offset against itself while still passing.
    """
    handler = events_handler()
    signed = signed_branch(handler)
    unsigned = unsigned_branch(handler)

    assert SIGNED_OPEN not in unsigned, "the unsigned section still contains the signed opener"
    assert UNSIGNED_OPEN not in signed, "the signed section runs past the unsigned opener"
    assert len(signed) > 100 and len(unsigned) > 100, (
        f"the split produced {len(signed)} and {len(unsigned)} characters; one half is trivial, "
        "so the ordering tests are measuring almost nothing"
    )
    assert code_only(unsigned).count(VERIFY_CALL) == 0, (
        "the unsigned branch calls the verifier; that branch exists precisely because there are "
        "no signature headers to verify, so this means the split put the signed path in both halves"
    )


def test_the_body_shape_is_checked_before_the_first_deref():
    """`isinstance(body, dict)` guards the `body.get` immediately below it.

    A signed body that is not an object - `[1,2,3]` - would otherwise raise
    AttributeError at the handler's top level, where nothing catches it.
    """
    signed = signed_branch(events_handler())

    parse = offset_of(signed, PARSE, "the parse is gone from the signed path")
    guard = offset_of(
        signed, SHAPE_GUARD,
        "no `isinstance(body, dict)` guard — the body is dereferenced as a mapping with nothing "
        "establishing that it is one",
    )
    deref = offset_of(signed, 'body.get("type")', "the `body.get(\"type\")` deref is gone")
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
# The mechanism, measured on a stand-in that carries BOTH shapes
# --------------------------------------------------------------------------

SIGNED_HEADERS = {
    "Content-Type": "application/json",
    "X-Slack-Request-Timestamp": "1234567890",
    "X-Slack-Signature": "v0=deadbeef",
}
PLAIN_HEADERS = {"Content-Type": "application/json"}

CHALLENGE = b'{"type":"url_verification","challenge":"probe"}'
REAL_EVENT = b'{"type":"event_callback","event":{"type":"app_mention"}}'
MALFORMED = b"{not json at all"


def _build(shape: str, sig_ok: bool = True) -> TestClient:
    """A stand-in carrying the pre-fix shape or the restructured one.

    `verify` is a boolean STUB, not HMAC, so what this measures is the SHAPE of the two
    orders — which request reaches which branch — and never whether Slack signs the
    handshake. That claim is not testable here, and the handler's own comment says so.

    `verify` is a closure rather than a module-level helper on purpose: a two-argument
    helper called at three-argument sites is a failure this suite has already had once.
    """
    app = FastAPI()

    def verify(body, timestamp, signature):
        return sig_ok

    @app.post("/events")
    async def handle(request: Request):
        body_bytes = await request.body()
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        if shape == "before":
            body = await request.json()
            if body.get("type") == "url_verification":
                return JSONResponse({"challenge": body.get("challenge")})
            if not verify(body_bytes, timestamp, signature):
                raise HTTPException(status_code=401, detail="Invalid Slack signature")
            return JSONResponse({"ok": True})

        if signature and timestamp:
            if not verify(body_bytes, timestamp, signature):
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

        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(status_code=400, detail="Malformed JSON body")
        if isinstance(body, dict) and body.get("type") == "url_verification":
            return JSONResponse({"challenge": body.get("challenge")})
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    return TestClient(app, raise_server_exceptions=False)


def _post(shape: str, content: bytes, headers: dict, sig_ok: bool = True):
    return _build(shape, sig_ok).post("/events", content=content, headers=headers)


def test_the_old_shape_still_reproduces_both_defects():
    """The control. If this stops failing the way it did, the stand-in has gone stale.

    A malformed body under the old shape is a bare 500 — so `raise_server_exceptions`
    is off and the 500 is OBSERVED rather than propagated.
    """
    echoed = _post("before", CHALLENGE, PLAIN_HEADERS)
    assert echoed.status_code == 200, (
        f"the old shape answered {echoed.status_code}, not 200 — this stand-in no longer "
        "reproduces the defect it was built for"
    )
    assert b"probe" in echoed.content, "the 200 did not echo the caller's challenge — wrong probe"

    broken = _post("before", MALFORMED, PLAIN_HEADERS)
    assert broken.status_code == 500, (
        f"the old shape answered {broken.status_code} for a malformed body, not the bare 500 "
        "Starlette gives an unguarded Request.json()"
    )


def test_a_signed_url_verification_still_works():
    """The behaviour risk of this fix, measured rather than assumed.

    Requiring a signature must NOT break a SIGNED handshake. If it did, the fix would
    trade an anonymous echo for a Slack app that never installs. What this measures is
    the branch, not Slack: the verifier here is a stub answering YES.
    """
    ok = _post("after", CHALLENGE, SIGNED_HEADERS)
    assert ok.status_code == 200, (
        f"a signed url_verification gets {ok.status_code} — the fix has broken the handshake "
        "for a caller that does sign"
    )
    assert ok.json() == {"challenge": "probe"}, "the challenge was not echoed back"


def test_an_unsigned_url_verification_is_also_answered():
    """The restructure's whole point: the install path cannot 401 on missing headers.

    Whether Slack signs this handshake is not established, so the handler answers it
    either way. This is the assertion that would fail if the restructure were reverted
    to verify-first-always.
    """
    r = _post("after", CHALLENGE, PLAIN_HEADERS)
    assert r.status_code == 200, (
        f"an UNSIGNED url_verification gets {r.status_code}; if Slack does not sign the "
        "handshake, this is the app's install path failing permanently"
    )
    assert r.json() == {"challenge": "probe"}


def test_the_unsigned_branch_answers_nothing_but_the_handshake():
    """The cost of the branch above, bounded: it must not become a general bypass."""
    real = _post("after", REAL_EVENT, PLAIN_HEADERS)
    assert real.status_code == 401, (
        f"an unsigned real event gets {real.status_code}; the unsigned branch has become a way "
        "to deliver events without a signature"
    )

    junk = b'{"type":"something_else"}'
    other = _post("after", junk, PLAIN_HEADERS)
    assert other.status_code == 401, (
        f"an unsigned body of an unrecognised type gets {other.status_code}, not 401"
    )


def test_a_signed_event_that_fails_verification_is_refused():
    r = _post("after", REAL_EVENT, SIGNED_HEADERS, sig_ok=False)
    assert r.status_code == 401, f"a signed event with a bad signature gets {r.status_code}, not 401"


def test_a_signed_real_event_is_answered():
    r = _post("after", REAL_EVENT, SIGNED_HEADERS)
    assert r.status_code == 200, f"a signed real event gets {r.status_code}, not 200"
    assert r.json() == {"ok": True}


def test_a_malformed_body_is_a_400_in_both_branches():
    """Non-vacuity for the parse guard: it must be REACHABLE, or it is decoration.

    Both branches must close this, because a 500 is the symptom the card opened with.
    """
    signed = _post("after", MALFORMED, SIGNED_HEADERS)
    assert signed.status_code == 400, (
        f"a SIGNED malformed body answered {signed.status_code}; unguarded it was a bare 500"
    )
    unsigned = _post("after", MALFORMED, PLAIN_HEADERS)
    assert unsigned.status_code == 400, (
        f"an UNSIGNED malformed body answered {unsigned.status_code}; the unsigned branch's parse "
        "is unguarded, or the refusal below the echo is being reached by a raise instead"
    )


def test_a_signed_body_that_is_not_an_object_is_a_400():
    r = _post("after", b"[1,2,3]", SIGNED_HEADERS)
    assert r.status_code == 400, (
        f"a signed JSON array body answered {r.status_code}; `body.get` on a list is an "
        "AttributeError nothing catches"
    )
