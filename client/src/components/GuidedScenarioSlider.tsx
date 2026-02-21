import { useMemo } from 'react';
import { AnnotatedSlider } from '@/components/AnnotatedSlider';
import { Badge } from '@/components/ui/badge';
import { Info, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SliderBenchmark {
  label: string;
  value: number;
  min: number;
  max: number;
}

interface SliderContext {
  benchmarks: SliderBenchmark[];
  zoneRanges: {
    sustainable: [number, number];
    aggressive: [number, number];
    unrealistic: [number, number];
  };
}

interface GuidedScenariosSliderProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  icon?: React.ReactNode;
  tooltip?: string;
  example?: string;
  markers?: { value: number; label: string }[];
  testId?: string;
  benchmarkLabel?: string;
  benchmarkValue?: string;
  impactDescription?: string;
  baselineMetrics?: {
    cashOnHand: number;
    monthlyExpenses: number;
    monthlyRevenue: number;
    currentRunway: number;
  };
  paramKey?: string;
}

// Benchmark context for each slider parameter
const SLIDER_BENCHMARKS: Record<string, SliderContext> = {
  pricing_change_pct: {
    benchmarks: [
      { label: 'Conservative', value: 0, min: -5, max: 5 },
      { label: 'SaaS avg increases', value: 7, min: 5, max: 10 },
      { label: 'Aggressive', value: 15, min: 10, max: 20 },
    ],
    zoneRanges: {
      sustainable: [-5, 10],
      aggressive: [10, 20],
      unrealistic: [20, 50],
    },
  },
  growth_uplift_pct: {
    benchmarks: [
      { label: 'Seed avg (monthly)', value: 5, min: 3, max: 8 },
      { label: 'Series A target', value: 10, min: 8, max: 15 },
      { label: 'Hypergrowth', value: 20, min: 15, max: 30 },
    ],
    zoneRanges: {
      sustainable: [-10, 15],
      aggressive: [15, 25],
      unrealistic: [25, 50],
    },
  },
  burn_reduction_pct: {
    benchmarks: [
      { label: 'Top quartile reduction', value: 15, min: 10, max: 20 },
      { label: 'Moderate cuts', value: 25, min: 20, max: 30 },
      { label: 'Deep restructuring', value: 35, min: 30, max: 40 },
    ],
    zoneRanges: {
      sustainable: [0, 20],
      aggressive: [20, 35],
      unrealistic: [35, 50],
    },
  },
  gross_margin_delta_pct: {
    benchmarks: [
      { label: 'SaaS benchmark', value: 70, min: 65, max: 75 },
      { label: 'Efficiency gain', value: 10, min: 5, max: 15 },
      { label: 'Significant improvement', value: 20, min: 15, max: 25 },
    ],
    zoneRanges: {
      sustainable: [-5, 10],
      aggressive: [10, 20],
      unrealistic: [20, 50],
    },
  },
  churn_change_pct: {
    benchmarks: [
      { label: 'Best in class (<1%)', value: -1, min: -3, max: 0 },
      { label: 'Healthy (1-2%)', value: 0, min: -1, max: 2 },
      { label: 'Concerning (>3%)', value: 5, min: 3, max: 10 },
    ],
    zoneRanges: {
      sustainable: [-5, 2],
      aggressive: [2, 4],
      unrealistic: [4, 10],
    },
  },
  cac_change_pct: {
    benchmarks: [
      { label: 'Efficient acquisition', value: -15, min: -25, max: -10 },
      { label: 'Neutral efficiency', value: 0, min: -5, max: 5 },
      { label: 'Higher costs', value: 15, min: 10, max: 20 },
    ],
    zoneRanges: {
      sustainable: [-30, 0],
      aggressive: [0, 15],
      unrealistic: [15, 30],
    },
  },
};

function getZoneColor(value: number, zoneRanges: Record<string, [number, number]>): string {
  if (value >= zoneRanges.unrealistic[0] && value <= zoneRanges.unrealistic[1]) {
    return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
  }
  if (value >= zoneRanges.aggressive[0] && value <= zoneRanges.aggressive[1]) {
    return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20';
  }
  return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
}

function getZoneLabel(value: number, zoneRanges: Record<string, [number, number]>): string {
  if (value >= zoneRanges.unrealistic[0] && value <= zoneRanges.unrealistic[1]) {
    return 'Unrealistic';
  }
  if (value >= zoneRanges.aggressive[0] && value <= zoneRanges.aggressive[1]) {
    return 'Aggressive';
  }
  return 'Sustainable';
}

