/**
 * Regenerate client/public/sitemap.xml from the routes the app actually serves.
 *
 * Why this exists (HAG-204): the sitemap was hand-maintained, so a page could ship
 * without ever appearing in it. Both blog posts added in PR #72 are the live example -
 * the day that PR merges, the hand-maintained file is two entries behind. A two-entry
 * hand-patch is not a fix either: on a `main` base those two posts have no page yet, so
 * the patch would list two URLs that 404. Generation is the only correct fix.
 *
 * What is generated and what is not, stated plainly:
 *
 *   - Every BLOG route is generated from `client/src/data/blog-posts.ts`. Add a post
 *     there and its entry appears; remove one and its entry goes away.
 *   - Every non-blog route is generated from `PUBLIC_ROUTES` below. Add a route there
 *     and its entry appears in the file; the generator no longer depends on someone
 *     remembering to hand-edit the XML.
 *
 * `PUBLIC_ROUTES` is declared here rather than derived, because the app has no single
 * route manifest to derive it from. What keeps it honest is the test half, in
 * `server/tests/sitemap-drift.test.ts`: every declared path must be a route
 * `client/src/App.tsx` actually registers (literally, or through a dynamic parent such
 * as `/runway/:slug`), and every non-blog `<loc>` in the file must be declared. The
 * remaining gap, stated rather than hidden: a route that is registered in App.tsx but
 * never declared here is not detected, so adding a page is still two edits - the
 * `<Route>` and its entry below. That gap is what Sentinel found in the posts-only
 * version of this generator (M1, `hive/reports/sentinel-review-pr79.md`); it is now one
 * line of data per page instead of a hand-edit of the XML, and the two checks above stop
 * the list and the file drifting apart in either direction.
 *
 * Existing entries are preserved byte for byte. In particular `lastmod` is NOT the
 * post's `date` field: 5 of the 16 published posts have a `lastmod` that differs from
 * their `date` (they were edited after publication), so re-deriving `lastmod` from
 * `date` would silently rewrite 5 entries. A newly added post has no existing entry, so
 * its `lastmod` is derived from its `date` - that is the only place a date is used.
 *
 * Run `npm run generate:sitemap` to rewrite the file, or import this module - the CLI
 * guard below means importing it has no side effects.
 */

import { readFileSync, writeFileSync } from "fs";
import { resolve } from "path";
import { fileURLToPath } from "url";

// The `.ts` extension is explicit on purpose: `tsx` and esbuild resolve an
// extensionless specifier, but plain `node` (which strips types itself) does not.
// scripts/ is outside tsconfig's `include` and is never bundled, so this costs nothing.
import { blogPosts } from "../client/src/data/blog-posts.ts";

export const ORIGIN = "https://founderconsole.ai";
export const BLOG_PREFIX = "/blog/";

export const ROOT = resolve(fileURLToPath(new URL(".", import.meta.url)), "..");
export const POSTS_FILE = resolve(ROOT, "client/src/data/blog-posts.ts");
export const SITEMAP_FILE = resolve(ROOT, "client/public/sitemap.xml");

/**
 * The number of `<loc>` entries main carries today: 44 = 36 multi-line entries plus the
 * 8 single-line `/runway/*` ones. The drift test asserts the file never drops below it,
 * so a generator bug cannot quietly delete a route that is still being served.
 */
export const SITEMAP_LOC_FLOOR = 44;

export interface PublicRoute {
  /** Path only, no origin: `/features`, `/tools/runway-calculator`. */
  path: string;
  /**
   * Used ONLY when the entry has to be created. An entry already in the file keeps the
   * `lastmod` it has, byte for byte - so editing this value never rewrites the sitemap.
   */
  lastmod: string;
  changefreq: string;
  priority: string;
}

