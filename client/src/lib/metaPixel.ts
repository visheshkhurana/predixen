/**
 * Meta (Facebook) Pixel.
 *
 * Enablement is a code constant, not an env var. `META_PIXEL_ENABLED` true
 * loads the pixel and lets `metaTrack` fire. False makes every helper a no-op.
 *
 * Events carry a fresh `eventID` so a later Conversions API call can dedupe
 * against the browser event. Email and other personal data never go to fbq.
 */

/** Flip to false to silence the pixel without adding an env var. */
export const META_PIXEL_ENABLED = true;

/**
 * Same pixel the marketing shell already initialized inline
 * (`872167299140812`). One id, one loader.
 */
export const META_PIXEL_ID = "872167299140812";

const PIXEL_ID = META_PIXEL_ID;

let loaded = false;

/** True when the code constant says the pixel may fire. */
export function isMetaPixelEnabled(): boolean {
  return META_PIXEL_ENABLED;
}

const PII_KEYS = new Set([
  "email",
  "e-mail",
  "user_email",
  "phone",
  "first_name",
  "last_name",
  "firstname",
  "lastname",
  "full_name",
  "name",
  "em",
  "ph",
  "fn",
  "ln",
  "external_id",
  "user_id",
  "distinct_id",
  "db",
  "ge",
  "ct",
  "st",
  "zp",
  "zip",
  "address",
  "client_ip_address",
  "ip",
]);

const EMAIL_RE = /[^\s@]+@[^\s@]+\.[^\s@]+/;

/** Drop email and other personal fields before they can reach fbq. */
export function metaPixelParams(
  params?: Record<string, unknown>,
): Record<string, unknown> {
  if (!params) return {};
  const safe: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(params)) {
    if (PII_KEYS.has(key.toLowerCase())) continue;
    if (typeof value === "string" && EMAIL_RE.test(value)) continue;
    safe[key] = value;
  }
  return safe;
}

/** One id per browser event. Pass the same value to CAPI later to dedupe. */
export function createMetaEventId(): string {
  const cryptoObj = globalThis.crypto;
  if (cryptoObj && typeof cryptoObj.randomUUID === "function") {
    return cryptoObj.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (ch) => {
    const r = Math.floor(Math.random() * 16);
    const v = ch === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function ensureLoaded(): boolean {
  if (!isMetaPixelEnabled() || !PIXEL_ID) return false;
  if (typeof window === "undefined" || typeof document === "undefined") return false;
  if (loaded) return typeof (window as any).fbq === "function";
  try {
    /* eslint-disable */
    (function (f: any, b: any, e: any, v: any, n?: any, t?: any, s?: any) {
      if (f.fbq) return;
      n = f.fbq = function () {
        n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
      };
      if (!f._fbq) f._fbq = n;
      n.push = n; n.loaded = true; n.version = '2.0'; n.queue = [];
      t = b.createElement(e); t.async = true; t.src = v;
      s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
    })(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
    /* eslint-enable */
    (window as any).fbq("init", PIXEL_ID);
    loaded = true;
    return true;
  } catch {
    return false;
  }
}

function track(event: string, params?: Record<string, unknown>): string | null {
  if (!ensureLoaded()) return null;
  const eventId = createMetaEventId();
  (window as any).fbq("track", event, metaPixelParams(params), { eventID: eventId });
  return eventId;
}

/** PageView on public marketing pages (call from MarketingLayout). */
export function metaPageView(): string | null {
  try {
    return track("PageView");
  } catch {
    return null;
  }
}

/**
 * Standard or custom event (Lead, CompleteRegistration, Subscribe, ...).
 * Returns the event id passed as fbq `eventID`, or null when the pixel is off.
 * Personal fields in `params` are removed and never sent.
 */
export function metaTrack(
  event: string,
  params?: Record<string, unknown>,
): string | null {
  try {
    return track(event, params);
  } catch {
    return null;
  }
}
