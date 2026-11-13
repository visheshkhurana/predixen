/**
 * HAG-204: the committed sitemap must match the routes the app actually serves.
 *
 * Run from the repo root: `npm run test:sitemap`, or `npx tsx server/tests/sitemap-drift.test.ts`.
 *
 * The point of this file is the four controls at the end. Every assertion above them
 * passes on `main` today, because `main`'s sitemap happens to be in sync - so on its own
 * this file would be a green step that cannot fail, which is the same defect class as the
 * `llms.txt` check: a test that only ever says yes. The first control proves the test
 * notices a post that is missing from the sitemap, the second proves it notices a sitemap
 * entry with no post behind it, the third proves the same for a declared non-blog route,
 * and the fourth proves the tag-balance check rejects the damaged file a same-anchor
 * auto-merge produces. Delete any of them and this file stops being evidence.
 *
 * The fourth control is there because the first three did not catch that damage. On
 * 2026-10-15 a rebase auto-merged two `<url>` blocks at one anchor into a file
 * `ET.parse` rejects, and every check in this file reported `ok` on it.
 *
 * The non-blog half is checked in both directions, because a list declared in the
 * generator can drift from the app in either: every declared route must be one `App.tsx`
 * actually registers, and every non-blog `<loc>` in the file must be declared.
 */

import { readFileSync } from "fs";
import {
  BLOG_PREFIX,
  ORIGIN,
  PUBLIC_ROUTES,
  SITEMAP_FILE,
  SITEMAP_LOC_FLOOR,
  loadPosts,
  parsePostDate,
  parseSitemap,
  renderSitemap,
  routeLoc,
  syncSitemap,
  type Post,
} from "../../scripts/generate-sitemap.ts";
import { renderHtmlPage } from "../seo-prerender.ts";
import { blogPosts as clientPosts } from "../../client/src/data/blog-posts.ts";

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