/**
 * Every non-blog route the app serves to the public. This is the list the generator
 * writes entries for; see the docblock for what keeps it in step with `App.tsx`.
 *
 * Deliberately absent: the app's authenticated routes (`/dashboard`, `/settings`, ...),
 * `/login`-style aliases, and anything under `App.tsx`'s private Switch. A sitemap lists
 * pages a crawler may index, not every path wouter can match.
 */
export const PUBLIC_ROUTES: readonly PublicRoute[] = [
  { path: "/", lastmod: "2026-03-17", changefreq: "weekly", priority: "1.0" },
  { path: "/features", lastmod: "2026-03-17", changefreq: "monthly", priority: "0.8" },
  { path: "/product", lastmod: "2026-09-16", changefreq: "monthly", priority: "0.8" },
  { path: "/ai-cfo", lastmod: "2026-09-16", changefreq: "monthly", priority: "0.8" },
  { path: "/pricing", lastmod: "2026-03-17", changefreq: "monthly", priority: "0.7" },
  { path: "/about", lastmod: "2026-03-17", changefreq: "monthly", priority: "0.7" },
  { path: "/compare", lastmod: "2026-09-16", changefreq: "monthly", priority: "0.7" },
  { path: "/customers", lastmod: "2026-09-16", changefreq: "monthly", priority: "0.7" },
  { path: "/use-cases", lastmod: "2026-09-16", changefreq: "monthly", priority: "0.7" },
  { path: "/how-it-works", lastmod: "2026-09-16", changefreq: "monthly", priority: "0.7" },
  { path: "/alternatives", lastmod: "2026-09-16", changefreq: "monthly", priority: "0.7" },
  { path: "/signup", lastmod: "2026-09-16", changefreq: "monthly", priority: "0.7" },
  { path: "/security", lastmod: "2026-09-16", changefreq: "monthly", priority: "0.7" },
  { path: "/blog", lastmod: "2026-08-10", changefreq: "weekly", priority: "0.8" },
  { path: "/default-alive", lastmod: "2026-08-08", changefreq: "monthly", priority: "0.9" },
  { path: "/faq", lastmod: "2026-03-17", changefreq: "monthly", priority: "0.5" },
  // HAG-449: the hub itself. The four leaves below were in the sitemap while the
  // page they hang off returned 404, so a crawler had the tools and no index.
  { path: "/tools", lastmod: "2026-10-19", changefreq: "monthly", priority: "0.9" },
  { path: "/tools/runway-calculator", lastmod: "2026-03-17", changefreq: "monthly", priority: "0.8" },
  { path: "/tools/burn-multiple", lastmod: "2026-10-15", changefreq: "monthly", priority: "0.8" },
  { path: "/tools/dilution", lastmod: "2026-10-15", changefreq: "monthly", priority: "0.8" },
  { path: "/tools/ltv-cac", lastmod: "2026-10-15", changefreq: "monthly", priority: "0.8" },
  { path: "/vs/runway-calculator-vs-spreadsheet", lastmod: "2026-10-15", changefreq: "monthly", priority: "0.8" },
  { path: "/contact", lastmod: "2026-03-17", changefreq: "monthly", priority: "0.5" },
  { path: "/demo", lastmod: "2026-03-17", changefreq: "monthly", priority: "0.6" },
  { path: "/survival-simulator", lastmod: "2026-03-17", changefreq: "monthly", priority: "0.6" },
  { path: "/runway/saas", lastmod: "2026-05-13", changefreq: "monthly", priority: "0.8" },
  { path: "/runway/ecommerce", lastmod: "2026-05-13", changefreq: "monthly", priority: "0.8" },
  { path: "/runway/fintech", lastmod: "2026-05-13", changefreq: "monthly", priority: "0.8" },
  { path: "/runway/marketplace", lastmod: "2026-05-13", changefreq: "monthly", priority: "0.8" },
  { path: "/runway/ai", lastmod: "2026-05-13", changefreq: "monthly", priority: "0.8" },
  { path: "/runway/hardware", lastmod: "2026-05-13", changefreq: "monthly", priority: "0.8" },
  { path: "/runway/biotech", lastmod: "2026-05-13", changefreq: "monthly", priority: "0.8" },
  { path: "/runway/devtools", lastmod: "2026-05-13", changefreq: "monthly", priority: "0.8" },
];

