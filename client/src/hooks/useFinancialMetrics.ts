import { useMemo } from 'react';
import { useFounderStore } from '@/store/founderStore';
import { useTruthScan } from '@/api/hooks';
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
  const { data: truthScan, isLoading: tsLoading } = useTruthScan(companyId);

  const { data: backendBaseline, isLoading: baselineLoading } = useQuery<any>({
    queryKey: ['/api/companies', companyId, 'financials/baseline'],
    enabled: !!companyId,
    staleTime: 30_000,
  });

  const isLoading = tsLoading || baselineLoading;

  const metrics = useMemo(() => {
    const ts = truthScan?.metrics || {};
    const bb = backendBaseline?.baseline;
    const ext = backendBaseline?.extendedMetrics;

    const baselineRevenue = bb?.monthlyRevenue ?? financialBaseline?.monthlyRevenue ?? 0;
    const baselineCash = bb?.cashOnHand ?? financialBaseline?.cashOnHand ?? 0;
    const baselineTotalExpenses = bb?.totalMonthlyExpenses ?? financialBaseline?.totalMonthlyExpenses ?? 0;

    const breakdownPayroll = bb?.expenseBreakdown?.payroll ?? financialBaseline?.expenseBreakdown?.payroll ?? 0;
    const breakdownMarketing = bb?.expenseBreakdown?.marketing ?? financialBaseline?.expenseBreakdown?.marketing ?? 0;
    const breakdownOperating = bb?.expenseBreakdown?.operating ?? financialBaseline?.expenseBreakdown?.operating ?? 0;
    const breakdownCogs = bb?.expenseBreakdown?.cogs ?? financialBaseline?.expenseBreakdown?.cogs ?? 0;
    const breakdownOther = bb?.expenseBreakdown?.otherOpex ?? financialBaseline?.expenseBreakdown?.otherOpex ?? 0;

    const breakdownSum = breakdownPayroll + breakdownMarketing + breakdownOperating + breakdownCogs + breakdownOther;

    const hasManualOverride = financialBaseline?.hasManualExpenseOverride ?? false;
    const effectiveExpenses = hasManualOverride
      ? baselineTotalExpenses
      : (breakdownSum > 0 ? breakdownSum : baselineTotalExpenses);

    const baselineNetBurn = Math.max(0, effectiveExpenses - baselineRevenue);

    const mrr = baselineRevenue > 0 ? baselineRevenue : extractTruthScanValue(ts, 'mrr') ?? 0;
    const arr = mrr > 0 ? mrr * 12 : (extractTruthScanValue(ts, 'arr') ?? mrr * 12);
    const cashOnHand = baselineCash > 0 ? baselineCash : (extractTruthScanValue(ts, 'cash_balance') ?? extractTruthScanValue(ts, 'cash') ?? 0);
    const netBurn = baselineNetBurn > 0 ? baselineNetBurn : (extractTruthScanValue(ts, 'net_burn') ?? extractTruthScanValue(ts, 'monthly_burn') ?? 0);
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

    const extCac = ext?.cac ?? null;
    const extLtv = ext?.ltv ?? null;
    const extLtvCacRatio = ext?.ltvCacRatio ?? null;
    const tsCac = extractTruthScanValue(ts, 'cac');
    const tsLtv = extractTruthScanValue(ts, 'ltv');
    const tsLtvCacRatio = extractTruthScanValue(ts, 'ltv_cac_ratio');

    const cac = extCac ?? tsCac ?? 0;
    const ltv = extLtv ?? tsLtv ?? 0;
    const ltvCacRatio = extLtvCacRatio ?? tsLtvCacRatio ?? (cac > 0 && ltv > 0 ? ltv / cac : 0);

    let grossMarginDecimal: number;
    const extGrossMargin = ext?.grossMargin ?? null;
    const tsGrossMargin = extractTruthScanValue(ts, 'gross_margin');

    if (extGrossMargin !== null && extGrossMargin > 0) {
      grossMarginDecimal = extGrossMargin > 1 ? extGrossMargin / 100 : extGrossMargin;
    } else if (baselineRevenue > 0 && breakdownCogs >= 0) {
      grossMarginDecimal = (baselineRevenue - breakdownCogs) / baselineRevenue;
    } else if (tsGrossMargin !== null && tsGrossMargin > 0) {
      grossMarginDecimal = tsGrossMargin > 1 ? tsGrossMargin / 100 : tsGrossMargin;
    } else {
      grossMarginDecimal = 0;
    }
    const grossMarginPct = grossMarginDecimal * 100;

    const tsChurn = extractTruthScanValue(ts, 'churn_rate') ?? extractTruthScanValue(ts, 'gross_churn_rate');
    let churnRateDecimal: number;
    if (tsChurn !== null) {
      churnRateDecimal = tsChurn > 1 ? tsChurn / 100 : tsChurn;
    } else {
      churnRateDecimal = 0;
    }
    const churnRatePct = churnRateDecimal * 100;

    const extCustomers = ext?.customers ?? null;
    const tsCustomers = extractTruthScanValue(ts, 'customer_count') ?? extractTruthScanValue(ts, 'total_customers') ?? extractTruthScanValue(ts, 'customers');
    const totalCustomers = extCustomers ?? tsCustomers ?? 0;

    const extHeadcount = ext?.headcount ?? null;
    const tsHeadcount = extractTruthScanValue(ts, 'headcount');
    const headcount = extHeadcount ?? tsHeadcount ?? (currentCompany ? (currentCompany as any).employees || 0 : 0);

    const arpu = totalCustomers > 0 ? mrr / totalCustomers : 0;

    let paybackPeriod: number;
    if (cac > 0 && arpu > 0 && grossMarginDecimal > 0) {
      paybackPeriod = cac / (arpu * grossMarginDecimal);
    } else if (cac > 0 && arpu > 0) {
      paybackPeriod = cac / arpu;
    } else {
      paybackPeriod = 0;
    }

    const monthlyGrowthRate = bb?.monthlyGrowthRate ?? financialBaseline?.monthlyGrowthRate ?? 0;
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
  }, [truthScan?.metrics, financialBaseline, currentCompany, backendBaseline]);

  return { metrics, isLoading };
}
