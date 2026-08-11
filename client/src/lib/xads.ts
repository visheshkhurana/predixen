// X (Twitter) Ads conversion tracking.
//
// Inert until VITE_X_PIXEL_ID is set, so this ships safely before the pixel
// exists in X Events Manager. No pixel id → no script injected, no requests.
//
// Env:
//   VITE_X_PIXEL_ID      the "o..." id from X Events Manager (e.g. "oabc1")
//   VITE_X_EVENT_<STEP>  per-conversion event id, e.g. VITE_X_EVENT_SIGN_UP
//
// X's event ids are minted per conversion event inside Events Manager and look
// like `tw-<pixel>-<event>`. They cannot be derived from the pixel id, which is
// why each funnel step needs its own env var rather than a naming convention.

const PIXEL_ID = import.meta.env.VITE_X_PIXEL_ID as string | undefined;

/** Funnel step → X conversion event id. Missing entries are simply not sent. */
const EVENT_IDS: Record<string, string | undefined> = {
  cta_click: import.meta.env.VITE_X_EVENT_CTA_CLICK,
  signup_view: import.meta.env.VITE_X_EVENT_SIGNUP_VIEW,
  signup_start: import.meta.env.VITE_X_EVENT_SIGNUP_START,
  sign_up: import.meta.env.VITE_X_EVENT_SIGN_UP,
  onboarding_complete: import.meta.env.VITE_X_EVENT_ONBOARDING_COMPLETE,
  calculator_used: import.meta.env.VITE_X_EVENT_CALCULATOR_USED,
};

let loaded = false;

declare global {
  interface Window {
    twq?: ((...args: any[]) => void) & { queue?: any[]; version?: string; exe?: any };
  }
}

/**
 * Inject the X universal website tag once.
 *
 * Note for anyone extending this: the tag is fetched from
 * static.ads-twitter.com and beacons to analytics.twitter.com / t.co. All three
 * are listed in the CSP in server/index.ts. Adding an X feature without
 * updating that header fails silently — the browser blocks the request and the
 * pixel simply reports nothing, which looks identical to "no one converted".
 */
export function initXAds(): void {
  if (loaded || !PIXEL_ID || typeof window === "undefined") return;
  loaded = true;

  try {
    // Official uwt.js bootstrap, transcribed rather than pasted as a blob so
    // it can be read and audited.
    if (!window.twq) {
      const twq: any = function (...args: any[]) {
        twq.exe ? twq.exe.apply(twq, args) : twq.queue!.push(args);
      };
      twq.version = "1.1";
      twq.queue = [];
      window.twq = twq;

      const script = document.createElement("script");
      script.async = true;
      script.src = "https://static.ads-twitter.com/uwt.js";
      script.onerror = () => console.debug("[xads] tag unavailable");
      document.head.appendChild(script);
    }
    window.twq!("config", PIXEL_ID);
  } catch (err) {
    console.debug("[xads] init failed", err);
  }
}

/**
 * Forward a funnel step to X, if a conversion event id is configured for it.
 * Silent no-op otherwise — an unmapped step must never throw into the caller's
 * click handler.
 */
export function trackXConversion(step: string, params: Record<string, unknown> = {}): void {
  if (!PIXEL_ID || typeof window === "undefined") return;
  const eventId = EVENT_IDS[step];
  if (!eventId) return;

  try {
    initXAds();
    window.twq?.("event", eventId, {
      // X only accepts a known set of keys; anything else is dropped server
      // side. Value/currency are the two that matter for a free product's
      // "conversion value" reporting later.
      ...(typeof params.value === "number" ? { value: params.value } : {}),
      ...(params.currency ? { currency: params.currency } : {}),
    });
  } catch (err) {
    console.debug("[xads] event failed", err);
  }
}

export const xAdsEnabled = Boolean(PIXEL_ID);
