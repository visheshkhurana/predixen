/**
 * HAG-204: the committed sitemap must match the routes the app actually serves.
 *
 * Run from the repo root: `npm run test:sitemap`, or `npx tsx server/tests/sitemap-drift.test.ts`.
 *
 * The point of this file is the two controls at the end. Every assertion above them
 * passes on `main` today, because `main`'s sitemap happens to be in sync - so on its own
 * this file would be a green step that cannot fail, which is the same defect class as the
 * `llms.txt` check: a test that only ever says yes. The positive control proves the test
 * notices a post that is missing from the sitemap, and the negative control proves it
 * notices a sitemap entry with no post behind it. Delete either and this file stops being
 * evidence.
 */

import { readFileSync } from "fs";
import {
  BLOG_PREFIX,
  ORIGIN,
  SITEMAP_FILE,
  SITEMAP_LOC_FLOOR,
  loadPosts,
  parsePostDate,
  parseSitemap,
  renderSitemap,
  syncSitemap,
  type Post,
} from "../../scripts/generate-sitemap.ts";

let failures = 0;

function check(name: string, ok: boolean, detail = ""): void {
  if (ok) {
    console.log(`  ok    ${name}`);
    return;
  }
  failures++;
  console.log(`  FAIL  ${name}${detail ? `\n        ${detail}` : ""}`);
}

function blogSlugsOf(locs: string[]): string[] {
  return locs
    .filter((l) => l.startsWith(`${ORIGIN}${BLOG_PREFIX}`))
    .map((l) => l.slice(`${ORIGIN}${BLOG_PREFIX}`.length));
}

function sameSet(a: string[], b: string[]): string[] {
  const bs = new Set(b);
  const as = new Set(a);
  return [
    ...a.filter((x) => !bs.has(x)).map((x) => `only in first: ${x}`),
    ...b.filter((x) => !as.has(x)).map((x) => `only in second: ${x}`),
  ];
}

// The committed file, read as bytes - not regenerated, not normalised.
const xml = readFileSync(SITEMAP_FILE, "utf8"); // run from the repo root
const entries = parseSitemap(xml);
const locs = entries.map((e) => e.loc);
const posts = loadPosts();

console.log("sitemap drift");

check(
  "every post has a parseable date",
  posts.every((p) => /^\d{4}-\d{2}-\d{2}$/.test(p.date)),
  `dates: ${posts.map((p) => p.date).join(", ")}`,
);
check("blog-posts.ts exports at least one post", posts.length > 0, `posts: ${posts.length}`);

check(
  `at least ${SITEMAP_LOC_FLOOR} <loc> entries`,
  locs.length >= SITEMAP_LOC_FLOOR,
  `found ${locs.length}`,
);

const postSlugs = posts.map((p) => p.slug).sort();
const sitemapSlugs = blogSlugsOf(locs).sort();
const diff = sameSet(postSlugs, sitemapSlugs);
check(
  "every post has a <loc> and every blog <loc> has a post",
  diff.length === 0,
  diff.join("\n        "),
);

// Re-rendering what we parsed must reproduce the file exactly. If this ever fails, the
// generator's parse/render round trip is lossy and every other check here is measuring
// something other than the file on disk.
check(
  "parse -> render reproduces the file byte for byte",
  renderSitemap(entries) === xml,
  `${renderSitemap(entries).length} bytes rendered vs ${xml.length} on disk`,
);

check(
  "every <loc> is on the canonical origin and appears once",
  locs.every((l) => l.startsWith(`${ORIGIN}/`)) && new Set(locs).size === locs.length,
  `unique ${new Set(locs).size} of ${locs.length}`,
);

// In sync: regenerating changes nothing. On main this is the whole of the "no diff"
// claim - the PR does not move the file.
const inSync = syncSitemap(xml, posts);
check(
  "regenerating an in-sync sitemap is a no-op",
  inSync.added.length === 0 && inSync.removed.length === 0 && inSync.xml === xml,
  `added ${JSON.stringify(inSync.added)} removed ${JSON.stringify(inSync.removed)}`,
);

// ---------------------------------------------------------------------------
// Controls. These are the reason the file exists.
// ---------------------------------------------------------------------------

const NEW_SLUG = "a-brand-new-post-nobody-has-written-yet";
const NEW_DATE = "2026-10-14";

{
  const withNew: Post[] = [...posts, { slug: NEW_SLUG, date: NEW_DATE }];
  const res = syncSitemap(xml, withNew);
  const rendered = parseSitemap(res.xml);
  const loc = `${ORIGIN}${BLOG_PREFIX}${NEW_SLUG}`;
  const block = rendered.find((e) => e.loc === loc)?.block ?? "";

  const ok =
    res.added.length === 1 &&
    res.added[0] === NEW_SLUG &&
    res.removed.length === 0 &&
    rendered.length === locs.length + 1 &&
    block.includes(`<loc>${loc}</loc>`) &&
    block.includes(`<lastmod>${NEW_DATE}</lastmod>`);

  check("POSITIVE CONTROL: a new post is added, with its date as lastmod", ok,
    `added ${JSON.stringify(res.added)} removed ${JSON.stringify(res.removed)} ` +
    `count ${rendered.length} (was ${locs.length})\n        block: ${JSON.stringify(block)}`);
}

{
  const dropped = posts[0];
  const fewer = posts.slice(1);
  const res = syncSitemap(xml, fewer);
  const ok =
    res.removed.length === 1 &&
    res.removed[0] === dropped.slug &&
    res.added.length === 0 &&
    parseSitemap(res.xml).length === locs.length - 1 &&
    !res.xml.includes(`${ORIGIN}${BLOG_PREFIX}${dropped.slug}<`);

  check("NEGATIVE CONTROL: a post with no page loses its <loc>", ok,
    `dropped ${dropped.slug}: removed ${JSON.stringify(res.removed)} ` +
    `added ${JSON.stringify(res.added)} count ${parseSitemap(res.xml).length} (was ${locs.length})`);
}

// A date the file has never seen must fail loudly rather than be guessed at.
{
  let threw = false;
  try {
    parsePostDate("14 October 2026");
  } catch {
    threw = true;
  }
  check("an unparseable post date throws instead of guessing", threw);
}

console.log(`\n${locs.length} <loc> entries, ${blogSlugsOf(locs).length} blog entries, ${posts.length} posts`);
console.log(failures === 0 ? "\nALL PASS" : `\n${failures} FAILURES`);
process.exit(failures === 0 ? 0 : 1);
