import { useMemo } from 'react';
import { useFounderStore } from '@/store/founderStore';
import { useQuery } from '@tanstack/react-query';

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
  isProfitable: boolean;
  hasData: boolean;
}

const EMPTY_METRICS: FinancialMetrics = {
  mrr: 0, arr: 0, cashOnHand: 0, burnRate: 0, netBurn: 0,
  runway: 0, runwayDisplay: '0.0 mo',
  cac: 0, ltv: 0, ltvCacRatio: 0,
  grossMargin: 0, grossMarginPct: 0,
  churnRate: 0, churnRatePct: 0,
  totalCustomers: 0, headcount: 0, arpu: 0,
  paybackPeriod: 0, burnMultiple: 0, revenuePerEmployee: 0,
  isProfitable: false, hasData: false,
};

function getToken(): string | null {
  let token = localStorage.getItem('predixen-token');
  if (!token) {
    try {
      const raw = localStorage.getItem('predixen-founder-storage');
      if (raw) {
        const parsed = JSON.parse(raw);
        token = parsed?.state?.token || null;
        if (token) {
          localStorage.setItem('predixen-token', token);
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

    const totalExpenses = c.totalExpenses || effectiveExpenses || 0;
    const isProfitable = totalExpenses > 0 && mrr >= totalExpenses;
    const hasData = mrr > 0 || cashOnHand > 0 || netBurn > 0;

    return {
      mrr, arr, cashOnHand, burnRate, netBurn, runway, runwayDisplay,
      cac, ltv, ltvCacRatio,
      grossMargin: grossMarginDecimal, grossMarginPct,
      churnRate: churnRateDecimal, churnRatePct,
      totalCustomers, headcount, arpu, paybackPeriod,
      burnMultiple, revenuePerEmployee, isProfitable, hasData,
    };
  }, [computed, truthScan?.metrics, financialBaseline, currentCompany, backendBaseline]);

  const isLoading = !companyId || (computedLoading && !computed);

  return { metrics, isLoading };
}
