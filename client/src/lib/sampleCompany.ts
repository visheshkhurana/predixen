/**
 * Canonical sample-company snapshot for the signup → first-insight path.
 * Keep in lockstep with server/services/sample_data.py.
 *
 * Burn and runway use the same formula as GET /metrics/computed:
 * expenses = opex + payroll + other; burn = expenses − revenue;
 * runway = cash / burn (1 decimal).
 */

export const SAMPLE_COMPANY = {
  name: 'Sample SaaS Co.',
  website: 'https://example.com',
  industry: 'general_saas',
  stage: 'seed',
  currency: 'USD',
  amount_scale: 'UNITS' as const,
};

export const SAMPLE_FINANCIALS = {
  monthly_revenue: 45000,
  gross_margin_pct: 75,
  opex: 22000,
  payroll: 40000,
  other_costs: 10000,
  cash_balance: 750000,
  headcount: 12,
};

export type SampleInsight = {
  inputs: {
    monthly_revenue: number;
    monthly_expenses: number;
    cash_balance: number;
  };
  outputs: {
    monthly_burn: number;
    runway_months: number | null;
  };
};

export function sampleMonthlyExpenses(
  fin: Pick<typeof SAMPLE_FINANCIALS, 'opex' | 'payroll' | 'other_costs'> = SAMPLE_FINANCIALS,
): number {
  return fin.opex + fin.payroll + fin.other_costs;
}

export function deriveSampleInsight(
  fin: typeof SAMPLE_FINANCIALS = SAMPLE_FINANCIALS,
): SampleInsight {
  const monthly_expenses = sampleMonthlyExpenses(fin);
  const monthly_burn = monthly_expenses - fin.monthly_revenue;
  const runway_months =
    monthly_burn > 0 && fin.cash_balance > 0
      ? Math.round((fin.cash_balance / monthly_burn) * 10) / 10
      : null;
  return {
    inputs: {
      monthly_revenue: fin.monthly_revenue,
      monthly_expenses,
      cash_balance: fin.cash_balance,
    },
    outputs: {
      monthly_burn,
      runway_months,
    },
  };
}

export function isSampleCompany(
  company?: { is_sample?: boolean } | null,
): boolean {
  return !!company?.is_sample;
}
