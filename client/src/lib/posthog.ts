import { flushPostHogQueue, type PostHogClient, type QueuedPostHogCall } from "./posthog-queue";

// PostHog client tokens are public by design (they ship in the JS bundle).
// The default below is the real project token — the VITE_POSTHOG_KEY that was
// previously configured at build time pointed at a nonexistent project, so
// PostHog rejected every event with 401 and no analytics were ever ingested.
const POSTHOG_KEY = 'phc_C3jjovUPQChwDJoJdCp6E7adYRKBYSPETq5bNJw7pt6M';
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com';

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

function dispatch(call: QueuedPostHogCall) {
  if (!POSTHOG_KEY) return;
  if (client) {
    flushPostHogQueue(client, [call]);
    return;
  }
  enqueue(call);
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

export const isPostHogEnabled = () => !!POSTHOG_KEY;
