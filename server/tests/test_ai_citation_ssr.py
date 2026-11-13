"""The Python half of `server/tests/ai-citation-ssr.test.ts` — the citation block.

Why this file exists at all, and why it is not a copy of the TypeScript one. The
TypeScript file is the better guard: it calls the real `injectSEO` over every
prerendered route and it renders `Footer()` through react-test-renderer, so it
sees behaviour. **It also does not run.** `pr-checks.yml` names each TypeScript
test file by hand as its own step and that workflow is on the hold list, so
`ai-citation-ssr.test.ts` is named nowhere (`grep -c` -> 0) and the pytest job —
`uv sync` then `uv run pytest` — installs no npm packages, so it could not run
it even if a step existed. The guard that protects the block in CI is therefore
this file, or nothing.

What it can honestly cover, given Python never executes the prerender: the three
source invariants the TypeScript file's claims rest on.

  1. ONE COPY. The copy lives in `client/src/data/ai-citation.ts`, and neither
     the prerender nor the footer retypes it. This is the HAG-311 defect shape —
     a second hand-maintained list that fell two posts behind the first — applied
     to prose, where the drift is invisible because both copies still render.
  2. ONE EMIT SITE. `citationBlock` is interpolated once, inside `injectSEO`,
     inside `if (meta.bodyContent) {`. That is what makes "every prerendered page
     can be cited" a property of the code rather than a list of routes somebody
     remembered to update. It is read here by deriving the block from the source,
     not by naming routes: a route list in a test is the same defect one level up.
  3. THE ABSENCE SIDE. `Footer()` still renders `<CitableSnippet />`. Every
     prerender assertion in the tree, this file included, passes on markup a
     human never receives, so deleting that one line from the footer used to keep
     the whole suite green while every person lost the block.

The outer edge of this file, stated rather than left implicit: it reads source
text, so it cannot see what the source does at runtime — an expression that
renders something other than what it appears to is invisible here. That half is
the TypeScript file's, and it runs when somebody runs it by hand. This file is
the part that runs on every pull request.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CITATION = REPO_ROOT / "client/src/data/ai-citation.ts"
LAYOUT = REPO_ROOT / "client/src/components/marketing/MarketingLayout.tsx"
PRERENDER = REPO_ROOT / "server/seo-prerender.ts"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_comments(ts: str) -> str:
    """Comments removed before any structural read.

    Not tidiness. `seo-prerender.ts:12` says in a comment: the "Cite FounderConsole"
    block a crawler is served … So a check for a retyped heading that reads the
    raw file reddens on a comment that quotes it, and the obvious repair is to
    weaken the check rather than to strip the comment. Comments are also the
    first place a structural regex grabs the wrong brace or the wrong `heading:`.
    """
    ts = re.sub(r"/\*[\s\S]*?\*/", "", ts)
    return re.sub(r"(?m)^[ \t]*//.*$", "", ts)


def braced_block(src: str, marker: str) -> str:
    """The `{ … }` block that opens at `marker`, brace-matched.

    Used to scope an assertion to ONE function or ONE guard. A file-wide
    `assert "<CitableSnippet />" in layout` would pass with the tag moved
    anywhere else in a 900-line file, which is the guard-cannot-see-its-subject
    family this repo keeps re-finding.
    """
    start = src.index(marker) + len(marker)
    depth, i = 1, start
    while i < len(src) and depth:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
        i += 1
    assert depth == 0, f"unbalanced braces after {marker!r} — the extractor read a cut-off block"
    return src[start : i - 1]


def citation_fields() -> dict[str, str]:
    """The shared copy, read out of the data module rather than restated here."""
    src = strip_comments(read(CITATION))
    out: dict[str, str] = {}
    for field in ("heading", "lede", "attribution"):
        m = re.search(rf'\b{field}:\s*"((?:[^"\\]|\\.)*)"', src)
        assert m, f"aiCitation.{field} is no longer a plain string literal"
        out[field] = m.group(1)
    for label in re.findall(r'label:\s*"((?:[^"\\]|\\.)*)"', src):
        out[f"label:{label[:24]}"] = label
    return out


def citation_hrefs() -> list[str]:
    """Every link target, with the named llms.txt constant resolved to its value."""
    src = strip_comments(read(CITATION))
    const = re.search(r'export const AI_CITATION_LLMS_TXT_URL\s*=\s*"([^"]+)"', src)
    assert const, "AI_CITATION_LLMS_TXT_URL is gone"
    hrefs = [const.group(1)]
    for literal, named in re.findall(r'href:\s*(?:"([^"]+)"|([A-Z_][A-Z0-9_]*))', src):
        hrefs.append(literal if literal else named)
    return hrefs


def citation_block_template() -> str:
    """The server-side block, from its declaration to the close of its list."""
    src = strip_comments(read(PRERENDER))
    start = src.index("const citationBlock = `")
    end = src.index("</ul>`;", start) + len("</ul>`;")
    return src[start:end]


def test_the_copy_is_declared_once_and_read_everywhere_else():
    fields = citation_fields()
    heading = fields["heading"]

    # The live defect this pins was shipped: the footer renders on /pricing, /features,
    # /security, /blog and the homepage, so "Cite this tool" named the wrong thing on
    # every page that is not a tool. Site-scoped, or the label is wrong site-wide.
    assert "FounderConsole" in heading, f"the heading {heading!r} does not name the site"
    assert not re.search(r"this tool", heading, re.I), f"{heading!r} is page-scoped but renders site-wide"

    # Exactly the two surfaces that could carry a second copy. Both must read the record.
    for name, path in (("server/seo-prerender.ts", PRERENDER), ("MarketingLayout.tsx", LAYOUT)):
        body = strip_comments(read(path))
        for field, text in fields.items():
            assert text not in body, (
                f"{name} retypes aiCitation.{field} as a literal ({text[:48]!r}…) instead of "
                f"reading it — the second copy is the one that goes stale"
            )

    hrefs = citation_hrefs()
    assert any("llms.txt" in h for h in hrefs), (
        "the block no longer points at llms.txt; see the module's own note that the pointer "
        "is the only thing allowed to be the source of truth"
    )


def test_the_block_states_no_figure_it_would_have_to_keep_true():
    # `ai-citation.ts` says outright that it carries no figures and points at llms.txt
    # instead, which is what makes it unable to go stale. A number added to the copy is
    # a claim that then has to be kept true on 46 prerendered pages.
    fields = citation_fields()
    for field, text in fields.items():
        assert not re.search(r"\d", text), f"aiCitation.{field} states a figure: {text!r}"


def test_the_crawler_block_is_assembled_from_the_shared_record():
    block = citation_block_template()

    for field in ("heading", "lede", "attribution"):
        assert f"escapeHtml(aiCitation.{field})" in block, (
            f"the served block does not escape-and-inline aiCitation.{field}"
        )
    assert "aiCitation.links" in block and ".map(" in block, "the links are not read from aiCitation"
    assert "escapeHtml(l.href)" in block and "escapeHtml(l.label)" in block, (
        "the link href/label are not taken from the shared record"
    )
    # Derived, not a list of URLs: every target in the block comes from `aiCitation`,
    # so a URL retyped here fails this. The footer's own tool links are elsewhere and
    # are not this block's subject.
    assert "http" not in block, "the served block carries a URL of its own instead of reading aiCitation.links"


def test_one_central_emit_reaches_every_route_that_has_a_body():
    src = strip_comments(read(PRERENDER))

    # Declaration plus exactly one interpolation. A second interpolation is a second
    # emit site, and a second emit site is how the homepage used to get the block twice
    # — once centrally and once from `buildLandingBodyContent()`.
    assert src.count("citationBlock") == 2, (
        f"citationBlock is referenced {src.count('citationBlock')} times, expected 2 "
        f"(the declaration and one interpolation) — a second emit site duplicates the block"
    )

    guard = braced_block(src, "if (meta.bodyContent) {")
    assert "${citationBlock}" in guard, (
        "the block is no longer emitted from inside `if (meta.bodyContent)`, so it has "
        "become conditional on something other than having a body"
    )
    assert "${meta.bodyContent}${citationBlock}" in guard, (
        "the block is no longer appended to the body it belongs to; it is meant to be the "
        "last thing in #ssr-content, after the body"
    )
    assert '<div id="ssr-content"' in guard, "the block is emitted outside the prerendered body container"

    # Non-vacuity: a collapsed extractor must fail loudly rather than assert on "".
    assert len(guard) > 200, f"the bodyContent guard extracted {len(guard)} characters — it did not read a block"


def test_the_footer_still_renders_the_block_for_a_person():
    layout = strip_comments(read(LAYOUT))

    # The TS guard imports Footer by name (`ai-citation-ssr.test.ts`), so an un-export
    # would break that file at import time rather than at an assertion.
    assert "export function Footer()" in layout, "Footer is no longer exported by name"

    snippet = braced_block(layout, "function CitableSnippet() {")
    assert 'data-testid="footer-ai-citation"' in snippet, "the rendered block lost its testid"
    for field in ("heading", "lede", "attribution"):
        assert f"aiCitation.{field}" in snippet, f"CitableSnippet does not render aiCitation.{field}"
    assert "aiCitation.links" in snippet, "CitableSnippet does not render the shared links"

    # Scoped to Footer's own body. This is the whole point of the file: every other
    # citation assertion in the tree reads prerendered HTML, which the React footer does
    # not affect, so deleting this one line kept all of them green while every human lost
    # the block.
    footer = braced_block(layout, "export function Footer() {")
    assert len(footer) > 500, f"Footer() extracted {len(footer)} characters — it did not read a body"
    assert "<CitableSnippet />" in footer, (
        'Footer() no longer renders <CitableSnippet />: the citation block is gone for every '
        "human, however green the prerender looks"
    )
