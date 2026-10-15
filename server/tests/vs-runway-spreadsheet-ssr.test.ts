// /vs/runway-calculator-vs-spreadsheet is a public marketing page reached from
// search by someone comparing a runway calculator with a spreadsheet. Without a
// getPageMeta() entry, injectSEO returns the shell untouched — index, follow,
// the HOMEPAGE canonical — so the page would ship as a soft duplicate of "/".
// This pins that the page has its own canonical, a non-empty SSR body inside
// #root, and the free-tool hrefs a crawler needs to follow.
//
// Run: npx tsx --test server/tests/vs-runway-spreadsheet-ssr.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { injectSEO } from "../seo-prerender";

const PATH = "/vs/runway-calculator-vs-spreadsheet";
const CANONICAL = "https://founderconsole.ai" + PATH;
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
  "/tools/runway-calculator",
  "/default-alive",
  "/survival-simulator",
  "/runway/saas",
  "/compare",
  "/features",
  "/pricing",
  "/auth",
];

test("the /vs/ page has its own canonical, not the homepage's", () => {
  const out = injectSEO(SHELL, PATH);
  const canon = (out.match(/rel="canonical" href="([^"]*)"/) || [, ""])[1];
  assert.equal(canon, CANONICAL);
  assert.ok(!out.includes('rel="canonical" href="https://founderconsole.ai/"'), "homepage canonical leaked");
  const robots = (out.match(/name="robots" content="([^"]*)"/) || [, ""])[1];
  assert.match(robots, /index, follow/);
});

test("the SSR body is visible, non-empty and inside #root", () => {
  const out = injectSEO(SHELL, PATH);
  const body = ssrBody(out);
  const text = body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  assert.ok(out.includes('<div id="root"><div id="ssr-content"'), "ssr-content is inside #root");
  assert.ok(!out.includes("left:-9999px"), "body is not off-screen hidden");
  assert.ok(text.length > 200, `visible text too short: ${text.length}`);
  assert.match(body, /<h1>/);
  assert.match(body, /<h1>Runway calculator vs spreadsheet/);
});

test("the SSR body carries every free-tool and product href", () => {
  const body = ssrBody(injectSEO(SHELL, PATH));
  for (const href of REQUIRED_HREFS) {
    assert.ok(body.includes(`href="${href}"`), `missing href ${href}`);
  }
});

test("the title names the comparison rather than the brand alone", () => {
  const out = injectSEO(SHELL, PATH);
  const title = (out.match(/<title>([^<]*)<\/title>/) || [, ""])[1];
  assert.ok(title.length > 10, `title too short: ${title}`);
  assert.match(title, /Runway Calculator vs Spreadsheet/);
  assert.ok(!/<title>FounderConsole - AI Decision Simulator/.test(out), "shell title leaked");
});

test("WebPage and BreadcrumbList JSON-LD point at this page", () => {
  const blocks = jsonLdBlocks(injectSEO(SHELL, PATH));
  const page = blocks.find((b) => (b as { "@type"?: string })["@type"] === "WebPage") as
    | { url?: string }
    | undefined;
  assert.ok(page, "WebPage JSON-LD missing");
  assert.equal(page?.url, CANONICAL);

  const crumb = blocks.find((b) => (b as { "@type"?: string })["@type"] === "BreadcrumbList") as
    | { itemListElement?: { item?: string }[] }
    | undefined;
  assert.ok(crumb, "BreadcrumbList JSON-LD missing");
  assert.equal(crumb?.itemListElement?.[2]?.item, CANONICAL);
});

test("the page does not name a competitor", () => {
  // The page's own closing note promises this; the assertion keeps the promise
  // from drifting when someone later adds a "how we compare to X" row.
  const text = ssrBody(injectSEO(SHELL, PATH)).replace(/<[^>]+>/g, " ").toLowerCase();
  for (const vendor of ["sturppy", "finmark", "causal", "mosaic", "pry", "brex", "lucanet", "excel", "googlesheets", "google sheets", "airtable", "notion"]) {
    assert.ok(!text.includes(vendor), `names a vendor: ${vendor}`);
  }
});
