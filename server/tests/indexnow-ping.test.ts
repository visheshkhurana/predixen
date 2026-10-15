/**
 * HAG-292: the URL list that goes to IndexNow, and the key it is signed with.
 *
 * Run: `npx tsx server/tests/indexnow-ping.test.ts` (or `npm run test:indexnow`).
 *
 * What this file is actually guarding, stated plainly:
 *
 *   - The list sent to IndexNow is the COMMITTED SITEMAP, parsed by the same function
 *     the sitemap generator uses. If the parse and the generator ever disagree, the
 *     ping silently submits the wrong set of URLs and nothing complains.
 *   - IndexNow fetches `keyLocation` and compares the body to the `key` we sent. If the
 *     key file's name and its contents disagree, every submission is rejected with a
 *     403 that looks like a permissions problem. `findKey` fails loudly instead.
 *   - A ping that fails must be a RETURN VALUE, not a thrown exception. The workflow
 *     step carries `continue-on-error: true` so a failed ping can never fail a deploy;
 *     a throw here would also mean a network blip kills the process before it can log
 *     what happened.
 *
 * The last four tests are the controls: without them this file asserts that a working
 * parse works, which it would also do if `extractUrls` returned a hard-coded list.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import {
  INDEXNOW_ENDPOINT,
  KEY_FILE_RE,
  URL_CAP,
  buildPayload,
  extractUrls,
  findKey,
  pingIndexNow,
} from "../../scripts/indexnow-ping.ts";
import { ORIGIN, SITEMAP_FILE } from "../../scripts/generate-sitemap.ts";
import { readFileSync } from "fs";

const SITEMAP_XML = readFileSync(SITEMAP_FILE, "utf8");
const HOST = new URL(ORIGIN).host;

/** A sitemap with one `<url>` per loc, in the generator's own one-line shape. */
function sitemapOf(locs: string[]): string {
  const body = locs
    .map((loc) => `  <url><loc>${loc}</loc><lastmod>2026-10-01</lastmod></url>`)
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;
}

function dirWithKey(name: string, contents: string): string {
  const dir = mkdtempSync(join(tmpdir(), "indexnow-"));
  writeFileSync(join(dir, name), contents);
  return dir;
}

// --- the real sitemap ------------------------------------------------------------

