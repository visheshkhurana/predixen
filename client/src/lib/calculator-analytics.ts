/**
 * Allow-list for every trackFunnel payload (PostHog, gtag, and X).
 *
 * Open strings: calculator, location, host. Known enums: method, source.
 * is_sample is the only boolean. Calculator results (runway_months, grade,
 * survival_12m) and every other key are dropped, including numbers.
 * A string that contains @ is dropped even on an allowed key.
 */
const OPEN_STRING_KEYS = new Set(["calculator", "location", "host"]);

const ENUM_VALUES: Record<string, ReadonlySet<string>> = {
  method: new Set(["email", "google"]),
  source: new Set(["truth_scan", "simulation"]),
};

const BOOLEAN_KEYS = new Set(["is_sample"]);

export function publicEventProperties(
  input: Record<string, unknown> | null | undefined,
): Record<string, string | boolean> {
  const out: Record<string, string | boolean> = {};
  if (!input) return out;
  for (const [key, value] of Object.entries(input)) {
    if (OPEN_STRING_KEYS.has(key)) {
      if (typeof value !== "string") continue;
      const trimmed = value.trim();
      if (!trimmed || trimmed.includes("@")) continue;
      out[key] = trimmed;
      continue;
    }
    const allowed = ENUM_VALUES[key];
    if (allowed) {
      if (typeof value !== "string") continue;
      const trimmed = value.trim();
      if (!allowed.has(trimmed)) continue;
      out[key] = trimmed;
      continue;
    }
    if (BOOLEAN_KEYS.has(key) && typeof value === "boolean") {
      out[key] = value;
    }
  }
  return out;
}
