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

console.log("PASS  auth-critical-routes source checks");
