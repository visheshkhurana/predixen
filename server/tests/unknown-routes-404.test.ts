// HAG-162. Every path that is not a file used to be answered with the
// prerendered shell and an implicit 200 -- React Router's catch-all
// (`<Route component={NotFound} />`, client/src/App.tsx:600) already rendered
// "not found", so the body was right and the status code lied. Worse, when
// `getPageMeta` had no entry for the path, `injectSEO` returned the shell
// untouched, so the 200 carried the HOMEPAGE title, the HOMEPAGE canonical and
// `index, follow`: every dead URL was a duplicate of the homepage, competing
// with it in the index.
//
// Two things are pinned here.
//
// 1. The status code, for a sample of unknown URLs and for the two families
//    that were already soft 404s (an unknown /blog/ slug, an unknown /runway/
//    vertical) -- both of those emitted `noindex, follow` and a "Page not
//    found" title from a 200.
//
// 2. The route allowlist cannot silently rot. `getPageMeta` knows only the
//    marketing routes, while the client declares every route in App.tsx; a
//    404 for anything `getPageMeta` does not recognise would break ~100
//    logged-in pages. So `server/known-routes.ts` holds the client's route
//    table and THIS FILE re-reads App.tsx and fails when a route appears that
//    the allowlist does not cover. Add a page under a new prefix and CI tells
//    you; you do not have to remember.
//
// Run: npx tsx --test server/tests/unknown-routes-404.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";

import { decideShellResponse } from "../static";
import { isKnownAppRoute, matchesRoutePattern } from "../known-routes";
import { aiCitation } from "../../client/src/data/ai-citation";

const SHELL = readFileSync("client/index.html", "utf8");
const APP_TSX = readFileSync("client/src/App.tsx", "utf8");
const SITEMAP = readFileSync("client/public/sitemap.xml", "utf8");

// Two spellings, because they are two different files: `getPageMeta` writes the
// em dash and `client/index.html` (the shell served when no meta matched)
// carries an ASCII hyphen. The bug being fixed served the second one, so a
// check against only the first would have missed it.
const HOMEPAGE_TITLES = [
  "FounderConsole — AI Decision Simulator for Founders",
  "FounderConsole - AI Decision Simulator for Founders",
];
const NOT_FOUND_TITLE = "Page not found | FounderConsole";

/** The URLs god measured live, plus the two shapes the card names. */
const UNKNOWN_URLS = [
  "/this-page-does-not-exist-xyz123",
  "/pricing/enterprise-does-not-exist",
  "/blog-archive-2019",
  "/admin/not-a-real-admin-page",
];

// Listed separately because they moved: at this branch's original base
// (e4034402) /tools/burn-multiple and /tools/dilution were dead URLs, which is
// why they were in UNKNOWN_URLS. Main has since shipped both as real pages with
// their own prerendered meta, and the sitemap test below requires them to be
// known routes answering 200. Keeping them in UNKNOWN_URLS would assert that a
// live page 404s -- the worse bug of the two this card exists to separate.
const NOW_REAL_TOOLS = ["/tools/burn-multiple", "/tools/dilution", "/tools/ltv-cac"];

function title(html: string): string {
  const m = html.match(/<title>([^<]*)<\/title>/);
  return m ? m[1] : "";
}

function clientRoutes(): string[] {
  const found = new Set<string>();
  const re = /path="([^"]*)"/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(APP_TSX))) {
    found.add(m[1]);
  }
  return [...found];
}

function sitemapUrls(): string[] {
  const found: string[] = [];
  const re = /<loc>([^<]*)<\/loc>/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(SITEMAP))) {
    found.push(m[1].replace(/^https:\/\/founderconsole\.ai/, "") || "/");
  }
  return found;
}

test("every route the client declares is in the server allowlist", () => {
  const routes = clientRoutes();
  // Guard against the regex silently matching nothing and the test passing
  // vacuously -- which is the failure mode of every source-reading test.
  assert.ok(routes.length > 100, `expected the App.tsx route table, got ${routes.length}`);
  assert.ok(routes.includes("/"), "the root route must be in the table");

  const uncovered = routes.filter((r) => !isKnownAppRoute(r));
  assert.deepEqual(
    uncovered,
    [],
    `client/src/App.tsx declares routes the server would answer 404.\n` +
      `Add them to APP_ROUTE_PATTERNS in server/known-routes.ts:\n  ${uncovered.join("\n  ")}`,
  );
});

test("the matcher is segment-wise, so a route does not swallow its children", () => {
  // Exactness matters: `/pricing/bogus` must not inherit `/pricing`.
  assert.equal(matchesRoutePattern("/pricing", "/pricing"), true);
  assert.equal(matchesRoutePattern("/pricing/bogus", "/pricing"), false);
  // `:param` is exactly one segment.
  assert.equal(matchesRoutePattern("/blog/some-post", "/blog/:slug"), true);
  assert.equal(matchesRoutePattern("/blog/some-post/extra", "/blog/:slug"), false);
  assert.equal(matchesRoutePattern("/blog/", "/blog/:slug"), false);
  // Case and trailing slash match what the router does, so neither may 404.
  assert.equal(matchesRoutePattern("/Pricing", "/pricing"), true);
  assert.equal(matchesRoutePattern("/pricing/", "/pricing"), true);
  // The root is its own route and nothing else matches it.
  assert.equal(matchesRoutePattern("/", "/"), true);
  assert.equal(matchesRoutePattern("/pricing", "/"), false);
});

