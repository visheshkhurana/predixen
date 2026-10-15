/**
 * Council item 3 (2026-10-15): the "Try with Sample Startup" client-side preview.
 *
 * Run: npx tsx --test server/tests/sample-startup-preview.test.ts
 *
 * Two kinds of assertion live here, and both are load-bearing:
 *
 *   1. **The engine's numbers.** The simulation is seeded, so its output is a
 *      fixed function of (SAMPLE_STARTUP, SEED, ITERATIONS) and every literal
 *      below was measured from a real run, not estimated. If a future edit
 *      changes the sample, the seed or the model, these fail — which is the
 *      point: the preview's copy quotes these numbers, and a screenshot of it
 *      is only honest while the numbers still hold.
 *   2. **The boundaries the job was given.** Client-side only, no new API call,
 *      no backend, feature-flagged, and never a probability claim about the
 *      visitor's own company. Those are structural facts about the files, so
 *      they are asserted against the files.
 *
 * NOTE ON CI: this file is not named by `.github/workflows/pr-checks.yml`, so
 * it does not run in CI — the same gap the dilution/ltv-cac/vs-runway tests
 * have. `pr-checks.yml` is on the hold list and this PR does not touch it.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  SAMPLE_STARTUP,
  HORIZON_MONTHS,
  ITERATIONS,
  SEED,
  percentile,
  mulberry32,
  deterministicRunwayMonths,
  runSamplePreview,
} from "../../client/src/lib/simulation/sampleStartupPreview";
import { calculateCashFlowForecast } from "../../client/src/lib/finance";

const PAGE = "client/src/pages/runway-calculator.tsx";
const COMPONENT = "client/src/components/tools/SampleStartupPreview.tsx";
const ENGINE = "client/src/lib/simulation/sampleStartupPreview.ts";
const FLAGS = "client/src/config/features.ts";

const read = (p: string) => readFileSync(p, "utf8");

/**
 * The source with its comments removed.
 *
 * Needed because these files *talk about* the things they must not do — the
 * engine's header says "`Math.random()` would break all three", and the page's
 * comment about the single capture path names `/api/leads`. Matching raw text
 * would fail on the prose that documents the rule rather than on a breach of it.
 * Comments are stripped so the assertions test the code.
 */
const code = (p: string) =>
  read(p)
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");

// ---------------------------------------------------------------------------
// 1. The engine's numbers, measured
// ---------------------------------------------------------------------------

test("the sample is the one the copy describes", () => {
  assert.equal(SAMPLE_STARTUP.cash, 600_000);
  assert.equal(SAMPLE_STARTUP.revenue, 40_000);
  assert.equal(SAMPLE_STARTUP.expenses, 75_000);
  assert.equal(SAMPLE_STARTUP.growthRate, 3);
  assert.equal(HORIZON_MONTHS, 36);
  assert.equal(ITERATIONS, 2_000);
});

test("the baseline is the app's own forecast, not cash over net burn", () => {
  // The regression this guards: the first version divided cash by net burn,
  // which ignores the revenue growth the visitor typed and printed "18.8 mo"
  // next to a calculator showing "36+". It must now agree with
  // calculateCashFlowForecast on the same four numbers.
  const forecast = calculateCashFlowForecast(
    SAMPLE_STARTUP.revenue,
    SAMPLE_STARTUP.expenses,
    SAMPLE_STARTUP.cash,
    SAMPLE_STARTUP.growthRate,
    36,
    1,
  );
  const firstZero = forecast.find((r) => r.cash_balance <= 0);
  assert.ok(firstZero, "the sample is supposed to run out inside the horizon");
  assert.equal(firstZero!.month, 23);

  assert.equal(
    deterministicRunwayMonths(
      SAMPLE_STARTUP.cash,
      SAMPLE_STARTUP.revenue,
      SAMPLE_STARTUP.expenses,
      SAMPLE_STARTUP.growthRate,
    ),
    23,
  );

  // The arithmetic the first version used, kept here so the difference is
  // visible rather than described: 600000 / (75000 - 40000) = 12.
  assert.notEqual(
    deterministicRunwayMonths(
      SAMPLE_STARTUP.cash,
      SAMPLE_STARTUP.revenue,
      SAMPLE_STARTUP.expenses,
      SAMPLE_STARTUP.growthRate,
    ),
    Math.round((SAMPLE_STARTUP.cash / (SAMPLE_STARTUP.expenses - SAMPLE_STARTUP.revenue)) * 10) / 10,
  );
});

