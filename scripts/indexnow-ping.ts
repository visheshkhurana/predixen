/**
 * Tell IndexNow about the URLs in `client/public/sitemap.xml`.
 *
 * Why this exists (HAG-292): without it a new page waits for a crawler to happen
 * past it, which is weeks. IndexNow is a push - one HTTP POST and Bing, Yandex and
 * the engines behind ChatGPT search know the URL within hours. It is free and needs
 * no account, which is why it is worth doing before anything that costs money.
 *
 * The URL list is the sitemap, not a hand-written array. `parseSitemap` is imported
 * from `generate-sitemap.ts` rather than re-implemented here, so there is one parser
 * and one definition of what a `<loc>` is; `sitemap-drift.test.ts` already holds that
 * parser to the routes `App.tsx` registers.
 *
 * WHAT IS DELIBERATELY NOT ATTEMPTED: "only the pages that changed in this deploy".
 * The card allows all of them, capped, and all of them is the honest choice here - the
 * sitemap is 44 entries, well under the 10,000 cap, so there is nothing to save, and
 * "changed since the last deploy" needs state the workflow does not have. A `git diff`
 * against the previous commit would under-report: a deploy can change a page whose
 * route file did not change (a shared component, a price, a template), and a stale
 * index is invisible from the outside.
 *
 * A FAILED PING MUST NEVER FAIL A DEPLOY. The workflow step that runs this carries
 * `continue-on-error: true`, and that is a requirement, not a convenience - see the
 * comment in `.github/workflows/indexnow-ping.yml`. This script still exits non-zero
 * when it could not do its job, so the failure is visible in the run log instead of
 * green; the `continue-on-error` is what keeps it from mattering.
 *
 * The 32-hex key is PUBLIC BY DESIGN. It is a verification token, not a credential:
 * IndexNow fetches it back from `keyLocation` to prove we control the host, so it is
 * served openly at `client/public/<key>.txt` and must never be put in a secret store.
 * There is nothing to leak, and treating it as a secret would break verification.
 *
 * Run it directly (`npx tsx scripts/indexnow-ping.ts`) or import it - the CLI guard
 * below means importing has no side effects.
 */

import { readFileSync, readdirSync } from "fs";
import { resolve } from "path";
import { fileURLToPath } from "url";
// The `.ts` extension is this repo's convention for importing from `scripts/`
// (`sitemap-drift.test.ts` does the same) and it is what makes this module runnable
// under plain `node` as well as `tsx` - `node` cannot resolve an extensionless
// specifier, and a script that only runs under one runner is a script that gets
// skipped.
import { ORIGIN, ROOT, SITEMAP_FILE, parseSitemap } from "./generate-sitemap.ts";

export const INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow";

/** IndexNow's documented per-request ceiling. We are nowhere near it. */
export const URL_CAP = 10_000;

/** `client/public/` - the same directory the sitemap is written to. */
export const PUBLIC_DIR = resolve(ROOT, "client/public");

/** An IndexNow key file: 32 lowercase hex characters, then `.txt`. */
export const KEY_FILE_RE = /^[0-9a-f]{32}\.txt$/;

export interface IndexNowPayload {
  host: string;
  key: string;
  keyLocation: string;
  urlList: string[];
}

export interface PingResult {
  ok: boolean;
  status?: number;
  /** Present when the ping did not go out at all (no key, no sitemap, network). */
  error?: string;
  sent: number;
}

/**
 * The key, read from the file that serves it - the file is the source of truth, so
 * the value the engines verify against and the value we submit cannot drift apart.
 * Throws rather than guessing if the directory does not hold exactly one.
 */
export function findKey(dir: string = PUBLIC_DIR): { key: string; file: string } {
  const matches = readdirSync(dir).filter((name) => KEY_FILE_RE.test(name));
  if (matches.length === 0) {
    throw new Error(
      `no IndexNow key file in ${dir}: expected one <32-hex>.txt whose contents are the key`,
    );
  }
  if (matches.length > 1) {
    throw new Error(`more than one IndexNow key file in ${dir}: ${matches.join(", ")}`);
  }
  const file = resolve(dir, matches[0]);
  const key = readFileSync(file, "utf8").trim();
  const stem = matches[0].replace(/\.txt$/, "");
  // The key file's own name must be the key. If they disagree, IndexNow's fetch of
  // keyLocation returns a body that does not match the key we sent, and the submission
  // is rejected - so fail here, where the message can say which two things disagree.
  if (key !== stem) {
    throw new Error(`key file ${matches[0]} contains ${JSON.stringify(key)}, not its own name`);
  }
  return { key, file };
}

/**
 * Every same-host URL in the sitemap, in file order, de-duplicated and capped.
 *
 * Same-host only, because IndexNow rejects a submission that lists a URL it does not
 * consider ours, and one bad entry fails the whole request. A cross-host `<loc>` is a
 * bug in the sitemap, but it must not be able to take the ping down with it.
 */
export function extractUrls(xml: string, cap: number = URL_CAP): string[] {
  const host = new URL(ORIGIN).host;
  const seen = new Set<string>();
  const urls: string[] = [];

  for (const entry of parseSitemap(xml)) {
    let parsed: URL;
    try {
      parsed = new URL(entry.loc);
    } catch {
      continue; // a malformed <loc> is skipped, not fatal
    }
    if (parsed.host !== host) continue;
    const url = parsed.toString();
    if (seen.has(url)) continue;
    seen.add(url);
    urls.push(url);
    if (urls.length >= cap) break;
  }
  return urls;
}

export function buildPayload(urls: string[], key: string): IndexNowPayload {
  return {
    host: new URL(ORIGIN).host,
    key,
    keyLocation: `${ORIGIN}/${key}.txt`,
    urlList: urls,
  };
}

/** POST the payload. Never throws: a ping failure is a return value, not an exception. */
export async function pingIndexNow(
  payload: IndexNowPayload,
  fetchImpl: typeof fetch = fetch,
): Promise<PingResult> {
  try {
    const res = await fetchImpl(INDEXNOW_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(payload),
    });
    // IndexNow answers 200 (accepted) or 202 (accepted, key pending verification).
    return { ok: res.status === 200 || res.status === 202, status: res.status, sent: payload.urlList.length };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err), sent: payload.urlList.length };
  }
}

async function main(): Promise<void> {
  const { key, file } = findKey();
  const urls = extractUrls(readFileSync(SITEMAP_FILE, "utf8"));
  if (urls.length === 0) throw new Error(`sitemap at ${SITEMAP_FILE} yielded no same-host URLs`);

  console.log(`[indexnow] key ${key} from ${file}`);
  console.log(`[indexnow] ${urls.length} URLs from ${SITEMAP_FILE}`);

  const result = await pingIndexNow(buildPayload(urls, key));
  if (result.ok) {
    console.log(`[indexnow] accepted: HTTP ${result.status}, ${result.sent} URLs submitted`);
    return;
  }
  // Non-zero on purpose: the workflow's `continue-on-error: true` keeps this from
  // failing the deploy, and a red log line is how anyone finds out the ping broke.
  throw new Error(
    `indexnow ping failed: ${result.error ?? `HTTP ${result.status}`} (${result.sent} URLs)`,
  );
}

const invoked = process.argv[1] ? resolve(process.argv[1]) : "";
if (invoked === fileURLToPath(import.meta.url)) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
