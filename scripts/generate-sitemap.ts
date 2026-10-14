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
 *   - The other routes (/, /features, /runway/*, ...) are still a hand-maintained list
 *     in the sitemap file itself. They are not derived from anything, because the app
 *     has no single route manifest to derive them from. They are held in place by the
 *     44-entry floor and the uniqueness/origin checks in
 *     `server/tests/sitemap-drift.test.ts`, and nothing here removes them.
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
}

/** Split a sitemap file into its `<url>` entries, verbatim, in file order. */
export function parseSitemap(xml: string): SitemapEntry[] {
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
  const m = /<loc>([^<]+)<\/loc>/.exec(block);
  if (!m) throw new Error(`sitemap: <url> entry near line ${line} has no <loc>`);
  return m[1];
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

/**
 * Bring one sitemap in line with the posts.
 *
 * Every unmodified entry keeps its exact bytes, so an unchanged input is a no-op and
 * `git diff` stays empty. Entry order on disk is preserved: a new post's entry is
 * inserted directly after the last existing blog entry, not appended to the file and not
 * re-sorted, because the blog block on disk is deliberately in reverse-chronological
 * order and re-sorting it would rewrite all 16 entries.
 */
export function syncSitemap(xml: string, posts: Post[]): SyncResult {
  const entries = parseSitemap(xml);
  const wanted = new Map(posts.map((p) => [blogLoc(p.slug), p] as const));

  const added: string[] = [];
  const removed: string[] = [];
  const kept: SitemapEntry[] = [];

  for (const entry of entries) {
    if (!isBlogLoc(entry.loc)) {
      kept.push(entry); // a hand-maintained route: never touched
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

  return { xml: renderSitemap(kept), added, removed };
}

/**
 * Bring `client/public/sitemap.xml` in line with the posts and write it if it moved.
 *
 * Returns what it did, so the build can log it and the test can assert on it. Throws
 * rather than writing if the result would fall below the floor - a generator bug must
 * not be able to delete a route that is still being served.
 */
export function generateSitemap(): { written: boolean; count: number; added: string[]; removed: string[] } {
  const before = readFileSync(SITEMAP_FILE, "utf8");
  const { xml, added, removed } = syncSitemap(before, loadPosts());

  for (const slug of removed) console.log(`removed  ${BLOG_PREFIX}${slug} (no such post)`);
  for (const slug of added) console.log(`added    ${BLOG_PREFIX}${slug}`);

  const count = parseSitemap(xml).length;
  if (count < SITEMAP_LOC_FLOOR) {
    throw new Error(
      `refusing to write: ${count} <loc> entries, below the floor of ${SITEMAP_LOC_FLOOR}`,
    );
  }

  if (xml === before) {
    console.log(`sitemap.xml unchanged: ${count} <loc> entries`);
    return { written: false, count, added, removed };
  }
  writeFileSync(SITEMAP_FILE, xml);
  console.log(`sitemap.xml written: ${count} <loc> entries`);
  return { written: true, count, added, removed };
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
