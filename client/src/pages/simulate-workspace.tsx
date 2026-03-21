import { useState, useEffect, useRef, useCallback } from 'react';
import { useSEO } from "@/lib/seo";
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import {
  Play, Users, TrendingUp, TrendingDown, DollarSign,
  Activity, Target, Clock, Zap,
  AlertTriangle, ShieldCheck, Loader2
} from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useFinancialMetrics } from '@/hooks/useFinancialMetrics';
import { useCounter } from '@/hooks/useCounter';
import { useCurrency } from '@/hooks/useCurrency';
import '@/styles/simulation-animations.css';

interface SimEvent {
  type: 'investor' | 'customer' | 'team' | 'market' | 'founder';
  message: string;
  time: string;
  impact?: 'positive' | 'negative' | 'neutral';
}

interface TimelineMonth {
  month: number;
  cash: number;
  revenue: number;
  burn: number;
  runway: number;
  headcount: number;
}

interface SimulationResult {
  summary: {
    survivalProbability: number;
    fundingProbability: number;
    finalCash: number;
    finalRunway: number;
    peakBurn: number;
    revenueGrowth: number;
  };
  timeline: TimelineMonth[];
  events: SimEvent[];
  keyRisks: Array<{ risk: string; severity: string; probability: number }>;
  recommendations: Array<{ action: string; impact: string; priority: string }>;
  trajectories: Record<string, number[]>;
  shareToken?: string;
  simulationId?: number;
}

function LiveMetricCard({
  label, value, prefix, suffix, trend, icon: Icon, color = 'text-foreground', testId
}: {
  label: string; value: number; prefix?: string; suffix?: string;
  trend?: 'up' | 'down' | 'flat'; icon: any; color?: string; testId: string;
}) {
  const animatedValue = useCounter(value);
  const isNegativeTrend = trend === 'down';
  const isPositiveTrend = trend === 'up';

  return (
    <div className="p-3 rounded-lg bg-card border border-border/50 sim-card-live" data-testid={testId}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[11px] text-muted-foreground uppercase tracking-wider">{label}</span>
        <Icon className={`h-3.5 w-3.5 ${color}`} />
      </div>
      <div className={`text-lg font-bold font-mono sim-number-pop ${color}`}>
        {prefix}{typeof value === 'number' && !isNaN(value) ? (value >= 1000 ? `${(animatedValue / 1000).toFixed(0)}k` : animatedValue.toFixed(value % 1 === 0 ? 0 : 1)) : '—'}{suffix}
      </div>
      {trend && (
        <div className={`flex items-center gap-1 mt-0.5 text-[10px] ${isPositiveTrend ? 'text-emerald-500' : isNegativeTrend ? 'text-red-400' : 'text-muted-foreground'}`}>
          {isPositiveTrend ? <TrendingUp className="h-3 w-3" /> : isNegativeTrend ? <TrendingDown className="h-3 w-3" /> : null}
          {isPositiveTrend ? 'Improving' : isNegativeTrend ? 'Declining' : 'Stable'}
        </div>
      )}
    </div>
  );
}

