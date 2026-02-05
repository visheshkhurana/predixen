export interface StressTestTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  severity: 'low' | 'moderate' | 'severe';
  color: string;
  adjustments: {
    revenueGrowthMultiplier?: number;
    churnRateMultiplier?: number;
    cacMultiplier?: number;
    burnMultiplier?: number;
    immediateRevenueHit?: number;
    fundraisingAvailable?: boolean;
    newCustomerMultiplier?: number;
  };
  duration: number;
  historicalProbability: number;
}

export const stressTestTemplates: StressTestTemplate[] = [
  {
    id: 'mild-recession',
    name: 'Mild Recession',
    description: 'Economic slowdown with reduced customer spending and longer sales cycles',
    icon: 'TrendingDown',
    severity: 'moderate',
    color: 'yellow',
    adjustments: {
      revenueGrowthMultiplier: 0.7,
      churnRateMultiplier: 1.3,
      cacMultiplier: 1.2,
      newCustomerMultiplier: 0.8,
    },
    duration: 12,
    historicalProbability: 0.25,
  },
  {
    id: 'severe-downturn',
    name: 'Severe Downturn',
    description: '2008-style financial crisis with significant market contraction',
    icon: 'AlertCircle',
    severity: 'severe',
    color: 'red',
    adjustments: {
      revenueGrowthMultiplier: 0.4,
      churnRateMultiplier: 1.8,
      cacMultiplier: 1.5,
      newCustomerMultiplier: 0.4,
      burnMultiplier: 1.1,
    },
    duration: 18,
    historicalProbability: 0.08,
  },
  {
    id: 'funding-winter',
    name: 'Funding Winter',
    description: 'VC market freeze with no external funding available for 24 months',
    icon: 'Snowflake',
    severity: 'severe',
    color: 'blue',
    adjustments: {
      fundraisingAvailable: false,
      revenueGrowthMultiplier: 0.85,
      churnRateMultiplier: 1.15,
    },
    duration: 24,
    historicalProbability: 0.15,
  },
  {
    id: 'key-customer-loss',
    name: 'Key Customer Loss',
    description: 'Top 3 customers churn simultaneously due to budget cuts or competition',
    icon: 'Users',
    severity: 'severe',
    color: 'orange',
    adjustments: {
      immediateRevenueHit: -0.30,
      churnRateMultiplier: 1.2,
      revenueGrowthMultiplier: 0.9,
    },
    duration: 6,
    historicalProbability: 0.05,
  },
  {
    id: 'competitive-disruption',
    name: 'Competitive Disruption',
    description: 'Well-funded competitor enters market with aggressive pricing',
    icon: 'Swords',
    severity: 'moderate',
    color: 'purple',
    adjustments: {
      churnRateMultiplier: 1.6,
      cacMultiplier: 1.35,
      revenueGrowthMultiplier: 0.65,
    },
    duration: 12,
    historicalProbability: 0.20,
  },
  {
    id: 'hiring-freeze',
    name: 'Hiring Freeze',
    description: 'Pause all hiring for 6 months to preserve runway and reduce burn',
    icon: 'Pause',
    severity: 'low',
    color: 'gray',
    adjustments: {
      burnMultiplier: 0.85,
      revenueGrowthMultiplier: 0.85,
    },
    duration: 6,
    historicalProbability: 0.40,
  },
];

export function applyStressTest(
  baseState: any,
  template: StressTestTemplate
): any {
  const stressedState = { ...baseState };
  
  if (template.adjustments.revenueGrowthMultiplier !== undefined) {
    stressedState.growthRate *= template.adjustments.revenueGrowthMultiplier;
  }
  if (template.adjustments.churnRateMultiplier !== undefined) {
    stressedState.churnRate *= template.adjustments.churnRateMultiplier;
  }
  if (template.adjustments.cacMultiplier !== undefined) {
    stressedState.cac *= template.adjustments.cacMultiplier;
  }
  if (template.adjustments.burnMultiplier !== undefined) {
    // Apply to all expense components consistently
    if (stressedState.opex !== undefined) {
      stressedState.opex *= template.adjustments.burnMultiplier;
    }
    if (stressedState.payroll !== undefined) {
      stressedState.payroll *= template.adjustments.burnMultiplier;
    }
    if (stressedState.otherCosts !== undefined) {
      stressedState.otherCosts *= template.adjustments.burnMultiplier;
    }
  }
  if (template.adjustments.immediateRevenueHit !== undefined) {
    stressedState.monthlyRevenue *= (1 + template.adjustments.immediateRevenueHit);
  }
  if (template.adjustments.fundraisingAvailable === false) {
    stressedState.fundraisingAvailable = false;
  }
  if (template.adjustments.newCustomerMultiplier !== undefined) {
    // Apply to growth rate as new customer acquisition affects growth
    stressedState.growthRate *= template.adjustments.newCustomerMultiplier;
  }
  
  return stressedState;
}
