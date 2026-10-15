// Council 2026-10-15 item 1 - the "Cite FounderConsole" block.
//
// The React footer renders it from `client/src/data/ai-citation.ts`, but the footer only
// exists after the bundle runs and GPTBot does not run it. So the half that matters to an
// AI crawler is the half the prerender emits. This pins that the served HTML carries the
// block on EVERY route that has a body, exactly once each, that it names llms.txt, that
// its text is the shared string rather than a retyped copy, and — the half nothing else
// can see — that the React footer still renders it for a human.
//
// The block is emitted centrally in `injectSEO`, not from a page builder. The first
// version called it from `buildLandingBodyContent()` alone and reached 1 of the 46
// prerendered routes that emit a body — the homepage only — which is the same shape as the
// duplicate `blogPosts` array that caused HAG-311: a per-route list somebody has to
// remember to update.
//
// Run: npx tsx --test server/tests/ai-citation-ssr.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { register } from "node:module";
import React from "react";
import TestRenderer from "react-test-renderer";
import { Router } from "wouter";
import { memoryLocation } from "wouter/memory-location";
import { injectSEO } from "../seo-prerender";
import { PUBLIC_ROUTES } from "../../scripts/generate-sitemap";
import { blogPosts } from "../../client/src/data/blog-posts";
import { aiCitation } from "../../client/src/data/ai-citation";

// The prerenderer is shell-agnostic about where it came from; `client/index.html` is the
// source the build copies, so this needs no `dist/` and no build step.
const SHELL = readFileSync("client/index.html", "utf8");

/** Every route the prerenderer can emit a body for. Derived, never hand-listed. */
const PRERENDERED_PATHS = [
  ...PUBLIC_ROUTES.map((r) => r.path),
  ...blogPosts.map((p) => `/blog/${p.slug}`),
];

function ssrBody(html: string): string {
  const m = html.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/);
  return m ? m[1] : "";
}

const HEADING = `<h2>${aiCitation.heading}</h2>`;
const occurrences = (haystack: string, needle: string) => haystack.split(needle).length - 1;

test("every prerendered route that has a body carries the citation block", () => {
  const missing: string[] = [];
  const noBody: string[] = [];
  let withBody = 0;

  for (const path of PRERENDERED_PATHS) {
    const body = ssrBody(injectSEO(SHELL, path));
    if (body.length === 0) {
      noBody.push(path);
      continue;
    }
    withBody++;
    if (!body.includes(HEADING)) missing.push(path);
  }

  assert.equal(
    missing.length,
    0,
    `these routes emit a body but no citation block:\n  ${missing.join("\n  ")}`
  );
  assert.ok(
    withBody > 40,
    `expected the majority of the ${PRERENDERED_PATHS.length} prerendered routes to emit a ` +
      `body, only ${withBody} did — a shrunken list must not be able to pass by walking itself`
  );
  // HAG-311's two slugs. Named so this list has to SHRINK to empty when that fix lands
  // rather than quietly grow a third entry.
  assert.deepEqual(
    noBody,
    ["/blog/what-is-a-good-burn-multiple", "/blog/13-week-cash-flow-template"],
    "the set of body-less routes changed"
  );
});

test("the block appears exactly once per route, the homepage included", () => {
  // The homepage is the one route that used to emit it from `buildLandingBodyContent()`.
  // Central emission replaced that call, so this is the assertion that catches the block
  // being emitted twice there — once by a leftover builder call and once centrally.
  for (const path of PRERENDERED_PATHS) {
    const out = injectSEO(SHELL, path);
    const body = ssrBody(out);
    if (body.length === 0) continue;

    assert.equal(
      occurrences(body, HEADING),
      1,
      `${path} carries the citation heading ${occurrences(body, HEADING)} times, expected 1`
    );
    // And not once in the body plus once somewhere else in the document: a crawler reads
    // the whole response, not just #ssr-content.
    const llms = `<a href="${aiCitation.links[0].href}">`;
    assert.equal(
      occurrences(out, llms),
      1,
      `${path} links llms.txt ${occurrences(out, llms)} times in the whole document, expected 1`
    );
  }
});

