// First-touch campaign capture. The landing URL is read once per tab and
// reused for PostHog super properties, POST /api/leads, and signup.
//
// Run: npx tsx --test server/tests/attribution-first-touch.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  ATTRIBUTION_KEYS,
  ATTRIBUTION_STORAGE_KEY,
  attributionFromSearch,
  captureFirstTouch,
  readFirstTouchAttribution,
  readStoredAttribution,
  type AttributionStorage,
} from "../../client/src/lib/attribution";
import { flushPostHogQueue, type QueuedPostHogCall } from "../../client/src/lib/posthog-queue";

const attributionSrc = readFileSync("client/src/lib/attribution.ts", "utf8");
const app = readFileSync("client/src/App.tsx", "utf8");
const optIn = readFileSync("client/src/components/marketing/CalculatorEmailOptIn.tsx", "utf8");
const api = readFileSync("client/src/api/client.ts", "utf8");
const posthogLib = readFileSync("client/src/lib/posthog.ts", "utf8");
const queueSrc = readFileSync("client/src/lib/posthog-queue.ts", "utf8");

function memoryStorage(): AttributionStorage & { data: Record<string, string> } {
  const data: Record<string, string> = {};
  return {
    data,
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : null;
    },
    setItem(key, value) {
      data[key] = value;
    },
  };
}

const LANDING =
  "?utm_source=google&utm_medium=cpc&utm_campaign=spring&utm_content=ad" +
  "&utm_term=runway%20calculator&fbclid=fb-1&gclid=gc-1&ip=203.0.113.9&email=a@b.c";

test("landing URL params are captured and unrelated params are ignored", () => {
  const found = attributionFromSearch(LANDING);
  assert.deepEqual(found, {
    utm_source: "google",
    utm_medium: "cpc",
    utm_campaign: "spring",
    utm_content: "ad",
    utm_term: "runway calculator",
    fbclid: "fb-1",
    gclid: "gc-1",
  });
  assert.equal("ip" in found, false);
  assert.equal("email" in found, false);
});

test("values are trimmed, control characters removed, and capped at 200", () => {
  const long = "x".repeat(240);
  const found = attributionFromSearch(
    `?utm_source=%20%20google%20&utm_medium=${long}&fbclid=%0Afb`,
  );
  assert.equal(found.utm_source, "google");
  assert.equal(found.utm_medium?.length, 200);
  assert.equal(found.fbclid, "fb");
});

test("first page load writes session storage once, including an empty landing URL", () => {
  const storage = memoryStorage();
  const first = captureFirstTouch(storage, LANDING);
  assert.equal(first.utm_source, "google");
  assert.equal(first.gclid, "gc-1");
  const raw = storage.data[ATTRIBUTION_STORAGE_KEY];
  assert.equal(raw, JSON.stringify(first));

  const later = captureFirstTouch(
    storage,
    "?utm_source=facebook&utm_medium=paid&fbclid=overwrite",
  );
  assert.equal(later.utm_source, "google");
  assert.equal(later.utm_medium, "cpc");
  assert.equal(storage.data[ATTRIBUTION_STORAGE_KEY], raw);
  assert.deepEqual(readStoredAttribution(storage), first);
});

test("an empty first touch blocks a later URL in the same session", () => {
  const storage = memoryStorage();
  assert.deepEqual(captureFirstTouch(storage, ""), {});
  assert.deepEqual(captureFirstTouch(storage, "?utm_source=later&gclid=abc"), {});
  assert.equal(storage.data[ATTRIBUTION_STORAGE_KEY], "{}");
});

test("corrupt stored JSON is kept and does not throw", () => {
  const storage = memoryStorage();
  storage.setItem(ATTRIBUTION_STORAGE_KEY, "{");
  assert.deepEqual(captureFirstTouch(storage, LANDING), {});
  assert.equal(storage.data[ATTRIBUTION_STORAGE_KEY], "{");
});

test("the capture module does not read an IP or the document referrer", () => {
  assert.deepEqual(ATTRIBUTION_KEYS, [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "fbclid",
    "gclid",
  ]);
  assert.doesNotMatch(attributionSrc, /ip_address|clientIp|remoteAddress|x-forwarded-for|document\.referrer/i);
  assert.match(attributionSrc, /registerSuperProperties\(captured, unset\)/);
});

test("first page load captures before React route effects", () => {
  assert.match(
    app,
    /if \(typeof window !== "undefined"\) \{\s*captureFirstTouchAttribution\(\);\s*\}/,
  );
  const captureAt = app.indexOf("captureFirstTouchAttribution()");
  const appFn = app.indexOf("function App()");
  assert.ok(captureAt !== -1 && captureAt < appFn, "capture runs when the module loads");
});

test("lead and signup payloads spread the stored touch", () => {
  assert.match(optIn, /fetch\("\/api\/leads"/);
  assert.match(optIn, /\.\.\.readFirstTouchAttribution\(\)/);
  assert.match(api, /\/auth\/register/);
  assert.match(api, /\.\.\.readFirstTouchAttribution\(\)/);
  assert.match(posthogLib, /kind:\s*"register"/);
  assert.match(queueSrc, /client\.register\?\.\(call\.properties\)/);
  assert.match(queueSrc, /client\.unregister\?\.\(key\)/);
});

test("register flushes after unsetting keys this session does not have", () => {
  const seen: string[] = [];
  const fake = {
    identify() {},
    reset() {},
    capture() {},
    register(properties: Record<string, unknown>) {
      seen.push(`register:${JSON.stringify(properties)}`);
    },
    unregister(property: string) {
      seen.push(`unregister:${property}`);
    },
  };
  const queue: QueuedPostHogCall[] = [
    {
      kind: "register",
      properties: { utm_source: "google" },
      unset: ["utm_medium", "gclid"],
    },
  ];
  flushPostHogQueue(fake, queue);
  assert.deepEqual(seen, [
    "unregister:utm_medium",
    "unregister:gclid",
    'register:{"utm_source":"google"}',
  ]);
  assert.equal(queue.length, 0);
});

test("readFirstTouchAttribution is a no-op without a browser window", () => {
  assert.deepEqual(readFirstTouchAttribution(), {});
});
