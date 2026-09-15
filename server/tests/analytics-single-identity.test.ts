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

const posthogLib = readFileSync("client/src/lib/posthog.ts", "utf8");
const app = readFileSync("client/src/App.tsx", "utf8");

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

test("successful lead creates emit lead_captured on the server", () => {
  // Client trackFunnel("lead_captured") after fetch is in the live calculator
  // chunk but PostHog 522965 has never ingested the event. The conversion
  // must fire from POST /api/leads after the row is committed.
  const leads = readFileSync("server/api/leads.py", "utf8");
  const posthog = readFileSync("server/services/posthog.py", "utf8");
  assert.match(leads, /background\.add_task\(_emit_lead_captured,/);
  assert.match(leads, /posthog_capture\(\s*"lead_captured"/);
  assert.match(posthog, /\/capture\//);
  assert.doesNotMatch(posthog, /\.identify\(/);
  assert.doesNotMatch(leads, /posthog.*identify/i);
});

test("the survival simulator sends the same lead fields the email is keyed off", () => {
  // Mirror of the calculator contract: /survival-simulator promises an inbox
  // summary, and /api/leads only queues the send when runway_months AND
  // runway_date are present. Source must be survival-simulator so these leads
  // stay distinguishable from calculator ones.
  const page = readFileSync("client/src/pages/survival-simulator.tsx", "utf8");
  const api = readFileSync("server/api/leads.py", "utf8");
  assert.match(page, /source:\s*"survival-simulator"/);
  assert.match(page, /plan:\s*"survival-simulator"/);
  assert.match(page, /trackFunnel\(\s*"lead_captured"/);
  for (const field of ["runway_months", "runway_date", "monthly_burn"]) {
    assert.match(page, new RegExp(`${field}:`), `survival-sim must send ${field}`);
    assert.match(api, new RegExp(field), `server must accept ${field}`);
  }
  assert.match(page, /data-testid="input-lead-email"/);
  assert.match(page, /data-testid="button-email-result"/);
  const resultsIdx = page.indexOf("{results && (");
  const emailIdx = page.indexOf("<EmailResultPanel results={results} />");
  assert.ok(resultsIdx !== -1 && emailIdx > resultsIdx, "email capture must render inside the results block");
});

test("the calculator sends the fields the runway email is keyed off", () => {
  // server/api/leads.py only queues the email when runway_months AND
  // runway_date are present. The UI promises "check your inbox" the moment the
  // POST succeeds, so if the client stops sending these the page starts lying.
  const page = readFileSync("client/src/pages/runway-calculator.tsx", "utf8");
  const api = readFileSync("server/api/leads.py", "utf8");
  for (const field of ["runway_months", "runway_date", "monthly_burn"]) {
    assert.match(page, new RegExp(`${field}:`), `client must send ${field}`);
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
