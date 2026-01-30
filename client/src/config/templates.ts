export interface ScenarioTemplate {
  id: string;
  name: string;
  description: string;
  detailedAssumptions: string;
  tags: string[];
  deltas: {
    pricing_change_pct?: number;
    growth_uplift_pct?: number;
    burn_reduction_pct?: number;
    gross_margin_delta_pct?: number;
    churn_change_pct?: number;
    cac_change_pct?: number;
    fundraise_month?: number;
    fundraise_amount?: number;
  };
  baselineDiff?: string;
}

export const SCENARIO_TEMPLATES: ScenarioTemplate[] = [
  { 
    id: 'baseline',
    name: 'Baseline (Status Quo)', 
    description: 'No adjustments - serves as control',
    detailedAssumptions: 'Maintains current trajectory with no changes to pricing, growth rate, or burn. Use this as a reference point for comparing other scenarios.',
    tags: ['baseline'],
    deltas: { 
      pricing_change_pct: 0, 
      growth_uplift_pct: 0, 
      burn_reduction_pct: 0,
      gross_margin_delta_pct: 0,
      churn_change_pct: 0,
      cac_change_pct: 0
    },
    baselineDiff: 'Reference scenario'
  },
  { 
    id: 'conservative-cut',
    name: 'Conservative Cut', 
    description: 'Reduce burn while accepting slower growth',
    detailedAssumptions: 'Reduces operating expenses by 20% through hiring freeze and discretionary spend cuts. Accepts 5% slower revenue growth as a trade-off for extended runway.',
    tags: ['cost-cutting'],
    deltas: { 
      burn_reduction_pct: 20, 
      growth_uplift_pct: -5,
      gross_margin_delta_pct: 2,
      churn_change_pct: 0,
      cac_change_pct: -10
    },
    baselineDiff: '-20% expenses, -5% growth'
  },
  { 
    id: 'moderate-growth',
    name: 'Moderate Growth Push', 
    description: 'Balanced growth with efficiency gains',
    detailedAssumptions: 'Modest revenue growth increase of 15% through improved sales efficiency and marketing optimization. Reduces cost inefficiencies by 10% while maintaining team capacity.',
    tags: ['growth'],
    deltas: { 
      growth_uplift_pct: 15, 
      burn_reduction_pct: 10,
      gross_margin_delta_pct: 3,
      churn_change_pct: -5,
      cac_change_pct: -15
    },
    baselineDiff: '+15% growth, -10% inefficiencies'
  },
  { 
    id: 'aggressive-growth',
    name: 'Aggressive Growth', 
    description: 'Maximize growth with increased investment',
    detailedAssumptions: 'Increases marketing and hiring spend by 30% to accelerate growth by 40%. Higher burn rate but targets faster market capture. Best suited for companies with strong unit economics.',
    tags: ['growth'],
    deltas: { 
      growth_uplift_pct: 40, 
      burn_reduction_pct: -30,
      gross_margin_delta_pct: -2,
      churn_change_pct: 5,
      cac_change_pct: 20
    },
    baselineDiff: '+40% growth, +30% costs'
  },
  { 
    id: 'deep-cost-cut',
    name: 'Deep Cost Cutting', 
    description: 'Maximum cost reduction to extend runway',
    detailedAssumptions: 'Implements deep cost reductions of 30% through layoffs, office downsizing, and contract renegotiations. Revenue growth remains flat or minimal. Prioritizes survival over growth.',
    tags: ['cost-cutting'],
    deltas: { 
      burn_reduction_pct: 30, 
      growth_uplift_pct: -10,
      gross_margin_delta_pct: 5,
      churn_change_pct: 3,
      cac_change_pct: -25
    },
    baselineDiff: '-30% expenses, flat growth'
  },
  { 
    id: 'price-increase',
    name: 'Price Increase', 
    description: 'Raise prices to improve unit economics',
    detailedAssumptions: 'Increases product price by 15% to improve gross margin. Expects 5% reduction in growth rate due to price sensitivity. Net positive impact on revenue if churn remains stable.',
    tags: ['pricing'],
    deltas: { 
      pricing_change_pct: 15, 
      growth_uplift_pct: -5,
      gross_margin_delta_pct: 12,
      churn_change_pct: 8,
      cac_change_pct: 0
    },
    baselineDiff: '+15% price, +12% margin'
  },
  { 
    id: 'bridge-round',
    name: 'Bridge Round', 
    description: 'Small funding round to extend runway',
    detailedAssumptions: 'Raises $500K bridge round in month 3 to extend runway without major dilution. Provides 6-9 months additional runway depending on burn rate.',
    tags: ['fundraising'],
    deltas: { 
      fundraise_month: 3, 
      fundraise_amount: 500000,
      growth_uplift_pct: 0,
      burn_reduction_pct: 0
    },
    baselineDiff: '+$500K in Month 3'
  },
  { 
    id: 'series-funding',
    name: 'Series Funding', 
    description: 'Full funding round with growth investment',
    detailedAssumptions: 'Raises $2M series round in month 6. Enables aggressive growth strategy with 25% increased spend on sales and marketing.',
    tags: ['fundraising'],
    deltas: { 
      fundraise_month: 6, 
      fundraise_amount: 2000000,
      growth_uplift_pct: 25,
      burn_reduction_pct: -25
    },
    baselineDiff: '+$2M in Month 6, +25% growth'
  },
  { 
    id: 'best-case',
    name: 'Best Case', 
    description: 'Optimistic scenario with favorable conditions',
    detailedAssumptions: 'Assumes all initiatives succeed: 30% revenue growth improvement, 15% cost efficiency gains, and 20% improvement in gross margin through operational excellence.',
    tags: ['optimistic'],
    deltas: { 
      growth_uplift_pct: 30, 
      burn_reduction_pct: 15,
      gross_margin_delta_pct: 20,
      churn_change_pct: -15,
      cac_change_pct: -20
    },
    baselineDiff: '+30% growth, +15% efficiency'
  },
  { 
    id: 'worst-case',
    name: 'Worst Case', 
    description: 'Stress test with adverse conditions',
    detailedAssumptions: 'Models downside scenario: 20% revenue decline, 10% cost increase due to inflation, and 25% higher churn from market headwinds. Tests company resilience.',
    tags: ['pessimistic'],
    deltas: { 
      growth_uplift_pct: -20, 
      burn_reduction_pct: -10,
      gross_margin_delta_pct: -10,
      churn_change_pct: 25,
      cac_change_pct: 30
    },
    baselineDiff: '-20% growth, +10% costs'
  }
];

