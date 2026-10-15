/**
 * Council item 3 (2026-10-15): the "Try with Sample Startup" live preview on
 * /tools/runway-calculator.
 *
 * There is NO Monte Carlo engine in the client today — the real one is Python,
 * server-side (`server/services/`). So this file carries the small seeded engine
 * the preview needs. It is deliberately:
 *
 *   - **seeded**, so the same sample always draws the same bands. Two visitors
 *     see the same chart, a screenshot matches the page, and SSR/prerender can
 *     run it without a hydration mismatch. `Math.random()` would break all three.
 *   - **client-side only** — no fetch, no API call, no persistence, no session.
 *     The council's `growth` and `analytics` seats both attacked the original
 *     server-side guest session and both replaced it with exactly this.
 *   - **about the SAMPLE, never about the visitor.** Nothing here reads a
 *     company row or a logged-in user, so it cannot produce a claim about
 *     someone's real runway. The UI labels it as an illustration.
 *
 * The numbers it produces are ILLUSTRATIVE for a fixed example company. They
 * are not a validated forecast and must never be presented as the visitor's
 * own probability of survival — the council's `product` objection on item 6 is
 * exactly that a specific survival percentage is a claim without a source.
 *
 * Run its tests: npx tsx --test server/tests/sample-startup-preview.test.ts
 */

import { calculateCashFlowForecast } from '@/lib/finance';

/**
 * The four inputs the preview runs on. Deliberately plain `number`, not the
 * literal types `as const` would infer: `runSamplePreview` reassigns these as
 * it walks a path, and `typeof SAMPLE_STARTUP` narrows `revenue` to the literal
 * `40000`, which makes the reassignment a type error.
 */
export type SampleStartup = {
  name: string;
  cash: number;
  revenue: number;
  expenses: number;
  growthRate: number;
};

/** The hard-coded example the button loads. Same shape as the page's own four inputs. */
export const SAMPLE_STARTUP: SampleStartup = {
  name: 'Sample SaaS Co.',
  /** Cash on hand, USD. */
  cash: 600_000,
  /** Monthly revenue at month 0, USD. */
  revenue: 40_000,
  /** Monthly expenses at month 0, USD. */
  expenses: 75_000,
  /** Mean monthly revenue growth, percent. */
  growthRate: 3,
};

/** Months projected. Long enough to separate "safe" from "runs out", short enough to stay instant. */
export const HORIZON_MONTHS = 36;
/** Paths drawn. 2,000 x 36 months is ~72k steps — under 10 ms, so it can run on click. */
export const ITERATIONS = 2_000;
/** Fixed seed. Change it and every published screenshot of this preview goes stale. */
export const SEED = 20261015;

/**
 * Mean monthly expense growth, percent. Costs creep; they do not sit still.
 *
 * Kept equal to `calculateCashFlowForecast`'s `expenseGrowthPct`, which is what
 * the deterministic baseline below is measured with. If the two ever drift
 * apart the preview compares a straight line drawn one way against a cloud
 * drawn another, and the whole point of the card — "the band is why the median
 * is not the straight-line number" — quietly stops being true.
 */
const EXPENSE_DRIFT_PCT = 1;
/** Standard deviation of monthly revenue growth, percentage points. */
const REVENUE_GROWTH_SD = 3;
/** Standard deviation of monthly expense drift, percentage points. */
const EXPENSE_DRIFT_SD = 1.5;

/**
 * Deterministic PRNG (mulberry32). Small, fast, and good enough for a chart —
 * it is not used for anything security-relevant and must not be.
 */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Box–Muller standard normal from two uniforms.
 *
 * Cached in a closure so a pair of draws costs one `rand()` pair rather than
 * throwing the second value away on every call.
 */
function normalSource(rand: () => number): () => number {
  let spare: number | null = null;
  return function () {
    if (spare !== null) {
      const v = spare;
      spare = null;
      return v;
    }
    let u = 0;
    let v = 0;
    while (u === 0) u = rand();
    while (v === 0) v = rand();
    const mag = Math.sqrt(-2 * Math.log(u));
    spare = mag * Math.sin(2 * Math.PI * v);
    return mag * Math.cos(2 * Math.PI * v);
  };
}

export type SamplePreviewBands = {
  /** Month index, 0..HORIZON_MONTHS. */
  month: number[];
  /** Cash remaining at each month, USD, for the pessimistic decile. */
  p10: number[];
  /** ...the median. */
  p50: number[];
  /** ...the optimistic decile. */
  p90: number[];
};

export type SamplePreview = {
  sample: SampleStartup;
  /**
   * What the app's own straight-line forecast gives for the sample, months.
   * Null when it never runs out inside the horizon.
   */
  deterministicRunoutMonth: number | null;
  /** Month the median path first hits zero, or null if the median never does inside the horizon. */
  medianRunoutMonth: number | null;
  /** Share of paths still solvent at the horizon, 0..1. */
  survivalAtHorizon: number;
  /** Share of paths that have hit zero by month 18, 0..1. */
  runoutByMonth18: number;
  bands: SamplePreviewBands;
  iterations: number;
  horizonMonths: number;
};

