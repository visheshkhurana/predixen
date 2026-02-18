/**
 * finance.ts - SINGLE SOURCE OF TRUTH for runway, burn rate, and forecast calculations.
 * Phase 2 fix for P0 #1 (forecast explosion) and P0 #2 (runway inconsistency).
 * 
 * ALL pages (Dashboard, Simulate, Decisions, Health Check) MUST use these functions.
 */

/** Maximum reasonable monthly growth rate (100% = doubling each month) */
const MAX_MONTHLY_GROWTH_RATE = 1.0;

/** Maximum reasonable forecast value (1 trillion) */
const MAX_FORECAST_VALUE = 1_000_000_000_000;

/**
 * CANONICAL runway calculation.
 * @param cashBalance - Current cash on hand (in whatever unit scale)
 * @param totalMonthlyExpenses - Total monthly expenses (same unit scale)
 * @param monthlyRevenue - Monthly revenue (same unit scale)
 * @returns Runway in months, or null if sustainable/infinite
 */
export function calculateRunway(
  cashBalance: number | null | undefined,
  totalMonthlyExpenses: number | null | undefined,
  monthlyRevenue: number | null | undefined,
): number | null {
  const cash = cashBalance ?? 0;
  const expenses = totalMonthlyExpenses ?? 0;
  const rev = monthlyRevenue ?? 0;

  const netBurn = expenses - rev;

  // If profitable or break-even, runway is infinite
  if (netBurn <= 0) return null;

  // If no cash, runway is 0
  if (cash <= 0) return 0;

  return Math.round((cash / netBurn) * 10) / 10; // Round to 1 decimal
}

/**
 * CANONICAL monthly burn rate calculation.
 * Positive = burning cash, negative = generating cash (profitable).
 */
export function calculateMonthlyBurn(
  totalMonthlyExpenses: number | null | undefined,
  monthlyRevenue: number | null | undefined,
): number {
  const expenses = totalMonthlyExpenses ?? 0;
  const rev = monthlyRevenue ?? 0;
  return expenses - rev;
}

/**
 * CANONICAL net burn rate (always positive or zero for display).
 */
export function calculateNetBurnRate(
  totalMonthlyExpenses: number | null | undefined,
  monthlyRevenue: number | null | undefined,
): number {
  return Math.max(0, calculateMonthlyBurn(totalMonthlyExpenses, monthlyRevenue));
}

/**
 * Clamp and validate a growth rate for use in forecasting.
 * Input: raw percentage (e.g., 5 for 5%, or 1268 for 1268%)
 * Output: clamped monthly rate as a decimal (e.g., 0.05 for 5%)
 */
export function clampGrowthRate(rawPercentage: number | null | undefined): number {
  if (rawPercentage == null || isNaN(rawPercentage)) return 0.05; // default 5%
  
  let rate = rawPercentage;
  
  // Input is always a percentage (e.g., 5 for 5%). Convert to decimal.
  // Do NOT try to auto-detect decimals — that turns 0.5% into 50%.
  const decimal = rate / 100;
  
  // Clamp to reasonable range: -50% to +100% monthly
  return Math.max(-0.5, Math.min(MAX_MONTHLY_GROWTH_RATE, decimal));
}

/**
 * CANONICAL cash flow forecast calculation.
 * Fixes P0 #1: no more exponential explosion.
 * 
 * @param monthlyRevenue - Current monthly revenue
 * @param baseExpenses - Current total monthly expenses
 * @param cashOnHand - Current cash balance
 * @param monthlyGrowthPct - Revenue growth rate as percentage (e.g., 5 for 5%)
 * @param months - Number of months to forecast (default 12)
 * @param expenseGrowthPct - Expense growth rate as percentage (default 2%)
 */
export function calculateCashFlowForecast(
  monthlyRevenue: number,
  baseExpenses: number,
  cashOnHand: number,
  monthlyGrowthPct: number = 5,
  months: number = 12,
  expenseGrowthPct: number = 2,
): Array<{
  month: number;
  inflow: number;
  outflow: number;
  net: number;
  cash_balance: number;
}> {
  const growthRate = clampGrowthRate(monthlyGrowthPct);
  const expenseGrowthRate = clampGrowthRate(expenseGrowthPct);

  const forecast: Array<{
    month: number;
    inflow: number;
    outflow: number;
    net: number;
    cash_balance: number;
  }> = [];

  let currentCash = cashOnHand;

  for (let month = 1; month <= months; month++) {
    // Revenue grows by growth rate each month (compound)
    let projectedRevenue = monthlyRevenue * Math.pow(1 + growthRate, month);
    
    // Expenses grow by expense growth rate each month
    let projectedExpenses = baseExpenses * Math.pow(1 + expenseGrowthRate, month);

    // Sanity clamp: prevent astronomical values
    projectedRevenue = Math.min(projectedRevenue, MAX_FORECAST_VALUE);
    projectedExpenses = Math.min(projectedExpenses, MAX_FORECAST_VALUE);

    const netFlow = projectedRevenue - projectedExpenses;
    currentCash += netFlow;

    // Clamp current cash to reasonable bounds
    currentCash = Math.max(-MAX_FORECAST_VALUE, Math.min(MAX_FORECAST_VALUE, currentCash));

    forecast.push({
      month,
      inflow: Math.round(projectedRevenue),
      outflow: Math.round(projectedExpenses),
      net: Math.round(netFlow),
      cash_balance: Math.round(currentCash),
    });
  }

  return forecast;
}

/**
 * Format runway for display.
 * @param runwayMonths - Result from calculateRunway()
 * @returns Human-readable string like "11.8 months" or "Sustainable"
 */
export function formatRunway(runwayMonths: number | null): string {
  if (runwayMonths === null) return 'Sustainable';
  if (runwayMonths === 0) return '0 months';
  if (runwayMonths >= 120) return '10+ years';
  if (runwayMonths >= 24) {
    const years = Math.round(runwayMonths / 12 * 10) / 10;
    return `${years} years`;
  }
  return `${runwayMonths.toFixed(1)} months`;
}

/**
 * Normalize a gross margin value to always be 0-100 percentage.
 * Handles both cases: stored as 0.90 (decimal) or 90 (percentage).
 */
export function normalizeGrossMarginPct(value: number | null | undefined): number | null {
  if (value == null || isNaN(value)) return null;
  
  // If value is between 0 and 1 (inclusive of boundaries), it's likely a decimal fraction
  if (value >= 0 && value <= 1) {
    return value * 100;
  }
  
  // If it's already in percentage form (e.g., 90 for 90%)
  return value;
}
