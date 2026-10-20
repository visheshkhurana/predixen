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
 *   - the Meta pixel loads only while the surface is "marketing"
 *     (MarketingLayout). Core-app routes stay on "core" and never inject it.
 *
 * Pixel and measurement ids are the ones previously hardcoded in
 * MarketingLayout and index.html. No new env vars.
 */

export const COOKIE_CONSENT_KEY = "cookie-consent";
export const COOKIE_CONSENT_EVENT = "cookie-consent-change";

export const GA4_MEASUREMENT_ID = "G-NJKW0TGC4C";
export const META_PIXEL_ID = "872167299140812";

export const GA4_SCRIPT_SRC = `https://www.googletagmanager.com/gtag/js?id=${GA4_MEASUREMENT_ID}`;
export const META_PIXEL_SCRIPT_SRC = "https://connect.facebook.net/en_US/fbevents.js";

export type TrackingSurface = "marketing" | "core";

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
}): ConsentTracker {
  let surface: TrackingSurface = "core";
  let gaLoaded = false;
  let pixelLoaded = false;

  function apply() {
    if (!hasTrackingConsent(options.getConsent())) return;

    if (!gaLoaded) {
      gaLoaded = true;
      options.sink.append({ src: GA4_SCRIPT_SRC, async: true });
      installGtag(options.window);
    }

    if (surface === "marketing" && !pixelLoaded) {
      pixelLoaded = true;
      // Stub first, then insert the tag, matching the previous marketing snippet.
      // init/PageView are queued until fbevents.js replaces the stub.
      installFbq(options.window);
      options.sink.append({ src: META_PIXEL_SCRIPT_SRC, async: true });
      options.window.fbq!("init", META_PIXEL_ID);
      options.window.fbq!("track", "PageView");
    }
  }

  return {
    apply,
    setSurface(next: TrackingSurface) {
      surface = next;
      apply();
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
    sink: {
      append(script) {
        const el = host.document.createElement("script");
        el.async = script.async;
        el.src = script.src;
        if (script.src.indexOf("googletagmanager.com/gtag/js") !== -1) {
          el.onerror = () => console.debug("Analytics unavailable");
        }
        host.document.head.appendChild(el);
      },
    },
  });

  subscribeToConsent(host.window, () => tracker.apply());
  tracker.apply();
  return tracker;
}

let installed: ConsentTracker | null = null;
let surface: TrackingSurface = "core";

/** MarketingLayout opts in; leaving it returns the surface to the core app. */
export function setTrackingSurface(next: TrackingSurface) {
  surface = next;
  installed?.setSurface(next);
}

/**
 * Start listening. Safe to call more than once. No-ops during SSR.
 * Does not load either tag until consent is "accepted".
 */
export function installConsentTracking() {
  if (typeof window === "undefined" || typeof document === "undefined") return;
  if (!installed) {
    installed = mountConsentTracking({
      window: window as unknown as ConsentWindow,
      document: document as unknown as ConsentDocument,
    });
  }
  installed.setSurface(surface);
}
