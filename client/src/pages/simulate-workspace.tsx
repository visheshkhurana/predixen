import { useState, useEffect, useRef, useCallback } from 'react';
import { useSEO } from "@/lib/seo";
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
  reason: string;
  impact: string;
  time: string;
  severity?: string;
  chainedFrom?: string;
}

interface TimelineMonth {
  month: number;
  cash: number;
  revenue: number;
  burn: number;
  runway: number;
  headcount: number;
}

interface SimRecommendation {
  action: string;
  impact: string;
  priority: string;
  why: string;
  affects: string;
  confidence: number;
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
  keyRisks: Array<{ risk: string; severity: string; probability: number; driver?: string }>;
  recommendations: SimRecommendation[];
  trajectories: Record<string, number[]>;
  shareToken?: string;
  simulationId?: number;
}

const THINKING_MESSAGES = [
  "Analyzing investor sentiment...",
  "Evaluating survival probability...",
  "Recalculating runway projections...",
  "Modeling customer acquisition patterns...",
  "Assessing team capacity and morale...",
  "Simulating market conditions...",
  "Computing burn rate trajectories...",
  "Running counter-move analysis...",
  "Evaluating fundraising readiness...",
  "Scoring decision confidence levels...",
];

const AGENT_CHAIN_ORDER = ['team', 'customer', 'market', 'investor', 'founder'];

function mapBackendEvent(e: any): SimEvent {
  const agentType = e.agentType || e.type || 'market';
  const impactObj = e.impact || {};
  const impactParts: string[] = [];
  if (impactObj.burn_increase) impactParts.push(`+$${Math.round(impactObj.burn_increase).toLocaleString()} burn`);
  if (impactObj.burn_reduction_pct) impactParts.push(`${Math.round(impactObj.burn_reduction_pct * 100)}% burn cut`);
  if (impactObj.headcount_change) impactParts.push(`+${impactObj.headcount_change} headcount`);
  if (impactObj.funding_climate_change) impactParts.push(`${(impactObj.funding_climate_change * 100).toFixed(0)}% funding shift`);
  if (impactObj.market_growth_change) impactParts.push(`${(impactObj.market_growth_change * 100).toFixed(0)}% growth shift`);
  if (impactObj.revenue_change) impactParts.push(`$${Math.round(impactObj.revenue_change).toLocaleString()} revenue`);
  if (impactObj.team_morale) impactParts.push(`${(impactObj.team_morale * 100).toFixed(0)}% morale`);
  if (impactObj.productivity_multiplier) impactParts.push(`${Math.round(impactObj.productivity_multiplier * 100)}% productivity`);

  const eventType = e.eventType || '';
  const reasonMap: Record<string, string> = {
    hiring_decision: 'Founder confidence high, runway sufficient',
    fundraising_initiated: 'Low runway triggered fundraising urgency',
    cost_cutting: 'Low confidence with declining runway',
    investment_interest: 'Metrics attracted investor attention',
    investment_pass: 'Metrics below investor threshold',
    churn_spike: 'Product quality or pricing pressure',
    growth_surge: 'Strong product-market fit signal',
    morale_crisis: 'Overwork or uncertainty in team',
    market_downturn: 'Macroeconomic cycle shift',
    market_opportunity: 'Expanding market conditions',
    competitor_move: 'Competitive landscape change',
    key_hire: 'Strategic talent acquisition',
    attrition: 'Team retention issues',
  };

  return {
    type: agentType as SimEvent['type'],
    message: e.description || e.message || '',
    reason: reasonMap[eventType] || `Triggered by ${eventType.replace(/_/g, ' ')}`,
    impact: impactParts.length > 0 ? impactParts.join(', ') : 'Indirect system effect',
    time: e.time || `Month ${e.month || '?'}`,
    severity: e.severity || 'info',
  };
}

function mapBackendRecommendation(r: any): SimRecommendation {
  const categoryWhyMap: Record<string, string> = {
    survival: 'Critical runway risk detected by simulation',
    efficiency: 'Burn efficiency below optimal threshold',
    growth: 'Growth metrics triggered optimization',
    team: 'Team dynamics impacting performance',
    fundraising: 'Funding readiness score below threshold',
    general: 'Overall trajectory analysis',
  };

  const categoryAffectsMap: Record<string, string> = {
    survival: 'Cash runway, survival probability',
    efficiency: 'Burn rate, investor attractiveness',
    growth: 'Revenue trajectory, market position',
    team: 'Productivity, retention, morale',
    fundraising: 'Funding probability, investor confidence',
    general: 'Overall company health',
  };

  const priorityConfidenceMap: Record<string, number> = {
    critical: 92,
    high: 78,
    medium: 65,
    low: 50,
    info: 40,
  };

  return {
    action: r.title || r.action || '',
    impact: r.impact || r.description || '',
    priority: r.priority || 'medium',
    why: categoryWhyMap[r.category] || r.description || 'Simulation analysis',
    affects: categoryAffectsMap[r.category] || 'Multiple metrics',
    confidence: priorityConfidenceMap[r.priority] || 60,
  };
}

