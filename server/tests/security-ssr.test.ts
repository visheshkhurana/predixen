// /security was a blank Googlebot shell (ssr_chars=0). Pin a non-empty
// #ssr-content body plus product / privacy / terms / signup / contact hrefs.
// Claims must mirror existing FAQ/privacy/about copy — no invented certs.
//
// Run: npx tsx --test server/tests/security-ssr.test.ts
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
  "/product",
  "/privacy",
  "/terms",
  "/signup",
  "/contact",
];

test("/security SSR body is non-empty and restates published security claims", () => {
  const out = injectSEO(SHELL, "/security");
  const body = ssrBody(out);
  const text = body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

  assert.ok(out.includes('<div id="root"><div id="ssr-content"'), "ssr-content is inside #root");
  assert.ok(!out.includes("left:-9999px"), "body is not off-screen hidden");
  assert.ok(text.length > 200, `visible text too short: ${text.length}`);
  assert.match(body, /<h1>/);
  for (const href of REQUIRED_HREFS) {
    assert.ok(body.includes(`href="${href}"`), `missing href ${href}`);
  }

  assert.match(text, /AES-256/);
  assert.match(text, /TLS/);
  assert.match(text, /HTTPS/);
  assert.match(text, /OAuth2/);
  assert.match(text, /bcrypt/);
  assert.match(text, /US-based PostgreSQL/);
  assert.match(text, /GDPR compliant/i);
  assert.match(text, /working toward SOC2 Type II/i);
  assert.match(text, /never sell your data/i);
  assert.doesNotMatch(text, /SOC2 Type II certified/i);
  assert.doesNotMatch(text, /pen-?test/i);

  const title = (out.match(/<title>([^<]*)<\/title>/) || [, ""])[1];
  const canon = (out.match(/rel="canonical" href="([^"]*)"/) || [, ""])[1];
  assert.ok(title.length > 10, `title too short: ${title}`);
  assert.equal(canon, "https://founderconsole.ai/security");

  const page = jsonLdBlocks(out).find((b) => (b as { "@type"?: string })["@type"] === "WebPage") as
    | { url?: string }
    | undefined;
  assert.ok(page, "WebPage JSON-LD missing");
  assert.equal(page?.url, "https://founderconsole.ai/security");
});
