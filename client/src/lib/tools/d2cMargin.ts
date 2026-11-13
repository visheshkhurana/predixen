/**
 * D2C contribution margin (CM1 / CM2 / CM3) for one month, per brand and per
 * delivered order. Pure, no imports: the page, the server prerender and the
 * test all read this one module, so the worked example published on the page,
 * in the blog posts and in llms.txt cannot drift from what the tool computes.
 *
 * Layer definitions follow the D2C engine proposed in PR #227
 * (`server/core/d2c.py`), so the free tool and the product use one vocabulary:
 *
 *   net revenue = value of orders delivered and kept, ex-GST, after discounts
 *   CM1 = net revenue − COGS
 *   CM2 = CM1 − fulfilment (forward + packaging + RTO reverse + return reverse)
 *               − payment costs (gateway % on prepaid, COD fee)
 *   CM3 = CM2 − marketing
 *
 * Assumptions, stated rather than hidden (the page prints them too):
 *   - AOV is entered ex-GST and after discounts.
 *   - RTO'd and returned goods go back into sellable stock, so they carry no
 *     COGS. Damaged returns would make the real CM1 lower.
 *   - Every shipped order pays forward shipping and packaging, including the
 *     ones that come back as RTO.
 *   - The gateway fee is charged on every prepaid order shipped; the COD fee on
 *     every COD order actually delivered. RTO is spread evenly across COD and
 *     prepaid, which flatters COD — in practice most RTO comes from COD orders.
 */

export interface D2cMarginInputs {
  /** Average order value, ₹, ex-GST, after discounts. */
  aov: number;
  /** Orders shipped in the month. */
  orders: number;
  /** Share of shipped orders returned to origin (undelivered), 0–100. */
  rtoPct: number;
  /** Share of delivered orders returned by the customer, 0–100. */
  returnPct: number;
  /** Share of orders paid cash on delivery, 0–100. */
  codPct: number;
  /** Landed product cost per order, ₹. */
  cogsPerOrder: number;
  /** Packaging per shipped order, ₹. */
  packagingPerOrder: number;
  /** Forward shipping per shipped order, ₹. */
  forwardShipping: number;
  /** Reverse shipping per RTO or customer return, ₹. */
  reverseShipping: number;
  /** Payment gateway fee on prepaid orders, % of order value. */
  gatewayPct: number;
  /** COD handling/remittance fee per delivered COD order, ₹. */
  codFee: number;
  /** Total marketing spend in the month (ads, influencers, affiliates), ₹. */
  marketing: number;
}

export interface D2cMarginResult {
  outcome: "ok" | "invalid";
  reason: string | null;
  rtoOrders: number;
  deliveredOrders: number;
  returnedOrders: number;
  keptOrders: number;
  netRevenue: number;
  cogs: number;
  fulfilment: number;
  paymentCosts: number;
  /** Direct logistics cost of failed deliveries: forward + packaging + reverse on RTO orders. */
  rtoLogisticsCost: number;
  cm1: number;
  cm2: number;
  cm3: number;
  /** As a share of net revenue, 0–100. Null when net revenue is zero. */
  cm1Pct: number | null;
  cm2Pct: number | null;
  cm3Pct: number | null;
  /** Per delivered order, ₹. Null when nothing was delivered. */
  cm1PerOrder: number | null;
  cm2PerOrder: number | null;
  cm3PerOrder: number | null;
  /** Marketing efficiency ratio = net revenue / marketing. Null when marketing is zero. */
  mer: number | null;
  /** MER at which CM3 is exactly zero = 1 / CM2 margin. Null when CM2 is not positive. */
  breakEvenMer: number | null;
}

/** The illustrative brand used on the page, in the blog posts and in llms.txt. */
export const D2C_WORKED_EXAMPLE: D2cMarginInputs = {
  aov: 1200,
  orders: 2000,
  rtoPct: 18,
  returnPct: 5,
  codPct: 55,
  cogsPerOrder: 420,
  packagingPerOrder: 30,
  forwardShipping: 70,
  reverseShipping: 70,
  gatewayPct: 2,
  codFee: 40,
  marketing: 600000,
};

