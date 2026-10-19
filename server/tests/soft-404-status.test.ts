// Unknown tool and industry URLs were HTTP 200 with the SPA shell (or a
// noindex title and an empty body). They must be a real 404: status and SSR.
// Valid slugs stay 200.
//
// HAG-449 removed `/tools` and `/tools/` from the 404 list: the hub is now a
// real page, so both are 200. `/tools/<unknown>` is still a 404 and still has
// to say so — otherwise this change would have turned every mistyped tool URL
// back into a soft 404.
//
// HAG-449 also moved the `/tools` hub guard here. It used to live in
// `tools-index.test.ts`, which CI never ran: `pr-checks.yml` names every test
// file one step at a time with no glob, so a new file under `server/tests/` is
// invisible until someone edits that workflow — and that workflow is hold-listed.
// This file IS wired (step "soft 404 status for unknown tools and industries"),
// so the guard lives where it actually executes. A test nothing runs is a
// liability disguised as coverage.
//
// Run: npx tsx --test server/tests/soft-404-status.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import { readFileSync } from "fs";
import type { Server } from "http";
import { RUNWAY_INDUSTRIES } from "../../client/src/data/runway-industries";
import { renderHtmlPage } from "../seo-prerender";

const SHELL = readFileSync("client/index.html", "utf8");
const SITE = "https://founderconsole.ai";
const TOOLS_INDEX_PAGE = "client/src/pages/tools-index.tsx";

/** Every `/tools/<slug>` route the app actually registers in App.tsx. */
function registeredToolRoutes(): string[] {
  const source = readFileSync("client/src/App.tsx", "utf8");
  const routes = [...source.matchAll(/<Route\s+path="(\/tools\/[^"]+)"/g)].map((m) => m[1]);
  // A duplicate path in App.tsx would silently pass a set comparison below.
  assert.equal(new Set(routes).size, routes.length, "duplicate /tools/* route in App.tsx");
  return [...new Set(routes)].sort();
}

/** Every `/tools/<slug>` path a document links to. */
function linkedToolPaths(html: string): string[] {
  const hrefs = [...html.matchAll(/href="(\/tools\/[^"?#]+)"/g)].map((m) => m[1]);
  return [...new Set(hrefs)].sort();
}

/** Every root-level (`/foo`, not `/tools/foo`) href inside one slice of a file. */
function rootHrefs(slice: string, pattern: RegExp): string[] {
  const hrefs = [...slice.matchAll(pattern)].map((m) => m[1]);
  return [...new Set(hrefs)].sort();
}

const NOT_FOUND = ["/tools/unknown", "/runway/not-a-real-industry"];
const TOOLS = [
  "/tools/runway-calculator",
  "/tools/burn-multiple",
  "/tools/dilution",
  "/tools/ltv-cac",
];

function startServer(): Promise<{ base: string; server: Server }> {
  const app = express();
  app.use("*", (req, res) => {
    const pathname = req.originalUrl.split("?")[0].split("#")[0];
    const page = renderHtmlPage(SHELL, pathname);
    res.status(page.status).type("html").send(page.html);
  });
  return new Promise((resolve) => {
    const server = app.listen(0, () => {
      resolve({ base: `http://127.0.0.1:${(server.address() as any).port}`, server });
    });
  });
}

test("unknown tool and industry URLs are HTTP 404 with a not-found document", async (t) => {
  const { base, server } = await startServer();
  t.after(() => server.close());

  for (const path of NOT_FOUND) {
    const response = await fetch(base + path);
    const html = await response.text();
    assert.equal(response.status, 404, path);
    assert.match(html, /<h1>Page not found<\/h1>/, path);
    assert.match(html, /content="noindex, follow"/, path);
    assert.doesNotMatch(html, /Flight Simulator for Founders/, path);
  }
});

test("valid tool and industry slugs stay 200, including a trailing slash", async (t) => {
  const { base, server } = await startServer();
  t.after(() => server.close());

  for (const path of TOOLS) {
    for (const suffix of ["", "/"]) {
      const response = await fetch(base + path + suffix);
      const html = await response.text();
      assert.equal(response.status, 200, path + suffix);
      assert.match(html, /<h1>/, path + suffix);
      assert.doesNotMatch(html, /<h1>Page not found<\/h1>/, path + suffix);
    }
  }

  // The hub, with and without the trailing slash. It is listed separately from
  // TOOLS because its body is the index, not a calculator.
  for (const path of ["/tools", "/tools/"]) {
    const response = await fetch(base + path);
    const html = await response.text();
    assert.equal(response.status, 200, path);
    assert.match(html, /<h1>Free Startup Finance Tools<\/h1>/, path);
    assert.doesNotMatch(html, /<h1>Page not found<\/h1>/, path);
  }

  for (const industry of RUNWAY_INDUSTRIES) {
    const response = await fetch(base + "/runway/" + industry.slug);
    const html = await response.text();
    assert.equal(response.status, 200, industry.slug);
    assert.match(html, new RegExp(`<h1>${industry.name}</h1>`));
    assert.doesNotMatch(html, /<h1>Page not found<\/h1>/);
  }

  const appShell = await fetch(base + "/overview");
  assert.equal(appShell.status, 200);
});

// --- HAG-449: the `/tools` hub ------------------------------------------
//
// A hub that lists three of four tools is worse than the 404 it replaced: the
// visitor cannot tell anything is missing. So the assertion is not "the page
// mentions a calculator" but set equality — the `/tools/*` links in the page
// equal the `/tools/*` routes `App.tsx` registers, and it fails by name with
// both lists printed. Checked against BOTH copies of the list, because
// `injectSEO` puts the prerendered body inside `#root` and `createRoot()`
// replaces it on first render: a guard over the prerender alone protects the
// crawler's view and nobody else's.

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
  for (const path of ["/tools", "/tools/"]) {
    const html = renderHtmlPage(SHELL, path).html;
    assert.deepEqual(
      linkedToolPaths(html),
      expected,
      `prerendered hub links do not match App.tsx routes (${path})`,
    );
  }
});

