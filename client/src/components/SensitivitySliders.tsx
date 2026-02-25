import { useState, useMemo, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import {
  SlidersHorizontal, TrendingUp, TrendingDown, Play,
  RotateCcw, Loader2, Zap
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface BaseMetrics {
  cashOnHand: number;
  monthlyExpenses: number;
  monthlyRevenue: number;
  currentRunway: number;
  growthRate: number;
  churnRate: number;
}

interface SliderConfig {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  default: number;
  higherIsBetter: boolean;
  description: string;
}

const SLIDER_CONFIGS: SliderConfig[] = [
  {
    key: 'churn_change_pct',
    label: 'Churn Rate',
    min: 0,
    max: 10,
    step: 0.5,
    unit: '%',
    default: 0,
    higherIsBetter: false,
    description: 'Monthly customer churn',
  },
  {
    key: 'burn_reduction_pct',
    label: 'Burn Reduction',
    min: 0,
    max: 50,
    step: 1,
    unit: '%',
    default: 0,
    higherIsBetter: true,
    description: 'Monthly expense reduction',
  },
  {
    key: 'pricing_change_pct',
    label: 'Price Increase',
    min: 0,
    max: 30,
    step: 1,
    unit: '%',
    default: 0,
    higherIsBetter: true,
    description: 'Revenue per customer uplift',
  },
];

function estimateImpact(
  baseMetrics: BaseMetrics,
  sliders: Record<string, number>
) {
  const churn = sliders.churn_change_pct ?? 0;
  const burnReduction = sliders.burn_reduction_pct ?? 0;
  const priceIncrease = sliders.pricing_change_pct ?? 0;

  const rawBaseNetBurn = baseMetrics.monthlyExpenses - baseMetrics.monthlyRevenue;
  const baseNetBurn = Math.max(1, rawBaseNetBurn);
  const adjustedExpenses = baseMetrics.monthlyExpenses * (1 - burnReduction / 100);
  const revenueWithPrice = baseMetrics.monthlyRevenue * (1 + priceIncrease / 100);
  const churnImpact = churn > 0 ? revenueWithPrice * (churn / 100) * 0.5 : 0;
  const adjustedRevenue = Math.max(0, revenueWithPrice - churnImpact);
  const rawNewNetBurn = adjustedExpenses - adjustedRevenue;
  const newNetBurn = rawNewNetBurn <= 0 ? rawNewNetBurn : Math.max(1, rawNewNetBurn);
  const isProfitable = rawBaseNetBurn <= 0;
  const newRunway = newNetBurn <= 0 ? 60 : baseMetrics.cashOnHand / newNetBurn;
  const baseRunway = isProfitable ? 60 : baseMetrics.cashOnHand / baseNetBurn;
  const runwayDelta = newRunway - baseRunway;

  const survivalBase = Math.min(95, Math.max(5, baseRunway >= 18 ? 85 : baseRunway >= 12 ? 65 : baseRunway >= 6 ? 35 : 15));
  const survivalNew = Math.min(95, Math.max(5, newRunway >= 18 ? 85 : newRunway >= 12 ? 65 : newRunway >= 6 ? 35 : 15));
  const survivalExtra = (burnReduction > 0 ? burnReduction * 0.3 : 0)
    + (priceIncrease > 0 ? priceIncrease * 0.2 : 0)
    - (churn > 0 ? churn * 2 : 0);
  const survivalDelta = (survivalNew - survivalBase) + survivalExtra;

  const monthlyBurnDelta = newNetBurn - baseNetBurn;

  return {
    runway: Math.max(0, newRunway),
    runwayDelta,
    survivalDelta: Math.round(survivalDelta),
    monthlyBurnDelta,
    newNetBurn,
    isChanged: churn > 0 || burnReduction > 0 || priceIncrease > 0,
  };
}

interface SensitivitySlidersProps {
  baseMetrics: BaseMetrics;
  onRunSimulation: (params: Record<string, any>) => void;
  isRunning?: boolean;
  testId?: string;
}

export function SensitivitySliders({
  baseMetrics,
  onRunSimulation,
  isRunning = false,
  testId = 'sensitivity-sliders',
}: SensitivitySlidersProps) {
  const [sliders, setSliders] = useState<Record<string, number>>(
    Object.fromEntries(SLIDER_CONFIGS.map(c => [c.key, c.default]))
  );
  const [expanded, setExpanded] = useState(false);

  const handleSliderChange = useCallback((key: string, value: number[]) => {
    setSliders(prev => ({ ...prev, [key]: value[0] }));
  }, []);

  const handleReset = useCallback(() => {
    setSliders(Object.fromEntries(SLIDER_CONFIGS.map(c => [c.key, c.default])));
  }, []);

  const impact = useMemo(() => estimateImpact(baseMetrics, sliders), [baseMetrics, sliders]);

  const handleRun = () => {
    const scenarioName = [];
    if (sliders.churn_change_pct > 0) scenarioName.push(`Churn ${sliders.churn_change_pct}%`);
    if (sliders.burn_reduction_pct > 0) scenarioName.push(`Cut burn ${sliders.burn_reduction_pct}%`);
    if (sliders.pricing_change_pct > 0) scenarioName.push(`Price +${sliders.pricing_change_pct}%`);
    const name = scenarioName.length > 0 ? scenarioName.join(' + ') : 'Custom Scenario';
    onRunSimulation({
      name,
      churn_change_pct: sliders.churn_change_pct,
      burn_reduction_pct: sliders.burn_reduction_pct,
      pricing_change_pct: sliders.pricing_change_pct,
      growth_uplift_pct: 0,
      gross_margin_delta_pct: 0,
      cac_change_pct: 0,
      fundraise_month: null,
      fundraise_amount: 0,
      tags: ['slider-scenario'],
    });
  };

  if (!expanded) {
    return (
      <div className="max-w-3xl mx-auto">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setExpanded(true)}
          className="w-full justify-center text-muted-foreground"
          data-testid={`${testId}-expand`}
        >
          <SlidersHorizontal className="h-3.5 w-3.5 mr-1.5" />
          Adjust Variables Manually
        </Button>
      </div>
    );
  }

  function fmt(v: number): string {
    if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
    if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
    return `$${v.toFixed(0)}`;
  }

  return (
    <Card className="max-w-3xl mx-auto" data-testid={testId}>
      <CardContent className="pt-4 pb-4 px-4">
        <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4 text-primary" />
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Sensitivity Sliders
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              disabled={!impact.isChanged}
              data-testid={`${testId}-reset`}
            >
              <RotateCcw className="h-3.5 w-3.5 mr-1" />
              Reset
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(false)}
              data-testid={`${testId}-collapse`}
            >
              Collapse
            </Button>
          </div>
        </div>

        <div className="space-y-5">
          {SLIDER_CONFIGS.map(config => {
            const value = sliders[config.key];
            const isActive = value !== config.default;
            return (
              <div key={config.key} data-testid={`${testId}-${config.key}`}>
                <div className="flex items-center justify-between mb-1.5 gap-2">
                  <div>
                    <span className="text-sm font-medium">{config.label}</span>
                    <span className="text-[10px] text-muted-foreground ml-2">{config.description}</span>
                  </div>
                  <Badge
                    variant={isActive ? 'default' : 'secondary'}
                    className="font-mono text-xs tabular-nums"
                  >
                    {value}{config.unit}
                  </Badge>
                </div>
                <Slider
                  value={[value]}
                  onValueChange={(v) => handleSliderChange(config.key, v)}
                  min={config.min}
                  max={config.max}
                  step={config.step}
                  className="w-full"
                  data-testid={`${testId}-slider-${config.key}`}
                />
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-[10px] text-muted-foreground">{config.min}{config.unit}</span>
                  <span className="text-[10px] text-muted-foreground">{config.max}{config.unit}</span>
                </div>
              </div>
            );
          })}
        </div>

        {impact.isChanged && (
          <div className="mt-4 p-3 rounded-md bg-muted/40 border border-dashed space-y-2" data-testid={`${testId}-preview`}>
            <div className="flex items-center gap-1.5 mb-1">
              <Zap className="h-3.5 w-3.5 text-primary" />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Estimated Impact Preview
              </span>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <p className="text-[10px] text-muted-foreground">Runway</p>
                <p className="text-sm font-bold font-mono">{impact.runway >= 900 ? 'Sustainable' : `${impact.runway.toFixed(1)} mo`}</p>
                <DeltaLabel value={impact.runwayDelta} suffix="mo" higherIsBetter />
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">Survival Impact</p>
                <p className="text-sm font-bold font-mono">
                  {impact.survivalDelta > 0 ? '+' : ''}{impact.survivalDelta}pp
                </p>
                <DeltaLabel value={impact.survivalDelta} suffix="pp" higherIsBetter />
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">Net Burn</p>
                <p className="text-sm font-bold font-mono">{fmt(impact.newNetBurn)}/mo</p>
                <DeltaLabel value={impact.monthlyBurnDelta} suffix="" higherIsBetter={false} isCurrency />
              </div>
            </div>
            <p className="text-[10px] text-muted-foreground text-center mt-1">
              This is a rough estimate. Run a full Monte Carlo simulation for precise results.
            </p>
          </div>
        )}

        <div className="mt-4 flex justify-end">
          <Button
            onClick={handleRun}
            disabled={!impact.isChanged || isRunning}
            data-testid={`${testId}-run`}
          >
            {isRunning ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Run Full Simulation
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function DeltaLabel({ value, suffix, higherIsBetter, isCurrency }: { value: number; suffix: string; higherIsBetter: boolean; isCurrency?: boolean }) {
  if (Math.abs(value) < 0.1) return null;
  const isBetter = higherIsBetter ? value > 0 : value < 0;
  const Icon = value > 0 ? TrendingUp : TrendingDown;
  const color = isBetter ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400';
  const display = isCurrency
    ? `${value > 0 ? '+' : ''}$${Math.abs(Math.round(value / 1000))}K`
    : `${value > 0 ? '+' : ''}${value.toFixed(1)} ${suffix}`;
  return (
    <span className={cn("flex items-center justify-center gap-0.5 text-[10px] font-medium", color)}>
      <Icon className="h-2.5 w-2.5" />
      {display}
    </span>
  );
}
