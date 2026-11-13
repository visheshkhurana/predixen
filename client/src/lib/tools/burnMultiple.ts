/**
 * HAG-163, tool 1 of 3: burn multiple.
 *
 * Formula source, transcribed rather than invented — the Quant lane's file:
 *   hive/reports/quant-forge-tools-maths.md, "Tool 1 — Burn multiple".
 * Benchmarks the page reads the answer against:
 *   hive/reports/quant-benchmarks.md, Table 1.
 *
 * The card's rule is "do not invent a formula". So the three inputs to this
 * file that are NOT forced by arithmetic are labelled here, at the point they
 * are applied, exactly as the maths file labels them:
 *
 *   TEXTBOOK  net_new_arr = new + expansion - churned - contraction   (net, not gross)
 *   CHOICE    net_burn    = cash_out - cash_in                       (net burn, not gross)
 *   CHOICE    the window defaults to the trailing 3 complete months   (the page's default)
 *   TEXTBOOK  burn_multiple = net_burn / net_new_arr
 *
 * The page prints each CHOICE in one line next to the field it affects, which
 * is what makes the choice reviewable rather than hidden.
 *
 * Every degenerate input resolves to a plain-English reason and a `null`
 * multiple. This file never returns Infinity, never returns NaN, and never
 * returns a negative number as if it were a good score.
 */

/** The maths file's exact field names and units. */
export interface BurnMultipleInputs {
  /** currency, in the period — ARR won from new customers */
  new_arr: number;
  /** currency, in the period — ARR added by existing customers */
  expansion_arr: number;
  /** currency, in the period — ARR lost to customers who left */
  churned_arr: number;
  /** currency, in the period — ARR lost to downgrades */
  contraction_arr: number;
  /** currency, in the period — OPERATING cash spent (payroll, tools, ads, rent) */
  cash_out: number;
  /** currency, in the period — cash collected from customers */
  cash_in: number;
  /** integer months — the window, used for the per-month readout only */
  period_months: number;
  /**
   * Not part of the formula. These two exist for CHOICE 3, the reconciliation
   * check: `starting_arr + net_new_arr` must equal `ending_arr`, and if it does
   * not the founder has mixed two definitions of ARR. Omit either and the check
   * is reported as not run rather than passing silently.
   */
  starting_arr?: number | null;
  ending_arr?: number | null;
}

export type BurnMultipleOutcome = "ok" | "not_applicable" | "invalid";

/** The two ways the reconciliation check (CHOICE 3) can come out. */
export type Reconciliation =
  | { state: "not_run" }
  | { state: "pass"; expectedEndingArr: number }
  | { state: "fail"; expectedEndingArr: number; difference: number };

export interface BurnMultipleResult {
  outcome: BurnMultipleOutcome;
  /** net_new_arr, computed even when the ratio is not */
  netNewArr: number;
  /** net_burn, computed even when the ratio is not */
  netBurn: number;
  /** `null` whenever there is no honest ratio to print */
  multiple: number | null;
  /** one plain-English line explaining a `null` multiple; `null` when there is a ratio */
  reason: string | null;
  /**
   * Dividing burn and ARR by the same window length cannot change a ratio, so
   * this is always the same number as `multiple`. The page prints it anyway,
   * because the maths file asks the tool to say so rather than let a founder
   * believe the window moves the score.
   */
  monthlyAverage: { netBurn: number; netNewArr: number; multiple: number | null };
  reconciliation: Reconciliation;
}

/** Half a currency unit: absorbs a founder's rounded ARR entry, not a definitional drift. */
const RECONCILE_TOLERANCE = 0.5;

const INVALID = (reason: string): BurnMultipleResult => ({
  outcome: "invalid",
  netNewArr: 0,
  netBurn: 0,
  multiple: null,
  reason,
  monthlyAverage: { netBurn: 0, netNewArr: 0, multiple: null },
  reconciliation: { state: "not_run" },
});

/**
 * The maths file's edge-case table, in its order. The order matters: a company
 * whose ARR is flat is the division-by-zero case and must be reported as that,
 * not as the shrinking case, and neither may fall through to a ratio.
 */
