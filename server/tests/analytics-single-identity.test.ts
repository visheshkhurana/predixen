// Guards the two changes that made a visitor countable.
//
// Both bugs were invisible in code review and obvious in the data: on 15 Aug a
// single device produced two $pageview events 258ms apart on one path, under
// two distinct_ids and two session_ids. Across 15-19 Aug that inflated sessions
// against real devices by ~1.8x (28 vs 16, 36 vs 21, 23 vs 13), and it meant an
// ad click and a later signup could never land on the same identity.
//
// Run: npx tsx server/tests/analytics-single-identity.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { flushPostHogQueue, type QueuedPostHogCall } from "../../client/src/lib/posthog-queue";
import { distinctIdFromPersistence } from "../../client/src/lib/posthog";

const posthogLib = readFileSync("client/src/lib/posthog.ts", "utf8");
const app = readFileSync("client/src/App.tsx", "utf8");
const funnel = readFileSync("client/src/lib/funnel.ts", "utf8");
const indexHtml = readFileSync("client/index.html", "utf8");

test("the SDK does not also capture pageviews itself", () => {
  // App.tsx fires trackPageView() on every route change including first render.
  // With capture_pageview left on, every load emitted two.
  assert.match(posthogLib, /capture_pageview:\s*false/);
  assert.doesNotMatch(posthogLib, /capture_pageview:\s*true/);
});

