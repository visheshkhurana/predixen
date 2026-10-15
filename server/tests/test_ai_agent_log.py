r"""The Python half of `server/tests/ai-agent-log.test.ts` — crawler classification.

Why this file exists at all, and why it is not a copy of the TypeScript one. The
TypeScript file is the better guard: it boots a real Express app twice, sends
real requests, and asserts on the finished status and the emitted line, so it
sees behaviour. **It also does not run.** `pr-checks.yml` names each TypeScript
test file by hand as its own step, that workflow is on the hold list, and
`ai-agent-log.test.ts` is named nowhere: it is one of five `.test.ts` files in
`server/tests` that no step runs — 32 exist there and 27 are named. Counted from
the disk rather than remembered (`find server/tests -name '*.test.ts' | wc -l`
against `grep -oE 'server/tests/[A-Za-z0-9._-]+\.test\.ts' .github/workflows/
pr-checks.yml | sort -u | wc -l`): an earlier version of this sentence said "the
seventh such file", and that number was never measured. Two more files under
`client/src/lib/__tests__/` are in the same position, and no job installs a
client runner at all. The
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

# The only two members of `res` the middleware may mention, and why each one is
# inert: `on` registers the finish listener that reports the status, and
# `statusCode` is the read that gives it something to report. Nothing else on
# the response object is reachable without the possibility of changing it, which
# is why this is a closed set and not a list of forbidden names.
ALLOWED_RES_MEMBERS = {"on", "statusCode"}


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


def test_the_logged_request_id_is_capped_like_the_user_agent():
    """The line's other stranger-controlled field - the half that was open.

    `x-request-id` arrives from the client and is written into the log line
    verbatim. The User-Agent beside it was capped and the id was not, so the
    module docstring's claim to cover "the source invariants the TypeScript
    file's claims rest on" was true of one field and not the other, and a single
    unauthenticated request carrying a 5,000-character header inflated one line
    to kilobytes. Sentinel measured that on #116 and this is its guard.

    Both halves are asserted, because either one alone leaves the hole open: the
    read has to cap, and the line has to be written from the capped local rather
    than from the raw header.
    """
    src = strip_comments(read(MIDDLEWARE))

    # `export ` is optional here on purpose: this test is about the log-side cap
    # existing and being positive, not about where the constant is declared. The
    # export itself is asserted by
    # test_the_id_the_response_carries_is_the_id_the_log_records, which is the
    # test that owns the one-owner question.
    limit = re.search(r"(?:export\s+)?const ID_ECHO_LIMIT\s*=\s*(\d+);", src)
    assert limit, "ID_ECHO_LIMIT is gone"
    assert int(limit.group(1)) > 0, "ID_ECHO_LIMIT is not a positive cap"

    fn = braced_block(src, "export function aiAgentLog(")
    assert 'req.headers["x-request-id"].slice(0, ID_ECHO_LIMIT)' in fn, (
        "the request id is no longer capped, so an unbounded and stranger-controlled header "
        "reaches the log line"
    )

    finish = braced_block(fn, 'res.on("finish", () => {')
    assert "request_id: requestId," in finish, (
        "the log line no longer writes the capped local, so the raw header can reach it"
    )


def test_the_middleware_is_actually_mounted():
    """A perfect classifier that is never registered logs nothing — and one
    registered in the wrong place logs the wrong page.

    This is not hypothetical here: the middleware is a new file, and the only
    thing that makes it production behaviour is one line in the gateway. The TS
    test file boots its own app and so cannot see the real registration at all.

    Presence is not the property that matters, though, and a search for
    `app.use(aiAgentLog(` cannot see position. Express runs middleware in
    registration order, so two positions are load-bearing:

      * **after the request-id middleware.** `aiAgentLog` reads the id back out
        of `req.headers["x-request-id"]`, so registered above that line every
        log line carries `request_id: null` — a field that is right-looking and
        always empty. Measured on the built bundle, not inferred.
      * **before whatever answers the request.** Nearly every page is answered
        by `serveStatic`, the SPA catch-all, or vite, all registered hundreds of
        lines below. A layer below any of those never runs for the requests it
        exists to count.

    So this asserts order. Each anchor is asserted to *exist* first: a renamed
    anchor would otherwise make the comparison vacuous, which is the same
    failure as the one this test is fixing.
    """
    src = strip_comments(read(INDEX))
    assert 'from "./middleware/aiAgentLog"' in src, "server/index.ts no longer imports the middleware"

    mount = re.search(r"app\.use\(\s*aiAgentLog\(", src)
    assert mount, (
        "server/index.ts no longer mounts aiAgentLog, so nothing is classified in production"
    )

    id_mw = src.find('req.headers["x-request-id"] = requestId')
    assert id_mw != -1, (
        "the request-id middleware is gone from server/index.ts, so this test can no longer "
        "prove the logger runs after it"
    )
    assert id_mw < mount.start(), (
        "aiAgentLog is registered BEFORE the request-id middleware, so every log line carries "
        "request_id: null — the logger reads that header, and it is only populated once the "
        "middleware above it has run"
    )

    for anchor, what in (
        ("serveStatic(app)", "static file serving"),
        ('app.use("*"', "the SPA catch-all"),
        ("setupVite(", "the dev server"),
    ):
        at = src.find(anchor)
        assert at != -1, (
            f"the {what} anchor ({anchor!r}) is gone from server/index.ts, so this test can no "
            f"longer prove the logger is registered above it"
        )
        assert mount.start() < at, (
            f"aiAgentLog is registered AFTER {what} ({anchor!r}), so a request answered there "
            f"is never classified at all"
        )


def test_the_id_the_response_carries_is_the_id_the_log_records():
    """MEDIUM 1 on #118 — the cap was on the log side only, and that broke them apart.

    `server/index.ts` writes the id onto the response as `X-Request-ID`, and
    `aiAgentLog` writes it into the log line. When only the logger capped, a
    65-character or 5,000-character id produced TWO different strings and nothing
    said so: the response carried the raw value and the log carried its 64-char
    prefix. An operator holding the id from a response would grep the log for it
    and find nothing — the one thing a request id exists to prevent.

    So what is asserted is that the bound has ONE OWNER and that both sides use
    it: the constant is exported, the gateway imports it, the id is capped before
    either write, and the same local feeds the request header, the response and
    therefore the log. Asserting that two files each contain the number `64` would
    pass today and drift the moment either is edited — the same defect one level
    down, which is what this file is already about.
    """
    mw = strip_comments(read(MIDDLEWARE))
    gateway = strip_comments(read(INDEX))

    assert re.search(r"export const ID_ECHO_LIMIT\s*=\s*\d+;", mw), (
        "ID_ECHO_LIMIT is not exported, so server/index.ts cannot use the one owner of this "
        "bound and would have to keep a second copy of the number"
    )
    assert re.search(
        r'import\s*\{[^}]*\bID_ECHO_LIMIT\b[^}]*\}\s*from\s*"\./middleware/aiAgentLog"',
        gateway,
    ), "server/index.ts does not import ID_ECHO_LIMIT from the middleware that defines it"

    assign = re.search(r'req\.headers\["x-request-id"\]\s*=\s*([A-Za-z_$][\w$]*)\s*;', gateway)
    echo = re.search(r'res\.setHeader\(\s*"X-Request-ID"\s*,\s*([A-Za-z_$][\w$]*)\s*\)', gateway)
    assert assign, (
        "the request header is no longer assigned from a local, so this test cannot tell which "
        "value reaches the log"
    )
    assert echo, (
        "server/index.ts no longer writes X-Request-ID, so this test can no longer prove the "
        "response and the log carry the same value"
    )
    assert assign.group(1) == echo.group(1), (
        f"the request header carries {assign.group(1)!r} and the response carries "
        f"{echo.group(1)!r} — two values, so the log and the response can disagree"
    )

    name = assign.group(1)
    capped = re.search(
        rf"const\s+{re.escape(name)}\s*=[\s\S]{{0,200}}?\.slice\(\s*0\s*,\s*ID_ECHO_LIMIT\s*\)",
        gateway,
    )
    assert capped, (
        f"{name!r} reaches the response and the log, but it is not the capped value: the cap is "
        f"applied somewhere other than the id that is echoed, which is how the log and the "
        f"response came apart in the first place"
    )

    cap_at = gateway.find(".slice(0, ID_ECHO_LIMIT)")
    echo_at = gateway.find('res.setHeader("X-Request-ID"')
    assert cap_at < echo_at, (
        "the response header is written before the id is capped, so the response carries the raw "
        "value while the log carries its prefix"
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

    # Every `res.<name>` the function mentions, against a CLOSED set of the two
    # that cannot change a response — the same shape as the header assertion
    # below, and for the same reason.
    #
    # What this replaces named six spellings of the mutation (`res.setHeader`,
    # `res.send`, `res.write`, `res.redirect`, `res.end`, `res.status`). Six is
    # the list of ways I happened to think of, not the class: `res.writeHead`,
    # `res.flushHeaders`, `res.append` and `res.set` all pass it untouched, and
    # the last two are the ones most likely to be typed by accident. A guard
    # that catches one spelling of a mutation rather than the mutation is the
    # defect this file exists to argue against, so it is written the closed way:
    # a new call on `res` has to be added to the allowed set deliberately, or
    # this reddens.
    #
    # Reading `res.X` rather than call syntax also handles the legitimate read
    # (`res.statusCode`) without the special case the old note needed, which is
    # why that note is gone.
    res_members = set(re.findall(r"(?<![\w$.])res\.([A-Za-z_$][\w$]*)", fn))
    assert res_members <= ALLOWED_RES_MEMBERS, (
        f"the middleware touches the response beyond listening for 'finish' and reading the "
        f"status code: {sorted(res_members - ALLOWED_RES_MEMBERS)}"
    )
    # That this listens for 'finish' at all is asserted separately, by the path
    # test below — so a subset here cannot quietly lose the report.

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
