/**
 * Consent-gated loader for GA4 and the Meta pixel.
 *
 * The cookie banner writes localStorage["cookie-consent"]. Nothing else used
 * to read it, so both tags loaded on first paint. This module is the only
 * place that injects gtag.js or fbevents.js:
 *
 *   - unset or anything other than "accepted" → no script tags
 *   - "accepted" → GA4 loads immediately (including when the banner flips
 *     to accepted in this tab)
 *   - the Meta pixel and the X Ads tag load only while the surface is
 *     "marketing" (MarketingLayout) and consent is "accepted". Core-app
 *     routes stay on "core": the pixel is never injected there, and every
 *     fbq / X call no-ops.
 *   - PageView is sent only from setTrackingSurface("marketing"), not by
 *     Meta's history.pushState hook (disablePushState + autoConfig off).
 *
 * Pixel and measurement ids are the ones previously hardcoded in
 * MarketingLayout and index.html. No new env vars. X still uses the
 * existing VITE_X_PIXEL_ID; with no id the X tag is not injected.
 */

export const COOKIE_CONSENT_KEY = "cookie-consent";
export const COOKIE_CONSENT_EVENT = "cookie-consent-change";

export const GA4_MEASUREMENT_ID = "G-NJKW0TGC4C";
export const META_PIXEL_ID = "872167299140812";

export const GA4_SCRIPT_SRC = `https://www.googletagmanager.com/gtag/js?id=${GA4_MEASUREMENT_ID}`;
export const META_PIXEL_SCRIPT_SRC = "https://connect.facebook.net/en_US/fbevents.js";
export const X_ADS_SCRIPT_SRC = "https://static.ads-twitter.com/uwt.js";

export type TrackingSurface = "marketing" | "core";

const trackingState: { surface: TrackingSurface } = { surface: "core" };
let marketingLive = false;

export function getTrackingSurface(): TrackingSurface {
  return trackingState.surface;
}

/** True only while the visitor is on a marketing surface and has accepted. */
export function marketingEventsEnabled(): boolean {
  return marketingLive;
}

export function readCookieConsent(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(COOKIE_CONSENT_KEY);
  } catch {
    return null;
  }
}

function publishSurface(next: TrackingSurface, consent: string | null) {
  trackingState.surface = next;
  marketingLive = next === "marketing" && hasTrackingConsent(consent);
}

export function hasTrackingConsent(value: string | null | undefined): boolean {
  return value === "accepted";
}

export interface ConsentScript {
  src: string;
  async: boolean;
}

export interface ConsentScriptSink {
  append(script: ConsentScript): void;
}

export interface ConsentWindow {
  dataLayer?: unknown[];
  gtag?: (...args: unknown[]) => void;
  fbq?: ((...args: unknown[]) => void) & {
    callMethod?: (...args: unknown[]) => void;
    queue?: unknown[];
    push?: unknown;
    loaded?: boolean;
    version?: string;
    disablePushState?: boolean;
  };
  __fcConsentMetaPixel?: boolean;
  localStorage?: { getItem(key: string): string | null };
  addEventListener(
    type: string,
    listener: (event?: { key?: string | null }) => void,
  ): void;
}

export interface ConsentDocument {
  createElement(tag: string): {
    async: boolean;
    src: string;
    onerror: (() => void) | null;
  };
  head: { appendChild(node: unknown): void };
}

export interface ConsentHost {
  window: ConsentWindow;
  document: ConsentDocument;
  getConsent?: () => string | null;
  /** When this returns an id, uwt.js is injected on an accepted marketing surface. */
  getXPixelId?: () => string | null;
  /** twq stub + config. The script tag itself is appended by the tracker. */
  bootstrapX?: () => void;
  /** Called when an accepted visitor switches to declined/rejected. */
  reload?: () => void;
}

export interface ConsentTracker {
  apply(): void;
  setSurface(surface: TrackingSurface): void;
}

function installGtag(target: ConsentWindow) {
  const dataLayer = (target.dataLayer = target.dataLayer || []);
  if (typeof target.gtag !== "function") {
    target.gtag = function gtag() {
      // Official gtag snippet: push the Arguments object, not a rest array.
      dataLayer.push(arguments);
    };
  }
  target.gtag("js", new Date());
  target.gtag("config", GA4_MEASUREMENT_ID);
}

function installFbq(target: ConsentWindow) {
  if (target.__fcConsentMetaPixel && typeof target.fbq === "function") return;
  const fbq = function fbq(this: unknown) {
    // Core-app routes must not emit, even after the real library attaches
    // callMethod. The surface is read at call time, not at install time.
    if (trackingState.surface !== "marketing") return;
    const self = target.fbq!;
    if (typeof self.callMethod === "function") {
      self.callMethod.apply(self, arguments as unknown as unknown[]);
    } else {
      self.queue!.push(arguments);
    }
  } as ConsentWindow["fbq"];
  target.fbq = fbq;
  fbq!.push = fbq;
  fbq!.loaded = true;
  fbq!.version = "2.0";
  fbq!.queue = [];
  // Set before init so fbevents.js does not hook history.pushState and
  // auto-fire PageView on SPA navigations, including into the core app.
  fbq!.disablePushState = true;
  target.__fcConsentMetaPixel = true;
}

