/**
 * Hiring planner runway from GET /companies/{id}/truth/latest.
 *
 * The truth scan's metrics are keyed net_burn (canonical NET burn: total costs
 * incl. COGS minus revenue; negative when profitable), cash_balance and
 * runway_p50. The page used to query a route that does not exist
 * (/truth-scan/latest) and read runway_months / total_monthly_expenses, so it
 * either showed nothing or treated gross spend as burn.
 */
function metricNumber(metrics: any, key: string): number | null {
  const raw = metrics?.[key];
  const v = raw !== null && typeof raw === "object" ? raw.value : raw;
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export function truthMetrics(truth: any): Record<string, unknown> | null {
  const m = truth?.metrics;
  return m && typeof m === "object" ? m : null;
}

/** Months of runway now, on canonical net burn; null when not burning or unknown. */
export function currentRunwayMonths(truth: any): number | null {
  const m = truthMetrics(truth);
  if (!m) return null;
  const cash = metricNumber(m, "cash_balance");
  const net = metricNumber(m, "net_burn");
  if (cash !== null && net !== null) {
    if (net <= 0 || cash <= 0) return null;
    return Math.round((cash / net) * 10) / 10;
  }
  const p50 = metricNumber(m, "runway_p50");
  return p50 !== null && p50 > 0 ? p50 : null;
}

/** Runway after adding `addedMonthlyCost` of payroll; null when still not burning. */
export function runwayAfterHires(truth: any, addedMonthlyCost: number): number | null {
  const m = truthMetrics(truth);
  if (!m) return null;
  const cash = metricNumber(m, "cash_balance");
  const net = metricNumber(m, "net_burn");
  if (cash === null || net === null || cash <= 0) return null;
  const newNet = net + Math.max(0, addedMonthlyCost);
  if (newNet <= 0) return null;
  return Math.round((cash / newNet) * 10) / 10;
}
