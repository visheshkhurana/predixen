// Client waits on Retry-After once. Run: npx tsx --test server/tests/rate-limit-backoff.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { backoffMsFor429 } from "../../client/src/lib/rateLimitBackoff";

test("backoff prefers Retry-After and caps the wait", () => {
  assert.equal(backoffMsFor429("12", null), 12_000);
  assert.equal(backoffMsFor429(null, 12), 12_000);
  assert.equal(backoffMsFor429(null, null), 5_000);
  assert.equal(backoffMsFor429("90", null), 60_000);
  assert.equal(backoffMsFor429("0", null), 0);
  assert.equal(backoffMsFor429("12", 1), 12_000);
});

test("api client does not retry-storm a 429", () => {
  const src = readFileSync(new URL("../../client/src/api/client.ts", import.meta.url), "utf8");
  assert.match(src, /const RETRYABLE_STATUS_CODES = \[502, 503, 504\]/);
  assert.match(src, /backoffMsFor429/);
  assert.equal(src.includes("429, 502") || src.includes("[429,"), false);
});
