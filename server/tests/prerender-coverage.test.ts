// Proves the prerenderer emits visible text INSIDE #root for every path that
// was blank before, and that it did not regress the ones that already worked.
import { injectSEO } from "../seo-prerender";

// The real built shell, not a hand-written stub. injectSEO REPLACES the
// canonical and robots tags rather than inserting them, so a minimal shell
// silently reports "no canonical" for pages that are in fact fine — the first
// version of this test failed all 15 paths for exactly that reason.
import { readFileSync } from "fs";
const SHELL = readFileSync("dist/public/index.html", "utf8");  // run from the repo root

const WAS_BLANK = ["/pricing", "/demo", "/ai-cfo",
  "/runway/saas", "/runway/ecommerce", "/runway/fintech", "/runway/marketplace",
  "/runway/ai", "/runway/hardware", "/runway/biotech", "/runway/devtools",
  "/features", "/about", "/faq", "/contact", "/privacy", "/terms", "/survival-simulator"];
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

console.log(failures === 0 ? "\nALL PASS" : `\n${failures} FAILURES`);
process.exit(failures === 0 ? 0 : 1);
