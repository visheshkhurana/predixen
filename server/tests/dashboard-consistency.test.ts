// Dashboard consistency: one runway threshold set, an honest "All clear",
// one LTV source, and /truth reading the same figures as the dashboard.
//
// Tester findings on the sample company: the briefing said "All clear." next
// to amber tiles; LTV on the dashboard differed from /truth; /truth showed N/A
// for revenue the dashboard displayed; an empty company could read "All clear".
//
// Run: npx tsx --test server/tests/dashboard-consistency.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  runwayBand,
  runwayCardVariant,
  runwayKpiStatus,
  dashboardStatus,
  dashboardStatusSentence,
} from "../../client/src/lib/dashboardStatus.ts";
import { pickUnitEconomics, alignTruthMetrics } from "../../client/src/lib/sharedMetricSources.ts";

test("runway bands: <6 critical, <12 warning, 12-18 watch, >=18 healthy", () => {
  assert.equal(runwayBand(3), "critical");
  assert.equal(runwayBand(5.99), "critical");
  assert.equal(runwayBand(6), "warning");
  assert.equal(runwayBand(11.9), "warning");
  assert.equal(runwayBand(12), "watch");
  assert.equal(runwayBand(17.9), "watch");
  assert.equal(runwayBand(18), "healthy");
  assert.equal(runwayBand(21.3), "healthy");
  assert.equal(runwayBand(Infinity), "profitable");
  assert.equal(runwayBand(NaN), "unknown");
});

test("cash card and KPI tile use the same bands", () => {
  assert.equal(runwayCardVariant(runwayBand(4)), "danger");
  assert.equal(runwayCardVariant(runwayBand(9)), "warning");
  assert.equal(runwayCardVariant(runwayBand(14)), "warning");
  assert.equal(runwayCardVariant(runwayBand(21.3)), "success");
  assert.equal(runwayKpiStatus(runwayBand(4)), "red");
  assert.equal(runwayKpiStatus(runwayBand(9)), "yellow");
  assert.equal(runwayKpiStatus(runwayBand(14)), "yellow");
  assert.equal(runwayKpiStatus(runwayBand(21.3)), "green");
});

const greenKpis = [
  { name: "Runway", metric: "runway", status: "green" as const },
  { name: "Gross Margin", metric: "grossMargin", status: "green" as const },
];

test("all clear only when every shown metric is healthy", () => {
  const s = dashboardStatus({ hasData: true, runwayMonths: 21.3, alerts: [], highSeverityFlagCount: 0, kpis: greenKpis });
  assert.equal(s.kind, "all_clear");
  assert.equal(dashboardStatusSentence(s), "All clear.");
});

test("sample company: 21.3 mo runway but growth tile amber -> not all clear", () => {
  const s = dashboardStatus({
    hasData: true,
    runwayMonths: 21.3,
    alerts: [],
    highSeverityFlagCount: 0,
    kpis: [...greenKpis, { name: "Growth Rate", metric: "growthRate", status: "yellow" }],
  });
  assert.equal(s.kind, "watch");
  assert.equal(dashboardStatusSentence(s), "1 metric to watch: Growth Rate.");
});

test("12-18 month runway is 'watch', never all clear", () => {
  const s = dashboardStatus({ hasData: true, runwayMonths: 14, alerts: [], highSeverityFlagCount: 0, kpis: [] });
  assert.equal(s.kind, "watch");
  assert.deepEqual(s.watchNames, ["Runway"]);
});

test("runway warning alert and runway KPI tile are counted once", () => {
  const s = dashboardStatus({
    hasData: true,
    runwayMonths: 9,
    alerts: [{ type: "warning", metric: "runway", title: "Low Runway Warning" }],
    highSeverityFlagCount: 0,
    kpis: [{ name: "Runway", metric: "runway", status: "yellow" }],
  });
  assert.equal(s.kind, "warning");
  assert.equal(s.warningCount, 1);
  assert.equal(dashboardStatusSentence(s), "1 warning to review.");
});

test("truth-scan critical flags count, so 'Critical Issues' never sits next to 'All clear'", () => {
  const s = dashboardStatus({ hasData: true, runwayMonths: 30, alerts: [], highSeverityFlagCount: 2, kpis: greenKpis });
  assert.equal(s.kind, "critical");
  assert.equal(s.criticalCount, 2);
});

test("a red KPI tile is a warning; LTV:CAC alert and tile dedupe", () => {
  const s = dashboardStatus({
    hasData: true,
    runwayMonths: 30,
    alerts: [{ type: "warning", metric: "ltvCac" }],
    highSeverityFlagCount: 0,
    kpis: [{ name: "LTV/CAC", metric: "ltv_cac", status: "red" }],
  });
  assert.equal(s.warningCount, 1);
});

test("empty company is 'not scored yet', never all clear", () => {
  const s = dashboardStatus({ hasData: false, runwayMonths: Infinity, alerts: [], highSeverityFlagCount: 0, kpis: [] });
  assert.equal(s.kind, "not_scored");
  assert.match(dashboardStatusSentence(s), /^Not scored yet/);
});

// ---- LTV: one source -------------------------------------------------------

const invented = (k: string) => ({ cac: 500, ltv: 3000, ltv_cac_ratio: 6 } as Record<string, number>)[k] ?? 0;

