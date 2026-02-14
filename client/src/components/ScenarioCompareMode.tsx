import { useState, useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  GitCompare, Trophy, TrendingUp, TrendingDown,
  Minus, ArrowRight, X, Shield, DollarSign, Timer, Target
} from 'lucide-react';
import { cn, formatCurrencyAbbrev } from '@/lib/utils';

interface SimData {
  runway?: { p10?: number; p50?: number; p90?: number };
  survivalProbability?: Record<string, number>;
  survival?: Record<string, number>;
  breakEvenMonth?: { p10?: number; p50?: number; p90?: number; mean?: number };
  metrics?: {
    revenue?: Array<Record<string, number>>;
    cash?: Array<Record<string, number>>;
    burn?: Array<Record<string, number>>;
  };
  [key: string]: any;
}

interface ScenarioWithSim {
  id: number;
  name: string;
  latest_simulation?: SimData | null;
  created_at?: string;
  inputs_json?: Record<string, any>;
}

function getSurvival(sim: SimData, period: string): number {
  if (sim.survivalProbability?.[period] != null) return sim.survivalProbability[period];
  if (sim.survival?.[period] != null) return sim.survival[period];
  return 0;
}

function getMetricAtMonth(metrics: Array<Record<string, number>> | undefined, monthIdx: number, percentile: string): number {
  if (!metrics || !metrics.length) return 0;
  if (monthIdx < metrics.length) return metrics[monthIdx]?.[percentile] || 0;
  return metrics[metrics.length - 1]?.[percentile] || 0;
}

function fmt(value: number): string {
  return formatCurrencyAbbrev(value);
}

function DeltaIndicator({ value, baseline, unit, higherIsBetter = true }: { value: number; baseline: number; unit: string; higherIsBetter?: boolean }) {
  const delta = value - baseline;
  if (Math.abs(delta) < 0.1) return <span className="text-[10px] text-muted-foreground">-</span>;
  const isBetter = higherIsBetter ? delta > 0 : delta < 0;
  const Icon = delta > 0 ? TrendingUp : TrendingDown;
  const color = isBetter ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400';
  return (
    <span className={cn("flex items-center gap-0.5 text-[10px] font-medium", color)}>
      <Icon className="h-3 w-3" />
      {delta > 0 ? '+' : ''}{unit === 'mo' ? `${delta.toFixed(1)} mo` : unit === '%' ? `${delta.toFixed(0)}pp` : unit === 'currency' ? fmt(delta) : fmt(delta)}
    </span>
  );
}

function getBarBg(v: number): string {
  if (v >= 7) return 'bg-emerald-600';
  if (v >= 5) return 'bg-amber-600';
  return 'bg-red-600';
}

function ScoreBar({ value, max, label, color }: { value: number; max: number; label: string; color: string }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div>
      <div className="flex items-center justify-between mb-0.5">
        <span className="text-[10px] text-muted-foreground">{label}</span>
        <span className={cn("text-xs font-bold font-mono", color)}>{value}/{max}</span>
      </div>
      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all duration-500", getBarBg(value))} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function computeScore(sim: SimData): { risk: number; reward: number; capEff: number } {
  const survival = getSurvival(sim, '18m');
  const runway = sim.runway?.p50 ?? 0;
  const spread = (sim.runway?.p90 ?? 0) - (sim.runway?.p10 ?? 0);
  const breakeven = sim.breakEvenMonth?.p50 ?? 25;

  let risk = 1;
  if (survival >= 90 && runway >= 18) risk = 9;
  else if (survival >= 80 && runway >= 14) risk = 8;
  else if (survival >= 70 && runway >= 12) risk = 7;
  else if (survival >= 60 && runway >= 10) risk = 6;
  else if (survival >= 50 && runway >= 8) risk = 5;
  else if (survival >= 40) risk = 4;
  else if (survival >= 30) risk = 3;
  else if (survival >= 20) risk = 2;
  if (spread > 15) risk = Math.max(1, risk - 1);

  let reward = 5;
  if (survival >= 85 && runway >= 18) reward = 9;
  else if (survival >= 70) reward = 7;
  else if (survival >= 50) reward = 5;
  else reward = 3;

  let capEff = 5;
  if (breakeven <= 12 && runway >= 18) capEff = 10;
  else if (breakeven <= 15 && runway >= 14) capEff = 9;
  else if (breakeven <= 18 && runway >= 12) capEff = 8;
  else if (breakeven <= 20 && runway >= 10) capEff = 7;
  else if (breakeven <= 22) capEff = 6;
  else if (breakeven <= 24) capEff = 5;
  else capEff = 4;

  return {
    risk: Math.min(10, Math.max(1, risk)),
    reward: Math.min(10, Math.max(1, reward)),
    capEff: Math.min(10, Math.max(1, capEff)),
  };
}

