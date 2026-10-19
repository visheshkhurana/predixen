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
  assert.match(authApi, /emit_signup_completed\(user_id=user\.id, method="email"\)/);
  assert.match(oauth, /emit_signup_completed\(user_id=user\.id, method="google"\)/);
  assert.match(activation, /posthog_capture\(\s*"signup_completed"/);
  assert.doesNotMatch(authApi, /emit_signup_completed.*login/i);
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

/* ------------------------------------------------------------------ HAG-161 */

test("auth.tsx identifies PostHog, not only GA4, and does it before the conversion", () => {
  // The defect: auth.tsx defined its own `identifyUser` that called gtag and nothing
  // else, shadowing the PostHog one. PostHog was therefore identified only when
  // App.tsx's effect reacted to the store — after trackSignup had already fired — so
  // signup_completed landed on the anonymous device distinct id while every later event
  // from that person carried the user id. One person, three ids.
  const auth = readFileSync("client/src/pages/auth.tsx", "utf8");
  assert.match(auth, /import \{ identifyUser \} from '@\/lib\/posthog';/);
  assert.match(auth, /const identifyEverywhere = /);
  assert.match(auth, /identifyUser\(userId, email, role\);/);
  assert.doesNotMatch(
    auth,
    /const identifyUser = \(/,
    "auth.tsx must not define its own identifyUser — that is the shadow that skipped PostHog",
  );

  // Ordering is the whole point: identify before the conversion it must be attributed to.
  const registerIdx = auth.indexOf("const handleRegister");
  const identifyIdx = auth.indexOf("identifyEverywhere(result.user_id", registerIdx);
  const signupIdx = auth.indexOf("trackSignup(result.user_id", registerIdx);
  assert.ok(identifyIdx !== -1, "register must identify");
  assert.ok(signupIdx !== -1, "register must still fire the signup conversion");
  assert.ok(
    identifyIdx < signupIdx,
    "identify must come before signup_completed, or the conversion lands on the device id",
  );
});

test("signup_view fires once per page load, not once per tab toggle", () => {
  // It fired on every transition INTO the register tab, so a visitor who toggled
  // Login / Register / Login / Register produced two signup_view events from one visit.
  const auth = readFileSync("client/src/pages/auth.tsx", "utf8");
  const fx = auth.slice(auth.indexOf("Funnel: fire signup_view once"));
  const body = fx.slice(0, fx.indexOf("}, [activeTab]);"));
  assert.match(body, /const signupViewed = useRef\(false\)/, "needs a once-guard ref");
  assert.match(body, /!signupViewed\.current/, "the guard must gate the capture");
  assert.match(body, /signupViewed\.current = true;/);
});

test("purchase_subscription carries a value and a currency", () => {
  // Without both, GA4 will not treat the event as a revenue key event and no ad platform
  // can price the conversion — so the only conversion this product is paid for arrived
  // with no number attached.
  const billing = readFileSync("client/src/pages/billing.tsx", "utf8");
  assert.match(billing, /buildPurchaseProperties\(input\)/);
  assert.match(billing, /isPurchaseResolvable\(input, settled\)/);
  assert.match(billing, /trackEvent\('purchase_subscription', properties\)/);
  assert.match(billing, /gtag\?\.\('event', 'purchase_subscription', properties\)/);
  assert.doesNotMatch(
    billing,
    /'purchase_subscription', \{ method: 'stripe_checkout' \}/,
    "a valueless purchase event is the defect this card exists to fix",
  );
});

test("the purchase property bag has a real value in every branch", async () => {
  // The pure-function half, so the case that actually happens — the redirect lands
  // before the subscription query has answered — is tested rather than assumed.
  const { buildPurchaseProperties, isPurchaseResolvable } = await import(
    "../../client/src/lib/purchase-properties"
  );

  const fromSubscription = buildPurchaseProperties({
    planId: "growth",
    checkoutId: "abc-123",
    subscriptionPrice: 99,
    cataloguePrice: 49,
  });
  assert.equal(fromSubscription.value, 99, "the server's number wins over the catalogue");
  assert.equal(fromSubscription.value_source, "subscription");
  assert.equal(fromSubscription.currency, "USD");
  assert.equal(fromSubscription.plan, "growth");
  assert.equal(fromSubscription.transaction_id, "abc-123");

  const fromCatalogue = buildPurchaseProperties({ planId: "starter", cataloguePrice: 29 });
  assert.equal(fromCatalogue.value, 29);
  assert.equal(fromCatalogue.value_source, "catalogue");

  // Nothing known yet: an explicit, labelled zero — never a missing `value`.
  const unknown = buildPurchaseProperties({});
  assert.equal(unknown.value, 0);
  assert.equal(unknown.value_source, "unavailable");
  assert.equal(unknown.plan, "unknown");
  assert.ok("value" in unknown && "currency" in unknown);

  // A free plan is a real zero, not a missing price.
  const free = buildPurchaseProperties({ planId: "free", subscriptionPrice: 0, cataloguePrice: 0 });
  assert.equal(free.value, 0);
  assert.equal(free.value_source, "subscription");

  // NaN and undefined are not prices.
  assert.equal(buildPurchaseProperties({ subscriptionPrice: Number.NaN }).value_source, "unavailable");
  assert.equal(isPurchaseResolvable({ subscriptionPrice: Number.NaN }, false), false);

  // The event waits for a price, and does not wait forever for one.
  assert.equal(isPurchaseResolvable({}, false), false, "must not fire before a price is known");
  assert.equal(isPurchaseResolvable({}, true), true, "must not hang when both queries settle empty");
  assert.equal(isPurchaseResolvable({ cataloguePrice: 49 }, false), true);
});

test("a checkout attempt is written down before the browser leaves for Stripe", () => {
  // The redirect leaves the page, so the plan has to survive it; and the correlation id
  // is what makes a reload of the success URL idempotent rather than a second purchase.
  const billing = readFileSync("client/src/pages/billing.tsx", "utf8");
  const handler = billing.slice(billing.indexOf("const handleSelectPlan"));
  const writeIdx = handler.indexOf("sessionStorage.setItem");
  const mutateIdx = handler.indexOf("subscribe.mutate(");
  assert.ok(writeIdx !== -1, "the pending checkout must be written");
  assert.ok(mutateIdx !== -1 && writeIdx < mutateIdx, "write it BEFORE the redirect is requested");
  assert.match(billing, /const purchaseFired = useRef\(false\)/);
  // The id reaches the event through the property bag, so assert the handoff on both
  // sides: billing passes it in, and the bag (not billing) builds `transaction_id`.
  assert.match(billing, /checkoutId: pending\?\.checkoutId/);
  const bag = readFileSync("client/src/lib/purchase-properties.ts", "utf8");
  assert.match(bag, /transaction_id: input\.checkoutId \?\? ''/);
});
