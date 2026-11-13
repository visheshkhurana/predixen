// GET 401s on /onboarding and /overview must not hard-redirect to /auth.
// That was the silent logout: PostHog (project 522965, founderconsole.ai,
// last 90d) shows /overview → /auth?expired=1 in ~300ms (18 pageviews / 5
// persons on ?expired=1). Mutations still redirect after refresh fails.
//
// Run: npx tsx --test server/tests/session-401-redirect.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  isMutationMethod,
  shouldHardRedirectOn401,
} from "../../client/src/lib/authSession.ts";

const queryClient = readFileSync("client/src/lib/queryClient.ts", "utf8");
const apiClient = readFileSync("client/src/api/client.ts", "utf8");
const onboarding = readFileSync("client/src/pages/onboarding.tsx", "utf8");
const app = readFileSync("client/src/App.tsx", "utf8");

test("GET 401 never hard-redirects, including on /onboarding and /overview", () => {
  assert.equal(shouldHardRedirectOn401("GET", "/onboarding"), false);
  assert.equal(shouldHardRedirectOn401("GET", "/overview"), false);
  assert.equal(shouldHardRedirectOn401("GET", "/dashboard"), false);
  assert.equal(shouldHardRedirectOn401(undefined, "/overview"), false);
});

test("mutation 401 after a failed refresh still sends the user to sign-in", () => {
  assert.equal(isMutationMethod("POST"), true);
  assert.equal(shouldHardRedirectOn401("POST", "/overview"), true);
  assert.equal(shouldHardRedirectOn401("PUT", "/onboarding"), true);
  assert.equal(shouldHardRedirectOn401("DELETE", "/dashboard"), true);
});

test("auth-screen 401s are not a session-expired loop", () => {
  assert.equal(shouldHardRedirectOn401("POST", "/auth"), false);
  assert.equal(shouldHardRedirectOn401("POST", "/auth/callback"), false);
});

test("both API clients share the mutation-only redirect policy", () => {
  assert.match(queryClient, /shouldHardRedirectOn401/);
  assert.match(apiClient, /shouldHardRedirectOn401/);
  assert.match(queryClient, /attemptTokenRefresh/);
  assert.match(apiClient, /attemptTokenRefresh/);
  // The old GET-unconditional redirect must not come back.
  assert.doesNotMatch(
    queryClient,
    /if \(res\.status === 401\) \{\s*handleSessionExpired\(res\.url\);/,
  );
  assert.doesNotMatch(
    apiClient,
    /window\.location\.href = '\/auth'/,
  );
});

test("first-insight GETs still go through the shared query client", () => {
  // Onboarding's existing-company probe uses the default queryFn (GET /api/companies).
  assert.match(onboarding, /queryKey:\s*\['\/api\/companies'\]/);
  // AppLayout loads smart-alerts as soon as a sample company exists — still on
  // /onboarding, then on /overview. That GET used to fire handleSessionExpired.
  assert.match(app, /queryKey:\s*\["\/api\/companies", currentCompany\?\.id, "smart-alerts"\]/);
});
