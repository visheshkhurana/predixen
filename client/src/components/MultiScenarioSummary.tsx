import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Trophy, TrendingUp, AlertTriangle, Clock } from 'lucide-react';
import { cn, formatCurrencyAbbrev } from '@/lib/utils';

interface ScenarioSummary {
  key: string;
  name: string;
  runway_p50: number;
  survival_18m: number;
  final_cash_p50: number;
}

interface MultiScenarioSummaryProps {
  comparison: ScenarioSummary[];
  testId?: string;
}

export function MultiScenarioSummary({ comparison, testId = 'multi-scenario-summary' }: MultiScenarioSummaryProps) {
  const sortedByRunway = [...comparison].sort((a, b) => b.runway_p50 - a.runway_p50);
  const bestScenario = sortedByRunway[0];
  const worstScenario = sortedByRunway[sortedByRunway.length - 1];

  const formatCurrency = (value: number) => formatCurrencyAbbrev(value);

  const getRunwayColor = (months: number) => {
    if (months <= 6) return 'text-red-600 dark:text-red-400';
    if (months <= 12) return 'text-amber-600 dark:text-amber-400';
    return 'text-emerald-600 dark:text-emerald-400';
  };

  const getSurvivalBadgeClass = (rate: number) => {
    if (rate < 50) return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
    if (rate < 75) return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400';
    return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400';
  };

  return (
    <div className="space-y-4" data-testid={testId}>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Trophy className="h-4 w-4 text-amber-500" />
              Best Scenario
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{bestScenario?.name}</p>
            <div className="mt-2 flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3 text-muted-foreground" />
                <span className={cn("font-mono font-medium", getRunwayColor(bestScenario?.runway_p50 || 0))}>
                  {bestScenario?.runway_p50.toFixed(1)} mo
                </span>
              </div>
              <Badge className={getSurvivalBadgeClass(bestScenario?.survival_18m || 0)}>
                {bestScenario?.survival_18m.toFixed(0)}% survival
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              Runway Range
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className={cn("text-2xl font-bold font-mono", getRunwayColor(worstScenario?.runway_p50 || 0))}>
                {worstScenario?.runway_p50.toFixed(1)}
              </span>
              <span className="text-muted-foreground">to</span>
              <span className={cn("text-2xl font-bold font-mono", getRunwayColor(bestScenario?.runway_p50 || 0))}>
                {bestScenario?.runway_p50.toFixed(1)}
              </span>
              <span className="text-sm text-muted-foreground">months</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {(bestScenario?.runway_p50 - (worstScenario?.runway_p50 || 0)).toFixed(1)} months difference
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Risk Assessment
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {sortedByRunway.map((s) => (
                <div key={s.key} className="flex items-center justify-between text-sm">
                  <span className="truncate max-w-[120px]">{s.name}</span>
                  <Badge 
                    variant="outline" 
                    className={cn("font-mono text-xs", getSurvivalBadgeClass(s.survival_18m))}
                  >
                    {s.survival_18m.toFixed(0)}%
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
