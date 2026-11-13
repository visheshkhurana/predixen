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
PRERENDER = REPO / "server" / "seo-prerender.ts"
CLIENT_POSTS = REPO / "client" / "src" / "data" / "blog-posts.ts"

# Either spelling satisfies "the list is taken from the client file": a local
# binding (`import { blogPosts as X }`) or a re-export (`export { blogPosts }`).
# main took the re-export in #131, which is one line shorter and leaves no
# binding to drift; this test asserts the ORIGIN, which both spellings name.
CLIENT_IMPORT = re.compile(
    r'(?:import|export)\s*\{[^}]*\bblogPosts\b[^}]*\}\s*from\s*["\']\.\./client/src/data/blog-posts["\']'
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
    """No `slug: "..."` FIELD literal may survive in seo-data.ts.

    This guards one of the two spellings a slug can take in this file: the
    field, as it appears in a re-typed post object. A field literal is the
    drift vector HAG-311 was, and it is what a well-meaning future edit would
    reach for.

    It is NOT a claim that no slug is spelled out here at all -- that was the
    sentence this docstring used to carry and it was false. `prerenderPostMeta`
    and `abridgedBlogPostContent` are keyed by 16 slugs each, spelled out as
    quoted keys, and they are deliberately hand-keyed editorial artifacts rather
    than copies of the list. The keys are a different spelling, they are
    covered by test_every_slug_keyed_here_is_a_real_client_slug below, and the
    two tests together are what makes the pair of claims complete: this one
    catches a re-typed field, that one catches an orphaned key.
    """
    src = source(SEO_DATA)
    literals = re.findall(r'slug:\s*"([^"]+)"', src)
    assert literals == [], (
        "server/seo-data.ts re-types blog slugs "
        f"{literals} -- derive them from ../client/src/data/blog-posts instead"
    )


def test_every_slug_keyed_here_is_a_real_client_slug():
    """A slug spelled out as a map KEY must be a slug the client list has.

    The invariant over the second spelling. An entry keyed by a slug that the
    client post list does not contain is orphaned: it is never looked up, so
    the post it was written for silently loses its pinned excerpt and reverts
    from its abridged crawler body to the full client content. No other test
    fails -- the page still renders, it just renders differently from the
    editorial intent, which is the class of thing this file exists to catch.

    The keys are allowed to exist; they are not allowed to go stale. This is
    the assertion that fires the day someone renames a slug in
    client/src/data/blog-posts.ts and leaves the two maps behind.
    """
    src = source(SEO_DATA)
    client = set(client_slugs())
    keyed = set(re.findall(r'^\s*"([^"]+)"\s*:', src, re.M))
    orphans = sorted(keyed - client)
    assert orphans == [], (
        f"server/seo-data.ts keys hand-maintained maps on slugs the client post "
        f"list does not have: {orphans} -- these entries are never reached, so "
        f"those posts lose their pinned excerpt and abridged body; fix the key "
        f"or derive the entry"
    )


def test_every_client_slug_has_a_body_in_seo_data():
    """A slug in the list but missing from the bodies renders an EMPTY article.

    buildBlogPostBodyContent returns null only when the post is not found; a
    post whose body resolves to nothing yields zero paragraphs, which is an
    article with a title and a byline and no body.

    After #131 the body is the client post's own `content` field, shipped down
    the one chain the sitemap also reads: blog-posts.ts -> seo-data.ts
    (re-export) -> seo-prerender.ts. So the invariant splits into the two
    things that chain needs: the prerenderer must take its posts from
    seo-data, and every post in the client list must actually carry content.
    A hand-kept body map in seo-data was the old way of satisfying this, and
    it is exactly what fell two posts behind.
    """
    prerender = source(PRERENDER)
    assert re.search(
        r'import\s*\{[^}]*\bblogPosts\b[^}]*\}\s*from\s*["\']\./seo-data["\']', prerender
    ), (
        "server/seo-prerender.ts must take blogPosts from ./seo-data, the module "
        "that re-exports the client list -- a second list here is the HAG-311 bug"
    )
    client = source(CLIENT_POSTS)
    slugs = client_slugs()
    # `content` is a paragraph array in the client data (`content: [` ... `]`).
    bodies = re.findall(r"^\s*content:\s*\[", client, re.M)
    assert bodies, "could not find any content: array in the client post list"
    assert not re.search(r"^\s*content:\s*\[\s*\]", client, re.M), (
        "a client post declares an EMPTY content array, so it would prerender as "
        "an article with a title and no body"
    )
    assert len(bodies) >= len(slugs), (
        f"{len(slugs)} posts in the client list but only {len(bodies)} content "
        "arrays; a post without content renders body-less"
    )



def test_no_second_post_list_lives_in_seo_data():
    """The regression HAG-311 actually was: a COPY of the list in seo-data.ts.

    The old file kept its own `blogPosts` array plus hand-written maps of
    excerpt and body overrides (prerenderPostMeta, abridgedBlogPostContent,
    blogPostContent), and it fell two posts behind the client list. #131
    replaced the whole thing with a one-line re-export. This asserts the
    replacement stayed a re-export: no local array, and no local body or
    excerpt map, so a future edit cannot quietly reintroduce the copy that
    drifted. The behaviour this protects -- every sitemap slug serving its own
    article -- is measured per slug in prerender-coverage.test.ts.
    """
    src = source(SEO_DATA)
    assert not re.search(r"\b(?:const|let|var)\s+blogPosts\b", src), (
        "server/seo-data.ts declares its own blogPosts -- that is the second copy "
        "that fell two posts behind the sitemap under HAG-311; re-export the "
        "client list instead"
    )
    for name in ("abridgedBlogPostContent", "blogPostContent", "prerenderPostMeta"):
        assert name not in src, (
            f"server/seo-data.ts keeps a local {name}: a second, hand-maintained "
            "copy of blog data is what drifted under HAG-311; read it from the "
            "client list instead"
        )
