import type { FinancialMetrics } from '@/hooks/useFinancialMetrics';

export interface ComputedCoremetrics {
  mrr: number;
  arr: number;
  netBurn: number;
  burnRate: number;
  cashOnHand: number;
  runway: number;
  runwayDisplay: string;
  totalMonthlyExpenses: number;
  ltvCacRatio: number;
  cac: number;
  ltv: number;
  totalCustomers: number;
  burnMultiple: number;
  grossMarginPct: number;
  churnRatePct: number;
  isProfitable: boolean;
  hasData: boolean;
}

export function computeCoreMetrics(raw: FinancialMetrics): ComputedCoremetrics {
  const mrr = raw.mrr ?? 0;
  const arr = raw.arr || mrr * 12;
  const cashOnHand = raw.cashOnHand ?? 0;
  const totalMonthlyExpenses = raw.totalMonthlyExpenses ?? 0;
  const netBurn = raw.netBurn ?? 0;
  const burnRate = netBurn;

  let runway: number;
  let runwayDisplay: string;
  if (netBurn <= 0) {
    runway = Infinity;
    runwayDisplay = '\u221E';
  } else if (cashOnHand <= 0) {
    runway = 0;
    runwayDisplay = '0.0 mo';
  } else {
    runway = Math.min(cashOnHand / netBurn, 120);
    runwayDisplay = `${runway.toFixed(1)} mo`;
  }

  if (raw.runway && raw.runway > 0 && raw.runway < 900) {
    runway = raw.runway;
    runwayDisplay = `${runway.toFixed(1)} mo`;
  }

  const cac = raw.cac ?? 0;
  const ltv = raw.ltv ?? 0;
  const ltvCacRatio = raw.ltvCacRatio ?? (cac > 0 && ltv > 0 ? ltv / cac : 0);
  const totalCustomers = raw.totalCustomers ?? 0;
  const burnMultiple = raw.burnMultiple ?? (mrr > 0 && netBurn > 0 ? netBurn / mrr : 0);
  const grossMarginPct = raw.grossMarginPct ?? 0;
  const churnRatePct = raw.churnRatePct ?? 0;
  const isProfitable = mrr > totalMonthlyExpenses;
  const hasData = raw.hasData ?? false;

  return {
    mrr,
    arr,
    netBurn,
    burnRate,
    cashOnHand,
    runway,
    runwayDisplay,
    totalMonthlyExpenses,
    ltvCacRatio,
    cac,
    ltv,
    totalCustomers,
    burnMultiple,
    grossMarginPct,
    churnRatePct,
    isProfitable,
    hasData,
  };
}

export function formatMetricValue(value: number, prefix?: string, unit?: string): string {
  if (!isFinite(value)) return '\u221E';
  if (prefix === '$' && Math.abs(value) >= 1_000_000) return `${prefix}${(value / 1_000_000).toFixed(1)}M`;
  if (prefix === '$' && Math.abs(value) >= 1_000) return `${prefix}${(value / 1_000).toFixed(value % 1_000 === 0 ? 0 : 1)}K`;
  if (prefix) return `${prefix}${value.toLocaleString()}`;
  return `${value}${unit || ''}`;
}

export function resolveGoalMetric(metricKey: string, metrics: ComputedCoremetrics): number | null {
  const map: Record<string, number> = {
    MRR: metrics.mrr,
    CAC: metrics.cac,
    Customers: metrics.totalCustomers,
    Runway: metrics.runway === Infinity ? 999 : metrics.runway,
    'LTV:CAC': metrics.ltvCacRatio,
    'Burn Rate': metrics.netBurn,
    'Gross Margin': metrics.grossMarginPct,
    'Churn Rate': metrics.churnRatePct,
  };
  return metricKey in map ? map[metricKey] : null;
}

export function deriveGoalStatus(
  current: number,
  target: number,
  deadline: string,
  isInverse: boolean
): 'on_track' | 'at_risk' | 'behind' | 'completed' {
  const progress = isInverse
    ? target > 0 ? (target / current) : 0
    : target > 0 ? (current / target) : 0;

  if (progress >= 1) return 'completed';

  const daysLeft = Math.max(0, Math.ceil((new Date(deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24)));
  if (progress >= 0.75 || (progress >= 0.5 && daysLeft > 60)) return 'on_track';
  if (progress >= 0.4 || daysLeft > 30) return 'at_risk';
  return 'behind';
}
