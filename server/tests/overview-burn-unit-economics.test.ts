// /overview honesty: burn, runway wording, unit economics, margin target.
//
// A D2C founder typed revenue ₹25L, margin 55%, costs and cash — no marketing
// spend, no customers. /overview showed "AI Estimated -₹5.8L /month" burn,
// "Runway is comfortably above 18 months at Profitable.", invented CAC / LTV /
// LTV:CAC, and a "Gross margin is 55% (target: 70%+)" pricing nudge.
//
// Run: npx tsx server/tests/overview-burn-unit-economics.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  netBurnSource,
  burnCardDisplay,
  briefingBurnSentence,
  briefingRunwaySentence,
  unitEconomicsAvailability,
} from "../../client/src/lib/overviewDisplay.ts";
import {
  generateSuggestedActions,
  grossMarginTargetFor,
  resolveOverviewSuggestedAction,
} from "../../client/src/lib/truthScanSuggestedActions.ts";

const fmt = (n: number) => `₹${(n / 100000).toFixed(1)}L`;
const months = (m: number) => `${m.toFixed(1)} months`;

// --- burn source -------------------------------------------------------------

test("a surplus computed from founder figures is 'computed', not estimated", () => {
  assert.equal(netBurnSource({ netBurn: -575000, mrr: 2500000, totalExpenses: 1925000 }), "computed");
  assert.equal(netBurnSource({ netBurn: 120000, mrr: 0, totalExpenses: 120000 }), "computed");
  assert.equal(netBurnSource({ netBurn: 0, mrr: 50000, totalExpenses: 50000 }), "computed");
});

test("burn with nothing behind it is estimated", () => {
  assert.equal(netBurnSource({ netBurn: 0, mrr: 0, totalExpenses: 0 }), "estimated");
  assert.equal(netBurnSource({ netBurn: NaN, mrr: 100, totalExpenses: 100 }), "estimated");
});

// --- burn card ---------------------------------------------------------------

test("negative burn shows as a monthly surplus with a positive amount", () => {
  const d = burnCardDisplay(-575000);
  assert.equal(d.title, "Monthly Surplus");
  assert.equal(d.amount, 575000);
  assert.equal(d.isSurplus, true);
  assert.equal(d.variant, "success");
});

test("positive burn keeps the Burn Rate card", () => {
  const d = burnCardDisplay(300000);
  assert.equal(d.title, "Burn Rate");
  assert.equal(d.amount, 300000);
  assert.equal(d.subtitle, "/month");
  assert.equal(d.isSurplus, false);
});

// --- briefing ----------------------------------------------------------------

test("briefing says a profitable company is not burning cash", () => {
  const s = briefingBurnSentence(-575000, 2500000, fmt);
  assert.equal(s, "You are not burning cash — revenue exceeds costs by ₹5.8L/mo.");
  assert.doesNotMatch(s, /AI-estimated|-₹/);
});

test("briefing burn wording for burning companies is unchanged in meaning", () => {
  assert.match(briefingBurnSentence(100000, 500000, fmt), /below revenue — you are burning efficiently at ₹1\.0L\/mo\./);
  assert.match(briefingBurnSentence(900000, 500000, fmt), /above revenue — monitor spending closely/);
  assert.match(briefingBurnSentence(0, 500000, fmt), /not burning cash — revenue covers costs exactly/);
});

test("runway sentence reads correctly in every band", () => {
  const profitable = briefingRunwaySentence(Infinity, months);
  assert.equal(profitable, "Runway is not a constraint while revenue covers costs.");
  assert.doesNotMatch(profitable, /at Profitable/);
  assert.equal(briefingRunwaySentence(24, months), "Runway is comfortably above 18 months at 24.0 months.");
  assert.equal(briefingRunwaySentence(18, months), "Runway is comfortably above 18 months at 18.0 months.");
  assert.equal(briefingRunwaySentence(14.2, months), "Runway is worth watching at 14.2 months — 12–18 months is when to plan the next raise.");
  assert.equal(briefingRunwaySentence(8, months), "Runway is getting tight at 8.0 months — consider extending.");
  assert.equal(briefingRunwaySentence(3.5, months), "Runway is critically low at 3.5 months — immediate action needed.");
  assert.match(briefingRunwaySentence(NaN, months), /unknown/);
});

// --- unit economics ----------------------------------------------------------

