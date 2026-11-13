export interface FinancialState {
  monthlyRevenue: number;
  grossMargin: number;
  /** opex, payroll and otherCosts EXCLUDE COGS: COGS enters via grossMargin. */
  opex: number;
  payroll: number;
  otherCosts: number;
  cashBalance: number;
  churnRate: number;
  growthRate: number;
  cac: number;
  ltv: number;
  monthlyBurn?: number;
  /** Inputs the company has no data for; consumers show "not available". */
  unavailable?: string[];
}

export interface MetricsForFinancialState {
  mrr?: number | null;
  cashOnHand?: number | null;
  burnRate?: number | null; // NET burn
  totalMonthlyExpenses?: number | null; // total costs incl. COGS
  grossMarginPct?: number | null;
  monthlyGrowthRate?: number | null;
  churnRatePct?: number | null;
  cac?: number | null;
  ltv?: number | null;
  expenseBreakdown?: { payroll?: number; operating?: number; marketing?: number; otherOpex?: number } | null;
}

function finite(v: number | null | undefined): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

/**
 * Dashboard metrics -> what-if / stress state, on the canonical burn.
 *
 * The old builder split TOTAL expenses (COGS included) into opex/payroll/other
 * and then also charged COGS through a 70% default margin, so COGS was counted
 * twice; it used net burn as total expenses when expenses were missing; and it
 * invented growth 10%, churn 5%, CAC 500, LTV 5000. Now:
 *  - total costs = reported total expenses, else net burn + revenue;
 *  - cost lines = total - revenue * (1 - margin), so runway equals the
 *    dashboard's cash / net burn;
 *  - unknown margin -> 100% (COGS is then carried as a fixed cost, still exact
 *    at today's revenue) and listed in `unavailable`;
 *  - the split follows the real expense breakdown when present, else all opex;
 *  - unknown growth/churn/CAC/LTV are 0 and listed in `unavailable`.
 */
export function financialStateFromMetrics(metrics: MetricsForFinancialState): FinancialState {
  const unavailable: string[] = [];
  const revenue = finite(metrics.mrr) ? Math.max(0, metrics.mrr) : 0;
  const net = finite(metrics.burnRate) ? metrics.burnRate : null;
  const reportedTotal = finite(metrics.totalMonthlyExpenses) && metrics.totalMonthlyExpenses > 0
    ? metrics.totalMonthlyExpenses : null;
  // Net burn is clamped at 0 on the dashboard, so it only reconstructs total
  // costs while the company is burning.
  const totalCosts = net !== null && net > 0 ? net + revenue : (reportedTotal ?? Math.max(0, net ?? 0) + revenue);

  let grossMargin: number;
  if (finite(metrics.grossMarginPct) && metrics.grossMarginPct !== 0) {
    grossMargin = metrics.grossMarginPct;
  } else {
    grossMargin = 100;
    if (revenue > 0) unavailable.push('grossMargin');
  }
  const costsExCogs = Math.max(0, totalCosts - revenue * (1 - grossMargin / 100));

  const b = metrics.expenseBreakdown;
  const payrollPart = Math.max(0, b?.payroll ?? 0);
  const opexPart = Math.max(0, (b?.operating ?? 0) + (b?.marketing ?? 0));
  const otherPart = Math.max(0, b?.otherOpex ?? 0);
  const partSum = payrollPart + opexPart + otherPart;
  let opex = costsExCogs, payroll = 0, otherCosts = 0;
  if (partSum > 0) {
    opex = costsExCogs * (opexPart / partSum);
    payroll = costsExCogs * (payrollPart / partSum);
    otherCosts = costsExCogs * (otherPart / partSum);
  } else {
    unavailable.push('payroll');
  }

  const orUnavailable = (key: string, v: number | null | undefined, positiveOnly = false): number => {
    if (finite(v) && (positiveOnly ? v > 0 : v !== 0)) return v;
    unavailable.push(key);
    return 0;
  };

  return {
    cashBalance: finite(metrics.cashOnHand) ? metrics.cashOnHand : 0,
    monthlyRevenue: revenue,
    monthlyBurn: Math.max(0, totalCosts - revenue),
    growthRate: orUnavailable('growthRate', metrics.monthlyGrowthRate),
    churnRate: orUnavailable('churnRate', metrics.churnRatePct),
    grossMargin,
    opex,
    payroll,
    otherCosts,
    cac: orUnavailable('cac', metrics.cac, true),
    ltv: orUnavailable('ltv', metrics.ltv, true),
    unavailable,
  };
}

export interface SensitivityResult {
  name: string;
  displayName: string;
  baseValue: number;
  unit: string;
  lowImpact: number;
  highImpact: number;
  currentValue: number;
}

export const RUNWAY_SUSTAINABLE = 900;
export const RUNWAY_DISPLAY_CAP = 120;

export function calculateRunway(state: FinancialState): number {
  const monthlyGrossProfit = state.monthlyRevenue * (state.grossMargin / 100);
  const totalExpenses = state.opex + state.payroll + state.otherCosts;
  const netBurn = totalExpenses - monthlyGrossProfit;
  
  if (netBurn <= 0) return RUNWAY_SUSTAINABLE;
  const runway = state.cashBalance / netBurn;
  return Math.min(runway, RUNWAY_SUSTAINABLE);
}