test("the client page lists the same /tools/* routes as the prerendered body", () => {
  // The page visitors actually see is `tools-index.tsx`; the prerender is
  // replaced by it for anyone with JS. Its card list is a separate hardcoded
  // array, so it needs its own assertion or it drifts silently.
  const expected = registeredToolRoutes();
  const src = readFileSync(TOOLS_INDEX_PAGE, "utf8");
  assert.deepEqual(
    rootHrefs(src, /href:\s*"(\/tools\/[^"?#]+)"/g),
    expected,
    "tools-index.tsx cards do not match App.tsx routes",
  );
});

test("the root-tools group offers only tools that need no account", () => {
  // `/ai-cfo` is a product page: its own copy excludes itself from the
  // no-account list and its only CTA is `/auth`. Listing it under a heading
  // that promises "no account, no card" sends a visitor to a signup.
  const NO_ACCOUNT = ["/default-alive", "/survival-simulator"];

  const html = renderHtmlPage(SHELL, "/tools").html;
  const start = html.indexOf("<h2>Two more free tools</h2>");
  assert.ok(start > 0, "prerendered hub is missing the free-tools group heading");
  const end = html.indexOf("<h2>", start + 1);
  assert.ok(end > start, "could not find the end of the free-tools group");
  assert.deepEqual(
    rootHrefs(html.slice(start, end), /href="(\/[^"?#]+)"/g),
    NO_ACCOUNT,
    "prerendered free-tools group lists a tool that needs an account",
  );

  const src = readFileSync(TOOLS_INDEX_PAGE, "utf8");
  const s = src.indexOf("const MORE_TOOLS");
  const e = src.indexOf("];", s);
  assert.ok(s > 0 && e > s, "could not find MORE_TOOLS in tools-index.tsx");
  assert.deepEqual(
    rootHrefs(src.slice(s, e), /href:\s*"(\/[^"?#]+)"/g),
    NO_ACCOUNT,
    "MORE_TOOLS lists a tool that needs an account",
  );

  // The link stays on both pages — it is a reason to continue, not a freebie.
  assert.ok(html.includes('href="/ai-cfo"'), "prerendered hub dropped /ai-cfo");
  assert.ok(src.includes('"/ai-cfo"'), "tools-index.tsx dropped /ai-cfo");
});

test("an unknown tool slug is still a real 404, and now points at the hub", () => {
  const page = renderHtmlPage(SHELL, "/tools/not-a-tool");
  assert.equal(page.status, 404);
  assert.match(page.html, /content="noindex, follow"/);
  assert.match(page.html, /<h1>Page not found<\/h1>/);
  assert.match(page.html, new RegExp(`href="${SITE}/tools"`), "404 should offer the hub");
});

test("production HTML catch-alls use renderHtmlPage for the status", () => {
  const staticSrc = readFileSync("server/static.ts", "utf8");
  const viteSrc = readFileSync("server/vite.ts", "utf8");
  assert.match(staticSrc, /renderHtmlPage\(indexHtml, pathname\)/);
  assert.match(staticSrc, /res\.status\(page\.status\)/);
  assert.match(viteSrc, /renderHtmlPage\(page, cleanPath\)/);
  assert.match(viteSrc, /res\.status\(rendered\.status\)/);
  assert.doesNotMatch(staticSrc, /res\.status\(200\)/);
  assert.doesNotMatch(viteSrc, /res\.status\(200\)/);
});
