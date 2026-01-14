import { Info, TrendingUp, TrendingDown, DollarSign, Percent, Clock, Users, PieChart, Target } from 'lucide-react';

export interface MetricDefinition {
  key: string;
  displayName: string;
  shortDescription: string;
  longDescription: string;
  formula?: string;
  whyItMatters: string;
  benchmarkContext?: string;
  direction: 'higher_is_better' | 'lower_is_better';
  category: 'revenue' | 'profitability' | 'efficiency' | 'growth' | 'cash' | 'customer';
  icon: typeof Info;
}

export const METRIC_DEFINITIONS: Record<string, MetricDefinition> = {
  mrr: {
    key: 'mrr',
    displayName: 'Monthly Recurring Revenue',
    shortDescription: 'Total predictable revenue earned each month',
    longDescription: 'Monthly Recurring Revenue (MRR) is the sum of all recurring subscription revenue normalized to a monthly amount. It excludes one-time fees, variable usage charges, and non-recurring revenue.',
    formula: 'MRR = Sum of (Monthly Subscription Value for All Active Customers)',
    whyItMatters: 'MRR is the foundation of SaaS valuation. Investors use it to assess business scale and calculate growth rates. A higher MRR indicates stronger product-market fit.',
    benchmarkContext: 'Seed-stage SaaS companies typically have $10K-$100K MRR. Series A companies often have $100K-$500K MRR.',
    direction: 'higher_is_better',
    category: 'revenue',
    icon: DollarSign,
  },
  arr: {
    key: 'arr',
    displayName: 'Annual Recurring Revenue',
    shortDescription: 'MRR annualized (MRR x 12)',
    longDescription: 'Annual Recurring Revenue (ARR) is MRR multiplied by 12. It provides a standardized yearly view of recurring revenue, useful for comparing companies with different billing cycles.',
    formula: 'ARR = MRR x 12',
    whyItMatters: 'ARR is the primary valuation metric for SaaS companies. Valuations are often expressed as multiples of ARR (e.g., 10x ARR).',
    benchmarkContext: 'Series A SaaS companies typically have $1M-$5M ARR. Series B often requires $5M-$15M ARR.',
    direction: 'higher_is_better',
    category: 'revenue',
    icon: DollarSign,
  },
  revenue_growth_mom: {
    key: 'revenue_growth_mom',
    displayName: 'Monthly Revenue Growth',
    shortDescription: 'Percentage change in revenue month-over-month',
    longDescription: 'Month-over-month revenue growth measures how quickly your recurring revenue is increasing. Consistent growth demonstrates product-market fit and execution capability.',
    formula: 'MoM Growth = (Current MRR - Previous MRR) / Previous MRR x 100%',
    whyItMatters: 'Growth rate is the most important metric for early-stage startups. Investors expect 10-20% monthly growth for seed-stage companies.',
    benchmarkContext: 'Top quartile seed companies grow 15-25% MoM. 5-10% is considered healthy but slower.',
    direction: 'higher_is_better',
    category: 'growth',
    icon: TrendingUp,
  },
  gross_margin: {
    key: 'gross_margin',
    displayName: 'Gross Margin',
    shortDescription: 'Revenue remaining after cost of goods sold',
    longDescription: 'Gross margin is the percentage of revenue remaining after subtracting direct costs (COGS) like hosting, support, and payment processing. Higher margins indicate more scalable economics.',
    formula: 'Gross Margin = (Revenue - COGS) / Revenue x 100%',
    whyItMatters: 'SaaS companies should target 70-80%+ gross margins. Lower margins suggest infrastructure inefficiency or heavy support costs.',
    benchmarkContext: 'Best-in-class SaaS has 80%+ gross margins. Below 60% is a red flag for investors.',
    direction: 'higher_is_better',
    category: 'profitability',
    icon: Percent,
  },
  operating_margin: {
    key: 'operating_margin',
    displayName: 'Operating Margin',
    shortDescription: 'Profit margin after all operating expenses',
    longDescription: 'Operating margin shows what percentage of revenue remains after all operating costs (COGS, R&D, S&M, G&A). Early-stage companies are typically negative as they invest in growth.',
    formula: 'Operating Margin = (Revenue - All Operating Expenses) / Revenue x 100%',
    whyItMatters: 'Shows path to profitability. Even if negative now, improving operating margin indicates efficient scaling.',
    benchmarkContext: 'Early-stage companies are often -50% to -100%. Mature SaaS targets 15-25%.',
    direction: 'higher_is_better',
    category: 'profitability',
    icon: Percent,
  },
  net_burn: {
    key: 'net_burn',
    displayName: 'Net Burn',
    shortDescription: 'Monthly cash consumption after revenue',
    longDescription: 'Net burn is the amount of cash your company loses each month after accounting for revenue. It equals total cash out minus total cash in from operations.',
    formula: 'Net Burn = Total Monthly Expenses - Total Monthly Revenue',
    whyItMatters: 'Net burn determines how long your cash will last. Lower burn extends runway and reduces fundraising pressure.',
    benchmarkContext: 'Healthy startups maintain net burn at 50-75% of revenue until reaching profitability path.',
    direction: 'lower_is_better',
    category: 'cash',
    icon: TrendingDown,
  },
  burn_multiple: {
    key: 'burn_multiple',
    displayName: 'Burn Multiple',
    shortDescription: 'Cash burned per dollar of new ARR',
    longDescription: 'Burn multiple measures capital efficiency by showing how much cash you burn to generate each new dollar of ARR. Lower is better - it means you acquire revenue efficiently.',
    formula: 'Burn Multiple = Net Burn / Net New ARR',
    whyItMatters: 'The most important efficiency metric. A burn multiple under 1.5x indicates excellent efficiency. Above 3x is concerning.',
    benchmarkContext: 'Elite: <1x, Good: 1-1.5x, Acceptable: 1.5-2x, Concerning: >2x',
    direction: 'lower_is_better',
    category: 'efficiency',
    icon: Target,
  },
  runway_months: {
    key: 'runway_months',
    displayName: 'Runway',
    shortDescription: 'Months of cash remaining at current burn rate',
    longDescription: 'Runway is how many months your company can operate before running out of cash, assuming current burn rate continues. It is the most critical survival metric.',
    formula: 'Runway = Cash Balance / Net Monthly Burn',
    whyItMatters: 'Runway under 12 months creates fundraising pressure. Under 6 months is an emergency requiring immediate action.',
    benchmarkContext: 'Ideal runway is 18-24 months post-raise. Maintain 12+ months at all times.',
    direction: 'higher_is_better',
    category: 'cash',
    icon: Clock,
  },
  cash_balance: {
    key: 'cash_balance',
    displayName: 'Cash Balance',
    shortDescription: 'Total cash and cash equivalents on hand',
    longDescription: 'Cash balance is the total amount of liquid assets available to fund operations. It includes bank accounts, money market funds, and short-term investments.',
    formula: 'Cash Balance = Bank Accounts + Money Market Funds + Short-term Investments',
    whyItMatters: 'Cash is the lifeblood of a startup. Insufficient cash leads to forced fundraising at poor terms or shutdown.',
    direction: 'higher_is_better',
    category: 'cash',
    icon: DollarSign,
  },
  net_revenue_retention: {
    key: 'net_revenue_retention',
    displayName: 'Net Revenue Retention (NRR)',
    shortDescription: 'Revenue retention including expansion and churn',
    longDescription: 'NRR measures how much revenue from existing customers you retain and grow over time. It includes expansions, contractions, and churn. Over 100% means expansion outpaces churn.',
    formula: 'NRR = (Beginning MRR + Expansion - Contraction - Churn) / Beginning MRR x 100%',
    whyItMatters: 'NRR above 100% means you can grow even with zero new customers. Best SaaS companies have 120%+ NRR.',
    benchmarkContext: 'Elite: >120%, Good: 100-120%, Concerning: <100%',
    direction: 'higher_is_better',
    category: 'customer',
    icon: Users,
  },
  churn_rate: {
    key: 'churn_rate',
    displayName: 'Churn Rate',
    shortDescription: 'Percentage of revenue lost monthly from cancellations',
    longDescription: 'Churn rate is the percentage of MRR lost each month due to customer cancellations and downgrades. High churn indicates product-market fit issues.',
    formula: 'Churn Rate = (Churned MRR / Beginning MRR) x 100%',
    whyItMatters: 'High churn makes growth unsustainable. Even small improvements compound significantly over time.',
    benchmarkContext: 'Best-in-class: <1% monthly. Good: 1-2%. Concerning: >3%.',
    direction: 'lower_is_better',
    category: 'customer',
    icon: TrendingDown,
  },
  ltv_cac_ratio: {
    key: 'ltv_cac_ratio',
    displayName: 'LTV/CAC Ratio',
    shortDescription: 'Lifetime value per customer acquisition cost',
    longDescription: 'LTV/CAC compares how much value a customer generates over their lifetime to how much it costs to acquire them. Higher ratios indicate more profitable customer acquisition.',
    formula: 'LTV/CAC = (Average Revenue Per User x Gross Margin / Churn Rate) / Customer Acquisition Cost',
    whyItMatters: 'LTV/CAC above 3x indicates healthy unit economics. Below 1x means you lose money on each customer.',
    benchmarkContext: 'Excellent: >5x, Good: 3-5x, Acceptable: 2-3x, Unsustainable: <2x',
    direction: 'higher_is_better',
    category: 'efficiency',
    icon: Target,
  },
  cac_payback: {
    key: 'cac_payback',
    displayName: 'CAC Payback Period',
    shortDescription: 'Months to recover customer acquisition cost',
    longDescription: 'CAC payback measures how many months of customer revenue are needed to recover the cost of acquiring that customer. Shorter is better.',
    formula: 'CAC Payback = CAC / (ARPU x Gross Margin)',
    whyItMatters: 'Long payback periods tie up capital. Payback over 18 months strains cash flow significantly.',
    benchmarkContext: 'Excellent: <6 months, Good: 6-12 months, Acceptable: 12-18 months',
    direction: 'lower_is_better',
    category: 'efficiency',
    icon: Clock,
  },
  customer_count: {
    key: 'customer_count',
    displayName: 'Customer Count',
    shortDescription: 'Total number of paying customers',
    longDescription: 'The total number of active, paying customers. Higher counts reduce concentration risk and demonstrate broader market appeal.',
    whyItMatters: 'More customers means more stable revenue and lower risk from any single customer churning.',
    direction: 'higher_is_better',
    category: 'customer',
    icon: Users,
  },
  concentration_top5: {
    key: 'concentration_top5',
    displayName: 'Top 5 Customer Concentration',
    shortDescription: 'Revenue percentage from top 5 customers',
    longDescription: 'Customer concentration measures what percentage of revenue comes from your largest customers. High concentration creates risk if those customers churn.',
    formula: 'Concentration = (Revenue from Top 5 Customers / Total Revenue) x 100%',
    whyItMatters: 'High concentration (>30%) is a major risk factor. Losing one large customer can devastate the business.',
    benchmarkContext: 'Healthy: <20%, Moderate risk: 20-30%, High risk: >30%',
    direction: 'lower_is_better',
    category: 'customer',
    icon: PieChart,
  },
};