export function calculateStressedRunway(
  state: FinancialState,
  durationMonths: number = 24
): number {
  let cash = state.cashBalance;
  let revenue = state.monthlyRevenue;
  const growthRate = (state.growthRate || 0) / 100;
  const churnRate = (state.churnRate || 0) / 100;
  const grossMargin = state.grossMargin / 100;
  const totalExpenses = state.opex + state.payroll + state.otherCosts;

  const maxProjection = Math.max(durationMonths, 60);
  for (let m = 0; m < maxProjection; m++) {
    const grossProfit = revenue * grossMargin;
    const netBurn = totalExpenses - grossProfit;
    cash -= netBurn;
    if (cash <= 0) return m;
    revenue *= (1 + growthRate - churnRate);
    if (revenue < 0) revenue = 0;
  }

  const finalGrossProfit = revenue * grossMargin;
  const finalNetBurn = totalExpenses - finalGrossProfit;
  if (finalNetBurn <= 0) return RUNWAY_SUSTAINABLE;
  const extraMonths = cash / finalNetBurn;
  return Math.min(maxProjection + extraMonths, RUNWAY_SUSTAINABLE);
}

export function formatRunwayDisplay(months: number): string {
  if (months >= RUNWAY_SUSTAINABLE) return 'Sustainable';
  if (months >= RUNWAY_DISPLAY_CAP) return '120+ mo';
  const fixed = months.toFixed(1);
  return `${fixed.replace(/\.0$/, '')} mo`;
}

export function isSustainable(runway: number): boolean {
  return runway >= RUNWAY_SUSTAINABLE;
}

export function calculateSensitivity(
  baseState: FinancialState,
  percentSwing: number = 20
): SensitivityResult[] {
  const baseRunway = calculateRunway(baseState);
  
  const variables = [
    { name: 'churnRate', displayName: 'Churn Rate', key: 'churnRate', unit: '%', invert: true },
    { name: 'cac', displayName: 'Customer Acquisition Cost', key: 'cac', unit: 'currency', invert: true },
    { name: 'growthRate', displayName: 'Revenue Growth Rate', key: 'growthRate', unit: '%', invert: false },
    { name: 'grossMargin', displayName: 'Gross Margin', key: 'grossMargin', unit: '%', invert: false },
    { name: 'payroll', displayName: 'Payroll Costs', key: 'payroll', unit: 'currency', invert: true },
    { name: 'opex', displayName: 'Operating Expenses', key: 'opex', unit: 'currency', invert: true },
  ];

  // calculateRunway is cash / (costs - revenue * margin): churn, CAC and
  // growth do not enter it, so their bars were always zero -- which read as
  // "does not matter". Leave them out, and leave out inputs with no data.
  const modelled = new Set(['grossMargin', 'payroll', 'opex']);
  const unavailable = new Set(baseState.unavailable ?? []);
  return variables.filter(v => modelled.has(v.key) && !unavailable.has(v.key)).map(v => {
    const baseValue = baseState[v.key as keyof FinancialState] as number;
    
    // Calculate impact when variable decreases by percentSwing%
    const lowState = { ...baseState, [v.key]: baseValue * (1 - percentSwing / 100) };
    const lowRunway = calculateRunway(lowState);
    const lowImpact = lowRunway - baseRunway;
    
    // Calculate impact when variable increases by percentSwing%
    const highState = { ...baseState, [v.key]: baseValue * (1 + percentSwing / 100) };
    const highRunway = calculateRunway(highState);
    const highImpact = highRunway - baseRunway;

    return {
      name: v.name,
      displayName: v.displayName,
      baseValue,
      unit: v.unit,
      lowImpact: v.invert ? highImpact : lowImpact,
      highImpact: v.invert ? lowImpact : highImpact,
      currentValue: baseValue,
    };
  });
}

export interface WhatIfResults {
  runway: number;
  runwayChange: number;
  survival18m: number;
  survivalChange: number;
  cashAt18m: number;
  cashChange: number;
}

export function calculateWhatIfImpact(
  baseState: FinancialState,
  adjustments: Record<string, number>,
  baselineResults: { runway: number; survival18m: number; cashAt18m: number }
): WhatIfResults {
  const adjustedState = { ...baseState };
  
  if (adjustments.revenueGrowth !== undefined) {
    adjustedState.growthRate = adjustments.revenueGrowth;
  }
  if (adjustments.churnRate !== undefined) {
    adjustedState.churnRate = adjustments.churnRate;
  }
  if (adjustments.grossMargin !== undefined) {
    adjustedState.grossMargin = adjustments.grossMargin;
  }
  if (adjustments.burnChange !== undefined) {
    const burnMultiplier = 1 + (adjustments.burnChange / 100);
    adjustedState.opex *= burnMultiplier;
    adjustedState.payroll *= burnMultiplier;
  }
  if (adjustments.fundraising !== undefined && adjustments.fundraising > 0) {
    adjustedState.cashBalance += adjustments.fundraising;
  }

  const newRunway = calculateRunway(adjustedState);
  
  // Simplified survival calculation based on runway
  const survival18m = Math.min(100, Math.max(0, (newRunway / 18) * 100));
  
  // Calculate ending cash at 18 months
  const monthlyGrossProfit = adjustedState.monthlyRevenue * (adjustedState.grossMargin / 100);
  const totalExpenses = adjustedState.opex + adjustedState.payroll + adjustedState.otherCosts;
  const netBurn = totalExpenses - monthlyGrossProfit;
  const cashAt18m = Math.max(0, adjustedState.cashBalance - (netBurn * 18));

  return {
    runway: newRunway,
    runwayChange: newRunway - baselineResults.runway,
    survival18m,
    survivalChange: survival18m - baselineResults.survival18m,
    cashAt18m,
    cashChange: cashAt18m - baselineResults.cashAt18m,
  };
}
