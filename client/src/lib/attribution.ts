import { registerSuperProperties } from "./posthog";

/**
 * First-touch campaign parameters from the landing URL.
 *
 * Nothing else in the client read these. They are stored once per tab
 * session and reused for PostHog and for the lead and signup requests.
 * A later URL in the same session does not replace them, including when
 * the landing URL had none. This does not read or store an IP address.
 */

export const ATTRIBUTION_KEYS = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_content",
  "utm_term",
  "fbclid",
  "gclid",
] as const;

export type AttributionKey = (typeof ATTRIBUTION_KEYS)[number];
export type Attribution = Partial<Record<AttributionKey, string>>;

export const ATTRIBUTION_STORAGE_KEY = "fc_first_touch_attribution";

/** Matches leads.utm_* VARCHAR(200). Longer click ids are truncated to fit. */
export const ATTRIBUTION_MAX_LENGTH = 200;

/** An address must not be stored or registered, even inside a campaign value. */
const EMAIL_RE = /[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}/i;

export type AttributionStorage = {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
};

export function cleanAttributionValue(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const text = value.trim().replace(/[\u0000-\u001f\u007f]/g, "");
  if (!text) return null;
  // Drop the whole value. A campaign parameter is not a place to keep an address.
  if (text.includes("@") || EMAIL_RE.test(text)) return null;
  return text.slice(0, ATTRIBUTION_MAX_LENGTH);
}

export function attributionFromSearch(search: string): Attribution {
  const query = search.startsWith("?") ? search.slice(1) : search;
  let params: URLSearchParams;
  try {
    params = new URLSearchParams(query);
  } catch {
    return {};
  }
  const out: Attribution = {};
  for (const key of ATTRIBUTION_KEYS) {
    const cleaned = cleanAttributionValue(params.get(key));
    if (cleaned) out[key] = cleaned;
  }
  return out;
}

function parseStored(raw: string): Attribution {
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const record = parsed as Record<string, unknown>;
    const out: Attribution = {};
    for (const key of ATTRIBUTION_KEYS) {
      const cleaned = cleanAttributionValue(record[key]);
      if (cleaned) out[key] = cleaned;
    }
    return out;
  } catch {
    return {};
  }
}

export function readStoredAttribution(
  storage: Pick<AttributionStorage, "getItem">,
): Attribution {
  try {
    const raw = storage.getItem(ATTRIBUTION_STORAGE_KEY);
    if (raw === null) return {};
    return parseStored(raw);
  } catch {
    return {};
  }
}

/**
 * Write the landing URL once. If the key is already present, return that
 * value and leave storage alone.
 */
export function captureFirstTouch(
  storage: AttributionStorage,
  search: string,
): Attribution {
  try {
    const existing = storage.getItem(ATTRIBUTION_STORAGE_KEY);
    if (existing !== null) return parseStored(existing);
  } catch {
    return {};
  }
  const captured = attributionFromSearch(search);
  try {
    storage.setItem(ATTRIBUTION_STORAGE_KEY, JSON.stringify(captured));
  } catch {
    // Private mode can throw. This page can still attach the values.
  }
  return captured;
}

export function readFirstTouchAttribution(): Attribution {
  if (typeof window === "undefined") return {};
  try {
    return readStoredAttribution(window.sessionStorage);
  } catch {
    return {};
  }
}

/** Capture on first page load and register the values as PostHog super properties. */
export function captureFirstTouchAttribution(): Attribution {
  if (typeof window === "undefined") return {};
  let captured: Attribution = {};
  try {
    captured = captureFirstTouch(window.sessionStorage, window.location.search);
  } catch {
    captured = {};
  }
  const unset = ATTRIBUTION_KEYS.filter((key) => !captured[key]);
  registerSuperProperties(captured, unset);
  return captured;
}
