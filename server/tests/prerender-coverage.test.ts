// Proves the prerenderer emits visible text INSIDE #root for every path that
// was blank before, and that it did not regress the ones that already worked.
import { injectSEO } from "../seo-prerender";
import {
  RUNWAY_INDUSTRIES,
  RUNWAY_RELATED_FREE_TOOLS,
} from "../../client/src/data/runway-industries";
// HAG-311: the REAL post list, the same one the sitemap generator reads. The
// whole point of this section is that it is driven by the client data rather
// than by a second copy, so a post added tomorrow is covered the day it lands.
import { blogPosts } from "../../client/src/data/blog-posts";

// The real built shell, not a hand-written stub. injectSEO REPLACES the
// canonical and robots tags rather than inserting them, so a minimal shell
// silently reports "no canonical" for pages that are in fact fine — the first
// version of this test failed all 15 paths for exactly that reason.
import { readFileSync } from "fs";
const SHELL = readFileSync("dist/public/index.html", "utf8");  // run from the repo root

const WAS_BLANK = ["/pricing", "/demo", "/ai-cfo",
  "/runway/saas", "/runway/ecommerce", "/runway/fintech", "/runway/marketplace",
  "/runway/ai", "/runway/hardware", "/runway/biotech", "/runway/devtools",
  "/features", "/product", "/about", "/compare", "/customers", "/use-cases", "/how-it-works", "/alternatives", "/signup", "/security", "/faq", "/contact", "/privacy", "/terms", "/survival-simulator"];
const ALREADY_WORKED = ["/", "/tools/runway-calculator", "/default-alive", "/blog"];

function textOf(html: string): string {
  const m = html.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/);
  if (!m) return "";
  return m[1].replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

let failures = 0;
for (const group of [WAS_BLANK, ALREADY_WORKED]) {
  for (const path of group) {
    const out = injectSEO(SHELL, path);
    const txt = textOf(out);
    const inside = out.includes('<div id="root"><div id="ssr-content"');
    const hidden = out.includes("left:-9999px");
    const title = (out.match(/<title>([^<]*)<\/title>/) || [, ""])[1];
    const canon = (out.match(/rel="canonical" href="([^"]*)"/) || [, ""])[1];
    const ok = txt.length > 200 && inside && !hidden && title.length > 10 && canon.length > 10;
    if (!ok) failures++;
    console.log(
      `${ok ? "PASS" : "FAIL"}  ${path.padEnd(26)} chars=${String(txt.length).padStart(5)}  inRoot=${inside}  hidden=${hidden}`,
    );
    if (!ok) console.log(`        title=${title} canonical=${canon}`);
  }
}

// An unknown vertical must NOT invite indexing of a 200-status not-found page.
const bogus = injectSEO(SHELL, "/runway/definitely-not-a-vertical");
const noindex = bogus.includes('content="noindex, follow"');
console.log(`${noindex ? "PASS" : "FAIL"}  /runway/<unknown> -> noindex=${noindex}`);
if (!noindex) failures++;

