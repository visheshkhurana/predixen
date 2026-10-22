import { flushPostHogQueue, type PostHogClient, type QueuedPostHogCall } from "./posthog-queue";
import { internalTrafficProperties } from "./internal-traffic";

// PostHog client tokens are public by design (they ship in the JS bundle).
// The default below is the real project token — the VITE_POSTHOG_KEY that was
// previously configured at build time pointed at a nonexistent project, so
// PostHog rejected every event with 401 and no analytics were ever ingested.
const POSTHOG_KEY = 'phc_C3jjovUPQChwDJoJdCp6E7adYRKBYSPETq5bNJw7pt6M';
const POSTHOG_HOST = import.meta.env?.VITE_POSTHOG_HOST || 'https://us.i.posthog.com';

type PostHogSdk = PostHogClient & {
  init: (apiKey: string, config: Record<string, unknown>) => void;
};

let client: PostHogSdk | null = null;
let loadPromise: Promise<PostHogSdk | null> | null = null;
const pending: QueuedPostHogCall[] = [];
let idleHandle: number | null = null;

function cancelIdleLoad() {
  if (idleHandle == null || typeof window === "undefined") return;
  if (typeof window.cancelIdleCallback === "function") {
    window.cancelIdleCallback(idleHandle);
  } else {
    window.clearTimeout(idleHandle);
  }
  idleHandle = null;
}

function resolveSdk(mod: { default?: PostHogSdk } & Partial<PostHogSdk>): PostHogSdk {
  const sdk = (mod.default ?? mod) as PostHogSdk;
  if (!sdk || typeof sdk.init !== "function") {
    throw new Error("posthog-js did not export an init() client");
  }
  return sdk;
}

async function loadAndInit(): Promise<PostHogSdk | null> {
  if (!POSTHOG_KEY || typeof window === "undefined") return null;
  try {
    const mod = await import("posthog-js");
    const sdk = resolveSdk(mod as { default?: PostHogSdk } & Partial<PostHogSdk>);
    sdk.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      // Send over XMLHttpRequest rather than fetch. A number of common browser
      // extensions (privacy blockers, anti-fingerprinting shims) monkey-patch
      // window.fetch and throw inside it, which silently kills every capture on
      // the default fetch transport while XHR sails through.
      api_transport: "XHR",
      // Off deliberately. App.tsx already fires trackPageView() on every route
      // change, including the first render, and wouter routing means the SDK's
      // own automatic capture cannot see client-side navigation anyway. With
      // both switched on, every single page load produced TWO $pageview events —
      // measurably: two events for the same path 258ms apart, same $device_id,
      // on 15 Aug. Every traffic number was inflated roughly 1.8x.
      capture_pageview: false,
      capture_pageleave: true,
      // Without this, $exception is never ingested and a JS error on the signup
      // page is completely invisible to us — we would see the drop-off and have
      // no way to tell a broken form from a bored visitor. Cheap insurance on the
      // one funnel step we cannot afford to be blind on.
      capture_exceptions: true,
      persistence: "localStorage",
      // Session replay: record marketing + auth funnel sessions so we can watch
      // where ad visitors drop off. Inputs are masked by default for privacy.
      disable_session_recording: false,
      session_recording: {
        maskAllInputs: true,
      },
    });
    client = sdk;
    flushPostHogQueue(sdk, pending);
    return sdk;
  } catch (err) {
    // Leave the queue intact and allow a later capture to retry the import.
    // Dropping events here would be a silent no-op — the failure mode this
    // wrapper exists to prevent.
    loadPromise = null;
    console.debug("PostHog unavailable", err);
    return null;
  }
}

function ensureClient(): Promise<PostHogSdk | null> {
  cancelIdleLoad();
  if (client) return Promise.resolve(client);
  if (!loadPromise) {
    loadPromise = loadAndInit();
  }
  return loadPromise;
}

function enqueue(call: QueuedPostHogCall) {
  pending.push(call);
  // Flush-on-first-capture: don't wait for requestIdleCallback if a real
  // identify / reset / $pageview / event is already in hand.
  void ensureClient();
}

/**
 * HAG-294. Attach the internal-traffic label to every call this module dispatches, so
 * `From search or AI` can be read as two numbers instead of one unreadable one.
 *
 * It is merged here, at the single choke point every event passes through, rather than
 * at the call sites: a tag that has to be remembered at each `trackEvent` is a tag that
 * will be missing from exactly the events that matter. The label wins over a caller's
 * own property of the same name, because it is derived from the environment rather
 * than passed in.
 *
 * It labels; it never drops. A filter that removes a real founder is worse than the
 * noise it removes.
 */
function tagInternalTraffic(call: QueuedPostHogCall): QueuedPostHogCall {
  if (typeof window === "undefined") return call;
  const tag = internalTrafficProperties();
  if (call.kind === "capture") {
    return { ...call, properties: { ...call.properties, ...tag } };
  }
  if (call.kind === "identify") {
    return { ...call, traits: { ...call.traits, ...tag } };
  }
  return call;
}

function dispatch(call: QueuedPostHogCall) {
  if (!POSTHOG_KEY) return;
  const tagged = tagInternalTraffic(call);
  if (client) {
    flushPostHogQueue(client, [tagged]);
    return;
  }
  enqueue(tagged);
}