test("/metrics/computed is final: its 0 (unknown) is not replaced by baseline/truth values", () => {
  const u = pickUnitEconomics({
    computed: { cac: 0, ltv: 0, ltvCacRatio: 0 },
    baselineExt: { cac: 500, ltv: 3000, ltvCacRatio: 6 },
    truthReal: invented,
  });
  assert.deepEqual(u, { cac: 0, ltv: 0, ltvCacRatio: 0 });
});

test("server LTV is what the dashboard shows", () => {
  const u = pickUnitEconomics({
    computed: { cac: 1500, ltv: 4800, ltvCacRatio: 3.2 },
    baselineExt: { cac: 500, ltv: 3000, ltvCacRatio: 6 },
    truthReal: invented,
  });
  assert.deepEqual(u, { cac: 1500, ltv: 4800, ltvCacRatio: 3.2 });
});

test("falls back to baseline then real truth values only when computed is unavailable", () => {
  const u = pickUnitEconomics({ computed: null, baselineExt: { ltv: 0 }, truthReal: (k) => (k === "ltv" ? 2000 : k === "cac" ? 400 : 0) });
  assert.equal(u.ltv, 2000);
  assert.equal(u.cac, 400);
  assert.equal(u.ltvCacRatio, 5);
});

// ---- /truth reads the dashboard's figures ---------------------------------

const shared = {
  hasData: true,
  mrr: 43949,
  arr: 527388,
  cashOnHand: 513746,
  netBurn: 24109,
  totalMonthlyExpenses: 68058,
  runway: 21.3,
  grossMarginPct: 75,
  cac: 1500,
  ltv: 4800,
  ltvCacRatio: 3.2,
  paybackPeriod: 8,
  sources: { cac: "reported", ltv: "reported", ltvCacRatio: "reported", paybackPeriod: "computed" },
};

test("sample-company scan keys (mrr, runway_months) are normalised", () => {
  const m = alignTruthMetrics({ mrr: { value: 43949 }, runway_months: { value: 21.3 } }, null);
  assert.deepEqual(m.monthly_revenue, { value: 43949 });
  assert.deepEqual(m.runway_p50, { value: 21.3 });
});

test("/truth shows the dashboard's revenue, cash, burn, runway and LTV", () => {
  const m = alignTruthMetrics({ ltv: { value: 9999 }, runway_p50: 16.5 }, shared);
  assert.equal(m.monthly_revenue, 43949);
  assert.equal(m.cash_balance, 513746);
  assert.equal(m.net_burn, 24109);
  assert.equal(m.runway_p50, 21.3);
  assert.equal(m.ltv, 4800);
  assert.equal(m.cac, 1500);
  assert.equal(m.ltv_cac_ratio, 3.2);
});

test("invented truth-scan LTV is never shown on /truth", () => {
  const raw = { ltv: 3000, cac: 500, ltv_cac_ratio: 6, _estimated_metrics: ["ltv", "cac", "ltv_cac_ratio"] };
  assert.equal(alignTruthMetrics(raw, null).ltv, null);
  const m = alignTruthMetrics(raw, { ...shared, cac: 0, ltv: 0, ltvCacRatio: 0, sources: {} });
  assert.equal(m.ltv, null);
  assert.equal(m.cac, null);
  assert.equal(m.ltv_cac_ratio, null);
});

test("not burning -> sustainable; cash-only company is not called sustainable", () => {
  const prof = alignTruthMetrics({}, { ...shared, netBurn: -5000, runway: Infinity });
  assert.equal(prof.runway_sustainable, true);
  const cashOnly = alignTruthMetrics({}, { ...shared, mrr: 0, arr: 0, totalMonthlyExpenses: 0, netBurn: 0, runway: Infinity });
  assert.notEqual(cashOnly.runway_sustainable, true);
});

// ---- wiring ---------------------------------------------------------------

const read = (p: string) => readFileSync(new URL(p, import.meta.url), "utf8");

test("overview uses the shared status helper, not its own All-clear rule", () => {
  const src = read("../../client/src/pages/overview.tsx");
  assert.match(src, /dashboardStatus\(/);
  assert.doesNotMatch(src, /> All clear\.<\/span>/);
  assert.match(src, /runwayCardVariant\(runwayBand\(/);
  assert.match(src, /Not scored yet/);
});

test("useFinancialMetrics and /truth go through the shared source helpers", () => {
  assert.match(read("../../client/src/hooks/useFinancialMetrics.ts"), /pickUnitEconomics\(/);
  assert.match(read("../../client/src/pages/truth-scan.tsx"), /alignTruthMetrics\(rawMetrics, sharedMetrics\)/);
});

test("demo simulation results carry the signup CTA, gated on demo sessions", () => {
  const ws = read("../../client/src/pages/simulate-workspace.tsx");
  assert.match(ws, /<DemoSignupCTA show=\{!!latestRun\} placement="scenarios"/);
  assert.match(ws, /<DemoSignupCTA placement="flight-simulator"/);
  const cta = read("../../client/src/components/DemoSignupCTA.tsx");
  assert.match(cta, /isDemoEmail\(user\?\.email\)/);
  assert.match(cta, /Create your free account to run this on your numbers/);
});