function chainEvents(events: SimEvent[]): SimEvent[] {
  if (events.length < 2) return events;
  const chained = [...events];
  for (let i = 1; i < chained.length; i++) {
    const prev = chained[i - 1];
    const curr = chained[i];
    if (prev.time === curr.time) {
      const prevIdx = AGENT_CHAIN_ORDER.indexOf(prev.type);
      const currIdx = AGENT_CHAIN_ORDER.indexOf(curr.type);
      if (currIdx > prevIdx && prevIdx >= 0) {
        curr.chainedFrom = prev.type;
      }
    }
  }
  return chained;
}

function ThinkingState({ isActive }: { isActive: boolean }) {
  const [msgIndex, setMsgIndex] = useState(0);

  useEffect(() => {
    if (!isActive) return;
    const interval = setInterval(() => {
      setMsgIndex(prev => (prev + 1) % THINKING_MESSAGES.length);
    }, 2500);
    return () => clearInterval(interval);
  }, [isActive]);

  if (!isActive) return null;

  return (
    <div className="thinking-text flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/20 border border-border/30 mb-2" data-testid="thinking-state" key={msgIndex}>
      <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-400 shrink-0" />
      <span className="text-xs text-cyan-400/90">{THINKING_MESSAGES[msgIndex]}</span>
      <span className="text-xs">
        <span className="dot-1">.</span>
        <span className="dot-2">.</span>
        <span className="dot-3">.</span>
      </span>
    </div>
  );
}

