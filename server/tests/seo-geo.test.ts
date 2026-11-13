// SEO / GEO behaviour of the server-rendered HTML.
//
//   1. Logged-in app routes (/overview, /settings, ...) are `noindex, follow`
//      with no canonical and no structured data, instead of a 200 duplicate of
//      the homepage with `index, follow`.
//   2. The homepage carries Organization, WebSite, SoftwareApplication (price 0)
//      and FAQPage JSON-LD.
//   3. Blog posts carry BlogPosting + BreadcrumbList.
//   4. /llms-full.txt is llms.txt plus every post, with absolute links.
//   5. Marketing routes keep their own titles; HAG-471 pins /demo and /pricing.
//
// Run: npx tsx --test server/tests/seo-geo.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { renderHtmlPage } from "../seo-prerender";
import { decideShellResponse } from "../static";
import { buildLlmsFull } from "../llms-full";
import { blogPosts } from "../../client/src/data/blog-posts";

const SHELL = readFileSync("client/index.html", "utf8");
const LLMS = readFileSync("client/public/llms.txt", "utf8");

function ldTypes(html: string): string[] {
  return [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(
    (m) => JSON.parse(m[1])["@type"],
  );
}

test("app routes are noindex with no canonical and no JSON-LD", () => {
  for (const path of ["/overview", "/settings", "/scenarios", "/login"]) {
    const d = decideShellResponse(SHELL, path);
    assert.equal(d.status, 200, path);
    assert.match(d.html, /<meta name="robots" content="noindex, follow" \/>/, path);
    assert.doesNotMatch(d.html, /rel="canonical"/, path);
    assert.deepEqual(ldTypes(d.html), [], path);
    assert.match(d.html, /<div id="root"><\/div>/, `${path} must still boot the SPA`);
  }
});

test("homepage JSON-LD: Organization, WebSite, SoftwareApplication (free), FAQPage", () => {
  const html = renderHtmlPage(SHELL, "/").html;
  const types = ldTypes(html);
  for (const t of ["Organization", "WebSite", "SoftwareApplication", "FAQPage"]) {
    assert.ok(types.includes(t), `homepage is missing ${t}: ${types}`);
  }
  assert.match(html, /"price":"0"/);
  assert.match(html, /<meta name="robots" content="index, follow" \/>/);
  assert.match(html, /D2C brands/);
});

test("blog posts carry BlogPosting and BreadcrumbList", () => {
  for (const post of blogPosts) {
    const html = renderHtmlPage(SHELL, `/blog/${post.slug}`).html;
    const types = ldTypes(html);
    assert.ok(types.includes("BlogPosting"), post.slug);
    assert.ok(types.includes("BreadcrumbList"), post.slug);
  }
});

test("HAG-471 titles are unchanged", () => {
  assert.match(renderHtmlPage(SHELL, "/demo").html, /<title>Demo \| FounderConsole<\/title>/);
  assert.match(renderHtmlPage(SHELL, "/pricing").html, /<title>Pricing \| FounderConsole<\/title>/);
});

test("llms-full.txt is llms.txt plus every post, with absolute links", () => {
  const full = buildLlmsFull(LLMS);
  assert.ok(full.startsWith(LLMS.trimEnd()));
  for (const post of blogPosts) {
    assert.ok(full.includes(`URL: https://founderconsole.ai/blog/${post.slug}`), post.slug);
  }
  assert.doesNotMatch(full, /\]\(\/[a-z]/, "a relative markdown link survived");
  assert.match(full, /\]\(https:\/\/founderconsole\.ai\/tools\/d2c-contribution-margin\)/);
});