test("every URL submitted is a <loc> from the committed sitemap, in order", () => {
  const urls = extractUrls(SITEMAP_XML);
  assert.ok(urls.length > 0, "the sitemap must yield URLs");
  // Independent of extractUrls: pull the <loc> values out with a plain regex and
  // compare sets, so a parse change cannot move both sides together.
  const literal = [...SITEMAP_XML.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  assert.deepEqual(urls, literal, "extractUrls must agree with the raw <loc> values, in order");
});

test("the committed sitemap is under the cap, so the cap changes nothing today", () => {
  const urls = extractUrls(SITEMAP_XML);
  assert.ok(urls.length < URL_CAP, `${urls.length} URLs vs cap ${URL_CAP}`);
  assert.equal(extractUrls(SITEMAP_XML, URL_CAP).length, urls.length);
});

test("the key served at client/public is 32 hex, and its name is its contents", () => {
  const { key, file } = findKey();
  assert.match(key, /^[0-9a-f]{32}$/, `key from ${file}`);
  assert.ok(KEY_FILE_RE.test(file.split("/").pop()!), "the filename must match the pattern");
});

test("the payload carries the host, the key and a keyLocation that serves the key", () => {
  const { key } = findKey();
  const payload = buildPayload(extractUrls(SITEMAP_XML), key);
  assert.equal(payload.host, HOST);
  assert.ok(!payload.host.includes("/"), "IndexNow wants the host, not the origin");
  assert.equal(payload.key, key);
  assert.equal(payload.keyLocation, `${ORIGIN}/${key}.txt`);
  assert.equal(payload.urlList.length, extractUrls(SITEMAP_XML).length);
});

// --- extractUrls controls --------------------------------------------------------

test("a foreign host is dropped: one bad <loc> must not fail the whole submission", () => {
  const xml = sitemapOf([`${ORIGIN}/a`, "https://evil.example/b", `${ORIGIN}/c`]);
  assert.deepEqual(extractUrls(xml), [`${ORIGIN}/a`, `${ORIGIN}/c`]);
});

test("a malformed <loc> is skipped rather than fatal", () => {
  const xml = sitemapOf([`${ORIGIN}/a`, "not a url", `${ORIGIN}/b`]);
  assert.deepEqual(extractUrls(xml), [`${ORIGIN}/a`, `${ORIGIN}/b`]);
});

test("duplicates collapse to one entry", () => {
  const xml = sitemapOf([`${ORIGIN}/a`, `${ORIGIN}/a`, `${ORIGIN}/b`]);
  assert.deepEqual(extractUrls(xml), [`${ORIGIN}/a`, `${ORIGIN}/b`]);
});

test("the cap truncates from the front, it does not reorder or drop the head", () => {
  const locs = Array.from({ length: 25 }, (_, i) => `${ORIGIN}/p${i}`);
  const capped = extractUrls(sitemapOf(locs), 10);
  assert.equal(capped.length, 10);
  assert.equal(capped[0], `${ORIGIN}/p0`);
  assert.equal(capped[9], `${ORIGIN}/p9`);
});

test("a sitemap with no <url> entries throws instead of submitting an empty list", () => {
  assert.throws(() => extractUrls(sitemapOf([])), /no <url> entries/);
});

// --- findKey controls ------------------------------------------------------------

const KEY = "0123456789abcdef0123456789abcdef";

test("findKey reads the key from the file's contents", () => {
  const { key, file } = findKey(dirWithKey(`${KEY}.txt`, KEY));
  assert.equal(key, KEY);
  assert.ok(file.endsWith(`${KEY}.txt`));
});

test("findKey throws when the file's name is not its contents", () => {
  // This is the 403-with-no-explanation case: verification fetches keyLocation and
  // compares it to the submitted key, so a mismatch rejects every submission.
  assert.throws(() => findKey(dirWithKey(`${KEY}.txt`, "another-key-entirely")), /not its own name/);
});

test("findKey throws when there is no key file, and when there are two", () => {
  assert.throws(() => findKey(mkdtempSync(join(tmpdir(), "indexnow-"))), /no IndexNow key file/);
  const dir = mkdtempSync(join(tmpdir(), "indexnow-"));
  writeFileSync(join(dir, `${KEY}.txt`), KEY);
  writeFileSync(join(dir, "fedcba9876543210fedcba9876543210.txt"), "fedcba9876543210fedcba9876543210");
  assert.throws(() => findKey(dir), /more than one/);
});

test("a trailing newline in the key file does not break verification", () => {
  const { key } = findKey(dirWithKey(`${KEY}.txt`, `${KEY}\n`));
  assert.equal(key, KEY);
});

// --- pingIndexNow: a failure is a return value -----------------------------------

const PAYLOAD = { host: HOST, key: KEY, keyLocation: `${ORIGIN}/${KEY}.txt`, urlList: [`${ORIGIN}/`] };

function fakeFetch(status: number): typeof fetch {
  return (async () => ({ status })) as unknown as typeof fetch;
}

test("200 and 202 are both accepted; anything else is not", async () => {
  assert.equal((await pingIndexNow(PAYLOAD, fakeFetch(200))).ok, true);
  assert.equal((await pingIndexNow(PAYLOAD, fakeFetch(202))).ok, true);
  const rejected = await pingIndexNow(PAYLOAD, fakeFetch(422));
  assert.equal(rejected.ok, false);
  assert.equal(rejected.status, 422);
});

test("a thrown network error becomes a result, not an exception", async () => {
  const throwing = (async () => {
    throw new Error("getaddrinfo ENOTFOUND api.indexnow.org");
  }) as unknown as typeof fetch;
  const result = await pingIndexNow(PAYLOAD, throwing);
  assert.equal(result.ok, false);
  assert.match(result.error ?? "", /ENOTFOUND/);
});

test("the request is a POST of JSON to the documented endpoint, with no credentials", async () => {
  let seen: { url: string; init: any } | null = null;
  const spy = (async (url: string, init: any) => {
    seen = { url, init };
    return { status: 200 };
  }) as unknown as typeof fetch;
  await pingIndexNow(PAYLOAD, spy);
  assert.ok(seen, "fetch must have been called");
  assert.equal(seen!.url, INDEXNOW_ENDPOINT);
  assert.equal(seen!.init.method, "POST");
  const headers = seen!.init.headers as Record<string, string>;
  assert.match(headers["Content-Type"], /application\/json/);
  assert.ok(
    !Object.keys(headers).some((h) => /authorization|api[-_]?key|x-api/i.test(h)),
    "IndexNow needs no credential - the key is a public verification token, not an auth header",
  );
  assert.deepEqual(JSON.parse(seen!.init.body), PAYLOAD);
});
