/**
 * One runway formula for every free tool: /tools/runway-calculator,
 * /runway/:slug, /embed/survival and /default-alive.
 *
 * Runway in months = cash / monthly net burn, where net burn = expenses - revenue.
 * Shown to one decimal (rounded), the same as the in-app runway figure.
 *
 * The runway calculator also takes a monthly revenue growth rate. projectRunway
 * walks the months and interpolates inside the month the cash runs out, so at 0%
 * growth it returns exactly cash / net burn — the same number the other tools print.
 *
 * Edge cases, fixed here so the pages cannot disagree again:
 *   - net burn <= 0 (revenue covers costs): "Profitable", never a number of months
 *     and never a negative burn like "$-20000";
 *   - cash <= 0 while burning: 0 months (the calculator used to show "36+");
 *   - still cash left at the projection horizon: "beyond N months".
 */

export type RunwayResult =
  | { kind: "profitable"; netBurn: number }
  | { kind: "months"; months: number; netBurn: number }
  | { kind: "beyond"; horizonMonths: number; netBurn: number };

export const RUNWAY_HORIZON_MONTHS = 36;

/** cash / (expenses - revenue). The constant-month model. */
export function simpleRunway(cash: number, expenses: number, revenue: number): RunwayResult {
  const netBurn = expenses - revenue;
  if (netBurn <= 0) return { kind: "profitable", netBurn };
  if (cash <= 0) return { kind: "months", months: 0, netBurn };
  return { kind: "months", months: cash / netBurn, netBurn };
}

/**
 * Month-by-month with revenue compounding at `growthPct` per month. At 0% growth this
 * equals simpleRunway (within the horizon).
 */
export function projectRunway(
  cash: number,
  expenses: number,
  revenue: number,
  growthPct: number,
  horizonMonths: number = RUNWAY_HORIZON_MONTHS,
): RunwayResult {
  const netBurn = expenses - revenue;
  if (cash <= 0 && netBurn > 0) return { kind: "months", months: 0, netBurn };

  let remaining = Math.max(0, cash);
  let rev = revenue;
  for (let m = 0; m < horizonMonths; m++) {
    const burn = expenses - rev;
    if (burn > 0 && remaining - burn <= 0) {
      return { kind: "months", months: m + remaining / burn, netBurn };
    }
    remaining -= burn;
    rev *= 1 + growthPct / 100;
  }
  // Never ran out inside the horizon. Profitable now and not shrinking: say so.
  if (netBurn <= 0 && growthPct >= 0) return { kind: "profitable", netBurn };
  return { kind: "beyond", horizonMonths, netBurn };
}

/** One decimal, rounded: 13.888 -> 13.9. */
export function roundMonths(months: number): number {
  return Math.round(months * 10) / 10;
}

/** "Profitable", "13.9 months", "0 months", "36+ months". */
export function formatRunway(r: RunwayResult, unit: "months" | "mo" = "months"): string {
  if (r.kind === "profitable") return "Profitable";
  if (r.kind === "beyond") return `${r.horizonMonths}+ ${unit}`;
  const m = roundMonths(r.months);
  const label = unit === "mo" ? "mo" : m === 1 ? "month" : "months";
  return `${m} ${label}`;
}

/** Months for comparisons and thresholds; Infinity when the cash never runs out. */
export function runwayMonthsOrInfinity(r: RunwayResult): number {
  return r.kind === "months" ? r.months : Number.POSITIVE_INFINITY;
}

export type RunwayVerdict = "Profitable" | "Healthy" | "Watch" | "Raise soon" | "Critical";

/** The thresholds /runway/:slug and /embed/survival already used (18 / 12 / 6 months). */
export function runwayVerdict(r: RunwayResult): RunwayVerdict {
  if (r.kind === "profitable") return "Profitable";
  const m = runwayMonthsOrInfinity(r);
  if (m >= 18) return "Healthy";
  if (m >= 12) return "Watch";
  if (m >= 6) return "Raise soon";
  return "Critical";
}

/**
 * Parse a text field for the model. Fields hold TEXT so deleting the last digit leaves
 * the box empty instead of snapping to "0" (the Number(e.target.value) bug).
 */
export function toNumber(text: string): number {
  const n = parseFloat(text);
  return Number.isFinite(n) ? n : 0;
}