function estimateImpactOnRunway(
  paramKey: string,
  value: number,
  baselineMetrics?: GuidedScenariosSliderProps['baselineMetrics']
): string {
  if (!baselineMetrics) return '';

  const monthlyExpenses = baselineMetrics.monthlyExpenses;
  const monthlyRevenue = baselineMetrics.monthlyRevenue;
  const currentRunway = baselineMetrics.currentRunway;

  switch (paramKey) {
    case 'burn_reduction_pct': {
      const burnReduction = monthlyExpenses * (value / 100);
      const newExpenses = monthlyExpenses - burnReduction;
      const netBurn = newExpenses - monthlyRevenue;
      if (netBurn <= 0) return 'Path to profitability';
      const newRunway = baselineMetrics.cashOnHand / netBurn;
      const impactMonths = Math.round((newRunway - currentRunway) * 10) / 10;
      return impactMonths > 0
        ? `Impact: +${impactMonths} months runway`
        : `Impact: ${impactMonths} months runway`;
    }
    case 'growth_uplift_pct': {
      const revenueGain = monthlyRevenue * (value / 100);
      const netBurn = monthlyExpenses - (monthlyRevenue + revenueGain);
      if (netBurn <= 0) return 'Potential path to profitability';
      const newRunway = baselineMetrics.cashOnHand / netBurn;
      const impactMonths = Math.round((newRunway - currentRunway) * 10) / 10;
      return impactMonths > 0
        ? `Impact: +${impactMonths} months runway`
        : `Impact: ${impactMonths} months runway`;
    }
    case 'pricing_change_pct': {
      const revenueLift = monthlyRevenue * (value / 100);
      const netBurn = monthlyExpenses - (monthlyRevenue + revenueLift);
      if (netBurn <= 0) return 'Potential path to profitability';
      const newRunway = baselineMetrics.cashOnHand / netBurn;
      const impactMonths = Math.round((newRunway - currentRunway) * 10) / 10;
      return impactMonths > 0
        ? `Impact: +${impactMonths} months runway`
        : `Impact: ${impactMonths} months runway`;
    }
    default:
      return '';
  }
}

export function GuidedScenarioSlider({
  label,
  value,
  onChange,
  min,
  max,
  icon,
  tooltip,
  example,
  markers,
  testId,
  benchmarkLabel,
  benchmarkValue,
  impactDescription,
  baselineMetrics,
  paramKey,
}: GuidedScenariosSliderProps) {
  const context = paramKey ? SLIDER_BENCHMARKS[paramKey] : undefined;
  const zoneInfo = context && {
    color: getZoneColor(value, context.zoneRanges),
    label: getZoneLabel(value, context.zoneRanges),
  };

  const runwayImpact = useMemo(() => {
    return paramKey && baselineMetrics
      ? estimateImpactOnRunway(paramKey, value, baselineMetrics)
      : '';
  }, [paramKey, value, baselineMetrics]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          {icon && <div className="flex-shrink-0">{icon}</div>}
          <label className="text-sm font-medium">{label}</label>
        </div>
        {zoneInfo && (
          <Badge variant="outline" className={cn('text-xs font-medium', zoneInfo.color)}>
            {zoneInfo.label}
          </Badge>
        )}
      </div>

      <AnnotatedSlider
        label={label}
        value={value}
        onChange={onChange}
        min={min}
        max={max}
        tooltip={tooltip}
        example={example}
        markers={markers}
        testId={testId}
      />

      {/* Contextual guidance section */}
      <div className="space-y-2 pt-1">
        {context && (
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-md bg-muted/50 p-2">
              <p className="text-muted-foreground font-medium">Benchmark Range</p>
              <p className="font-mono text-foreground mt-0.5">
                {context.benchmarks[0].label}: {context.benchmarks[0].value}%
              </p>
              <p className="text-muted-foreground text-xs mt-1">
                SaaS avg: {context.benchmarks[1].value}%
              </p>
            </div>

            <div className="rounded-md bg-muted/50 p-2">
              <p className="text-muted-foreground font-medium">Your Setting</p>
              <p className="font-mono text-foreground mt-0.5">{value}%</p>
              {runwayImpact && (
                <p className="text-muted-foreground text-xs mt-1 line-clamp-2">
                  {runwayImpact}
                </p>
              )}
            </div>
          </div>
        )}

        {benchmarkValue && (
          <div className="flex items-start gap-2 rounded-md bg-blue-50 dark:bg-blue-900/20 p-2 border border-blue-200 dark:border-blue-800">
            <Info className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-blue-900 dark:text-blue-300">
              <span className="font-medium">{benchmarkLabel}:</span> {benchmarkValue}
            </p>
          </div>
        )}

        {impactDescription && (
          <div className="flex items-start gap-2 rounded-md bg-amber-50 dark:bg-amber-900/20 p-2 border border-amber-200 dark:border-amber-800">
            <AlertCircle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-amber-900 dark:text-amber-300">{impactDescription}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export { SLIDER_BENCHMARKS };
