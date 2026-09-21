// Residual client Switch aliases from the #44 defer list.
// Server SPA fallback returns 200 HTML for every path, so 404s are client-side:
// unmatched Switch entries render NotFound. This file only reads client sources
// (App.tsx). It must not open templates.py, onboarding_sequence.py, or
// templates/integrations/notifications lock files.
import { readFileSync } from "fs";
import assert from "assert";

const app = readFileSync("client/src/App.tsx", "utf8");
const self = readFileSync(new URL(import.meta.url).pathname, "utf8");

assert.doesNotMatch(
  self,
  /readFileSync\(["']server\/email\/(templates|onboarding_sequence)\.py["']/,
  "this test must not read templates.py or onboarding_sequence.py",
);
assert.doesNotMatch(
  self,
  /readFileSync\(["']client\/src\/pages\/(integrations|settings|alerts)\.tsx["']/,
  "this test must not open integrations/notifications lock files",
);

function assertAlias(from: string, to: string) {
  const fromEsc = from.replace(/\//g, "\\/");
  const toEsc = to.replace(/\//g, "\\/");
  const re = new RegExp(
    `path="${fromEsc}"[\\s\\S]{0,220}?Redirect to="${toEsc}"`,
  );
  assert.match(app, re, `${from} must redirect to ${to}`);
}

// Live destinations these aliases land on must stay registered.
const live = ["/settings", "/signup", "/data", "/integrations"];
for (const path of live) {
  assert.match(
    app,
    new RegExp(`path="${path.replace("/", "\\/")}"`),
    `${path} must be registered as a live destination`,
  );
}

assertAlias("/unsubscribe", "/settings");
assertAlias("/apply", "/signup");
assertAlias("/matches", "/");
assertAlias("/referral", "/signup");
assertAlias("/ingest", "/data");
assertAlias("/data-source/:id", "/integrations");

assert.match(app, /<Route component=\{NotFound\} \/>/, "Switch catch-all must remain NotFound");

console.log("PASS  residual dead-route source checks");
