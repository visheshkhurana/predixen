import { useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  ArrowUp, ArrowDown, Minus, AlertTriangle,
  TrendingUp, TrendingDown, Timer, ArrowRight,
  DollarSign, PieChart, Fuel, Shield, Target
} from 'lucide-react';

interface SimulationData {
  runway?: { p10?: number; p50?: number; p90?: number };
  survivalProbability?: Record<string, number>;
  survival?: Record<string, number>;
  breakEvenMonth?: { p10?: number; p50?: number; p90?: number; mean?: number };
  metrics?: {
    revenue?: Array<Record<string, number>>;
    cash?: Array<Record<string, number>>;
    burn?: Array<Record<string, number>>;
  };
  survivalCurve?: Array<{ month: number; survival_rate: number }>;
  [key: string]: any;
}

interface ScenarioMeta {
  name?: string;
  tags?: string[];
}

function getSurvival(sim: SimulationData, period: string): number | null {
  if (sim.survivalProbability?.[period] != null) return sim.survivalProbability[period];
  if (sim.survival?.[period] != null) return sim.survival[period];
  return null;
}

function getMetricAtMonth(metrics: Array<Record<string, number>> | undefined, monthIdx: number, percentile: string): number {
  if (!metrics || !metrics.length) return 0;
  if (monthIdx < metrics.length) return metrics[monthIdx]?.[percentile] || 0;
  return metrics[metrics.length - 1]?.[percentile] || 0;
}

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function formatDelta(value: number, suffix: string = '', isPercent: boolean = false): string {
  const sign = value > 0 ? '+' : '';
  if (isPercent) return `${sign}${value.toFixed(0)}pp`;
  if (suffix === 'mo') return `${sign}${value.toFixed(1)} mo`;
  return `${sign}${formatCurrency(value)}`;
}

interface DeltaMetric {
  label: string;
  baseline: number;
  scenario: number;
  delta: number;
  isPercent?: boolean;
  suffix?: string;
  higherIsBetter: boolean;
}

function computeDeltas(baseline: SimulationData, scenario: SimulationData): DeltaMetric[] {
  const deltas: DeltaMetric[] = [];

  const bRunway = baseline.runway?.p50 ?? 0;
  const sRunway = scenario.runway?.p50 ?? 0;
  deltas.push({
    label: 'Runway (P50)',
    baseline: bRunway,
    scenario: sRunway,
    delta: sRunway - bRunway,
    suffix: 'mo',
    higherIsBetter: true,
  });

  const bSurvival = getSurvival(baseline, '18m') ?? 0;
  const sSurvival = getSurvival(scenario, '18m') ?? 0;
  deltas.push({
    label: '18-Month Survival',
    baseline: bSurvival,
    scenario: sSurvival,
    delta: sSurvival - bSurvival,
    isPercent: true,
    higherIsBetter: true,
  });

  const bRevenue = getMetricAtMonth(baseline.metrics?.revenue, 23, 'p50');
  const sRevenue = getMetricAtMonth(scenario.metrics?.revenue, 23, 'p50');
  if (bRevenue > 0 || sRevenue > 0) {
    deltas.push({
      label: 'Revenue @24mo',
      baseline: bRevenue,
      scenario: sRevenue,
      delta: sRevenue - bRevenue,
      higherIsBetter: true,
    });
  }

  const bBurn = getMetricAtMonth(baseline.metrics?.burn, 5, 'p50');
  const sBurn = getMetricAtMonth(scenario.metrics?.burn, 5, 'p50');
  if (bBurn > 0 || sBurn > 0) {
    deltas.push({
      label: 'Monthly Burn @6mo',
      baseline: bBurn,
      scenario: sBurn,
      delta: sBurn - bBurn,
      higherIsBetter: false,
    });
  }

  const bBreakeven = baseline.breakEvenMonth?.p50;
  const sBreakeven = scenario.breakEvenMonth?.p50;
  if (bBreakeven != null && sBreakeven != null && (bBreakeven <= 24 || sBreakeven <= 24)) {
    deltas.push({
      label: 'Break-even',
      baseline: Math.min(bBreakeven, 25),
      scenario: Math.min(sBreakeven, 25),
      delta: Math.min(sBreakeven, 25) - Math.min(bBreakeven, 25),
      suffix: 'mo',
      higherIsBetter: false,
    });
  }

  return deltas;
}

function DeltaIcon({ delta, higherIsBetter }: { delta: number; higherIsBetter: boolean }) {
  if (Math.abs(delta) < 0.1) return <Minus className="h-3.5 w-3.5 text-muted-foreground" />;
  const isPositive = higherIsBetter ? delta > 0 : delta < 0;
  if (isPositive) return <ArrowUp className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />;
  return <ArrowDown className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />;
}

