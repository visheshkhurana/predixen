import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Target, Check, AlertTriangle, AlertCircle } from 'lucide-react';
import { calculateRunway, type FinancialState } from '@/lib/simulation/sensitivityAnalysis';
import { cn, formatCurrencyAbbrev } from '@/lib/utils';

interface BreakingPoint {
  variable: string;
  displayName: string;
  currentValue: number;
  breakingValue: number;
  percentageChange: number;
  unit: string;
  likelihood: 'low' | 'moderate' | 'high';
}

interface ReverseStressTestProps {
  currentState: FinancialState;
  testId?: string;
}

const likelihoodStyles = {
  low: { 
    badge: 'bg-green-500/10 text-green-500 border-green-500/30',
    bar: 'bg-green-500',
    icon: Check,
    label: 'Unlikely'
  },
  moderate: { 
    badge: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/30',
    bar: 'bg-yellow-500',
    icon: AlertTriangle,
    label: 'Possible'
  },
  high: { 
    badge: 'bg-red-500/10 text-red-500 border-red-500/30',
    bar: 'bg-red-500',
    icon: AlertCircle,
    label: 'Risky'
  },
};

export function ReverseStressTest({ currentState, testId = 'reverse-stress-test' }: ReverseStressTestProps) {
  const [targetMonths, setTargetMonths] = useState<string>('12');

  const breakingPoints = useMemo(() => {
    const target = parseInt(targetMonths);
    const variables = [
      { key: 'churnRate', displayName: 'Churn Rate', unit: '%', direction: 'increase' as const },
      { key: 'growthRate', displayName: 'Revenue Growth', unit: '%', direction: 'decrease' as const },
      { key: 'opex', displayName: 'Operating Expenses', unit: 'currency', direction: 'increase' as const },
      { key: 'grossMargin', displayName: 'Gross Margin', unit: '%', direction: 'decrease' as const },
    ];

    return variables.map(v => {
      const currentValue = currentState[v.key as keyof FinancialState] as number;
      let testValue = currentValue;
      const step = v.direction === 'increase' ? currentValue * 0.05 : -currentValue * 0.05;
      let iterations = 0;
      const maxIterations = 100;

      // Iteratively find breaking point
      while (iterations < maxIterations) {
        const testState = { ...currentState, [v.key]: testValue };
        const runway = calculateRunway(testState);
        
        if (runway <= target) break;
        
        testValue += step;
        iterations++;
        
        // Prevent going negative for percentages
        if (v.unit === '%' && v.direction === 'decrease' && testValue < 0) {
          testValue = 0;
          break;
        }
      }

      const percentChange = currentValue !== 0 ? ((testValue - currentValue) / currentValue) * 100 : 0;
      
      let likelihood: 'low' | 'moderate' | 'high' = 'low';
      if (Math.abs(percentChange) < 30) likelihood = 'high';
      else if (Math.abs(percentChange) < 60) likelihood = 'moderate';

      return {
        variable: v.key,
        displayName: v.displayName,
        currentValue,
        breakingValue: testValue,
        percentageChange: percentChange,
        unit: v.unit,
        likelihood,
      };
    });
  }, [currentState, targetMonths]);

  const formatValue = (value: number, unit: string) => {
    if (unit === 'currency') {
      return formatCurrencyAbbrev(value);
    }
    return `${value.toFixed(1)}${unit}`;
  };

  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Breaking Point Analysis
            </CardTitle>
            <CardDescription className="mt-1">
              What would have to go wrong to run out of cash?
            </CardDescription>
          </div>
          <Select value={targetMonths} onValueChange={setTargetMonths}>
            <SelectTrigger className="w-[120px]" data-testid="select-target-months">
              <SelectValue placeholder="Target" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="6">6 months</SelectItem>
              <SelectItem value="12">12 months</SelectItem>
              <SelectItem value="18">18 months</SelectItem>
              <SelectItem value="24">24 months</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {breakingPoints.map((bp) => {
            const styles = likelihoodStyles[bp.likelihood];
            const Icon = styles.icon;
            // Calculate bar width as inverse of likelihood (higher % change = safer = wider bar)
            const barWidth = Math.min(100, Math.abs(bp.percentageChange));
            
            return (
              <div key={bp.variable} className="rounded-lg p-4 border bg-muted/30" data-testid={`breaking-point-${bp.variable}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{bp.displayName}</span>
                  <Badge variant="outline" className={cn("text-xs", styles.badge)}>
                    <Icon className="h-3 w-3 mr-1" />
                    {styles.label}
                  </Badge>
                </div>
                
                <div className="flex items-center gap-4 text-sm mb-3">
                  <span className="text-muted-foreground">
                    Current: <span className="text-foreground font-mono">{formatValue(bp.currentValue, bp.unit)}</span>
                  </span>
                  <span className="text-muted-foreground">→</span>
                  <span className="text-muted-foreground">
                    Breaking: <span className="text-red-500 font-mono">{formatValue(bp.breakingValue, bp.unit)}</span>
                  </span>
                  <span className={cn("font-mono", bp.percentageChange > 0 ? 'text-red-500' : 'text-red-500')}>
                    ({bp.percentageChange > 0 ? '+' : ''}{bp.percentageChange.toFixed(0)}%)
                  </span>
                </div>
                
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className={cn("h-2 rounded-full transition-all", styles.bar)}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground mt-1">
                  <span>High risk</span>
                  <span>Low risk</span>
                </div>
              </div>
            );
          })}
        </div>
        
        <p className="text-muted-foreground text-xs text-center mt-4">
          Analysis shows how much each variable must change to reduce runway to {targetMonths} months
        </p>
      </CardContent>
    </Card>
  );
}

export default ReverseStressTest;
