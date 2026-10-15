// Council 2026-10-15 item 1 - the "Cite this tool" block.
//
// The React footer renders it from `client/src/data/ai-citation.ts`, but the footer only
// exists after the bundle runs and GPTBot does not run it. So the half that matters to an
// AI crawler is the half `buildLandingBodyContent()` emits. This pins that the served
// homepage carries the block, that it names llms.txt, and that its text is the same
// string the footer renders rather than a retyped copy.
//
// Run: npx tsx --test server/tests/ai-citation-ssr.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { injectSEO } from "../seo-prerender";
import { aiCitation } from "../../client/src/data/ai-citation";

const SHELL = readFileSync("client/index.html", "utf8");

function ssrBody(html: string): string {
  const m = html.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/);
  return m ? m[1] : "";
}

test("the served homepage carries the Cite this tool block", () => {
  const out = injectSEO(SHELL, "/");
  const body = ssrBody(out);

  assert.ok(body.length > 0, "no #ssr-content body was emitted for /");
  assert.ok(
    body.includes(`<h2>${aiCitation.heading}</h2>`),
    `ssr body does not contain the citation heading: ${aiCitation.heading}`
  );
  assert.match(body, /Cite this tool/);

  for (const link of aiCitation.links) {
    assert.ok(body.includes(`href="${link.href}"`), `missing citation href ${link.href}`);
  }

  // The pointer to the canonical quotable-figures file is the whole point of the block.
  assert.ok(
    body.includes("https://founderconsole.ai/llms.txt"),
    "the block does not point at llms.txt"
  );
});

test("the crawler copy is the same string the footer renders", () => {
  const body = ssrBody(injectSEO(SHELL, "/"));
  const text = body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

  assert.ok(
    text.includes(`${aiCitation.lede} ${aiCitation.attribution}`),
    "the lede/attribution in the served HTML is not the shared string"
  );
});

test("the block is on the homepage only, not on every prerendered page", () => {
  // `/pricing` has its own bodyContent and the footer hides nothing, but the citation
  // belongs to the page that publishes the figures. If this starts failing, either the
  // block was added centrally in injectSEO or the homepage lost it.
  const pricing = ssrBody(injectSEO(SHELL, "/pricing"));
  assert.ok(pricing.length > 0, "no #ssr-content body was emitted for /pricing");
  assert.ok(
    !pricing.includes("Cite this tool"),
    "/pricing unexpectedly carries the citation block"
  );
});
