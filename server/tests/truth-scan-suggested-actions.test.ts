// Truth Scan Suggested Actions → /simulate prefill (product bet #4).
//
// CTAs are derived from red Truth Scan metrics already on the page (no
// Modeling / truth_scan.py). Each deep-link uses wizard-native lever names
// so ScenarioWizard / StrategicScenarioBuilder land ready to run.
//
// Run: npx tsx server/tests/truth-scan-suggested-actions.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  generateSuggestedActions,
  buildSimulateUrl,
  parseSimulatePrefill,
  SUGGESTED_ACTIONS_MAX,
  TRUTH_SCAN_SIM_SOURCE,
  TRUTH_SCAN_SIM_FROM,
} from "../../client/src/lib/truthScanSuggestedActions.ts";

const suggested = readFileSync("client/src/components/TruthScanSuggestedActions.tsx", "utf8");
const scenarios = readFileSync("client/src/pages/scenarios.tsx", "utf8");
const hooks = readFileSync("client/src/api/hooks.ts", "utf8");
const features = readFileSync("client/src/config/features.ts", "utf8");
const truthPage = readFileSync("client/src/pages/truth-scan.tsx", "utf8");

const RED_METRICS = {
  runway_p50: 4.2,
  runway_sustainable: false,
  burn_multiple: 3.8,
  gross_margin: 48,
  churn_rate_customer: 0.12,
};

test("red metrics produce 2–3 CTAs, never more than SUGGESTED_ACTIONS_MAX", () => {
  const actions = generateSuggestedActions(RED_METRICS, []);
  assert.ok(actions.length >= 2, "expected at least two CTAs from a fully red scan");
  assert.ok(actions.length <= SUGGESTED_ACTIONS_MAX);
  assert.equal(SUGGESTED_ACTIONS_MAX, 3);
});

test("CTA → prefill mapping uses wizard-native levers", () => {
  const actions = generateSuggestedActions(RED_METRICS, []);
  const byId = Object.fromEntries(actions.map((a) => [a.id, a]));

  assert.ok(byId["action-runway"], "low runway must suggest a fundraising CTA");
  assert.equal(byId["action-runway"].strategyId, "balance_bridge");
  assert.equal(byId["action-runway"].wizardParams.fundraise_amount, 500000);
  assert.equal(byId["action-runway"].wizardParams.fundraise_month, 3);

  assert.ok(byId["action-burn"], "high burn multiple must suggest cost optimization");
  assert.equal(byId["action-burn"].strategyId, "extend_conservative");
  assert.equal(byId["action-burn"].wizardParams.burn_reduction_pct, 15);

  assert.ok(byId["action-margin"], "low gross margin must suggest pricing");
  assert.equal(byId["action-margin"].strategyId, "extend_pricing");
  assert.equal(byId["action-margin"].wizardParams.pricing_change_pct, 12);
});

test("a single red runway metric still yields two CTAs (raise + cut)", () => {
  const actions = generateSuggestedActions(
    { runway_p50: 8, runway_sustainable: false },
    [],
  );
  assert.equal(actions.length, 2);
  assert.deepEqual(
    actions.map((a) => a.id).sort(),
    ["action-burn", "action-runway"],
  );
});

test("healthy metrics produce no CTAs (block stays hidden)", () => {
  const actions = generateSuggestedActions(
    {
      runway_p50: 24,
      runway_sustainable: true,
      burn_multiple: 1.1,
      gross_margin: 78,
      churn_rate_customer: 0.03,
    },
    [],
  );
  assert.equal(actions.length, 0);
});

test("buildSimulateUrl round-trips through parseSimulatePrefill", () => {
  const [action] = generateSuggestedActions({ runway_p50: 5, runway_sustainable: false }, []);
  assert.ok(action);
  const url = buildSimulateUrl(action, 42);
  assert.match(url, /^\/simulate\?/);
  assert.doesNotMatch(url, /^\/scenarios/);
  const qs = url.split("?")[1];
  const prefill = parseSimulatePrefill(qs);
  assert.ok(prefill);
  assert.equal(prefill.from, TRUTH_SCAN_SIM_SOURCE);
  assert.equal(prefill.actionId, action.id);
  assert.equal(prefill.strategyId, action.strategyId);
  assert.equal(prefill.params.fundraise_amount, action.wizardParams.fundraise_amount);
  assert.equal(prefill.params.fundraise_month, action.wizardParams.fundraise_month);
  assert.match(url, /company=42/);
});

test("object-shaped metrics (value wrappers) still count as red", () => {
  const actions = generateSuggestedActions(
    { runway_p50: { value: 3.5 }, runway_sustainable: false },
    [],
  );
  assert.ok(actions.some((a) => a.id === "action-runway"));
});

test("CTA click is not simulation_started; Run on /simulate is", () => {
  assert.match(suggested, /trackEvent\('cta_click'/);
  assert.doesNotMatch(suggested, /trackEvent\(\s*['"]simulation_started['"]/);
  assert.match(
    hooks,
    /trackEvent\(\s*'simulation_started'/,
    "simulation_started must fire when the prefilled scenario actually runs",
  );
  assert.match(hooks, /source: TRUTH_SCAN_SIM_SOURCE/);
  assert.match(hooks, /trackEvent\(\s*'simulation_run'/);
  assert.match(
    hooks,
    /trackFounderActivated\(\{\s*source: 'simulation'/,
    "founder_activated path=simulation stays on the existing first-real-run hook",
  );
  assert.match(hooks, /company\.is_sample === false/);
});

test("scenarios page consumes from=truth_scan and lands ready to run", () => {
  assert.match(scenarios, /parseSimulatePrefill\(window\.location\.search\)/);
  assert.match(scenarios, /data-testid="card-truth-scan-prefill"/);
  assert.match(scenarios, /data-testid="button-run-truth-scan-prefill"/);
  assert.match(scenarios, /initialStrategyId=\{truthScanPrefill\?\.strategyId\}/);
  assert.match(scenarios, /initialStep=\{truthScanPrefill \? 5 : undefined\}/);
});

test("kill switch is a boolean, not new infra", () => {
  assert.match(features, /TRUTH_SCAN_SUGGESTED_ACTIONS:\s*true/);
  assert.match(truthPage, /FEATURE_FLAGS\.TRUTH_SCAN_SUGGESTED_ACTIONS/);
});

test("attribution constants stay stable for PostHog breakdowns", () => {
  assert.equal(TRUTH_SCAN_SIM_SOURCE, "truth_scan");
  assert.equal(TRUTH_SCAN_SIM_FROM, "truth_scan_suggested_action");
});
