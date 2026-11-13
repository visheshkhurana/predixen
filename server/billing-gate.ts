/**
 * Is Razorpay billing live? The Node-side copy of
 * server/core/razorpay_billing.razorpay_enabled(): an explicit
 * BILLING_PROVIDER=razorpay AND all three Razorpay secrets. Anything less and
 * payments are off, so the site keeps its "free during public beta" copy.
 *
 * Used by the CSP (server/index.ts) and by the /pricing prerender
 * (server/seo-prerender.ts). Reads the environment at call time so a test can
 * flip it; in production the env is fixed for the life of the process.
 */
export function razorpayBillingEnabled(env: NodeJS.ProcessEnv = process.env): boolean {
  return (
    (env.BILLING_PROVIDER || "").trim().toLowerCase() === "razorpay" &&
    !!(env.RAZORPAY_KEY_ID || "").trim() &&
    !!(env.RAZORPAY_KEY_SECRET || "").trim() &&
    !!(env.RAZORPAY_WEBHOOK_SECRET || "").trim()
  );
}