const HEADER =
  '<?xml version="1.0" encoding="UTF-8"?>\n' +
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';
const FOOTER = "</urlset>\n";

/** Shape used for a blog entry this generator has to create (matches the newest ones). */
const BLOG_CHANGEFREQ = "monthly";
const BLOG_PRIORITY = "0.8";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

export interface SitemapEntry {
  /** The `<loc>` value, e.g. `https://founderconsole.ai/blog/board-deck-30-minutes`. */
  loc: string;
  /** The entry exactly as it appears in the file, without its trailing newline. */
  block: string;
}

export interface Post {
  slug: string;
  /** ISO `YYYY-MM-DD`, parsed from the post's human date. */
  date: string;
}

export interface SyncResult {
  xml: string;
  added: string[];
  removed: string[];
  /** Declared non-blog paths that had no entry and were added, in declaration order. */
  addedRoutes: string[];
}

/**
 * Split a sitemap file into its `<url>` entries, verbatim, in file order.
 *
 * This is deliberately a *strict* parse. It is line-based, so a tag it does not expect
 * between `<url>` and `</url>` is carried inside the entry's bytes rather than rejected -
 * which is exactly how a malformed file slipped past this module, the drift test and
 * `generateSitemap()` at once (2026-10-15, the `#107` rebase: git auto-merged both
 * sides' new `<url>` block at the same anchor and produced two opening tags against one
 * closing one). The file stopped being parseable XML - `ET.parse` reported
 * `mismatched tag` - while every check still read "ok", because the stray tag was
 * absorbed into a neighbouring entry, the entry count never moved, and the round trip
 * reproduced the damaged bytes exactly.
 *
 * So the two structural shapes a bad merge produces are rejected here rather than
 * tolerated: a `<url>` that is never closed before the next `<url>` opens, and a block
 * carrying more than one `<loc>`. Both name the line they are on, because the caller's
 * only sane next move is to look at that line.
 */
export function parseSitemap(xml: string): SitemapEntry[] {
  const opens = xml.match(/<url>/g)?.length ?? 0;
  const closes = xml.match(/<\/url>/g)?.length ?? 0;
  if (opens !== closes) {
    throw new Error(
      `sitemap: ${opens} <url> tags open but ${closes} close - the file is not ` +
        `well-formed XML (this is what a bad auto-merge looks like)`,
    );
  }

  const lines = xml.split("\n");
  const entries: SitemapEntry[] = [];

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim();

    // A whole entry on one line, e.g. every /runway/* entry.
    if (trimmed.startsWith("<url>") && trimmed.endsWith("</url>")) {
      entries.push({ loc: locOf(lines[i], i + 1), block: lines[i] });
      continue;
    }

    // An entry spread over several lines, e.g. every blog entry.
    if (trimmed === "<url>") {
      const block: string[] = [];
      let j = i;
      for (; j < lines.length; j++) {
        if (j > i && lines[j].trim() === "<url>") {
          throw new Error(
            `sitemap: <url> opened at line ${i + 1} is not closed before another ` +
              `<url> at line ${j + 1}`,
          );
        }
        block.push(lines[j]);
        if (lines[j].trim() === "</url>") break;
      }
      if (j === lines.length) {
        throw new Error(`sitemap: unterminated <url> opened at line ${i + 1}`);
      }
      i = j;
      const text = block.join("\n");
      entries.push({ loc: locOf(text, i + 1), block: text });
    }
  }

  if (entries.length === 0) throw new Error("sitemap: no <url> entries found");
  return entries;
}