export const INPUT_FIELD_TOOLTIPS: Record<string, { title: string; description: string; whyItMatters: string }> = {
  cashOnHand: {
    title: 'Cash on Hand',
    description: 'Total liquid assets available in bank accounts and short-term investments.',
    whyItMatters: 'Determines your runway and ability to weather unexpected challenges. This is your financial safety net.',
  },
  monthlyRevenue: {
    title: 'Monthly Revenue (MRR)',
    description: 'Sum of all recurring subscription revenue, normalized to monthly.',
    whyItMatters: 'The foundation for valuation multiples and growth rate calculations. Higher MRR indicates stronger market position.',
  },
  monthlyExpenses: {
    title: 'Monthly Expenses (Burn)',
    description: 'Total operating costs including payroll, rent, software, marketing, and all other expenses.',
    whyItMatters: 'Combined with revenue, determines your net burn rate and runway. Lower expenses extend survival time.',
  },
  growthRate: {
    title: 'Monthly Growth Rate',
    description: 'Expected month-over-month increase in revenue, expressed as a percentage.',
    whyItMatters: 'Growth rate is the most important metric for early-stage startups. Compounds significantly over the projection period.',
  },
  grossMargin: {
    title: 'Gross Margin',
    description: 'Percentage of revenue remaining after direct costs (hosting, support, payments).',
    whyItMatters: 'Indicates scalability of your business model. Higher margins mean more resources for growth.',
  },
  payroll: {
    title: 'Monthly Payroll',
    description: 'Total compensation costs including salaries, benefits, and payroll taxes.',
    whyItMatters: 'Typically 60-70% of startup expenses. Understanding payroll is key to burn management.',
  },
  opex: {
    title: 'Operating Expenses',
    description: 'Non-payroll operational costs: software, rent, marketing, legal, etc.',
    whyItMatters: 'More flexible than payroll. Often the first target for burn reduction initiatives.',
  },
};

