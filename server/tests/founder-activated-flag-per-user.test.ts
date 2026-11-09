// Guards the browser-side half of `founder_activated`: the "already emitted"
// flag must be keyed by user id.
//
// The bug this pins: the flag was one browser-wide `fc_founder_activated`. On a
// shared browser the first account to activate set it and every later account
// emitted nothing — neither the client copy nor the pair. It is a MISSING event,
// which is invisible to the control built to catch split identities: a dropped
// event shrinks `count()` and `uniqExact(user_id)` together, so the ratio still
// reads 1.0. Test 2 below is the defect; reverting activation-flag.ts to the old
// browser-wide key reds exactly that one.
//
// Run: npx tsx server/tests/founder-activated-flag-per-user.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  founderActivatedFlagKey,
  rememberFounderActivated,
  shouldEmitFounderActivated,
  type FlagStore,
} from "../../client/src/lib/activation-flag";

function memoryStore(): FlagStore & { keys(): string[] } {
  const map = new Map<string, string>();
  return {
    getItem: (k) => (map.has(k) ? map.get(k)! : null),
    setItem: (k, v) => void map.set(k, v),
    keys: () => [...map.keys()],
  };
}

test("the flag key carries the user id", () => {
  assert.equal(founderActivatedFlagKey(42), "fc_founder_activated:42");
  assert.equal(founderActivatedFlagKey("42"), "fc_founder_activated:42");
  assert.notEqual(founderActivatedFlagKey(42), founderActivatedFlagKey(43));
});

test("a second account on the same browser still emits (the defect)", () => {
  const store = memoryStore();
  // Account 42 activates: emits once, and never again on reload.
  assert.equal(shouldEmitFounderActivated(store, 42), true);
  rememberFounderActivated(store, 42);
  assert.equal(shouldEmitFounderActivated(store, 42), false);
  // Account 43 signs in on the same browser: the browser-wide flag used to
  // silence this emit. It must not.
  assert.equal(shouldEmitFounderActivated(store, 43), true);
});

test("each user's flag is its own key, not a rewrite of one", () => {
  const store = memoryStore();
  rememberFounderActivated(store, 42);
  rememberFounderActivated(store, 43);
  assert.deepEqual(store.keys().sort(), [
    "fc_founder_activated:42",
    "fc_founder_activated:43",
  ]);
});

test("a blocked or absent store emits rather than losing the activation", () => {
  assert.equal(shouldEmitFounderActivated(null, 42), true);
  assert.equal(shouldEmitFounderActivated(undefined, 42), true);
  assert.doesNotThrow(() => rememberFounderActivated(null, 42));
  // A store that throws on read (private mode) is treated as absent.
  const throwing: FlagStore = {
    getItem: () => {
      throw new Error("blocked");
    },
    setItem: () => {
      throw new Error("blocked");
    },
  };
  assert.equal(shouldEmitFounderActivated(throwing, 42), true);
  assert.doesNotThrow(() => rememberFounderActivated(throwing, 42));
});

test("funnel.ts keys the guard by user id and keeps no browser-wide constant", () => {
  const funnel = readFileSync("client/src/lib/funnel.ts", "utf8");
  assert.doesNotMatch(
    funnel,
    /const FOUNDER_ACTIVATED_KEY/,
    "the browser-wide constant is back — that is the defect",
  );
  assert.match(funnel, /shouldEmitFounderActivated\(store, params\.user_id\)/);
  assert.match(funnel, /rememberFounderActivated\(store, params\.user_id\)/);
  assert.match(funnel, /user_id\?: number \| string \| null/);
});

test("both activation call sites pass the current user id", () => {
  const hooks = readFileSync("client/src/api/hooks.ts", "utf8");
  const calls = hooks.match(/trackFounderActivated\(\{/g) ?? [];
  assert.equal(calls.length, 2, "expected exactly two activation call sites");
  const withUserId = hooks.match(
    /trackFounderActivated\(\{[\s\S]{0,220}?user_id: useFounderStore\.getState\(\)\.user\?\.id/g,
  ) ?? [];
  assert.equal(
    withUserId.length,
    2,
    "a call site emits without a user id, so its flag cannot be scoped",
  );
});
