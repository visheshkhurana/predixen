"""HAG-311: the prerenderer must not keep its own copy of the blog post list.

Two blog URLs in client/public/sitemap.xml served "Article not found" with a
canonical pointing at /blog. HTTP 200, so nothing looked broken; the two slugs
were simply absent from a second, hand-maintained `blogPosts` array in
server/seo-data.ts that had fallen behind client/src/data/blog-posts.ts.

Fixing the two slugs would have left the mechanism, and the next post added
would have drifted the same way. This file guards the mechanism instead: the
list is DERIVED from the client data, which is the pattern seo-prerender.ts
already uses for runway industries (line 8) and founder FAQs (line 11) -- each
with a comment saying not to list the slugs locally. The blog list was the one
never converted, and the one that drifted.

Structural rather than behavioural on purpose: the behavioural half lives in
server/tests/prerender-coverage.test.ts, which calls injectSEO per slug and
needs a production build. This half reads the source, so it runs in the pytest
job with no build, and it fails for a different reason -- a re-typed literal
list restored by a future refactor, which the behavioural test would only catch
once the two lists had already diverged again.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SEO_DATA = REPO / "server" / "seo-data.ts"
CLIENT_POSTS = REPO / "client" / "src" / "data" / "blog-posts.ts"

CLIENT_IMPORT = re.compile(
    r'import\s*\{[^}]*\bblogPosts\s+as\s+\w+[^}]*\}\s*from\s*["\']\.\./client/src/data/blog-posts["\']'
)


def source(path: Path) -> str:
    assert path.is_file(), f"{path} is missing"
    return path.read_text(encoding="utf-8")


def client_slugs() -> list[str]:
    """Every slug in the real post list, which is what the sitemap is built from."""
    return re.findall(r'slug:\s*"([^"]+)"', source(CLIENT_POSTS))


def test_the_client_post_list_is_the_one_with_the_posts_in_it():
    """Precondition for everything below: the real list is non-trivial."""
    slugs = client_slugs()
    assert len(slugs) >= 18, f"expected the client list to hold the real posts, found {len(slugs)}"
    assert len(set(slugs)) == len(slugs), "duplicate slug in the client post list"


def test_seo_data_imports_the_client_post_list():
    """The list is taken from the client file, not re-typed.

    This is the assertion that fails on the broken state: before the fix,
    seo-data.ts declared its own array and imported nothing.
    """
    src = source(SEO_DATA)
    assert CLIENT_IMPORT.search(src), (
        "server/seo-data.ts must import blogPosts from ../client/src/data/blog-posts; "
        "a locally declared list is the duplication that caused HAG-311"
    )


def test_seo_data_does_not_re_type_the_slugs():
    """No hand-typed `slug: "..."` literal may survive in seo-data.ts.

    The client file is the only place a slug is spelled out. A literal here is
    the drift vector itself, and it is what a well-meaning future edit would
    reach for.
    """
    src = source(SEO_DATA)
    literals = re.findall(r'slug:\s*"([^"]+)"', src)
    assert literals == [], (
        "server/seo-data.ts re-types blog slugs "
        f"{literals} -- derive them from ../client/src/data/blog-posts instead"
    )


def test_every_client_slug_has_a_body_in_seo_data():
    """A slug in the list but missing from the bodies renders an EMPTY article.

    buildBlogPostBodyContent returns null only when the post is not found; a
    missing entry in blogPostContent yields zero paragraphs, which is an article
    with a title and a byline and no body. The derived fallback is what makes
    that unreachable for a post the client list knows about.
    """
    src = source(SEO_DATA)
    # The merged export must spread the client bodies before the abridged ones,
    # so every real post has a body and the editorial overrides still win.
    derived = re.search(
        r"Object\.fromEntries\(\s*\w+\.map\(\s*\(\s*\w+\s*\)\s*=>\s*\[\s*\w+\.slug\s*,\s*\w+\.content\s*\]",
        src,
    )
    assert derived, (
        "server/seo-data.ts must build a fallback body map from the client posts "
        "(slug -> content) and merge the abridged bodies on top, so no post in "
        "the list can render body-less"
    )


def test_the_abridged_bodies_were_kept_not_derived():
    """The abridged bodies are an editorial artifact, not a stale copy.

    Deriving them would rewrite the prerendered HTML of 16 correct pages. They
    are shorter than the client by design (5 paragraphs against the client's 16
    for ltv-cac-ratio-explained), so their presence must be explicit.
    """
    src = source(SEO_DATA)
    assert "abridgedBlogPostContent" in src, (
        "the deliberately abridged prerender bodies must stay a named, explicit "
        "artifact -- replacing them with the client bodies silently changes the "
        "served HTML of every post"
    )
    # The abridged map must still override the derived fallback, i.e. be spread
    # AFTER it. If the order flips, the abridged copy is dead code and the
    # pages change.
    # Anchored at the line start so it cannot match `abridgedBlogPostContent`,
    # which is the map declared just above and has no spreads in it at all.
    merged = re.search(
        r"\nexport const blogPostContent[^=]*=\s*\{(.*?)\n\};", src, re.S
    )
    assert merged, "could not find the blogPostContent export to check merge order"
    body = merged.group(1)
    order = re.findall(r"\.\.\.(\w+)", body)
    assert len(order) == 2, f"expected exactly two spreads in blogPostContent, found {order}"
    assert order[0] == "Object", (
        f"the derived client bodies must be spread FIRST so the abridged bodies "
        f"override them; found spreads {order}"
    )
    assert order[1] == "abridgedBlogPostContent", (
        f"abridgedBlogPostContent must be spread second; found spreads {order}"
    )