/**
 * Kick off a single PostHog load. Prefer requestIdleCallback so posthog-js
 * (~240KB) stays out of the entry parse/eval path. Any capture / identify /
 * reset that arrives first cancels idle and loads immediately so early
 * funnel events ($pageview, cta_click, signup_view) are not dropped.
 *
 * Single init only — index.html must not also load array.js.
 */
export function initPostHog() {
  if (!POSTHOG_KEY || client || loadPromise || idleHandle != null) return;
  if (typeof window === "undefined") return;

  if (typeof window.requestIdleCallback === "function") {
    idleHandle = window.requestIdleCallback(
      () => {
        idleHandle = null;
        void ensureClient();
      },
      { timeout: 2500 },
    );
  } else {
    idleHandle = window.setTimeout(() => {
      idleHandle = null;
      void ensureClient();
    }, 1) as unknown as number;
  }
}

export function identifyUser(userId: number, email: string, role?: string) {
  dispatch({
    kind: "identify",
    distinctId: String(userId),
    traits: { email, role: role || "viewer" },
  });
}

/** posthog-js localStorage blob → distinct_id, or null when it isn't one. */
export function distinctIdFromPersistence(raw: string | null): string | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as { distinct_id?: unknown };
    const id = parsed?.distinct_id;
    if (typeof id !== "string") return null;
    const trimmed = id.trim();
    if (!trimmed || trimmed.length > 200 || trimmed.includes("@")) return null;
    return trimmed;
  } catch {
    return null;
  }
}

function readLoadedDistinctId(): string | null {
  const reader = client as { get_distinct_id?: () => unknown } | null;
  if (!reader || typeof reader.get_distinct_id !== "function") return null;
  try {
    const id = reader.get_distinct_id();
    return distinctIdFromPersistence(JSON.stringify({ distinct_id: id }));
  } catch {
    return null;
  }
}

function readPersistedDistinctId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return distinctIdFromPersistence(window.localStorage.getItem(`ph_${POSTHOG_KEY}_posthog`));
  } catch {
    return null;
  }
}

/**
 * Current browser distinct_id, for server events that must join this person.
 * Prefers the loaded SDK, then localStorage. Waits briefly for init so a
 * submit on a cold page still has an id. Null means the server should use
 * its email-hash fallback.
 */
export async function getBrowserDistinctId(): Promise<string | null> {
  if (!POSTHOG_KEY || typeof window === "undefined") return null;
  const loaded = readLoadedDistinctId();
  if (loaded) return loaded;
  const persisted = readPersistedDistinctId();
  if (persisted) return persisted;
  let timer: number | null = null;
  try {
    const sdk = await Promise.race([
      ensureClient(),
      new Promise<PostHogSdk | null>((resolve) => {
        timer = window.setTimeout(() => resolve(null), 1500);
      }),
    ]);
    if (sdk) {
      const id = readLoadedDistinctId();
      if (id) return id;
    }
  } catch {
    // persistence below is the remaining source
  } finally {
    if (timer != null) window.clearTimeout(timer);
  }
  return readPersistedDistinctId();
}

/**
 * Clears the current identity. Call this on an actual sign-out, never on a
 * page that merely happens to have no logged-in user.
 *
 * posthog.reset() mints a fresh distinct_id AND a fresh session_id. It used to
 * be called from an effect that ran whenever `user` was falsy — which is every
 * marketing page, on every load. The result was that a single visitor arrived,
 * got an identity, was immediately reset, and continued under a second one:
 * two identities and two sessions per visit, from one device.
 *
 * The damage was not cosmetic. An ad click landed on identity A and any later
 * signup would land on identity B, so no funnel could ever connect the two.
 * The account has spent AED 1,900 on clicks it could not have attributed.
 */
export function resetUser() {
  dispatch({ kind: "reset" });
}

export function trackPageView(path: string) {
  if (!POSTHOG_KEY) return;
  dispatch({
    kind: "capture",
    event: "$pageview",
    properties: { $current_url: window.location.href, path },
  });
}

export function trackEvent(event: string, properties?: Record<string, any>) {
  dispatch({ kind: "capture", event, properties });
}

/**
 * Super properties for every later event. `unset` drops keys this session
 * does not have, so a previous visit's campaign does not stick in
 * localStorage after a landing URL with no parameters.
 *
 * Queued, not loaded. The pageview / idle init flushes this before the
 * first event. Calling ensureClient here would pull posthog-js forward of
 * that path on every document.
 */
export function registerSuperProperties(
  properties: Record<string, string>,
  unset: readonly string[] = [],
) {
  if (!POSTHOG_KEY) return;
  const present: Record<string, string> = {};
  for (const [key, value] of Object.entries(properties)) {
    if (typeof value === "string" && value.length > 0) present[key] = value;
  }
  const presentKeys = new Set(Object.keys(present));
  const call: QueuedPostHogCall = {
    kind: "register",
    properties: present,
    unset: unset.filter((key) => !presentKeys.has(key)),
  };
  if (client) {
    flushPostHogQueue(client, [call]);
    return;
  }
  pending.push(call);
}

/** Test seam: the calls waiting to become PostHog super properties. */
export function takeQueuedPostHogCalls(): QueuedPostHogCall[] {
  return pending.splice(0, pending.length);
}

export const isPostHogEnabled = () => !!POSTHOG_KEY;
