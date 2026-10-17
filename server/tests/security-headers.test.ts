// The gateway's CSP/HSTS policy. Production must not allow eval, any-host
// sockets, or leftover dev hosts; dev keeps what Vite's HMR needs.
//
// Run: npx tsx --test server/tests/security-headers.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { buildCsp, HSTS_VALUE } from "../middleware/securityHeaders";

const directive = (csp: string, name: string) =>
  (csp.split("; ").find((d) => d.startsWith(name + " ")) || "").split(" ").slice(1);

test("production CSP: no eval, no wildcard sockets, no replit hosts", () => {
  delete process.env.APP_BASE_URL;
  const csp = buildCsp({ isEmbed: false, dev: false });
  assert.ok(!directive(csp, "script-src").includes("'unsafe-eval'"));
  const connect = directive(csp, "connect-src");
  assert.ok(!connect.includes("ws:") && !connect.includes("wss:"), connect.join(" "));
  assert.ok(connect.includes("wss://founderconsole.ai"));
  assert.ok(!csp.includes("replit"));
});

test("socket origin follows APP_BASE_URL", () => {
  process.env.APP_BASE_URL = "https://staging.example.com";
  try {
    assert.ok(directive(buildCsp({ isEmbed: false, dev: false }), "connect-src").includes("wss://staging.example.com"));
  } finally {
    delete process.env.APP_BASE_URL;
  }
});

test("dev CSP keeps Vite HMR working", () => {
  const csp = buildCsp({ isEmbed: false, dev: true });
  assert.ok(directive(csp, "connect-src").includes("ws:"));
  assert.ok(directive(csp, "script-src").includes("'unsafe-eval'"));
});

test("embeds may be framed; app pages may not", () => {
  assert.ok(buildCsp({ isEmbed: true, dev: false }).includes("frame-ancestors *"));
  assert.ok(!buildCsp({ isEmbed: false, dev: false }).includes("frame-ancestors *"));
});

test("HSTS matches FastAPI (two years)", () => {
  assert.equal(HSTS_VALUE, "max-age=63072000; includeSubDomains; preload");
});
