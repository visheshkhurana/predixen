import { useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Sparkles, Shield, AlertTriangle, CheckCircle, ArrowRight, CircleAlert, Target, Activity } from 'lucide-react';
import { cn, isRunwaySustainable, formatCurrencyAbbrev } from '@/lib/utils';
import { describeRunwayChange, runwayChange, runwayDeltaForScoring, runwaySentence, scenarioConsistency, SIM_HORIZON_MONTHS, type ScenarioInputs } from '@/lib/simulationConsistency';

function fmtRunway(v: number): string {
  if (isRunwaySustainable(v)) return 'sustainable';
  return v.toFixed(0);
}

/** "18 months of runway", "more than 24 months of runway" or "a sustainable runway". */
const runwayPhrase = runwaySentence;

interface AIDecisionSummaryProps {
  simulation: any;
  scenarioName: string;
  baselineSimulation?: any;
  counterMoves?: any;
  /** The scenario's levers, so a result that contradicts them gets no verdict. */
  scenarioInputs?: ScenarioInputs | null;
  /** Dashboard runway (cash ÷ burn), used for the consistency check when no baseline run exists. */
  dashboardRunway?: number | null;
  className?: string;
}

function fmtCurrency(val: number): string {
  return formatCurrencyAbbrev(val);
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

interface CounterMovePick { name: string; runwayGain: number; gainText: string }

function bestCounterMove(counterMoves: any, runwayP50: number): CounterMovePick | null {
  if (!counterMoves) return null;
  let best: CounterMovePick | null = null;
  const entries: Array<[string, any]> = Array.isArray(counterMoves)
    ? counterMoves.map((v: any, i: number) => [String(i), v])
    : Object.entries(counterMoves);
  for (const [key, val] of entries) {
    if (!val || (val as any).error) continue;
    const v = val as any;
    // Arrays have numeric keys: the name must come from the move itself
    // ("Pair with 0" was the array index).
    const rawName: string | undefined = v.name || v.label || (/^\d+$/.test(key) ? undefined : key);
    if (!rawName) continue;
    const change = runwayChange(runwayP50, v.runway?.p50);
    let gain = 0;
    let gainText = '';
    if (change.kind === 'months' && change.months > 0) {
      gain = change.months;
      gainText = `+${change.months.toFixed(0)} months of runway`;
    } else if (change.kind === 'becomes_sustainable') {
      gain = 12;
      gainText = 'a sustainable runway';
    } else {
      continue;
    }
    if (!best || gain > best.runwayGain) {
      best = { name: rawName.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()), runwayGain: gain, gainText };
    }
  }
  return best;
}

