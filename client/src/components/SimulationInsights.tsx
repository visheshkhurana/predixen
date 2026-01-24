import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  AlertTriangle, 
  TrendingUp, 
  TrendingDown, 
  Lightbulb, 
  Target,
  DollarSign,
  Calendar,
  ArrowRight,
  CheckCircle,
  AlertCircle,
  Zap
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SimulationData {
  runway?: {
    p10?: number;
    p50?: number;
    p90?: number;
  };
  survival?: {
    '12m'?: number;
    '18m'?: number;
    '24m'?: number;
  };
  summary?: {
    end_cash?: number;
    monthly_burn?: number;
    monthly_burn_p50?: number;
  };
  month_data?: Array<{
    cash_p50?: number;
    revenue_p50?: number;
    burn_p50?: number;
  }>;
}

interface SimulationInsightsProps {
  simulation: SimulationData;
  scenarioName: string;
  testId?: string;
}

interface Recommendation {
  id: string;
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  category: 'cost' | 'revenue' | 'funding' | 'strategic';
  actionable: boolean;
}

function generateRecommendations(simulation: SimulationData): Recommendation[] {
  const recommendations: Recommendation[] = [];
  const runwayP50 = simulation.runway?.p50 || 0;
  const survival18m = simulation.survival?.['18m'] || 0;
  const survival12m = simulation.survival?.['12m'] || 0;
  const endCash = simulation.summary?.end_cash || 0;
  const monthlyBurn = simulation.summary?.monthly_burn || simulation.summary?.monthly_burn_p50 || 0;
  
  if (runwayP50 <= 6) {
    recommendations.push({
      id: 'critical-runway',
      title: 'Immediate Action Required',
      description: 'Your runway is critically short. Focus on emergency cost reduction and accelerate fundraising conversations.',
      impact: 'high',
      category: 'cost',
      actionable: true,
    });
    recommendations.push({
      id: 'bridge-funding',
      title: 'Explore Bridge Financing',
      description: 'With less than 6 months of runway, consider a bridge round or revenue-based financing to extend survival.',
      impact: 'high',
      category: 'funding',
      actionable: true,
    });
  } else if (runwayP50 <= 12) {
    recommendations.push({
      id: 'start-fundraising',
      title: 'Begin Fundraising Preparation',
      description: 'Start building investor relationships now. A 12-month runway typically means 6-9 months to close a round.',
      impact: 'high',
      category: 'funding',
      actionable: true,
    });
    recommendations.push({
      id: 'optimize-burn',
      title: 'Optimize Monthly Burn',
      description: 'Review recurring expenses and identify 10-20% cost reduction opportunities to extend runway.',
      impact: 'medium',
      category: 'cost',
      actionable: true,
    });
  } else if (runwayP50 <= 18) {
    recommendations.push({
      id: 'plan-ahead',
      title: 'Strategic Planning Window',
      description: 'You have a healthy runway. Use this time to focus on growth and build investor relationships proactively.',
      impact: 'medium',
      category: 'strategic',
      actionable: true,
    });
  }

  if (survival18m < 50) {
    recommendations.push({
      id: 'survival-risk',
      title: 'Address Survival Risk',
      description: `Your 18-month survival probability is ${survival18m.toFixed(0)}%. Consider conservative scenarios to improve odds.`,
      impact: 'high',
      category: 'strategic',
      actionable: true,
    });
  } else if (survival18m < 80) {
    recommendations.push({
      id: 'improve-survival',
      title: 'Improve Survival Probability',
      description: `At ${survival18m.toFixed(0)}% survival rate, you have room for improvement. Explore cost optimization scenarios.`,
      impact: 'medium',
      category: 'cost',
      actionable: true,
    });
  }

  const monthData = simulation.month_data || [];
  if (monthData.length >= 2) {
    const lastRevenue = monthData[monthData.length - 1]?.revenue_p50 || 0;
    const firstRevenue = monthData[0]?.revenue_p50 || 0;
    if (firstRevenue > 0 && lastRevenue / firstRevenue < 1.5) {
      recommendations.push({
        id: 'growth-opportunity',
        title: 'Accelerate Revenue Growth',
        description: 'Revenue growth appears modest. Consider growth investments to improve unit economics and investor appeal.',
        impact: 'medium',
        category: 'revenue',
        actionable: true,
      });
    }
  }

  if (endCash < 0) {
    recommendations.push({
      id: 'negative-cash',
      title: 'Cash Projection Negative',
      description: 'Your simulation projects negative cash. Take immediate action to prevent this outcome.',
      impact: 'high',
      category: 'cost',
      actionable: true,
    });
  }

  if (recommendations.length === 0) {
    recommendations.push({
      id: 'healthy-trajectory',
      title: 'Strong Financial Position',
      description: 'Your current trajectory looks healthy. Focus on sustainable growth and building competitive moats.',
      impact: 'low',
      category: 'strategic',
      actionable: false,
    });
  }

  return recommendations.slice(0, 4);
}