function getScoreColor(v: number) {
  if (v >= 7) return 'text-emerald-600 dark:text-emerald-400';
  if (v >= 5) return 'text-amber-600 dark:text-amber-400';
  return 'text-red-600 dark:text-red-400';
}

interface ScenarioComparePickerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  scenarios: ScenarioWithSim[];
  onCompare: (ids: number[]) => void;
}

export function ScenarioComparePicker({ open, onOpenChange, scenarios, onCompare }: ScenarioComparePickerProps) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const simulated = scenarios.filter(s => s.latest_simulation);

  const toggle = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 3) next.add(id);
      return next;
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" data-testid="dialog-compare-picker">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitCompare className="h-5 w-5" />
            Compare Scenarios
          </DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">Select 2-3 simulated scenarios to compare side-by-side.</p>
        <ScrollArea className="max-h-[340px] pr-2">
          <div className="space-y-1.5">
            {simulated.length === 0 && (
              <p className="text-sm text-muted-foreground py-4 text-center">No simulated scenarios available. Run simulations first.</p>
            )}
            {simulated.map(s => {
              const sim = s.latest_simulation!;
              const survival = getSurvival(sim, '18m');
              const runway = sim.runway?.p50 ?? 0;
              const checked = selected.has(s.id);
              const disabled = !checked && selected.size >= 3;
              return (
                <div
                  key={s.id}
                  className={cn(
                    "flex items-center gap-3 p-2.5 rounded-md cursor-pointer transition-colors",
                    checked ? "bg-primary/10 border border-primary/30" : "hover-elevate",
                    disabled && "opacity-40 pointer-events-none"
                  )}
                  onClick={() => !disabled && toggle(s.id)}
                  data-testid={`compare-pick-${s.id}`}
                >
                  <Checkbox checked={checked} className="pointer-events-none" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{s.name}</p>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-[10px] text-muted-foreground">Runway {runway.toFixed(1)} mo</span>
                      <span className="text-[10px] text-muted-foreground">Survival {survival.toFixed(0)}%</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={() => { setSelected(new Set()); onOpenChange(false); }}
            data-testid="button-compare-cancel"
          >
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={selected.size < 2}
            onClick={() => { onCompare(Array.from(selected)); onOpenChange(false); }}
            data-testid="button-compare-go"
          >
            <GitCompare className="h-3.5 w-3.5 mr-1.5" />
            Compare {selected.size} Scenarios
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface ScenarioCompareModeProps {
  scenarios: ScenarioWithSim[];
  selectedIds: number[];
  onClose: () => void;
  onSelectScenario?: (id: number) => void;
}

export function ScenarioCompareMode({ scenarios, selectedIds, onClose, onSelectScenario }: ScenarioCompareModeProps) {
  const columns = useMemo(() => {
    return selectedIds
      .map(id => scenarios.find(s => s.id === id))
      .filter((s): s is ScenarioWithSim => !!s && !!s.latest_simulation);
  }, [scenarios, selectedIds]);

  if (columns.length < 2) return null;

  const bestRunway = Math.max(...columns.map(c => c.latest_simulation!.runway?.p50 ?? 0));
  const bestSurvival = Math.max(...columns.map(c => getSurvival(c.latest_simulation!, '18m')));
  const bestOverall = columns.reduce((best, c) => {
    const s = computeScore(c.latest_simulation!);
    const total = s.risk + s.reward + s.capEff;
    if (total > best.total) return { id: c.id, total };
    return best;
  }, { id: -1, total: 0 });

  const metrics = [
    { label: 'Runway (P50)', key: 'runway_p50', unit: 'mo', higherIsBetter: true },
    { label: 'Runway (P10)', key: 'runway_p10', unit: 'mo', higherIsBetter: true },
    { label: 'Runway (P90)', key: 'runway_p90', unit: 'mo', higherIsBetter: true },
    { label: '18-Month Survival', key: 'survival_18m', unit: '%', higherIsBetter: true },
    { label: '12-Month Survival', key: 'survival_12m', unit: '%', higherIsBetter: true },
    { label: 'Break-Even (P50)', key: 'breakeven', unit: 'mo', higherIsBetter: false },
    { label: 'Revenue @12m', key: 'rev_12', unit: 'currency', higherIsBetter: true },
    { label: 'Revenue @24m', key: 'rev_24', unit: 'currency', higherIsBetter: true },
    { label: 'Cash @24m', key: 'cash_24', unit: 'currency', higherIsBetter: true },
    { label: 'Burn @6m', key: 'burn_6', unit: 'currency', higherIsBetter: false },
  ];

  function getMetricValue(sim: SimData, key: string): number {
    switch (key) {
      case 'runway_p50': return sim.runway?.p50 ?? 0;
      case 'runway_p10': return sim.runway?.p10 ?? 0;
      case 'runway_p90': return sim.runway?.p90 ?? 0;
      case 'survival_18m': return getSurvival(sim, '18m');
      case 'survival_12m': return getSurvival(sim, '12m');
      case 'breakeven': return sim.breakEvenMonth?.p50 ?? 25;
      case 'rev_12': return getMetricAtMonth(sim.metrics?.revenue, 11, 'p50');
      case 'rev_24': return getMetricAtMonth(sim.metrics?.revenue, 23, 'p50');
      case 'cash_24': return getMetricAtMonth(sim.metrics?.cash, 23, 'p50');
      case 'burn_6': return getMetricAtMonth(sim.metrics?.burn, 5, 'p50');
      default: return 0;
    }
  }

  function formatVal(v: number, unit: string): string {
    if (unit === 'mo') return `${v.toFixed(1)} mo`;
    if (unit === '%') return `${v.toFixed(0)}%`;
    if (unit === 'currency') return fmt(v);
    return fmt(v);
  }

  const baselineCol = columns[0];

  return (
    <Card data-testid="card-compare-mode">
      <CardContent className="pt-4 pb-4 px-4">
        <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
          <div className="flex items-center gap-2">
            <GitCompare className="h-4 w-4 text-primary" />
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Side-by-Side Comparison
            </span>
            <Badge variant="outline" className="text-[10px]">{columns.length} scenarios</Badge>
          </div>
          <Button size="icon" variant="ghost" onClick={onClose} data-testid="button-compare-close">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="overflow-x-auto">
          <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(200px, 1fr))` }}>
            {columns.map((col, colIdx) => {
              const sim = col.latest_simulation!;
              const scores = computeScore(sim);
              const overall = Math.round((scores.risk + scores.reward + scores.capEff) / 3);
              const isBest = col.id === bestOverall.id;
              const survival = getSurvival(sim, '18m');
              const runway = sim.runway?.p50 ?? 0;

              return (
                <div
                  key={col.id}
                  className={cn(
                    "rounded-md border p-3 space-y-3 transition-all",
                    isBest && "border-primary bg-primary/5",
                    !isBest && "border-border"
                  )}
                  data-testid={`compare-col-${col.id}`}
                >
                  <div className="flex items-start justify-between gap-1">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold truncate">{col.name}</p>
                      {colIdx === 0 && <Badge variant="outline" className="text-[10px] mt-1">Anchor</Badge>}
                    </div>
                    {isBest && (
                      <Badge variant="default" className="shrink-0 text-[10px]">
                        <Trophy className="h-3 w-3 mr-0.5" /> Best
                      </Badge>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2 py-2 border-t border-b border-dashed">
                    <div className="text-center">
                      <p className="text-lg font-bold font-mono">{runway.toFixed(1)}</p>
                      <p className="text-[10px] text-muted-foreground">Runway (mo)</p>
                      {runway === bestRunway && <Badge variant="default" className="text-[9px] mt-0.5 px-1 py-0 h-3.5">Best</Badge>}
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold font-mono">{survival.toFixed(0)}%</p>
                      <p className="text-[10px] text-muted-foreground">18m Survival</p>
                      {survival === bestSurvival && <Badge variant="default" className="text-[9px] mt-0.5 px-1 py-0 h-3.5">Best</Badge>}
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <ScoreBar value={scores.risk} max={10} label="Risk" color={getScoreColor(scores.risk)} />
                    <ScoreBar value={scores.reward} max={10} label="Reward" color={getScoreColor(scores.reward)} />
                    <ScoreBar value={scores.capEff} max={10} label="Cap. Efficiency" color={getScoreColor(scores.capEff)} />
                    <div className="flex items-center justify-between pt-1 border-t">
                      <span className="text-[10px] font-semibold text-muted-foreground">OVERALL</span>
                      <span className={cn("text-sm font-bold font-mono", getScoreColor(overall))}>{overall}/10</span>
                    </div>
                  </div>

                  <div className="space-y-1.5 pt-1">
                    {metrics.map(m => {
                      const val = getMetricValue(sim, m.key);
                      const baselineVal = colIdx === 0 ? val : getMetricValue(baselineCol.latest_simulation!, m.key);
                      if (m.key.startsWith('rev_') || m.key.startsWith('cash_') || m.key === 'burn_6') {
                        if (val === 0 && baselineVal === 0) return null;
                      }
                      return (
                        <div key={m.key} className="flex items-center justify-between gap-1">
                          <span className="text-[10px] text-muted-foreground truncate">{m.label}</span>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <span className="text-xs font-mono font-medium">{formatVal(val, m.unit)}</span>
                            {colIdx > 0 && (
                              <DeltaIndicator value={val} baseline={baselineVal} unit={m.unit} higherIsBetter={m.higherIsBetter} />
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {onSelectScenario && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full mt-2"
                      onClick={() => onSelectScenario(col.id)}
                      data-testid={`compare-view-${col.id}`}
                    >
                      <ArrowRight className="h-3.5 w-3.5 mr-1.5" />
                      View Full Results
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
