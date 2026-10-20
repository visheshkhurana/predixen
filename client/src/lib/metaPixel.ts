/**
 * Meta (Facebook) Pixel — privacy-scoped loader.
 *
 * Loads only on public marketing pages, per the Privacy Policy.
 * Never active inside the core app.
 *
 * Enablement is the code constant META_PIXEL_ENABLED, not an env var.
 * The marketing shell is what installs fbq. metaTrack is a no-op when fbq
 * is absent (a later change consent-gates that load) and a no-op on any
 * core-app route. Each event that does fire gets an eventID for a later
 * Conversions API dedupe. Email and other personal data are never sent.
 */

/** Flip to false to silence the pixel without adding an env var. */
export const META_PIXEL_ENABLED = true;

/**
 * Same pixel the marketing shell already initialized inline
 * (`872167299140812`). One id, one loader.
 */
export const META_PIXEL_ID = "872167299140812";

const PIXEL_ID = META_PIXEL_ID;

/**
 * Public pages that render MarketingLayout. The pixel script is installed
 * only from that shell. Auth, onboarding, billing, and the signed-in app
 * are not in this set.
 */
const MARKETING_EXACT = new Set([
  "/",
  "/about",
  "/ai-cfo",
  "/alternatives",
  "/blog",
  "/compare",
  "/contact",
  "/customers",
  "/default-alive",
  "/demo",
  "/faq",
  "/features",
  "/how-it-works",
  "/pricing",
  "/product",
  "/security",
  "/survival-simulator",
  "/tools",
  "/use-cases",
]);

const MARKETING_PREFIXES = ["/blog/", "/runway/", "/survival/", "/tools/", "/vs/"];

/** True when the code constant says the pixel may fire. */
export function isMetaPixelEnabled(): boolean {
  return META_PIXEL_ENABLED;
}

function currentPath(): string {
  if (typeof window === "undefined") return "";
  try {
    const path = window.location?.pathname;
    if (typeof path !== "string" || path.length === 0) return "";
    return path.split("?")[0];
  } catch {
    return "";
  }
}

/** True on a public marketing page. False inside the core app. */
export function isMetaPixelSurface(pathname?: string): boolean {
  const path = pathname ?? currentPath();
  if (MARKETING_EXACT.has(path)) return true;
  return MARKETING_PREFIXES.some((prefix) => path.startsWith(prefix));
}

function fbqFn(): ((...args: unknown[]) => void) | null {
  if (typeof window === "undefined") return null;
  const fbq = (window as any).fbq;
  return typeof fbq === "function" ? fbq : null;
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
  if (!isMetaPixelSurface()) return false;
  if (typeof window === "undefined" || typeof document === "undefined") return false;
  if (fbqFn()) return true;
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
    return true;
  } catch {
    return false;
  }
}

function send(event: string, params?: Record<string, unknown>): string | null {
  const fbq = fbqFn();
  if (!fbq) return null;
  const eventId = createMetaEventId();
  fbq("track", event, metaPixelParams(params), { eventID: eventId });
  return eventId;
}

/** PageView on public marketing pages (call from MarketingLayout). Installs fbq. */
export function metaPageView(): string | null {
  try {
    if (!ensureLoaded()) return null;
    return send("PageView");
  } catch {
    return null;
  }
}

/**
 * Standard or custom event.
 * No-op unless this is a marketing page and fbq is already loaded.
 * Does not install the pixel. Personal fields in `params` are removed.
 * Returns the event id passed as fbq `eventID`, or null when it does not fire.
 */
export function metaTrack(
  event: string,
  params?: Record<string, unknown>,
): string | null {
  try {
    if (!isMetaPixelEnabled() || !isMetaPixelSurface()) return null;
    return send(event, params);
  } catch {
    return null;
  }
}