/** Render entries back to a sitemap file. Byte-identical for unmodified input. */
export function renderSitemap(entries: SitemapEntry[]): string {
  return HEADER + entries.map((e) => e.block + "\n").join("") + FOOTER;
}

/** `"Aug 10, 2026"` -> `"2026-08-10"`. Throws rather than guessing. */
export function parsePostDate(date: string): string {
  const m = /^([A-Z][a-z]{2}) (\d{1,2}), (\d{4})$/.exec(date.trim());
  if (!m) throw new Error(`post date is not parseable: ${JSON.stringify(date)}`);
  const month = MONTHS.indexOf(m[1]);
  if (month < 0) throw new Error(`post date has an unknown month: ${JSON.stringify(date)}`);
  return `${m[3]}-${String(month + 1).padStart(2, "0")}-${m[2].padStart(2, "0")}`;
}

/** The posts as the sitemap needs them, straight from the app's own data module. */
export function loadPosts(): Post[] {
  if (blogPosts.length === 0) throw new Error("blog-posts.ts exports no posts");
  const seen = new Set<string>();
  return blogPosts.map((p) => {
    if (seen.has(p.slug)) throw new Error(`blog-posts.ts has a duplicate slug: ${p.slug}`);
    seen.add(p.slug);
    return { slug: p.slug, date: parsePostDate(p.date) };
  });
}

function blogLoc(slug: string): string {
  return `${ORIGIN}${BLOG_PREFIX}${slug}`;
}

function isBlogLoc(loc: string): boolean {
  return loc.startsWith(`${ORIGIN}${BLOG_PREFIX}`);
}

function locOf(block: string, line: number): string {
  const all = [...block.matchAll(/<loc>([^<]+)<\/loc>/g)];
  if (all.length === 0) throw new Error(`sitemap: <url> entry near line ${line} has no <loc>`);
  if (all.length > 1) {
    throw new Error(
      `sitemap: <url> entry near line ${line} carries ${all.length} <loc> values - ` +
        `one entry must hold exactly one, so two entries have been merged into one block`,
    );
  }
  return all[0][1];
}

function blogBlock(slug: string, lastmod: string): string {
  return [
    "  <url>",
    `    <loc>${blogLoc(slug)}</loc>`,
    `    <lastmod>${lastmod}</lastmod>`,
    `    <changefreq>${BLOG_CHANGEFREQ}</changefreq>`,
    `    <priority>${BLOG_PRIORITY}</priority>`,
    "  </url>",
  ].join("\n");
}

export function routeLoc(path: string): string {
  return `${ORIGIN}${path}`;
}

/**
 * The block written for a declared route that has no entry yet. Multi-line, matching the
 * shape of the routes already in the file - including the eight `/runway/*` ones, which
 * on disk are single-line. That difference only shows up if one of them is ever deleted
 * and re-added; nothing here rewrites a shape that is already written.
 */
function routeBlock(route: PublicRoute): string {
  return [
    "  <url>",
    `    <loc>${routeLoc(route.path)}</loc>`,
    `    <lastmod>${route.lastmod}</lastmod>`,
    `    <changefreq>${route.changefreq}</changefreq>`,
    `    <priority>${route.priority}</priority>`,
    "  </url>",
  ].join("\n");
}

/**
 * Bring one sitemap in line with the posts and the declared public routes.
 *
 * Every unmodified entry keeps its exact bytes, so an unchanged input is a no-op and
 * `git diff` stays empty. Entry order on disk is preserved: a new post's entry is
 * inserted directly after the last existing blog entry, not appended to the file and not
 * re-sorted, because the blog block on disk is deliberately in reverse-chronological
 * order and re-sorting it would rewrite all 16 entries.
 *
 * Nothing is ever removed for being undeclared. A non-blog `<loc>` with no route behind
 * it is a real defect, but deleting it is a decision about the site, not about keeping a
 * generator's output consistent - so it is left for the drift test to fail on, loudly,
 * rather than silently rewritten here.
 */
