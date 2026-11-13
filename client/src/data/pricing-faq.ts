/**
 * The pricing answers on /faq, for both billing states. One copy, read by
 * client/src/pages/faq.tsx and server/seo-prerender.ts, with every number taken
 * from shared/pricing.json (via public-pricing.ts) — the file plans.py charges
 * from. The retired planned prices (Starter $29 / Growth $49 / Scale $99) are
 * gone: there is one real paid plan, Starter.
 *
 * `paid` is the billing gate: razorpayBillingEnabled() in the prerender, and
 * payments_enabled + provider === "razorpay" from /api/billing/plans in React.
 * With payments off the answers keep the "free during the public beta" wording.
 */
import { STARTER_PRICES, ANNUAL_LABEL } from "./public-pricing";

export type PricingFaqKey = "is-free" | "pay-now" | "cost";

export interface PricingFaqItem {
  q: string;
  a: string;
}

const inr = STARTER_PRICES.INR;
const usd = STARTER_PRICES.USD;
const aed = STARTER_PRICES.AED;

const starterPrice = `${inr.monthlyLabel}/month in India, or ${usd.monthlyLabel} / ${aed.monthlyLabel} a month internationally`;
const starterAnnual = `annual billing is ${inr.annualLabel} / ${usd.annualLabel} / ${aed.annualLabel} a year (${ANNUAL_LABEL})`;
const starterIncludes =
  "Starter includes 50 simulations and 100 copilot messages a month, 2 data connectors, Truth Scan and stress tests, industry benchmarks and PDF export";

export function pricingFaq(paid: boolean): Record<PricingFaqKey, PricingFaqItem> {
  if (paid) {
    return {
      "is-free": {
        q: "Is FounderConsole free?",
        a: `Yes — the Free plan is free forever, with no credit card required: 1 company, 3 simulations and 10 copilot messages a month, CSV upload and the basic dashboard. When you need more, Starter is ${starterPrice}.`,
      },
      "pay-now": {
        q: "Do I need to pay anything right now?",
        a: "Only if you upgrade. The Free plan is never charged. Starter is billed in advance, monthly or annually, through Razorpay, and you can cancel anytime from Billing — see our Refund & Cancellation Policy.",
      },
      cost: {
        q: "What do the paid plans cost?",
        a: `Starter is ${starterPrice}; ${starterAnnual}. ${starterIncludes}.`,
      },
    };
  }
  return {
    "is-free": {
      q: "Is FounderConsole free?",
      a: `Yes — every feature is free during the public beta, and no credit card is required. When paid plans start, Starter will be ${starterPrice}; we'll give plenty of notice before anything changes.`,
    },
    "pay-now": {
      q: "Do I need to pay anything right now?",
      a: "No. Every feature is free during the public beta, with no credit card required. We'll announce paid plans well in advance before anything changes.",
    },
    cost: {
      q: "What will the paid plans cost later?",
      a: `Starter will be ${starterPrice}; ${starterAnnual}. ${starterIncludes}. Nothing is charged yet — every feature is free during the public beta.`,
    },
  };
}