export function AIDecisionSummary({ simulation, scenarioName, baselineSimulation, counterMoves, scenarioInputs, dashboardRunway, className }: AIDecisionSummaryProps) {
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

    const action = inferAction(scenarioName);
    const cm = bestCounterMove(counterMoves ?? simulation.counter_moves, runwayP50);

    let bRunwayDelta = 0;
    let bSurvDelta = 0;
    let change: ReturnType<typeof runwayChange> | null = null;
    let bRunwayForCheck: number | null = null;
    let bSurvForCheck: number | null = null;
    if (baselineSimulation) {
      const bRunway = baselineSimulation.runway?.p50 ?? 0;
      const bSurv = baselineSimulation.survivalProbability?.['18m'] ?? baselineSimulation.survival?.['18m'] ?? 0;
      change = runwayChange(bRunway, runwayP50);
      // Sentinel-safe: 999 ("never ran out") is never subtracted.
      bRunwayDelta = runwayDeltaForScoring(change);
      bSurvDelta = survival18m - bSurv;
      bRunwayForCheck = bRunway;
      bSurvForCheck = bSurv;
    }
    const consistency = baselineSimulation
      ? scenarioConsistency(scenarioInputs, { runwayP50: bRunwayForCheck, survival18m: bSurvForCheck }, { runwayP50, survival18m })
      : scenarioConsistency(scenarioInputs, dashboardRunway != null ? { runwayP50: dashboardRunway } : null, { runwayP50, survival18m }, { approximate: true });
    const gainPhrase = change?.kind === 'becomes_sustainable'
      ? 'your runway becomes sustainable'
      : `you gain ${bRunwayDelta.toFixed(0)} months of runway`;


    const burnIncreaseWarning = baselineSimulation
      ? (() => {
          const baseBurn = baselineSimulation.summary?.monthly_burn ?? baselineSimulation.summary?.monthly_burn_p50 ?? 0;
          const burnIncreasePct = baseBurn > 0 ? Math.round(((monthlyBurn - baseBurn) / baseBurn) * 100) : 0;
          return burnIncreasePct >= 40 ? burnIncreasePct : 0;
        })()
      : 0;

    const hasNegativeImpact = bRunwayDelta < -3 || bSurvDelta < -10;
    const hasSevereNegativeImpact = bRunwayDelta < -8 || bSurvDelta < -20;

    if (survival18m < 40 || runwayP50 < 8 || hasSevereNegativeImpact) {
      verdict = 'no-go';
      verdictLabel = 'NO-GO';
      verdictColor = 'text-red-600 dark:text-red-400';
      verdictBg = 'bg-red-50/80 dark:bg-red-950/30 border-red-200/50 dark:border-red-800/30';
      verdictIcon = <Shield className="h-5 w-5 text-red-500" />;
    } else if (survival18m >= 75 && runwayP50 >= 14 && !hasNegativeImpact) {
      if (burnIncreaseWarning >= 40) {
        verdict = 'conditional';
        verdictLabel = 'CONDITIONAL GO';
      } else {
        verdict = 'go';
        verdictLabel = 'GO';
        verdictColor = 'text-emerald-600 dark:text-emerald-400';
        verdictBg = 'bg-emerald-50/80 dark:bg-emerald-950/30 border-emerald-200/50 dark:border-emerald-800/30';
        verdictIcon = <CheckCircle className="h-5 w-5 text-emerald-500" />;
      }
    }

    let headline = '';

    if (verdict === 'go') {
      if (bRunwayDelta > 2 && breakeven && breakeven <= 18) {
        headline = `${action}. Your unit economics support it \u2014 ${gainPhrase} and hit breakeven by month ${breakeven}.`;
      } else if (bRunwayDelta > 0 && cm) {
        headline = `${action}. The numbers back you up \u2014 ${runwayPhrase(runwayP50)} at ${survival18m.toFixed(0)}% survival. Pair with ${cm.name.toLowerCase()} for ${cm.gainText}.`;
      } else if (endCash > 500000 && runwayP50 >= 18) {
        headline = `${action}. You end with ${fmtCurrency(endCash)} in the bank and ${runwayPhrase(runwayP50)} \u2014 this is a strong position.`;
      } else {
        headline = `${action}. ${survival18m.toFixed(0)}% survival and ${runwayPhrase(runwayP50)} give you room to execute. The data says go.`;
      }
      if (burnIncreaseWarning > 0) {
        headline += ` Caution: this increases burn by ~${burnIncreaseWarning}%. Consider phased execution to validate growth assumptions before full commitment.`;
      }
    } else if (verdict === 'no-go') {
      if (cm && cm.runwayGain >= 3) {
        headline = `Don't ${action.toLowerCase()} yet. At ${runwayPhrase(runwayP50)} and ${survival18m.toFixed(0)}% survival, you're exposed. ${cm.name} would give you ${cm.gainText} \u2014 do that first.`;
      } else if (monthlyBurn > 0 && endCash > 0 && endCash / monthlyBurn < 6) {
        headline = `Hold off. ${fmtCurrency(endCash)} end cash covers only ${(endCash / monthlyBurn).toFixed(0)} months of burn at ${fmtCurrency(monthlyBurn)}/mo. You need to cut burn or raise capital before this move.`;
      } else {
        headline = `This doesn't work yet. ${runwayPhrase(runwayP50)} and ${survival18m.toFixed(0)}% survival is below the safety threshold. Restructure before committing.`;
      }
    } else {
      if (cm && cm.runwayGain >= 2) {
        headline = `Viable, but protect yourself. ${action} with a hedge \u2014 ${cm.name.toLowerCase()} gives you ${cm.gainText} and moves this from conditional to go.`;
      } else if (bSurvDelta > 5 && bRunwayDelta > 0) {
        headline = `${action} \u2014 cautiously. You gain +${bSurvDelta.toFixed(0)}% survival and ${change?.kind === 'becomes_sustainable' ? 'a sustainable runway' : `+${bRunwayDelta.toFixed(1)} months`} vs baseline, but keep a close eye on ${monthlyBurn > 0 ? `the ${fmtCurrency(monthlyBurn)}/mo burn` : 'your burn rate'}.`;
      } else if (breakeven && breakeven <= 20) {
        headline = `${action}, but watch the timing. Breakeven at month ${breakeven} is achievable, but ${runwayPhrase(runwayP50)} doesn't leave much margin for slippage.`;
      } else {
        headline = `${action} is possible but needs guardrails. ${runwayPhrase(runwayP50)} at ${survival18m.toFixed(0)}% survival \u2014 not enough conviction to go all-in without a backup plan.`;
      }
      if (burnIncreaseWarning > 0) {
        headline += ` Note: burn increases ~${burnIncreaseWarning}% — consider phased hiring (2-3 per quarter) to validate growth before full commitment.`;
      }
    }

    // A sustainable (999) end of the range is not a spread of hundreds of months.
    const spread = Math.min(runwayP90, SIM_HORIZON_MONTHS) - Math.min(runwayP10, SIM_HORIZON_MONTHS);
    const burnCoverage = monthlyBurn > 0 && endCash > 0 ? endCash / monthlyBurn : null;

    let keyRisk = '';
    if (burnIncreaseWarning >= 75) {
      keyRisk = `Burn nearly doubles (+${burnIncreaseWarning}%). If growth assumptions don't materialize within 2-3 months, you'll be in a cash crisis with no room to course-correct.`;
    } else if (burnIncreaseWarning >= 50) {
      keyRisk = `Burn increases ${burnIncreaseWarning}% \u2014 this bets the company on growth materializing fast. Phase the commitment to preserve optionality.`;
    } else if (survival18m < 50) {
      keyRisk = `${survival18m.toFixed(0)}% survival probability at 18 months puts you in the danger zone \u2014 one bad quarter could be fatal.`;
    } else if (runwayP50 < 12) {
      keyRisk = `${runwayP50.toFixed(0)} months of runway is below the 12-month minimum \u2014 you'll be fundraising from a position of weakness.`;
    } else if (spread > 12) {
      keyRisk = `Outcome spread of ${spread.toFixed(0)} months (P10: ${runwayP10.toFixed(0)}mo, P90: ${runwayP90.toFixed(0)}mo) means high variance \u2014 the downside tail is real.`;
    } else if (burnCoverage !== null && burnCoverage < 6) {
      keyRisk = `End cash of ${fmtCurrency(endCash)} only covers ${burnCoverage.toFixed(0)} months at ${fmtCurrency(monthlyBurn)}/mo burn \u2014 you have no margin for error.`;
    } else if (monthlyBurn > 0) {
      keyRisk = `Monthly burn of ${fmtCurrency(monthlyBurn)} compounds quickly \u2014 any revenue miss accelerates your cash-out date.`;
    } else if (isRunwaySustainable(runwayP10)) {
      keyRisk = `Even the pessimistic case (P10) stays cash-positive, so the main risk is the assumptions themselves \u2014 check growth and costs are realistic.`;
    } else {
      keyRisk = `The pessimistic case (P10) leaves only ${runwayP10.toFixed(0)} months \u2014 stress-test your assumptions.`;
    }

    let keyOpportunity = '';
    if (cm) {
      keyOpportunity = `${cm.name} gives you ${cm.gainText} \u2014 combine it with this scenario to move into a stronger position.`;
    } else if (breakeven && breakeven <= 18) {
      keyOpportunity = `Breakeven at month ${breakeven} means you can stop burning cash and grow from revenue \u2014 that's the best position to negotiate from.`;
    } else if (bRunwayDelta > 3) {
      keyOpportunity = change?.kind === 'becomes_sustainable'
        ? `Your runway becomes sustainable versus the baseline, which gives you time to execute and hit milestones.`
        : `+${bRunwayDelta.toFixed(0)} months of runway vs baseline gives you significantly more time to execute and hit milestones.`;
    } else if (runwayP90 >= 24) {
      keyOpportunity = `In the best case (P90), you have ${runwayPhrase(runwayP90)} \u2014 enough to reach key milestones and raise from strength.`;
    } else if (survival18m >= 75) {
      keyOpportunity = `${survival18m.toFixed(0)}% survival gives you strong odds \u2014 use this window to hit growth targets that improve your next raise.`;
    } else {
      keyOpportunity = `Each month of additional runway you unlock through efficiency gains compounds your optionality.`;
    }

    let watchMetric = '';
    if (monthlyBurn > 0 && runwayP50 < 15) {
      watchMetric = `Monthly burn rate (currently ${fmtCurrency(monthlyBurn)}/mo) \u2014 a 10% reduction extends runway by ~${(runwayP50 * 0.11).toFixed(1)} months.`;
    } else if (breakeven && breakeven > 18) {
      watchMetric = `Months to breakeven (currently month ${breakeven}) \u2014 every month earlier is a month less dependency on external capital.`;
    } else if (spread > 10) {
      watchMetric = `Outcome variance (${runwayP10.toFixed(0)}\u2013${runwayP90.toFixed(0)}mo spread) \u2014 track which assumptions drive the widest range and lock them down.`;
    } else if (burnCoverage !== null) {
      watchMetric = `Cash coverage ratio (${burnCoverage.toFixed(1)}x monthly burn) \u2014 keep this above 6x to maintain negotiating leverage.`;
    } else {
      watchMetric = `Survival probability trend \u2014 if ${survival18m.toFixed(0)}% drops below 50% in future sims, reassess immediately.`;
    }

    let score = 0;
    score += Math.min(survival18m / 100, 1) * 3;
    score += (isRunwaySustainable(runwayP50) ? 1 : Math.min(runwayP50 / 24, 1)) * 2.5;
    if (breakeven && breakeven <= 24) score += Math.max(0, (24 - breakeven) / 24) * 1.5;
    if (spread > 0) score += Math.max(0, 1 - spread / 20) * 1;
    if (burnCoverage !== null) score += Math.min(burnCoverage / 12, 1) * 1;
    else score += 0.5;
    if (bRunwayDelta > 0) score += Math.min(bRunwayDelta / 10, 1) * 0.5;
    else if (bRunwayDelta < 0) score += Math.max(-2, bRunwayDelta / 5) * 1.0;
    if (bSurvDelta > 0) score += Math.min(bSurvDelta / 30, 1) * 0.5;
    else if (bSurvDelta < 0) score += Math.max(-2, bSurvDelta / 15) * 1.0;
    if (burnIncreaseWarning >= 75) score -= 3.5;
    else if (burnIncreaseWarning >= 50) score -= 2.5;
    else if (burnIncreaseWarning > 0) score -= 1.0;
    if (survival18m < 50) score = Math.min(score, 4.5);
    else if (survival18m < 70) score = Math.min(score, 6.5);
    if (!consistency.consistent) score = Math.min(score, 4);
    const decisionScore = Math.max(1, Math.min(10, Math.round(score)));

    if (!consistency.consistent) {
      verdict = 'conditional';
      verdictLabel = 'CHECK ASSUMPTIONS';
      verdictColor = 'text-amber-600 dark:text-amber-400';
      verdictBg = 'bg-amber-50/80 dark:bg-amber-950/30 border-amber-200/50 dark:border-amber-800/30';
      verdictIcon = <AlertTriangle className="h-5 w-5 text-amber-500" />;
      headline = consistency.reason || headline;
      keyOpportunity = 'Fix the inputs and re-run before acting on this result.';
    }

    let baselineDelta = '';
    if (baselineSimulation) {
      if (bSurvDelta !== 0 || (change && describeRunwayChange(change))) {
        const parts = [];
        const runwayText = change ? describeRunwayChange(change) : null;
        if (runwayText) parts.push(runwayText);
        if (bSurvDelta !== 0) parts.push(`${bSurvDelta > 0 ? '+' : ''}${bSurvDelta.toFixed(0)}% survival`);
        baselineDelta = `vs Baseline: ${parts.join(', ')}`;
      }
    }

    return { verdict, verdictLabel, verdictColor, verdictBg, verdictIcon, headline, keyRisk, keyOpportunity, watchMetric, baselineDelta, decisionScore };
  }, [simulation, scenarioName, baselineSimulation, counterMoves, scenarioInputs, dashboardRunway]);

  if (!analysis) return null;

  return (
    <div
      className={cn('rounded-md p-[1.5px]', className)}
      style={{ background: 'linear-gradient(135deg, #10b981, #3b82f6)' }}
      data-testid="card-ai-decision-summary"
    >
      <Card className={cn('overflow-visible border-0 rounded-[5px]', analysis.verdictBg)}>
        <CardContent className="pt-5 pb-4 px-5">
          <div className="flex items-center gap-1.5 mb-2">
            <Sparkles className="h-4 w-4 text-primary flex-shrink-0" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground" data-testid="text-ai-summary-title">Your Answer</h3>
          </div>

          <p className="text-base font-semibold leading-snug mb-3" data-testid="text-ai-headline">
            {analysis.headline}
          </p>

          <div className="flex items-center gap-2 mb-4 flex-wrap">
            <div
              className="flex items-center gap-1.5 rounded-md px-2.5 py-1"
              style={{ background: 'linear-gradient(135deg, #10b981, #3b82f6)' }}
              data-testid="decision-score"
            >
              <span className="text-sm font-bold text-white">{analysis.decisionScore}/10</span>
            </div>
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

          <div className="space-y-2">
            <div className="flex items-start gap-2" data-testid="bullet-key-risk">
              <CircleAlert className="h-3.5 w-3.5 text-red-500 flex-shrink-0 mt-0.5" />
              <span className="text-xs text-muted-foreground"><span className="font-semibold text-foreground">Key Risk:</span> {analysis.keyRisk}</span>
            </div>
            <div className="flex items-start gap-2" data-testid="bullet-key-opportunity">
              <Target className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
              <span className="text-xs text-muted-foreground"><span className="font-semibold text-foreground">Key Opportunity:</span> {analysis.keyOpportunity}</span>
            </div>
            <div className="flex items-start gap-2" data-testid="bullet-watch-metric">
              <Activity className="h-3.5 w-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
              <span className="text-xs text-muted-foreground"><span className="font-semibold text-foreground">Watch:</span> {analysis.watchMetric}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
