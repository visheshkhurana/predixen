import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { RiskGauge, TrafficLight } from '@/components/RiskGauge';
import { cn } from '@/lib/utils';
import {
  Trophy,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Lightbulb,
  ArrowRight,
  Target,
  DollarSign,
  Clock,
  CheckCircle,
  Sparkles,
} from 'lucide-react';

interface ScenarioResult {
  id: string;
  name: string;
  runway_p50: number;
  runway_p10?: number;
  runway_p90?: number;
  survival_rate: number;
  end_cash_p50?: number;
  monthly_burn_p50?: number;
  assumptions?: {
    pricing_change_pct?: number;
    growth_uplift_pct?: number;
    burn_reduction_pct?: number;
    fundraise_amount?: number;
    fundraise_month?: number;
  };
}

interface ExecutiveSummaryProps {
  scenarios: ScenarioResult[];
  baselineId?: string;
  targetRunway?: number;
  minSurvival?: number;
  onScenarioSelect?: (id: string) => void;
  testId?: string;
}

export function ExecutiveSummary({
  scenarios,
  baselineId,
  targetRunway = 18,
  minSurvival = 0.8,
  onScenarioSelect,
  testId = 'executive-summary',
}: ExecutiveSummaryProps) {
  const analysis = useMemo(() => {
    if (!scenarios || scenarios.length === 0) return null;
    
    const sorted = [...scenarios].sort((a, b) => {
      const scoreA = a.survival_rate * 0.6 + (a.runway_p50 / 24) * 0.4;
      const scoreB = b.survival_rate * 0.6 + (b.runway_p50 / 24) * 0.4;
      return scoreB - scoreA;
    });
    
    const best = sorted[0];
    const baseline = scenarios.find(s => s.id === baselineId) || scenarios[0];
    const worst = sorted[sorted.length - 1];
    
    const meetsBenchmark = scenarios.filter(
      s => s.runway_p50 >= targetRunway && s.survival_rate >= minSurvival
    );
    
    const recommendations: string[] = [];
    
    if (best.assumptions?.pricing_change_pct && best.assumptions.pricing_change_pct > 0) {
      recommendations.push(`Increase pricing by ${best.assumptions.pricing_change_pct}%`);
    }
    if (best.assumptions?.burn_reduction_pct && best.assumptions.burn_reduction_pct > 0) {
      recommendations.push(`Reduce burn by ${best.assumptions.burn_reduction_pct}%`);
    }
    if (best.assumptions?.growth_uplift_pct && best.assumptions.growth_uplift_pct > 0) {
      recommendations.push(`Accelerate growth by ${best.assumptions.growth_uplift_pct}%`);
    }
    if (best.assumptions?.fundraise_amount) {
      const amount = best.assumptions.fundraise_amount >= 1000000
        ? `$${(best.assumptions.fundraise_amount / 1000000).toFixed(1)}M`
        : `$${(best.assumptions.fundraise_amount / 1000).toFixed(0)}K`;
      recommendations.push(`Raise ${amount} by month ${best.assumptions.fundraise_month || 'TBD'}`);
    }
    
    const runwayImprovement = best.runway_p50 - baseline.runway_p50;
    const survivalImprovement = (best.survival_rate - baseline.survival_rate) * 100;
    
    return {
      best,
      baseline,
      worst,
      meetsBenchmark,
      recommendations,
      runwayImprovement,
      survivalImprovement,
      totalScenarios: scenarios.length,
    };
  }, [scenarios, baselineId, targetRunway, minSurvival]);
  
  if (!analysis) {
    return null;
  }
  
  const formatCurrency = (value: number | undefined) => {
    if (!value) return 'N/A';
    if (Math.abs(value) >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    return `$${(value / 1000).toFixed(0)}K`;
  };
  
  return (
    <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-transparent" data-testid={testId}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10">
              <Sparkles className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-lg">Executive Summary</CardTitle>
              <p className="text-sm text-muted-foreground">
                Analysis of {analysis.totalScenarios} scenario{analysis.totalScenarios !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
          <TrafficLight survivalProbability={analysis.best.survival_rate} />
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-card rounded-lg p-4 border">
            <div className="flex items-center gap-2 mb-3">
              <Trophy className="h-5 w-5 text-amber-500" />
              <span className="font-medium">Best Scenario</span>
            </div>
            <div className="space-y-2">
              <p className="text-lg font-semibold">{analysis.best.name}</p>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="font-mono">{analysis.best.runway_p50.toFixed(1)} mo</span>
                </div>
                <div className="flex items-center gap-1">
                  <Target className="h-4 w-4 text-muted-foreground" />
                  <span className="font-mono">{Math.round(analysis.best.survival_rate * 100)}%</span>
                </div>
              </div>
              {analysis.runwayImprovement !== 0 && (
                <Badge variant={analysis.runwayImprovement > 0 ? 'default' : 'destructive'} className="text-xs">
                  {analysis.runwayImprovement > 0 ? '+' : ''}{analysis.runwayImprovement.toFixed(1)} months vs baseline
                </Badge>
              )}
            </div>
            {onScenarioSelect && (
              <Button
                variant="outline"
                size="sm"
                className="w-full mt-3"
                onClick={() => onScenarioSelect(analysis.best.id)}
                data-testid="button-view-best"
              >
                View Details
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            )}
          </div>
          
          <div className="bg-card rounded-lg p-4 border">
            <div className="flex items-center gap-2 mb-3">
              <Target className="h-5 w-5 text-primary" />
              <span className="font-medium">Runway Range</span>
            </div>
            <div className="space-y-3">
              <div className="text-center">
                <p className="text-3xl font-mono font-bold">
                  {analysis.best.runway_p10?.toFixed(0) || (analysis.best.runway_p50 - 3).toFixed(0)}
                  {' - '}
                  {analysis.best.runway_p90?.toFixed(0) || (analysis.best.runway_p50 + 5).toFixed(0)}
                </p>
                <p className="text-sm text-muted-foreground">months (P10 - P90)</p>
              </div>
              <RiskGauge survivalProbability={analysis.best.survival_rate} size="sm" showLabel={false} />
            </div>
          </div>
          
          <div className="bg-card rounded-lg p-4 border">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle className="h-5 w-5 text-emerald-500" />
              <span className="font-medium">Benchmark Status</span>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Target Runway</span>
                <span className="font-mono font-medium">{targetRunway} months</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Min Survival</span>
                <span className="font-mono font-medium">{Math.round(minSurvival * 100)}%</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm">Scenarios meeting benchmark</span>
                <Badge variant={analysis.meetsBenchmark.length > 0 ? 'default' : 'destructive'}>
                  {analysis.meetsBenchmark.length} / {analysis.totalScenarios}
                </Badge>
              </div>
            </div>
          </div>
        </div>
        
        {analysis.recommendations.length > 0 && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Lightbulb className="h-5 w-5 text-amber-500 mt-0.5 shrink-0" />
              <div>
                <p className="font-medium text-amber-700 dark:text-amber-400 mb-2">
                  Recommended Actions
                </p>
                <p className="text-sm">
                  {analysis.recommendations.join(' and ')} to achieve{' '}
                  <span className="font-semibold">{analysis.best.runway_p50.toFixed(1)} months</span> of runway
                  with <span className="font-semibold">{Math.round(analysis.best.survival_rate * 100)}%</span> survival probability.
                </p>
              </div>
            </div>
          </div>
        )}
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-2xl font-mono font-bold text-primary">
              {formatCurrency(analysis.best.end_cash_p50)}
            </p>
            <p className="text-xs text-muted-foreground">Projected End Cash</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-mono font-bold">
              {formatCurrency(analysis.best.monthly_burn_p50)}
            </p>
            <p className="text-xs text-muted-foreground">Monthly Burn</p>
          </div>
          <div className="text-center">
            <p className={cn(
              'text-2xl font-mono font-bold',
              analysis.survivalImprovement > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
            )}>
              {analysis.survivalImprovement > 0 ? '+' : ''}{analysis.survivalImprovement.toFixed(0)}%
            </p>
            <p className="text-xs text-muted-foreground">Survival Improvement</p>
          </div>
          <div className="text-center">
            <p className={cn(
              'text-2xl font-mono font-bold',
              analysis.runwayImprovement > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
            )}>
              {analysis.runwayImprovement > 0 ? '+' : ''}{analysis.runwayImprovement.toFixed(1)}
            </p>
            <p className="text-xs text-muted-foreground">Runway Gain (months)</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
