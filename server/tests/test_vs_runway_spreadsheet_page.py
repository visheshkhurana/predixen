"""Structural checks for the public page `/vs/runway-calculator-vs-spreadsheet`.

Why this file exists in Python as well as TypeScript: `pr-checks.yml` names every
TypeScript test file one by one as its own step, and that workflow is on the hold
list, so `vs-runway-spreadsheet-ssr.test.ts` does NOT run in CI. `pytest.ini` sets
`testpaths = server/tests`, so this file is collected automatically with no
workflow change at all. It is the half of the coverage that actually executes.

The thing being guarded is a page that is served but cannot rank. A new public
page needs FOUR registrations, not two, and getting three of them right still
ships a soft duplicate of `/`:

  1. the `<Route>` in `client/src/App.tsx`;
  2. membership of the marketing set in `client/src/App.tsx` — without it a
     LOGGED-IN visitor gets the app shell (sidebar, dashboard chrome) wrapped
     around a public page, while a logged-out visitor sees it correctly, which is
     exactly the bug that survives a manual check;
  3. the `PUBLIC_ROUTES` entry in `scripts/generate-sitemap.ts` plus the
     regenerated `client/public/sitemap.xml`;
  4. the `getPageMeta()` entry in `server/seo-prerender.ts` — `injectSEO` returns
     the shell UNTOUCHED for a path it does not know, and that shell carries
     `index, follow` and the HOMEPAGE canonical.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PAGE_PATH = "/vs/runway-calculator-vs-spreadsheet"
PAGE_FILE = REPO_ROOT / "client/src/pages/vs-runway-calculator-vs-spreadsheet.tsx"
APP = REPO_ROOT / "client/src/App.tsx"
SITEMAP_GEN = REPO_ROOT / "scripts/generate-sitemap.ts"
SITEMAP_XML = REPO_ROOT / "client/public/sitemap.xml"
PRERENDER = REPO_ROOT / "server/seo-prerender.ts"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_page_component_exists_and_uses_the_house_pattern():
    src = read(PAGE_FILE)
    # The pattern every other public marketing page uses: /alternatives and
    # /compare are built the same way. The card said to pick the pattern the
    # existing site uses if no doc fixes it.
    assert 'from "@/components/marketing/MarketingLayout"' in src
    assert "useSEO({" in src
    assert f'path: "{PAGE_PATH}"' in src
    assert "data-testid=\"text-vs-title\"" in src


def test_edit_one_the_route_is_registered():
    src = read(APP)
    assert f'<Route path="{PAGE_PATH}">' in src, "route missing from App.tsx"
    assert 'lazy(() => import("@/pages/vs-runway-calculator-vs-spreadsheet"))' in src, "lazy import missing"


def test_edit_two_the_marketing_set_covers_the_vs_prefix():
    src = read(APP)
    # marketingPrefixes, not marketingPaths: "/vs/" is a series, and the prefix
    # keeps the next comparison page from having to remember this.
    assert "'/vs/'," in src, "the /vs/ prefix is not in the marketing prefix list"


def test_edit_three_the_route_is_declared_and_in_the_sitemap():
    gen = read(SITEMAP_GEN)
    assert f'path: "{PAGE_PATH}"' in gen, "not declared in PUBLIC_ROUTES"
    xml = read(SITEMAP_XML)
    assert f"<loc>https://founderconsole.ai{PAGE_PATH}</loc>" in xml, "no <loc> in sitemap.xml"


def test_edit_four_get_page_meta_knows_the_path():
    src = read(PRERENDER)
    assert f'if (path === "{PAGE_PATH}")' in src, "getPageMeta does not know the path"
    assert f'canonical: SITE_URL + "{PAGE_PATH}"' in src, "no canonical of its own"
    # The body must be built by the page's own builder, not borrowed from another
    # path — a shared builder would hand this page the wrong copy.
    assert "bodyContent: buildVsRunwaySpreadsheetBodyContent()," in src


def test_the_prerendered_body_links_the_free_tools_it_compares():
    src = read(PRERENDER)
    start = src.index("function buildVsRunwaySpreadsheetBodyContent")
    end = src.index("function esc(t: string)", start)
    body = src[start:end]
    for href in (
        "/tools/runway-calculator",
        "/default-alive",
        "/survival-simulator",
        "/runway/saas",
        "/compare",
        "/features",
        "/pricing",
        "/signup",
    ):
        assert f'href="{href}"' in body, f"server-rendered body is missing {href}"


def test_the_page_ends_in_a_reason_to_sign_up():
    # Same rule the free tools carry: the page has to earn the next step.
    # HAG-449 moved the CTA off /auth?tab=register (the un-prerendered shell)
    # and onto /signup, which renders the same register form from a prerendered
    # document. The rule is unchanged: the page still ends in a signup CTA.
    src = read(PAGE_FILE)
    assert '/signup' in src, "no signup CTA"
    assert 'data-testid="button-vs-auth"' in src, "CTA is not instrumentable"


def test_the_page_keeps_its_promise_not_to_name_a_competitor():
    # The page states this in its own closing note, so the assertion is the page
    # keeping its word rather than an outside preference.
    #
    # Scoped to THIS page's two halves on purpose: /compare's body elsewhere in
    # seo-prerender.ts names Sturppy, Finmark and Causal, and scanning the whole
    # file would assert that published page's copy instead of this one's.
    prerender = read(PRERENDER)
    start = prerender.index("function buildVsRunwaySpreadsheetBodyContent")
    end = prerender.index("function esc(t: string)", start)
    for src in (read(PAGE_FILE), prerender[start:end]):
        lowered = src.lower()
        for vendor in ("sturppy", "finmark", "causal", "lucanet", "mosaic", "brex"):
            assert vendor not in lowered, f"names a vendor: {vendor}"


def test_the_page_states_the_limit_of_a_free_calculator():
    # The honest half. Without it the page is an advert, and an advert does not
    # rank for a comparison query.
    src = read(PAGE_FILE).lower()
    assert "where the spreadsheet wins" in src
    assert "the honest limit of a free calculator" in src
    assert "it still returns one number" in src


def test_the_spreadsheet_arithmetic_on_the_page_is_arithmetic():
    # $120,000 against $20,000 a month is six months. The page presents this as
    # arithmetic, not as a product claim or a benchmark — an invented figure in a
    # comparison page is the failure mode this pins.
    assert 120_000 / 20_000 == 6
    src = read(PAGE_FILE)
    assert "$120,000 in the bank against $20,000 of net burn is six months" in src