export const SCENARIO_SLIDER_TOOLTIPS: Record<string, { title: string; description: string; example: string; markers: { value: number; label: string }[] }> = {
  pricing_change_pct: {
    title: 'Pricing Change',
    description: 'Adjust your pricing strategy. Increases may impact growth, but improve unit economics.',
    example: 'A 10% price increase on $50K MRR adds $5K/mo to revenue immediately.',
    markers: [
      { value: -10, label: 'Discount' },
      { value: 0, label: 'Current' },
      { value: 10, label: 'Moderate' },
      { value: 20, label: 'Aggressive' },
    ],
  },
  growth_uplift_pct: {
    title: 'Growth Uplift',
    description: 'Expected change in growth rate from marketing, sales, or product improvements.',
    example: 'A 5% growth uplift compounds to ~30% more revenue over 12 months.',
    markers: [
      { value: -5, label: 'Slowdown' },
      { value: 0, label: 'Current' },
      { value: 10, label: 'Optimistic' },
      { value: 20, label: 'Aggressive' },
    ],
  },
  burn_reduction_pct: {
    title: 'Burn Reduction',
    description: 'Cost-cutting measures to extend runway. May impact growth or morale.',
    example: 'A 20% reduction on $80K/mo expenses saves $16K/mo, adding ~5 months runway.',
    markers: [
      { value: 0, label: 'None' },
      { value: 10, label: 'Conservative' },
      { value: 20, label: 'Moderate' },
      { value: 30, label: 'Aggressive' },
    ],
  },
  gross_margin_delta_pct: {
    title: 'Gross Margin Change',
    description: 'Improvements in unit economics through pricing, cost reduction, or efficiency.',
    example: 'A 5% margin improvement means $2.5K more profit per $50K revenue.',
    markers: [
      { value: -5, label: 'Decline' },
      { value: 0, label: 'Current' },
      { value: 5, label: 'Improved' },
      { value: 10, label: 'Optimized' },
    ],
  },
  churn_change_pct: {
    title: 'Churn Rate Change',
    description: 'Adjustment to monthly customer churn. Negative values reduce churn (improve retention).',
    example: 'Reducing churn by 2% on 100 customers saves 2 customers/month, worth $2K+ in ARR.',
    markers: [
      { value: -3, label: 'Reduced' },
      { value: 0, label: 'Current' },
      { value: 2, label: 'Increased' },
      { value: 5, label: 'High' },
    ],
  },
  cac_change_pct: {
    title: 'CAC Change',
    description: 'Change in Customer Acquisition Cost. Negative values mean more efficient acquisition.',
    example: 'A 15% CAC reduction on $500 CAC saves $75 per customer, improving LTV/CAC ratio.',
    markers: [
      { value: -20, label: 'Efficient' },
      { value: -10, label: 'Improved' },
      { value: 0, label: 'Current' },
      { value: 10, label: 'Higher' },
    ],
  },
};

export function getMetricDefinition(key: string): MetricDefinition | undefined {
  const normalizedKey = key.toLowerCase().replace(/[\s-]/g, '_');
  return METRIC_DEFINITIONS[normalizedKey] || Object.values(METRIC_DEFINITIONS).find(m => 
    m.displayName.toLowerCase().includes(key.toLowerCase()) ||
    m.key.includes(normalizedKey)
  );
}
