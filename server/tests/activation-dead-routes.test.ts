// Client Switch aliases on signup → first trusted insight.
// Server SPA fallback returns 200 HTML for every path, so 404s are client-side:
// unmatched Switch entries render NotFound. This file only reads client sources
// (App.tsx + in-app navigations). It must not open templates.py or
// onboarding_sequence.py.
import { readFileSync } from "fs";
import assert from "assert";

const app = readFileSync("client/src/App.tsx", "utf8");
const gate = readFileSync("client/src/components/TruthScanGate.tsx", "utf8");
const suggested = readFileSync("client/src/components/TruthScanSuggestedActions.tsx", "utf8");
const suggestedLib = readFileSync("client/src/lib/truthScanSuggestedActions.ts", "utf8");
const stepper = readFileSync("client/src/components/Layout/Stepper.tsx", "utf8");
const overview = readFileSync("client/src/pages/overview.tsx", "utf8");

assert.doesNotMatch(
  readFileSync(new URL(import.meta.url).pathname, "utf8"),
  /readFileSync\(["']server\/email\/(templates|onboarding_sequence)\.py["']/,
  "this test must not read templates.py or onboarding_sequence.py",
);

const owned = [
  "/onboarding",
  "/overview",
  "/dashboard",
  "/truth-scan",
  "/simulate",
  "/scenarios",
  "/decisions",
];
for (const path of owned) {
  assert.match(app, new RegExp(`path="${path.replace("/", "\\/")}"`), `${path} must be registered`);
}

assert.match(app, /path="\/onboard"/, "stale /onboard alias must exist");
assert.match(app, /Redirect to="\/onboarding"/, "/onboard must redirect to /onboarding");

assert.match(app, /path="\/simulation"/, "/simulation alias must exist");
assert.match(app, /path="\/simulator"/, "/simulator alias must exist");

assert.match(
  app,
  /path="\/companies\/:companyId\/scenarios"/,
  "TruthScanGate leftover /companies/:id/scenarios must alias",
);

assert.match(app, /path="\/account\/notifications"/, "/account/notifications alias must exist");
assert.match(app, /path="\/settings\/notifications"/, "/settings/notifications alias must exist");

assert.doesNotMatch(
  gate,
  /\/companies\/\$\{companyId\}\/scenarios/,
  "TruthScanGate must not navigate to the unmatched /companies/:id/scenarios path",
);
assert.match(gate, /setLocation\('\/simulate'\)/, "TruthScanGate finalize must go to /simulate");

assert.match(
  suggested,
  /buildSimulateUrl\(action/,
  "truth-scan suggested actions must deep-link via buildSimulateUrl",
);
assert.match(
  suggestedLib,
  /`\/simulate\$\{qs/,
  "truth-scan suggested actions must open /simulate, not the /scenarios redirect",
);
assert.doesNotMatch(
  suggested,
  /navigate\(`\/scenarios/,
  "suggested actions must not navigate to the leftover /scenarios path",
);

assert.match(stepper, /path: '\/simulate'/, "first-run stepper Simulate must link to /simulate");
assert.match(stepper, /'\/simulate': 'simulation'/, "stepper must highlight Simulate on /simulate");
assert.match(stepper, /'\/truth-scan': 'truth'/, "stepper must recognize /truth-scan");
assert.match(stepper, /'\/dashboard': 'truth'/, "stepper must recognize /dashboard");

assert.doesNotMatch(
  overview,
  /setLocation\('\/scenarios'\)/,
  "overview first-insight CTAs must not send users through the leftover /scenarios path",
);

console.log("PASS  activation-path dead-route source checks");
