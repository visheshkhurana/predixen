// Razorpay website verification: the public legal surfaces a reviewer checks.
//
//   - /refund-policy is a real prerendered page (200, its own title, the prices,
//     the cancellation and refund terms, the legal entity), and its aliases
//     /cancellation-policy and /refunds land on it;
//   - /terms, /privacy and /contact name ULTRASAFE AI INDIA PRIVATE LIMITED, and
//     /privacy and /contact carry a Grievance Officer section;
//   - /pricing shows the paid Starter plan ONLY when Razorpay billing is live
//     (BILLING_PROVIDER=razorpay + all three secrets), and keeps the pinned
//     <title>Pricing | FounderConsole</title> (scripts/launch_gate.sh, HAG-471);
//   - no "TODO" placeholder from client/src/data/legal.ts ever reaches HTML.
//
// pr-checks.yml lists TS tests by hand and is hold-listed, so the CI half of
// this guard is server/tests/test_razorpay_site_verification.py.
//
// Run: npx tsx --test server/tests/legal-pages-ssr.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import { readFileSync } from "fs";
import type { Server } from "http";
import { injectSEO, renderHtmlPage } from "../seo-prerender";
import { legacyRedirects } from "../middleware/legacyRedirects";
import { isKnownAppRoute } from "../known-routes";
import { razorpayBillingEnabled } from "../billing-gate";
import { STARTER_PRICES } from "../../client/src/data/public-pricing";
import {
  LEGAL_ENTITY_ADDRESS,
  GRIEVANCE_OFFICER_NAME,
  GRIEVANCE_OFFICER_EMAIL,
  FIRST_PAYMENT_REFUND_WINDOW_DAYS,
  legalValue,
} from "../../client/src/data/legal";

const SHELL = readFileSync("client/index.html", "utf8");
const ENTITY = "ULTRASAFE AI INDIA PRIVATE LIMITED";
const BILLING_ENV = ["BILLING_PROVIDER", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET"];

function ssrBody(html: string): string {
  const m = html.match(/<div id="ssr-content"[^>]*>([\s\S]*)<\/div>\s*<\/div>/);
  return m ? m[1] : "";
}
function textOf(html: string): string {
  return ssrBody(html).replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/\s+/g, " ").trim();
}
function titleOf(html: string): string {
  return (html.match(/<title>([^<]*)<\/title>/) || [, ""])[1] as string;
}

function withBillingEnv<T>(values: Record<string, string> | null, fn: () => T): T {
  const saved: Record<string, string | undefined> = {};
  for (const k of BILLING_ENV) {
    saved[k] = process.env[k];
    delete process.env[k];
  }
  if (values) Object.assign(process.env, values);
  try {
    return fn();
  } finally {
    for (const k of BILLING_ENV) {
      if (saved[k] === undefined) delete process.env[k];
      else process.env[k] = saved[k];
    }
  }
}
const LIVE = {
  BILLING_PROVIDER: "razorpay",
  RAZORPAY_KEY_ID: "rzp_test_x",
  RAZORPAY_KEY_SECRET: "s",
  RAZORPAY_WEBHOOK_SECRET: "w",
};

test("/refund-policy is a prerendered 200 page with the policy terms", () => {
  assert.ok(isKnownAppRoute("/refund-policy"));
  const { status, html } = renderHtmlPage(SHELL, "/refund-policy");
  assert.equal(status, 200);
  assert.equal(titleOf(html), "Refund &amp; Cancellation Policy | FounderConsole");
  assert.match(html, /rel="canonical" href="https:\/\/founderconsole\.ai\/refund-policy"/);
  const body = ssrBody(html);
  const text = textOf(html);
  assert.match(body, /<h1>Refund &amp; Cancellation Policy<\/h1>/);
  for (const price of ["₹3,000", "$39", "AED 149", "₹30,000", "$390", "AED 1,490"]) {
    assert.ok(text.includes(price), `missing price ${price}`);
  }
  assert.ok(text.includes(ENTITY));
  assert.match(text, /cancel anytime from Billing/i);
  assert.match(text, /end of the current billing period/);
  assert.match(text, /no further charges/i);
  assert.match(text, /No partial-period refunds/);
  assert.ok(text.includes(`within ${FIRST_PAYMENT_REFUND_WINDOW_DAYS} days of the first payment`));
  assert.match(text, /Duplicate or erroneous charges/);
  assert.match(text, /original payment method/);
  assert.match(text, /5–7 business days/);
  assert.match(text, /Razorpay/);
  assert.ok(body.includes('href="mailto:hello@founderconsole.ai"'));
  for (const href of ["/terms", "/privacy", "/contact", "/pricing"]) {
    assert.ok(body.includes(`href="${href}"`), `missing href ${href}`);
  }
});

test("/cancellation-policy and /refunds 301 to /refund-policy", async () => {
  const app = express();
  app.use(legacyRedirects());
  app.use("*", (_req, res) => res.status(200).send("PAGE"));
  const server: Server = await new Promise((resolve) => {
    const s = app.listen(0, () => resolve(s));
  });
  try {
    const base = `http://127.0.0.1:${(server.address() as any).port}`;
    for (const p of ["/cancellation-policy", "/refunds"]) {
      const r = await fetch(base + p, { redirect: "manual" });
      assert.equal(r.status, 301, p);
      assert.equal(r.headers.get("location"), "/refund-policy", p);
    }
  } finally {
    server.close();
  }
});

