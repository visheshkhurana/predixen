// Audit 10-19 leftovers, client-side pieces: scenario sensitivity bars come
// from the real sensitivity function; no invented churn default or survival
// fallback; agent-sim "funding probability" relabelled; Slack link card.
//
// Run: npx tsx --test server/tests/audit-1019-leftovers.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  calculateSensitivity,
  sensitivityBarsFromResults,
  type FinancialState,
} from "../../client/src/lib/simulation/sensitivityAnalysis.ts";

const scenarios = readFileSync("client/src/pages/scenarios.tsx", "utf8");

const STATE: FinancialState = {
  monthlyRevenue: 40000, grossMargin: 70, opex: 30000, payroll: 50000, otherCosts: 5000,
  cashBalance: 600000, churnRate: 3, growthRate: 5, cac: 0, ltv: 0,
};

test("sensitivity bars are computed, ranked and scaled to the top lever", () => {
  const bars = sensitivityBarsFromResults(calculateSensitivity(STATE));
  assert.ok(bars.length > 0);
  assert.equal(bars[0].impact, 100);
  for (let i = 1; i < bars.length; i++) {
    assert.ok(bars[i].swingMonths <= bars[i - 1].swingMonths, "sorted by swing");
    assert.ok(bars[i].impact <= 100 && bars[i].impact >= 1);
  }
  // Payroll is the biggest cost line here, so it is the top lever.
  assert.equal(bars[0].label, "Payroll Costs");
  assert.equal(bars[0].level, "high");
  // Changing inputs changes the bars (not a constant list).
  const other = sensitivityBarsFromResults(calculateSensitivity({ ...STATE, opex: 200000, payroll: 1000 }));
  assert.equal(other[0].label, "Operating Expenses");
});

test("not computable -> no bars", () => {
  assert.deepEqual(sensitivityBarsFromResults([]), []);
  const flat = calculateSensitivity({ ...STATE, opex: 0, payroll: 0, grossMargin: 0, monthlyRevenue: 0, unavailable: ["grossMargin"] });
  assert.deepEqual(sensitivityBarsFromResults(flat), []);
});

test("scenarios page has no hardcoded sensitivity bars and hides the list when empty", () => {
  for (const n of ["impact: 85", "impact: 78", "impact: 52", "impact: 30"]) {
    assert.ok(!scenarios.includes(n), n);
  }
  assert.match(scenarios, /sensitivityBarsFromResults\(calculateSensitivity\(stressTestFinancialState\)\)/);
  assert.match(scenarios, /sensitivityBars\.length > 0 &&/);
});

test("no invented churn default or survival fallback", () => {
  assert.ok(!/params\.churn_change_pct = 5;/.test(scenarios), "bare 'churn' must not invent +5%");
  assert.match(scenarios, /churnTargetMatch/);
  assert.ok(!scenarios.includes("survival: '65'"));
  assert.ok(!scenarios.includes("65 * 0.7") && !scenarios.includes("65 * 1.15"));
});

test("agent-sim summary card says investor interest, not funding probability", () => {
  const src = readFileSync("client/src/pages/simulate-v2.tsx", "utf8");
  assert.match(src, /Investor interest/);
  assert.ok(!src.includes("summary.fundingProbability.toFixed"));
  assert.match(src, /investorInterestPct \?\? summary\?\.fundingProbability/);
});

test("Slack link card: paths match the backend endpoints", () => {
  // The component pulls in @/ UI modules that tsx cannot resolve here, so
  // check it by source against the FastAPI routes.
  const src = readFileSync("client/src/components/integrations/SlackLinkCard.tsx", "utf8");
  const backend = readFileSync("server/api/slack_bot.py", "utf8");
  assert.match(src, /\/api\/companies\/\$\{companyId\}\/integrations\/slack`/);
  assert.match(src, /\/api\/companies\/\$\{companyId\}\/integrations\/slack\/link-code`/);
  assert.match(backend, /@link_router\.post\("\/companies\/\{company_id\}\/integrations\/slack\/link-code"\)/);
  assert.match(backend, /@link_router\.get\("\/companies\/\{company_id\}\/integrations\/slack"\)/);
  assert.match(backend, /@link_router\.delete\("\/companies\/\{company_id\}\/integrations\/slack"\)/);
  assert.match(src, /`\/fc-link \$\{code\}`/);
  assert.match(src, /apiRequest\("DELETE", paths\.status\)/);
  assert.match(src, /apiRequest\("POST", paths\.linkCode\)/);
  const page = readFileSync("client/src/pages/integrations.tsx", "utf8");
  assert.match(page, /<SlackLinkCard companyId=\{slackCompanyId\} \/>/);
});
