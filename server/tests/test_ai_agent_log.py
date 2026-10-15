"""The Python half of `server/tests/ai-agent-log.test.ts` — crawler classification.

Why this file exists at all, and why it is not a copy of the TypeScript one. The
TypeScript file is the better guard: it boots a real Express app twice, sends
real requests, and asserts on the finished status and the emitted line, so it
sees behaviour. **It also does not run.** `pr-checks.yml` names each TypeScript
test file by hand as its own step, that workflow is on the hold list, and
`ai-agent-log.test.ts` is named nowhere — it is the seventh such file. The
pytest job (`uv sync` then `uv run pytest`) installs no npm packages, so it
could not execute the middleware even if a step existed. The guard that protects
this middleware on a pull request is therefore this file, or nothing.

What it can honestly cover, given Python never runs the middleware: the source
invariants the TypeScript file's claims rest on. The classification rule is
**re-derived** here rather than restated — the table is parsed out of the
TypeScript, the matching primitive is read out of `classifyUserAgent`, and this
file then applies that rule to every entry. A list of expected answers copied
into Python would be the same hand-maintained second copy this middleware exists
to remove, one level up.

The outer edge, stated rather than left implicit: this reads source text, so it
cannot see what the source does at runtime. Whether a real request is logged,
with which status, is the TypeScript file's half, and it runs when somebody runs
it by hand. This file is the part that runs on every pull request.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MIDDLEWARE = REPO_ROOT / "server/middleware/aiAgentLog.ts"
INDEX = REPO_ROOT / "server/index.ts"

# The four classes the type declares. `other_bot` is the backstop, not a table
# class — a table entry claiming it would be a crawler that a *known* token
# failed to name, which is the case the backstop exists for.
BACKSTOP_CLASS = "other_bot"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_comments(ts: str) -> str:
    """Comments removed before any structural read.

    Not tidiness, and this file needs it more than the citation twin does. The
    module docstring above `aiAgentLog` discusses `req.path` and `originalUrl`
    *in prose*, and `classifyUserAgent`'s own comment discusses the bot tokens.
    A structural check that reads the raw file finds `req.path` inside a comment
    that is explaining why `req.path` is correct, and finds `applebot-extended`
    in prose about the ordering. The obvious repair for a check that reddens on
    a comment is to weaken the check.
    """
    ts = re.sub(r"/\*[\s\S]*?\*/", "", ts)
    return re.sub(r"(?m)^[ \t]*//.*$", "", ts)


def braced_block(src: str, marker: str) -> str:
    """The `{ … }` body of the declaration that starts at `marker`, brace-matched.

    `marker` is the text *before* the opening brace — a signature or a call head.
    The body brace is found by scanning forward for the first `{` at paren depth
    zero, which is what makes this work on `export function aiAgentLog(opts:
    AiAgentLogOptions = {}) {`: the `{}` in the default parameter is inside
    parentheses and is skipped, so the extractor does not open the body a
    parameter early and read a cut-off block.

    A marker that already ends at its own `{` — an arrow callback, a `for`, an
    `if` — opens the body directly. That branch is not decoration: in
    `res.on("finish", () => {` the `on(` is still open when the body brace
    arrives, so the paren-depth rule alone would walk straight past it.

    Used to scope an assertion to ONE function or ONE callback. A file-wide
    search for `req.path` would match the doc comment, the body, and any future
    helper alike; scoping is what lets this file say *where* a thing is read.
    """
    i = src.index(marker) + len(marker)
    if not marker.rstrip().endswith("{"):
        parens = marker.count("(") - marker.count(")")
        while i < len(src):
            ch = src[i]
            if ch == "(":
                parens += 1
            elif ch == ")":
                parens -= 1
            elif ch == "{" and parens == 0:
                break
            i += 1
        else:
            raise AssertionError(f"no body brace after {marker!r}")
        start = i + 1
    else:
        start = i

    depth, i = 1, start
    while i < len(src) and depth:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
        i += 1
    assert depth == 0, f"unbalanced braces after {marker!r} — the extractor read a cut-off block"
    return src[start : i - 1]


def known_agents() -> list[tuple[str, str, str]]:
    """`KNOWN_AGENTS` parsed out of the TypeScript: (token, agent, class)."""
    src = strip_comments(read(MIDDLEWARE))
    start = src.index("export const KNOWN_AGENTS")
    end = src.index("];", start)
    table = src[start:end]
    rows = re.findall(
        r'\{\s*token:\s*"([^"]+)",\s*agent:\s*"([^"]+)",\s*class:\s*"([^"]+)"\s*\}', table
    )
    assert rows, "KNOWN_AGENTS no longer parses as { token, agent, class } records"
    return rows


def classify_like_the_code(ua: str) -> tuple[str, str] | None:
    """The code's rule, applied in Python.

    First match wins over the table in declaration order, matched with
    `includes` against a lowercased User-Agent. If the TypeScript ever stops
    being first-match-wins — if it grows a longest-token preference, say — the
    assertions in `test_the_matching_rule_is_still_first_match_wins_in_order`
    go red rather than this helper quietly testing a rule the code does not use.
    """
    s = ua.lower()
    if not s:
        return None
    for token, agent, cls in known_agents():
        if token in s:
            return agent, cls
    return None


def test_the_matching_rule_is_still_first_match_wins_in_order():
    """The rule this file re-derives, asserted against the code that implements it.

    Everything below applies `classify_like_the_code`. That is only meaningful
    while it is the rule the middleware actually uses, so the rule is pinned
    first: a lowercased subject, `includes` as the primitive, the table iterated
    in declaration order, and the first hit returned.
    """
    src = strip_comments(read(MIDDLEWARE))
    fn = braced_block(src, "export function classifyUserAgent(")

    assert 'String(ua || "").toLowerCase()' in fn, (
        "the User-Agent is no longer lowercased before matching; every token in the table is "
        "lowercase, so this would stop matching real crawlers whose UA casing differs"
    )
    assert "s.includes(entry.token)" in fn, "the matching primitive is no longer a substring test"
    assert "for (const entry of KNOWN_AGENTS)" in fn, (
        "the table is no longer iterated in declaration order, so the ordering assertions below "
        "are testing a rule the code does not use"
    )
    loop = braced_block(fn, "for (const entry of KNOWN_AGENTS)")
    assert "return {" in loop, "the first match no longer returns — the table is no longer first-win"

    # An absent header is silent, and it is the caller's silence that matters:
    # null means "not classified", which is not the same as "not a bot".
    assert 'if (s.length === 0) return null;' in fn, (
        "an empty User-Agent no longer short-circuits, so it falls through to the backstop"
    )


def test_no_table_entry_can_be_shadowed_by_an_earlier_one():
    """First-match-wins tables rot quietly.

    Insert a broad token above a narrow one and the narrow entry becomes dead
    config that still reads as live. This is the whole reason the table is
    re-derived instead of restated: each entry's own token is fed through the
    code's rule, and the only entry that can match is the one being asked about
    — unless something earlier swallows it.
    """
    dead = []
    for token, agent, _cls in known_agents():
        got = classify_like_the_code(token)
        if got is None or got[0] != agent:
            dead.append(f"{token} -> {got[0] if got else 'null'}")
    assert dead == [], "these entries can never match:\n  " + "\n  ".join(dead)


def test_applebot_extended_is_not_counted_as_applebot():
    """The one ordering dependency in the table, named because it is load-bearing.

    `applebot-extended` contains `applebot`, so a table that lists the short
    token first reports Google's AI-training crawler as Apple's plain search
    crawl. That is the same conflation as folding crawlers into `Direct`, which
    is the failure this middleware was built to undo.
    """
    extended = classify_like_the_code(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Applebot-Extended/0.1"
    )
    assert extended == ("Applebot-Extended", "ai_agent"), f"Applebot-Extended classified as {extended}"

    # And the plain one still resolves, or the fix would only have moved the bug.
    plain = classify_like_the_code(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Applebot/0.1"
    )
    assert plain == ("Applebot", "search_crawler"), f"Applebot classified as {plain}"


def test_every_entry_declares_a_class_the_type_allows_and_the_backstop_owns():
    """The class vocabulary is closed, and `other_bot` is not one of the table's.

    `UaClass` is a union of four strings. A typo in a table entry (`search_bot`,
    say) would typecheck nowhere but read fine in a diff, and the metric would
    carry a class nothing downstream knows. `other_bot` is reserved: an entry
    that declared it would be a *known* token claiming to be unrecognised, which
    silently disables the backstop's purpose for that agent.
    """
    src = strip_comments(read(MIDDLEWARE))
    union = re.search(r'export type UaClass\s*=\s*([^;]+);', src)
    assert union, "UaClass is no longer a declared union"
    classes = set(re.findall(r'"([^"]+)"', union.group(1)))
    assert classes == {"ai_agent", "search_crawler", "ads_crawler", BACKSTOP_CLASS}, (
        f"the class union changed: {sorted(classes)}"
    )

    declared = {cls for _t, _a, cls in known_agents()}
    assert BACKSTOP_CLASS not in declared, (
        f"a table entry declares the backstop class {BACKSTOP_CLASS!r}; the backstop is for "
        f"agents the table does not know"
    )
    assert declared <= classes, f"table entries use a class outside the union: {sorted(declared - classes)}"


def test_the_backstop_carries_the_user_agent_and_the_table_does_not():
    """"Unclassified" must not be indistinguishable from "did not visit".

    The backstop exists so the next ChatGPT-User shows up as *something*. For
    that class the User-Agent **is** the finding, so it is attached — capped,
    because it is attacker-controlled text of unbounded length. A table hit
    needs no UA: the token already names the agent.
    """
    src = strip_comments(read(MIDDLEWARE))

    limit = re.search(r"const UA_ECHO_LIMIT\s*=\s*(\d+);", src)
    assert limit, "UA_ECHO_LIMIT is gone"
    assert int(limit.group(1)) > 0, "UA_ECHO_LIMIT is not a positive cap"

    fn = braced_block(src, "export function classifyUserAgent(")
    assert "ua: s.slice(0, UA_ECHO_LIMIT)" in fn, (
        "the backstop no longer caps the echoed User-Agent, so an unbounded header reaches the log"
    )

    backstop = braced_block(fn, "if (GENERIC_BOT_UA.test(s))")
    assert f'class: "{BACKSTOP_CLASS}"' in backstop, "the backstop no longer declares its own class"

    # The table's return carries no UA — a table hit is named by its token.
    loop = braced_block(fn, "for (const entry of KNOWN_AGENTS)")
    assert "ua:" not in loop, "a table hit now echoes the raw User-Agent, which the token already names"


def test_the_middleware_is_actually_mounted():
    """A perfect classifier that is never registered logs nothing.

    This is not hypothetical here: the middleware is a new file, and the only
    thing that makes it production behaviour is one line in the gateway. The TS
    test file boots its own app and so cannot see the real registration at all.
    """
    src = strip_comments(read(INDEX))
    assert 'from "./middleware/aiAgentLog"' in src, "server/index.ts no longer imports the middleware"
    assert re.search(r"app\.use\(\s*aiAgentLog\(", src), (
        "server/index.ts no longer mounts aiAgentLog, so nothing is classified in production"
    )


def test_the_logged_path_is_read_on_entry_and_carries_no_query_string():
    """The bug this pins was found by running the real server, not by the tests.

    Express rewrites `req.url` while dispatching a wildcard layer: once
    `app.use("*", …)` matches, `req.path` reads `"/"` and only `req.originalUrl`
    keeps the real path. In production nearly every page is answered by exactly
    such a layer — the SPA catch-all in `static.ts` — so a `req.path` read
    *inside* the `finish` callback logged `path:"/"` for every crawler hit: the
    agent right, the page wrong, and wrong in a way that looks fine.

    So two things are asserted, and they pull in opposite directions on purpose:
    the path is read OUTSIDE the finish callback, and what is recorded is
    `path` rather than `originalUrl` — because the query string is where
    `/auth?email=…` style values live and no metric here needs one.
    """
    src = strip_comments(read(MIDDLEWARE))
    fn = braced_block(src, "export function aiAgentLog(")

    assert "const path = req.path;" in fn, "the logged path is no longer read from req.path"

    finish = braced_block(fn, 'res.on("finish", () => {')
    assert "req.path" not in finish and "req.originalUrl" not in finish, (
        "the path is read inside the finish callback again — a wildcard route answering the "
        "request makes that read `\"/\"` while looking correct"
    )
    assert "originalUrl" not in fn, (
        "the middleware reads originalUrl, which still carries the query string"
    )


def test_the_middleware_touches_no_response_and_reads_no_header_but_two():
    """"Measurement only" is a claim about behaviour, and this is the source half of it.

    The TypeScript file proves the response is byte-identical by booting the app
    twice. That is the real proof and it runs on no pull request. This is the
    weaker, always-on half: the middleware never calls a method that could
    change a response, and the only request headers it reads are the User-Agent
    (public by definition — it is the bot announcing itself) and the request id
    (the server's own correlation header, not the client's identity). Not
    reading a header is the only way to be sure nothing from it is logged.
    """
    src = strip_comments(read(MIDDLEWARE))
    fn = braced_block(src, "export function aiAgentLog(")

    # Call syntax, not a substring: `res.status` also matches the *read*
    # `status: res.statusCode`, which is exactly what this middleware must do.
    # Matching the bare name would have made this assertion red on correct code
    # and pushed the next person to weaken it.
    for forbidden in ("res.setHeader", "res.status", "res.send", "res.write", "res.redirect", "res.end"):
        assert f"{forbidden}(" not in fn, (
            f"the middleware calls {forbidden}() — it is supposed to be measurement only"
        )

    headers = set(re.findall(r'req\.headers\[\s*"([^"]+)"\s*\]', fn))
    assert headers <= {"user-agent", "x-request-id"}, (
        f"the middleware reads request headers beyond the two it documents: {sorted(headers)}"
    )

    # One JSON object per line. A multi-line payload is unparseable by every log
    # tool that splits on newline, which is all of them. Counted on the emit
    # rather than on `write(`, because the default sink assigns to `write` too —
    # counting bare `write(` would be red on correct code.
    emits = re.findall(r"write\(JSON\.stringify\(line\)\)", fn)
    assert len(emits) == 1, f"the middleware emits {len(emits)} lines per finished response; one request is one line"
    assert "JSON.stringify(line)" in fn, "the emitted line is no longer a single JSON object"
    assert "process.stdout.write(line + \"\\n\")" in src, (
        "the default sink no longer terminates the line; Railway splits log lines on newline, so a "
        "missing terminator merges consecutive records into one unparseable record"
    )


def test_the_liveness_exemption_covers_the_backstop_only():
    """The exemption is scoped, and widening it would silence real crawlers.

    `Dockerfile:64` curls `/health` every 30s. Un-exempted that is one
    `other_bot` line every 30 seconds — 2,880 a day of our own health check
    burying the traffic this log exists to show. But the exemption must apply to
    the backstop alone: a *recognised* crawler requesting `/health` is a real
    finding, and a guard that swallowed it would be invisible.
    """
    src = strip_comments(read(MIDDLEWARE))
    fn = braced_block(src, "export function aiAgentLog(")

    assert "const LIVENESS_PATHS = new Set([\"/health\", \"/healthz\"]);" in src, (
        "the liveness path set changed shape; the exemption it drives is the reason it exists"
    )

    match = re.search(r"if \(([^)]*LIVENESS_PATHS[^)]*)\)", fn)
    assert match, "the liveness exemption is gone entirely, so the probe floods the log"
    guard = match.group(1)
    assert BACKSTOP_CLASS in guard, (
        "the liveness exemption no longer checks the class, so a recognised crawler on /health "
        "is silently dropped"
    )
