/**
 * HAG-294: the internal-traffic classifier.
 *
 * The assertions that carry the weight are the negative ones. A tag that fires on a
 * real founder is worse than the noise it was meant to remove, so most of this file is
 * spent proving the classifier stays quiet: a plain browser, a path that merely
 * resembles the probe, a UA that merely resembles ours, and an empty `?fc_internal=`.
 *
 * Run: `npx tsx --test server/tests/internal-traffic.test.ts`
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  INTERNAL_FLAG_KEY,
  INTERNAL_PROBE_PREFIX,
  INTERNAL_UA_MARKER,
  classifyInternalTraffic,
  flagFromSearch,
} from "../../client/src/lib/internal-traffic.ts";

/** A browser that is not ours: no webdriver, an ordinary UA, a real page. */
const FOUNDER = {
  webdriver: false,
  userAgent:
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36",
  pathname: "/tools/runway-calculator",
  search: "",
  storedFlag: null as string | null,
};

test("a plain browser is NOT labelled internal - the whole point", () => {
  const verdict = classifyInternalTraffic(FOUNDER);
  assert.equal(verdict.internal, false);
  assert.equal(verdict.reason, null);
});

test("Playwright / Puppeteer is labelled internal via navigator.webdriver", () => {
  const verdict = classifyInternalTraffic({ ...FOUNDER, webdriver: true });
  assert.equal(verdict.internal, true);
  assert.equal(verdict.reason, "webdriver");
});

test("our own UA marker labels internal", () => {
  const verdict = classifyInternalTraffic({
    ...FOUNDER,
    userAgent: `Mozilla/5.0 (compatible; ${INTERNAL_UA_MARKER}/1.0)`,
  });
  assert.equal(verdict.internal, true);
  assert.equal(verdict.reason, "internal-user-agent");
});

test("a UA that merely resembles ours does NOT label internal", () => {
  // Same words, none of them the marker: a crawler named after us by someone else
  // must not be swept in, and a substring test is what makes that true.
  const verdict = classifyInternalTraffic({
    ...FOUNDER,
    userAgent: "Mozilla/5.0 (compatible; FounderConsoleBot/1.0)",
  });
  assert.equal(verdict.internal, false);
  assert.equal(verdict.reason, null);
});

test("the floor's 404 probe path labels internal", () => {
  const verdict = classifyInternalTraffic({
    ...FOUNDER,
    pathname: `${INTERNAL_PROBE_PREFIX}xyz123`,
  });
  assert.equal(verdict.internal, true);
  assert.equal(verdict.reason, "internal-probe-path");
});

test("the probe prefix is the one the scoreboard names", () => {
  // latest.md calls out `/this-page-does-not-exist-xyz123` by name. If this constant
  // ever drifts from that path, the classifier silently stops matching the visits the
  // column is actually polluted by.
  assert.equal(INTERNAL_PROBE_PREFIX, "/this-page-does-not-exist-");
});

test("a path that only CONTAINS the probe prefix does NOT label internal", () => {
  const verdict = classifyInternalTraffic({
    ...FOUNDER,
    pathname: `/blog${INTERNAL_PROBE_PREFIX}xyz123`,
  });
  assert.equal(verdict.internal, false);
});

test("?fc_internal=1 labels internal with reason flag", () => {
  const verdict = classifyInternalTraffic({ ...FOUNDER, search: `?${INTERNAL_FLAG_KEY}=1` });
  assert.equal(verdict.internal, true);
  assert.equal(verdict.reason, "flag");
});

test("an empty ?fc_internal= does NOT label internal", () => {
  // A truncated or template-filled URL must not silently tag a founder's visit.
  const verdict = classifyInternalTraffic({ ...FOUNDER, search: `?${INTERNAL_FLAG_KEY}=` });
  assert.equal(verdict.internal, false);
  assert.equal(flagFromSearch(`?${INTERNAL_FLAG_KEY}=`), null);
});

test("a persisted flag labels internal on a later load with no query string", () => {
  const verdict = classifyInternalTraffic({ ...FOUNDER, storedFlag: "agents" });
  assert.equal(verdict.internal, true);
  assert.equal(verdict.reason, "flag");
});

test("the flag outranks webdriver, so the reason names the deliberate signal", () => {
  const verdict = classifyInternalTraffic({
    ...FOUNDER,
    storedFlag: "vishesh",
    webdriver: true,
  });
  assert.equal(verdict.reason, "flag");
});

test("the flag is read from a search string without the leading ?", () => {
  assert.equal(flagFromSearch(`${INTERNAL_FLAG_KEY}=checkout`), "checkout");
  assert.equal(flagFromSearch(""), null);
  assert.equal(flagFromSearch(undefined), null);
});

test("webdriver outranks the probe path, so the mechanism is named first", () => {
  const verdict = classifyInternalTraffic({
    ...FOUNDER,
    webdriver: true,
    pathname: `${INTERNAL_PROBE_PREFIX}xyz123`,
  });
  assert.equal(verdict.reason, "webdriver");
});

test("every signal absent is still not internal", () => {
  // The SSR path: no navigator, no location, nothing to read.
  const verdict = classifyInternalTraffic({});
  assert.equal(verdict.internal, false);
  assert.equal(verdict.reason, null);
});
