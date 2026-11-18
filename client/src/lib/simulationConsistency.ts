/**
 * One place that decides whether a simulation result makes sense, used by the
 * verdict, the decision score and the Math Check so they can't disagree.
 *
 * Runway of 900+ months is the engine's "never ran out" sentinel (999). It is
 * never a number to show or subtract: "gain 971 months" was 999 − 28.
 */

export const SUSTAINABLE_RUNWAY = 900;

export function isSustainable(months: number | null | undefined): boolean {
  if (months === null || months === undefined || !Number.isFinite(months)) return true;
  return months >= SUSTAINABLE_RUNWAY;
}

export type RunwayChange =
  | { kind: 'months'; months: number }
  | { kind: 'becomes_sustainable' }
  | { kind: 'loses_sustainable'; months: number }
  | { kind: 'both_sustainable' };

export function runwayChange(baseline: number | null | undefined, scenario: number | null | undefined): RunwayChange {
  const b = isSustainable(baseline);
  const s = isSustainable(scenario);
  if (b && s) return { kind: 'both_sustainable' };
  if (!b && s) return { kind: 'becomes_sustainable' };
  if (b && !s) return { kind: 'loses_sustainable', months: scenario as number };
  return { kind: 'months', months: (scenario as number) - (baseline as number) };
}

/** Months of change as a number for scoring, never using the sentinel. */
export function runwayDeltaForScoring(change: RunwayChange): number {
  switch (change.kind) {
    case 'months': return change.months;
    case 'becomes_sustainable': return 12;
    case 'loses_sustainable': return -12;
    default: return 0;
  }
}

export function describeRunwayChange(change: RunwayChange): string | null {
  switch (change.kind) {
    case 'months':
      if (Math.abs(change.months) < 0.05) return null;
      return `${change.months > 0 ? '+' : ''}${change.months.toFixed(1)}mo runway`;
    case 'becomes_sustainable': return 'runway becomes sustainable';
    case 'loses_sustainable': return `no longer cash-positive (${change.months.toFixed(1)}mo runway)`;
    default: return null;
  }
}

export interface ScenarioInputs {
  pricing_change_pct?: number;
  growth_uplift_pct?: number;
  burn_reduction_pct?: number;
  gross_margin_delta_pct?: number;
  churn_change_pct?: number;
  cac_change_pct?: number;
  fundraise_amount?: number;
  hiring_plan?: unknown[];
}

export interface ConsistencyResult {
  consistent: boolean;
  /** Plain-language reason, shown instead of a verdict when inconsistent. */
  reason: string | null;
}

/**
 * A scenario whose every lever makes things worse (more burn, less growth,
 * more churn, higher CAC, lower prices or margin) cannot improve runway or
 * survival. When the result says it does, the numbers are wrong somewhere and
 * no GO should be shown.
 */
export function scenarioConsistency(
  inputs: ScenarioInputs | null | undefined,
  baseline: { runwayP50?: number | null; survival18m?: number | null } | null | undefined,
  scenario: { runwayP50?: number | null; survival18m?: number | null },
  /**
   * The baseline is the dashboard's simple cash ÷ burn, not a simulated
   * no-change run. Growth alone can lift a simulated runway above it, so only
   * the impossible case is flagged: an adverse scenario becoming sustainable.
   */
  options: { approximate?: boolean } = {},
): ConsistencyResult {
  if (!inputs || !baseline) return { consistent: true, reason: null };
  const n = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : 0);
  const hires = Array.isArray(inputs.hiring_plan) ? inputs.hiring_plan.length : 0;
  const adverse =
    n(inputs.burn_reduction_pct) < 0 || hires > 0 || n(inputs.growth_uplift_pct) < 0 ||
    n(inputs.churn_change_pct) > 0 || n(inputs.cac_change_pct) > 0 ||
    n(inputs.pricing_change_pct) < 0 || n(inputs.gross_margin_delta_pct) < 0;
  const favourable =
    n(inputs.burn_reduction_pct) > 0 || n(inputs.growth_uplift_pct) > 0 ||
    n(inputs.churn_change_pct) < 0 || n(inputs.cac_change_pct) < 0 ||
    n(inputs.pricing_change_pct) > 0 || n(inputs.gross_margin_delta_pct) > 0 ||
    n(inputs.fundraise_amount) > 0;
  if (!adverse || favourable) return { consistent: true, reason: null };

  const change = runwayChange(baseline.runwayP50, scenario.runwayP50);
  const runwayImproved = options.approximate
    ? change.kind === 'becomes_sustainable'
    : change.kind === 'becomes_sustainable' || (change.kind === 'months' && change.months > 0.5);
  const survivalImproved = !options.approximate &&
    n(scenario.survival18m) - n(baseline.survival18m) > 2;
  if (!runwayImproved && !survivalImproved) return { consistent: true, reason: null };

  return {
    consistent: false,
    reason:
      'This scenario only adds cost or risk, yet the simulation shows a better outcome than your baseline. ' +
      'That cannot be right, so there is no verdict. Check the scenario inputs below and run it again.',
  };
}

/** The engine simulates this many months; anything longer is extrapolated. */
export const SIM_HORIZON_MONTHS = 24;

/**
 * Runway for display: "Sustainable" for the never-ran-out sentinel, "24+ mo"
 * past the simulated period (a 24-month simulation cannot know "222 months"),
 * otherwise one decimal.
 */
export function formatRunwayShort(months: number | null | undefined): string {
  if (months === null || months === undefined) return '?';
  if (isSustainable(months)) return 'Sustainable';
  if (months > SIM_HORIZON_MONTHS) return `${SIM_HORIZON_MONTHS}+ mo`;
  return `${months.toFixed(1)} mo`;
}

/** For sentences: "a sustainable runway", "more than 24 months of runway", "9 months of runway". */
export function runwaySentence(months: number): string {
  if (isSustainable(months)) return 'a sustainable runway';
  if (months > SIM_HORIZON_MONTHS) return `more than ${SIM_HORIZON_MONTHS} months of runway`;
  return `${months.toFixed(0)} months of runway`;
}
