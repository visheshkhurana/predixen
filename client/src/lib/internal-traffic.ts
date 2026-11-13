/**
 * HAG-294: tell the floor's own visits apart from a founder's, as a *label* rather
 * than a filter.
 *
 * Why this exists. `founderconsole/scoreboard/latest.md` reports `From search or AI`
 * as a single number, and its own note 3 says that number cannot be read: "Much of
 * this week's traffic is our own agents. `/this-page-does-not-exist-xyz123` is the
 * floor's 404 test, and the 7 'bing.com' visits at 16:00 UTC landed on it too - very
 * likely our own checks or a crawler, not founders." The daily golden path fires at
 * 07:30 UTC and loads pages in a real browser, so the instrument that checks the site
 * is itself a counted visitor; and the dead URL answers `HTTP 200` with the same
 * 4,558-byte shell as a live route, so nothing keyed off status can separate the two.
 *
 * The fix is the opposite of a filter. Every event carries `fc_internal`, and the
 * column is read as two numbers - `From search or AI (verified)` and
 * `... (unverified)`. A hard filter that drops a real founder is worse than the noise
 * it removes, so nothing here ever suppresses an event. It only labels it.
 *
 * **What this cannot see, stated rather than hidden.** This runs in a browser, so it
 * only labels visits that execute our JS. That covers our Playwright checks, our
 * crawler checks and any headed browser. It does *not* cover a raw HTTP client, and
 * that is not a gap: a client that never runs the bundle never fires a PostHog event,
 * so it was never in the column to begin with.
 *
 * **It also cannot see Vishesh's own browser**, because a normal browser is
 * indistinguishable from a founder's by every signal available here. That is what the
 * explicit flag below is for: setting `fc_internal` once (or landing on any URL with
 * `?fc_internal=1`) labels that browser for good, since the param is persisted.
 */

/** localStorage key, and the query param that writes it. */
export const INTERNAL_FLAG_KEY = "fc_internal";
/**
 * Marker in `navigator.userAgent`. Our own checks and crawler set it; a real browser
 * never contains it. Kept as a substring test, not a regex, so it cannot be fooled by
 * a UA that merely resembles it.
 */
export const INTERNAL_UA_MARKER = "FounderConsoleHive";
/**
 * The floor's 404 test path. This is the exact prefix `latest.md` names, and it is the
 * reason the column is unreadable today: those visits look like a founder landing on
 * the site. Checking the prefix catches the probe even when it is driven by something
 * that does not set `navigator.webdriver`.
 */
export const INTERNAL_PROBE_PREFIX = "/this-page-does-not-exist-";

/** Why a visit was labelled internal. `null` when it was not. */
export type InternalReason =
  | "flag"
  | "webdriver"
  | "internal-user-agent"
  | "internal-probe-path";

export interface InternalSignals {
  /** `navigator.webdriver` - true under Playwright / Puppeteer / Selenium. */
  webdriver?: boolean;
  /** `navigator.userAgent`. */
  userAgent?: string;
  /** `location.pathname`. */
  pathname?: string;
  /** `location.search`, including the leading `?`. */
  search?: string;
  /** A previously persisted flag, if the caller has already read storage. */
  storedFlag?: string | null;
}

export interface InternalVerdict {
  internal: boolean;
  /** Set only when `internal` is true. */
  reason: InternalReason | null;
}

/** The `?fc_internal=` value, or null. Accepts anything non-empty; the value is the note. */
export function flagFromSearch(search: string | undefined): string | null {
  if (!search) return null;
  const params = new URLSearchParams(search.startsWith("?") ? search : `?${search}`);
  const value = params.get(INTERNAL_FLAG_KEY);
  return value && value.length > 0 ? value : null;
}

/**
 * Decide whether this visit is one of ours.
 *
 * Pure, so it can be tested without a DOM, and ordered so the most deliberate signal
 * wins: an explicit flag beats a UA marker, which beats the probe path. Only the
 * reason is ordered - any one signal is enough to set `internal`.
 */
export function classifyInternalTraffic(signals: InternalSignals): InternalVerdict {
  const flagged = signals.storedFlag ?? flagFromSearch(signals.search);
  if (flagged) return { internal: true, reason: "flag" };

  if (signals.webdriver === true) return { internal: true, reason: "webdriver" };

  if (signals.userAgent && signals.userAgent.includes(INTERNAL_UA_MARKER)) {
    return { internal: true, reason: "internal-user-agent" };
  }

  const pathname = signals.pathname ?? "";
  if (pathname.startsWith(INTERNAL_PROBE_PREFIX)) {
    return { internal: true, reason: "internal-probe-path" };
  }

  return { internal: false, reason: null };
}

/** Read storage without throwing: private mode and blocked storage both throw. */
function readStoredFlag(): string | null {
  try {
    return window.localStorage.getItem(INTERNAL_FLAG_KEY);
  } catch {
    return null;
  }
}

/**
 * Persist the flag when `?fc_internal=` is present, so a labelled browser stays
 * labelled across client-side navigation and across sessions. Best-effort: if storage
 * is unavailable the visit is still labelled for this page load.
 */
function persistFlagFromUrl(): void {
  try {
    const fromUrl = flagFromSearch(window.location.search);
    if (fromUrl && !window.localStorage.getItem(INTERNAL_FLAG_KEY)) {
      window.localStorage.setItem(INTERNAL_FLAG_KEY, fromUrl);
    }
  } catch {
    // storage blocked - the URL signal still applies to this load
  }
}

/**
 * Browser wrapper around the classifier. Safe to call anywhere in the client, and
 * returns "not internal" rather than throwing when there is no window (SSR).
 */
export function detectInternalTraffic(): InternalVerdict {
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    return { internal: false, reason: null };
  }
  persistFlagFromUrl();
  return classifyInternalTraffic({
    webdriver: navigator.webdriver === true,
    userAgent: navigator.userAgent,
    pathname: window.location.pathname,
    search: window.location.search,
    storedFlag: readStoredFlag(),
  });
}

/**
 * The properties merged into every event. Always both keys, so a query can test
 * `fc_internal = false` for the verified number rather than for "absent", which would
 * also match events sent before this shipped.
 */
export function internalTrafficProperties(): Record<string, unknown> {
  const verdict = detectInternalTraffic();
  return { fc_internal: verdict.internal, fc_internal_reason: verdict.reason };
}
