/**
 * Properties safe to send from a public calculator.
 * The address, notes, and anything that looks like an email stay out.
 * Numeric results and the calculator name stay in.
 */
const BLOCKED_KEYS = new Set([
  "email",
  "e-mail",
  "mail",
  "phone",
  "notes",
  "distinct_id",
  "first_name",
  "last_name",
  "full_name",
  "name",
  "address",
  "ip",
]);

export function publicEventProperties(
  input: Record<string, unknown> | null | undefined,
): Record<string, string | number | boolean> {
  const out: Record<string, string | number | boolean> = {};
  if (!input) return out;
  for (const [key, value] of Object.entries(input)) {
    if (BLOCKED_KEYS.has(key.toLowerCase())) continue;
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (!trimmed || trimmed.includes("@")) continue;
      out[key] = trimmed;
    } else if (typeof value === "number" && Number.isFinite(value)) {
      out[key] = value;
    } else if (typeof value === "boolean") {
      out[key] = value;
    }
  }
  return out;
}
