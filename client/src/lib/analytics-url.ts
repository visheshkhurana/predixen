/**
 * Query strings and hashes are credentials on this app:
 * /verify-email?token=, /unsubscribe?token=, /reset-password?token=,
 * /auth/callback?code=. PostHog copies the full browser URL into
 * $current_url, $referrer, $initial_* url/referrer, $set/$set_once, and
 * session-replay href. GA4 does the same for page_location / page_referrer.
 *
 * Strip those from every URL property on every path. Campaign keys
 * (utm_*, fbclid, gclid) are a separate first-touch capture and stay.
 */

export type PostHogBeforeSendEvent = {
  event: string;
  properties?: Record<string, unknown>;
  [key: string]: unknown;
};

/** PR #186 registers these from the landing query. They are not URLs. */
function isAttributionKey(key: string): boolean {
  return (
    /(?:^|_)utm_/i.test(key) ||
    /(?:^|_)(?:fbclid|gclid)$/i.test(key)
  );
}

/**
 * URL / referrer / href, plus pathname-adjacent path fields our pageview
 * and replay payloads carry next to href.
 */
function isUrlKey(key: string): boolean {
  if (isAttributionKey(key)) return false;
  return /url|referrer|referring|^href$|(?:^|\$)pathname$|(?:^|_)pathname$|(?:^|\$)path$|(?:^|_)path$/i.test(
    key,
  );
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const proto = Object.getPrototypeOf(value);
  return proto === Object.prototype || proto === null;
}

/** Drop ?query and #hash. http(s) results are origin + pathname. */
export function stripQueryAndHash(value: string): string {
  if (typeof value !== "string" || value.length === 0) return value;
  if (!value.includes("?") && !value.includes("#")) return value;
  try {
    const url = new URL(value, "https://founderconsole.ai");
    if (url.protocol === "http:" || url.protocol === "https:") {
      const absolute = /^[a-z][a-z0-9+.-]*:/i.test(value);
      if (absolute) return url.origin + url.pathname;
      if (value.startsWith("//")) return `//${url.host}${url.pathname}`;
      return url.pathname || "/";
    }
    url.search = "";
    url.hash = "";
    return url.toString();
  } catch {
    const hashless = value.split("#")[0] ?? value;
    return hashless.split("?")[0] ?? hashless;
  }
}

export function gtagPageFields(
  pageUrl: string,
  referrer = "",
): { page_location: string; page_referrer: string } {
  let page_location = pageUrl;
  try {
    const url = new URL(pageUrl, "https://founderconsole.ai");
    if (url.protocol === "http:" || url.protocol === "https:") {
      page_location = url.origin + url.pathname;
    } else {
      page_location = stripQueryAndHash(pageUrl);
    }
  } catch {
    page_location = stripQueryAndHash(pageUrl);
  }
  return {
    page_location,
    page_referrer: referrer ? stripQueryAndHash(referrer) : "",
  };
}

/** Params for gtag('config') and gtag('event', 'page_view' | ...). */
export function withGtagPage<T extends Record<string, unknown>>(
  params: T = {} as T,
): T & { page_location: string; page_referrer: string } {
  if (typeof window === "undefined") {
    return { ...params, page_location: "", page_referrer: "" };
  }
  const referrer = typeof document === "undefined" ? "" : document.referrer || "";
  return { ...params, ...gtagPageFields(window.location.href, referrer) };
}

function sanitizeNode(value: unknown): unknown {
  if (Array.isArray(value)) {
    let changed = false;
    const next = value.map((item) => {
      const updated = sanitizeNode(item);
      if (updated !== item) changed = true;
      return updated;
    });
    return changed ? next : value;
  }
  if (!isPlainObject(value)) return value;
  let changed = false;
  const next: Record<string, unknown> = {};
  for (const [key, child] of Object.entries(value)) {
    let updated = child;
    if (typeof child === "string" && isUrlKey(key)) {
      updated = stripQueryAndHash(child);
    } else if (child && typeof child === "object") {
      updated = sanitizeNode(child);
    }
    if (updated !== child) changed = true;
    next[key] = updated;
  }
  return changed ? next : value;
}

export function sanitizePostHogProperties(
  properties: Record<string, unknown>,
): Record<string, unknown> {
  const sanitized = sanitizeNode(properties);
  if (!isPlainObject(sanitized)) return properties;
  return sanitized;
}

/**
 * posthog-js before_send. Returning null would drop the event. This always
 * returns it, including $pageview, with URL properties reduced to
 * origin + pathname.
 */
export function beforeSendPostHog<T extends PostHogBeforeSendEvent | null | undefined>(
  event: T,
): T {
  if (!event?.properties) return event;
  try {
    const properties = sanitizePostHogProperties(event.properties);
    if (properties === event.properties) return event;
    return { ...event, properties };
  } catch {
    return event;
  }
}
