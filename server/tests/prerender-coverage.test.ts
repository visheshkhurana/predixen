// Proves the prerenderer emits visible text INSIDE #root for every path that
// was blank before, and that it did not regress the ones that already worked.
import { injectSEO } from "../seo-prerender";
import {
  RUNWAY_INDUSTRIES,
  RUNWAY_RELATED_FREE_TOOLS,
} from "../../client/src/data/runway-industries";

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
    "/auth",
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
    "/auth",
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
    "/auth",
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
    "/auth",
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
    "/auth",
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
    "/auth",
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

// /signup was a blank SPA shell (empty #ssr-content) because the route
// redirected to /auth?tab=register. Body must be non-empty and keep the
// register funnel plus product / free-tool hrefs.
{
  const out = injectSEO(SHELL, "/signup");
  const body = (out.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
  const txt = textOf(out);
  const hrefs = [
    "/auth?tab=register",
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
// restates published FAQ/privacy claims with product / legal / signup hrefs.
{
  const out = injectSEO(SHELL, "/security");
  const body = (out.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/) || [, ""])[1];
  const txt = textOf(out);
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

console.log(failures === 0 ? "\nALL PASS" : `\n${failures} FAILURES`);
process.exit(failures === 0 ? 0 : 1);