/**
 * Pure loader. Default surface is "core", so a caller that forgets to opt
 * into marketing cannot inject the pixel.
 */
export function createConsentTracker(options: {
  getConsent: () => string | null;
  sink: ConsentScriptSink;
  window: ConsentWindow;
  getXPixelId?: () => string | null;
  bootstrapX?: () => void;
}): ConsentTracker {
  // A fresh tracker must not inherit a marketing surface from an earlier page.
  publishSurface("core", options.getConsent());
  let gaLoaded = false;
  let pixelLoaded = false;
  let xLoaded = false;

  function manualPageView() {
    if (trackingState.surface !== "marketing") return;
    if (!hasTrackingConsent(options.getConsent())) return;
    if (!pixelLoaded || typeof options.window.fbq !== "function") return;
    options.window.fbq("track", "PageView");
  }

  function apply() {
    publishSurface(trackingState.surface, options.getConsent());
    if (!hasTrackingConsent(options.getConsent())) return;

    if (!gaLoaded) {
      gaLoaded = true;
      options.sink.append({ src: GA4_SCRIPT_SRC, async: true });
      installGtag(options.window);
    }

    if (trackingState.surface === "marketing" && !pixelLoaded) {
      pixelLoaded = true;
      // Stub (with disablePushState) before the tag, then autoConfig, then init.
      // PageView is not sent here — only setSurface("marketing") sends it.
      installFbq(options.window);
      options.sink.append({ src: META_PIXEL_SCRIPT_SRC, async: true });
      options.window.fbq!("set", "autoConfig", false, META_PIXEL_ID);
      options.window.fbq!("init", META_PIXEL_ID);
    }

    const xPixelId = options.getXPixelId?.() ?? null;
    if (trackingState.surface === "marketing" && xPixelId && !xLoaded) {
      xLoaded = true;
      options.sink.append({ src: X_ADS_SCRIPT_SRC, async: true });
      options.bootstrapX?.();
    }
  }

  return {
    apply,
    setSurface(next: TrackingSurface) {
      publishSurface(next, options.getConsent());
      apply();
      if (next === "marketing") manualPageView();
    },
  };
}

export function subscribeToConsent(
  target: ConsentWindow,
  onChange: () => void,
) {
  target.addEventListener(COOKIE_CONSENT_EVENT, () => onChange());
  target.addEventListener("storage", (event) => {
    if (event?.key === COOKIE_CONSENT_KEY) onChange();
  });
}

export function mountConsentTracking(host: ConsentHost): ConsentTracker {
  const getConsent =
    host.getConsent ??
    (() => {
      try {
        return host.window.localStorage?.getItem(COOKIE_CONSENT_KEY) ?? null;
      } catch {
        return null;
      }
    });

  const tracker = createConsentTracker({
    getConsent,
    window: host.window,
    getXPixelId: host.getXPixelId,
    bootstrapX: host.bootstrapX,
    sink: {
      append(script) {
        const el = host.document.createElement("script");
        el.async = script.async;
        el.src = script.src;
        if (script.src.indexOf("googletagmanager.com/gtag/js") !== -1) {
          el.onerror = () => console.debug("Analytics unavailable");
        }
        if (script.src === X_ADS_SCRIPT_SRC) {
          el.onerror = () => console.debug("[xads] tag unavailable");
        }
        host.document.head.appendChild(el);
      },
    },
  });

  const reload =
    host.reload ??
    (() => {
      if (typeof location !== "undefined" && typeof location.reload === "function") {
        location.reload();
      }
    });

  let previous = getConsent();
  subscribeToConsent(host.window, () => {
    const next = getConsent();
    // Already-loaded tags cannot be unloaded. A withdrawal reloads so the
    // next document starts with no pixel and no X tag.
    if (previous === "accepted" && (next === "declined" || next === "rejected")) {
      previous = next;
      reload();
      return;
    }
    const becameAccepted = previous !== "accepted" && next === "accepted";
    previous = next;
    if (becameAccepted && trackingState.surface === "marketing") {
      tracker.setSurface("marketing");
      return;
    }
    tracker.apply();
  });
  tracker.apply();
  return tracker;
}

function readXPixelId(): string | null {
  try {
    const id = import.meta.env.VITE_X_PIXEL_ID as string | undefined;
    return typeof id === "string" && id ? id : null;
  } catch {
    return null;
  }
}

let installed: ConsentTracker | null = null;

/**
 * MarketingLayout opts in. PageView is sent from this transition only.
 * Leaving the layout returns the surface to the core app, where fbq and X no-op.
 */
export function setTrackingSurface(next: TrackingSurface) {
  if (!installed) {
    publishSurface(next, readCookieConsent());
    return;
  }
  installed.setSurface(next);
}

/**
 * Start listening. Safe to call more than once. No-ops during SSR.
 * Does not load either tag until consent is "accepted".
 */
export function installConsentTracking() {
  if (typeof window === "undefined" || typeof document === "undefined") return;
  // mount() resets the surface to core. Keep a choice made before install.
  const pending = trackingState.surface;
  if (!installed) {
    installed = mountConsentTracking({
      window: window as unknown as ConsentWindow,
      document: document as unknown as ConsentDocument,
      getXPixelId: readXPixelId,
      bootstrapX: () => {
        void import("./xads").then((mod) => mod.initXAds());
      },
    });
  }
  installed.setSurface(pending);
}