const EMPTY: Omit<D2cMarginResult, "outcome" | "reason"> = {
  rtoOrders: 0,
  deliveredOrders: 0,
  returnedOrders: 0,
  keptOrders: 0,
  netRevenue: 0,
  cogs: 0,
  fulfilment: 0,
  paymentCosts: 0,
  rtoLogisticsCost: 0,
  cm1: 0,
  cm2: 0,
  cm3: 0,
  cm1Pct: null,
  cm2Pct: null,
  cm3Pct: null,
  cm1PerOrder: null,
  cm2PerOrder: null,
  cm3PerOrder: null,
  mer: null,
  breakEvenMer: null,
};

const PCT_FIELDS: ReadonlyArray<keyof D2cMarginInputs> = ["rtoPct", "returnPct", "codPct", "gatewayPct"];

export function computeD2cMargin(i: D2cMarginInputs): D2cMarginResult {
  for (const [key, value] of Object.entries(i) as Array<[keyof D2cMarginInputs, number]>) {
    if (!Number.isFinite(value)) {
      return { outcome: "invalid", reason: `Enter a number for ${key}.`, ...EMPTY };
    }
    if (value < 0) {
      return { outcome: "invalid", reason: "Inputs cannot be negative.", ...EMPTY };
    }
  }
  for (const key of PCT_FIELDS) {
    if (i[key] > 100) {
      return { outcome: "invalid", reason: "Percentages must be between 0 and 100.", ...EMPTY };
    }
  }

  const rtoOrders = i.orders * (i.rtoPct / 100);
  const deliveredOrders = i.orders - rtoOrders;
  const returnedOrders = deliveredOrders * (i.returnPct / 100);
  const keptOrders = deliveredOrders - returnedOrders;

  const netRevenue = keptOrders * i.aov;
  const cogs = keptOrders * i.cogsPerOrder;
  const cm1 = netRevenue - cogs;

  const fulfilment =
    i.orders * (i.forwardShipping + i.packagingPerOrder) +
    (rtoOrders + returnedOrders) * i.reverseShipping;
  const gateway = i.orders * (1 - i.codPct / 100) * i.aov * (i.gatewayPct / 100);
  const codFees = deliveredOrders * (i.codPct / 100) * i.codFee;
  const paymentCosts = gateway + codFees;
  const cm2 = cm1 - fulfilment - paymentCosts;
  const cm3 = cm2 - i.marketing;

  const rtoLogisticsCost = rtoOrders * (i.forwardShipping + i.packagingPerOrder + i.reverseShipping);

  const pct = (v: number) => (netRevenue > 0 ? (v / netRevenue) * 100 : null);
  const perOrder = (v: number) => (deliveredOrders > 0 ? v / deliveredOrders : null);
  const cm2Margin = netRevenue > 0 ? cm2 / netRevenue : 0;

  return {
    outcome: "ok",
    reason: null,
    rtoOrders,
    deliveredOrders,
    returnedOrders,
    keptOrders,
    netRevenue,
    cogs,
    fulfilment,
    paymentCosts,
    rtoLogisticsCost,
    cm1,
    cm2,
    cm3,
    cm1Pct: pct(cm1),
    cm2Pct: pct(cm2),
    cm3Pct: pct(cm3),
    cm1PerOrder: perOrder(cm1),
    cm2PerOrder: perOrder(cm2),
    cm3PerOrder: perOrder(cm3),
    mer: i.marketing > 0 ? netRevenue / i.marketing : null,
    breakEvenMer: cm2Margin > 0 ? 1 / cm2Margin : null,
  };
}

/**
 * ₹ in the Indian system: ₹3.27 L, ₹1.20 Cr, ₹420. Lakh = 1,00,000; crore = 1,00,00,000.
 */
export function formatInr(value: number): string {
  const sign = value < 0 ? "−" : "";
  const abs = Math.abs(value);
  if (abs >= 1_00_00_000) return `${sign}₹${(abs / 1_00_00_000).toFixed(2)} Cr`;
  if (abs >= 1_00_000) return `${sign}₹${(abs / 1_00_000).toFixed(2)} L`;
  return `${sign}₹${Math.round(abs).toLocaleString("en-IN")}`;
}
