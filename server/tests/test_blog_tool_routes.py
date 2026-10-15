"""E-blog-links-1: every blog post routes the reader to the runway calculator.

Why this file is Python rather than a `.test.ts`: `pr-checks.yml` lists every
TypeScript test file by hand as its own step, and that workflow is on the hold
list, so a new `.test.ts` would not run in CI at all. `pytest.ini` sets
`testpaths = server/tests`, so this file is collected automatically with no
workflow change. It is the half of the coverage that actually executes.

The experiment. The blog is the only surface where the scoreboard has ever
recorded a stranger-like arrival, and most of its posts carried no route to a
tool at all, so a reader who arrived from search had nothing to do next. The
change adds one in-body link to `/tools/runway-calculator` per post that had
none, inside the argument rather than in a footer, and the metric is
`/tools visitors`, 1 -> >=4, checked 2026-10-29.

What is guarded, and why each one is worth a test:

  1. Every post carries the link. This is the precondition of the metric: a new
     post published without one silently leaks readers, and the leak is
     invisible in the dashboard because it looks like a slow month.
  2. The link is inside the post's `content` array. `content: string[]` IS the
     body, and the site footer is rendered by `MarketingLayout`, so a link in
     `content` is in-body by construction. The card's instruction was "inside
     the argument rather than a footer" — this pins the structural half of that
     sentence, which is the half a test can see; the editorial half (does the
     sentence belong to the argument?) is a review question, not an assertion.
  3. The link is a markdown link to the exact path, so a typo cannot ship a
     route that 404s. Wouter renders `](...)` targets, and the calculator's
     route is `/tools/runway-calculator`.
  4. The target was not replaced by the killed `/tools` nav link. The nav link
     was killed on two independent measurements; this is the destination that
     survived, and the two are easy to confuse in a later edit.

This file is deliberately a count-of-posts test, not a list of 18 slugs: a slug
list would need editing on every new post and would fail for the wrong reason.
The cost is that adding a post without a link fails here — which is the point.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

BLOG_POSTS = REPO_ROOT / "client/src/data/blog-posts.ts"

CALC_PATH = "/tools/runway-calculator"
FOOTER_OWNER = REPO_ROOT / "client/src/components/marketing/MarketingLayout.tsx"


def source() -> str:
    return BLOG_POSTS.read_text(encoding="utf-8")


def blocks(src: str) -> dict[str, str]:
    """Split the posts array into one block per post, keyed by slug."""
    out: dict[str, str] = {}
    for chunk in re.split(r"\n  \{\n", src)[1:]:
        found = re.search(r'slug:\s*"([^"]+)"', chunk)
        if found:
            out[found.group(1)] = chunk
    return out


def content_block(post: str) -> str:
    """The `content: [...]` array of one post, by bracket matching.

    Slicing from the marker to the next `\n  ]` would work on today's file and
    break on the first post whose body contains that indentation, so this
    counts brackets instead.
    """
    at = post.index("content: [")
    start = post.index("[", at)
    depth, i = 0, start
    while i < len(post):
        if post[i] == "[":
            depth += 1
        elif post[i] == "]":
            depth -= 1
            if depth == 0:
                return post[start : i + 1]
        i += 1
    raise AssertionError("unbalanced brackets in content array")


def test_every_post_has_a_body() -> None:
    src = source()
    posts = blocks(src)
    assert len(posts) >= 13, f"only {len(posts)} posts parsed; the splitter is wrong"
    for slug, post in posts.items():
        body = content_block(post)
        assert "content: [" in post, f"{slug} has no content array"
        assert body.count('"') >= 2, f"{slug} has an empty content array"


def test_every_post_routes_to_the_calculator() -> None:
    src = source()
    missing = [slug for slug, post in blocks(src).items() if CALC_PATH not in post]
    assert not missing, f"posts with no route to {CALC_PATH}: {missing}"


def test_the_route_is_inside_the_body_not_the_excerpt() -> None:
    src = source()
    for slug, post in blocks(src).items():
        in_body = content_block(post).count(CALC_PATH)
        in_whole_post = post.count(CALC_PATH)
        assert in_body == in_whole_post, (
            f"{slug} has {in_whole_post - in_body} occurrence(s) outside content[] "
            "— a link in excerpt/metadata is a teaser, not an in-body route"
        )
        assert in_body >= 1, f"{slug} has no in-body route"


def test_the_route_is_a_markdown_link_to_the_calculator_page() -> None:
    src = source()
    pattern = re.compile(r"\]\(" + re.escape(CALC_PATH) + r"\)")
    for slug, post in blocks(src).items():
        assert pattern.search(content_block(post)), (
            f"{slug} mentions {CALC_PATH} without a markdown link to it"
        )


def test_the_destination_is_not_the_killed_tools_nav_link() -> None:
    src = source()
    # The `/tools` nav link was killed on two independent measurements; the
    # calculator page is the destination that survived. `](/tools)` is not a
    # substring of the good link, so this cannot pass by accident.
    for slug, post in blocks(src).items():
        assert "](/tools)" not in post, f"{slug} links the killed /tools nav page"


def test_the_footer_route_already_existed_and_is_unchanged() -> None:
    # Measured, not assumed: `MarketingLayout` already carries a site-wide
    # footer nav link to the calculator, identical on `main`, so this change is
    # additive rather than the blog's first route to the tool. Pinned to exactly
    # one so that a later edit which removes it (changing the metric's floor) or
    # duplicates it (inflating every page's contribution) fails here, where the
    # reason is legible, instead of showing up as an unexplained move in
    # `/tools visitors`.
    layout = FOOTER_OWNER.read_text(encoding="utf-8")
    assert layout.count(CALC_PATH) == 1, (
        f"MarketingLayout has {layout.count(CALC_PATH)} links to {CALC_PATH}; "
        "expected exactly the one pre-existing footer nav item, so that the "
        "blog experiment is read against a fixed baseline"
    )
    assert '"Runway Calculator"' in layout, "the footer nav item was renamed"
