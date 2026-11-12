// Industry homepages (`/for/<slug>`) and the homepage industry picker.
//
//   1. Every INDUSTRY_PAGES entry has a client route, a known-route entry, SSR meta
//      (title, description, canonical, JSON-LD incl. FAQPage), a visible SSR body
//      and a sitemap entry. Adding an industry is one config entry; this proves the
//      rest follows from it.
//   2. `/` and every variant have distinct titles and canonicals.
//   3. Unknown `/for/<x>` is a real 404, not a soft one.
//   4. The picker is never shown to crawlers: the SSR HTML has no picker markup, and
//      the client gate refuses bot UAs, deep links, `?industry=` and returning visitors.
//   5. The copy respects the published facts: no planned prices, no retired trial
//      offer, no stale connector count, no invented customer counts; every connector
//      named is registered, every link resolves to a real public page.
//   6. Onboarding prefill maps only to values the onboarding Industry select offers.
//
// Run: npx tsx --test server/tests/industry-homepage.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { renderHtmlPage } from "../seo-prerender";
import { isKnownAppRoute } from "../known-routes";
import {
  INDUSTRY_PAGES,
  INDUSTRY_SKIPPED,
  SITE_URL,
  getIndustryPage,
  industryPath,
  industrySignupHref,
} from "../../client/src/data/industry-pages";
import {
  isBotUserAgent,
  onboardingIndustryPrefill,
  shouldShowIndustryPicker,
  type PickerContext,
} from "../../client/src/lib/industryPicker";
import { blogPosts } from "../../client/src/data/blog-posts";
import { PUBLIC_ROUTES } from "../../scripts/generate-sitemap";

const SHELL = readFileSync("client/index.html", "utf8");
const APP = readFileSync("client/src/App.tsx", "utf8");
const SITEMAP = readFileSync("client/public/sitemap.xml", "utf8");
const ONBOARDING = readFileSync("client/src/pages/onboarding.tsx", "utf8");
const CONFIG_SOURCE = readFileSync("client/src/data/industry-pages.ts", "utf8");
const CONNECTOR_INIT = readFileSync("server/connectors/__init__.py", "utf8");

function meta(html: string) {
  return {
    title: (html.match(/<title>([^<]*)<\/title>/) || [, ""])[1],
    canonical: (html.match(/<link rel="canonical" href="([^"]*)"/) || [, ""])[1],
    description: (html.match(/<meta name="description" content="([^"]*)"/) || [, ""])[1],
    robots: (html.match(/<meta name="robots" content="([^"]*)"/) || [, ""])[1],
  };
}