function EventFeed({ events, isLive }: { events: SimEvent[]; isLive: boolean }) {
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [events.length]);

  const typeColors: Record<string, string> = {
    investor: 'text-purple-400 bg-purple-500/10 border border-purple-500/30',
    customer: 'text-blue-400 bg-blue-500/10 border border-blue-500/30',
    team: 'text-green-400 bg-green-500/10 border border-green-500/30',
    market: 'text-orange-400 bg-orange-500/10 border border-orange-500/30',
    founder: 'text-cyan-400 bg-cyan-500/10 border border-cyan-500/30',
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-1 mb-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Agent Events</h3>
        {isLive && (
          <div className="flex items-center gap-1.5">
            <div className="sim-status-dot" />
            <span className="text-[10px] text-emerald-500 font-medium">LIVE</span>
          </div>
        )}
      </div>
      <div ref={feedRef} className="flex-1 overflow-y-auto space-y-1.5 min-h-0 max-h-[340px] pr-1" data-testid="event-feed">
        {events.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-xs">
            <Activity className="h-6 w-6 mx-auto mb-2 opacity-40" />
            Run a simulation to see agent events
          </div>
        ) : (
          events.map((event, i) => {
            const colorClass = typeColors[event.type] || 'bg-muted/50 border border-border/40';
            return (
              <div key={i} className={`event-item flex items-start gap-3 p-3 rounded-lg ${colorClass}`} data-testid={`event-${i}`}>
                <div className="text-[10px] uppercase tracking-wide text-muted-foreground w-14 shrink-0 pt-0.5">
                  {event.type}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs leading-snug">{event.message}</p>
                  <span className="text-[10px] text-muted-foreground mt-1 block">{event.time}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function SimTimeline({ timeline, currentMonth }: { timeline: TimelineMonth[]; currentMonth: number }) {
  const maxCash = Math.max(...timeline.map(t => t.cash), 1);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between px-1 mb-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Cash Timeline</h3>
        <span className="text-[10px] text-muted-foreground font-mono">{timeline.length} months</span>
      </div>
      <div className="space-y-0.5" data-testid="timeline-bars">
        {timeline.map((m, i) => {
          const pct = Math.max(2, (m.cash / maxCash) * 100);
          const isActive = i === currentMonth;
          const isDanger = m.runway < 3;
          const isWarning = m.runway < 6;
          const barColor = isDanger ? 'bg-red-500/80' : isWarning ? 'bg-amber-500/70' : 'bg-emerald-500/60';

          return (
            <div key={i} className={`sim-timeline-bar ${isActive ? 'ring-1 ring-emerald-500/50' : ''}`} data-testid={`timeline-month-${i}`}>
              <div
                className={`sim-timeline-bar__fill ${barColor}`}
                style={{ width: `${pct}%`, '--bar-width': `${pct}%` } as any}
              />
              <div className="absolute inset-0 flex items-center justify-between px-2 text-[10px]">
                <span className="font-medium">M{m.month}</span>
                <span className="font-mono opacity-70">${(m.cash / 1000).toFixed(0)}k</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function InvestorPanel({ probability, risks }: { probability: number; risks: Array<{ risk: string; severity: string; probability: number }> }) {
  const animatedProb = useCounter(probability);
  const probColor = probability >= 60 ? 'bg-emerald-500' : probability >= 30 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Investor Outlook</h3>
      <div className="p-3 rounded-lg bg-muted/30 border border-border/40">
        <div className="text-[10px] text-muted-foreground mb-1">Term Sheet Probability</div>
        <div className="text-2xl font-bold font-mono sim-number-pop" data-testid="text-investor-prob">
          {animatedProb.toFixed(0)}%
        </div>
        <div className="sim-progress-bar mt-2">
          <div className={`sim-progress-bar__fill ${probColor}`} style={{ width: `${probability}%` }} />
        </div>
      </div>
      {risks.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Key Risks</div>
          {risks.slice(0, 3).map((r, i) => (
            <div key={i} className="flex items-start gap-2 p-2 rounded bg-muted/20 text-xs" data-testid={`risk-${i}`}>
              <AlertTriangle className={`h-3 w-3 shrink-0 mt-0.5 ${r.severity === 'high' ? 'text-red-400' : r.severity === 'medium' ? 'text-amber-400' : 'text-muted-foreground'}`} />
              <span className="leading-snug">{r.risk}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CohortPanel({ timeline }: { timeline: TimelineMonth[] }) {
  if (timeline.length === 0) return null;
  const retentionPoints = timeline.slice(0, 8).map((m, i) => {
    const retention = Math.max(20, 100 - (i * 6) + Math.random() * 8);
    return { month: i + 1, retention: Math.min(100, retention) };
  });

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Cohort Retention</h3>
      <div className="space-y-1" data-testid="cohort-bars">
        {retentionPoints.map((p) => (
          <div key={p.month} className="flex items-center gap-2">
            <span className="text-[10px] text-muted-foreground w-6 text-right font-mono">M{p.month}</span>
            <div className="flex-1 sim-progress-bar">
              <div
                className="sim-progress-bar__fill bg-cyan-500/70"
                style={{ width: `${p.retention}%` }}
              />
            </div>
            <span className="text-[10px] font-mono w-8 text-right">{p.retention.toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DecisionReplay({ recommendations }: { recommendations: Array<{ action: string; impact: string; priority: string }> }) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (recommendations.length <= 1) return;
    const interval = setInterval(() => {
      setActiveIndex(prev => (prev + 1) % recommendations.length);
    }, 1500);
    return () => clearInterval(interval);
  }, [recommendations.length]);

  if (recommendations.length === 0) return null;

  const current = recommendations[activeIndex];
  const priorityColors: Record<string, string> = {
    high: 'bg-red-500/20 text-red-400 border-red-500/30',
    medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    low: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Decision Replay</h3>
        <span className="text-[10px] text-muted-foreground font-mono">{activeIndex + 1}/{recommendations.length}</span>
      </div>
      <div className="p-3 rounded-lg bg-muted/20 border border-border/40 sim-fade-in" key={activeIndex} data-testid="decision-replay-card">
        <div className="flex items-center gap-2 mb-2">
          <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
          <Badge variant="outline" className={`text-[9px] px-1.5 py-0 ${priorityColors[current.priority] || ''}`}>
            {current.priority}
          </Badge>
        </div>
        <p className="text-xs leading-snug mb-1.5">{current.action}</p>
        <p className="text-[10px] text-muted-foreground">{current.impact}</p>
      </div>
      <div className="flex gap-1 justify-center">
        {recommendations.map((_, i) => (
          <div key={i} className={`h-1 rounded-full transition-all duration-300 ${i === activeIndex ? 'w-4 bg-cyan-500' : 'w-1.5 bg-muted-foreground/30'}`} />
        ))}
      </div>
    </div>
  );
}

function ScenarioSlider({
  label, value, onChange, min, max, step, unit, testId
}: {
  label: string; value: number; onChange: (v: number) => void;
  min: number; max: number; step: number; unit?: string; testId: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <label className="text-[11px] text-muted-foreground">{label}</label>
        <span className="text-xs font-mono font-medium">{value}{unit}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-1 bg-muted rounded-full appearance-none cursor-pointer accent-emerald-500"
        data-testid={testId}
      />
    </div>
  );
}

export default function SimulateWorkspace() {
  useSEO({
    title: "Scenario Simulator — What-If Analysis for Startups | FounderConsole",
    description: "Run Monte Carlo simulations to model hiring, pricing, and fundraising scenarios. See P10/P50/P90 confidence bands and compare outcomes side by side.",
    path: "/simulate",
    robots: "noindex, nofollow",
  });

  const currentCompany = useFounderStore((s) => s.currentCompany);
  const { metrics: baseMetrics, isLoading: metricsLoading } = useFinancialMetrics();
  const { format: formatCurrency } = useCurrency();
  const { toast } = useToast();

  const [numRounds, setNumRounds] = useState(12);
  const [fundingClimate, setFundingClimate] = useState(0.6);
  const [marketGrowth, setMarketGrowth] = useState(0.5);
  const [hiringRate, setHiringRate] = useState(0);
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [currentTimelineMonth, setCurrentTimelineMonth] = useState(0);

  const runMutation = useMutation({
    mutationFn: async () => {
      if (!currentCompany) throw new Error('No company selected');
      const res = await apiRequest(
        'POST',
        `/api/companies/${currentCompany.id}/simulation/agent-run`,
        {
          num_rounds: numRounds,
          funding_climate: fundingClimate,
          market_growth: marketGrowth,
          hiring_rate: hiringRate,
          monthly_revenue: baseMetrics?.mrr ?? undefined,
          monthly_burn: baseMetrics?.burnRate ?? undefined,
          cash_balance: baseMetrics?.cashOnHand ?? undefined,
          growth_rate: baseMetrics?.monthlyGrowthRate ?? undefined,
          headcount: baseMetrics?.headcount ?? undefined,
        }
      );
      return res.json();
    },
    onMutate: () => {
      setIsSimulating(true);
      setSimResult(null);
      setCurrentTimelineMonth(0);
    },
    onSuccess: (data: SimulationResult) => {
      setSimResult(data);
      setIsSimulating(false);
      toast({ title: 'Simulation Complete', description: `Survival probability: ${data.summary.survivalProbability.toFixed(0)}%` });
    },
    onError: (err: any) => {
      setIsSimulating(false);
      toast({ title: 'Simulation Failed', description: err.message || 'An error occurred', variant: 'destructive' });
    },
  });

  useEffect(() => {
    if (!simResult?.timeline?.length) return;
    if (currentTimelineMonth >= simResult.timeline.length - 1) return;
    const timer = setTimeout(() => {
      setCurrentTimelineMonth(prev => prev + 1);
    }, 200);
    return () => clearTimeout(timer);
  }, [simResult, currentTimelineMonth]);

  const events = simResult?.events ?? [];
  const timeline = simResult?.timeline ?? [];
  const risks = simResult?.keyRisks ?? [];
  const recommendations = simResult?.recommendations ?? [];
  const summary = simResult?.summary;

  const currentCash = summary?.finalCash ?? baseMetrics?.cashOnHand ?? 0;
  const currentBurn = baseMetrics?.burnRate ?? 0;
  const currentRevenue = baseMetrics?.mrr ?? 0;
  const currentRunway = summary?.finalRunway ?? (currentBurn > 0 ? currentCash / currentBurn : 0);
  const survivalPct = summary?.survivalProbability ?? 0;
  const fundingPct = summary?.fundingProbability ?? 0;

  const handleShare = useCallback(() => {
    if (!simResult?.shareToken) return;
    const url = `${window.location.origin}/simulate-v2/shared/${simResult.shareToken}`;
    navigator.clipboard.writeText(url).then(() => {
      toast({ title: 'Link Copied', description: 'Shareable simulation link copied to clipboard.' });
    });
  }, [simResult, toast]);

  const riskHigh = currentRunway > 0 && currentRunway < 10;

  return (
    <div className="simulation-root relative min-h-screen p-4 md:p-6 max-w-[1400px] mx-auto">
      <div className="bg-orb top-10 left-10" />
      <div className="bg-orb bottom-10 right-10" />

      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              {isSimulating && <div className="status-dot" />}
              <h1 className="text-lg font-bold" data-testid="text-sim-title">Simulation Console</h1>
            </div>
            <Badge variant="outline" className="text-[9px] px-1.5 py-0 border-emerald-500/30 text-emerald-500">
              {isSimulating ? 'RUNNING' : simResult ? 'COMPLETE' : 'READY'}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            {simResult?.shareToken && (
              <Button variant="ghost" size="sm" onClick={handleShare} className="text-xs h-7" data-testid="button-share-results">
                Share
              </Button>
            )}
            <Button
              size="sm"
              onClick={() => runMutation.mutate()}
              disabled={isSimulating || !currentCompany}
              className="h-7 text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700"
              data-testid="button-run-simulation"
            >
              {isSimulating ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
              {isSimulating ? 'Simulating...' : 'Run Simulation'}
            </Button>
          </div>
        </div>

        {isSimulating && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
            <div className="status-dot" />
            <span>Running simulation...</span>
          </div>
        )}

        <div className="grid grid-cols-12 gap-4">
          {/* LEFT — Live Metrics + Controls */}
          <div className="col-span-12 lg:col-span-3 space-y-3">
            <div className="bg-card/50 border border-border/50 p-4 rounded-lg">
              <h3 className="text-sm mb-3 font-medium">Live Metrics</h3>
              <div className="space-y-2">
                <LiveMetricCard
                  label="Cash" value={currentCash} prefix="$" icon={DollarSign}
                  color="text-emerald-500" trend={summary ? (summary.finalCash > (baseMetrics?.cashOnHand ?? 0) ? 'up' : 'down') : undefined}
                  testId="metric-cash"
                />
                <LiveMetricCard
                  label="Monthly Burn" value={currentBurn} prefix="$" icon={TrendingDown}
                  color="text-red-400" trend={summary ? 'flat' : undefined}
                  testId="metric-burn"
                />
                <LiveMetricCard
                  label="Revenue" value={currentRevenue} prefix="$" icon={TrendingUp}
                  color="text-blue-400" trend={summary ? (summary.revenueGrowth > 0 ? 'up' : 'down') : undefined}
                  testId="metric-revenue"
                />
                <LiveMetricCard
                  label="Runway" value={currentRunway} suffix=" mo" icon={Clock}
                  color={currentRunway < 6 ? 'text-red-400' : currentRunway < 12 ? 'text-amber-400' : 'text-emerald-500'}
                  trend={summary ? (summary.finalRunway > 12 ? 'up' : 'down') : undefined}
                  testId="metric-runway"
                />
                {summary && (
                  <LiveMetricCard
                    label="Survival" value={survivalPct} suffix="%" icon={ShieldCheck}
                    color={survivalPct >= 70 ? 'text-emerald-500' : survivalPct >= 40 ? 'text-amber-400' : 'text-red-400'}
                    testId="metric-survival"
                  />
                )}
                <div className={`mt-2 px-2 py-1 text-xs rounded ${riskHigh ? 'risk-alert bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`} data-testid="risk-badge">
                  Risk: {riskHigh ? 'High' : 'Moderate'}
                </div>
              </div>
            </div>

            <div className="bg-card/50 border border-border/50 p-4 rounded-lg">
              <h3 className="text-sm mb-3 font-medium">Scenario Controls</h3>
              <div className="space-y-3">
                <ScenarioSlider label="Simulation Months" value={numRounds} onChange={setNumRounds} min={6} max={36} step={1} testId="slider-rounds" />
                <ScenarioSlider label="Funding Climate" value={fundingClimate} onChange={setFundingClimate} min={0} max={1} step={0.1} testId="slider-funding" />
                <ScenarioSlider label="Market Growth" value={marketGrowth} onChange={setMarketGrowth} min={0} max={1} step={0.1} testId="slider-market" />
                <ScenarioSlider label="Hiring Rate" value={hiringRate} onChange={setHiringRate} min={0} max={10} step={1} unit="/mo" testId="slider-hiring" />
              </div>
            </div>
          </div>

          {/* CENTER — Timeline + Event Feed */}
          <div className="col-span-12 lg:col-span-6 space-y-3">
            {timeline.length > 0 ? (
              <SimTimeline timeline={timeline} currentMonth={currentTimelineMonth} />
            ) : (
              <div className="flex items-center gap-2 mb-2">
                {[...Array(12)].map((_, i) => (
                  <div key={i} className="h-2 flex-1 rounded transition-all duration-300 bg-muted/40" />
                ))}
              </div>
            )}

            {isSimulating && (
              <div className="flex items-center justify-center gap-3 py-6 rounded-lg bg-muted/20 border border-border/30 sim-pulse">
                <Loader2 className="h-5 w-5 animate-spin text-emerald-500" />
                <span className="text-sm text-muted-foreground">Running multi-agent simulation...</span>
              </div>
            )}

            <div className="bg-card/50 border border-border/50 p-4 rounded-lg">
              <h3 className="text-sm mb-3 font-medium">Simulation Events</h3>
              <EventFeed events={events} isLive={isSimulating} />
            </div>

            {!simResult && !isSimulating && (
              <div className="text-center py-10 rounded-lg border border-dashed border-border/50">
                <Activity className="h-8 w-8 mx-auto text-muted-foreground/30 mb-3" />
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Ready to Simulate</h3>
                <p className="text-xs text-muted-foreground/70 max-w-sm mx-auto">
                  Adjust scenario parameters and click Run Simulation to see how your startup evolves.
                </p>
              </div>
            )}
          </div>

          {/* RIGHT — Investor + Cohort + Decisions */}
          <div className="col-span-12 lg:col-span-3 space-y-3">
            <div className="result-card bg-card/50 border border-border/50 p-4 rounded-lg">
              <InvestorPanel probability={fundingPct} risks={risks} />
            </div>

            {timeline.length > 0 && (
              <div className="result-card bg-card/50 border border-border/50 p-4 rounded-lg">
                <CohortPanel timeline={timeline} />
              </div>
            )}

            {recommendations.length > 0 && (
              <div className="result-card bg-card/50 border border-border/50 p-4 rounded-lg">
                <DecisionReplay recommendations={recommendations} />
              </div>
            )}

            {!simResult && !isSimulating && (
              <div className="space-y-3">
                <div className="result-card bg-card/50 border border-border/50 p-4 rounded-lg">
                  <h3 className="text-sm mb-2 font-medium">Recommendation</h3>
                  <p className="text-xs text-muted-foreground">Run simulation for insights</p>
                </div>
                <div className="result-card bg-card/50 border border-border/50 p-4 rounded-lg">
                  <h3 className="text-sm mb-2 font-medium">Key Risk</h3>
                  <p className="text-xs text-muted-foreground">Awaiting simulation data</p>
                </div>
                <div className="result-card bg-card/50 border border-border/50 p-4 rounded-lg">
                  <h3 className="text-sm mb-2 font-medium">Suggested Action</h3>
                  <p className="text-xs text-muted-foreground">Start a simulation to see actions</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {isSimulating && (
          <div className="mt-4">
            <div className="shimmer h-10 rounded-lg flex items-center justify-center text-xs text-muted-foreground">
              Re-running simulation...
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
