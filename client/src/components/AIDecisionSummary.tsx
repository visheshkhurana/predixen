import { useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Sparkles, TrendingUp, TrendingDown, Shield, AlertTriangle, CheckCircle, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AIDecisionSummaryProps {
  simulation: any;
  scenarioName: string;
  baselineSimulation?: any;
  counterMoves?: any;
  className?: string;
}

function fmtCurrency(val: number): string {
  const abs = Math.abs(val);
  if (abs >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `$${(val / 1_000).toFixed(0)}k`;
  return `$${val.toFixed(0)}`;
}

function inferAction(name: string): string {
  const n = name.toLowerCase();
  if (n.includes('hire') || n.includes('engineer') || n.includes('team')) return 'Make the hire';
  if (n.includes('raise') || n.includes('series') || n.includes('fund')) return 'Raise the round';
  if (n.includes('price') || n.includes('pricing')) return 'Push the price increase';
  if (n.includes('cut') || n.includes('reduce') || n.includes('layoff')) return 'Make the cut';
  if (n.includes('expand') || n.includes('market') || n.includes('launch')) return 'Launch it';
  if (n.includes('pivot')) return 'Make the pivot';
  if (n.includes('burn') && n.includes('reduc')) return 'Cut the burn';
  if (n.includes('churn')) return 'Fix the churn';
  if (n.includes('freeze')) return 'Freeze hiring';
  if (n.includes('baseline') || n.includes('base') || n.includes('current')) return 'Stay the course';
  return 'Move forward';
}

function bestCounterMove(counterMoves: any, runwayP50: number): { name: string; runwayGain: number } | null {
  if (!counterMoves) return null;
  let best: { name: string; runwayGain: number } | null = null;
  for (const [key, val] of Object.entries(counterMoves)) {
    if (!val || (val as any).error) continue;
    const v = val as any;
    const cmRunway = v.runway?.p50 ?? 0;
    const gain = cmRunway - runwayP50;
    if (gain > 0 && (!best || gain > best.runwayGain)) {
      best = { name: key.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()), runwayGain: gain };
    }
  }
  return best;
}

export function AIDecisionSummary({ simulation, scenarioName, baselineSimulation, counterMoves, className }: AIDecisionSummaryProps) {
  const analysis = useMemo(() => {
    if (!simulation) return null;

    const survival18m = simulation.survivalProbability?.['18m'] ?? simulation.survival?.['18m'] ?? 0;
    const runwayP50 = simulation.runway?.p50 ?? 0;
    const runwayP10 = simulation.runway?.p10 ?? 0;
    const runwayP90 = simulation.runway?.p90 ?? 0;
    const endCash = simulation.summary?.end_cash ?? 0;
    const monthlyBurn = simulation.summary?.monthly_burn ?? simulation.summary?.monthly_burn_p50 ?? 0;
    const breakeven = simulation.breakEvenMonth?.p50 ?? null;

    let verdict: 'go' | 'conditional' | 'no-go' = 'conditional';
    let verdictLabel = 'CONDITIONAL GO';
    let verdictColor = 'text-amber-600 dark:text-amber-400';
    let verdictBg = 'bg-amber-50/80 dark:bg-amber-950/30 border-amber-200/50 dark:border-amber-800/30';
    let verdictIcon = <AlertTriangle className="h-5 w-5 text-amber-500" />;

    if (survival18m >= 75 && runwayP50 >= 14) {
      verdict = 'go';
      verdictLabel = 'GO';
      verdictColor = 'text-emerald-600 dark:text-emerald-400';
      verdictBg = 'bg-emerald-50/80 dark:bg-emerald-950/30 border-emerald-200/50 dark:border-emerald-800/30';
      verdictIcon = <CheckCircle className="h-5 w-5 text-emerald-500" />;
    } else if (survival18m < 40 || runwayP50 < 8) {
      verdict = 'no-go';
      verdictLabel = 'NO-GO';
      verdictColor = 'text-red-600 dark:text-red-400';
      verdictBg = 'bg-red-50/80 dark:bg-red-950/30 border-red-200/50 dark:border-red-800/30';
      verdictIcon = <Shield className="h-5 w-5 text-red-500" />;
    }

    const action = inferAction(scenarioName);
    const cm = bestCounterMove(counterMoves ?? simulation.counter_moves, runwayP50);

    let bRunwayDelta = 0;
    let bSurvDelta = 0;
    if (baselineSimulation) {
      const bRunway = baselineSimulation.runway?.p50 ?? 0;
      const bSurv = baselineSimulation.survivalProbability?.['18m'] ?? baselineSimulation.survival?.['18m'] ?? 0;
      bRunwayDelta = runwayP50 - bRunway;
      bSurvDelta = survival18m - bSurv;
    }

    let headline = '';

    if (verdict === 'go') {
      if (bRunwayDelta > 2 && breakeven && breakeven <= 18) {
        headline = `${action}. Your unit economics support it \u2014 you gain ${bRunwayDelta.toFixed(0)} months of runway and hit breakeven by month ${breakeven}.`;
      } else if (bRunwayDelta > 0 && cm) {
        headline = `${action}. The numbers back you up \u2014 ${runwayP50.toFixed(0)} months of runway at ${survival18m.toFixed(0)}% survival. Pair with ${cm.name.toLowerCase()} for another +${cm.runwayGain.toFixed(0)} months.`;
      } else if (endCash > 500000 && runwayP50 >= 18) {
        headline = `${action}. You end with ${fmtCurrency(endCash)} in the bank and ${runwayP50.toFixed(0)} months of runway \u2014 this is a strong position.`;
      } else {
        headline = `${action}. ${survival18m.toFixed(0)}% survival and ${runwayP50.toFixed(0)} months of runway give you room to execute. The data says go.`;
      }
    } else if (verdict === 'no-go') {
      if (cm && cm.runwayGain >= 3) {
        headline = `Don't ${action.toLowerCase()} yet. At ${runwayP50.toFixed(0)} months runway and ${survival18m.toFixed(0)}% survival, you're exposed. ${cm.name} would add +${cm.runwayGain.toFixed(0)} months \u2014 do that first.`;
      } else if (monthlyBurn > 0 && endCash > 0 && endCash / monthlyBurn < 6) {
        headline = `Hold off. ${fmtCurrency(endCash)} end cash covers only ${(endCash / monthlyBurn).toFixed(0)} months of burn at ${fmtCurrency(monthlyBurn)}/mo. You need to cut burn or raise capital before this move.`;
      } else {
        headline = `This doesn't work yet. ${runwayP50.toFixed(0)} months of runway and ${survival18m.toFixed(0)}% survival is below the safety threshold. Restructure before committing.`;
      }
    } else {
      if (cm && cm.runwayGain >= 2) {
        headline = `Viable, but protect yourself. ${action} with a hedge \u2014 ${cm.name.toLowerCase()} adds +${cm.runwayGain.toFixed(0)} months of runway and moves this from conditional to go.`;
      } else if (bSurvDelta > 5 && bRunwayDelta > 0) {
        headline = `${action} \u2014 cautiously. You gain +${bSurvDelta.toFixed(0)}% survival and +${bRunwayDelta.toFixed(1)} months vs baseline, but keep a close eye on ${monthlyBurn > 0 ? `the ${fmtCurrency(monthlyBurn)}/mo burn` : 'your burn rate'}.`;
      } else if (breakeven && breakeven <= 20) {
        headline = `${action}, but watch the timing. Breakeven at month ${breakeven} is achievable, but ${runwayP50.toFixed(0)} months of runway doesn't leave much margin for slippage.`;
      } else {
        headline = `${action} is possible but needs guardrails. ${runwayP50.toFixed(0)} months runway at ${survival18m.toFixed(0)}% survival \u2014 not enough conviction to go all-in without a backup plan.`;
      }
    }

    const signals: Array<{ text: string; type: 'positive' | 'negative' | 'neutral' }> = [];

    if (runwayP50 >= 18) signals.push({ text: `${runwayP50.toFixed(0)}mo runway exceeds 18mo safety threshold`, type: 'positive' });
    else if (runwayP50 >= 12) signals.push({ text: `${runwayP50.toFixed(0)}mo runway is adequate but tight`, type: 'neutral' });
    else signals.push({ text: `${runwayP50.toFixed(0)}mo runway is below 12mo minimum`, type: 'negative' });

    if (survival18m >= 80) signals.push({ text: `${survival18m.toFixed(0)}% survival is strong`, type: 'positive' });
    else if (survival18m >= 50) signals.push({ text: `${survival18m.toFixed(0)}% survival needs improvement`, type: 'neutral' });
    else signals.push({ text: `${survival18m.toFixed(0)}% survival is critically low`, type: 'negative' });

    const spread = runwayP90 - runwayP10;
    if (spread > 15) signals.push({ text: `Wide range (${runwayP10.toFixed(0)}\u2013${runwayP90.toFixed(0)}mo) \u2014 high uncertainty`, type: 'negative' });
    else if (spread <= 6) signals.push({ text: `Tight range (${runwayP10.toFixed(0)}\u2013${runwayP90.toFixed(0)}mo) \u2014 predictable`, type: 'positive' });

    if (breakeven && breakeven <= 18) signals.push({ text: `Breakeven month ${breakeven} \u2014 strong unit economics`, type: 'positive' });
    else if (breakeven && breakeven > 24) signals.push({ text: `Breakeven beyond 24mo \u2014 capital risk`, type: 'negative' });

    if (monthlyBurn > 0 && endCash > 0) {
      const burnCoverage = endCash / monthlyBurn;
      if (burnCoverage < 6) signals.push({ text: `End cash covers only ${burnCoverage.toFixed(0)} months of burn`, type: 'negative' });
    }

    let baselineDelta = '';
    if (baselineSimulation) {
      if (bSurvDelta !== 0 || bRunwayDelta !== 0) {
        const parts = [];
        if (bRunwayDelta !== 0) parts.push(`${bRunwayDelta > 0 ? '+' : ''}${bRunwayDelta.toFixed(1)}mo runway`);
        if (bSurvDelta !== 0) parts.push(`${bSurvDelta > 0 ? '+' : ''}${bSurvDelta.toFixed(0)}% survival`);
        baselineDelta = `vs Baseline: ${parts.join(', ')}`;
      }
    }

    return { verdict, verdictLabel, verdictColor, verdictBg, verdictIcon, headline, signals, baselineDelta };
  }, [simulation, scenarioName, baselineSimulation, counterMoves]);

  if (!analysis) return null;

  return (
    <Card className={cn('overflow-visible border', analysis.verdictBg, className)} data-testid="card-ai-decision-summary">
      <CardContent className="pt-5 pb-4 px-5">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-0.5">
            <div className="h-9 w-9 rounded-md bg-primary/10 flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-primary" />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground" data-testid="text-ai-summary-title">Your Answer</h3>
              <Badge
                variant="outline"
                className={cn('text-xs font-bold gap-1', analysis.verdictColor)}
                data-testid="badge-verdict"
              >
                {analysis.verdictIcon}
                {analysis.verdictLabel}
              </Badge>
              {analysis.baselineDelta && (
                <Badge variant="secondary" className="text-[10px] gap-1" data-testid="badge-baseline-delta">
                  <ArrowRight className="h-3 w-3" />
                  {analysis.baselineDelta}
                </Badge>
              )}
            </div>

            <p className="text-sm font-medium leading-relaxed mb-3" data-testid="text-ai-headline">
              {analysis.headline}
            </p>

            <div className="flex flex-wrap gap-x-4 gap-y-1.5">
              {analysis.signals.slice(0, 4).map((signal, idx) => (
                <div key={idx} className="flex items-center gap-1.5" data-testid={`signal-item-${idx}`}>
                  {signal.type === 'positive' ? (
                    <TrendingUp className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0" />
                  ) : signal.type === 'negative' ? (
                    <TrendingDown className="h-3.5 w-3.5 text-red-500 flex-shrink-0" />
                  ) : (
                    <ArrowRight className="h-3.5 w-3.5 text-amber-500 flex-shrink-0" />
                  )}
                  <span className="text-xs text-muted-foreground">{signal.text}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