test("a profitable sample has no runout month", () => {
  assert.equal(deterministicRunwayMonths(600_000, 90_000, 75_000, 3), null);
  assert.equal(deterministicRunwayMonths(0, 40_000, 75_000, 3), 0);
});

test("runSamplePreview returns the measured figures", () => {
  const r = runSamplePreview();
  assert.equal(r.iterations, ITERATIONS);
  assert.equal(r.horizonMonths, HORIZON_MONTHS);

  assert.equal(r.deterministicRunoutMonth, 23);
  assert.equal(r.medianRunoutMonth, 22);
  assert.ok(Math.abs(r.survivalAtHorizon - 0.3335) < 1e-9);
  assert.ok(Math.abs(r.runoutByMonth18 - 0.2085) < 1e-9);

  // Everyone starts with the same cash: the band has zero width at month 0.
  assert.equal(r.bands.p10[0], 600_000);
  assert.equal(r.bands.p50[0], 600_000);
  assert.equal(r.bands.p90[0], 600_000);
  assert.equal(r.bands.month.length, HORIZON_MONTHS + 1);

  // The band has to actually straddle zero at the horizon for the card's
  // claim — "the width is the point" — to be true rather than decorative.
  assert.ok(r.bands.p10[HORIZON_MONTHS] < 0, "P10 should be out of cash at month 36");
  assert.ok(r.bands.p90[HORIZON_MONTHS] > 0, "P90 should still be solvent at month 36");
});

test("the bands are ordered at every month", () => {
  const { p10, p50, p90 } = runSamplePreview().bands;
  for (let m = 0; m <= HORIZON_MONTHS; m++) {
    assert.ok(p10[m] <= p50[m], `p10 > p50 at month ${m}`);
    assert.ok(p50[m] <= p90[m], `p50 > p90 at month ${m}`);
  }
});

test("the band widens with time", () => {
  const { p10, p90 } = runSamplePreview().bands;
  const width = (m: number) => p90[m] - p10[m];
  assert.equal(width(0), 0);
  assert.ok(width(36) > width(18), "P90-P10 should widen from month 18 to 36");
  assert.ok(width(18) > width(6), "P90-P10 should widen from month 6 to 18");
});

test("the same sample always draws the same futures", () => {
  // Seeded on purpose. Math.random() here would mean two visitors comparing
  // screenshots see different charts, and SSR/prerender would hydrate against
  // a different draw than the server rendered.
  const a = runSamplePreview();
  const b = runSamplePreview();
  assert.deepEqual(a, b);
  assert.deepEqual(a.bands, b.bands);
  assert.equal(SEED, 20261015, "changing the seed invalidates every published screenshot");
});

test("two seeds give different futures", () => {
  const randA = mulberry32(1);
  const randB = mulberry32(2);
  assert.notEqual(randA(), randB());
  assert.equal(mulberry32(7)(), mulberry32(7)());
});

test("percentile is nearest-rank over the values that were actually drawn", () => {
  const sorted = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
  assert.equal(percentile(sorted, 0), 10);
  assert.equal(percentile(sorted, 10), 10);
  assert.equal(percentile(sorted, 50), 50);
  assert.equal(percentile(sorted, 100), 100);
  assert.equal(percentile([], 50), 0);
  // Never returns a value outside the input set.
  for (const p of [1, 25, 33, 66, 99]) {
    assert.ok(sorted.includes(percentile(sorted, p)));
  }
});