export const REQUIRED_FIELDS = [
  { key: 'cash_balance', label: 'Cash Balance', section: 'financials' },
  { key: 'monthly_revenue', label: 'Monthly Revenue', section: 'financials' },
  { key: 'total_expenses', label: 'Total Expenses', section: 'financials' },
  { key: 'gross_margin', label: 'Gross Margin', section: 'financials' },
  { key: 'monthly_burn', label: 'Monthly Burn', section: 'financials' },
];

export const METRIC_GLOSSARY: Record<string, { title: string; definition: string; formula?: string }> = {
  runway: {
    title: 'Runway',
    definition: 'The number of months your company can continue operating before running out of cash, assuming current burn rate continues.',
    formula: 'Runway = Cash Balance / Monthly Burn'
  },
  survival_probability: {
    title: 'Survival Probability',
    definition: 'The likelihood your company will still be operating at a given time horizon (e.g., 18 months), based on Monte Carlo simulation outcomes.',
    formula: 'Survival % = (Simulations with positive cash at month N) / Total Simulations'
  },
  burn_multiple: {
    title: 'Burn Multiple',
    definition: 'Measures efficiency by comparing how much you burn to how much net new ARR you generate. Lower is better; <1x is excellent, 1-2x is good, >3x needs attention.',
    formula: 'Burn Multiple = Net Burn / Net New ARR'
  },
  gross_margin: {
    title: 'Gross Margin',
    definition: 'The percentage of revenue remaining after subtracting cost of goods sold (COGS). Indicates pricing power and operational efficiency.',
    formula: 'Gross Margin = (Revenue - COGS) / Revenue × 100%'
  },
  composite_score: {
    title: 'Composite Score',
    definition: 'A weighted score combining runway (40%), survival probability (35%), and financial efficiency (25%) to rank scenarios.',
    formula: 'Score = 0.4×Runway + 0.35×Survival + 0.25×Efficiency'
  },
  p10_p50_p90: {
    title: 'P10 / P50 / P90',
    definition: 'Percentile outcomes from Monte Carlo simulation. P10 = pessimistic (10th percentile), P50 = median (50th), P90 = optimistic (90th percentile).',
  },
  net_burn: {
    title: 'Net Burn',
    definition: 'The net cash decrease per month after accounting for revenue. Negative net burn means you are cash-flow positive.',
    formula: 'Net Burn = Total Expenses - Revenue'
  },
  churn_rate: {
    title: 'Churn Rate',
    definition: 'The percentage of customers or revenue lost over a given period. High churn reduces growth efficiency and lifetime value.',
    formula: 'Churn Rate = Lost Customers / Starting Customers × 100%'
  },
  cac: {
    title: 'Customer Acquisition Cost (CAC)',
    definition: 'The total cost to acquire a new customer, including sales and marketing expenses.',
    formula: 'CAC = Total Sales & Marketing Spend / New Customers Acquired'
  }
};

export function getTemplateById(id: string): ScenarioTemplate | undefined {
  return SCENARIO_TEMPLATES.find(t => t.id === id);
}

export function getBaselineTemplate(): ScenarioTemplate {
  return SCENARIO_TEMPLATES.find(t => t.tags.includes('baseline')) || SCENARIO_TEMPLATES[0];
}

export function calculateDeltaVsBaseline(template: ScenarioTemplate, baselineTemplate: ScenarioTemplate): Record<string, number> {
  const deltas: Record<string, number> = {};
  const baseDeltas = baselineTemplate.deltas;
  const templateDeltas = template.deltas;
  
  for (const key of Object.keys(templateDeltas) as (keyof typeof templateDeltas)[]) {
    const templateVal = templateDeltas[key] ?? 0;
    const baseVal = baseDeltas[key] ?? 0;
    if (templateVal !== baseVal) {
      deltas[key] = templateVal - baseVal;
    }
  }
  
  return deltas;
}