test("terms, privacy, contact name the legal entity; privacy and contact name a grievance officer", () => {
  for (const path of ["/terms", "/privacy", "/contact", "/refund-policy"]) {
    const text = textOf(injectSEO(SHELL, path));
    assert.ok(text.includes(`FounderConsole is a product of ${ENTITY}`), `${path}: entity line missing`);
  }
  for (const path of ["/privacy", "/contact"]) {
    const text = textOf(injectSEO(SHELL, path));
    assert.match(text, /Grievance Officer/, path);
    assert.match(text, /Information Technology Act, 2000/, path);
  }
  const terms = textOf(injectSEO(SHELL, "/terms"));
  assert.match(terms, /processed securely by Razorpay/);
  assert.doesNotMatch(terms, /processed securely by Stripe/);
});

test("/pricing: paid Starter plan only when Razorpay billing is live; title pinned", () => {
  const off = withBillingEnv(null, () => injectSEO(SHELL, "/pricing"));
  const partial = withBillingEnv({ BILLING_PROVIDER: "razorpay", RAZORPAY_KEY_ID: "k" }, () => injectSEO(SHELL, "/pricing"));
  const stripe = withBillingEnv({ ...LIVE, BILLING_PROVIDER: "stripe" }, () => injectSEO(SHELL, "/pricing"));
  const on = withBillingEnv(LIVE, () => injectSEO(SHELL, "/pricing"));

  for (const html of [off, partial, stripe, on]) {
    assert.ok(html.includes("<title>Pricing | FounderConsole</title>"), "HAG-471 title changed");
    assert.ok(textOf(html).includes("What is included"), "launch gate body marker missing");
  }
  for (const html of [off, partial, stripe]) {
    const text = textOf(html);
    assert.match(text, /free during the public beta/);
    // Billing off: Starter appears only as the price once paid plans start,
    // never as a plan on sale.
    assert.ok(!text.includes("Starter — "), "paid plan listed with billing off");
    assert.match(text, /When they start, Starter will be ₹3,000\/month/);
  }
  const text = textOf(on);
  assert.ok(text.includes(`Starter — ${STARTER_PRICES.INR.monthlyLabel}/month`));
  for (const price of ["₹3,000", "₹30,000", "$39", "AED 149", "2 months free"]) {
    assert.ok(text.includes(price), `missing ${price}`);
  }
  assert.match(text, /Free — ₹0/);
  assert.doesNotMatch(text, /free during the public beta/);
  assert.ok(ssrBody(on).includes('href="/refund-policy"'));
  assert.ok(!text.includes("$29"));
});

test("billing gate matches razorpay_enabled(): provider + all three secrets", () => {
  assert.equal(razorpayBillingEnabled({}), false);
  assert.equal(razorpayBillingEnabled({ ...LIVE }), true);
  assert.equal(razorpayBillingEnabled({ ...LIVE, BILLING_PROVIDER: " RazorPay " }), true);
  for (const k of BILLING_ENV) {
    assert.equal(razorpayBillingEnabled({ ...LIVE, [k]: "  " }), false, k);
  }
});

test("no TODO placeholder ever renders", () => {
  // The committed constants ARE placeholders today; the renderers must drop them.
  assert.equal(legalValue("TODO: registered office address"), null);
  assert.equal(legalValue("  todo later "), null);
  assert.equal(legalValue(""), null);
  assert.equal(legalValue("12 MG Road, Bengaluru"), "12 MG Road, Bengaluru");

  const placeholders = [LEGAL_ENTITY_ADDRESS, GRIEVANCE_OFFICER_NAME, GRIEVANCE_OFFICER_EMAIL]
    .filter((v) => legalValue(v) === null);
  for (const env of [null, LIVE]) {
    for (const path of ["/refund-policy", "/terms", "/privacy", "/contact", "/pricing"]) {
      const html = withBillingEnv(env, () => injectSEO(SHELL, path));
      assert.ok(!/TODO/i.test(ssrBody(html)), `${path}: TODO in body`);
      for (const v of placeholders) {
        assert.ok(!html.includes(v), `${path}: placeholder ${v} rendered`);
      }
    }
  }
});


test("/faq pricing answers: real Starter price, beta wording when billing is off", () => {
  const off = textOf(withBillingEnv(null, () => injectSEO(SHELL, "/faq")));
  const on = textOf(withBillingEnv(LIVE, () => injectSEO(SHELL, "/faq")));
  for (const text of [off, on]) {
    for (const old of ["$29", "$49", "$99"]) assert.ok(!text.includes(old), `old planned price ${old}`);
    for (const price of ["₹3,000", "$39", "AED 149", "₹30,000", "2 months free"]) {
      assert.ok(text.includes(price), `missing ${price}`);
    }
  }
  assert.match(off, /free during the public beta/);
  assert.match(off, /What will the paid plans cost later\?/);
  assert.match(on, /What do the paid plans cost\?/);
  assert.doesNotMatch(on, /free during the public beta/);
  const offBeta = textOf(withBillingEnv(null, () => injectSEO(SHELL, "/pricing")));
  assert.ok(offBeta.includes("₹3,000") && !offBeta.includes("$29"), "beta /pricing shows the real Starter price");
});

test("landing prerender: beta FAQ unchanged when billing is off, real Starter price when live", () => {
  const off = textOf(withBillingEnv(null, () => injectSEO(SHELL, "/")));
  const on = textOf(withBillingEnv(LIVE, () => injectSEO(SHELL, "/")));
  for (const text of [off, on]) {
    for (const old of ["$29", "$49", "$99"]) assert.ok(!text.includes(old), old);
  }
  assert.match(off, /All features are free during the public beta/);
  assert.ok(on.includes("₹3,000"));
  assert.doesNotMatch(on, /All features are free during the public beta/);
});
