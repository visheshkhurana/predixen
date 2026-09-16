// E10.2: sibling /runway links + reachable WebApplication JSON-LD.
// E10.3: hub /tools/runway-calculator lists every RUNWAY_INDUSTRIES slug;
// vertical pages also emit BreadcrumbList alongside WebApplication.
//
// The early path.startsWith("/runway/") handler used to return without jsonLd
// (live ld_count=0). A later block hardcoded known=["saas",...] + titleMap and
// never ran. These cases pin the reachable handler and the typed-array siblings.
//
// Run: npx tsx --test server/tests/runway-industry-ssr.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { injectSEO } from "../seo-prerender";
import {
  RUNWAY_INDUSTRIES,
  RUNWAY_RELATED_FREE_TOOLS,
} from "../../client/src/data/runway-industries";

// client/index.html has the tags injectSEO replaces (title, canonical, robots,
// og/twitter, homepage JSON-LD, #root). Using it means this file does not
// depend on a production build the way prerender-coverage.test.ts does.
const SHELL = readFileSync("client/index.html", "utf8");
const PRERENDER_SRC = readFileSync("server/seo-prerender.ts", "utf8");
const INDUSTRIES_SRC = readFileSync("client/src/data/runway-industries.ts", "utf8");

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

test("the hardcoded slug map is gone — siblings and hub links come from RUNWAY_INDUSTRIES", () => {
  assert.doesNotMatch(PRERENDER_SRC, /runwayIndustryMatch/);
  assert.doesNotMatch(PRERENDER_SRC, /const known = \["saas"/);
  assert.doesNotMatch(PRERENDER_SRC, /titleMap/);
  assert.match(PRERENDER_SRC, /RUNWAY_INDUSTRIES\.filter/);
  assert.match(PRERENDER_SRC, /Industry runway calculators/);
  assert.match(PRERENDER_SRC, /RUNWAY_INDUSTRIES\.map/);
  assert.equal(RUNWAY_INDUSTRIES.length, 8);
  assert.match(INDUSTRIES_SRC, /export const RUNWAY_RELATED_FREE_TOOLS/);
});

test("hub SSR lists every typed industry as /runway/{slug} and keeps Related free tools", () => {
  const out = injectSEO(SHELL, "/tools/runway-calculator");
  const body = ssrBody(out);
  assert.match(body, /Related free tools/);
  assert.match(body, /href="\/default-alive"/);
  assert.match(body, /href="\/survival-simulator"/);
  assert.match(body, /Industry runway calculators/);
  assert.equal(RUNWAY_INDUSTRIES.length, 8);
  for (const industry of RUNWAY_INDUSTRIES) {
    assert.ok(
      body.includes(`href="/runway/${industry.slug}"`),
      `hub must link /runway/${industry.slug} from RUNWAY_INDUSTRIES`,
    );
    assert.ok(
      body.includes(`>${industry.shortName}<`) || body.includes(`>${industry.name}<`),
      `hub link text must be typed name or shortName for ${industry.slug}`,
    );
  }
});

test("every /runway/<slug> page links the other 7 industries and keeps E10.1", () => {
  for (const industry of RUNWAY_INDUSTRIES) {
    const out = injectSEO(SHELL, `/runway/${industry.slug}`);
    const body = ssrBody(out);
    assert.match(body, /Other industry runway calculators/);
    assert.match(body, /Typical starting inputs/);
    assert.match(
      body,
      new RegExp(
        `\\$${industry.defaultBurn.toLocaleString("en-US")}/mo burn`,
      ),
    );
    for (const tool of RUNWAY_RELATED_FREE_TOOLS) {
      assert.ok(
        body.includes(`href="${tool.href}"`),
        `${industry.slug} must keep free-tool href ${tool.href}`,
      );
    }
    assert.ok(body.includes('href="/auth"'), `${industry.slug} must keep /auth`);

    const siblings = RUNWAY_INDUSTRIES.filter((i) => i.slug !== industry.slug);
    assert.equal(siblings.length, 7);
    for (const sib of siblings) {
      assert.ok(
        body.includes(`href="/runway/${sib.slug}"`),
        `${industry.slug} must link sibling /runway/${sib.slug}`,
      );
      assert.ok(
        body.includes(`>${sib.shortName}<`) || body.includes(`>${sib.name}<`),
        `${industry.slug} sibling link text must be typed name or shortName for ${sib.slug}`,
      );
    }
    assert.equal(
      (body.match(new RegExp(`href="/runway/${industry.slug}"`, "g")) || []).length,
      0,
      `${industry.slug} must not self-link in the sibling list`,
    );
  }
});

test("reachable /runway/<slug> handler emits WebApplication JSON-LD from IndustryProfile", () => {
  for (const industry of RUNWAY_INDUSTRIES) {
    const out = injectSEO(SHELL, `/runway/${industry.slug}`);
    const blocks = jsonLdBlocks(out);
    const apps = blocks.filter((b) => (b as { "@type"?: string })["@type"] === "WebApplication");
    assert.equal(apps.length, 1, `${industry.slug} must emit exactly one WebApplication`);
    const app = apps[0] as {
      name: string;
      url: string;
      applicationCategory: string;
      operatingSystem: string;
      offers: { "@type": string; price: string; priceCurrency: string };
    };
    assert.equal(app.name, industry.name);
    assert.equal(app.url, `https://founderconsole.ai/runway/${industry.slug}`);
    assert.equal(app.applicationCategory, "BusinessApplication");
    assert.equal(app.operatingSystem, "Web");
    assert.equal(app.offers["@type"], "Offer");
    assert.equal(app.offers.price, "0");
    assert.equal(app.offers.priceCurrency, "USD");

    const crumbs = blocks.filter((b) => (b as { "@type"?: string })["@type"] === "BreadcrumbList");
    assert.equal(crumbs.length, 1, `${industry.slug} must emit exactly one BreadcrumbList`);
    const crumb = crumbs[0] as {
      itemListElement: Array<{ "@type": string; position: number; name: string; item: string }>;
    };
    assert.equal(crumb.itemListElement.length, 3);
    assert.deepEqual(crumb.itemListElement[0], {
      "@type": "ListItem",
      position: 1,
      name: "Home",
      item: "https://founderconsole.ai/",
    });
    assert.deepEqual(crumb.itemListElement[1], {
      "@type": "ListItem",
      position: 2,
      name: "Runway calculator",
      item: "https://founderconsole.ai/tools/runway-calculator",
    });
    assert.deepEqual(crumb.itemListElement[2], {
      "@type": "ListItem",
      position: 3,
      name: industry.name,
      item: `https://founderconsole.ai/runway/${industry.slug}`,
    });
  }
});

test("unknown /runway/<slug> stays noindex and does not emit industry JSON-LD", () => {
  const out = injectSEO(SHELL, "/runway/definitely-not-a-vertical");
  assert.match(out, /content="noindex, follow"/);
  const blocks = jsonLdBlocks(out);
  const apps = blocks.filter(
    (b) => (b as { "@type"?: string })["@type"] === "WebApplication",
  );
  const crumbs = blocks.filter(
    (b) => (b as { "@type"?: string })["@type"] === "BreadcrumbList",
  );
  assert.equal(apps.length, 0);
  assert.equal(crumbs.length, 0);
});