test("the served copy points at llms.txt and is the string the footer renders", () => {
  const body = ssrBody(injectSEO(SHELL, "/"));
  assert.ok(body.length > 0, "no #ssr-content body was emitted for /");

  for (const link of aiCitation.links) {
    assert.ok(body.includes(`href="${link.href}"`), `missing citation href ${link.href}`);
  }
  // The pointer to the canonical quotable-figures file is the whole point of the block.
  assert.ok(
    body.includes("https://founderconsole.ai/llms.txt"),
    "the block does not point at llms.txt"
  );

  const text = body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
  assert.ok(
    text.includes(`${aiCitation.lede} ${aiCitation.attribution}`),
    "the lede/attribution in the served HTML is not the shared string"
  );
});

test("the heading names the site, not the page it happens to be on", () => {
  // A live defect, not a style preference. The React copy renders inside `Footer()`, so
  // "Cite this tool" was already on /pricing, /features, /security, /blog and the
  // homepage — pages that are not a tool. Widening the prerender without fixing it would
  // have put the wrong label on 45 more.
  assert.ok(
    !/this tool/i.test(aiCitation.heading),
    `the heading "${aiCitation.heading}" is page-scoped but renders site-wide`
  );
  assert.match(aiCitation.heading, /FounderConsole/);
});

/**
 * Stand-in for the bundler, so `Footer` can be rendered outside a browser.
 *
 * Vite does two things to `client/src/**` that bare Node does not:
 *
 *   1. Replaces `import.meta.env.X` with a literal. In Node `import.meta.env` is
 *      undefined, so `metaPixel.ts` and `xads.ts` — both reachable from this module
 *      graph — throw while being imported. Substituting an empty object preserves each
 *      module's own "no id configured, stay off" path, which is the path CI wants.
 *   2. Compiles JSX with the automatic runtime. `tsconfig.json` sets `"jsx": "preserve"`,
 *      so tsx falls back to `React.createElement` and only the 7 of 211 client components
 *      that import React by name would load. The prefix restores the binding the build
 *      would have supplied.
 *
 * This is harness, not product: it applies only to `client/src`, and only to modules the
 * render below pulls in.
 */
register(
  "data:text/javascript," +
    encodeURIComponent(`
export async function load(url, context, nextLoad) {
  if (!url.includes("/client/src/")) return nextLoad(url, context);
  const r = await nextLoad(url, context);
  let s = r.source ? r.source.toString() : "";
  if (s.includes("import.meta.env")) {
    s = s.split("import.meta.env").join("(globalThis.__VITE_ENV__||{})");
  }
  if (url.endsWith(".tsx") && !/import\\s*(?:\\*\\s*as\\s+)?React\\b/.test(s)) {
    s = 'import React from "react";\\n' + s;
  }
  return { ...r, source: s, format: r.format || "module" };
}
`)
);
(globalThis as any).__VITE_ENV__ = {};

test("the React footer still renders the block — the absence side", async () => {
  // Nothing else in this file can see this, and neither could the three tests #113
  // shipped: every one of them reads prerendered HTML, and `data-testid` is referenced
  // nowhere but its own definition. Deleting `<CitableSnippet />` from `Footer()` kept
  // the whole suite green while every human lost the block. A testid nothing asserts on
  // is not a guard.
  //
  // Dynamic, not static: the harness above has to be registered before this module graph
  // is loaded.
  const { Footer } = await import("../../client/src/components/marketing/MarketingLayout");

  let tree!: TestRenderer.ReactTestRenderer;
  TestRenderer.act(() => {
    tree = TestRenderer.create(
      // `memoryLocation`, not `ssrPath`: wouter's browser hook reads `location`, which
      // does not exist here. The path is irrelevant — this renders one subtree.
      React.createElement(
        Router,
        { hook: memoryLocation({ path: "/" }).hook },
        React.createElement(Footer)
      )
    );
  });

  const json = JSON.stringify(tree.toJSON());
  assert.ok(
    json.length > 1000,
    `Footer() rendered ${json.length} characters — it did not render, so this proves nothing`
  );
  assert.ok(
    json.includes("footer-ai-citation"),
    'Footer() no longer renders data-testid="footer-ai-citation" — the citation block is ' +
      "gone for every human, however green the prerender looks"
  );
  assert.ok(
    json.includes(aiCitation.heading),
    `the rendered footer does not contain the heading "${aiCitation.heading}"`
  );
  for (const link of aiCitation.links) {
    assert.ok(json.includes(link.href), `the rendered footer does not link ${link.href}`);
  }
});