// The sitemap is generated from blog-posts.ts. SSR used to read a second list
// in server/seo-data.ts, so a post could be in the sitemap and still prerender
// as "Article not found". Every blog <loc> must render that post.
const SHELL = readFileSync("client/index.html", "utf8");
function escapeHtml(str: string): string {
  return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
const ssrMisses: string[] = [];
for (const slug of sitemapSlugs) {
  const page = renderHtmlPage(SHELL, `/blog/${slug}`);
  const post = clientPosts.find((p) => p.slug === slug);
  const hasArticle =
    !!post &&
    page.status === 200 &&
    page.html.includes(`<h1>${escapeHtml(post.title)}</h1>`) &&
    page.html.includes(`/blog/${slug}`) &&
    !page.html.includes("Article not found");
  if (!hasArticle) ssrMisses.push(`${slug} status=${page.status}`);
}
check(
  "every sitemap blog URL has SSR article data",
  ssrMisses.length === 0,
  ssrMisses.join("\n        "),
);

{
  const missing = renderHtmlPage(SHELL, "/blog/not-a-real-article-zzzz");
  check(
    "CONTROL: a blog URL with no post is Article not found and HTTP 404",
    missing.status === 404 && missing.html.includes("Article not found"),
    `status=${missing.status}`,
  );
}

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

// The tag balance, which is the check that was missing. Every assertion above passed on
// a file that `ET.parse` rejects with `mismatched tag`, because this parser is line-based:
// a stray `<url>` between one entry's open and its close is absorbed into that entry's
// bytes, the entry count does not move, and the round trip above reproduces the damage
// faithfully. Counting the tags is what the parser structurally cannot see, so the two
// numbers are compared here against each other and against the entry count.
//
// This is also why the file is not asserted to be well-formed XML directly: a real parse
// needs a dependency, and one is on the hold list. Two open tags against one close is the
// shape a same-anchor auto-merge produces, and it is what this catches.
const openTags = (xml.match(/<url>/g) ?? []).length;
const closeTags = (xml.match(/<\/url>/g) ?? []).length;
check(
  "every <url> is closed, none is nested, and each entry is one <url>",
  openTags === closeTags && openTags === entries.length && openTags === locs.length,
  `<url> ${openTags} vs </url> ${closeTags}, parsed entries ${entries.length}, ` +
    `<loc> ${locs.length}`,
);

// ---------------------------------------------------------------------------
// The non-blog half: the declared routes and the app must agree.
// ---------------------------------------------------------------------------

const declaredLocs = PUBLIC_ROUTES.map((r) => routeLoc(r.path));
const nonBlogLocs = locs.filter((l) => !l.startsWith(`${ORIGIN}${BLOG_PREFIX}`));

const undeclared = sameSet(declaredLocs.slice().sort(), nonBlogLocs.slice().sort());
check(
  "every declared route has a <loc>, and every non-blog <loc> is declared",
  undeclared.length === 0,
  undeclared.join("\n        "),
);

// A declared path that the app does not register is a sitemap entry for a page nobody
// serves. Matched literally (`path="/pricing"`) or through a dynamic parent, so
// `/runway/saas` counts as covered by `/runway/:slug`.
const appSource = readFileSync("client/src/App.tsx", "utf8");
const appPaths = [...appSource.matchAll(/path="([^"]*)"/g)].map((m) => m[1]);

function segments(p: string): string[] {
  return p.split("/").filter((s) => s.length > 0);
}

function registered(path: string): boolean {
  const want = segments(path);
  return appPaths.some((candidate) => {
    const have = segments(candidate);
    return (
      have.length === want.length &&
      have.every((seg, i) => seg === want[i] || seg.startsWith(":"))
    );
  });
}

const unregistered = PUBLIC_ROUTES.map((r) => r.path).filter((p) => !registered(p));
check(
  "every declared route is a route App.tsx registers",
  unregistered.length === 0,
  `no matching <Route path> for: ${unregistered.join(", ")}`,
);

// In sync: regenerating changes nothing. On main this is the whole of the "no diff"
// claim - the PR does not move the file.
const inSync = syncSitemap(xml, posts);
check(
  "regenerating an in-sync sitemap is a no-op",
  inSync.added.length === 0 &&
    inSync.removed.length === 0 &&
    inSync.addedRoutes.length === 0 &&
    inSync.xml === xml,
  `added ${JSON.stringify(inSync.added)} removed ${JSON.stringify(inSync.removed)} ` +
    `addedRoutes ${JSON.stringify(inSync.addedRoutes)}`,
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

// The control for the tag-balance check above: the same damaged file the `#107` rebase
// produced - one anchor, both sides' `<url>`, two opens against one close - must be
// rejected. Without this the balance check is a step that has only ever said yes on a
// file that happened to be well-formed, which is the defect class this file was written
// to avoid. It is built from the live file, so it also proves the damage is reachable
// from the real input rather than from a hand-made string.
{
  const damaged = xml.replace("  <url>\n", "  <url>\n  <url>\n");
  const dOpen = (damaged.match(/<url>/g) ?? []).length;
  const dClose = (damaged.match(/<\/url>/g) ?? []).length;
  let parserRejected = false;
  try {
    parseSitemap(damaged);
  } catch {
    parserRejected = true;
  }
  check(
    "CONTROL: a duplicated <url> open fails the balance check and the parser",
    dOpen !== dClose && !(dOpen === dClose && dOpen === entries.length) && parserRejected,
    `damaged: <url> ${dOpen} vs </url> ${dClose}, parser threw: ${parserRejected}`,
  );
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

// The same control for the non-blog half: a page ships, nobody edits the XML, and the
// route has to appear anyway. This is the failure Sentinel's M1 named - the three
// `/tools/` pages HAG-163 adds would otherwise ship absent from the sitemap.
{
  const TARGET = "/tools/runway-calculator";
  const targetLoc = routeLoc(TARGET);
  const route = PUBLIC_ROUTES.find((r) => r.path === TARGET);
  if (!route) throw new Error(`${TARGET} is not declared in PUBLIC_ROUTES`);

  const without = renderSitemap(entries.filter((e) => e.loc !== targetLoc));
  const res = syncSitemap(without, posts);
  const back = parseSitemap(res.xml).find((e) => e.loc === targetLoc)?.block ?? "";

  const ok =
    res.addedRoutes.length === 1 &&
    res.addedRoutes[0] === TARGET &&
    res.added.length === 0 &&
    res.removed.length === 0 &&
    parseSitemap(res.xml).length === locs.length &&
    back.includes(`<loc>${targetLoc}</loc>`) &&
    back.includes(`<lastmod>${route.lastmod}</lastmod>`);

  check("POSITIVE CONTROL: a declared route missing from the file is added", ok,
    `addedRoutes ${JSON.stringify(res.addedRoutes)} added ${JSON.stringify(res.added)} ` +
    `count ${parseSitemap(res.xml).length} (was ${locs.length})\n        block: ${JSON.stringify(back)}`);
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
