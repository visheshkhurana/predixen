/**
 * Which source wins when the dashboard and /truth show the same number.
 *
 * The server's GET /companies/:id/metrics/computed is the single source of
 * truth (server/api/ingest.py:get_computed_metrics). For CAC / LTV / LTV:CAC
 * it resolves founder record -> D2C month CAC -> real truth-scan values via
 * server/truth/invented_metrics.py:resolve_unit_economics, and never passes
 * on the defaults the truth scan invents (LTV 3,000, CAC 500, ...).
 *
 * Two client paths used to bypass it:
 *  - useFinancialMetrics fell back to /financials/baseline `extendedMetrics`
 *    whenever /metrics/computed returned 0 (= unknown). With no financial
 *    record that endpoint copies the raw truth-scan values, invented ones
 *    included, so the dashboard showed an LTV the server had refused.
 *  - /truth read LTV / CAC / revenue / runway straight from the stored truth
 *    scan (`metrics.ltv`, `metrics.monthly_revenue`, `metrics.runway_p50`),
 *    so a stale scan, an invented default or a differently named key (the
 *    sample company's scan stores `mrr` and `runway_months`) disagreed with,
 *    or blanked out, what the dashboard showed.
 *
 * Both now go through the helpers below.
 */

export type UnitEconomics = { cac: number; ltv: number; ltvCacRatio: number };

const pos = (v: unknown): number => {
  const n = typeof v === 'string' ? parseFloat(v) : (v as number);
  return typeof n === 'number' && Number.isFinite(n) && n > 0 ? n : 0;
};

/**
 * CAC / LTV / LTV:CAC for the dashboard.
 *
 * When /metrics/computed answered, its values are final — 0 means "unknown",
 * not "try the next source". Only when that endpoint is unavailable do we fall
 * back to the baseline record and to truth-scan values the scan did not invent.
 */
export function pickUnitEconomics(input: {
  computed: { cac?: unknown; ltv?: unknown; ltvCacRatio?: unknown } | null | undefined;
  baselineExt?: { cac?: unknown; ltv?: unknown; ltvCacRatio?: unknown } | null;
  /** Truth-scan value, already 0 for anything listed in `_estimated_metrics`. */
  truthReal: (key: 'cac' | 'ltv' | 'ltv_cac_ratio') => number;
}): UnitEconomics {
  const { computed, baselineExt, truthReal } = input;
  let cac: number;
  let ltv: number;
  let ratio: number;
  if (computed) {
    cac = pos(computed.cac);
    ltv = pos(computed.ltv);
    ratio = pos(computed.ltvCacRatio);
  } else {
    cac = pos(baselineExt?.cac) || truthReal('cac');
    ltv = pos(baselineExt?.ltv) || truthReal('ltv');
    ratio = pos(baselineExt?.ltvCacRatio) || truthReal('ltv_cac_ratio');
  }
  if (!ratio && cac > 0 && ltv > 0) ratio = ltv / cac;
  return { cac, ltv, ltvCacRatio: ratio };
}

/** The subset of useFinancialMetrics() /truth needs. */
export type SharedMetricsForTruth = {
  hasData: boolean;
  mrr: number;
  arr: number;
  cashOnHand: number;
  netBurn: number;
  totalMonthlyExpenses: number;
  runway: number;
  grossMarginPct: number;
  cac: number;
  ltv: number;
  ltvCacRatio: number;
  paybackPeriod: number;
  sources: Record<string, string | undefined>;
};

/** Truth-scan keys some scans (e.g. the seeded sample company) store under another name. */
const TRUTH_KEY_ALIASES: Array<[canonical: string, alias: string]> = [
  ['monthly_revenue', 'mrr'],
  ['runway_p50', 'runway_months'],
  ['payback_months', 'cac_payback_months'],
  ['customer_count', 'total_customers'],
];

const truthNum = (v: unknown): number | null => {
  if (v === null || v === undefined) return null;
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  if (typeof v === 'object' && v !== null && 'value' in (v as Record<string, unknown>)) {
    return truthNum((v as Record<string, unknown>).value);
  }
  return null;
};

/**
 * The truth-scan metrics /truth renders, with the headline figures replaced
 * by the ones the dashboard shows (same hook, same server endpoint) and
 * invented unit economics removed. Returns a new object.
 */
export function alignTruthMetrics(
  raw: Record<string, any> | null | undefined,
  shared: SharedMetricsForTruth | null | undefined,
): Record<string, any> {
  const m: Record<string, any> = { ...(raw || {}) };

  for (const [canonical, alias] of TRUTH_KEY_ALIASES) {
    if (truthNum(m[canonical]) === null && truthNum(m[alias]) !== null) m[canonical] = m[alias];
  }

  // The scan's own list of values it filled from defaults: never shown as facts.
  const estimated = new Set<string>(Array.isArray(m._estimated_metrics) ? m._estimated_metrics : []);
  for (const key of ['cac', 'ltv', 'ltv_cac_ratio', 'payback_months']) {
    if (estimated.has(key)) m[key] = null;
  }

  if (!shared || !shared.hasData) return m;

  if (shared.mrr > 0) {
    m.monthly_revenue = shared.mrr;
    m.mrr = shared.mrr;
  }
  if (shared.arr > 0) m.arr = shared.arr;
  if (shared.cashOnHand > 0) m.cash_balance = shared.cashOnHand;
  if (shared.netBurn > 0) m.net_burn = shared.netBurn;
  if (shared.grossMarginPct !== 0 && Number.isFinite(shared.grossMarginPct)) m.gross_margin = shared.grossMarginPct;

  const scoreable = shared.mrr > 0 || shared.totalMonthlyExpenses > 0;
  if (shared.runway === Infinity && scoreable) {
    m.runway_sustainable = true;
  } else if (Number.isFinite(shared.runway) && shared.runway > 0) {
    m.runway_p50 = shared.runway;
    m.runway_sustainable = false;
  }

  // Unit economics: the dashboard's (server-resolved) value or nothing.
  const known = (key: string, v: number) => v > 0 && shared.sources[key] !== 'estimated';
  m.cac = known('cac', shared.cac) ? shared.cac : null;
  m.ltv = known('ltv', shared.ltv) ? shared.ltv : null;
  m.ltv_cac_ratio =
    m.cac !== null && m.ltv !== null && known('ltvCacRatio', shared.ltvCacRatio) ? shared.ltvCacRatio : null;
  if (known('paybackPeriod', shared.paybackPeriod)) m.payback_months = shared.paybackPeriod;

  return m;
}
