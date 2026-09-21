// Source assertions for dead client routes on signup → first trusted insight.
// Server SPA fallback returns 200 HTML for every path, so 404s are client-side:
// unmatched Switch entries render NotFound. These checks lock the aliases and
// the sources that used to emit the dead URLs.
import { readFileSync } from "fs";
import assert from "assert";

const app = readFileSync("client/src/App.tsx", "utf8");
const gate = readFileSync("client/src/components/TruthScanGate.tsx", "utf8");
const suggested = readFileSync("client/src/components/TruthScanSuggestedActions.tsx", "utf8");
const stepper = readFileSync("client/src/components/Layout/Stepper.tsx", "utf8");
const overview = readFileSync("client/src/pages/overview.tsx", "utf8");
const onboardingEmail = readFileSync("server/email/onboarding_sequence.py", "utf8");
const emailTemplates = readFileSync("server/email/templates.py", "utf8");

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

assert.match(app, /path="\/simulation"/, "email /simulation alias must exist");
assert.match(app, /path="\/simulator"/, "/simulator alias must exist");

assert.match(
  app,
  /path="\/companies\/:companyId\/scenarios"/,
  "TruthScanGate leftover /companies/:id/scenarios must alias",
);

assert.match(app, /path="\/account\/notifications"/, "onboarding-email /account/notifications alias");
assert.match(app, /path="\/settings\/notifications"/, "email /settings/notifications alias");

assert.doesNotMatch(
  gate,
  /\/companies\/\$\{companyId\}\/scenarios/,
  "TruthScanGate must not navigate to the unmatched /companies/:id/scenarios path",
);
assert.match(gate, /setLocation\('\/simulate'\)/, "TruthScanGate finalize must go to /simulate");

assert.match(
  suggested,
  /`\/simulate\$\{params/,
  "truth-scan suggested actions must open /simulate, not the /scenarios redirect",
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

assert.doesNotMatch(
  onboardingEmail,
  /\/account\/notifications/,
  "onboarding drip footer must not link to unmatched /account/notifications",
);
assert.match(onboardingEmail, /\{APP_URL\}\/settings"/, "onboarding drip Manage emails → /settings");

assert.doesNotMatch(
  emailTemplates,
  /\/settings\/notifications/,
  "email preference URL must not be unmatched /settings/notifications",
);
assert.doesNotMatch(
  emailTemplates,
  /APP_URL\}\/simulation"/,
  "simulation-complete / decision emails must not CTA to unmatched /simulation",
);
assert.match(emailTemplates, /APP_URL\}\/simulate"/, "simulation emails must CTA to /simulate");

console.log("PASS  activation-path dead-route source checks");