function DataFreshness({ lastUpdated }: { lastUpdated: number | null }) {
  const [ago, setAgo] = useState('');

  useEffect(() => {
    if (!lastUpdated) return;
    const tick = () => {
      const diff = Math.floor((Date.now() - lastUpdated) / 1000);
      if (diff < 5) setAgo('just now');
      else if (diff < 60) setAgo(`${diff}s ago`);
      else setAgo(`${Math.floor(diff / 60)}m ago`);
    };
    tick();
    const interval = setInterval(tick, 2000);
    return () => clearInterval(interval);
  }, [lastUpdated]);

  if (!lastUpdated) return null;

  const isStale = Date.now() - lastUpdated > 120000;

  return (
    <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground" data-testid="data-freshness">
      <div className={`freshness-dot ${isStale ? 'freshness-dot--stale' : ''}`} />
      <span>Live</span>
      <span className="opacity-60">(updated {ago})</span>
    </div>
  );
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
    investor: 'bg-purple-500/10 border-purple-500/30',
    customer: 'bg-blue-500/10 border-blue-500/30',
    team: 'bg-green-500/10 border-green-500/30',
    market: 'bg-orange-500/10 border-orange-500/30',
    founder: 'bg-cyan-500/10 border-cyan-500/30',
  };

  const typeLabelColors: Record<string, string> = {
    investor: 'text-purple-400',
    customer: 'text-blue-400',
    team: 'text-green-400',
    market: 'text-orange-400',
    founder: 'text-cyan-400',
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
      <div ref={feedRef} className="flex-1 overflow-y-auto space-y-1.5 min-h-0 max-h-[420px] pr-1" data-testid="event-feed">
        {events.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-xs">
            <Activity className="h-6 w-6 mx-auto mb-2 opacity-40" />
            Run a simulation to see agent events
          </div>
        ) : (
          events.map((event, i) => {
            const colorClass = typeColors[event.type] || 'bg-muted/50 border-border/40';
            const labelColor = typeLabelColors[event.type] || 'text-muted-foreground';
            const isChained = !!event.chainedFrom;
            return (
              <div
                key={i}
                className={`event-item flex items-start gap-3 p-3 rounded-lg border ${colorClass} ${isChained ? 'chain-connector' : ''}`}
                data-testid={`event-${i}`}
              >
                <div className={`text-[10px] uppercase tracking-wide font-medium w-16 shrink-0 pt-0.5 ${labelColor}`}>
                  {event.type}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs leading-snug">{event.message}</p>
                  {event.reason && (
                    <p className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
                      <span className="opacity-50">→</span> {event.reason}
                    </p>
                  )}
                  {event.impact && event.impact !== 'Indirect system effect' && (
                    <p className="text-[10px] text-muted-foreground/70 mt-0.5 flex items-center gap-1">
                      <span className="opacity-50">→</span> {event.impact}
                    </p>
                  )}
                  <span className="text-[10px] text-muted-foreground/50 mt-1 block">{event.time}</span>
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

function InvestorPanel({ probability, risks, previousProb }: {
  probability: number;
  risks: Array<{ risk: string; severity: string; probability: number; driver?: string }>;
  previousProb: number | null;
}) {
  const animatedProb = useCounter(probability);
  const probColor = probability >= 60 ? 'bg-emerald-500' : probability >= 30 ? 'bg-amber-500' : 'bg-red-500';
  const delta = previousProb !== null ? probability - previousProb : null;
  const topDriver = risks.length > 0 ? (risks[0].driver || risks[0].risk.split(' ')[0].toLowerCase()) : null;

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Investor Outlook</h3>
      <div className="p-3 rounded-lg bg-muted/30 border border-border/40">
        <div className="text-[10px] text-muted-foreground mb-1">Term Sheet Probability</div>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-bold font-mono sim-number-pop" data-testid="text-investor-prob">
            {animatedProb.toFixed(0)}%
          </div>
          {delta !== null && delta !== 0 && (
            <span className={`text-xs font-mono sim-fade-in ${delta > 0 ? 'text-emerald-400' : 'text-red-400'}`} data-testid="investor-delta">
              {delta > 0 ? '+' : ''}{delta.toFixed(0)}%
            </span>
          )}
        </div>
        <div className="sim-progress-bar mt-2">
          <div className={`sim-progress-bar__fill ${probColor}`} style={{ width: `${probability}%` }} />
        </div>
        {topDriver && (
          <div className="mt-2 text-[10px] text-muted-foreground flex items-center gap-1" data-testid="investor-driver">
            <span className="opacity-50">Key driver:</span>
            <span className="text-foreground/80">{topDriver}</span>
          </div>
        )}
      </div>
      {risks.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Key Risks</div>
          {risks.slice(0, 3).map((r, i) => (
            <div key={i} className="flex items-start gap-2 p-2 rounded bg-muted/20 text-xs" data-testid={`risk-${i}`}>
              <AlertTriangle className={`h-3 w-3 shrink-0 mt-0.5 ${r.severity === 'high' ? 'text-red-400' : r.severity === 'medium' ? 'text-amber-400' : 'text-muted-foreground'}`} />
              <div className="flex-1">
                <span className="leading-snug">{r.risk}</span>
                {r.driver && (
                  <span className="text-[10px] text-muted-foreground/60 ml-1">({r.driver})</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CohortPanel({ timeline }: { timeline: TimelineMonth[] }) {
  if (timeline.length === 0) return null;

  const firstRevenue = timeline[0]?.revenue || 1;
  const retentionPoints = timeline.slice(0, 8).map((m, i) => {
    const revenueRetention = firstRevenue > 0 ? Math.min(100, (m.revenue / firstRevenue) * 100) : 100 - (i * 5);
    const burnPressure = m.burn > 0 ? Math.min(20, (m.burn / Math.max(m.revenue, 1)) * 3) : 0;
    const retention = Math.max(10, revenueRetention - burnPressure);
    return { month: m.month, retention: Math.min(100, retention) };
  });

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Cohort Retention</h3>
      <div className="space-y-1" data-testid="cohort-bars">
        {retentionPoints.map((p, i) => {
          const prev = i > 0 ? retentionPoints[i - 1].retention : 100;
          const delta = p.retention - prev;
          const trend = delta > 2 ? '↑' : delta < -3 ? '↓' : '';
          const trendColor = delta > 2 ? 'text-emerald-400' : delta < -3 ? 'text-red-400' : '';
          const churnReason = delta < -8 ? 'high burn' : delta < -5 ? 'revenue drop' : '';

          return (
            <div key={p.month} className="flex items-center gap-2">
              <span className="text-[10px] text-muted-foreground w-6 text-right font-mono">M{p.month}</span>
              <div className="flex-1 sim-progress-bar">
                <div
                  className="sim-progress-bar__fill bg-cyan-500/70"
                  style={{ width: `${p.retention}%` }}
                />
              </div>
              <span className="text-[10px] font-mono w-8 text-right">{p.retention.toFixed(0)}%</span>
              {trend && (
                <span className={`text-[10px] w-3 ${trendColor}`} data-testid={`cohort-trend-${p.month}`}>{trend}</span>
              )}
              {churnReason && (
                <span className="text-[9px] text-muted-foreground/50 w-16 truncate" data-testid={`cohort-reason-${p.month}`}>{churnReason}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DecisionReplay({ recommendations }: { recommendations: SimRecommendation[] }) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (recommendations.length <= 1) return;
    const interval = setInterval(() => {
      setActiveIndex(prev => (prev + 1) % recommendations.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [recommendations.length]);

  if (recommendations.length === 0) return null;

  const current = recommendations[activeIndex];
  const priorityColors: Record<string, string> = {
    critical: 'bg-red-500/20 text-red-400 border-red-500/30',
    high: 'bg-red-500/20 text-red-400 border-red-500/30',
    medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    low: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
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
          <span className="text-[9px] font-mono text-muted-foreground ml-auto" data-testid="decision-confidence">
            {current.confidence}% confidence
          </span>
        </div>
        <p className="text-xs leading-snug mb-1.5 font-medium">{current.action}</p>
        <p className="text-[10px] text-muted-foreground mb-2">{current.impact}</p>
        <div className="space-y-1 pt-2 border-t border-border/30">
          <p className="text-[10px] text-muted-foreground/70 flex gap-1">
            <span className="opacity-50 shrink-0">Why:</span>
            <span>{current.why}</span>
          </p>
          <p className="text-[10px] text-muted-foreground/70 flex gap-1">
            <span className="opacity-50 shrink-0">Affects:</span>
            <span>{current.affects}</span>
          </p>
        </div>
      </div>
      <div className="flex gap-1 justify-center">
        {recommendations.map((_, i) => (
          <button
            key={i}
            onClick={() => setActiveIndex(i)}
            className={`h-1 rounded-full transition-all duration-300 ${i === activeIndex ? 'w-4 bg-cyan-500' : 'w-1.5 bg-muted-foreground/30 hover:bg-muted-foreground/50'}`}
            data-testid={`decision-dot-${i}`}
          />
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
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const [previousFundingProb, setPreviousFundingProb] = useState<number | null>(null);

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
      if (simResult) {
        setPreviousFundingProb(simResult.summary.fundingProbability);
      }
      setIsSimulating(true);
      setSimResult(null);
      setCurrentTimelineMonth(0);
    },
    onSuccess: (data: any) => {
      const mappedEvents = chainEvents((data.events || []).map(mapBackendEvent));
      const mappedRecs = (data.recommendations || []).map(mapBackendRecommendation);
      const mappedRisks = (data.keyRisks || []).map((r: any) => ({
        risk: r.description || r.risk || r.type || '',
        severity: r.severity || 'medium',
        probability: r.probability || r.occurrences || 0,
        driver: r.type ? r.type.replace(/_/g, ' ') : undefined,
      }));
      const mappedTimeline = (data.timeline || []).map((t: any) => ({
        month: t.month,
        cash: t.cash_balance ?? t.cash ?? 0,
        revenue: t.monthly_revenue ?? t.revenue ?? 0,
        burn: t.monthly_burn ?? t.burn ?? 0,
        runway: t.runway_months ?? t.runway ?? 0,
        headcount: t.headcount ?? 0,
      }));
      const result: SimulationResult = {
        ...data,
        timeline: mappedTimeline,
        events: mappedEvents,
        recommendations: mappedRecs,
        keyRisks: mappedRisks,
      };
      setSimResult(result);
      setIsSimulating(false);
      setLastUpdated(Date.now());
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
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              {isSimulating && <div className="status-dot" />}
              <h1 className="text-lg font-bold" data-testid="text-sim-title">Simulation Console</h1>
            </div>
            <Badge variant="outline" className="text-[9px] px-1.5 py-0 border-emerald-500/30 text-emerald-500">
              {isSimulating ? 'THINKING' : simResult ? 'COMPLETE' : 'READY'}
            </Badge>
          </div>
          <div className="flex items-center gap-3">
            <DataFreshness lastUpdated={lastUpdated} />
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
                {isSimulating ? 'Thinking...' : 'Run Simulation'}
              </Button>
            </div>
          </div>
        </div>

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

          {/* CENTER — Thinking + Timeline + Events */}
          <div className="col-span-12 lg:col-span-6 space-y-3">
            <ThinkingState isActive={isSimulating} />

            {timeline.length > 0 && (
              <SimTimeline timeline={timeline} currentMonth={currentTimelineMonth} />
            )}

            <div className="bg-card/50 border border-border/50 p-4 rounded-lg">
              <EventFeed events={events} isLive={isSimulating} />
            </div>

            {!simResult && !isSimulating && (
              <div className="text-center py-10 rounded-lg border border-dashed border-border/50">
                <Activity className="h-8 w-8 mx-auto text-muted-foreground/30 mb-3" />
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Ready to Simulate</h3>
                <p className="text-xs text-muted-foreground/70 max-w-sm mx-auto">
                  Adjust scenario parameters and click Run Simulation to watch the system think.
                </p>
              </div>
            )}
          </div>

          {/* RIGHT — Investor + Cohort + Decisions */}
          <div className="col-span-12 lg:col-span-3 space-y-3">
            <div className="result-card bg-card/50 border border-border/50 p-4 rounded-lg">
              <InvestorPanel probability={fundingPct} risks={risks} previousProb={previousFundingProb} />
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
