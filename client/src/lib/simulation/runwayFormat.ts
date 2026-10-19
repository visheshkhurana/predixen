/**
 * Runway values from the Monte Carlo engines use 999 as a "never ran out of
 * cash within the horizon" sentinel. It must never render as "999mo".
 */
export const SUSTAINABLE_RUNWAY_SENTINEL = 900;

export function isSustainableRunway(value: unknown): boolean {
  return typeof value === "number" && Number.isFinite(value) && value >= SUSTAINABLE_RUNWAY_SENTINEL;
}

/** "12.3" for a finite runway, "Sustainable" for the sentinel, "—" when absent. */
export function formatRunwayMonths(value: unknown, digits = 1): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  if (isSustainableRunway(value)) return "Sustainable";
  return value.toFixed(digits);
}

export interface TwinSimulationSummary {
  p10_runway: number | null;
  p50_runway: number | null;
  p90_runway: number | null;
  survival_probability: number | null;
  iterations: number | null;
  horizon_months: number | null;
}

/**
 * POST /twin/simulate returns { summary: {...flat...}, results: <nested enhanced
 * MC output> }. Older responses had no summary; read the nested shape then.
 */
export function twinSummary(data: any): TwinSimulationSummary | null {
  if (!data) return null;
  const s = data.summary;
  if (s && typeof s === "object") {
    return {
      p10_runway: num(s.p10_runway),
      p50_runway: num(s.p50_runway),
      p90_runway: num(s.p90_runway),
      survival_probability: num(s.survival_probability),
      iterations: num(s.iterations),
      horizon_months: num(s.horizon_months),
    };
  }
  const r = data.results;
  if (!r || typeof r !== "object") return null;
  const s24 = num(r.survivalProbability?.["24m"]);
  return {
    p10_runway: num(r.runway?.p10),
    p50_runway: num(r.runway?.p50),
    p90_runway: num(r.runway?.p90),
    survival_probability: s24 === null ? null : s24 / 100,
    iterations: num(r.config?.iterations),
    horizon_months: num(r.config?.horizonMonths),
  };
}

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}