test("runSamplePreview scales with the iteration count it is given", () => {
  const small = runSamplePreview(SAMPLE_STARTUP, 100);
  assert.equal(small.iterations, 100);
  assert.ok(small.survivalAtHorizon >= 0 && small.survivalAtHorizon <= 1);
  assert.ok(small.runoutByMonth18 >= 0 && small.runoutByMonth18 <= 1);
});

// ---------------------------------------------------------------------------
// 2. The boundaries the job was given
// ---------------------------------------------------------------------------

test("the engine makes no network call and imports no data source", () => {
  const src = code(ENGINE);
  assert.doesNotMatch(src, /\bfetch\s*\(/, "client-side only: no fetch");
  assert.doesNotMatch(src, /axios|XMLHttpRequest|EventSource/);
  assert.doesNotMatch(src, /Math\.random/, "seeded, or SSR hydration breaks");
  // Exactly one import, and it is a pure local calculation module.
  const imports = src.match(/^import .*$/gm) ?? [];
  assert.equal(imports.length, 1);
  assert.match(imports[0], /from '@\/lib\/finance'/);
});

test("the component makes no network call either", () => {
  const src = code(COMPONENT);
  assert.doesNotMatch(src, /\bfetch\s*\(/);
  assert.doesNotMatch(src, /axios|XMLHttpRequest|EventSource/);
  assert.doesNotMatch(src, /\/api\//, "no new API call: the page's own lead form does the posting");
});

test("the preview never emits founder_activated", () => {
  // funnel.ts: sample companies must never count as activation.
  for (const p of [COMPONENT, ENGINE]) {
    assert.doesNotMatch(read(p), /founder_activated/);
  }
});

test("the page renders the preview only behind the flag", () => {
  const page = read(PAGE);
  assert.match(page, /import \{ SampleStartupPreview \} from "@\/components\/tools\/SampleStartupPreview"/);
  assert.match(page, /import \{ isSampleStartupPreviewEnabled \} from "@\/config\/features"/);
  assert.match(page, /isSampleStartupPreviewEnabled\(\) && \(/);
  assert.match(page, /<SampleStartupPreview onUnlock=\{focusEmailCapture\} \/>/);
  // With the flag off the page must still be the page it was: one email
  // capture path, and the preview is not a second one.
  assert.match(page, /data-testid="input-lead-email"/);
  // Still exactly one POST to the lead endpoint — the preview adds no second
  // capture path of its own.
  assert.equal((code(PAGE).match(/fetch\("\/api\/leads"/g) ?? []).length, 1);
});

test("the flag defaults ON, so it can be killed without a revert", () => {
  const flags = read(FLAGS);
  assert.match(
    flags,
    /SAMPLE_STARTUP_PREVIEW: import\.meta\.env\.VITE_FEATURE_SAMPLE_STARTUP_PREVIEW !== 'false'/,
  );
  assert.match(flags, /export function isSampleStartupPreviewEnabled\(\): boolean \{/);
  // `=== 'true'` would mean an unset variable ships nothing — a kill switch
  // that has to be switched on to be off is not a kill switch.
  assert.doesNotMatch(
    flags,
    /SAMPLE_STARTUP_PREVIEW: import\.meta\.env\.VITE_FEATURE_SAMPLE_STARTUP_PREVIEW === 'true'/,
  );
});

test("the component says out loud that the sample is an illustration", () => {
  const src = read(COMPONENT);
  assert.match(src, /illustration, not a prediction about your company/);
  // No bare "chance of surviving" claim anywhere in the copy.
  assert.doesNotMatch(src, /chance of surviving|probability of survival/i);
});

test("the preview hands the unlock back to the page's one email field", () => {
  const page = read(PAGE);
  // The ref is on the existing lead input, and the handler focuses it.
  assert.match(page, /ref=\{emailInputRef\}/);
  assert.match(page, /emailInputRef\.current/);
  assert.match(page, /function focusEmailCapture\(\)/);
});
