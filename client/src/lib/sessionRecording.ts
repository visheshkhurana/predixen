/**
 * Session replay gate.
 *
 * Recording starts only on public marketing routes after
 * localStorage["cookie-consent"] === "accepted". Every other route is the
 * core app (overview, simulate, billing, settings, copilot, onboarding, auth,
 * signup, and the rest of the signed-in product) and recording is stopped.
 *
 * PR #188 (not on main) owns GA4 / Meta / X in consentTracking.ts and switches
 * surface with setTrackingSurface / setSurface. That module is not imported
 * here. #188 can call the hooks below from its own setTrackingSurface:
 *
 *   import { setTrackingSurface as setSessionRecordingSurface } from "./sessionRecording";
 *
 * Route changes call syncSessionRecording(path) as well, so replay stops on
 * the way into the product even before #188 lands.
 *
 * $pageview and named captures are not gated here.
 */

export const COOKIE_CONSENT_KEY = "cookie-consent";
/** Same name #188 dispatches from the cookie banner. */
export const COOKIE_CONSENT_EVENT = "cookie-consent-change";

export type TrackingSurface = "marketing" | "core";

export type SessionRecordingControls = {
  startSessionRecording?: (...args: unknown[]) => void;
  stopSessionRecording?: () => void;
};

export type RecordingDecision = "start" | "stop";

export type RecordingRuntime = {
  client: SessionRecordingControls | null;
  surface: TrackingSurface;
  readConsent: () => string | null;
};

/** Public pages that do not render a founder's own books. */
const MARKETING_EXACT = new Set([
  "/",
  "/features",
  "/product",
  "/pricing",
  "/about",
  "/compare",
  "/customers",
  "/use-cases",
  "/how-it-works",
  "/alternatives",
  "/blog",
  "/faq",
  "/contact",
  "/demo",
  "/demo/enter",
  "/survival-simulator",
  "/default-alive",
  "/privacy",
  "/terms",
  "/security",
  "/ai-cfo",
  "/tools",
  "/embed/survival",
]);

const MARKETING_PREFIXES = [
  "/blog/",
  "/tools/",
  "/survival/",
  "/runway/",
  "/embed/",
  "/vs/",
];

/**
 * Pages whose query string can carry calculator inputs.
 * The embed widget opens
 * /survival-simulator?cash=&burn=&revenue=&utm_source=embed.
 */
const CALCULATOR_EXACT = new Set([
  "/survival-simulator",
  "/embed/survival",
  "/default-alive",
  "/tools/runway-calculator",
  "/tools/dilution",
  "/tools/ltv-cac",
  "/tools/burn-multiple",
]);

const URL_PROPERTY = /url|referrer|referring|^href$/i;

export function normalizePath(path: string | null | undefined): string {
  if (!path) return "/";
  let value = path.trim();
  if (!value) return "/";
  try {
    if (value.includes("://")) value = new URL(value).pathname;
  } catch {
    // Keep the raw string and strip query/hash below.
  }
  const noHash = value.split("#")[0] || "/";
  const noQuery = noHash.split("?")[0] || "/";
  const trimmed = noQuery.length > 1 && noQuery.endsWith("/") ? noQuery.slice(0, -1) : noQuery;
  return trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
}

export function surfaceForPath(path: string | null | undefined): TrackingSurface {
  if (!path) return "core";
  const normalized = normalizePath(path);
  if (MARKETING_EXACT.has(normalized)) return "marketing";
  if (MARKETING_PREFIXES.some((prefix) => normalized.startsWith(prefix))) return "marketing";
  return "core";
}

export function isCalculatorQueryPath(path: string | null | undefined): boolean {
  const normalized = normalizePath(path);
  if (CALCULATOR_EXACT.has(normalized)) return true;
  return normalized.startsWith("/tools/") && normalized !== "/tools";
}

export function readCookieConsent(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(COOKIE_CONSENT_KEY);
  } catch {
    return null;
  }
}

export function hasRecordingConsent(value: string | null | undefined): boolean {
  return value === "accepted";
}

export function shouldRecordSession(
  surface: TrackingSurface,
  consent: string | null | undefined,
): boolean {
  return surface === "marketing" && hasRecordingConsent(consent);
}

export function recordingDecision(
  surface: TrackingSurface,
  consent: string | null | undefined,
): RecordingDecision {
  return shouldRecordSession(surface, consent) ? "start" : "stop";
}

function applyTo(runtime: RecordingRuntime): RecordingDecision {
  const decision = recordingDecision(runtime.surface, runtime.readConsent());
  const client = runtime.client;
  if (!client) return decision;
  try {
    if (decision === "start") {
      // `true` overrides project sampling and URL/event triggers. The product
      // gate is surface + consent; init leaves recording disabled.
      client.startSessionRecording?.(true);
    } else {
      client.stopSessionRecording?.();
    }
  } catch {
    // A recorder failure must not block $pageview or named events.
  }
  return decision;
}

