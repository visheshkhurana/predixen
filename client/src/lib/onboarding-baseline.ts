/**
 * The onboarding Health Check must show the burn and runway the dashboard will
 * show once the baseline is saved. The server (split_cogs_from_entered_costs in
 * server/api/datasets.py) treats opex + payroll + other as the whole cost base
 * and carves the COGS a gross margin implies out of opex, then other costs.
 * Only when the margin implies more COGS than those two can hold do total costs
 * rise. This mirrors that rule so the two screens agree.
 */

export interface BaselineNumbers {
  monthly_revenue: number;
  gross_margin_pct: number;
  opex: number;
  payroll: number;
  other_costs: number;
  cash_balance: number;
}

export interface BaselineSummary {
  cogs: number;
  totalCosts: number;
  /** Positive = burning cash each month; negative = monthly surplus. */
  netBurn: number;
  /** Months of cash at the current burn; null when not burning or no cash. */
  runwayMonths: number | null;
  /** Revenue covers costs, so cash is not running down. */
  notBurning: boolean;
}

function nonNeg(n: number): number {
  return Number.isFinite(n) && n > 0 ? n : 0;
}

export function summarizeBaseline(b: BaselineNumbers): BaselineSummary {
  const revenue = nonNeg(b.monthly_revenue);
  // Same rule as server/core/units.py: 0.55 and 55 both mean 55%.
  const rawGm = nonNeg(b.gross_margin_pct);
  const gm = Math.min(100, rawGm <= 1 ? rawGm * 100 : rawGm);
  const opex = nonNeg(b.opex);
  const payroll = nonNeg(b.payroll);
  const other = nonNeg(b.other_costs);

  const cogs = revenue > 0 ? (revenue * (100 - gm)) / 100 : 0;
  const fromOpex = Math.min(cogs, opex);
  const fromOther = Math.min(cogs - fromOpex, other);
  const totalCosts = cogs + (opex - fromOpex) + payroll + (other - fromOther);

  const netBurn = totalCosts - revenue;
  const cash = nonNeg(b.cash_balance);
  const runwayMonths = netBurn > 0 && cash > 0 ? cash / netBurn : null;
  return { cogs, totalCosts, netBurn, runwayMonths, notBurning: totalCosts > 0 && netBurn <= 0 };
}

/**
 * Stage example figures are written in US dollars. Shown as placeholders in
 * another currency they must be converted, or a seed D2C brand in India sees
 * "₹25000" as typical monthly revenue. Rough rates: these are labelled as
 * estimates, never saved.
 */
const APPROX_PER_USD: Record<string, number> = {
  USD: 1,
  INR: 85,
  AED: 3.67,
  SGD: 1.35,
  GBP: 0.8,
  EUR: 0.92,
};

export function exampleAmount(usd: number, currency: string): number {
  const rate = APPROX_PER_USD[currency] ?? 1;
  const value = usd * rate;
  if (value === 0) return 0;
  // Round to 2 significant figures so it reads as an example, not a quote.
  const magnitude = Math.pow(10, Math.max(0, Math.floor(Math.log10(Math.abs(value))) - 1));
  return Math.round(value / magnitude) * magnitude;
}
