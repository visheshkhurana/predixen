import { useState, useEffect, useMemo, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { SlidersHorizontal, TrendingUp, TrendingDown, Percent, DollarSign, Flame, RotateCcw, Play } from 'lucide-react';
import { cn, formatCurrencyAbbrev } from '@/lib/utils';
import { formatRunwayDisplay, isSustainable } from '@/lib/simulation/sensitivityAnalysis';

interface SliderConfig {
  key: string;
  label: string;
  icon: typeof TrendingUp;
  min: number;
  max: number;
  step: number;
  defaultValue: number;
  unit: string;
  format?: (value: number) => string;
}

interface WhatIfResults {
  runway: number;
  runwayChange: number;
  survival18m: number;
  survivalChange: number;
  cashAt18m: number;
  cashChange: number;
}

interface WhatIfExplorerProps {
  baselineState: any;
  baselineResults: { runway: number; survival18m: number; cashAt18m: number };
  onRunFullSimulation: (adjustments: Record<string, number>) => void;
  calculateQuickImpact: (adjustments: Record<string, number>) => WhatIfResults;
  testId?: string;
}

export function WhatIfExplorer({ 
  baselineState, 
  baselineResults,
  onRunFullSimulation, 
  calculateQuickImpact,
  testId = 'what-if-explorer'
}: WhatIfExplorerProps) {
  const sliderConfigs: SliderConfig[] = useMemo(() => [
    { key: 'revenueGrowth', label: 'Revenue Growth Rate', icon: TrendingUp, min: -30, max: 60, step: 1, defaultValue: baselineState?.monthlyGrowthRate || baselineState?.growthRate || 0, unit: '%' },
    { key: 'churnRate', label: 'Monthly Churn Rate', icon: TrendingDown, min: 0, max: 20, step: 0.5, defaultValue: baselineState?.churnRate ? (baselineState.churnRate > 1 ? baselineState.churnRate : baselineState.churnRate * 100) : 5, unit: '%' },
    { key: 'grossMargin', label: 'Gross Margin', icon: Percent, min: 30, max: 95, step: 1, defaultValue: baselineState?.grossMargin ? (baselineState.grossMargin > 1 ? baselineState.grossMargin : baselineState.grossMargin * 100) : 70, unit: '%' },
    { key: 'burnChange', label: 'Burn Rate Change', icon: Flame, min: -50, max: 100, step: 5, defaultValue: 0, unit: '%' },
    { key: 'fundraising', label: 'Fundraising Amount', icon: DollarSign, min: 0, max: 5000000, step: 100000, defaultValue: 0, unit: '$', format: (v) => formatCurrencyAbbrev(v) },
  ], [baselineState]);

  const [values, setValues] = useState<Record<string, number>>(() => 
    Object.fromEntries(sliderConfigs.map(s => [s.key, s.defaultValue]))
  );
  const [results, setResults] = useState<WhatIfResults | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);

  const debouncedCalculate = useCallback((vals: Record<string, number>) => {
    setIsCalculating(true);
    // Use setTimeout to debounce
    const timer = setTimeout(() => {
      const newResults = calculateQuickImpact(vals);
      setResults(newResults);
      setIsCalculating(false);
    }, 150);
    return () => clearTimeout(timer);
  }, [calculateQuickImpact]);

  useEffect(() => {
    const cleanup = debouncedCalculate(values);
    return cleanup;
  }, [values, debouncedCalculate]);

  const handleSliderChange = (key: string, value: number[]) => {
    setValues(prev => ({ ...prev, [key]: value[0] }));
  };

  const handleReset = () => {
    setValues(Object.fromEntries(sliderConfigs.map(s => [s.key, s.defaultValue])));
  };

  const getChangeColor = (change: number, higherIsBetter: boolean = true) => {
    if (Math.abs(change) < 0.01) return 'text-muted-foreground';
    const isPositive = higherIsBetter ? change > 0 : change < 0;
    return isPositive ? 'text-green-500' : 'text-red-500';
  };

  const getChangeIcon = (change: number, higherIsBetter: boolean = true) => {
    if (Math.abs(change) < 0.01) return null;
    const isPositive = higherIsBetter ? change > 0 : change < 0;
    return isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />;
  };

  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2">
          <SlidersHorizontal className="h-5 w-5" />
          What-If Explorer
        </CardTitle>
        <CardDescription>
          Drag sliders to see instant impact on your metrics
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6 mb-8">
          {sliderConfigs.map((config) => {
            const Icon = config.icon;
            return (
              <div key={config.key} className="space-y-3" data-testid={`slider-${config.key}`}>
                <div className="flex justify-between items-center">
                  <label className="text-sm text-foreground flex items-center gap-2">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    {config.label}
                  </label>
                  <span className="text-sm font-medium font-mono">
                    {config.format ? config.format(values[config.key]) : `${values[config.key]}${config.unit}`}
                  </span>
                </div>
                <Slider
                  value={[values[config.key]]}
                  min={config.min}
                  max={config.max}
                  step={config.step}
                  onValueChange={(value) => handleSliderChange(config.key, value)}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{config.format ? config.format(config.min) : `${config.min}${config.unit}`}</span>
                  <span>{config.format ? config.format(config.max) : `${config.max}${config.unit}`}</span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="border-t pt-6">
          <h4 className="text-sm font-medium text-muted-foreground mb-4 flex items-center gap-2">
            INSTANT IMPACT
            {isCalculating && <span className="animate-pulse text-primary text-xs">calculating...</span>}
          </h4>
          
          {results && (
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className={cn(
                "rounded-lg p-4 border transition-all",
                isSustainable(results.runway) ? 'border-green-500/30 bg-green-500/5' :
                results.runwayChange > 0.5 ? 'border-green-500/30 bg-green-500/5' : 
                results.runwayChange < -0.5 ? 'border-red-500/30 bg-red-500/5' : 
                'border-border bg-muted/30'
              )}>
                <div className="text-muted-foreground text-xs mb-1">Runway</div>
                <div className="text-xl font-semibold font-mono tracking-tight">{formatRunwayDisplay(results.runway)}</div>
                <div className={cn("text-sm flex items-center gap-1", 
                  isSustainable(results.runway) ? 'text-green-500' : 
                  isSustainable(baselineResults.runway) ? 'text-red-500' :
                  getChangeColor(results.runwayChange)
                )}>
                  {isSustainable(results.runway) && isSustainable(baselineResults.runway) 
                    ? 'Cash-flow positive' 
                    : isSustainable(results.runway) 
                    ? <><TrendingUp className="h-3 w-3" /> Now sustainable</>
                    : isSustainable(baselineResults.runway)
                    ? <><TrendingDown className="h-3 w-3" /> No longer sustainable</>
                    : <>{getChangeIcon(results.runwayChange)} {results.runwayChange > 0 ? '+' : ''}{results.runwayChange.toFixed(1).replace(/\.0$/, '')} months</>}
                </div>
              </div>
              
              <div className={cn(
                "rounded-lg p-4 border transition-all",
                results.survivalChange > 5 ? 'border-green-500/30 bg-green-500/5' : 
                results.survivalChange < -5 ? 'border-red-500/30 bg-red-500/5' : 
                'border-border bg-muted/30'
              )}>
                <div className="text-muted-foreground text-xs mb-1">Survival (18m)</div>
                <div className="text-xl font-semibold font-mono tracking-tight">{results.survival18m.toFixed(0)}%</div>
                <div className={cn("text-sm flex items-center gap-1", getChangeColor(results.survivalChange))}>
                  {getChangeIcon(results.survivalChange)}
                  {results.survivalChange > 0 ? '+' : ''}{results.survivalChange.toFixed(0)}%
                </div>
              </div>
              
              <div className={cn(
                "rounded-lg p-4 border transition-all",
                results.cashChange > 10000 ? 'border-green-500/30 bg-green-500/5' : 
                results.cashChange < -10000 ? 'border-red-500/30 bg-red-500/5' : 
                'border-border bg-muted/30'
              )}>
                <div className="text-muted-foreground text-xs mb-1">Cash at 18mo</div>
                <div className="text-xl font-semibold font-mono tracking-tight">{formatCurrencyAbbrev(results.cashAt18m)}</div>
                <div className={cn("text-sm flex items-center gap-1", getChangeColor(results.cashChange))}>
                  {getChangeIcon(results.cashChange)}
                  {results.cashChange > 0 ? '+' : ''}{formatCurrencyAbbrev(results.cashChange)}
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-between gap-2 flex-wrap">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              data-testid="button-reset-sliders"
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Reset to Baseline
            </Button>
            <Button
              onClick={() => onRunFullSimulation(values)}
              data-testid="button-run-monte-carlo"
            >
              <Play className="h-4 w-4 mr-2" />
              Run Full Monte Carlo
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default WhatIfExplorer;
