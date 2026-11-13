// /simulate must not post canned fallbacks for null founder metrics.
// Those omissions come back from the engine as assumed, never entered.
//
// Run: npx tsx server/tests/simulation-v2-client-payload.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { buildSimulationV2Payload } from "../../client/src/lib/simulation/v2Request.ts";
import {
  formatSyncedAtLocal,
  groupInputProvenance,
} from "../../client/src/lib/simulation/inputProvenance.ts";

const page = readFileSync("client/src/pages/simulate-workspace.tsx", "utf8");
const controls = {
  totalRounds: 12,
  fundingClimate: 0.6,
  marketGrowth: 0.5,
  marketVolatility: 0.1,
};

test("null mrr, burn, cash, growth and headcount are not sent", () => {
  const payload = buildSimulationV2Payload(
    {
      mrr: null,
      burnRate: null,
      cashOnHand: null,
      monthlyGrowthRate: null,
      headcount: null,
    },
    controls,
  );

  for (const key of [
    "monthly_revenue",
    "monthly_burn",
    "cash_balance",
    "growth_rate",
    "team_size",
    "customers",
    "churn_rate",
  ]) {
    assert.equal(key in payload, false, `${key} must not be sent`);
  }
  assert.deepEqual(payload, {
    total_rounds: 12,
    funding_climate: 0.6,
    market_growth: 0.5,
    market_volatility: 0.1,
  });
});

test("non-null base metrics are sent and canned customers/churn are not", () => {
  const payload = buildSimulationV2Payload(
    {
      mrr: 43948.68,
      burnRate: 24109.37,
      cashOnHand: 513745.58,
      monthlyGrowthRate: 10.8,
      headcount: 11,
    },
    controls,
  );
  assert.equal(payload.monthly_revenue, 43948.68);
  // monthly_burn is GROSS spend (engine does cash += mrr - burn): net + MRR.
  assert.ok(Math.abs(payload.monthly_burn - (24109.37 + 43948.68)) < 1e-6);
  assert.equal(payload.cash_balance, 513745.58);
  assert.ok(Math.abs(payload.growth_rate - 0.108) < 1e-12);
  assert.equal(payload.team_size, 11);
  assert.equal("customers" in payload, false);
  assert.equal("churn_rate" in payload, false);
});

test("zero burn and cash are sent; zero headcount is not a team size", () => {
  const payload = buildSimulationV2Payload(
    { mrr: 0, burnRate: 0, cashOnHand: 0, monthlyGrowthRate: 0, headcount: 0 },
    controls,
  );
  assert.equal(payload.monthly_revenue, 0);
  assert.equal(payload.monthly_burn, 0);
  assert.equal(payload.cash_balance, 0);
  assert.equal(payload.growth_rate, 0);
  assert.equal("team_size" in payload, false);
});

test("gross spend reproduces the dashboard's net burn and runway", () => {
  const mrr = 43949;
  const net = 24109;
  const cash = 514000;
  const payload = buildSimulationV2Payload({ mrr, burnRate: net, cashOnHand: cash }, controls);
  // One month of the engine's cash update: cash += mrr - burn.
  const monthlyChange = payload.monthly_revenue - payload.monthly_burn;
  assert.ok(Math.abs(monthlyChange + net) < 1e-9);
  const runway = cash / (payload.monthly_burn - payload.monthly_revenue);
  assert.ok(runway > 21 && runway < 21.5, `runway ${runway}`);
});

test("profitable company sends total expenses; burn without MRR is not sent", () => {
  const profitable = buildSimulationV2Payload(
    { mrr: 100000, burnRate: 0, totalMonthlyExpenses: 80000 },
    controls,
  );
  assert.equal(profitable.monthly_burn, 80000);
  const noMrr = buildSimulationV2Payload({ mrr: null, burnRate: 24109 }, controls);
  assert.equal("monthly_burn" in noMrr, false);
});

test("missing or unknown provenance is not labelled entered", () => {
  assert.equal(groupInputProvenance(null), null);
  assert.equal(groupInputProvenance(undefined), null);
  assert.equal(groupInputProvenance({}), null);
  const groups = groupInputProvenance({
    mystery: { kind: "guessed" },
    monthly_revenue: { kind: "assumed" },
    funding_climate: { kind: "entered" },
    customers: { kind: "synced", source: "stripe", synced_at: "2026-01-02T03:04:05Z" },
  });
  assert.ok(groups);
  assert.deepEqual(groups.entered, ["funding_climate"]);
  assert.deepEqual(groups.assumed, ["monthly_revenue"]);
  assert.deepEqual(groups.synced, ["customers"]);
  assert.equal(groups.entered.includes("mystery"), false);
});

test("synced_at renders in a chosen local timezone", () => {
  const local = formatSyncedAtLocal("2026-01-02T03:04:05Z", "en-US", "America/Los_Angeles");
  assert.match(local, /Jan 1, 2026/);
  assert.match(local, /7:04/);
});

test("/simulate posts the payload builder and renders the inputs panel", () => {
  assert.match(page, /buildSimulationV2Payload\(baseMetrics/);
  assert.match(page, /SimulationInputsPanel/);
  assert.doesNotMatch(page, /monthly_revenue:\s*baseMetrics\?\.mrr \?\? 50000/);
  assert.doesNotMatch(page, /monthly_burn:\s*baseMetrics\?\.burnRate \?\? 80000/);
  assert.doesNotMatch(page, /cash_balance:\s*baseMetrics\?\.cashOnHand \?\? 500000/);
  assert.doesNotMatch(page, /customers:\s*50/);
  assert.doesNotMatch(page, /churn_rate:\s*0\.03/);
  assert.doesNotMatch(page, /headcount \|\| 10/);
  assert.doesNotMatch(page, /monthlyGrowthRate \?\? 5/);
});