export function createRecordingRuntime(
  readConsent: () => string | null,
  client: SessionRecordingControls | null = null,
): RecordingRuntime {
  return { client, surface: "core", readConsent };
}

const defaultRuntime: RecordingRuntime = createRecordingRuntime(readCookieConsent);

export function bindSessionRecordingClient(
  client: SessionRecordingControls | null,
): RecordingDecision {
  defaultRuntime.client = client;
  return applyTo(defaultRuntime);
}

/**
 * Surface switch #188 can call. "core" always stops. "marketing" starts only
 * when cookie consent is "accepted".
 */
export function setTrackingSurface(
  surface: TrackingSurface,
  runtime: RecordingRuntime = defaultRuntime,
): RecordingDecision {
  runtime.surface = surface;
  return applyTo(runtime);
}

export function setSurface(
  surface: TrackingSurface,
  runtime: RecordingRuntime = defaultRuntime,
): RecordingDecision {
  return setTrackingSurface(surface, runtime);
}

/** Route-based SPA hook. Core paths stop; marketing paths start only with consent. */
export function syncSessionRecording(
  path: string | null | undefined,
  runtime: RecordingRuntime = defaultRuntime,
): RecordingDecision {
  return setTrackingSurface(surfaceForPath(path), runtime);
}

export function refreshSessionRecording(
  runtime: RecordingRuntime = defaultRuntime,
): RecordingDecision {
  return applyTo(runtime);
}

let consentListenerInstalled = false;

export function installRecordingConsentListener(): void {
  if (consentListenerInstalled || typeof window === "undefined") return;
  consentListenerInstalled = true;
  const refresh = () => {
    refreshSessionRecording();
  };
  window.addEventListener(COOKIE_CONSENT_EVENT, refresh);
  window.addEventListener("storage", (event) => {
    if (event.key === COOKIE_CONSENT_KEY) refresh();
  });
}

/** Drop ?query and #hash when the URL is a calculator page. Other URLs stay. */
export function stripCalculatorQuery(value: string): string {
  if (!value) return value;
  const absolute = /^[a-z][a-z0-9+.-]*:/i.test(value);
  try {
    const url = new URL(value, "https://founderconsole.ai");
    if (!isCalculatorQueryPath(url.pathname)) return value;
    if (!url.search && !url.hash) return value;
    url.search = "";
    url.hash = "";
    if (!absolute) return `${url.pathname}${url.hash}`;
    return url.toString();
  } catch {
    return value;
  }
}

function sanitizeUrlFields(record: Record<string, unknown>): Record<string, unknown> {
  let changed = false;
  const next: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(record)) {
    let updated = value;
    if (typeof value === "string" && URL_PROPERTY.test(key)) {
      updated = stripCalculatorQuery(value);
    }
    if (updated !== value) changed = true;
    next[key] = updated;
  }
  return changed ? next : record;
}

function sanitizeSnapshotHref(data: unknown): unknown {
  if (!Array.isArray(data)) return data;
  let changed = false;
  const next = data.map((item) => {
    if (!item || typeof item !== "object") return item;
    const event = item as { data?: unknown };
    if (!event.data || typeof event.data !== "object" || Array.isArray(event.data)) return item;
    const payload = event.data as Record<string, unknown>;
    if (typeof payload.href !== "string") return item;
    const href = stripCalculatorQuery(payload.href);
    if (href === payload.href) return item;
    changed = true;
    return { ...event, data: { ...payload, href } };
  });
  return changed ? next : data;
}

export function sanitizePostHogProperties(
  properties: Record<string, unknown>,
  eventName?: string,
): Record<string, unknown> {
  const top = sanitizeUrlFields(properties);
  if (eventName !== "$snapshot") return top;
  const snapshotKey = Object.keys(top).find((key) => key === "$snapshot_data" || key === "snapshot_data");
  if (!snapshotKey) return top;
  const snapshot = sanitizeSnapshotHref(top[snapshotKey]);
  if (snapshot === top[snapshotKey]) return top;
  return { ...top, [snapshotKey]: snapshot };
}

type PostHogEventLike = {
  event: string;
  properties?: Record<string, unknown>;
};

/**
 * posthog-js before_send. sanitize_properties is deprecated in 1.438 and logs
 * an error on every event, so URL scrubbing lives here. Returning null would
 * drop the event; this always returns it.
 */
export function beforeSendPostHog<T extends PostHogEventLike | null>(event: T): T {
  if (!event?.properties) return event;
  try {
    const properties = sanitizePostHogProperties(event.properties, event.event);
    if (properties === event.properties) return event;
    return { ...event, properties } as T;
  } catch {
    return event;
  }
}
