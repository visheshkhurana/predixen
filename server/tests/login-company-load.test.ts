// A failed companies.list() after login must not look like "no company".
// Forgot-password must not show "check your email" when the request failed.
//
// Run: npx tsx --test server/tests/login-company-load.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  forgotPasswordAccepted,
  forgotPasswordFailureCopy,
  postLoginDestination,
} from "../../client/src/lib/authFlow.ts";

const auth = readFileSync("client/src/pages/auth.tsx", "utf8");

test("onboarding only after a successful empty company list", () => {
  assert.equal(postLoginDestination(false, { status: "error" }), "retry");
  assert.equal(postLoginDestination(true, { status: "error" }), "retry");
  assert.equal(postLoginDestination(false, { status: "ok", companies: [] }), "/onboarding");
  assert.equal(postLoginDestination(true, { status: "ok", companies: [] }), "/");
  assert.equal(
    postLoginDestination(false, { status: "ok", companies: [{ id: 1 }] }),
    "/",
  );
  assert.equal(
    postLoginDestination(true, { status: "ok", companies: [{ id: 1 }] }),
    "/",
  );
});

test("forgot-password is sent only on a 2xx", () => {
  assert.equal(forgotPasswordAccepted(true), true);
  assert.equal(forgotPasswordAccepted(false), false);
  assert.match(forgotPasswordFailureCopy(null).description, /connection/i);
  assert.match(forgotPasswordFailureCopy(429).description, /too many/i);
  assert.match(forgotPasswordFailureCopy(500).description, /try again/i);
  assert.equal(forgotPasswordFailureCopy(502).title, "Couldn't send reset email");
});

test("the login page uses that decision and does not swallow the list error", () => {
  const login = auth.slice(auth.indexOf("const handleLogin"), auth.indexOf("const handleRegister"));
  assert.match(login, /continueAfterLogin/);
  assert.doesNotMatch(login, /setLocation\(['"]\/onboarding['"]\)/);
  assert.match(auth, /postLoginDestination/);
  assert.match(auth, /data-testid="button-retry-companies"/);
  assert.match(auth, /data-testid="login-companies-error"/);
});

test("forgot-password stays on the form when the response is not ok", () => {
  const forgot = auth.slice(
    auth.indexOf("const handleForgotPassword"),
    auth.indexOf("const continueAfterLogin"),
  );
  assert.match(forgot, /forgotPasswordAccepted\(res\.ok\)/);
  assert.match(auth, /data-testid="text-forgot-error"/);
  assert.doesNotMatch(forgot, /catch\s*\{[^}]*setForgotPasswordSent\(true\)/);
  const sentAssignments = forgot.match(/setForgotPasswordSent\(true\)/g) ?? [];
  assert.equal(sentAssignments.length, 1);
});
