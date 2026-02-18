import { useMemo } from 'react';
import { useFounderStore } from '@/store/founderStore';
import { useQuery } from '@tanstack/react-query';

export type MetricSource = 'reported' | 'computed' | 'estimated';

export interface MetricWarning {
  metric: string;
  value: number;
  reason: string;
}

export interface FinancialMetrics {
  mrr: number;
  arr: number;
  cashOnHand: number;
  burnRate: number;
  netBurn: number;
  runway: number;
  runwayDisplay: string;
  cac: number;
  ltv: number;
  ltvCacRatio: number;
  grossMargin: number;
  grossMarginPct: number;
  churnRate: number;
  churnRatePct: number;
  totalCustomers: number;
  headcount: number;
  arpu: number;
  paybackPeriod: number;
  burnMultiple: number;
  revenuePerEmployee: number;
  monthlyGrowthRate: number;
  ndr: number;
  isProfitable: boolean;
  hasData: boolean;
  sources: Record<string, MetricSource>;
  warnings: MetricWarning[];
}

const EMPTY_METRICS: FinancialMetrics = {
  mrr: 0, arr: 0, cashOnHand: 0, burnRate: 0, netBurn: 0,
  runway: 0, runwayDisplay: '0.0 mo',
  cac: 0, ltv: 0, ltvCacRatio: 0,
  grossMargin: 0, grossMarginPct: 0,
  churnRate: 0, churnRatePct: 0,
  totalCustomers: 0, headcount: 0, arpu: 0,
  paybackPeriod: 0, burnMultiple: 0, revenuePerEmployee: 0,
  monthlyGrowthRate: 0, ndr: 0,
  isProfitable: false, hasData: false,
  sources: {},
  warnings: [],
};

function getToken(): string | null {
  let token = localStorage.getItem('founderconsole-token');
  if (!token) {
    try {
      const raw = localStorage.getItem('founderconsole-founder-storage');
      if (raw) {
        const parsed = JSON.parse(raw);
        token = parsed?.state?.token || null;
        if (token) {
          localStorage.setItem('founderconsole-token', token);
        }
      }
    } catch {}
  }
  return token;
}

