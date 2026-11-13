// "Get started free" / "Sign up" CTAs must land on the register form, never on
// the login form. Two ways that has gone wrong here:
//
//   1. the original bug — the CTA pointed at bare /auth, which opens
//      "Welcome back — Sign in", so a new founder met a login form and
//      signup_start never fired (this is the assertion the file was written for);
//   2. HAG-449 — every register CTA pointed at /auth?tab=register, the
//      un-prerendered SPA shell (8.4 s to first paint at 400 kbps/4x CPU) while
//      the prerendered /signup page (2.8 s) had no inbound links at all.
//
// The rule now: the CTA points at /signup, which renders AuthPage in register
// mode. /auth?tab=register is still supported for old links, but it is no
// longer what the site's own CTAs use.
//
// Run: npx tsx server/tests/signup-cta-register-tab.test.ts
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// Run from the repo root, like the other source-reading tests.
const read = (p: string) => readFileSync(p, "utf8");

const SIGNUP_CTA_FILES = [
  "client/src/components/ScenarioCompare.tsx",
  "client/src/components/marketing/MarketingLayout.tsx",
  "client/src/pages/alternatives.tsx",
  "client/src/pages/blog.tsx",
  "client/src/pages/compare.tsx",
  "client/src/pages/customers.tsx",
  "client/src/pages/demo-redirect.tsx",
  "client/src/pages/how-it-works.tsx",
  "client/src/pages/marketing-features.tsx",
  "client/src/pages/landing.tsx",
  "client/src/pages/pricing.tsx",
  "client/src/pages/product.tsx",
  "client/src/pages/tools-index.tsx",
  "client/src/pages/use-cases.tsx",
  // HAG-455: the prerendered body is what a crawler and a no-JS visitor get —
  // createRoot() replaces it only once JS runs. A bare /auth here is the
  // original bug for the audience that cannot click twice.
  "server/seo-prerender.ts",
];

for (const file of SIGNUP_CTA_FILES) {
  const src = read(file);
  assert.ok(src.includes('"/signup"'), `${file}: signup CTA must use /signup`);
  // A "get started" / "sign up" label must never sit on a link to the login page.
  const bare = /(?:href="\/auth"|navigate\("\/auth"\))[\s\S]{0,300}?(get started|sign up)/i.exec(src);
  assert.equal(bare, null, `${file}: signup label on bare /auth link`);
  // Nor on the slow shell. `href="/auth?tab=register"` may survive in a comment
  // explaining history, but not as a live link.
  assert.ok(
    !/href="\/auth\?tab=register"|navigate\("\/auth\?tab=register"\)/.test(src),
    `${file}: signup CTA still points at the un-prerendered /auth shell`,
  );
}

const auth = read("client/src/pages/auth.tsx");
for (const alias of ["'register'", "'signup'", "params.get('mode') === 'signup'"]) {
  assert.ok(auth.includes(alias), `auth.tsx must open the register tab for ${alias}`);
}

// /signup renders the real form on the register tab; without this it would be a
// fast page that opens on "Welcome back", which is the bug it exists to avoid.
const signup = read("client/src/pages/signup.tsx");
assert.ok(signup.includes('initialTab="register"'), "/signup must open on the register tab");

console.log(`signup-cta-register-tab: ${SIGNUP_CTA_FILES.length} files OK`);
