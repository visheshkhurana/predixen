/**
 * The paid plan as the public pages show it, derived from shared/pricing.json —
 * the same file server/core/plans.py reads to build the Razorpay price table.
 * So the price on /pricing and /refund-policy cannot drift from the price
 * checkout charges. Imported by the React pages and by server/seo-prerender.ts.
 *
 * Whether the paid plan is shown at all is a separate question (is billing
 * live?). The server answers it: `razorpayBillingEnabled()` in
 * server/billing-gate.ts for the prerender, and `payments_enabled` +
 * `provider === "razorpay"` from GET /api/billing/plans for the React page.
 */
import pricing from "../../../shared/pricing.json";

export type PriceCurrency = "INR" | "USD" | "AED";

export const ANNUAL_MULTIPLIER: number = pricing.annual_multiplier;
export const ANNUAL_LABEL: string = pricing.annual_label;

const STARTER = pricing.regional_monthly_prices.starter as Record<PriceCurrency, number>;

export interface CurrencyPrice {
  currency: PriceCurrency;
  monthly: number;
  annual: number;
  monthlyLabel: string;
  annualLabel: string;
}

/** Grouping is done by hand so the output is identical in Node and every browser. */
function group(amount: number, indian: boolean): string {
  const digits = String(Math.round(amount));
  if (!indian || digits.length <= 3) {
    return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  const last3 = digits.slice(-3);
  const rest = digits.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  return `${rest},${last3}`;
}

export function formatPrice(currency: PriceCurrency, amount: number): string {
  if (currency === "INR") return `₹${group(amount, true)}`;
  if (currency === "USD") return `$${group(amount, false)}`;
  return `AED ${group(amount, false)}`;
}

function priceFor(currency: PriceCurrency): CurrencyPrice {
  const monthly = STARTER[currency];
  const annual = monthly * ANNUAL_MULTIPLIER;
  return {
    currency,
    monthly,
    annual,
    monthlyLabel: formatPrice(currency, monthly),
    annualLabel: formatPrice(currency, annual),
  };
}

/** Starter in each sold currency. INR first: India is the home market. */
export const STARTER_PRICES: Record<PriceCurrency, CurrencyPrice> = {
  INR: priceFor("INR"),
  USD: priceFor("USD"),
  AED: priceFor("AED"),
};

/** e.g. "₹3,000/month or ₹30,000/year (2 months free)" */
export function starterSummary(currency: PriceCurrency): string {
  const p = STARTER_PRICES[currency];
  return `${p.monthlyLabel}/month or ${p.annualLabel}/year (${ANNUAL_LABEL})`;
}