function ldBlocks(html: string): any[] {
  return [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((m) => JSON.parse(m[1]));
}

function ssrBody(html: string): string {
  return (html.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
}

const unescape = (s: string) =>
  s.replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">");

test("the config has six industries with unique slugs", () => {
  const slugs = INDUSTRY_PAGES.map((p) => p.slug);
  assert.equal(new Set(slugs).size, slugs.length, "duplicate slug");
  assert.ok(slugs.length >= 6, `expected at least 6 industries, got ${slugs.length}`);
  for (const required of ["d2c", "saas", "marketplace", "agency", "fintech", "startup"]) {
    assert.ok(slugs.includes(required), `missing ${required}`);
  }
  for (const p of INDUSTRY_PAGES) {
    assert.match(p.slug, /^[a-z0-9-]+$/, p.slug);
    assert.ok(p.pains.length >= 3 && p.pains.length <= 4, `${p.slug}: 3-4 pain points`);
    assert.ok(p.faqs.length >= 3, `${p.slug}: at least 3 FAQs`);
    assert.ok(p.metrics.length >= 4, `${p.slug}: metrics strip`);
  }
});

test("every industry has a client route and is a known app route", () => {
  assert.match(APP, /<Route path="\/for\/:slug">/, "App.tsx must register /for/:slug");
  for (const p of INDUSTRY_PAGES) {
    assert.ok(isKnownAppRoute(industryPath(p.slug)), `${p.slug} is not a known route`);
  }
});

test("every industry is prerendered with its own meta, JSON-LD and visible body", () => {
  for (const p of INDUSTRY_PAGES) {
    const { status, html } = renderHtmlPage(SHELL, industryPath(p.slug));
    const m = meta(html);
    assert.equal(status, 200, p.slug);
    assert.equal(unescape(m.title), p.title, `${p.slug} title`);
    assert.equal(unescape(m.description), p.description, `${p.slug} description`);
    assert.equal(m.canonical, `${SITE_URL}/for/${p.slug}`, `${p.slug} canonical`);
    assert.equal(m.robots, "index, follow", `${p.slug} robots`);
    assert.ok(p.title.length <= 95, `${p.slug} title is ${p.title.length} chars`);

    const ld = ldBlocks(html);
    const types = ld.map((b) => b["@type"]);
    for (const t of ["WebPage", "BreadcrumbList", "FAQPage"]) {
      assert.ok(types.includes(t), `${p.slug} missing ${t} JSON-LD: ${types}`);
    }
    const faq = ld.find((b) => b["@type"] === "FAQPage");
    assert.equal(faq.mainEntity.length, p.faqs.length, `${p.slug} FAQPage count`);
    assert.equal(faq.mainEntity[0].name, p.faqs[0].q);
    const webPage = ld.find((b) => b["@type"] === "WebPage");
    assert.equal(webPage.url, `${SITE_URL}/for/${p.slug}`);
    assert.equal(webPage.about.offers.price, "0");

    const body = ssrBody(html);
    const text = unescape(body);
    assert.ok(body.length > 1500, `${p.slug} SSR body is only ${body.length} chars`);
    assert.ok(text.includes(p.headline), `${p.slug} SSR body lacks the headline`);
    assert.ok(text.includes(p.subhead), `${p.slug} SSR body lacks the subhead`);
    assert.ok(body.includes(`href="${industrySignupHref(p.slug)}"`), `${p.slug} CTA must carry industry=`);
    for (const f of p.faqs) assert.ok(text.includes(f.q), `${p.slug} SSR body lacks FAQ ${f.q}`);
    for (const l of p.links) assert.ok(body.includes(`href="${l.href}"`), `${p.slug} SSR body lacks ${l.href}`);
    for (const pain of p.pains) assert.ok(text.includes(pain.feature), `${p.slug} lacks ${pain.feature}`);
  }
});

test("the CTA carries industry=<slug> to signup", () => {
  for (const p of INDUSTRY_PAGES) {
    assert.equal(industrySignupHref(p.slug), `/signup?industry=${p.slug}`);
  }
});

test("every industry is in the sitemap and in the generator's route list", () => {
  const declared = new Set(PUBLIC_ROUTES.map((r) => r.path));
  for (const p of INDUSTRY_PAGES) {
    assert.ok(declared.has(`/for/${p.slug}`), `${p.slug} not declared in PUBLIC_ROUTES`);
    assert.ok(SITEMAP.includes(`<loc>${SITE_URL}/for/${p.slug}</loc>`), `${p.slug} missing from sitemap.xml`);
  }
});

test("/ and every variant have distinct titles and canonicals; / still links them all", () => {
  const paths = ["/", ...INDUSTRY_PAGES.map((p) => industryPath(p.slug))];
  const metas = paths.map((path) => meta(renderHtmlPage(SHELL, path).html));
  assert.equal(new Set(metas.map((m) => m.title)).size, paths.length, "titles must be distinct");
  assert.equal(new Set(metas.map((m) => m.canonical)).size, paths.length, "canonicals must be distinct");
  const home = renderHtmlPage(SHELL, "/").html;
  for (const p of INDUSTRY_PAGES) {
    assert.ok(ssrBody(home).includes(`href="/for/${p.slug}"`), `/ does not link /for/${p.slug}`);
  }
});

test("unknown or nested industry slugs are a real 404", () => {
  for (const path of ["/for/not-an-industry", "/for/saas/extra", "/for/"]) {
    const { status, html } = renderHtmlPage(SHELL, path);
    if (path === "/for/") continue; // stripped to "/for", which is not an app route (static 404s it)
    assert.equal(status, 404, path);
    assert.equal(meta(html).robots, "noindex, follow", path);
  }
  assert.equal(isKnownAppRoute("/for"), false);
});

/* ----------------------------- picker / crawlers ----------------------------- */

const HUMAN_UAS = [
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
  "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
  "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
];
const BOT_UAS = [
  "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)",
  "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
  "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
  "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
  "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot",
  "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
  "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/131.0.0.0 Safari/537.36",
  "curl/8.7.1",
  "",
];

const firstVisit: PickerContext = {
  userAgent: HUMAN_UAS[0],
  pathname: "/",
  search: "",
  hash: "",
  stored: null,
  dismissedThisSession: false,
};

test("bot user agents are detected, real browsers are not", () => {
  for (const ua of HUMAN_UAS) assert.equal(isBotUserAgent(ua), false, ua);
  for (const ua of BOT_UAS) assert.equal(isBotUserAgent(ua), true, ua);
});

test("the picker opens only for a human's first visit to the bare homepage", () => {
  for (const ua of HUMAN_UAS) assert.equal(shouldShowIndustryPicker({ ...firstVisit, userAgent: ua }), true, ua);
  for (const ua of BOT_UAS) assert.equal(shouldShowIndustryPicker({ ...firstVisit, userAgent: ua }), false, `bot: ${ua}`);
  assert.equal(shouldShowIndustryPicker({ ...firstVisit, search: "?industry=saas" }), false, "?industry=");
  assert.equal(shouldShowIndustryPicker({ ...firstVisit, search: "?industry=bogus" }), false, "?industry=bogus");
  assert.equal(shouldShowIndustryPicker({ ...firstVisit, hash: "#faq" }), false, "anchor deep link");
  for (const path of ["/pricing", "/for/saas", "/blog/timing-series-a", "/tools/runway-calculator"]) {
    assert.equal(shouldShowIndustryPicker({ ...firstVisit, pathname: path }), false, path);
  }
  assert.equal(shouldShowIndustryPicker({ ...firstVisit, stored: "saas" }), false, "returning visitor");
  assert.equal(shouldShowIndustryPicker({ ...firstVisit, stored: INDUSTRY_SKIPPED }), false, "skipped");
  assert.equal(shouldShowIndustryPicker({ ...firstVisit, dismissedThisSession: true }), false, "dismissed");
  assert.equal(shouldShowIndustryPicker({ ...firstVisit, search: "?utm_source=x" }), true, "utm params are fine");
});

test("no picker markup in the server-rendered HTML a crawler receives", () => {
  // SSR output does not depend on the user agent; GPTBot and a browser get the same
  // document. The picker is mounted client-side only, behind the bot check above.
  for (const path of ["/", ...INDUSTRY_PAGES.map((p) => industryPath(p.slug))]) {
    const html = renderHtmlPage(SHELL, path).html;
    assert.doesNotMatch(html, /industry-picker/, path);
    assert.doesNotMatch(html, /What kind of business do you run/, path);
    assert.doesNotMatch(html, /role="dialog"/, path);
  }
});

/* ---------------------------------- facts ---------------------------------- */

test("no planned prices, retired offers, stale counts or invented social proof", () => {
  const forbidden = [
    "$29", "$49", "$99", "30-day", "Start Free Trial", "free trial",
    "37 data connector", "37 connectors", "37 read-only", "37 integrations",
    "trusted by", "Trusted by", "testimonial", "loved by", "used by",
  ];
  const copy = JSON.stringify(INDUSTRY_PAGES);
  for (const phrase of forbidden) assert.ok(!copy.includes(phrase), `config contains ${phrase}`);
  // Any connector count stated is 34.
  for (const m of copy.matchAll(/(\d+)\s+(?:read-only\s+)?(?:data\s+)?connectors/g)) {
    assert.equal(m[1], "34", `connector count ${m[0]}`);
  }
  // No "N founders/brands/companies/customers use ..." style counts.
  assert.doesNotMatch(copy, /\b\d[\d,.]*\+?\s*(founders|brands|companies|customers|startups|teams)\b/i);
  // Every page states the free beta.
  for (const p of INDUSTRY_PAGES) {
    assert.ok(/free during (the )?public beta/i.test(JSON.stringify(p)), `${p.slug} must state free during beta`);
  }
  // The config file itself (comments included) carries no planned price.
  assert.ok(!CONFIG_SOURCE.includes("$29"));
});

test("every connector named is a registered connector", () => {
  const registered = new Set([...CONNECTOR_INIT.matchAll(/"([a-z_]+)"/g)].map((m) => m[1]));
  for (const p of INDUSTRY_PAGES) {
    for (const name of p.connectors) {
      const id = name.toLowerCase().replace(/\s+/g, "_");
      assert.ok(registered.has(id), `${p.slug}: connector ${name} (${id}) is not registered`);
    }
  }
});

test("every link points at a real public page", () => {
  const slugs = new Set(blogPosts.map((b) => b.slug));
  const publicPaths = new Set(PUBLIC_ROUTES.map((r) => r.path));
  for (const p of INDUSTRY_PAGES) {
    const hrefs = [...p.links.map((l) => l.href), ...p.pains.flatMap((x) => (x.href ? [x.href] : []))];
    for (const href of hrefs) {
      if (href.startsWith("/blog/")) {
        assert.ok(slugs.has(href.slice("/blog/".length)), `${p.slug}: no blog post ${href}`);
        const status = renderHtmlPage(SHELL, href).status;
        assert.equal(status, 200, `${p.slug}: ${href} is ${status}`);
      } else {
        assert.ok(publicPaths.has(href), `${p.slug}: ${href} is not a public (sitemapped) page`);
      }
    }
  }
});

test("D2C links the calculator and the D2C posts", () => {
  const d2c = getIndustryPage("d2c")!;
  const hrefs = d2c.links.map((l) => l.href);
  assert.ok(hrefs.includes("/tools/d2c-contribution-margin"));
  const d2cPosts = blogPosts.filter((b) => /d2c/.test(b.slug)).map((b) => `/blog/${b.slug}`);
  assert.ok(d2cPosts.length >= 6);
  for (const post of d2cPosts) assert.ok(hrefs.includes(post), `D2C page should link ${post}`);
});

/* -------------------------------- onboarding -------------------------------- */

test("onboarding prefill maps only to values the Industry select offers", () => {
  const offered = new Set([...ONBOARDING.matchAll(/<SelectItem value="([a-z0-9_]+)">/g)].map((m) => m[1]));
  for (const p of INDUSTRY_PAGES) {
    if (p.onboardingIndustry) assert.ok(offered.has(p.onboardingIndustry), `${p.slug} -> ${p.onboardingIndustry}`);
  }
  assert.equal(onboardingIndustryPrefill("?industry=saas", null), "general_saas");
  assert.equal(onboardingIndustryPrefill("", "d2c"), "d2c");
  assert.equal(onboardingIndustryPrefill("?industry=fintech", "d2c"), "fintech", "param wins");
  assert.equal(onboardingIndustryPrefill("", null), "");
  assert.equal(onboardingIndustryPrefill("", INDUSTRY_SKIPPED), "");
  assert.equal(onboardingIndustryPrefill("?industry=nope", null), "");
});

test("homepage meta is unchanged and consistent across shell, prerender and landing", () => {
  const home = meta(renderHtmlPage(SHELL, "/").html);
  const landing = readFileSync("client/src/pages/landing.tsx", "utf8");
  assert.equal(home.title, "FounderConsole — AI Decision Simulator for Founders");
  // The raw shell spells the dash as "-" (pre-existing, before this change); crawlers
  // never see it because the prerender rewrites the title. Compare modulo the dash.
  const shellTitle = (SHELL.match(/<title>([^<]*)<\/title>/) || [, ""])[1];
  assert.equal(shellTitle.replace(" - ", " — "), home.title, "shell title");
  assert.ok(SHELL.includes(`content="${home.description}"`), "shell description");
  assert.ok(landing.includes(`title: "${home.title}"`), "landing title");
  assert.ok(landing.includes(unescape(home.description)), "landing description matches prerender");
  assert.equal(home.canonical, `${SITE_URL}/`);
});