test("unknown URLs answer 404, not a 200 duplicate of the homepage", () => {
  for (const url of UNKNOWN_URLS) {
    const decision = decideShellResponse(SHELL, url);
    assert.equal(decision.status, 404, `${url} must be a 404`);
    // The old response was byte-for-byte the homepage shell. Asserting only
    // the status would not catch a regression that restored that body, so the
    // title is pinned exactly, and both homepage spellings are ruled out.
    assert.equal(
      title(decision.html),
      NOT_FOUND_TITLE,
      `${url} must carry the not-found title`,
    );
    for (const homepage of HOMEPAGE_TITLES) {
      assert.doesNotMatch(
        decision.html,
        new RegExp(`<title>${homepage}</title>`),
        `${url} must not carry the homepage title`,
      );
    }
    assert.match(decision.html, /Page not found/, `${url} must say so in the body`);
    assert.match(decision.html, /noindex/, `${url} must not invite indexing`);
    assert.doesNotMatch(
      decision.html,
      /rel="canonical" href="https:\/\/founderconsole\.ai\/"/,
      `${url} must not claim the homepage as its canonical`,
    );
  }
});

test("unknown blog slugs and runway verticals answer 404", () => {
  // Both families already emitted `noindex, follow` and a "Page not found"
  // title -- from a 200. The meta was right and the status was the bug.
  for (const url of ["/blog/no-such-post-xyz", "/runway/no-such-industry"]) {
    assert.equal(decideShellResponse(SHELL, url).status, 404, `${url} must be a 404`);
  }
  // And the real ones keep working: a 404 that swallowed a live page would be
  // a worse bug than the one being fixed.
  for (const url of ["/blog", "/runway/saas", ...NOW_REAL_TOOLS]) {
    assert.equal(decideShellResponse(SHELL, url).status, 200, `${url} must stay a 200`);
  }
});

test("unknown URLs still render the app, so a visitor is not stranded", () => {
  // The 404 body is the SPA shell: React Router's catch-all renders the
  // not-found page once the bundle loads, exactly as it did at 200. The status
  // is what changed, not the experience.
  const decision = decideShellResponse(SHELL, "/this-page-does-not-exist-xyz123");
  assert.match(decision.html, /<div id="root">/, "the app mount point must survive");
  assert.match(decision.html, /<h1>Page not found<\/h1>/, "and a readable body with it");
  // Links out, so a crawler that lands on a dead URL has somewhere to go.
  // The anchor text is the shared citation label, not a second hardcoded copy.
  assert.match(decision.html, /href="\/tools\/runway-calculator"/);
  const runway = aiCitation.links.find((link) => link.href.endsWith("/tools/runway-calculator"));
  assert.ok(runway, "aiCitation must name the runway calculator");
  assert.match(decision.html, new RegExp(runway.label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
});

test("logged-in app routes are not caught by the 404", () => {
  // The trap this card had to be solved around: `getPageMeta` is a marketing
  // table and knows none of these, so 404-ing what it does not recognise would
  // have broken every authenticated page in the product.
  const appRoutes = [
    "/dashboard",
    "/scenarios",
    "/admin/users",
    "/admin",
    "/settings/notifications",
    "/scenarios/123",
    "/dashboard/abc",
    "/survival/abc",
  ];
  for (const url of appRoutes) {
    assert.equal(decideShellResponse(SHELL, url).status, 200, `${url} must stay a 200`);
  }
});

test("every sitemap URL is a known route and prerenders its own meta", () => {
  const urls = sitemapUrls();
  assert.ok(urls.length >= 44, `sitemap should list 44+ URLs, got ${urls.length}`);

  for (const url of urls) {
    assert.ok(isKnownAppRoute(url), `${url} is in sitemap.xml but not a known route`);
    const decision = decideShellResponse(SHELL, url);
    assert.equal(decision.status, 200, `${url} is in sitemap.xml, so it must be a 200`);

    const pageTitle = title(decision.html);
    assert.notEqual(pageTitle, "", `${url} has no <title>`);
    // `/` is the homepage, so it is the one URL in the sitemap whose title
    // SHOULD be a homepage title. Every other URL carrying one would be the
    // duplicate this card is about.
    if (url !== "/") {
      assert.ok(
        !HOMEPAGE_TITLES.includes(pageTitle),
        `${url} is in the sitemap but renders the homepage title -- a duplicate, not a page`,
      );
    }
    assert.doesNotMatch(decision.html, /noindex/, `${url} is in the sitemap, so it is indexable`);
    // Server-side content, for a crawler that runs no JavaScript: this is the
    // "renders server-side, not just in a browser" half of the card.
    assert.match(
      decision.html,
      /<div id="ssr-content"/,
      `${url} has no prerendered body in the server HTML`,
    );
    assert.match(
      decision.html,
      /<h1[ >]/,
      `${url} has no server-rendered <h1>`,
    );
  }
});
