import { useMemo } from 'react';
import { useFounderStore } from '@/store/founderStore';
import { useTruthScan } from '@/api/hooks';

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
  const { data: truthScan, isLoading } = useTruthScan(currentCompany?.id || null);

  const metrics = useMemo(() => {
    const ts = truthScan?.metrics || {};

    const baselineRevenue = financialBaseline?.monthlyRevenue ?? 0;
    const baselineCash = financialBaseline?.cashOnHand ?? 0;
    const baselineTotalExpenses = financialBaseline?.totalMonthlyExpenses ?? 0;

    const breakdownSum =
      (financialBaseline?.expenseBreakdown?.payroll || 0) +
      (financialBaseline?.expenseBreakdown?.marketing || 0) +
      (financialBaseline?.expenseBreakdown?.operating || 0) +
      (financialBaseline?.expenseBreakdown?.cogs || 0) +
      (financialBaseline?.expenseBreakdown?.otherOpex || 0);

    const effectiveExpenses = financialBaseline?.hasManualExpenseOverride
      ? baselineTotalExpenses
      : (breakdownSum > 0 ? breakdownSum : baselineTotalExpenses);

    const baselineNetBurn = Math.max(0, effectiveExpenses - baselineRevenue);
    const baselineCogs = financialBaseline?.expenseBreakdown?.cogs ?? 0;

    const pick = (tsKey: string, fallback: number): number => {
      const tsVal = extractTruthScanValue(ts, tsKey);
      if (tsVal !== null && tsVal > 0) return tsVal;
      return fallback;
    };

    const pickAllowZero = (tsKey: string, fallback: number): number => {
      const tsVal = extractTruthScanValue(ts, tsKey);
      if (tsVal !== null) return tsVal;
      return fallback;
    };

    const mrr = pick('mrr', baselineRevenue);
    const arr = pick('arr', mrr * 12);
    const cashOnHand = pick('cash_balance', pick('cash', baselineCash));
    const netBurn = pick('net_burn', pick('monthly_burn', baselineNetBurn));
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
      runway = cashOnHand / netBurn;
      runway = Math.min(runway, 120);
      runwayDisplay = `${runway.toFixed(1)} mo`;
    }

    const cac = pick('cac', 0);
    const ltv = pick('ltv', 0);

    const ltvCacRatio = cac > 0 && ltv > 0 ? ltv / cac : 0;

    const baselineGrossMarginDecimal = baselineRevenue > 0
      ? (baselineRevenue - baselineCogs) / baselineRevenue
      : 0;

    const tsGrossMargin = extractTruthScanValue(ts, 'gross_margin');
    let grossMarginDecimal: number;
    if (tsGrossMargin !== null && tsGrossMargin > 0) {
      grossMarginDecimal = tsGrossMargin > 1 ? tsGrossMargin / 100 : tsGrossMargin;
    } else {
      grossMarginDecimal = baselineGrossMarginDecimal;
    }
    const grossMarginPct = grossMarginDecimal * 100;

    const tsChurn = extractTruthScanValue(ts, 'churn_rate');
    let churnRateDecimal: number;
    if (tsChurn !== null) {
      churnRateDecimal = tsChurn > 1 ? tsChurn / 100 : tsChurn;
    } else {
      churnRateDecimal = 0;
    }
    const churnRatePct = churnRateDecimal * 100;

    const totalCustomers = pick('total_customers', pick('customers', 0));
    const headcount = pick('headcount', currentCompany ? (currentCompany as any).employees || 0 : 0);

    const arpu = totalCustomers > 0 ? mrr / totalCustomers : 0;

    let paybackPeriod: number;
    if (cac > 0 && arpu > 0 && grossMarginDecimal > 0) {
      paybackPeriod = cac / (arpu * grossMarginDecimal);
    } else if (cac > 0 && arpu > 0) {
      paybackPeriod = cac / arpu;
    } else {
      paybackPeriod = 0;
    }

    const monthlyGrowthRate = financialBaseline?.monthlyGrowthRate ?? 0;
    const newMRR = mrr * (monthlyGrowthRate / 100);
    const newARR = newMRR * 12;
    let burnMultiple: number;
    if (newARR > 0 && netBurn > 0) {
      burnMultiple = (netBurn * 12) / newARR;
    } else {
      burnMultiple = 0;
    }

    const revenuePerEmployee = headcount > 0 ? mrr / headcount : 0;

    const isProfitable = effectiveExpenses > 0 && baselineRevenue >= effectiveExpenses;

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
  }, [truthScan?.metrics, financialBaseline, currentCompany]);

  return { metrics, isLoading };
}