test("estimated CAC / LTV are not shown as numbers", () => {
  const u = unitEconomicsAvailability({
    cac: 20000, ltv: 286458, ltvCacRatio: 14.3,
    sources: { cac: "estimated", ltv: "estimated", ltvCacRatio: "estimated" },
  });
  assert.deepEqual(u, { cacKnown: false, ltvKnown: false, ratioKnown: false });
});

test("missing CAC / LTV are not shown as numbers", () => {
  const u = unitEconomicsAvailability({ cac: 0, ltv: 0, ltvCacRatio: 0, sources: {} });
  assert.deepEqual(u, { cacKnown: false, ltvKnown: false, ratioKnown: false });
});

test("reported / computed CAC and LTV are shown", () => {
  const u = unitEconomicsAvailability({
    cac: 4000, ltv: 24000, ltvCacRatio: 6,
    sources: { cac: "reported", ltv: "computed", ltvCacRatio: "computed" },
  });
  assert.deepEqual(u, { cacKnown: true, ltvKnown: true, ratioKnown: true });
});

test("ratio needs both sides real", () => {
  const u = unitEconomicsAvailability({
    cac: 4000, ltv: 24000, ltvCacRatio: 6,
    sources: { cac: "reported", ltv: "estimated", ltvCacRatio: "computed" },
  });
  assert.equal(u.cacKnown, true);
  assert.equal(u.ratioKnown, false);
});

// --- gross margin target -----------------------------------------------------

test("physical-goods industries use a 40% flag / 50%+ target", () => {
  for (const ind of ["d2c", "ecommerce", "food", "marketplace", "D2C"]) {
    assert.deepEqual(grossMarginTargetFor(ind), { flagBelow: 40, targetLabel: "50%+" }, ind);
  }
});

test("software and unknown industries keep 65% / 70%+", () => {
  for (const ind of ["saas", "fintech", "", null, undefined]) {
    assert.deepEqual(grossMarginTargetFor(ind as any), { flagBelow: 65, targetLabel: "70%+" });
  }
});

test("55% margin is not flagged for D2C but is for SaaS", () => {
  const metrics = { gross_margin: 55 };
  const d2c = generateSuggestedActions(metrics, [], { industry: "d2c" });
  assert.equal(d2c.find((a) => a.id === "action-margin"), undefined);
  const saas = generateSuggestedActions(metrics, [], { industry: "saas" });
  const m = saas.find((a) => a.id === "action-margin");
  assert.ok(m);
  assert.equal(m!.metricIssue, "Gross margin is 55% (target: 70%+)");
  // No options: unchanged default behaviour.
  assert.ok(generateSuggestedActions(metrics).find((a) => a.id === "action-margin"));
});

test("D2C below 40% is flagged with a 50%+ target", () => {
  const d2c = generateSuggestedActions({ gross_margin: 32 }, [], { industry: "food" });
  const m = d2c.find((a) => a.id === "action-margin");
  assert.ok(m);
  assert.equal(m!.metricIssue, "Gross margin is 32% (target: 50%+)");
});

test("overview card resolves with the company industry", () => {
  const scan = { metrics: { gross_margin: 55 }, flags: [] };
  assert.equal(resolveOverviewSuggestedAction({ enabled: true, isSample: false, scan, industry: "d2c" }), null);
  assert.equal(resolveOverviewSuggestedAction({ enabled: true, isSample: false, scan, industry: "saas" })?.id, "action-margin");
});

// --- wiring ------------------------------------------------------------------

test("overview and truth scan pass the industry; overview drops the AI-estimated burn wording", () => {
  const overview = readFileSync("client/src/pages/overview.tsx", "utf8");
  const truth = readFileSync("client/src/pages/truth-scan.tsx", "utf8");
  assert.match(overview, /industry=\{currentCompany\.industry\}/);
  assert.match(truth, /generateSuggestedActions\(metrics, flags, \{ industry: currentCompany\?\.industry \}\)/);
  assert.doesNotMatch(overview, /'AI-estimated'/);
  assert.doesNotMatch(overview, /Runway is \{briefingRunwayShift\} at/);
});

test("metrics hook never falls back to estimated truth-scan unit economics", () => {
  const hook = readFileSync("client/src/hooks/useFinancialMetrics.ts", "utf8");
  // Unit economics go through pickUnitEconomics (truth fallback = tsReal,
  // which drops estimated values); see dashboard-consistency.test.ts.
  assert.match(hook, /pickUnitEconomics\(\{[\s\S]*?truthReal: tsReal,/);
  assert.match(hook, /sources\['netBurn'\] = netBurnSource\(/);
});
