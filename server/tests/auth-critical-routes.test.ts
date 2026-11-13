// Source assertions for the two critical auth holes from the ops audit.
import { readFileSync } from "fs";
import assert from "assert";

const events = readFileSync("server/api/events.py", "utf8");
const gov = readFileSync("server/ai-governance/routes.ts", "utf8");
const auth = readFileSync("server/middleware/requireAuth.ts", "utf8");

assert.match(events, /require_platform_admin/, "GET /api/events must require platform admin");
assert.match(events, /get_current_user/, "POST /api/events must require authenticated user");
assert.doesNotMatch(events, /user_id:\s*Optional/, "caller must not supply user_id on POST");

assert.match(gov, /requirePlatformAdmin|asyncPlatformAdmin/, "ai-governance admin routes must be gated");
assert.match(gov, /admin\.use\(asyncPlatformAdmin\)/, "admin router must mount platform-admin middleware");
assert.doesNotMatch(gov, /founderconsole-ai-governance-secret-change-me/, "no default HMAC secret");
assert.match(gov, /a\.length !== b\.length/, "timingSafeEqual must guard unequal lengths");
assert.doesNotMatch(gov, /REPLIT_DEV_DOMAIN|fund-flow--vysheshk\.replit\.app/, "no Replit callback fallback");
assert.match(gov, /Invalid or missing callback signature/, "unsigned callbacks must 401");

assert.match(auth, /export async function requirePlatformAdmin/, "requirePlatformAdmin exported");

const feedback = readFileSync("server/api/feedback.py", "utf8");
assert.match(feedback, /require_platform_admin/, "GET /api/feedback must require platform admin");

const forecasting = readFileSync("server/api/forecasting.py", "utf8");
assert.match(forecasting, /require_company_access/, "company forecasting must require company access");
assert.match(forecasting, /require_company_access_by_path/, "forecast+trend must use path access helper");

console.log("PASS  auth-critical-routes source checks");

// HAG-453: /demo is the front door. A failed or empty companies.list() used to be
// swallowed and logged, then the redirect ran anyway — the demo user was signed in
// with no company, /overview's AuthenticatedRoute bounced it to /onboarding, and the
// visitor met a signup wall with no error and no retry. The failure must reach the
// outer catch, and /overview must not be reachable without a selected company.
const demo = readFileSync("client/src/pages/demo-redirect.tsx", "utf8");

assert.doesNotMatch(
  demo,
  /catch\s*(?:\(\s*\w*\s*\))?\s*\{\s*console\.warn\(\s*['"]Failed to auto-select demo company/,
  "a failed companies.list() must not be swallowed and logged",
);
assert.match(
  demo,
  /if\s*\(\s*!companies\s*\|\|\s*companies\.length\s*===\s*0\s*\)\s*\{\s*throw/,
  "an empty companies.list() must throw, not fall through to the redirect",
);
assert.ok(
  demo.indexOf("setLocation('/overview')") > demo.indexOf("companies.length === 0"),
  "the /overview redirect must come after the company check",
);
assert.ok(
  demo.indexOf("setLocation('/overview')") > -1,
  "demo-redirect must still land on /overview in the happy path",
);
assert.match(demo, /data-testid="button-demo-retry"/, "the failure path must offer Try Again");
assert.match(
  demo,
  /href="\/signup"[\s\S]{0,200}data-testid="button-demo-signup"/,
  "the failure path must offer /signup as an escape",
);

console.log("PASS  demo-redirect error path checks");
