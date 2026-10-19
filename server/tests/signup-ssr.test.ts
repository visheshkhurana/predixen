// /signup was a blank Googlebot shell (~4.7KB, empty #ssr-content) because
// App.tsx redirected to /auth?tab=register — crawlers never saw body copy.
// Pin a non-empty #ssr-content body plus register / product / free-tool hrefs.
//
// Run: npx tsx --test server/tests/signup-ssr.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { injectSEO } from "../seo-prerender";

const SHELL = readFileSync("client/index.html", "utf8");

function ssrBody(html: string): string {
  const m = html.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/);
  return m ? m[1] : "";
}

function jsonLdBlocks(html: string): object[] {
  const blocks: object[] = [];
  const re = /<script type="application\/ld\+json">([\s\S]*?)<\/script>/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html))) {
    blocks.push(JSON.parse(m[1]));
  }
  return blocks;
}

const REQUIRED_HREFS = [
  "/signup",
  "/product",
  "/features",
  "/pricing",
  "/tools/runway-calculator",
  "/survival-simulator",
  "/default-alive",
];

test("/signup SSR body is non-empty and preserves the register funnel", () => {
  const out = injectSEO(SHELL, "/signup");
  const body = ssrBody(out);
  const text = body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

  assert.ok(out.includes('<div id="root"><div id="ssr-content"'), "ssr-content is inside #root");
  assert.ok(!out.includes("left:-9999px"), "body is not off-screen hidden");
  assert.ok(text.length > 200, `visible text too short: ${text.length}`);
  assert.match(body, /<h1>/);
  for (const href of REQUIRED_HREFS) {
    assert.ok(body.includes(`href="${href}"`), `missing href ${href}`);
  }
  assert.match(text, /free — all features/i);
  assert.match(text, /no credit card/i);
  assert.match(text, /create a free account/i);

  const title = (out.match(/<title>([^<]*)<\/title>/) || [, ""])[1];
  const canon = (out.match(/rel="canonical" href="([^"]*)"/) || [, ""])[1];
  assert.ok(title.length > 10, `title too short: ${title}`);
  assert.equal(canon, "https://founderconsole.ai/signup");

  const page = jsonLdBlocks(out).find((b) => (b as { "@type"?: string })["@type"] === "WebPage") as
    | { url?: string }
    | undefined;
  assert.ok(page, "WebPage JSON-LD missing");
  assert.equal(page?.url, "https://founderconsole.ai/signup");
});

// FounderConsole is free: /pricing prerenders a single Free plan and its
// JSON-LD carries one Offer at price 0 — no paid tier prices for crawlers.
test("/pricing SSR states the single Free plan with an Offer at price 0", () => {
  const out = injectSEO(SHELL, "/pricing");
  const text = ssrBody(out).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  assert.match(text, /Free — all features, no credit card/);
  assert.doesNotMatch(text, /\$(29|49|99)\b/);
  assert.doesNotMatch(text, /trial clock running|after the beta|paid tiers will/i);
  const offers = jsonLdBlocks(out)
    .map((b) => (b as { offers?: { price?: string; name?: string } }).offers)
    .filter(Boolean) as { price?: string; name?: string }[];
  assert.ok(offers.length >= 1, "pricing JSON-LD has an Offer");
  for (const o of offers) assert.equal(o.price, "0");
});