// E10.2: each industry page links the other seven from RUNWAY_INDUSTRIES and
// the reachable handler emits WebApplication JSON-LD (the dead titleMap block
// never did). E10.1 starting-inputs + free-tool hrefs must still be present.
const RUNWAY_PATHS = WAS_BLANK.filter((p) => p.startsWith("/runway/"));
for (const path of RUNWAY_PATHS) {
  const slug = path.slice("/runway/".length);
  const out = injectSEO(SHELL, path);
  const body = (out.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
  const ld = [...out.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
    .map((m) => JSON.parse(m[1]));
  const app = ld.find((b) => b["@type"] === "WebApplication");
  const ind = RUNWAY_INDUSTRIES.find((i) => i.slug === slug);
  const siblingOk = RUNWAY_INDUSTRIES
    .filter((i) => i.slug !== slug)
    .every((i) => body.includes(`href="/runway/${i.slug}"`));
  const toolsOk = RUNWAY_RELATED_FREE_TOOLS.every((t) => body.includes(`href="${t.href}"`));
  const jsonOk = !!app && app.name === ind?.name && app.url === `https://founderconsole.ai/runway/${slug}`;
  const e101 = body.includes("Typical starting inputs") && toolsOk;
  const crumbs = ld.filter((b) => b["@type"] === "BreadcrumbList");
  const crumb = crumbs[0];
  const crumbOk =
    crumbs.length === 1 &&
    crumb?.itemListElement?.[2]?.name === ind?.name &&
    crumb?.itemListElement?.[2]?.item === `https://founderconsole.ai/runway/${slug}` &&
    crumb?.itemListElement?.[1]?.item === "https://founderconsole.ai/tools/runway-calculator";
  const ok = siblingOk && jsonOk && e101 && crumbOk && body.includes("Other industry runway calculators");
  if (!ok) failures++;
  console.log(
    `${ok ? "PASS" : "FAIL"}  ${path.padEnd(26)} siblings=${siblingOk}  jsonLd=${jsonOk}  e10.1=${e101}  crumb=${crumbOk}`,
  );
}

// E10.3: the hub must emit every typed /runway/{slug} (live hub had none)
// without dropping Related free tools.
{
  const out = injectSEO(SHELL, "/tools/runway-calculator");
  const body = (out.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
  const hubLinks = RUNWAY_INDUSTRIES.every((i) => body.includes(`href="/runway/${i.slug}"`));
  const hubTools = body.includes("Related free tools") && body.includes('href="/default-alive"');
  const hubOk = hubLinks && hubTools && body.includes("Industry runway calculators");
  if (!hubOk) failures++;
  console.log(
    `${hubOk ? "PASS" : "FAIL"}  ${"/tools/runway-calculator".padEnd(26)} hubIndustries=${hubLinks}  freeTools=${hubTools}`,
  );
}

// /compare was a blank SPA shell (ssr_chars=0). Body must be non-empty and
// expose the free-tool + blog + features + auth hrefs crawlers should follow.
{
  const out = injectSEO(SHELL, "/compare");
  const body = (out.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
  const txt = textOf(out);
  const hrefs = [
    "/tools/runway-calculator",
    "/survival-simulator",
    "/default-alive",
    "/features",
    "/signup",
    "/blog/founderconsole-vs-sturppy-vs-finmark-vs-causal",
  ];
  const hrefsOk = hrefs.every((h) => body.includes(`href="${h}"`));
  const ld = [...out.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
    .map((m) => JSON.parse(m[1]));
  const page = ld.find((b) => b["@type"] === "WebPage");
  const jsonOk = !!page && page.url === "https://founderconsole.ai/compare";
  const compareOk = txt.length > 200 && hrefsOk && jsonOk && body.includes("<h1>");
  if (!compareOk) failures++;
  console.log(
    `${compareOk ? "PASS" : "FAIL"}  ${"/compare".padEnd(26)} body=${txt.length}  hrefs=${hrefsOk}  jsonLd=${jsonOk}`,
  );
}

// /product was a blank SPA shell (ssr_chars=0). Body must be non-empty and
// expose the features / pricing / compare / free-tool / auth hrefs.
{
  const out = injectSEO(SHELL, "/product");
  const body = (out.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
  const txt = textOf(out);
  const hrefs = [
    "/features",
    "/pricing",
    "/compare",
    "/tools/runway-calculator",
    "/survival-simulator",
    "/default-alive",
    "/signup",
  ];
  const hrefsOk = hrefs.every((h) => body.includes(`href="${h}"`));
  const ld = [...out.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
    .map((m) => JSON.parse(m[1]));
  const page = ld.find((b) => b["@type"] === "WebPage");
  const jsonOk = !!page && page.url === "https://founderconsole.ai/product";
  const productOk = txt.length > 200 && hrefsOk && jsonOk && body.includes("<h1>");
  if (!productOk) failures++;
  console.log(
    `${productOk ? "PASS" : "FAIL"}  ${"/product".padEnd(26)} body=${txt.length}  hrefs=${hrefsOk}  jsonLd=${jsonOk}`,
  );
}

// /customers was a blank SPA shell (ssr_chars=0). Body must be non-empty and
// expose the product / features / compare / pricing / free-tool / auth hrefs.
{
  const out = injectSEO(SHELL, "/customers");
  const body = (out.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
  const txt = textOf(out);
  const hrefs = [
    "/product",
    "/features",
    "/compare",
    "/pricing",
    "/tools/runway-calculator",
    "/survival-simulator",
    "/default-alive",
    "/signup",
  ];
  const hrefsOk = hrefs.every((h) => body.includes(`href="${h}"`));
  const ld = [...out.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
    .map((m) => JSON.parse(m[1]));
  const page = ld.find((b) => b["@type"] === "WebPage");
  const jsonOk = !!page && page.url === "https://founderconsole.ai/customers";
  const customersOk = txt.length > 200 && hrefsOk && jsonOk && body.includes("<h1>");
  if (!customersOk) failures++;
  console.log(
    `${customersOk ? "PASS" : "FAIL"}  ${"/customers".padEnd(26)} body=${txt.length}  hrefs=${hrefsOk}  jsonLd=${jsonOk}`,
  );
}

// /use-cases was a blank SPA shell (ssr_chars=0). Body must be non-empty and
// expose the product / features / free-tool / industry / pricing / auth hrefs.
{
  const out = injectSEO(SHELL, "/use-cases");
  const body = (out.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
  const txt = textOf(out);
  const hrefs = [
    "/product",
    "/features",
    "/tools/runway-calculator",
    "/survival-simulator",
    "/default-alive",
    "/runway/saas",
    "/pricing",
    "/signup",
  ];
  const hrefsOk = hrefs.every((h) => body.includes(`href="${h}"`));
  const ld = [...out.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
    .map((m) => JSON.parse(m[1]));
  const page = ld.find((b) => b["@type"] === "WebPage");
  const jsonOk = !!page && page.url === "https://founderconsole.ai/use-cases";
  const useCasesOk = txt.length > 200 && hrefsOk && jsonOk && body.includes("<h1>");
  if (!useCasesOk) failures++;
  console.log(
    `${useCasesOk ? "PASS" : "FAIL"}  ${"/use-cases".padEnd(26)} body=${txt.length}  hrefs=${hrefsOk}  jsonLd=${jsonOk}`,
  );
}

// /how-it-works was a blank SPA shell (ssr_chars=0). Body must be non-empty and
// expose the product / features / use-cases / free-tool / pricing / auth hrefs.
{
  const out = injectSEO(SHELL, "/how-it-works");
  const body = (out.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
  const txt = textOf(out);
  const hrefs = [
    "/product",
    "/features",
    "/use-cases",
    "/tools/runway-calculator",
    "/survival-simulator",
    "/default-alive",
    "/pricing",
    "/signup",
  ];
  const hrefsOk = hrefs.every((h) => body.includes(`href="${h}"`));
  const ld = [...out.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
    .map((m) => JSON.parse(m[1]));
  const page = ld.find((b) => b["@type"] === "WebPage");
  const jsonOk = !!page && page.url === "https://founderconsole.ai/how-it-works";
  const howItWorksOk = txt.length > 200 && hrefsOk && jsonOk && body.includes("<h1>");
  if (!howItWorksOk) failures++;
  console.log(
    `${howItWorksOk ? "PASS" : "FAIL"}  ${"/how-it-works".padEnd(26)} body=${txt.length}  hrefs=${hrefsOk}  jsonLd=${jsonOk}`,
  );
}

// /alternatives was a blank SPA shell (ssr_chars=0). Body must be non-empty and
// expose the compare / blog / product / free-tool / pricing / auth hrefs.
{
  const out = injectSEO(SHELL, "/alternatives");
  const body = (out.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
  const txt = textOf(out);
  const hrefs = [
    "/compare",
    "/blog/founderconsole-vs-sturppy-vs-finmark-vs-causal",
    "/blog/startup-fpa-tools-acquired-timeline",
    "/blog/finmark-shut-down-alternative",
    "/product",
    "/features",
    "/tools/runway-calculator",
    "/survival-simulator",
    "/default-alive",
    "/pricing",
    "/signup",
  ];
  const hrefsOk = hrefs.every((h) => body.includes(`href="${h}"`));
  const ld = [...out.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
    .map((m) => JSON.parse(m[1]));
  const page = ld.find((b) => b["@type"] === "WebPage");
  const jsonOk = !!page && page.url === "https://founderconsole.ai/alternatives";
  const alternativesOk = txt.length > 200 && hrefsOk && jsonOk && body.includes("<h1>");
  if (!alternativesOk) failures++;
  console.log(
    `${alternativesOk ? "PASS" : "FAIL"}  ${"/alternatives".padEnd(26)} body=${txt.length}  hrefs=${hrefsOk}  jsonLd=${jsonOk}`,
  );
}

// /signup used to be a blank SPA shell (empty #ssr-content) because the route
// redirected to /auth?tab=register. Body must be non-empty and keep the
// register funnel plus product / free-tool hrefs.
{
  const out = injectSEO(SHELL, "/signup");
  const body = (out.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
  const txt = textOf(out);
  const hrefs = [
    "/signup",
    "/product",
    "/features",
    "/pricing",
    "/tools/runway-calculator",
    "/survival-simulator",
    "/default-alive",
  ];
  const hrefsOk = hrefs.every((h) => body.includes(`href="${h}"`));
  const ld = [...out.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
    .map((m) => JSON.parse(m[1]));
  const page = ld.find((b) => b["@type"] === "WebPage");
  const jsonOk = !!page && page.url === "https://founderconsole.ai/signup";
  const signupOk = txt.length > 200 && hrefsOk && jsonOk && body.includes("<h1>");
  if (!signupOk) failures++;
  console.log(
    `${signupOk ? "PASS" : "FAIL"}  ${"/signup".padEnd(26)} body=${txt.length}  hrefs=${hrefsOk}  jsonLd=${jsonOk}`,
  );
}

// /security was a blank SPA shell (ssr_chars=0). Body must be non-empty and
// restates published FAQ/privacy claims with product / legal / register hrefs.
{
  const out = injectSEO(SHELL, "/security");
  const body = (out.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
  const txt = textOf(out);
  // HAG-236 moved this page's "get started free" anchor from /signup to
  // /auth?tab=register; HAG-449 moved every register CTA back to /signup, which
  // now renders the same register form from a prerendered document.
  const hrefs = [
    "/product",
    "/privacy",
    "/terms",
    "/signup",
    "/contact",
  ];
  const hrefsOk = hrefs.every((h) => body.includes(`href="${h}"`));
  const ld = [...out.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
    .map((m) => JSON.parse(m[1]));
  const page = ld.find((b) => b["@type"] === "WebPage");
  const jsonOk = !!page && page.url === "https://founderconsole.ai/security";
  const securityOk = txt.length > 200 && hrefsOk && jsonOk && body.includes("<h1>");
  if (!securityOk) failures++;
  console.log(
    `${securityOk ? "PASS" : "FAIL"}  ${"/security".padEnd(26)} body=${txt.length}  hrefs=${hrefsOk}  jsonLd=${jsonOk}`,
  );
}

// HAG-311. Two blog URLs from the sitemap served "Article not found" with a
// canonical pointing at /blog: HTTP 200, advertises nothing wrong to a status
// check, and tells a search engine to index /blog instead of the post. The
// cause was a SECOND, hand-maintained post list in server/seo-data.ts that had
// fallen two posts behind the real one. It is derived now, so the list cannot
// drift again — and this section is what proves it, per slug, from the same
// data the sitemap generator reads.
//
// It guards both halves of the failure, because they are two different bugs
// wearing the same symptom: a slug missing from the LIST falls through to the
// not-found branch, while a slug present in the list but missing from
// blogPostContent renders an article with a title, a byline and NO BODY.
{
  // The prerenderer escapes into HTML before it renders, so a title carrying a
  // bare & ("Every Startup FP&A Tool Got Acquired") is served as &amp; and a
  // comparison against the raw title fails on a page that is in fact correct.
  // The first version of this check did exactly that and reported 17/18.
  const esc = (s: string) =>
    s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  let blogFailures = 0;
  for (const post of blogPosts) {
    const path = `/blog/${post.slug}`;
    const out = injectSEO(SHELL, path);
    const txt = textOf(out);
    const title = (out.match(/<title>([^<]*)<\/title>/) || [, ""])[1];
    const canon = (out.match(/rel="canonical" href="([^"]*)"/) || [, ""])[1];
    const notFound = out.includes("Article not found");
    const titled = title === `${esc(post.title)} | FounderConsole`;
    const selfCanon = canon === `https://founderconsole.ai${path}`;
    const body = out.includes(`<h1>${esc(post.title)}</h1>`) && txt.length > 200;
    const ok = !notFound && titled && selfCanon && body;
    if (!ok) {
      blogFailures++;
      failures++;
      console.log(`FAIL  ${path}`);
      console.log(`        title=${title}  canonical=${canon}  chars=${txt.length}  notFound=${notFound}`);
    }
  }
  console.log(
    `${blogFailures === 0 ? "PASS" : "FAIL"}  blog posts: ${blogPosts.length - blogFailures}/${blogPosts.length} render their own article, title and self-canonical`,
  );
}

// The count is asserted, not assumed: the loop above can only be as good as the
// list it walks, and a list that silently shrank would pass every assertion in
// it. 18 is the number the sitemap generator writes into client/public/
// sitemap.xml, so this is the join between the two files.
const EXPECTED_BLOG_POSTS = 18;
console.log(
  `${blogPosts.length === EXPECTED_BLOG_POSTS ? "PASS" : "FAIL"}  blog list has ${blogPosts.length} posts (expected ${EXPECTED_BLOG_POSTS}, the count the sitemap is built from)`,
);
if (blogPosts.length !== EXPECTED_BLOG_POSTS) failures++;

// HAG-374. The loop above asserts a FLOOR, and only a floor: the post's <h1> is
// present and the page carries more than 200 characters. That is what it takes
// to catch a page serving "Article not found", and it is all it claims -- a post
// whose body was cut to a single paragraph passes it, and so does an abridged
// override written against the wrong slug.
//
// This section is the other half. For every post, the served body must carry
// EVERY paragraph of the client's own `content` array. Measured at the head
// this was written on: 2 of 18 posts conserved in full, the other 16 being
// served an abridged body from server/seo-data.ts. #131 removed that map, so
// the same check now reads 18 of 18 -- the assertion got stronger, not weaker,
// because there is no longer any post whose body is allowed to differ.
//
// The normalisation below is load-bearing, and it was arrived at by failing.
// Comparing raw strings reports 0 of 18. Two fixtures cause it, and both are
// properties of the renderer rather than losses: the extractor turns every HTML
// tag into a space, so `<strong>x</strong>,` reads back as `x ,`; and a markdown
// link `[t](/u)` is served as the rendered text `t`, never as its source. An
// assertion written naively and then loosened until it went green would have
// shipped a test that proves nothing, which is the failure this file exists to
// catch.
const decodeEntities = (s: string) =>
  s.replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#39;/g, "'")
   .replace(/&lt;/g, "<").replace(/&gt;/g, ">");
// Markdown source -> the characters the prerenderer actually emits: it strips
// the markers (`## `, `**`) and renders a link as its own text.
const stripMarkdown = (s: string) =>
  s.replace(/\[([^\]]*)\]\([^)]*\)/g, "$1").replace(/\*\*/g, "").replace(/^#+\s*/, "");
// Whitespace carries no content here, because every tag collapsed to a space.
const squash = (s: string) => decodeEntities(stripMarkdown(s)).replace(/\s+/g, "");

// The abridged set is PINNED on purpose, and it is EMPTY as of #131.
//
// When this block was written, server/seo-data.ts kept 16 hand-shortened bodies
// as an editorial artifact, a crawler being served the argument rather than the
// whole article. #131 deleted that map: seo-data.ts is now a one-line
// re-export of the client list, so every post is served its own full `content`
// and nothing can be reduced. Measured on the rebased head: 18 of 18 conserve
// in full, 0 reduced.
//
// The list stays, empty, because it is the guard rather than the record: a
// future override that shortens a body has to be declared here and come past
// this test, instead of silently changing what a live page serves.
const ABRIDGED_BY_DESIGN: string[] = [];
{
  const abridged = new Set(ABRIDGED_BY_DESIGN);
  const reduced: string[] = [];
  const unexplained: string[] = [];
  for (const post of blogPosts) {
    const served = squash(textOf(injectSEO(SHELL, `/blog/${post.slug}`)));
    // A shell that failed to extract would report every post as a content loss,
    // which is the loudest possible way to be wrong. Say what it actually is.
    if (served.length < 200) {
      failures++;
      console.log(`FAIL  /blog/${post.slug} extracted ${served.length} chars of body -- cannot judge conservation`);
      continue;
    }
    const missing = post.content.filter((p) => {
      const n = squash(p);
      return n.length > 0 && !served.includes(n);
    });
    if (missing.length === 0) continue;
    reduced.push(post.slug);
    if (abridged.has(post.slug)) continue;
    unexplained.push(post.slug);
    failures++;
    console.log(`FAIL  /blog/${post.slug} serves a REDUCED body and is not abridged by design`);
    console.log(`        ${missing.length} of ${post.content.length} client paragraphs never reach the page`);
    console.log(`        first loss: ${JSON.stringify(missing[0].slice(0, 110))}`);
  }
  console.log(
    `${unexplained.length === 0 ? "PASS" : "FAIL"}  blog conservation: the ${
      blogPosts.length - abridged.size
    } un-abridged posts serve every client paragraph`,
  );

  // The exactness half, and the half a count cannot do. A set that quietly grew
  // would hand a new post an override nobody chose; one that quietly shrank would
  // take an editorial body away from a page that still expects it. Both are named
  // rather than counted.
  const newlyAbridged = reduced.filter((s) => !abridged.has(s));
  const noLongerAbridged = ABRIDGED_BY_DESIGN.filter((s) => !reduced.includes(s));
  const exact = newlyAbridged.length === 0 && noLongerAbridged.length === 0;
  if (!exact) failures++;
  console.log(
    `${exact ? "PASS" : "FAIL"}  abridged set is exactly the ${ABRIDGED_BY_DESIGN.length} pinned (measured ${reduced.length})`,
  );
  if (newlyAbridged.length) console.log(`        abridged but not pinned: ${newlyAbridged.join(", ")}`);
  if (noLongerAbridged.length) console.log(`        pinned but no longer abridged: ${noLongerAbridged.join(", ")}`);
}

// The two slugs Sentinel's golden path caught, named explicitly so the exact
// regression from 2026-10-15 cannot come back under a refactor that happens to
// keep the totals right.
for (const slug of ["what-is-a-good-burn-multiple", "13-week-cash-flow-template"]) {
  const out = injectSEO(SHELL, `/blog/${slug}`);
  const ok = !out.includes("Article not found") && out.includes('rel="canonical" href="https://founderconsole.ai/blog/' + slug + '"');
  console.log(`${ok ? "PASS" : "FAIL"}  golden-path slug /blog/${slug}`);
  if (!ok) failures++;
}

console.log(failures === 0 ? "\nALL PASS" : `\n${failures} FAILURES`);
process.exit(failures === 0 ? 0 : 1);