export function computeBurnMultiple(input: BurnMultipleInputs): BurnMultipleResult {
  const raw = [
    input.new_arr,
    input.expansion_arr,
    input.churned_arr,
    input.contraction_arr,
    input.cash_out,
    input.cash_in,
    input.period_months,
  ];

  if (raw.some((v) => !Number.isFinite(v))) {
    return INVALID("Every field needs a number in it.");
  }
  if (raw.some((v) => v < 0)) {
    return INVALID("Every input must be zero or greater.");
  }
  if (!Number.isInteger(input.period_months) || input.period_months < 1) {
    return INVALID("The window must be at least one whole month.");
  }

  const netNewArr =
    input.new_arr + input.expansion_arr - input.churned_arr - input.contraction_arr;
  const netBurn = input.cash_out - input.cash_in;

  let multiple: number | null = null;
  let reason: string | null = null;
  let outcome: BurnMultipleOutcome = "ok";

  if (netNewArr === 0) {
    // Division by zero. A company with flat ARR and any burn is failing.
    outcome = "not_applicable";
    reason = "n/a — no new ARR. With flat ARR, any burn is a loss, not an efficiency.";
  } else if (netNewArr < 0) {
    // A negative ratio is not "better than 1".
    outcome = "not_applicable";
    reason = "n/a — ARR is shrinking. Burn multiple measures the cost of growth, and there is no growth in this window.";
  } else if (netBurn < 0) {
    // Cash-flow positive: do not render a negative number as an achievement.
    outcome = "not_applicable";
    reason = "n/a — cash-flow positive. Burn multiple does not apply to a window that added cash.";
  } else {
    multiple = netBurn / netNewArr;
  }

  const months = input.period_months;

  return {
    outcome,
    netNewArr,
    netBurn,
    multiple,
    reason,
    monthlyAverage: {
      netBurn: netBurn / months,
      netNewArr: netNewArr / months,
      multiple,
    },
    reconciliation: reconcile(input, netNewArr),
  };
}

function reconcile(input: BurnMultipleInputs, netNewArr: number): Reconciliation {
  const start = input.starting_arr;
  const end = input.ending_arr;
  if (start == null || end == null) return { state: "not_run" };
  if (!Number.isFinite(start) || !Number.isFinite(end)) return { state: "not_run" };

  const expectedEndingArr = start + netNewArr;
  const difference = end - expectedEndingArr;
  if (Math.abs(difference) <= RECONCILE_TOLERANCE) {
    return { state: "pass", expectedEndingArr };
  }
  return { state: "fail", expectedEndingArr, difference };
}

/**
 * Table 1 of quant-benchmarks.md, as bands. The citations live here so the page
 * cannot quote a threshold without the source that published it.
 *
 * Both sources are tier T1 in the benchmark file, and both are explicitly
 * caveated there as having no published sample size — so these read as
 * directional, and the page says so next to them.
 */
export interface BurnMultipleBand {
  id: "efficient" | "median-2024" | "above-median";
  label: string;
  /** what this band is, in one line, sourced */
  detail: string;
}

export const BURN_MULTIPLE_BANDS: readonly BurnMultipleBand[] = [
  {
    id: "efficient",
    label: "Efficient",
    detail:
      "Under 1.0x — Benchmarkit's 2025 target for a company at $25M–$50M ARR (< 1.0).",
  },
  {
    id: "median-2024",
    label: "At or better than the 2024 median",
    detail:
      "1.0x–2.3x — Scale Venture Partners' 2024 median was 2.3x, down from 3.3x in 2023.",
  },
  {
    id: "above-median",
    label: "Above the 2024 median",
    detail:
      "Over 2.3x — above Scale Venture Partners' 2024 median of 2.3x.",
  },
];

export function bandFor(multiple: number): BurnMultipleBand {
  if (multiple < 1) return BURN_MULTIPLE_BANDS[0];
  if (multiple <= 2.3) return BURN_MULTIPLE_BANDS[1];
  return BURN_MULTIPLE_BANDS[2];
}

/** The maths file's worked example, used by the page as its pre-filled default and by the test. */
export const WORKED_EXAMPLE: BurnMultipleInputs = {
  new_arr: 180_000,
  expansion_arr: 30_000,
  churned_arr: 45_000,
  contraction_arr: 15_000,
  cash_out: 600_000,
  cash_in: 150_000,
  period_months: 3,
  starting_arr: 1_200_000,
  ending_arr: 1_350_000,
};
