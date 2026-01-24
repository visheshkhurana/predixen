import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Trophy,
  GitCompare,
  Check
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface ScenarioResult {
  name: string;
  runway_p50: number;
  runway_p10?: number;
  runway_p90?: number;
  survival_18m: number;
  survival_12m?: number;
  end_cash?: number;
  avg_burn?: number;
  score?: number;
}

interface ScenarioComparisonViewProps {
  scenarios: ScenarioResult[];
  baselineScenarioName?: string;
  onSelectScenario?: (name: string) => void;
  selectedScenario?: string;
  testId?: string;
}

function formatCurrency(value: number): string {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function getDeltaIndicator(value: number | undefined, baseline: number | undefined, higherIsBetter: boolean = true) {
  const safeValue = value ?? 0;
  const safeBaseline = baseline ?? 0;
  
  if (safeValue === safeBaseline) return { icon: Minus, color: 'text-muted-foreground', label: '0' };
  
  const diff = safeValue - safeBaseline;
  const percentDiff = safeBaseline !== 0 ? ((diff / safeBaseline) * 100).toFixed(1) : 'N/A';
  const isBetter = higherIsBetter ? diff > 0 : diff < 0;
  
  return {
    icon: isBetter ? TrendingUp : TrendingDown,
    color: isBetter ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400',
    label: `${diff > 0 ? '+' : ''}${percentDiff}%`,
  };
}

function getRunwayBadge(months: number) {
  if (months >= 18) return { variant: 'default' as const, label: 'Strong' };
  if (months >= 12) return { variant: 'secondary' as const, label: 'Moderate' };
  return { variant: 'destructive' as const, label: 'Low' };
}

function getSurvivalBadge(probability: number) {
  if (probability >= 80) return { variant: 'default' as const, label: 'Likely' };
  if (probability >= 50) return { variant: 'secondary' as const, label: 'Uncertain' };
  return { variant: 'destructive' as const, label: 'At Risk' };
}

export function ScenarioComparisonView({ 
  scenarios, 
  baselineScenarioName = 'Baseline',
  onSelectScenario,
  selectedScenario,
  testId = 'scenario-comparison' 
}: ScenarioComparisonViewProps) {
  const baseline = scenarios.find(s => s.name.toLowerCase().includes('baseline')) || scenarios[0];
  
  const sortedScenarios = [...scenarios].sort((a, b) => {
    if (a.score !== undefined && b.score !== undefined) return b.score - a.score;
    return b.survival_18m - a.survival_18m;
  });
  
  const bestScenario = sortedScenarios[0];

  if (scenarios.length === 0) {
    return (
      <Card data-testid={testId}>
        <CardContent className="py-12 text-center">
          <GitCompare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">
            Run simulations to compare scenarios side-by-side
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid={testId}>
      <CardHeader>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <GitCompare className="h-5 w-5" />
              Scenario Comparison
            </CardTitle>
            <CardDescription>
              Compare {scenarios.length} scenarios against baseline
            </CardDescription>
          </div>
          {bestScenario && (
            <Badge variant="default" className="flex items-center gap-1">
              <Trophy className="h-3 w-3" />
              Best: {bestScenario.name}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[200px]">Scenario</TableHead>
                <TableHead className="text-right">Runway (P50)</TableHead>
                <TableHead className="text-right">vs Baseline</TableHead>
                <TableHead className="text-right">18-mo Survival</TableHead>
                <TableHead className="text-right">vs Baseline</TableHead>
                {scenarios.some(s => s.end_cash !== undefined) && (
                  <TableHead className="text-right">End Cash</TableHead>
                )}
                {scenarios.some(s => s.score !== undefined) && (
                  <TableHead className="text-right">Score</TableHead>
                )}
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedScenarios.map((scenario, index) => {
                const runwayDelta = getDeltaIndicator(scenario.runway_p50, baseline.runway_p50, true);
                const survivalDelta = getDeltaIndicator(scenario.survival_18m, baseline.survival_18m, true);
                const isBest = scenario.name === bestScenario?.name;
                const isBaseline = scenario.name === baseline.name;
                const isSelected = scenario.name === selectedScenario;
                
                return (
                  <TableRow 
                    key={scenario.name}
                    className={cn(
                      isSelected && "bg-muted/50",
                      isBest && "bg-primary/5"
                    )}
                    data-testid={`${testId}-row-${index}`}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{scenario.name}</span>
                        {isBest && (
                          <Badge variant="default" className="text-xs">
                            <Trophy className="h-3 w-3 mr-1" />
                            Best
                          </Badge>
                        )}
                        {isBaseline && (
                          <Badge variant="outline" className="text-xs">Baseline</Badge>
                        )}
                      </div>
                    </TableCell>
                    
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <span className="font-mono font-semibold">
                          {scenario.runway_p50.toFixed(1)} mo
                        </span>
                        <Badge {...getRunwayBadge(scenario.runway_p50)} className="text-xs">
                          {getRunwayBadge(scenario.runway_p50).label}
                        </Badge>
                      </div>
                    </TableCell>
                    
                    <TableCell className="text-right">
                      {!isBaseline && (
                        <span className={cn("flex items-center justify-end gap-1 text-sm", runwayDelta.color)}>
                          <runwayDelta.icon className="h-3 w-3" />
                          {runwayDelta.label}
                        </span>
                      )}
                      {isBaseline && <span className="text-muted-foreground">—</span>}
                    </TableCell>
                    
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <span className="font-mono font-semibold">
                          {scenario.survival_18m.toFixed(0)}%
                        </span>
                        <Badge {...getSurvivalBadge(scenario.survival_18m)} className="text-xs">
                          {getSurvivalBadge(scenario.survival_18m).label}
                        </Badge>
                      </div>
                    </TableCell>
                    
                    <TableCell className="text-right">
                      {!isBaseline && (
                        <span className={cn("flex items-center justify-end gap-1 text-sm", survivalDelta.color)}>
                          <survivalDelta.icon className="h-3 w-3" />
                          {survivalDelta.label}
                        </span>
                      )}
                      {isBaseline && <span className="text-muted-foreground">—</span>}
                    </TableCell>
                    
                    {scenarios.some(s => s.end_cash !== undefined) && (
                      <TableCell className="text-right font-mono">
                        {scenario.end_cash !== undefined ? formatCurrency(scenario.end_cash) : '—'}
                      </TableCell>
                    )}
                    
                    {scenarios.some(s => s.score !== undefined) && (
                      <TableCell className="text-right">
                        {scenario.score !== undefined && (
                          <span className="font-mono font-semibold">
                            {(scenario.score * 100).toFixed(0)}
                          </span>
                        )}
                      </TableCell>
                    )}
                    
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant={isSelected ? "default" : "outline"}
                        onClick={() => onSelectScenario?.(scenario.name)}
                        data-testid={`${testId}-select-${index}`}
                      >
                        {isSelected ? (
                          <>
                            <Check className="h-3 w-3 mr-1" />
                            Selected
                          </>
                        ) : (
                          'View'
                        )}
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
        
        <div className="mt-4 p-3 bg-muted/30 rounded-lg">
          <p className="text-xs text-muted-foreground">
            Scenarios are ranked by a composite score considering runway, survival probability, and financial efficiency. 
            Deltas show the change compared to the baseline scenario.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