function deltaColor(delta: number, higherIsBetter: boolean): string {
  if (Math.abs(delta) < 0.1) return 'text-muted-foreground';
  const isPositive = higherIsBetter ? delta > 0 : delta < 0;
  return isPositive
    ? 'text-emerald-600 dark:text-emerald-400'
    : 'text-red-600 dark:text-red-400';
}

export function BeforeAfterDeltaCards({
  baselineSimulation,
  scenarioSimulation,
  baselineName = 'Baseline',
  scenarioName = 'Scenario',
}: {
  baselineSimulation: SimulationData;
  scenarioSimulation: SimulationData;
  baselineName?: string;
  scenarioName?: string;
}) {
  const deltas = useMemo(
    () => computeDeltas(baselineSimulation, scenarioSimulation),
    [baselineSimulation, scenarioSimulation]
  );

  return (
    <Card data-testid="card-before-after-deltas">
      <CardContent className="pt-4 pb-4 px-4">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="h-4 w-4 text-primary" />
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Before / After Comparison
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {deltas.map((d) => (
            <div
              key={d.label}
              className="p-2.5 rounded-md bg-muted/40 space-y-1"
              data-testid={`delta-${d.label.toLowerCase().replace(/[\s@()]/g, '-')}`}
            >
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider truncate">{d.label}</p>
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-muted-foreground font-mono line-through">
                  {d.isPercent ? `${d.baseline.toFixed(0)}%` : d.suffix === 'mo' ? `${d.baseline.toFixed(1)}` : formatCurrency(d.baseline)}
                </span>
                <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                <span className="text-sm font-semibold font-mono">
                  {d.isPercent ? `${d.scenario.toFixed(0)}%` : d.suffix === 'mo' ? `${d.scenario.toFixed(1)}` : formatCurrency(d.scenario)}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <DeltaIcon delta={d.delta} higherIsBetter={d.higherIsBetter} />
                <span className={`text-xs font-semibold font-mono ${deltaColor(d.delta, d.higherIsBetter)}`}>
                  {formatDelta(d.delta, d.suffix, d.isPercent)}
                </span>
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-3 mt-3 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground/40" />
            {baselineName}
          </span>
          <span className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-primary" />
            {scenarioName}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

export function PaybackClock({
  simulation,
}: {
  simulation: SimulationData;
}) {
  const breakeven = useMemo(() => {
    const be = simulation.breakEvenMonth;
    if (!be) return null;
    return {
      p10: be.p10 ?? null,
      p50: be.p50 ?? null,
      p90: be.p90 ?? null,
      mean: be.mean ?? null,
    };
  }, [simulation]);

  if (!breakeven || breakeven.p50 == null) return null;

  const p50 = breakeven.p50;
  const isWithinHorizon = p50 <= 24;
  const displayMonths = isWithinHorizon ? Math.round(p50) : null;

  const progressPct = isWithinHorizon ? Math.min(100, (p50 / 24) * 100) : 100;
  const progressColor = p50 <= 12
    ? 'bg-emerald-500'
    : p50 <= 18
      ? 'bg-amber-500'
      : p50 <= 24
        ? 'bg-orange-500'
        : 'bg-red-500';

  return (
    <Card data-testid="card-payback-clock">
      <CardContent className="pt-4 pb-4 px-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-md bg-primary/10 shrink-0">
            <Timer className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-sm font-semibold">Payback Clock</h3>
              {isWithinHorizon && (
                <Badge variant="outline" className="text-[10px]">
                  {p50 <= 12 ? 'Fast' : p50 <= 18 ? 'Moderate' : 'Slow'}
                </Badge>
              )}
            </div>
            <p className="text-2xl font-bold font-mono tracking-tight" data-testid="text-payback-months">
              {isWithinHorizon ? (
                <>
                  {displayMonths} <span className="text-base font-normal text-muted-foreground">months</span>
                </>
              ) : (
                <span className="text-base text-muted-foreground">24+ months (beyond horizon)</span>
              )}
            </p>
            <div className="mt-2">
              <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
                <span>Now</span>
                <span>24 months</span>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${progressColor}`}
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
            {breakeven.p10 != null && breakeven.p90 != null && isWithinHorizon && (
              <p className="text-[11px] text-muted-foreground mt-1.5">
                Range: {Math.round(Math.min(breakeven.p10, breakeven.p90))} &ndash; {Math.round(Math.max(breakeven.p10, breakeven.p90))} months (P10&ndash;P90)
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function RiskAlertBanner({
  baselineSimulation,
  scenarioSimulation,
  scenarioName = 'This scenario',
}: {
  baselineSimulation: SimulationData;
  scenarioSimulation: SimulationData;
  scenarioName?: string;
}) {
  const alert = useMemo(() => {
    const bSurvival = getSurvival(baselineSimulation, '18m');
    const sSurvival = getSurvival(scenarioSimulation, '18m');
    if (bSurvival == null || sSurvival == null) return null;

    const drop = bSurvival - sSurvival;
    const isCritical = sSurvival < 50 || drop > 20;
    const isWarning = drop > 10 || sSurvival < 65;

    if (!isCritical && !isWarning) return null;

    const bRunway = baselineSimulation.runway?.p50 ?? 0;
    const sRunway = scenarioSimulation.runway?.p50 ?? 0;
    const runwayDrop = bRunway - sRunway;

    return {
      level: isCritical ? 'critical' as const : 'warning' as const,
      survivalDrop: drop,
      baselineSurvival: bSurvival,
      scenarioSurvival: sSurvival,
      runwayDrop,
      baselineRunway: bRunway,
      scenarioRunway: sRunway,
    };
  }, [baselineSimulation, scenarioSimulation]);

  if (!alert) return null;

  const isCritical = alert.level === 'critical';

  return (
    <Card
      className={`border-2 ${isCritical
        ? 'border-red-500/60 bg-red-50/40 dark:bg-red-950/20'
        : 'border-amber-500/60 bg-amber-50/40 dark:bg-amber-950/20'
      }`}
      data-testid="card-risk-alert"
    >
      <CardContent className="pt-4 pb-4 px-4">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-md shrink-0 ${isCritical ? 'bg-red-100 dark:bg-red-900/40' : 'bg-amber-100 dark:bg-amber-900/40'}`}>
            <AlertTriangle className={`h-5 w-5 ${isCritical ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h3 className={`text-sm font-semibold ${isCritical ? 'text-red-800 dark:text-red-200' : 'text-amber-800 dark:text-amber-200'}`}>
                {isCritical ? 'High Risk Alert' : 'Elevated Risk Warning'}
              </h3>
              <Badge variant="outline" className={`text-[10px] ${isCritical
                ? 'border-red-500/50 text-red-700 dark:text-red-300'
                : 'border-amber-500/50 text-amber-700 dark:text-amber-300'
              }`}>
                {isCritical ? 'Critical' : 'Warning'}
              </Badge>
            </div>
            <p className={`text-sm leading-relaxed ${isCritical ? 'text-red-700 dark:text-red-300' : 'text-amber-700 dark:text-amber-300'}`}>
              {scenarioName} drops 18-month survival from{' '}
              <strong>{alert.baselineSurvival.toFixed(0)}%</strong> to{' '}
              <strong>{alert.scenarioSurvival.toFixed(0)}%</strong>
              {alert.survivalDrop > 0 && (
                <> ({alert.survivalDrop.toFixed(0)}pp decrease)</>
              )}
              {alert.runwayDrop > 1 && (
                <>
                  {'. '}Runway shortens by <strong>{alert.runwayDrop.toFixed(1)} months</strong> (
                  {alert.baselineRunway.toFixed(1)} &rarr; {alert.scenarioRunway.toFixed(1)}).
                </>
              )}
              {alert.scenarioSurvival < 50 && ' Immediate corrective action recommended.'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function DataDrivenRecommendation({
  baselineSimulation,
  scenarioSimulation,
  baselineName = 'Baseline',
  scenarioName = 'This scenario',
}: {
  baselineSimulation: SimulationData | null;
  scenarioSimulation: SimulationData;
  baselineName?: string;
  scenarioName?: string;
}) {
  const insights = useMemo(() => {
    const runwayP50 = scenarioSimulation.runway?.p50 ?? 0;
    const runwayP10 = scenarioSimulation.runway?.p10 ?? 0;
    const runwayP90 = scenarioSimulation.runway?.p90 ?? 0;
    const survival18m = getSurvival(scenarioSimulation, '18m') ?? 0;
    const survival12m = getSurvival(scenarioSimulation, '12m') ?? 0;
    const breakeven = scenarioSimulation.breakEvenMonth?.p50 ?? 25;

    const sentences: string[] = [];
    const secondOrderEffects: string[] = [];

    if (baselineSimulation) {
      const bRunway = baselineSimulation.runway?.p50 ?? 0;
      const bSurvival = baselineSimulation.survival?.['18m'] ?? getSurvival(baselineSimulation, '18m') ?? 0;
      const runwayDelta = runwayP50 - bRunway;
      const survivalDelta = survival18m - bSurvival;

      const bRevenue24 = getMetricAtMonth(baselineSimulation.metrics?.revenue, 23, 'p50');
      const sRevenue24 = getMetricAtMonth(scenarioSimulation.metrics?.revenue, 23, 'p50');
      const revenueDeltaPct = bRevenue24 > 0 ? ((sRevenue24 - bRevenue24) / bRevenue24) * 100 : 0;

      if (Math.abs(survivalDelta) > 1) {
        sentences.push(
          `This move ${survivalDelta > 0 ? 'increases' : 'decreases'} survival probability by ${Math.abs(survivalDelta).toFixed(0)} percentage points${
            Math.abs(revenueDeltaPct) > 5
              ? ` but ${revenueDeltaPct > 0 ? 'increases' : 'reduces'} 24-month projected revenue by ${Math.abs(revenueDeltaPct).toFixed(0)}%`
              : ''
          }.`
        );
      }

      if (Math.abs(runwayDelta) > 0.5) {
        sentences.push(
          `Runway ${runwayDelta > 0 ? 'extends' : 'shrinks'} by ${Math.abs(runwayDelta).toFixed(1)} months (${bRunway.toFixed(1)} to ${runwayP50.toFixed(1)}).`
        );
      }

      const bBurn6 = getMetricAtMonth(baselineSimulation.metrics?.burn, 5, 'p50');
      const sBurn6 = getMetricAtMonth(scenarioSimulation.metrics?.burn, 5, 'p50');
      if (bBurn6 > 0 && sBurn6 > 0) {
        const burnDelta = ((sBurn6 - bBurn6) / bBurn6) * 100;
        if (Math.abs(burnDelta) > 10) {
          secondOrderEffects.push(
            `Burn rate ${burnDelta > 0 ? 'increases' : 'decreases'} by ${Math.abs(burnDelta).toFixed(0)}% within 6 months.`
          );
        }
      }

      const bRev12 = getMetricAtMonth(baselineSimulation.metrics?.revenue, 11, 'p50');
      const sRev12 = getMetricAtMonth(scenarioSimulation.metrics?.revenue, 11, 'p50');
      const bRev6 = getMetricAtMonth(baselineSimulation.metrics?.revenue, 5, 'p50');
      const sRev6 = getMetricAtMonth(scenarioSimulation.metrics?.revenue, 5, 'p50');
      if (bRev6 > 0 && sRev6 > 0 && bRev12 > 0 && sRev12 > 0) {
        const earlyGrowthDelta = ((sRev6 - bRev6) / bRev6) * 100;
        const lateGrowthDelta = ((sRev12 - bRev12) / bRev12) * 100;
        if (earlyGrowthDelta > 5 && lateGrowthDelta < earlyGrowthDelta * 0.5) {
          secondOrderEffects.push(
            'Revenue growth decelerates after month 6 as initial gains normalize. Plan for sustained investment to maintain momentum.'
          );
        }
      }
    }

    if (sentences.length === 0) {
      if (survival18m >= 80) {
        sentences.push(`Strong position: ${survival18m.toFixed(0)}% survival probability with ${runwayP50.toFixed(1)} months of runway.`);
      } else if (survival18m >= 50) {
        sentences.push(`Moderate position: ${survival18m.toFixed(0)}% survival at 18 months suggests manageable risk, but improvements should be explored.`);
      } else {
        sentences.push(`Elevated risk: Only ${survival18m.toFixed(0)}% survival probability. Prioritize runway extension through cost reduction or fundraising.`);
      }
    }

    let verdict: 'go' | 'conditional' | 'no-go' = 'conditional';
    if (baselineSimulation) {
      const bSurvival = getSurvival(baselineSimulation, '18m') ?? 0;
      const survivalDelta = survival18m - bSurvival;
      if (survivalDelta > 5 && survival18m >= 70) verdict = 'go';
      else if (survivalDelta < -15 || survival18m < 40) verdict = 'no-go';
    } else {
      if (survival18m >= 75) verdict = 'go';
      else if (survival18m < 40) verdict = 'no-go';
    }

    const spread = runwayP90 - runwayP10;
    let confidence: 'high' | 'medium' | 'low' = 'medium';
    if (spread < 6) confidence = 'high';
    else if (spread > 15) confidence = 'low';

    return { sentences, secondOrderEffects, verdict, confidence, spread, runwayP50, survival18m, breakeven };
  }, [baselineSimulation, scenarioSimulation]);

  const verdictConfig = {
    'go': { label: 'GO', color: 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-700' },
    'conditional': { label: 'CONDITIONAL', color: 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-700' },
    'no-go': { label: 'NO-GO', color: 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900/40 dark:text-red-300 dark:border-red-700' },
  };

  const v = verdictConfig[insights.verdict];

  return (
    <div className="space-y-3" data-testid="data-driven-recommendation">
      <div className="flex items-center gap-2 mb-1 flex-wrap">
        <Badge variant="outline" className={`text-xs font-bold px-2 ${v.color}`} data-testid="badge-verdict">
          {v.label}
        </Badge>
        <Badge variant="outline" className="text-[10px]" data-testid="badge-confidence">
          {insights.confidence === 'high' ? 'High' : insights.confidence === 'medium' ? 'Medium' : 'Low'} confidence
          (P10-P90 spread: {insights.spread.toFixed(1)} mo)
        </Badge>
      </div>
      {insights.sentences.map((s, i) => (
        <p key={i} className="text-sm text-muted-foreground leading-relaxed">{s}</p>
      ))}
      {insights.secondOrderEffects.length > 0 && (
        <div className="mt-2 pt-2 border-t border-dashed">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">Second-Order Effects</p>
          {insights.secondOrderEffects.map((e, i) => (
            <div key={i} className="flex items-start gap-2 mb-1">
              <TrendingDown className="h-3.5 w-3.5 text-amber-500 shrink-0 mt-0.5" />
              <p className="text-xs text-muted-foreground leading-relaxed">{e}</p>
            </div>
          ))}
        </div>
      )}
      {insights.breakeven <= 24 && (
        <p className="text-xs text-muted-foreground">
          Break-even projected at <strong>month {Math.round(insights.breakeven)}</strong>.
        </p>
      )}
    </div>
  );
}

interface FundraisingData {
  fundraise_amount: number;
  fundraise_month?: number;
  dilution: { low: number; mid: number; high: number };
  ownership_post_raise: { best_case: number; expected: number; worst_case: number };
  valuation_range: { low: number; mid: number; high: number };
  runway_extension_months: number;
  capital_efficiency: number;
  pre_raise_runway: number;
  post_raise_runway: number;
  monthly_burn: number;
  survival_lift_pct: number;
  runway_lift_months: number;
}

export function FundraisingIntelligence({
  data,
}: {
  data: FundraisingData;
}) {
  const efficiencyLabel = data.capital_efficiency >= 18 ? 'Excellent' : data.capital_efficiency >= 12 ? 'Good' : data.capital_efficiency >= 6 ? 'Fair' : 'Low';
  const efficiencyColor = data.capital_efficiency >= 18
    ? 'text-emerald-600 dark:text-emerald-400'
    : data.capital_efficiency >= 12
      ? 'text-emerald-600 dark:text-emerald-400'
      : data.capital_efficiency >= 6
        ? 'text-amber-600 dark:text-amber-400'
        : 'text-red-600 dark:text-red-400';

  return (
    <Card data-testid="card-fundraising-intelligence">
      <CardContent className="pt-4 pb-4 px-4">
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <DollarSign className="h-4 w-4 text-primary" />
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Fundraising Intelligence
          </span>
          <Badge variant="outline" className="text-[10px]">
            {formatCurrency(data.fundraise_amount)} raise
          </Badge>
          {data.fundraise_month && (
            <Badge variant="outline" className="text-[10px]">
              Month {data.fundraise_month}
            </Badge>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
          <div className="p-2.5 rounded-md bg-muted/40 space-y-1" data-testid="metric-dilution">
            <div className="flex items-center gap-1">
              <PieChart className="h-3 w-3 text-muted-foreground" />
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Dilution</p>
            </div>
            <p className="text-sm font-semibold font-mono" data-testid="text-dilution-mid">
              {data.dilution.mid.toFixed(1)}%
            </p>
            <p className="text-[10px] text-muted-foreground">
              {data.dilution.low.toFixed(1)}% &ndash; {data.dilution.high.toFixed(1)}%
            </p>
          </div>

          <div className="p-2.5 rounded-md bg-muted/40 space-y-1" data-testid="metric-ownership">
            <div className="flex items-center gap-1">
              <Shield className="h-3 w-3 text-muted-foreground" />
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Ownership</p>
            </div>
            <p className="text-sm font-semibold font-mono" data-testid="text-ownership-post">
              {data.ownership_post_raise.expected.toFixed(1)}%
            </p>
            <p className="text-[10px] text-muted-foreground">
              {data.ownership_post_raise.worst_case.toFixed(1)}% &ndash; {data.ownership_post_raise.best_case.toFixed(1)}%
            </p>
          </div>

          <div className="p-2.5 rounded-md bg-muted/40 space-y-1" data-testid="metric-runway-ext">
            <div className="flex items-center gap-1">
              <Fuel className="h-3 w-3 text-muted-foreground" />
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Runway Ext.</p>
            </div>
            <p className="text-sm font-semibold font-mono text-emerald-600 dark:text-emerald-400" data-testid="text-runway-extension">
              +{data.runway_extension_months.toFixed(1)} mo
            </p>
            <p className="text-[10px] text-muted-foreground">
              {data.pre_raise_runway.toFixed(1)} &rarr; {data.post_raise_runway.toFixed(1)} mo
            </p>
          </div>

          <div className="p-2.5 rounded-md bg-muted/40 space-y-1" data-testid="metric-cap-efficiency">
            <div className="flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-muted-foreground" />
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Cap. Efficiency</p>
            </div>
            <p className={`text-sm font-semibold font-mono ${efficiencyColor}`} data-testid="text-capital-efficiency">
              {data.capital_efficiency.toFixed(1)}
            </p>
            <p className="text-[10px] text-muted-foreground">
              mo / $1M &middot; {efficiencyLabel}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="p-2.5 rounded-md bg-muted/40 space-y-1" data-testid="metric-survival-lift">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Survival Lift</p>
            <div className="flex items-center gap-1">
              {data.survival_lift_pct > 0 && <ArrowUp className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />}
              <span className={`text-sm font-semibold font-mono ${data.survival_lift_pct > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'}`}>
                {data.survival_lift_pct > 0 ? '+' : ''}{data.survival_lift_pct.toFixed(1)}pp
              </span>
              <span className="text-[10px] text-muted-foreground">vs no raise</span>
            </div>
          </div>
          <div className="p-2.5 rounded-md bg-muted/40 space-y-1" data-testid="metric-valuation">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Implied Valuation</p>
            <p className="text-sm font-semibold font-mono">
              {formatCurrency(data.valuation_range.mid)}
            </p>
            <p className="text-[10px] text-muted-foreground">
              {formatCurrency(data.valuation_range.low)} &ndash; {formatCurrency(data.valuation_range.high)}
            </p>
          </div>
        </div>

        <div className="mt-3 pt-2 border-t border-dashed">
          <p className="text-[10px] text-muted-foreground">
            Monthly burn: {formatCurrency(data.monthly_burn)} &middot; Runway lift from raise: +{data.runway_lift_months.toFixed(1)} months (simulated)
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export function findBaselineScenario(scenarios: any[]): any | null {
  if (!scenarios || scenarios.length === 0) return null;
  const byTag = scenarios.find(
    (s: any) => s.tags?.includes('baseline') && s.latest_simulation
  );
  if (byTag) return byTag;
  const byName = scenarios.find(
    (s: any) =>
      s.name?.toLowerCase().includes('baseline') && s.latest_simulation
  );
  if (byName) return byName;
  const first = scenarios.find((s: any) => s.latest_simulation);
  return first || null;
}

interface CounterMoveResult {
  id: string;
  name: string;
  description: string;
  icon: string;
  overrides_applied: Record<string, number>;
  runway: { p10: number; p50: number; p90: number };
  survival: Record<string, number>;
  survivalProbability: Record<string, number>;
  breakEvenMonth: { p10: number; p50: number; p90: number };
}

const ICON_MAP: Record<string, typeof ArrowUp> = {
  'scissors': TrendingDown,
  'dollar-sign': TrendingUp,
  'user-minus': Timer,
};

function CounterMoveCard({
  move,
  currentSimulation,
  onApply,
}: {
  move: CounterMoveResult;
  currentSimulation: SimulationData;
  onApply?: (move: CounterMoveResult) => void;
}) {
  const currentRunway = currentSimulation.runway?.p50 ?? 0;
  const currentSurvival = getSurvival(currentSimulation, '18m') ?? 0;
  const moveRunway = move.runway?.p50 ?? 0;
  const moveSurvival = (move.survivalProbability?.['18m'] ?? move.survival?.['18m']) ?? 0;

  const runwayDelta = moveRunway - currentRunway;
  const survivalDelta = moveSurvival - currentSurvival;

  const isPositiveRunway = runwayDelta > 0.2;
  const isPositiveSurvival = survivalDelta > 1;
  const isNeutral = Math.abs(runwayDelta) <= 0.2 && Math.abs(survivalDelta) <= 1;

  const IconComponent = ICON_MAP[move.icon] || ArrowRight;

  return (
    <Card
      className="hover-elevate transition-all"
      data-testid={`card-counter-move-${move.id}`}
    >
      <CardContent className="pt-4 pb-3 px-4">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-md shrink-0 ${
            isNeutral
              ? 'bg-muted'
              : isPositiveSurvival || isPositiveRunway
                ? 'bg-emerald-100 dark:bg-emerald-900/30'
                : 'bg-amber-100 dark:bg-amber-900/30'
          }`}>
            <IconComponent className={`h-4 w-4 ${
              isNeutral
                ? 'text-muted-foreground'
                : isPositiveSurvival || isPositiveRunway
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-amber-600 dark:text-amber-400'
            }`} />
          </div>
          <div className="flex-1 min-w-0 space-y-2">
            <div>
              <p className="text-sm font-semibold leading-tight">{move.name}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{move.description}</p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2 rounded-md bg-muted/40">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Runway</p>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className="text-sm font-semibold font-mono">{moveRunway.toFixed(1)}mo</span>
                  <span className={`text-xs font-mono ${deltaColor(runwayDelta, true)}`}>
                    {runwayDelta > 0 ? '+' : ''}{runwayDelta.toFixed(1)}
                  </span>
                </div>
              </div>
              <div className="p-2 rounded-md bg-muted/40">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Survival</p>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className="text-sm font-semibold font-mono">{moveSurvival.toFixed(0)}%</span>
                  <span className={`text-xs font-mono ${deltaColor(survivalDelta, true)}`}>
                    {survivalDelta > 0 ? '+' : ''}{survivalDelta.toFixed(0)}pp
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
        {onApply && (
          <div className="mt-3 pt-2 border-t">
            <button
              onClick={() => onApply(move)}
              className="w-full text-xs font-medium text-primary hover:underline text-center py-1"
              data-testid={`button-apply-counter-move-${move.id}`}
            >
              Apply this counter-move
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function CounterMoveCards({
  counterMoves,
  currentSimulation,
  isLoading,
  hasFailed,
  onRetry,
  onApply,
}: {
  counterMoves: CounterMoveResult[] | null;
  currentSimulation: SimulationData;
  isLoading: boolean;
  hasFailed?: boolean;
  onRetry?: () => void;
  onApply?: (move: CounterMoveResult) => void;
}) {
  if (!counterMoves && !isLoading && !hasFailed) {
    return null;
  }

  if (hasFailed && !isLoading && !counterMoves) {
    return (
      <Card data-testid="card-counter-moves-failed">
        <CardContent className="pt-4 pb-4 px-4">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-2 min-w-0">
              <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
              <div>
                <p className="text-sm font-semibold">Counter-moves failed to load</p>
                <p className="text-xs text-muted-foreground">
                  Automatic counter-move analysis could not be completed
                </p>
              </div>
            </div>
            {onRetry && (
              <button
                onClick={onRetry}
                className="text-xs font-medium text-primary hover:underline shrink-0"
                data-testid="button-retry-counter-moves"
              >
                Retry
              </button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3" data-testid="section-counter-moves">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-500" />
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Automatic Counter-Moves
        </span>
        {isLoading && (
          <div className="h-3 w-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        )}
      </div>
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="pt-4 pb-3 px-4">
                <div className="space-y-3 animate-pulse">
                  <div className="flex items-start gap-3">
                    <div className="h-8 w-8 rounded-md bg-muted" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 w-24 rounded bg-muted" />
                      <div className="h-3 w-32 rounded bg-muted" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="h-12 rounded bg-muted" />
                    <div className="h-12 rounded bg-muted" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : counterMoves ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {counterMoves.map((move) => (
            <CounterMoveCard
              key={move.id}
              move={move}
              currentSimulation={currentSimulation}
              onApply={onApply}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function getBaselineSimulation(
  scenarios: any[],
  currentScenarioId: number | null
): { simulation: SimulationData | null; name: string } {
  const baseline = findBaselineScenario(
    scenarios?.filter((s: any) => s.id !== currentScenarioId) || []
  );
  if (!baseline?.latest_simulation) return { simulation: null, name: 'Baseline' };
  return {
    simulation: baseline.latest_simulation as SimulationData,
    name: baseline.name || 'Baseline',
  };
}

interface ScoreItem {
  label: string;
  value: number;
  max: number;
  suffix: string;
  color: string;
  bgColor: string;
}

function computeDecisionScores(
  scenario: SimulationData,
  baseline: SimulationData | null
): ScoreItem[] {
  const survival18m = getSurvival(scenario, '18m') ?? 0;
  const runwayP50 = scenario.runway?.p50 ?? 0;
  const runwayP10 = scenario.runway?.p10 ?? 0;
  const runwayP90 = scenario.runway?.p90 ?? 0;
  const spread = runwayP90 - runwayP10;

  let riskScore: number;
  if (survival18m >= 90 && runwayP50 >= 18) riskScore = 9;
  else if (survival18m >= 80 && runwayP50 >= 14) riskScore = 8;
  else if (survival18m >= 70 && runwayP50 >= 12) riskScore = 7;
  else if (survival18m >= 60 && runwayP50 >= 10) riskScore = 6;
  else if (survival18m >= 50 && runwayP50 >= 8) riskScore = 5;
  else if (survival18m >= 40) riskScore = 4;
  else if (survival18m >= 30) riskScore = 3;
  else if (survival18m >= 20) riskScore = 2;
  else riskScore = 1;
  if (spread > 15) riskScore = Math.max(1, riskScore - 1);
  riskScore = Math.min(10, Math.max(1, riskScore));

  let rewardScore: number;
  if (baseline) {
    const bRevenue24 = getMetricAtMonth(baseline.metrics?.revenue, 23, 'p50');
    const sRevenue24 = getMetricAtMonth(scenario.metrics?.revenue, 23, 'p50');
    const revGrowthPct = bRevenue24 > 0 ? ((sRevenue24 - bRevenue24) / bRevenue24) * 100 : 0;
    const bRunway = baseline.runway?.p50 ?? 0;
    const runwayGain = runwayP50 - bRunway;

    if (revGrowthPct > 30 && runwayGain > 3) rewardScore = 10;
    else if (revGrowthPct > 20 || runwayGain > 5) rewardScore = 9;
    else if (revGrowthPct > 10 || runwayGain > 3) rewardScore = 8;
    else if (revGrowthPct > 5 || runwayGain > 1) rewardScore = 7;
    else if (revGrowthPct > 0 || runwayGain > 0) rewardScore = 6;
    else if (revGrowthPct > -5) rewardScore = 5;
    else if (revGrowthPct > -15) rewardScore = 4;
    else rewardScore = 3;
  } else {
    if (survival18m >= 85 && runwayP50 >= 18) rewardScore = 9;
    else if (survival18m >= 70) rewardScore = 7;
    else if (survival18m >= 50) rewardScore = 5;
    else rewardScore = 3;
  }
  rewardScore = Math.min(10, Math.max(1, rewardScore));

  let capEffScore: number;
  const breakeven = scenario.breakEvenMonth?.p50 ?? 25;
  if (breakeven <= 12 && runwayP50 >= 18) capEffScore = 10;
  else if (breakeven <= 15 && runwayP50 >= 14) capEffScore = 9;
  else if (breakeven <= 18 && runwayP50 >= 12) capEffScore = 8;
  else if (breakeven <= 20 && runwayP50 >= 10) capEffScore = 7;
  else if (breakeven <= 22) capEffScore = 6;
  else if (breakeven <= 24) capEffScore = 5;
  else capEffScore = 4;
  if (runwayP50 >= 24) capEffScore = Math.min(10, capEffScore + 1);
  capEffScore = Math.min(10, Math.max(1, capEffScore));

  let survivalImpact: number;
  if (baseline) {
    const bSurvival = getSurvival(baseline, '18m') ?? 0;
    survivalImpact = survival18m - bSurvival;
  } else {
    survivalImpact = survival18m - 50;
  }

  const riskColor = riskScore >= 7 ? 'text-emerald-600 dark:text-emerald-400' : riskScore >= 5 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400';
  const riskBg = riskScore >= 7 ? 'bg-emerald-500' : riskScore >= 5 ? 'bg-amber-500' : 'bg-red-500';
  const rewardColor = rewardScore >= 7 ? 'text-emerald-600 dark:text-emerald-400' : rewardScore >= 5 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400';
  const rewardBg = rewardScore >= 7 ? 'bg-emerald-500' : rewardScore >= 5 ? 'bg-amber-500' : 'bg-red-500';
  const capColor = capEffScore >= 7 ? 'text-emerald-600 dark:text-emerald-400' : capEffScore >= 5 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400';
  const capBg = capEffScore >= 7 ? 'bg-emerald-500' : capEffScore >= 5 ? 'bg-amber-500' : 'bg-red-500';
  const survColor = survivalImpact > 5 ? 'text-emerald-600 dark:text-emerald-400' : survivalImpact >= -5 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400';
  const survBg = survivalImpact > 5 ? 'bg-emerald-500' : survivalImpact >= -5 ? 'bg-amber-500' : 'bg-red-500';

  return [
    { label: 'Risk', value: riskScore, max: 10, suffix: '/10', color: riskColor, bgColor: riskBg },
    { label: 'Reward', value: rewardScore, max: 10, suffix: '/10', color: rewardColor, bgColor: rewardBg },
    { label: 'Capital Efficiency', value: capEffScore, max: 10, suffix: '/10', color: capColor, bgColor: capBg },
    { label: 'Survival Impact', value: Math.round(survivalImpact), max: 100, suffix: '%', color: survColor, bgColor: survBg },
  ];
}

export function DecisionScoreCard({
  scenarioSimulation,
  baselineSimulation,
}: {
  scenarioSimulation: SimulationData;
  baselineSimulation: SimulationData | null;
}) {
  const scores = useMemo(
    () => computeDecisionScores(scenarioSimulation, baselineSimulation),
    [scenarioSimulation, baselineSimulation]
  );

  const overallScore = Math.round(
    (scores[0].value + scores[1].value + scores[2].value) / 3
  );
  const overallColor = overallScore >= 7
    ? 'text-emerald-600 dark:text-emerald-400'
    : overallScore >= 5
      ? 'text-amber-600 dark:text-amber-400'
      : 'text-red-600 dark:text-red-400';

  return (
    <Card data-testid="card-decision-score">
      <CardContent className="pt-4 pb-4 px-4">
        <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Target className="h-4 w-4 text-primary" />
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Decision Score
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Overall</span>
            <span className={`text-lg font-bold font-mono ${overallColor}`} data-testid="text-overall-score">
              {overallScore}/10
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-x-6 gap-y-4">
          {scores.map((score) => (
            <div key={score.label} data-testid={`score-${score.label.toLowerCase().replace(/\s/g, '-')}`}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium">{score.label}</span>
                <span className={`text-sm font-bold font-mono ${score.color}`}>
                  {score.label === 'Survival Impact'
                    ? `${score.value > 0 ? '+' : ''}${score.value}${score.suffix}`
                    : `${score.value}${score.suffix}`
                  }
                </span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ease-out ${score.bgColor}`}
                  style={{
                    width: score.label === 'Survival Impact'
                      ? `${Math.min(100, Math.max(5, Math.abs(score.value)))}%`
                      : `${(score.value / score.max) * 100}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
