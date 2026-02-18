export interface FinancialState {
  monthlyRevenue: number;
  grossMargin: number;
  opex: number;
  payroll: number;
  otherCosts: number;
  cashBalance: number;
  churnRate: number;
  growthRate: number;
  cac: number;
  ltv: number;
  monthlyBurn?: number;
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

export const RUNWAY_SUSTAINABLE = 999;
export const RUNWAY_DISPLAY_CAP = 120;

export function calculateRunway(state: FinancialState): number {
  const monthlyGrossProfit = state.monthlyRevenue * (state.grossMargin / 100);
  const totalExpenses = state.opex + state.payroll + state.otherCosts;
  const netBurn = totalExpenses - monthlyGrossProfit;
  
  if (netBurn <= 0) return RUNWAY_SUSTAINABLE;
  const runway = state.cashBalance / netBurn;
  return Math.min(runway, RUNWAY_SUSTAINABLE);
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

  return variables.map(v => {
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