/**
 * Percentile of an already-sorted array, by nearest-rank.
 *
 * Nearest-rank, not interpolation, on purpose: every value returned is an
 * outcome some path actually produced, so the chart never shows a cash balance
 * no simulation reached.
 */
export function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1));
  return sorted[idx];
}

/**
 * Straight-line runway in months: the month the canonical client forecast
 * first goes to zero, or null if it never does inside the horizon.
 *
 * This defers to `calculateCashFlowForecast` in `@/lib/finance` — the file that
 * calls itself the single source of truth for runway — rather than dividing
 * cash by net burn here. Dividing was the first version of this function and it
 * was wrong on screen: cash / (expenses - revenue) ignores the revenue growth
 * the visitor typed, so with the sample it said "18.8 mo" while the calculator
 * directly above it said "36+". Two different answers for the same four numbers
 * on one page is worse than no preview at all, so the baseline now runs the
 * app's own forecast with the same expense drift the simulation uses.
 */
export function deterministicRunwayMonths(
  cash: number,
  revenue: number,
  expenses: number,
  growthRatePct: number,
  months: number = HORIZON_MONTHS,
): number | null {
  if (cash <= 0) return 0;
  const forecast = calculateCashFlowForecast(
    revenue,
    expenses,
    cash,
    growthRatePct,
    months,
    EXPENSE_DRIFT_PCT,
  );
  const broke = forecast.find((row) => row.cash_balance <= 0);
  return broke ? broke.month : null;
}

/**
 * Run the sample through the engine.
 *
 * Each month, revenue compounds by a drawn growth rate and expenses drift by a
 * drawn amount. A path ends the first month its cash goes to zero or below.
 * Everything is a pure function of (SAMPLE_STARTUP, SEED, ITERATIONS).
 */
export function runSamplePreview(
  sample: SampleStartup = SAMPLE_STARTUP,
  iterations: number = ITERATIONS,
): SamplePreview {
  const rand = mulberry32(SEED);
  const normal = normalSource(rand);

  // Cash at each month, one array per path. Kept so the bands can be taken
  // after the fact; 2,000 x 37 numbers is trivial next to a re-render.
  const paths: number[][] = [];
  const runoutMonths: number[] = [];

  for (let i = 0; i < iterations; i++) {
    const path: number[] = new Array(HORIZON_MONTHS + 1);
    let cash = sample.cash;
    let revenue = sample.revenue;
    let expenses = sample.expenses;
    let runout = -1;

    path[0] = cash;
    for (let m = 1; m <= HORIZON_MONTHS; m++) {
      const growth = (sample.growthRate + normal() * REVENUE_GROWTH_SD) / 100;
      const drift = (EXPENSE_DRIFT_PCT + normal() * EXPENSE_DRIFT_SD) / 100;
      // Floor the compounding at -95%/mo so one absurd draw cannot make the
      // revenue line negative and invert the whole path.
      revenue = Math.max(0, revenue * (1 + Math.max(growth, -0.95)));
      expenses = Math.max(0, expenses * (1 + Math.max(drift, -0.95)));
      cash = cash + revenue - expenses;
      path[m] = cash;
      if (cash <= 0 && runout === -1) runout = m;
    }

    paths.push(path);
    runoutMonths.push(runout === -1 ? HORIZON_MONTHS + 1 : runout);
  }

  const bands: SamplePreviewBands = { month: [], p10: [], p50: [], p90: [] };
  for (let m = 0; m <= HORIZON_MONTHS; m++) {
    const atMonth = paths.map((p) => p[m]).sort((a, b) => a - b);
    bands.month.push(m);
    bands.p10.push(percentile(atMonth, 10));
    bands.p50.push(percentile(atMonth, 50));
    bands.p90.push(percentile(atMonth, 90));
  }

  const sortedRunout = [...runoutMonths].sort((a, b) => a - b);
  const medianDraw = percentile(sortedRunout, 50);
  const survived = runoutMonths.filter((m) => m > HORIZON_MONTHS).length;

  return {
    sample,
    deterministicRunoutMonth: deterministicRunwayMonths(
      sample.cash,
      sample.revenue,
      sample.expenses,
      sample.growthRate,
    ),
    medianRunoutMonth: medianDraw > HORIZON_MONTHS ? null : medianDraw,
    survivalAtHorizon: survived / iterations,
    runoutByMonth18: runoutMonths.filter((m) => m <= 18).length / iterations,
    bands,
    iterations,
    horizonMonths: HORIZON_MONTHS,
  };
}
