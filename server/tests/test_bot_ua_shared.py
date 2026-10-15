"""The generic bot User-Agent heuristic lives in ONE place, and may only widen.

Why this file exists. `server/middleware/geoRestrict.ts` and
`server/middleware/aiAgentLog.ts` each carried their own copy of the same
heuristic, and **they had already diverged** — geoRestrict's was the wider one by
six tokens (`monitor`, `preview`, `validator`, `feedparser`, `java/`, `^node$`).
The failure that caused was one-way and silent: a client matching one of those
six was treated as a bot by the geo gate (and therefore waved *through* it) while
being invisible to the AI-agent metric. The metric undercounted exactly the
traffic the older middleware let past, and nothing in either file said so.

The merged list is geoRestrict's, and the direction matters:

  * `geoRestrict.ts` uses a match to BYPASS the gate. Narrowing the list makes
    the gate STRICTER, which can start blocking real people — the direction whose
    bug reports arrive days later from somewhere else (see the AdsBot comment in
    that file: two days of disapproved ads).
  * `aiAgentLog.ts` uses a match to CLASSIFY as `other_bot`. Narrowing it only
    loses log lines.

So widening is safe for both callers and narrowing is safe for only one. This
file pins both facts: that the literal is not duplicated again, and that it has
not been narrowed. A source-text check alone would not be enough — a regex can be
"present" and still not match — so the pattern is also extracted and *run*
against the six tokens that were the whole point of the merge.

Run: uv run pytest server/tests/test_bot_ua_shared.py
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIDDLEWARE = REPO_ROOT / "server" / "middleware"

SHARED = MIDDLEWARE / "botUserAgent.ts"
GEO = MIDDLEWARE / "geoRestrict.ts"
AI_LOG = MIDDLEWARE / "aiAgentLog.ts"

# geoRestrict.ts's literal, verbatim from `git show HEAD:server/middleware/geoRestrict.ts`
# at the commit before the merge (it was byte-identical to the shared copy this
# replaced — verified by diffing the two strings, not by reading them).
#
# Pinned in full rather than as a token set, so that a future edit has to be a
# deliberate edit to this test as well. Any of these tokens disappearing is a
# narrowing, and a narrowing makes the geo gate stricter.
HISTORICAL_GEO_LIST = (
    r"bot\b|\bbot|crawler|spider|crawl|fetcher|scraper|monitor|preview|validator"
    r"|feedparser|headlesschrome|python-requests|curl\/|wget\/|axios\/"
    r"|go-http-client|okhttp|java\/|libwww|undici|node-fetch|^node$"
)

# The six tokens only geoRestrict.ts had. Each one is a client that the geo gate
# already treats as a bot; before the merge, aiAgentLog.ts could not see any of
# them. Named individually so a failure says which capability was lost.
THE_SIX = ["monitor", "preview", "validator", "feedparser", "java/", "^node$"]


def _read(path: Path) -> str:
    assert path.is_file(), f"{path} is missing — the middleware moved?"
    return path.read_text(encoding="utf-8")


def _shared_pattern_source() -> str:
    """The regex *source* exactly as written in botUserAgent.ts.

    Matches `export const GENERIC_BOT_UA =\n  /(...)/i;` and returns the token
    alternation *inside* the wrapping group, which is what HISTORICAL_GEO_LIST
    holds. Asserted against the historical literal so this test cannot silently
    pass on an empty or truncated extraction.
    """
    src = _read(SHARED)
    m = re.search(r"export const GENERIC_BOT_UA\s*=\s*\n\s*/\((.*)\)/i;", src, re.S)
    assert m, "GENERIC_BOT_UA is not exported from botUserAgent.ts in the expected form"
    return m.group(1)


def test_the_literal_is_exported_from_the_shared_module():
    pattern = _shared_pattern_source()
    assert pattern == HISTORICAL_GEO_LIST, (
        "the shared list changed. If it WIDENED, update HISTORICAL_GEO_LIST here to "
        "match and say so in the commit. If it NARROWED, stop: narrowing makes "
        "geoRestrict.ts stricter and can turn away real people."
    )


def test_neither_middleware_declares_its_own_copy():
    """The duplication is the bug. Two literals drift; one cannot."""
    for path in (GEO, AI_LOG):
        src = _read(path)
        assert "const GENERIC_BOT_UA" not in src, (
            f"{path.name} declares its own GENERIC_BOT_UA again — that is the "
            f"duplication this test exists to prevent. Import it from botUserAgent.ts."
        )
        assert 'from "./botUserAgent"' in src, (
            f"{path.name} does not import from ./botUserAgent — it must use the shared list"
        )


@pytest.mark.parametrize("token", THE_SIX)
def test_the_six_tokens_geo_restrict_relied_on_still_match(token: str):
    """Behavioural, not textual: run the real pattern against the real tokens.

    These six are what the merge was for. A UA matching one of them is a bot to
    the geo gate, so it must be a bot to the logger too.
    """
    pattern = re.compile(_shared_pattern_source(), re.I)
    # A plausible client string carrying the token, not the bare token: `^node$`
    # is anchored, so the bare string is the only thing it can match, and a real
    # UA is what the middleware actually sees.
    samples = {
        "monitor": "SiteMonitor/2.1 (+http://example.com/monitor)",
        "preview": "Mozilla/5.0 (compatible; SomeLinkPreview/1.0)",
        "validator": "W3C_Validator/1.3",
        "feedparser": "FeedParser/6.0 +https://pypi.org/project/feedparser/",
        "java/": "Java/1.8.0_292",
        "^node$": "node",
    }
    assert pattern.search(samples[token]), (
        f"the shared pattern no longer matches {samples[token]!r} (token {token!r}). "
        f"geoRestrict.ts still treats that client as a bot, so aiAgentLog.ts has "
        f"gone back to being unable to see it."
    )


def test_a_human_browser_still_matches_nothing():
    """The counterweight. Widening the list is safe only while it stays off real
    people: a false positive in geoRestrict.ts waves a browser through a gate it
    should have hit, and in aiAgentLog.ts miscounts a real pageview as a bot."""
    pattern = re.compile(_shared_pattern_source(), re.I)
    browsers = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    ]
    for ua in browsers:
        assert not pattern.search(ua), f"a real browser matches the bot heuristic: {ua!r}"
