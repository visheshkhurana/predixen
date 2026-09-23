// "Get started free" / "Sign up" CTAs must open /auth on the Create Account tab.
// Bare /auth opens "Welcome back — Sign in", so a new founder clicking a signup
// CTA met a login form and signup_start never fired.
//
// Run: npx tsx server/tests/signup-cta-register-tab.test.ts
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// Run from the repo root, like the other source-reading tests.
const read = (p: string) => readFileSync(p, "utf8");

const SIGNUP_CTA_FILES = [
  "client/src/components/ScenarioCompare.tsx",
  "client/src/pages/alternatives.tsx",
  "client/src/pages/blog.tsx",
  "client/src/pages/compare.tsx",
  "client/src/pages/customers.tsx",
  "client/src/pages/demo-redirect.tsx",
  "client/src/pages/how-it-works.tsx",
  "client/src/pages/marketing-features.tsx",
  "client/src/pages/pricing.tsx",
  "client/src/pages/product.tsx",
  "client/src/pages/use-cases.tsx",
];

for (const file of SIGNUP_CTA_FILES) {
  const src = read(file);
  assert.ok(src.includes("/auth?tab=register"), `${file}: signup CTA must use /auth?tab=register`);
  // A "get started" / "sign up" label must never sit on a bare /auth link.
  const bare = /(?:href="\/auth"|navigate\("\/auth"\))[\s\S]{0,300}?(get started|sign up)/i.exec(src);
  assert.equal(bare, null, `${file}: signup label on bare /auth link`);
}

const auth = read("client/src/pages/auth.tsx");
for (const alias of ["'register'", "'signup'", "params.get('mode') === 'signup'"]) {
  assert.ok(auth.includes(alias), `auth.tsx must open the register tab for ${alias}`);
}

console.log(`signup-cta-register-tab: ${SIGNUP_CTA_FILES.length} files OK`);