function generateNarrativeSummary(simulation: SimulationData, scenarioName: string): string {
  const runwayP50 = simulation.runway?.p50 || 0;
  const runwayP10 = simulation.runway?.p10 || 0;
  const runwayP90 = simulation.runway?.p90 || 0;
  const survival18m = simulation.survival?.['18m'] || 0;
  const survival12m = simulation.survival?.['12m'] || 0;
  
  let narrative = `Under the "${scenarioName}" scenario, your company has a median runway of ${runwayP50.toFixed(1)} months. `;
  
  narrative += `In the worst-case outcomes (P10), runway drops to ${runwayP10.toFixed(1)} months, while best-case scenarios (P90) extend to ${runwayP90.toFixed(1)} months. `;
  
  if (survival18m >= 80) {
    narrative += `With an ${survival18m.toFixed(0)}% probability of surviving 18 months, your financial position is strong. `;
  } else if (survival18m >= 50) {
    narrative += `Your 18-month survival probability of ${survival18m.toFixed(0)}% indicates moderate risk. Consider conservative adjustments. `;
  } else {
    narrative += `A ${survival18m.toFixed(0)}% 18-month survival probability signals high risk. Immediate action is recommended. `;
  }
  
  if (survival12m >= 90) {
    narrative += `Short-term outlook is excellent with ${survival12m.toFixed(0)}% 12-month survival.`;
  } else if (survival12m >= 70) {
    narrative += `Short-term outlook is stable with ${survival12m.toFixed(0)}% 12-month survival.`;
  } else {
    narrative += `Short-term risk is elevated with only ${survival12m.toFixed(0)}% 12-month survival probability.`;
  }
  
  return narrative;
}

function getCategoryIcon(category: Recommendation['category']) {
  switch (category) {
    case 'cost': return <TrendingDown className="h-4 w-4" />;
    case 'revenue': return <TrendingUp className="h-4 w-4" />;
    case 'funding': return <DollarSign className="h-4 w-4" />;
    case 'strategic': return <Target className="h-4 w-4" />;
  }
}

function getImpactColor(impact: Recommendation['impact']) {
  switch (impact) {
    case 'high': return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
    case 'medium': return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400';
    case 'low': return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400';
  }
}

