import { Shield, Rocket, Scale, TrendingDown, DollarSign, Users, Zap, Target, BarChart3 } from "lucide-react";
import type { SimulationGoal } from "@/components/GoalSelector";

export interface StrategyTemplate {
  id: string;
  name: string;
  shortName: string;
  description: string;
  narrative: string;
  icon: typeof Shield;
  goal: SimulationGoal;
  riskLevel: 'low' | 'medium' | 'high';
  params: {
    pricing_change_pct: number;
    growth_uplift_pct: number;
    burn_reduction_pct: number;
    gross_margin_delta_pct: number;
    fundraise_amount: number;
    churn_change_pct: number;
  };
  projections: {
    runwayChange: number;
    survivalProbability: number;
    arrGrowth: number;
    burnChange: number;
  };
  assumptions: string[];
  tradeoffs: string[];
  recommended?: boolean;
}

export const STRATEGY_TEMPLATES: StrategyTemplate[] = [
  {
    id: 'extend_conservative',
    name: 'Conservative Cost Cutting',
    shortName: 'Conservative',
    description: 'Reduce non-essential spend while maintaining core operations',
    narrative: 'Focus on efficiency by trimming 15% of expenses without impacting product development or customer success.',
    icon: Shield,
    goal: 'extend_runway',
    riskLevel: 'low',
    params: {
      pricing_change_pct: 0,
      growth_uplift_pct: 0,
      burn_reduction_pct: 15,
      gross_margin_delta_pct: 0,
      fundraise_amount: 0,
      churn_change_pct: 0,
    },
    projections: {
      runwayChange: 3.5,
      survivalProbability: 78,
      arrGrowth: 0,
      burnChange: -15,
    },
    assumptions: [
      '15% reduction in operating expenses',
      'No impact on product roadmap',
      'Maintain current team size',
    ],
    tradeoffs: [
      'Slower marketing reach',
      'Reduced discretionary spending',
    ],
    recommended: true,
  },
  {
    id: 'extend_aggressive',
    name: 'Deep Cost Restructuring',
    shortName: 'Deep Cuts',
    description: 'Significant expense reduction including headcount optimization',
    narrative: 'Aggressive cost measures to extend runway by 6+ months, accepting slower growth in exchange for survival.',
    icon: TrendingDown,
    goal: 'extend_runway',
    riskLevel: 'medium',
    params: {
      pricing_change_pct: 0,
      growth_uplift_pct: -10,
      burn_reduction_pct: 30,
      gross_margin_delta_pct: 5,
      fundraise_amount: 0,
      churn_change_pct: -5,
    },
    projections: {
      runwayChange: 7.2,
      survivalProbability: 85,
      arrGrowth: -10,
      burnChange: -30,
    },
    assumptions: [
      '30% reduction in operating expenses',
      '10-15% team size reduction',
      'Pause on new feature development',
    ],
    tradeoffs: [
      'Growth slowdown expected',
      'Team morale considerations',
      'Potential customer impact',
    ],
  },
  {
    id: 'extend_pricing',
    name: 'Price Increase Strategy',
    shortName: 'Raise Prices',
    description: 'Improve unit economics through strategic price increases',
    narrative: 'Increase prices by 10-15% to improve margins and extend runway without cutting costs.',
    icon: DollarSign,
    goal: 'extend_runway',
    riskLevel: 'medium',
    params: {
      pricing_change_pct: 12,
      growth_uplift_pct: -5,
      burn_reduction_pct: 0,
      gross_margin_delta_pct: 8,
      fundraise_amount: 0,
      churn_change_pct: -3,
    },
    projections: {
      runwayChange: 4.1,
      survivalProbability: 72,
      arrGrowth: 7,
      burnChange: 0,
    },
    assumptions: [
      '12% price increase on new contracts',
      'Grandfather existing customers for 6 months',
      'Slight increase in churn expected',
    ],
    tradeoffs: [
      '3-5% expected customer churn',
      'Slower new customer acquisition',
      'Competitor positioning risk',
    ],
  },
  {
    id: 'growth_aggressive',
    name: 'Aggressive Growth Push',
    shortName: 'Scale Fast',
    description: 'Double down on sales and marketing to capture market share',
    narrative: 'Invest heavily in growth now to reach key milestones before the next funding round.',
    icon: Rocket,
    goal: 'accelerate_growth',
    riskLevel: 'high',
    params: {
      pricing_change_pct: 0,
      growth_uplift_pct: 40,
      burn_reduction_pct: -25,
      gross_margin_delta_pct: -5,
      fundraise_amount: 0,
      churn_change_pct: 0,
    },
    projections: {
      runwayChange: -4.5,
      survivalProbability: 52,
      arrGrowth: 40,
      burnChange: 25,
    },
    assumptions: [
      'Hire 5-8 new sales/marketing team members',
      'Increase marketing spend by 50%',
      'Assumes fundraise within 9-12 months',
    ],
    tradeoffs: [
      'Significant runway reduction',
      'Higher cash burn',
      'Execution risk on hiring',
    ],
    recommended: true,
  },
  {
    id: 'growth_measured',
    name: 'Measured Growth Acceleration',
    shortName: 'Steady Growth',
    description: 'Strategic growth investment with controlled burn increase',
    narrative: 'Grow 20% faster while keeping runway above 12 months through selective hiring.',
    icon: Target,
    goal: 'accelerate_growth',
    riskLevel: 'medium',
    params: {
      pricing_change_pct: 5,
      growth_uplift_pct: 20,
      burn_reduction_pct: -10,
      gross_margin_delta_pct: 0,
      fundraise_amount: 0,
      churn_change_pct: 5,
    },
    projections: {
      runwayChange: -1.8,
      survivalProbability: 68,
      arrGrowth: 25,
      burnChange: 10,
    },
    assumptions: [
      'Hire 2-3 key revenue-generating roles',
      'Modest marketing budget increase',
      '5% price increase on new deals',
    ],
    tradeoffs: [
      'Moderate runway impact',
      'Requires strong execution',
    ],
  },
  {
    id: 'growth_product_led',
    name: 'Product-Led Growth',
    shortName: 'PLG Focus',
    description: 'Invest in product virality and self-serve conversion',
    narrative: 'Build growth loops into the product to reduce CAC and accelerate organic growth.',
    icon: Users,
    goal: 'accelerate_growth',
    riskLevel: 'medium',
    params: {
      pricing_change_pct: -5,
      growth_uplift_pct: 15,
      burn_reduction_pct: 5,
      gross_margin_delta_pct: 10,
      fundraise_amount: 0,
      churn_change_pct: 10,
    },
    projections: {
      runwayChange: 1.2,
      survivalProbability: 75,
      arrGrowth: 15,
      burnChange: -5,
    },
    assumptions: [
      'Invest in self-serve onboarding',
      'Launch referral program',
      'Lower price point for entry tier',
    ],
    tradeoffs: [
      'Lower ARPU initially',
      'Engineering investment required',
      'Longer payback period',
    ],
  },
  {
    id: 'balance_efficient',
    name: 'Efficient Growth',
    shortName: 'Efficient',
    description: 'Optimize unit economics while maintaining growth trajectory',
    narrative: 'The Goldilocks approach—not too hot, not too cold. Grow sustainably while improving margins.',
    icon: Scale,
    goal: 'balance',
    riskLevel: 'low',
    params: {
      pricing_change_pct: 5,
      growth_uplift_pct: 10,
      burn_reduction_pct: 10,
      gross_margin_delta_pct: 5,
      fundraise_amount: 0,
      churn_change_pct: 5,
    },
    projections: {
      runwayChange: 2.5,
      survivalProbability: 80,
      arrGrowth: 15,
      burnChange: -10,
    },
    assumptions: [
      'Modest price increase (5%)',
      '10% expense optimization',
      'Focus on high-value customers',
    ],
    tradeoffs: [
      'Slower than aggressive growth',
      'Requires disciplined execution',
    ],
    recommended: true,
  },
  {
    id: 'balance_optimize',
    name: 'Margin Optimization',
    shortName: 'Optimize',
    description: 'Focus on improving gross margins and unit economics',
    narrative: 'Improve profitability per customer while maintaining current growth rates.',
    icon: BarChart3,
    goal: 'balance',
    riskLevel: 'low',
    params: {
      pricing_change_pct: 8,
      growth_uplift_pct: 0,
      burn_reduction_pct: 5,
      gross_margin_delta_pct: 10,
      fundraise_amount: 0,
      churn_change_pct: 0,
    },
    projections: {
      runwayChange: 3.8,
      survivalProbability: 82,
      arrGrowth: 8,
      burnChange: -5,
    },
    assumptions: [
      '8% price increase',
      'Reduce COGS through automation',
      'Optimize vendor contracts',
    ],
    tradeoffs: [
      'Growth stays flat',
      'Customer sensitivity to price',
    ],
  },
  {
    id: 'balance_bridge',
    name: 'Bridge Round Strategy',
    shortName: 'Bridge',
    description: 'Raise a small bridge to extend runway while proving metrics',
    narrative: 'Secure 6-9 months of additional runway through a convertible note or SAFE.',
    icon: Zap,
    goal: 'balance',
    riskLevel: 'medium',
    params: {
      pricing_change_pct: 0,
      growth_uplift_pct: 10,
      burn_reduction_pct: 0,
      gross_margin_delta_pct: 0,
      fundraise_amount: 500000,
      churn_change_pct: 0,
    },
    projections: {
      runwayChange: 6.5,
      survivalProbability: 88,
      arrGrowth: 10,
      burnChange: 0,
    },
    assumptions: [
      '$500K bridge at reasonable terms',
      'Existing investor participation',
      'Use funds to hit key milestones',
    ],
    tradeoffs: [
      'Additional dilution (5-10%)',
      'Sets expectations for next round',
      'Investor relationship complexity',
    ],
  },
];

export function getStrategiesForGoal(goal: SimulationGoal): StrategyTemplate[] {
  return STRATEGY_TEMPLATES.filter(s => s.goal === goal);
}

export function getRecommendedStrategy(goal: SimulationGoal): StrategyTemplate | undefined {
  return STRATEGY_TEMPLATES.find(s => s.goal === goal && s.recommended);
}

export function getStrategyById(id: string): StrategyTemplate | undefined {
  return STRATEGY_TEMPLATES.find(s => s.id === id);
}
