// Simulator math/plumbing audit (2026-10-18), client-side pieces.
//
// Run: npx tsx server/tests/simulator-audit-1018.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  calculateRunway,
  calculateSensitivity,
  financialStateFromMetrics,
} from "../../client/src/lib/simulation/sensitivityAnalysis.ts";
import { formatRunwayMonths, twinSummary } from "../../client/src/lib/simulation/runwayFormat.ts";
import { currentRunwayMonths, runwayAfterHires } from "../../client/src/lib/hiringRunway.ts";

const MRR = 43949;
const NET = 24109;
const CASH = 514000;

test("what-if state reproduces the dashboard runway (COGS counted once)", () => {
  const state = financialStateFromMetrics({
    mrr: MRR,
    burnRate: NET,
    cashOnHand: CASH,
    totalMonthlyExpenses: NET + MRR,
    grossMarginPct: 62,
  });
  const runway = calculateRunway(state);
  assert.ok(Math.abs(runway - CASH / NET) < 1e-9, `runway ${runway}`);
  assert.ok(runway > 21 && runway < 21.5);
});

test("missing total expenses: net burn is not used as gross", () => {
  const state = financialStateFromMetrics({ mrr: MRR, burnRate: NET, cashOnHand: CASH, grossMarginPct: 70 });
  assert.ok(Math.abs(calculateRunway(state) - CASH / NET) < 1e-9);
});

test("no invented growth/churn/CAC/LTV/margin defaults", () => {
  const state = financialStateFromMetrics({
    mrr: MRR, burnRate: NET, cashOnHand: CASH,
    monthlyGrowthRate: 0, churnRatePct: 0, cac: 0, ltv: 0, grossMarginPct: 0,
  });
  assert.equal(state.growthRate, 0);
  assert.equal(state.churnRate, 0);
  assert.equal(state.cac, 0);
  assert.equal(state.ltv, 0);
  for (const k of ["growthRate", "churnRate", "cac", "ltv", "grossMargin", "payroll"]) {
    assert.ok(state.unavailable?.includes(k), `${k} should be unavailable`);
  }
  // Unknown margin still gives the dashboard runway.
  assert.ok(Math.abs(calculateRunway(state) - CASH / NET) < 1e-9);
  const names = calculateSensitivity(state).map((v) => v.name);
  assert.deepEqual(names, ["opex"]);
});

test("sensitivity leaves out variables the runway model does not use", () => {
  const state = financialStateFromMetrics({
    mrr: MRR, burnRate: NET, cashOnHand: CASH, grossMarginPct: 60,
    monthlyGrowthRate: 5, churnRatePct: 3, cac: 900, ltv: 9000,
    expenseBreakdown: { payroll: 30000, operating: 10000, marketing: 5000, otherOpex: 1000 },
  });
  const names = calculateSensitivity(state).map((v) => v.name).sort();
  assert.deepEqual(names, ["grossMargin", "opex", "payroll"]);
});

test("runway sentinel never renders as 999", () => {
  assert.equal(formatRunwayMonths(999), "Sustainable");
  assert.equal(formatRunwayMonths(12.34), "12.3");
  assert.equal(formatRunwayMonths(undefined), "—");
});

test("digital twin summary reads the server summary and the nested engine shape", () => {
  const flat = twinSummary({ summary: { p10_runway: 18, p50_runway: 21, p90_runway: 999, survival_probability: 0.4, iterations: 500, horizon_months: 24 } });
  assert.equal(flat?.p50_runway, 21);
  assert.equal(flat?.iterations, 500);
  const nested = twinSummary({ results: { runway: { p10: 1, p50: 2, p90: 3 }, survivalProbability: { "24m": 40 }, config: { iterations: 500, horizonMonths: 24 } } });
  assert.equal(nested?.p10_runway, 1);
  assert.equal(nested?.survival_probability, 0.4);
  assert.equal(twinSummary(null), null);
});

test("hiring planner runway from /truth/latest on canonical net burn", () => {
  const truth = { metrics: { net_burn: NET, cash_balance: CASH, runway_p50: 21.3, total_expenses: NET + MRR } };
  assert.equal(currentRunwayMonths(truth), Math.round((CASH / NET) * 10) / 10);
  assert.equal(runwayAfterHires(truth, 10000), Math.round((CASH / (NET + 10000)) * 10) / 10);
  // Profitable: no current runway; hires that tip it into burn do produce one.
  const profitable = { metrics: { net_burn: -5000, cash_balance: CASH } };
  assert.equal(currentRunwayMonths(profitable), null);
  assert.equal(runwayAfterHires(profitable, 15000), Math.round((CASH / 10000) * 10) / 10);
  assert.equal(currentRunwayMonths({}), null);
});

test("pages call real routes and drop dead UI", () => {
  const planner = readFileSync("client/src/pages/hiring-planner.tsx", "utf8");
  assert.doesNotMatch(planner, /"truth-scan", "latest"/);
  assert.match(planner, /"truth", "latest"/);

  const twin = readFileSync("client/src/pages/digital-twin.tsx", "utf8");
  assert.doesNotMatch(twin, /1,000 Simulations/);
  assert.doesNotMatch(twin, /results\.p10_runway\?\.toFixed/);
  assert.doesNotMatch(twin, /simplified model/);

  const goals = readFileSync("client/src/pages/goals.tsx", "utf8");
  assert.doesNotMatch(goals, /button-new-goal/);
  assert.doesNotMatch(goals, /Close Series A at \$3M/);

  const survival = readFileSync("client/src/pages/survival-simulator.tsx", "utf8");
  assert.doesNotMatch(survival, /\{runway\.p90\}mo/);
});