async function fetchJson(url: string): Promise<any> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(url, { headers, credentials: 'include' });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function useFinancialMetrics(): { metrics: FinancialMetrics; isLoading: boolean } {
  const { currentCompany, financialBaseline } = useFounderStore();
  const companyId = currentCompany?.id ?? null;

  const { data: computed, isLoading: computedLoading } = useQuery<any>({
    queryKey: ['computed-metrics', companyId],
    queryFn: () => fetchJson(`/api/companies/${companyId}/metrics/computed`),
    enabled: !!companyId,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    retry: 3,
    retryDelay: (attempt) => Math.min(1000 * Math.pow(2, attempt), 5000),
  });

  const { data: truthScan } = useQuery<any>({
    queryKey: ['truth-latest', companyId],
    queryFn: () => fetchJson(`/api/companies/${companyId}/truth/latest`),
    enabled: !!companyId,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    refetchOnMount: true,
    retry: 1,
  });

  const { data: backendBaseline } = useQuery<any>({
    queryKey: ['financials-baseline', companyId],
    queryFn: () => fetchJson(`/api/companies/${companyId}/financials/baseline`),
    enabled: !!companyId,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    refetchOnMount: true,
    retry: 1,
  });

  const metrics = useMemo((): FinancialMetrics => {
    const c = computed || {};
    const tsMetrics = truthScan?.metrics || {};
    const bb = backendBaseline?.baseline;
    const ext = backendBaseline?.extendedMetrics;
    const fb = financialBaseline;

    const v = (primary: any, ...fallbacks: any[]): number => {
      const candidates = [primary, ...fallbacks];
      for (const val of candidates) {
        const n = typeof val === 'string' ? parseFloat(val) : val;
        if (typeof n === 'number' && isFinite(n) && n > 0) return n;
      }
      return 0;
    };

    const tsVal = (key: string): number => {
      const val = tsMetrics[key];
      if (val === null || val === undefined) return 0;
      if (typeof val === 'object' && 'value' in val) return typeof val.value === 'number' ? val.value : 0;
      if (typeof val === 'number') return val;
      return 0;
    };

    const mrr = v(c.mrr, bb?.monthlyRevenue, fb?.monthlyRevenue, tsVal('mrr'));
    const arr = v(c.arr, ext?.arr, tsVal('arr')) || mrr * 12;
    const cashOnHand = v(c.cashOnHand, bb?.cashOnHand, fb?.cashOnHand, tsVal('cash_balance'));

    const breakdownPayroll = bb?.expenseBreakdown?.payroll ?? fb?.expenseBreakdown?.payroll ?? 0;
    const breakdownMarketing = bb?.expenseBreakdown?.marketing ?? fb?.expenseBreakdown?.marketing ?? 0;
    const breakdownOperating = bb?.expenseBreakdown?.operating ?? fb?.expenseBreakdown?.operating ?? 0;
    const breakdownCogs = bb?.expenseBreakdown?.cogs ?? fb?.expenseBreakdown?.cogs ?? 0;
    const breakdownOther = bb?.expenseBreakdown?.otherOpex ?? fb?.expenseBreakdown?.otherOpex ?? 0;
    const breakdownSum = breakdownPayroll + breakdownMarketing + breakdownOperating + breakdownCogs + breakdownOther;

    const hasManualOverride = fb?.hasManualExpenseOverride ?? false;
    const baselineTotalExpenses = bb?.totalMonthlyExpenses ?? fb?.totalMonthlyExpenses ?? 0;
    const effectiveExpenses = hasManualOverride
      ? baselineTotalExpenses
      : (breakdownSum > 0 ? breakdownSum : baselineTotalExpenses);

    const netBurn = v(
      c.netBurn,
      effectiveExpenses > 0 && mrr > 0 ? Math.max(0, effectiveExpenses - mrr) : 0,
      tsVal('net_burn')
    );
    const burnRate = netBurn;

    let runway: number;
    let runwayDisplay: string;
    if (c.runway && c.runway > 0 && c.runway < 999) {
      runway = c.runway;
      runwayDisplay = `${runway.toFixed(1)} mo`;
    } else if (netBurn <= 0) {
      runway = Infinity;
      runwayDisplay = '\u221E';
    } else if (cashOnHand <= 0) {
      runway = 0;
      runwayDisplay = '0.0 mo';
    } else {
      runway = Math.min(cashOnHand / netBurn, 120);
      runwayDisplay = `${runway.toFixed(1)} mo`;
    }

    const cac = v(c.cac, ext?.cac, tsVal('cac'));
    const ltv = v(c.ltv, ext?.ltv, tsVal('ltv'));
    const ltvCacRatio = v(c.ltvCacRatio, ext?.ltvCacRatio, tsVal('ltv_cac_ratio'))
      || (cac > 0 && ltv > 0 ? ltv / cac : 0);
    const grossMarginRaw = v(c.grossMarginPct, ext?.grossMargin, tsVal('gross_margin'));
    const grossMarginPct = grossMarginRaw > 0 && grossMarginRaw <= 1 ? grossMarginRaw * 100 : grossMarginRaw;
    const grossMarginDecimal = c.grossMarginDecimal || grossMarginPct / 100;

    const churnRaw = v(c.churnRatePct, tsVal('churn_rate'), tsVal('gross_churn_rate'));
    const churnRatePct = churnRaw > 0 && churnRaw <= 1 ? churnRaw * 100 : churnRaw;
    const churnRateDecimal = churnRatePct / 100;

    const totalCustomers = v(c.totalCustomers, ext?.customers, tsVal('customer_count'), tsVal('total_customers'));
    const headcount = v(c.headcount, ext?.headcount, tsVal('headcount'))
      || (currentCompany ? (currentCompany as any).employees || 0 : 0);
    const arpu = v(c.arpu) || (totalCustomers > 0 ? mrr / totalCustomers : 0);

    let paybackPeriod: number;
    if (c.paybackPeriod && c.paybackPeriod > 0) {
      paybackPeriod = c.paybackPeriod;
    } else if (cac > 0 && arpu > 0 && grossMarginDecimal > 0) {
      paybackPeriod = cac / (arpu * grossMarginDecimal);
    } else if (cac > 0 && arpu > 0) {
      paybackPeriod = cac / arpu;
    } else {
      paybackPeriod = 0;
    }

    const burnMultiple = v(c.burnMultiple, ext?.burnMultiple, tsVal('burn_multiple'));
    const revenuePerEmployee = headcount > 0 ? mrr / headcount : 0;

    const rawGrowthRate = v(c.momGrowth, tsVal('revenue_growth_mom'), fb?.monthlyGrowthRate);
    const monthlyGrowthRate = rawGrowthRate;
    const rawNdr = v(c.ndr, tsVal('net_revenue_retention'));
    const ndr = rawNdr > 0 && rawNdr <= 200 ? rawNdr : 0;

    const warnings: MetricWarning[] = [];
    if (rawGrowthRate > 100 || rawGrowthRate < -100) {
      warnings.push({ metric: 'monthlyGrowthRate', value: rawGrowthRate, reason: `Out of sanity bounds (-100% to +100%): ${rawGrowthRate}%` });
    }
    if (rawNdr > 200 || rawNdr < 0) {
      warnings.push({ metric: 'ndr', value: rawNdr, reason: `Out of sanity bounds (0-200%): ${rawNdr}%` });
    }
    if (grossMarginPct > 100 || grossMarginPct < -100) {
      warnings.push({ metric: 'grossMargin', value: grossMarginPct, reason: `Unusual gross margin: ${grossMarginPct}%` });
    }

    const totalExpenses = c.totalExpenses || effectiveExpenses || 0;
    const isProfitable = totalExpenses > 0 && mrr >= totalExpenses;
    const hasData = mrr > 0 || cashOnHand > 0 || netBurn > 0;

    const sources: Record<string, MetricSource> = {};
    const mark = (key: string, directValue: any, computedValue: number) => {
      if (directValue && Number(directValue) > 0) {
        sources[key] = 'reported';
      } else if (computedValue > 0) {
        sources[key] = 'computed';
      }
    };
    mark('mrr', c.mrr || bb?.monthlyRevenue || fb?.monthlyRevenue, mrr);
    sources['arr'] = (c.arr || ext?.arr) ? 'reported' : (mrr > 0 ? 'computed' : 'estimated');
    mark('cashOnHand', c.cashOnHand || bb?.cashOnHand || fb?.cashOnHand, cashOnHand);
    mark('netBurn', c.netBurn, netBurn);
    sources['runway'] = (netBurn > 0 && cashOnHand > 0) ? 'computed' : 'estimated';
    mark('cac', c.cac || ext?.cac, cac);
    mark('ltv', c.ltv || ext?.ltv, ltv);
    sources['ltvCacRatio'] = (c.ltvCacRatio || ext?.ltvCacRatio) ? 'reported' : (cac > 0 && ltv > 0 ? 'computed' : 'estimated');
    mark('grossMargin', c.grossMarginPct || ext?.grossMargin, grossMarginPct);
    mark('churnRate', c.churnRatePct, churnRatePct);
    mark('totalCustomers', c.totalCustomers || ext?.customers, totalCustomers);
    mark('headcount', c.headcount || ext?.headcount, headcount);
    sources['arpu'] = c.arpu ? 'reported' : (totalCustomers > 0 && mrr > 0 ? 'computed' : 'estimated');
    sources['paybackPeriod'] = c.paybackPeriod ? 'reported' : (cac > 0 && arpu > 0 ? 'computed' : 'estimated');
    sources['burnMultiple'] = (c.burnMultiple || ext?.burnMultiple) ? 'reported' : 'computed';
    sources['revenuePerEmployee'] = headcount > 0 ? 'computed' : 'estimated';
    sources['monthlyGrowthRate'] = (c.momGrowth || tsVal('revenue_growth_mom') > 0) ? 'reported' : (fb?.monthlyGrowthRate ? 'estimated' : 'estimated');
    sources['ndr'] = (c.ndr || tsVal('net_revenue_retention') > 0) ? 'reported' : 'estimated';

    return {
      mrr, arr, cashOnHand, burnRate, netBurn, runway, runwayDisplay,
      cac, ltv, ltvCacRatio,
      grossMargin: grossMarginDecimal, grossMarginPct,
      churnRate: churnRateDecimal, churnRatePct,
      totalCustomers, headcount, arpu, paybackPeriod,
      burnMultiple, revenuePerEmployee, monthlyGrowthRate, ndr,
      isProfitable, hasData, sources, warnings,
    };
  }, [computed, truthScan?.metrics, financialBaseline, currentCompany, backendBaseline]);

  const isLoading = !companyId || (computedLoading && !computed && !backendBaseline && !truthScan);

  return { metrics, isLoading };
}
