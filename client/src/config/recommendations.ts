export interface Recommendation {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  category: 'cost' | 'revenue' | 'fundraising' | 'operations' | 'strategy';
  action: string;
  impact: string;
}

interface SimulationMetrics {
  runwayMonths: number;
  survivalProbability: number;
  burnRate: number;
  revenueGrowth: number;
  grossMargin: number;
  cashBalance: number;
}

export function generateRecommendations(metrics: SimulationMetrics): Recommendation[] {
  const recommendations: Recommendation[] = [];
  
  if (metrics.runwayMonths < 6) {
    recommendations.push({
      id: 'urgent_runway',
      title: 'Critical: Runway Below 6 Months',
      description: 'Your cash runway is dangerously low. Immediate action required to avoid running out of funds.',
      priority: 'high',
      category: 'fundraising',
      action: 'Begin emergency fundraising or explore bridge financing options immediately.',
      impact: 'Could extend runway by 6-12 months with successful raise.',
    });
    
    recommendations.push({
      id: 'immediate_cuts',
      title: 'Implement Immediate Cost Reductions',
      description: 'Reduce non-essential expenses to slow burn rate while fundraising.',
      priority: 'high',
      category: 'cost',
      action: 'Review all discretionary spending and pause non-critical projects.',
      impact: 'Could reduce burn by 15-25% within 30 days.',
    });
  } else if (metrics.runwayMonths < 12) {
    recommendations.push({
      id: 'start_fundraise',
      title: 'Begin Fundraising Process',
      description: 'With less than 12 months runway, start preparing for your next raise.',
      priority: 'high',
      category: 'fundraising',
      action: 'Update investor deck, reach out to warm leads, and set up initial meetings.',
      impact: 'Typical fundraising takes 3-6 months. Start now to avoid desperation.',
    });
  } else if (metrics.runwayMonths < 18) {
    recommendations.push({
      id: 'prepare_metrics',
      title: 'Focus on Fundraising Metrics',
      description: 'You have time to improve key metrics before your next raise.',
      priority: 'medium',
      category: 'strategy',
      action: 'Identify and optimize the 2-3 metrics most important for your next round.',
      impact: 'Better metrics = better terms and higher valuation.',
    });
  }
  
  if (metrics.survivalProbability < 50) {
    recommendations.push({
      id: 'survival_risk',
      title: 'High Business Risk Detected',
      description: 'Your 18-month survival probability is below 50%. Consider de-risking.',
      priority: 'high',
      category: 'strategy',
      action: 'Evaluate pivot options, reduce burn, or accelerate path to profitability.',
      impact: 'Could significantly improve survival odds with right strategy.',
    });
  } else if (metrics.survivalProbability < 70) {
    recommendations.push({
      id: 'moderate_risk',
      title: 'Moderate Business Risk',
      description: 'There is meaningful risk in your current trajectory. Consider hedging.',
      priority: 'medium',
      category: 'strategy',
      action: 'Build contingency plans and identify potential cost levers if needed.',
      impact: 'Preparation reduces stress and improves decision-making under pressure.',
    });
  }
  
  if (metrics.grossMargin < 50) {
    recommendations.push({
      id: 'improve_margins',
      title: 'Improve Gross Margins',
      description: 'Your gross margin is below SaaS benchmarks. Focus on unit economics.',
      priority: 'medium',
      category: 'revenue',
      action: 'Review pricing, reduce COGS, and optimize service delivery costs.',
      impact: 'Each 5% margin improvement extends runway and improves fundability.',
    });
  }
  
  if (metrics.revenueGrowth < 10 && metrics.runwayMonths > 12) {
    recommendations.push({
      id: 'accelerate_growth',
      title: 'Consider Growth Investment',
      description: 'With healthy runway, you may be under-investing in growth.',
      priority: 'medium',
      category: 'revenue',
      action: 'Evaluate sales/marketing investments that could accelerate revenue.',
      impact: 'Faster growth improves fundraising position and optionality.',
    });
  }
  
  if (metrics.burnRate > metrics.cashBalance * 0.15) {
    recommendations.push({
      id: 'high_burn',
      title: 'High Burn Rate Alert',
      description: 'Your monthly burn is consuming cash quickly. Review efficiency.',
      priority: 'medium',
      category: 'cost',
      action: 'Audit all expenses and identify areas for optimization.',
      impact: 'Burn reduction directly extends runway month-for-month.',
    });
  }
  
  if (recommendations.length === 0) {
    recommendations.push({
      id: 'healthy_position',
      title: 'Strong Financial Position',
      description: 'Your metrics look healthy. Focus on execution and growth.',
      priority: 'low',
      category: 'strategy',
      action: 'Continue current strategy while monitoring key metrics weekly.',
      impact: 'Consistency in execution compounds over time.',
    });
  }
  
  recommendations.sort((a, b) => {
    const priorityOrder = { high: 0, medium: 1, low: 2 };
    return priorityOrder[a.priority] - priorityOrder[b.priority];
  });
  
  return recommendations;
}

export function getRecommendationIconName(category: Recommendation['category']): 'dollar-sign' | 'trending-up' | 'landmark' | 'settings' | 'target' | 'lightbulb' {
  switch (category) {
    case 'cost': return 'dollar-sign';
    case 'revenue': return 'trending-up';
    case 'fundraising': return 'landmark';
    case 'operations': return 'settings';
    case 'strategy': return 'target';
    default: return 'lightbulb';
  }
}
