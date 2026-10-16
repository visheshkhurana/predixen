// POST /hiring-plans/{id}/simulate returns runway as { p10, p50, p90 }; the flat
// keys are kept as fallbacks for older responses.
export function formatRunway(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(1) : "N/A";
}

// survival["12m"] is already a percentage (0–100); the legacy flat key was a fraction.
export function survival12mPct(results: any): number | null {
  const pct = results?.survival?.["12m"];
  if (typeof pct === "number" && Number.isFinite(pct)) return pct;
  const frac = results?.survival_probability;
  if (typeof frac === "number" && Number.isFinite(frac)) return frac * 100;
  return null;
}
