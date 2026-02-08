import { useMemo } from 'react';
import { useFounderStore } from '@/store/founderStore';
import { useTruthScan, useComputedMetrics } from '@/api/hooks';
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

function extractTruthScanValue(metrics: Record<string, any>, key: string): number | null {
  const val = metrics[key];
  if (val === null || val === undefined) return null;
  if (typeof val === 'object' && 'value' in val) {
    return val.value ?? null;
  }
  if (typeof val === 'number') return val;
  return null;
}

export function useFinancialMetrics(): { metrics: FinancialMetrics; isLoading: boolean } {
  const { currentCompany, financialBaseline } = useFounderStore();
  const companyId = currentCompany?.id ?? null;

  const { data: computed, isLoading: computedLoading, error: computedError } = useComputedMetrics(companyId);

  const { data: truthScan, isLoading: tsLoading, error: tsError } = useTruthScan(companyId);

  const { data: backendBaseline, isLoading: baselineLoading, error: baselineError } = useQuery<any>({
    queryKey: ['/api/companies', companyId, 'financials', 'baseline'],
    enabled: !!companyId,
    staleTime: 60_000,
  });

  if (companyId && (computedError || tsError || baselineError)) {
    console.warn('[useFinancialMetrics] Query errors:', {
      computed: computedError?.message,
      truthScan: tsError?.message,
      baseline: baselineError?.message,
      companyId,
    });
  }

  const isLoading = computedLoading && tsLoading && baselineLoading;

  const metrics = useMemo(() => {
    const c = computed || {};
    const ts = truthScan?.metrics || {};
    const bb = backendBaseline?.baseline;
    const ext = backendBaseline?.extendedMetrics;

    if (companyId) {
      console.log('[useFinancialMetrics] Data state:', {
        hasComputed: !!computed,
        computedLtv: c.ltv,
        hasTruthScan: !!truthScan,
        tsLtv: ts?.ltv,
        hasBaseline: !!backendBaseline,
        extLtv: ext?.ltv,
      });
    }

    const pick = (...vals: (number | null | undefined)[]) => {
      for (const v of vals) {
        if (v !== null && v !== undefined && v > 0) return v;
      }
      return 0;
    };

    const mrr = pick(
      c.mrr,
      bb?.monthlyRevenue,
      financialBaseline?.monthlyRevenue,
      extractTruthScanValue(ts, 'mrr')
    );
    const arr = pick(c.arr, ext?.arr, extractTruthScanValue(ts, 'arr')) || mrr * 12;
    const cashOnHand = pick(
      c.cashOnHand,
      bb?.cashOnHand,
      financialBaseline?.cashOnHand,
      extractTruthScanValue(ts, 'cash_balance')
    );

    const breakdownPayroll = bb?.expenseBreakdown?.payroll ?? financialBaseline?.expenseBreakdown?.payroll ?? 0;
    const breakdownMarketing = bb?.expenseBreakdown?.marketing ?? financialBaseline?.expenseBreakdown?.marketing ?? 0;
    const breakdownOperating = bb?.expenseBreakdown?.operating ?? financialBaseline?.expenseBreakdown?.operating ?? 0;
    const breakdownCogs = bb?.expenseBreakdown?.cogs ?? financialBaseline?.expenseBreakdown?.cogs ?? 0;
    const breakdownOther = bb?.expenseBreakdown?.otherOpex ?? financialBaseline?.expenseBreakdown?.otherOpex ?? 0;
    const breakdownSum = breakdownPayroll + breakdownMarketing + breakdownOperating + breakdownCogs + breakdownOther;

    const hasManualOverride = financialBaseline?.hasManualExpenseOverride ?? false;
    const baselineTotalExpenses = bb?.totalMonthlyExpenses ?? financialBaseline?.totalMonthlyExpenses ?? 0;
    const effectiveExpenses = hasManualOverride
      ? baselineTotalExpenses
      : (breakdownSum > 0 ? breakdownSum : baselineTotalExpenses);

    const netBurn = pick(
      c.netBurn,
      effectiveExpenses > 0 && mrr > 0 ? Math.max(0, effectiveExpenses - mrr) : null,
      extractTruthScanValue(ts, 'net_burn')
    );
    const burnRate = netBurn;

    let runway: number;
    let runwayDisplay: string;
    const computedRunway = c.runway;
    if (computedRunway && computedRunway > 0 && computedRunway < 999) {
      runway = computedRunway;
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

    const cac = pick(c.cac, ext?.cac, extractTruthScanValue(ts, 'cac'));
    const ltv = pick(c.ltv, ext?.ltv, extractTruthScanValue(ts, 'ltv'));
    const ltvCacRatio = pick(
      c.ltvCacRatio,
      ext?.ltvCacRatio,
      extractTruthScanValue(ts, 'ltv_cac_ratio')
    ) || (cac > 0 && ltv > 0 ? ltv / cac : 0);

    const grossMarginPct = pick(
      c.grossMarginPct,
      ext?.grossMargin ? (ext.grossMargin > 1 ? ext.grossMargin : ext.grossMargin * 100) : null,
      extractTruthScanValue(ts, 'gross_margin') ? (
        (extractTruthScanValue(ts, 'gross_margin') as number) > 1
          ? extractTruthScanValue(ts, 'gross_margin')
          : (extractTruthScanValue(ts, 'gross_margin') as number) * 100
      ) : null
    );
    const grossMarginDecimal = c.grossMarginDecimal || grossMarginPct / 100;

    const churnRatePct = pick(
      c.churnRatePct,
      extractTruthScanValue(ts, 'churn_rate') !== null ? (
        (extractTruthScanValue(ts, 'churn_rate') as number) > 1
          ? extractTruthScanValue(ts, 'churn_rate')
          : (extractTruthScanValue(ts, 'churn_rate') as number) * 100
      ) : null,
      extractTruthScanValue(ts, 'gross_churn_rate') !== null ? (
        (extractTruthScanValue(ts, 'gross_churn_rate') as number) > 1
          ? extractTruthScanValue(ts, 'gross_churn_rate')
          : (extractTruthScanValue(ts, 'gross_churn_rate') as number) * 100
      ) : null
    );
    const churnRateDecimal = churnRatePct / 100;

    const totalCustomers = pick(c.totalCustomers, ext?.customers, extractTruthScanValue(ts, 'customer_count'), extractTruthScanValue(ts, 'total_customers'));
    const headcount = pick(c.headcount, ext?.headcount, extractTruthScanValue(ts, 'headcount')) || (currentCompany ? (currentCompany as any).employees || 0 : 0);
    const arpu = pick(c.arpu) || (totalCustomers > 0 ? mrr / totalCustomers : 0);

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

    const burnMultiple = pick(c.burnMultiple, ext?.burnMultiple, extractTruthScanValue(ts, 'burn_multiple'));
    const revenuePerEmployee = headcount > 0 ? mrr / headcount : 0;

    const totalExpenses = c.totalExpenses || effectiveExpenses || 0;
    const isProfitable = totalExpenses > 0 && mrr >= totalExpenses;

    const hasData = mrr > 0 || cashOnHand > 0 || netBurn > 0;

    return {
      mrr,
      arr,
      cashOnHand,
      burnRate,
      netBurn,
      runway,
      runwayDisplay,
      cac,
      ltv,
      ltvCacRatio,
      grossMargin: grossMarginDecimal,
      grossMarginPct,
      churnRate: churnRateDecimal,
      churnRatePct,
      totalCustomers,
      headcount,
      arpu,
      paybackPeriod,
      burnMultiple,
      revenuePerEmployee,
      isProfitable,
      hasData,
    };
  }, [computed, truthScan?.metrics, financialBaseline, currentCompany, backendBaseline]);

  return { metrics, isLoading };
}