test("exactly one thing sends a pageview", () => {
  const manual = (app.match(/trackPageView\(/g) || []).length;
  // One import reference plus one call site.
  assert.ok(manual >= 1, "App.tsx must still send pageviews itself");
  assert.match(app, /useEffect\(\(\) => \{\s*trackPageView\(location\);/);
});

test("posthog-js is dynamic-imported from the public API module only", () => {
  assert.doesNotMatch(
    posthogLib,
    /^import\s+posthog\s+from\s+['"]posthog-js['"]/m,
    "static import puts ~240KB in the entry bundle",
  );
  assert.doesNotMatch(posthogLib, /^import\s+['"]posthog-js['"]/m);
  assert.match(posthogLib, /import\(\s*["']posthog-js["']\s*\)/);
  assert.doesNotMatch(app, /posthog-js/);
  assert.doesNotMatch(funnel, /posthog-js/);
});

test("init options stay XHR, manual pageview, pageleave, exceptions, localStorage", () => {
  assert.match(posthogLib, /api_transport:\s*["']XHR["']/);
  assert.match(posthogLib, /capture_pageview:\s*false/);
  assert.doesNotMatch(posthogLib, /capture_pageview:\s*true/);
  assert.match(posthogLib, /capture_pageleave:\s*true/);
  assert.match(posthogLib, /capture_exceptions:\s*true/);
  assert.match(posthogLib, /persistence:\s*["']localStorage["']/);
  assert.match(posthogLib, /maskAllInputs:\s*true/);
});

test("captures before init are queued; idle load flushes on first capture", () => {
  assert.match(posthogLib, /requestIdleCallback/);
  assert.match(posthogLib, /pending\.push/);
  assert.match(posthogLib, /flushPostHogQueue/);
  assert.match(posthogLib, /ensureClient/);
  assert.match(posthogLib, /Flush-on-first-capture/);
});

test("queued identify / reset / capture flush in insertion order", () => {
  const seen: string[] = [];
  const fake = {
    identify: (id: string, traits?: Record<string, unknown>) => {
      seen.push(`identify:${id}:${String(traits?.email ?? "")}`);
    },
    reset: () => {
      seen.push("reset");
    },
    capture: (event: string, properties?: Record<string, unknown>) => {
      seen.push(`capture:${event}:${String(properties?.path ?? "")}`);
    },
  };
  const queue: QueuedPostHogCall[] = [
    { kind: "capture", event: "$pageview", properties: { path: "/" } },
    { kind: "capture", event: "cta_click", properties: { path: "" } },
    { kind: "capture", event: "signup_view", properties: { path: "" } },
    { kind: "identify", distinctId: "42", traits: { email: "a@b.c", role: "viewer" } },
    { kind: "reset" },
  ];
  flushPostHogQueue(fake, queue);
  assert.deepEqual(seen, [
    "capture:$pageview:/",
    "capture:cta_click:",
    "capture:signup_view:",
    "identify:42:a@b.c",
    "reset",
  ]);
  assert.equal(queue.length, 0, "flush must drain the queue");
});

test("index.html does not load a second PostHog snippet", () => {
  // The HTML comment documents the old array.js snippet; a real second SDK
  // would be a <script src="...array.js"> (or posthog.init in a script body).
  assert.doesNotMatch(indexHtml, /<script[^>]+array\.js/i);
  assert.doesNotMatch(indexHtml, /<script[^>]+posthog/i);
  assert.doesNotMatch(indexHtml, /cdn\.posthog/);
  assert.match(indexHtml, /initialized once, from client\/src\/lib\/posthog\.ts/);
});

test("reset fires on sign-out, never on an anonymous page load", () => {
  // posthog.reset() mints a new distinct_id AND a new session_id. Calling it
  // whenever `user` is falsy means calling it on the first render of every
  // marketing page, which splits one visitor into two identities.
  assert.match(app, /wasIdentified/, "needs a guard remembering prior identification");
  assert.match(
    app,
    /\}\s*else if \(wasIdentified\.current\) \{\s*resetUser\(\);/,
    "resetUser() must be behind the identified -> anonymous transition",
  );
  // The exact shape of the old bug must not come back.
  assert.doesNotMatch(
    app,
    /identifyUser\(user\.id, user\.email, user\.role\);\s*\} else \{\s*resetUser\(\);/,
    "unguarded resetUser() in the user effect is the original bug",
  );
});

test("the leads endpoint is reachable through the Express proxy", () => {
  // server/index.ts proxies /api/* to FastAPI with pathRewrite {"^/api": ""}.
  // A router prefix containing /api therefore never matches. This is why the
  // lead-capture endpoint had never served a request.
  const index = readFileSync("server/index.ts", "utf8");
  assert.match(index, /"\^\/api":\s*""/, "the rewrite this test reasons about must still exist");

  for (const f of ["leads", "events", "simulation_jobs", "slack_bot"]) {
    const src = readFileSync(`server/api/${f}.py`, "utf8");
    assert.doesNotMatch(
      src,
      /APIRouter\(prefix="\/api\//,
      `server/api/${f}.py: a prefix starting /api is unreachable behind the proxy rewrite`,
    );
  }
});

test("listing leads requires platform admin", () => {
  // POST is public by design; GET returns email addresses.
  const leads = readFileSync("server/api/leads.py", "utf8");
  const getBlock = leads.slice(leads.indexOf('@router.get("")'));
  assert.match(getBlock, /require_platform_admin/, "GET /leads must not be open");
});

test("signup_completed fires through trackFunnel and the server first-success path", () => {
  const funnel = readFileSync("client/src/lib/funnel.ts", "utf8");
  const auth = readFileSync("client/src/pages/auth.tsx", "utf8");
  const callback = readFileSync("client/src/pages/auth-callback.tsx", "utf8");
  const authApi = readFileSync("server/api/auth.py", "utf8");
  const oauth = readFileSync("server/api/oauth.py", "utf8");
  const activation = readFileSync("server/services/activation.py", "utf8");

  assert.match(funnel, /signup_completed/);
  assert.match(auth, /trackFunnel\(\s*['"]signup_completed['"]/);
  assert.match(callback, /trackFunnel\(\s*['"]signup_completed['"]/);
  assert.match(authApi, /emit_signup_completed\(\s*user_id=user\.id,\s*method="email"/);
  assert.match(authApi, /anonymous_distinct_id=req\.distinct_id/);
  assert.match(oauth, /emit_signup_completed\(\s*user_id=user\.id,\s*method="google"/);
  assert.match(oauth, /anonymous_distinct_id=anonymous_distinct_id/);
  assert.match(activation, /posthog_capture\(\s*"signup_completed"/);
  // Browser identifyUser uses String(userId). A user:{id} prefix is a second person.
  assert.match(activation, /user_distinct_id\(user_id\)/);
  assert.doesNotMatch(activation, /f"user:\{user_id\}"/);
  assert.match(posthogLib, /distinctId:\s*String\(userId\)/);
  assert.doesNotMatch(authApi, /emit_signup_completed.*login/i);
});

test("server events alias the pre-signup id onto the browser user id", () => {
  const activation = readFileSync("server/services/activation.py", "utf8");
  const posthog = readFileSync("server/services/posthog.py", "utf8");
  assert.match(activation, /posthog_alias\(/);
  assert.match(posthog, /\$create_alias/);
  assert.match(posthog, /"alias":\s*canonical/);
  // The event distinct_id is the id being merged; alias is the canonical user id.
  assert.match(posthog, /"distinct_id":\s*previous/);
});

test("founder_activated is gated on is_sample and wired on first real success", () => {
  const funnel = readFileSync("client/src/lib/funnel.ts", "utf8");
  const hooks = readFileSync("client/src/api/hooks.ts", "utf8");
  const truth = readFileSync("server/api/truth_scan.py", "utf8");
  const sims = readFileSync("server/api/simulations.py", "utf8");
  const sample = readFileSync("server/services/sample_data.py", "utf8");
  const activation = readFileSync("server/services/activation.py", "utf8");

  assert.match(funnel, /params\.is_sample !== false/);
  assert.match(funnel, /trackFunnel\(\s*['"]founder_activated['"]/);
  assert.match(hooks, /trackFounderActivated\(\{\s*source: 'truth_scan'/);
  assert.match(hooks, /trackFounderActivated\(\{\s*source: 'simulation'/);
  assert.match(hooks, /company\.is_sample === false/);
  assert.match(truth, /maybe_emit_founder_activated/);
  assert.match(truth, /source="truth_scan"/);
  assert.match(sims, /maybe_emit_founder_activated/);
  assert.match(sims, /source="simulation"/);
  assert.match(activation, /company_is_sample/);
  assert.match(activation, /metadata_json/);
  assert.match(activation, /"founder_activated"/);
  assert.doesNotMatch(sample, /founder_activated|emit_signup_completed|maybe_emit_founder/);
});

test("successful lead creates emit lead_captured on the server", () => {
  // The conversion fires once from POST /api/leads after the row is committed.
  // The browser sends lead_form_submitted instead, so the two are not the same event.
  const leads = readFileSync("server/api/leads.py", "utf8");
  const posthog = readFileSync("server/services/posthog.py", "utf8");
  assert.match(leads, /background\.add_task\(_emit_lead_captured,/);
  assert.match(leads, /posthog_capture\(\s*"lead_captured"/);
  assert.match(leads, /"browser"/);
  assert.match(leads, /"anonymous"/);
  assert.match(leads, /optin:/);
  // The address and a hash of it must not be the PostHog distinct_id.
  assert.doesNotMatch(leads, /"email_hash"/);
  assert.doesNotMatch(leads, /return _lead_distinct_id\(/);
  assert.match(posthog, /\/capture\//);
  assert.match(posthog, /refusing/);
  assert.doesNotMatch(posthog, /\.identify\(/);
  assert.doesNotMatch(leads, /posthog.*identify/i);
});

test("lead forms and signup pass the browser distinct_id when they have one", () => {
  const runway = readFileSync("client/src/pages/runway-calculator.tsx", "utf8");
  const survival = readFileSync("client/src/pages/survival-simulator.tsx", "utf8");
  const optIn = readFileSync("client/src/components/marketing/CalculatorEmailOptIn.tsx", "utf8");
  const auth = readFileSync("client/src/pages/auth.tsx", "utf8");
  const api = readFileSync("client/src/api/client.ts", "utf8");
  // Both calculators post through the shared opt-in, which attaches the id.
  for (const page of [runway, survival]) {
    assert.match(page, /CalculatorEmailOptIn/);
  }
  assert.match(optIn, /getBrowserDistinctId\(/);
  assert.match(optIn, /distinct_id:\s*distinctId/);
  assert.match(auth, /getBrowserDistinctId\(/);
  assert.match(auth, /api\.auth\.register\([^)]*distinctId/);
  assert.match(auth, /params\.set\(\s*['"]distinct_id['"]/);
  assert.match(auth, /\/api\/auth\/\$\{provider\}\/start/);
  assert.match(api, /distinct_id:\s*distinctId/);
});

test("persistence distinct_id is read only when it is a real id", () => {
  assert.equal(
    distinctIdFromPersistence(JSON.stringify({ distinct_id: "anon-browser" })),
    "anon-browser",
  );
  assert.equal(distinctIdFromPersistence(JSON.stringify({ distinct_id: "  anon-browser  " })), "anon-browser");
  assert.equal(distinctIdFromPersistence(JSON.stringify({ distinct_id: "founder@example.com" })), null);
  assert.equal(distinctIdFromPersistence(JSON.stringify({ distinct_id: "" })), null);
  assert.equal(distinctIdFromPersistence(JSON.stringify({ distinct_id: "x".repeat(201) })), null);
  assert.equal(distinctIdFromPersistence("not-json"), null);
  assert.equal(distinctIdFromPersistence(null), null);
});

test("the survival simulator sends the same lead fields the email is keyed off", () => {
  // Mirror of the calculator contract: /survival-simulator promises an inbox
  // summary, and /api/leads only queues the send when runway_months AND
  // runway_date are present. Source must be survival-simulator so these leads
  // stay distinguishable from calculator ones.
  const page = readFileSync("client/src/pages/survival-simulator.tsx", "utf8");
  const optIn = readFileSync("client/src/components/marketing/CalculatorEmailOptIn.tsx", "utf8");
  const api = readFileSync("server/api/leads.py", "utf8");
  assert.match(page, /source="survival-simulator"/);
  assert.match(page, /plan="survival-simulator"/);
  assert.match(page, /runwayMonths=/);
  assert.match(page, /runwayDate=/);
  assert.match(page, /monthlyBurn=/);
  assert.match(optIn, /trackFunnel\(\s*"lead_form_submitted"/);
  assert.doesNotMatch(optIn, /lead_captured/);
  for (const field of ["runway_months", "runway_date", "monthly_burn"]) {
    assert.match(optIn, new RegExp(`${field}:`), `opt-in must send ${field}`);
    assert.match(api, new RegExp(field), `server must accept ${field}`);
  }
  assert.match(optIn, /data-testid="input-lead-email"/);
  assert.match(optIn, /data-testid="button-email-result"/);
  const resultsIdx = page.indexOf("{results && (");
  const emailIdx = page.indexOf("<EmailResultPanel results={results} />");
  assert.ok(resultsIdx !== -1 && emailIdx > resultsIdx, "email capture must render inside the results block");
});

test("the calculator sends the fields the runway email is keyed off", () => {
  // server/api/leads.py only queues the email when runway_months AND
  // runway_date are present. The UI promises "check your inbox" the moment the
  // POST succeeds, so if the client stops sending these the page starts lying.
  const page = readFileSync("client/src/pages/runway-calculator.tsx", "utf8");
  const optIn = readFileSync("client/src/components/marketing/CalculatorEmailOptIn.tsx", "utf8");
  const api = readFileSync("server/api/leads.py", "utf8");
  assert.match(page, /runwayMonths=/);
  assert.match(page, /runwayDate=/);
  assert.match(page, /monthlyBurn=/);
  for (const field of ["runway_months", "runway_date", "monthly_burn"]) {
    assert.match(optIn, new RegExp(`${field}:`), `opt-in must send ${field}`);
    assert.match(api, new RegExp(field), `server must accept ${field}`);
  }
  assert.match(api, /if data\.runway_months and data\.runway_date:/);
});

test("the calculator's number fields can actually be cleared", () => {
  // type="number" with onChange={e => setX(Number(e.target.value))} means
  // Number("") === 0, so deleting the last digit snaps the field back to "0"
  // and it can never be emptied.
  const page = readFileSync("client/src/pages/runway-calculator.tsx", "utf8");
  assert.doesNotMatch(page, /onChange=\{\(e\) => set\w+\(Number\(e\.target\.value\)\)\}/);
  assert.match(page, /function toNumber\(text: string\): number/);
});
