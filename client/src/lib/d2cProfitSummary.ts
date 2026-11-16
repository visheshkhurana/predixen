/**
 * What the dashboard shows a goods business about Profit per order: nothing
 * entered yet, a month that is missing inputs, or the latest month's CM2/CM3.
 * Input: GET /api/companies/:id/d2c/months (server/services/d2c_months.py).
 */

export const GOODS_INDUSTRIES: ReadonlySet<string> = new Set(['d2c', 'ecommerce', 'food', 'marketplace']);

export function isGoodsIndustry(industry?: string | null): boolean {
  return GOODS_INDUSTRIES.has((industry ?? '').trim().toLowerCase());
}

interface MonthLike {
  period: string;
  unit_economics?: {
    cm2?: number | null;
    cm3?: number | null;
    cm2_per_order?: number | null;
    cm3_per_order?: number | null;
    cm2_pct?: number | null;
    cm3_pct?: number | null;
    delivered_orders?: number | null;
    missing?: string[];
  } | null;
  missing?: string[];
}

export type ProfitSummary =
  | { state: 'empty' }
  | { state: 'incomplete'; period: string }
  | {
      state: 'ready';
      period: string;
      deliveredOrders: number | null;
      cm2PerOrder: number | null;
      cm3PerOrder: number | null;
      cm2Pct: number | null;
      cm3Pct: number | null;
    };

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

export function latestProfitSummary(months: MonthLike[] | null | undefined): ProfitSummary {
  if (!months || months.length === 0) return { state: 'empty' };
  const sorted = [...months].sort((a, b) => b.period.localeCompare(a.period));
  const withNumbers = sorted.find((m) => num(m.unit_economics?.cm2_per_order) !== null || num(m.unit_economics?.cm3_per_order) !== null);
  if (!withNumbers) return { state: 'incomplete', period: sorted[0].period.slice(0, 7) };
  const ue = withNumbers.unit_economics!;
  return {
    state: 'ready',
    period: withNumbers.period.slice(0, 7),
    deliveredOrders: num(ue.delivered_orders),
    cm2PerOrder: num(ue.cm2_per_order),
    cm3PerOrder: num(ue.cm3_per_order),
    cm2Pct: num(ue.cm2_pct),
    cm3Pct: num(ue.cm3_pct),
  };
}
