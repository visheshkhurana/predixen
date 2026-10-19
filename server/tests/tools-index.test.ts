// HAG-449: `/tools` is a page now, and a hub that lists three of four tools is
// worse than the 404 it replaced — the visitor cannot tell anything is missing.
//
// So the assertion is not "the page mentions a calculator". It is that the set
// of `/tools/*` links in the page equals the set of `/tools/*` routes `App.tsx`
// registers. Add a tool and forget the hub, and this fails by name.
//
// Run: npx tsx --test server/tests/tools-index.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { renderHtmlPage } from "../seo-prerender";

const SHELL = readFileSync("client/index.html", "utf8");
const SITE = "https://founderconsole.ai";

/** Every `/tools/<slug>` route the app actually registers in App.tsx. */
function registeredToolRoutes(): string[] {
  const source = readFileSync("client/src/App.tsx", "utf8");
  const routes = [...source.matchAll(/<Route\s+path="(\/tools\/[^"]+)"/g)].map((m) => m[1]);
  // A duplicate path in App.tsx would silently pass a set comparison below.
  assert.equal(new Set(routes).size, routes.length, "duplicate /tools/* route in App.tsx");
  return [...new Set(routes)].sort();
}

/** Every `/tools/<slug>` path the rendered page links to. */
function linkedToolPaths(html: string): string[] {
  const hrefs = [...html.matchAll(/href="(\/tools\/[^"?#]+)"/g)].map((m) => m[1]);
  return [...new Set(hrefs)].sort();
}

test("the hub is a real 200 page with its own canonical", () => {
  for (const path of ["/tools", "/tools/"]) {
    const page = renderHtmlPage(SHELL, path);
    assert.equal(page.status, 200, path);
    assert.match(page.html, /<h1>Free Startup Finance Tools<\/h1>/, path);
    assert.match(page.html, new RegExp(`<link rel="canonical" href="${SITE}/tools" />`), path);
    assert.doesNotMatch(page.html, /content="noindex/, `${path} must be indexable`);
    assert.doesNotMatch(page.html, /<h1>Page not found<\/h1>/, path);
  }
});

test("the hub links every /tools/* route the app registers, and nothing else", () => {
  const expected = registeredToolRoutes();
  assert.ok(expected.length >= 4, `expected at least four tool routes, found ${expected.length}`);
  const html = renderHtmlPage(SHELL, "/tools").html;
  assert.deepEqual(linkedToolPaths(html), expected, "hub links vs App.tsx routes");
});

test("the hub also lists the free tools that live at the site root", () => {
  const html = renderHtmlPage(SHELL, "/tools").html;
  for (const href of ["/default-alive", "/survival-simulator", "/ai-cfo"]) {
    assert.ok(html.includes(`href="${href}"`), `hub is missing ${href}`);
  }
});

test("an unknown tool slug is still a real 404, and now points at the hub", () => {
  const page = renderHtmlPage(SHELL, "/tools/not-a-tool");
  assert.equal(page.status, 404);
  assert.match(page.html, /content="noindex, follow"/);
  assert.match(page.html, /<h1>Page not found<\/h1>/);
  assert.match(page.html, new RegExp(`href="${SITE}/tools"`), "404 should offer the hub");
});