export function syncSitemap(
  xml: string,
  posts: Post[],
  routes: readonly PublicRoute[] = PUBLIC_ROUTES,
): SyncResult {
  const entries = parseSitemap(xml);
  const wanted = new Map(posts.map((p) => [blogLoc(p.slug), p] as const));

  const added: string[] = [];
  const removed: string[] = [];
  const addedRoutes: string[] = [];
  const kept: SitemapEntry[] = [];

  for (const entry of entries) {
    if (!isBlogLoc(entry.loc)) {
      kept.push(entry); // a non-blog route: never rewritten, lastmod and all
      continue;
    }
    if (wanted.has(entry.loc)) {
      kept.push(entry); // in sync: keep the exact bytes, lastmod and all
      continue;
    }
    removed.push(entry.loc.slice(`${ORIGIN}${BLOG_PREFIX}`.length));
  }

  const present = new Set(
    entries.filter((e) => isBlogLoc(e.loc)).map((e) => e.loc),
  );
  const missing = posts.filter((p) => !present.has(blogLoc(p.slug)));
  added.push(...missing.map((p) => p.slug));

  if (missing.length > 0) {
    // Insert after the last blog entry that survived; append if the file has none.
    let at = kept.length;
    for (let i = kept.length - 1; i >= 0; i--) {
      if (isBlogLoc(kept[i].loc)) {
        at = i + 1;
        break;
      }
    }
    kept.splice(
      at,
      0,
      ...missing.map((p) => ({ loc: blogLoc(p.slug), block: blogBlock(p.slug, p.date) })),
    );
  }

  // Declared non-blog routes that have no entry yet. Appended at the end, in declaration
  // order: appending is the one placement that cannot disturb the order of the routes
  // already in the file. An entry that is already present is not touched at all.
  const presentRoutes = new Set(entries.map((e) => e.loc));
  const missingRoutes = routes.filter((r) => !presentRoutes.has(routeLoc(r.path)));
  addedRoutes.push(...missingRoutes.map((r) => r.path));
  kept.push(...missingRoutes.map((r) => ({ loc: routeLoc(r.path), block: routeBlock(r) })));

  return { xml: renderSitemap(kept), added, removed, addedRoutes };
}

/**
 * Bring `client/public/sitemap.xml` in line with the posts and write it if it moved.
 *
 * Returns what it did, so the build can log it and the test can assert on it. Throws
 * rather than writing if the result would fall below the floor - a generator bug must
 * not be able to delete a route that is still being served.
 */
export function generateSitemap(): {
  written: boolean;
  count: number;
  added: string[];
  removed: string[];
  addedRoutes: string[];
} {
  const before = readFileSync(SITEMAP_FILE, "utf8");
  const { xml, added, removed, addedRoutes } = syncSitemap(before, loadPosts());

  for (const slug of removed) console.log(`removed  ${BLOG_PREFIX}${slug} (no such post)`);
  for (const slug of added) console.log(`added    ${BLOG_PREFIX}${slug}`);
  for (const path of addedRoutes) console.log(`added    ${path} (declared route, had no <loc>)`);

  const count = parseSitemap(xml).length;
  if (count < SITEMAP_LOC_FLOOR) {
    throw new Error(
      `refusing to write: ${count} <loc> entries, below the floor of ${SITEMAP_LOC_FLOOR}`,
    );
  }

  if (xml === before) {
    console.log(`sitemap.xml unchanged: ${count} <loc> entries`);
    return { written: false, count, added, removed, addedRoutes };
  }
  writeFileSync(SITEMAP_FILE, xml);
  console.log(`sitemap.xml written: ${count} <loc> entries`);
  return { written: true, count, added, removed, addedRoutes };
}

const invoked = process.argv[1] ? resolve(process.argv[1]) : "";
if (invoked === fileURLToPath(import.meta.url)) {
  try {
    generateSitemap();
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
}