export function SimulationInsights({ simulation, scenarioName, testId = 'simulation-insights' }: SimulationInsightsProps) {
  const runwayP50 = simulation.runway?.p50 || 0;
  const survival18m = simulation.survival?.['18m'] || 0;
  
  const hasValidData = runwayP50 > 0 || survival18m > 0;
  
  if (!hasValidData) {
    return (
      <div className="space-y-4" data-testid={testId}>
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Simulation Analysis</CardTitle>
            <CardDescription>
              No simulation data available yet. Run a simulation to see insights.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }
  
  const recommendations = generateRecommendations(simulation);
  const narrative = generateNarrativeSummary(simulation, scenarioName);
  
  const overallHealth = survival18m >= 80 ? 'healthy' : survival18m >= 50 ? 'warning' : 'critical';
  
  const healthColors = {
    healthy: 'border-emerald-500',
    warning: 'border-amber-500',
    critical: 'border-red-500'
  };
  
  return (
    <div className="space-y-4" data-testid={testId}>
      <Card className={cn("border-2", healthColors[overallHealth])}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              {overallHealth === 'healthy' && <CheckCircle className="h-5 w-5 text-emerald-500" />}
              {overallHealth === 'warning' && <AlertCircle className="h-5 w-5 text-amber-500" />}
              {overallHealth === 'critical' && <AlertTriangle className="h-5 w-5 text-red-500" />}
              <CardTitle className="text-lg">Simulation Analysis</CardTitle>
            </div>
            <Badge variant={overallHealth === 'healthy' ? 'default' : overallHealth === 'warning' ? 'secondary' : 'destructive'}>
              {overallHealth === 'healthy' ? 'Healthy Trajectory' : overallHealth === 'warning' ? 'Needs Attention' : 'Critical Risk'}
            </Badge>
          </div>
          <CardDescription className="mt-2">
            AI-powered analysis of your simulation results
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="p-4 bg-muted/50 rounded-lg mb-4">
            <div className="flex items-start gap-2">
              <Zap className="h-4 w-4 mt-0.5 text-primary shrink-0" />
              <p className="text-sm leading-relaxed" data-testid="text-narrative-summary">
                {narrative}
              </p>
            </div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="p-3 bg-background rounded-lg border">
              <p className="text-xs text-muted-foreground mb-1">Runway (P50)</p>
              <p className="text-lg font-mono font-semibold" data-testid="text-insight-runway">
                {runwayP50.toFixed(1)} mo
              </p>
            </div>
            <div className="p-3 bg-background rounded-lg border">
              <p className="text-xs text-muted-foreground mb-1">Survival (18m)</p>
              <p className="text-lg font-mono font-semibold" data-testid="text-insight-survival">
                {survival18m.toFixed(0)}%
              </p>
            </div>
            <div className="p-3 bg-background rounded-lg border">
              <p className="text-xs text-muted-foreground mb-1">Range Spread</p>
              <p className="text-lg font-mono font-semibold" data-testid="text-insight-spread">
                {((simulation.runway?.p90 || 0) - (simulation.runway?.p10 || 0)).toFixed(1)} mo
              </p>
            </div>
            <div className="p-3 bg-background rounded-lg border">
              <p className="text-xs text-muted-foreground mb-1">Risk Level</p>
              <p className={cn(
                "text-lg font-semibold capitalize",
                overallHealth === 'healthy' && "text-emerald-600 dark:text-emerald-400",
                overallHealth === 'warning' && "text-amber-600 dark:text-amber-400",
                overallHealth === 'critical' && "text-red-600 dark:text-red-400"
              )} data-testid="text-insight-risk">
                {overallHealth}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">Actionable Recommendations</CardTitle>
          </div>
          <CardDescription>
            Based on your simulation results
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recommendations.map((rec) => (
              <div 
                key={rec.id}
                className="flex items-start gap-3 p-3 rounded-lg border hover-elevate"
                data-testid={`recommendation-${rec.id}`}
              >
                <div className={cn(
                  "p-2 rounded-lg shrink-0",
                  rec.category === 'cost' && "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400",
                  rec.category === 'revenue' && "bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400",
                  rec.category === 'funding' && "bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400",
                  rec.category === 'strategic' && "bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400"
                )}>
                  {getCategoryIcon(rec.category)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-medium">{rec.title}</span>
                    <Badge variant="outline" className={cn("text-xs", getImpactColor(rec.impact))}>
                      {rec.impact} impact
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{rec.description}</p>
                </div>
                {rec.actionable && (
                  <Button variant="ghost" size="icon" className="shrink-0">
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
