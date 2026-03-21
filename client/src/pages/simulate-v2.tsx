import { useState, useCallback, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useRoute } from 'wouter';
import { useSEO } from '@/lib/seo';
import { useFounderStore } from '@/store/founderStore';
import { apiRequest } from '@/lib/queryClient';
import { cn } from '@/lib/utils';
import { formatCurrencyAbbrev } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Play, RotateCcw, Share2, Download, ChevronRight,
  TrendingUp, TrendingDown, AlertTriangle, Users, DollarSign,
  Target, Zap, Shield, Brain, Activity, Clock, Loader2,
  Copy, CheckCircle, XCircle, Info
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip as RechartsTooltip,
  CartesianGrid, LineChart, Line, Legend
} from 'recharts';

interface SimulationResult {
  simulationId: number;
  companyName: string;
  shareToken: string;
  summary: {
    survivalProbability: number;
    fundingProbability: number;
    finalCash: number;
    finalRunway: number;
    finalRevenue: number;
    finalHeadcount: number;
    finalCustomers: number;
    totalEvents: number;
    riskEvents: number;
  };
  timeline: Array<{
    month: number;
    cash_balance: number;
    monthly_revenue: number;
    monthly_burn: number;
    runway_months: number;
    headcount: number;
    customers: number;
    growth_rate: number;
    survival: boolean;
  }>;
  events: Array<{
    month: number;
    agentType: string;
    eventType: string;
    description: string;
    severity: string;
    impact: Record<string, number>;
  }>;
  agentStates: Array<{
    month: number;
    agents: Record<string, { sentiment: string; confidence: number; trend?: string }>;
  }>;
  keyRisks: Array<{
    type: string;
    occurrences: number;
    description: string;
    severity: string;
  }>;
  recommendations: Array<{
    priority: string;
    title: string;
    description: string;
    impact: string;
    category: string;
  }>;
  trajectories: {
    cash: number[];
    revenue: number[];
    runway: number[];
  };
  report: {
    overallRating: string;
    ratingLabel: string;
    ratingColor: string;
    headline: string;
    survivalProbability: number;
    fundingProbability: number;
    turningPoints: Array<{ month: number; type: string; description: string; severity: string }>;
    agentSummary: Record<string, { finalSentiment: string; averageConfidence: number; trend: string }>;
    topRecommendations: Array<{ priority: string; title: string; description: string; impact: string }>;
  };
}

const AGENT_CONFIG = {
  founder: { label: 'Founder', icon: Brain, color: 'text-purple-500', bg: 'bg-purple-500/10' },
  investor: { label: 'Investor', icon: DollarSign, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  customer: { label: 'Customer', icon: Users, color: 'text-blue-500', bg: 'bg-blue-500/10' },
  team: { label: 'Team', icon: Users, color: 'text-orange-500', bg: 'bg-orange-500/10' },
  market: { label: 'Market', icon: Activity, color: 'text-cyan-500', bg: 'bg-cyan-500/10' },
};

const SEVERITY_CONFIG = {
  info: { color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20', icon: Info },
  warning: { color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', icon: AlertTriangle },
  danger: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', icon: XCircle },
  positive: { color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20', icon: CheckCircle },
};

const PRIORITY_CONFIG: Record<string, { color: string; bg: string }> = {
  critical: { color: 'text-red-400', bg: 'bg-red-500/10' },
  high: { color: 'text-orange-400', bg: 'bg-orange-500/10' },
  medium: { color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  info: { color: 'text-blue-400', bg: 'bg-blue-500/10' },
};

export default function SimulateV2Page() {
  useSEO({ title: 'Flight Simulator — FounderConsole', description: 'Agent-based simulation engine' });
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();

  const [scenarioInputs, setScenarioInputs] = useState({
    num_rounds: 24,
    hiring_rate: 0,
    pricing_change: 0,
    marketing_spend_multiplier: 1.0,
    funding_climate: 0.6,
    market_trend: 'neutral',
    market_volatility: 0.1,
    founder_risk_tolerance: 0.6,
    hiring_aggressiveness: 0.5,
  });

  const [result, setResult] = useState<SimulationResult | null>(null);
  const [activeTab, setActiveTab] = useState('timeline');
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  const runMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest(
        'POST',
        `/api/companies/${currentCompany!.id}/simulation/agent-run`,
        scenarioInputs
      );
      return res.json();
    },
    onSuccess: (data: SimulationResult) => {
      setResult(data);
      setSelectedMonth(null);
      toast({ title: 'Simulation complete', description: `Survival probability: ${data.summary.survivalProbability}%` });
    },
    onError: (err: Error) => {
      toast({ title: 'Simulation failed', description: err.message, variant: 'destructive' });
    },
  });

  const handleSliderChange = (key: string, value: number[]) => {
    setScenarioInputs(prev => ({ ...prev, [key]: value[0] }));
  };

  const handleReset = () => {
    setScenarioInputs({
      num_rounds: 24,
      hiring_rate: 0,
      pricing_change: 0,
      marketing_spend_multiplier: 1.0,
      funding_climate: 0.6,
      market_trend: 'neutral',
      market_volatility: 0.1,
      founder_risk_tolerance: 0.6,
      hiring_aggressiveness: 0.5,
    });
    setResult(null);
  };

  const handleShare = () => {
    if (!result?.shareToken) return;
    const url = `${window.location.origin}/simulate-v2/shared/${result.shareToken}`;
    navigator.clipboard.writeText(url);
    toast({ title: 'Link copied', description: 'Share this link with your team or investors' });
  };

  const filteredEvents = selectedMonth
    ? result?.events.filter(e => e.month === selectedMonth)
    : result?.events;

  if (!currentCompany) {
    return (
      <div className="flex items-center justify-center h-full" data-testid="simulate-v2-no-company">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <Brain className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h2 className="text-xl font-semibold mb-2">Select a company</h2>
            <p className="text-muted-foreground">Choose a company from the sidebar to run agent simulations.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col" data-testid="simulate-v2-page">
      <div className="border-b bg-card/50 backdrop-blur-sm px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            Flight Simulator
          </h1>
          <p className="text-sm text-muted-foreground">Multi-agent simulation engine — watch your startup's future unfold</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            data-testid="button-reset"
          >
            <RotateCcw className="h-4 w-4 mr-1" /> Reset
          </Button>
          {result && (
            <Button variant="outline" size="sm" onClick={handleShare} data-testid="button-share">
              <Share2 className="h-4 w-4 mr-1" /> Share
            </Button>
          )}
          <Button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            size="sm"
            data-testid="button-run-simulation"
          >
            {runMutation.isPending ? (
              <><Loader2 className="h-4 w-4 mr-1 animate-spin" /> Simulating...</>
            ) : (
              <><Play className="h-4 w-4 mr-1" /> Run Simulation</>
            )}
          </Button>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-[280px_1fr_320px] gap-0 overflow-hidden">
        {/* LEFT PANEL — Scenario Controls */}
        <div className="border-r overflow-y-auto p-4 space-y-5 bg-card/30">
          <div>
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Target className="h-4 w-4 text-primary" /> Scenario Controls
            </h3>
          </div>

          <SliderControl
            label="Simulation Length"
            value={scenarioInputs.num_rounds}
            min={6} max={60} step={6}
            format={(v) => `${v} months`}
            onChange={(v) => handleSliderChange('num_rounds', v)}
          />
          <SliderControl
            label="Hiring Rate"
            value={scenarioInputs.hiring_rate}
            min={0} max={10} step={1}
            format={(v) => `${v}/quarter`}
            onChange={(v) => handleSliderChange('hiring_rate', v)}
          />
          <SliderControl
            label="Pricing Change"
            value={scenarioInputs.pricing_change}
            min={-30} max={50} step={5}
            format={(v) => `${v > 0 ? '+' : ''}${v}%`}
            onChange={(v) => handleSliderChange('pricing_change', v)}
          />
          <SliderControl
            label="Marketing Spend"
            value={scenarioInputs.marketing_spend_multiplier}
            min={0.5} max={3.0} step={0.1}
            format={(v) => `${v.toFixed(1)}x`}
            onChange={(v) => handleSliderChange('marketing_spend_multiplier', v)}
          />

          <div className="border-t pt-4">
            <h4 className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider">Environment</h4>
          </div>

          <SliderControl
            label="Funding Climate"
            value={scenarioInputs.funding_climate}
            min={0.1} max={0.9} step={0.1}
            format={(v) => v > 0.6 ? 'Favorable' : v > 0.4 ? 'Neutral' : 'Tight'}
            onChange={(v) => handleSliderChange('funding_climate', v)}
          />
          <SliderControl
            label="Market Volatility"
            value={scenarioInputs.market_volatility}
            min={0.0} max={0.5} step={0.05}
            format={(v) => v > 0.3 ? 'High' : v > 0.15 ? 'Moderate' : 'Low'}
            onChange={(v) => handleSliderChange('market_volatility', v)}
          />

          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Market Trend</label>
            <Select
              value={scenarioInputs.market_trend}
              onValueChange={(v) => setScenarioInputs(prev => ({ ...prev, market_trend: v }))}
            >
              <SelectTrigger data-testid="select-market-trend"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="bull">Bull Market</SelectItem>
                <SelectItem value="neutral">Neutral</SelectItem>
                <SelectItem value="bear">Bear Market</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="border-t pt-4">
            <h4 className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider">Founder DNA</h4>
          </div>

          <SliderControl
            label="Risk Tolerance"
            value={scenarioInputs.founder_risk_tolerance}
            min={0.1} max={0.9} step={0.1}
            format={(v) => v > 0.7 ? 'Aggressive' : v > 0.4 ? 'Balanced' : 'Conservative'}
            onChange={(v) => handleSliderChange('founder_risk_tolerance', v)}
          />
          <SliderControl
            label="Hiring Aggressiveness"
            value={scenarioInputs.hiring_aggressiveness}
            min={0.1} max={0.9} step={0.1}
            format={(v) => v > 0.7 ? 'Aggressive' : v > 0.4 ? 'Moderate' : 'Conservative'}
            onChange={(v) => handleSliderChange('hiring_aggressiveness', v)}
          />
        </div>

        {/* CENTER PANEL — Simulation Results */}
        <div className="overflow-y-auto p-6" data-testid="simulation-center-panel">
          {!result && !runMutation.isPending && (
            <EmptyState onRun={() => runMutation.mutate()} />
          )}

          {runMutation.isPending && <SimulationLoading />}

          {result && (
            <div className="space-y-6">
              <SummaryCards summary={result.summary} report={result.report} />

              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="w-full">
                  <TabsTrigger value="timeline" className="flex-1" data-testid="tab-timeline">Timeline</TabsTrigger>
                  <TabsTrigger value="events" className="flex-1" data-testid="tab-events">Events ({result.events.length})</TabsTrigger>
                  <TabsTrigger value="agents" className="flex-1" data-testid="tab-agents">Agents</TabsTrigger>
                  <TabsTrigger value="charts" className="flex-1" data-testid="tab-charts">Charts</TabsTrigger>
                </TabsList>

                <TabsContent value="timeline" className="mt-4">
                  <TimelineView
                    timeline={result.timeline}
                    events={result.events}
                    selectedMonth={selectedMonth}
                    onSelectMonth={setSelectedMonth}
                  />
                </TabsContent>

                <TabsContent value="events" className="mt-4">
                  <EventFeed events={filteredEvents || []} selectedMonth={selectedMonth} onClearFilter={() => setSelectedMonth(null)} />
                </TabsContent>

                <TabsContent value="agents" className="mt-4">
                  <AgentStatesView agentStates={result.agentStates} report={result.report} />
                </TabsContent>

                <TabsContent value="charts" className="mt-4">
                  <ChartsView timeline={result.timeline} trajectories={result.trajectories} />
                </TabsContent>
              </Tabs>
            </div>
          )}
        </div>

        {/* RIGHT PANEL — AI Insights */}
        <div className="border-l overflow-y-auto p-4 bg-card/30">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" /> AI Insights
          </h3>

          {!result && (
            <div className="text-sm text-muted-foreground italic">
              Run a simulation to see AI-powered insights and recommendations.
            </div>
          )}

          {result && (
            <div className="space-y-4">
              {result.report && (
                <Card className={cn(
                  "border",
                  result.report.ratingColor === 'green' && 'border-green-500/30',
                  result.report.ratingColor === 'yellow' && 'border-yellow-500/30',
                  result.report.ratingColor === 'orange' && 'border-orange-500/30',
                  result.report.ratingColor === 'red' && 'border-red-500/30',
                )}>
                  <CardContent className="pt-4 pb-3">
                    <Badge variant="outline" className={cn(
                      "mb-2",
                      result.report.ratingColor === 'green' && 'text-green-500 border-green-500/30',
                      result.report.ratingColor === 'yellow' && 'text-yellow-500 border-yellow-500/30',
                      result.report.ratingColor === 'orange' && 'text-orange-500 border-orange-500/30',
                      result.report.ratingColor === 'red' && 'text-red-500 border-red-500/30',
                    )}>
                      {result.report.ratingLabel}
                    </Badge>
                    <p className="text-sm mt-1">{result.report.headline}</p>
                  </CardContent>
                </Card>
              )}

              {result.keyRisks.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2">Key Risks</h4>
                  <div className="space-y-2">
                    {result.keyRisks.map((risk, i) => {
                      const sev = SEVERITY_CONFIG[risk.severity as keyof typeof SEVERITY_CONFIG] || SEVERITY_CONFIG.info;
                      return (
                        <div key={i} className={cn("p-2.5 rounded-lg border text-sm", sev.bg, sev.border)}>
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <AlertTriangle className={cn("h-3.5 w-3.5", sev.color)} />
                            <span className="font-medium text-xs">{risk.type.replace(/_/g, ' ')}</span>
                            <Badge variant="outline" className="ml-auto text-[10px] py-0">{risk.occurrences}x</Badge>
                          </div>
                          <p className="text-xs text-muted-foreground">{risk.description}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2">Recommendations</h4>
                <div className="space-y-2">
                  {result.recommendations.map((rec, i) => {
                    const pri = PRIORITY_CONFIG[rec.priority] || PRIORITY_CONFIG.info;
                    return (
                      <div key={i} className={cn("p-2.5 rounded-lg border", pri.bg, 'border-border')}>
                        <div className="flex items-center gap-1.5 mb-1">
                          <Badge variant="outline" className={cn("text-[10px] py-0", pri.color)}>{rec.priority}</Badge>
                          <span className="text-xs font-medium">{rec.title}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">{rec.description}</p>
                        <p className="text-xs text-primary mt-1">{rec.impact}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {result.report?.turningPoints?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2">Turning Points</h4>
                  <div className="space-y-1.5">
                    {result.report.turningPoints.map((tp, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-2 text-xs p-2 rounded hover:bg-muted/50 cursor-pointer"
                        onClick={() => { setSelectedMonth(tp.month); setActiveTab('events'); }}
                        data-testid={`turning-point-${i}`}
                      >
                        <span className="text-muted-foreground font-mono shrink-0">M{tp.month}</span>
                        <span>{tp.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


function SliderControl({ label, value, min, max, step, format, onChange }: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  onChange: (v: number[]) => void;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <label className="text-xs text-muted-foreground">{label}</label>
        <span className="text-xs font-mono font-medium">{format(value)}</span>
      </div>
      <Slider value={[value]} min={min} max={max} step={step} onValueChange={onChange} className="w-full" />
    </div>
  );
}


function EmptyState({ onRun }: { onRun: () => void }) {
  return (
    <div className="flex items-center justify-center h-full min-h-[400px]">
      <div className="text-center max-w-md">
        <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-primary/10 flex items-center justify-center">
          <Zap className="h-10 w-10 text-primary" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Flight Simulator</h2>
        <p className="text-muted-foreground mb-6">
          Run a multi-agent simulation to see how your startup navigates the next 24 months.
          Five AI agents — Founder, Investor, Customer, Team, and Market — interact to model
          realistic outcomes based on your data.
        </p>
        <Button onClick={onRun} size="lg" data-testid="button-run-empty">
          <Play className="h-5 w-5 mr-2" /> Launch Simulation
        </Button>
      </div>
    </div>
  );
}


function SimulationLoading() {
  const messages = [
    "Initializing agents...",
    "Building knowledge graph...",
    "Simulating market conditions...",
    "Investors evaluating your metrics...",
    "Customers reacting to product changes...",
    "Team dynamics evolving...",
    "Compiling results...",
  ];
  const [msgIdx, setMsgIdx] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setMsgIdx(prev => (prev + 1) % messages.length);
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center justify-center h-full min-h-[400px]">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
        <h3 className="text-lg font-semibold mb-2">Running Agent Simulation</h3>
        <p className="text-sm text-muted-foreground animate-pulse">{messages[msgIdx]}</p>
      </div>
    </div>
  );
}


function SummaryCards({ summary, report }: { summary: SimulationResult['summary']; report: SimulationResult['report'] }) {
  const ratingColor = report?.ratingColor || 'green';
  const survivalColor = summary.survivalProbability >= 70 ? 'text-green-500' :
    summary.survivalProbability >= 40 ? 'text-yellow-500' : 'text-red-500';

  return (
    <div className="grid grid-cols-4 gap-3" data-testid="summary-cards">
      <Card>
        <CardContent className="pt-4 pb-3">
          <div className="text-xs text-muted-foreground mb-1">Survival</div>
          <div className={cn("text-2xl font-bold font-mono", survivalColor)}>
            {summary.survivalProbability.toFixed(0)}%
          </div>
          <div className="text-xs text-muted-foreground">probability</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4 pb-3">
          <div className="text-xs text-muted-foreground mb-1">Funding</div>
          <div className="text-2xl font-bold font-mono text-emerald-500">
            {summary.fundingProbability.toFixed(0)}%
          </div>
          <div className="text-xs text-muted-foreground">probability</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4 pb-3">
          <div className="text-xs text-muted-foreground mb-1">Final Cash</div>
          <div className={cn("text-2xl font-bold font-mono", summary.finalCash > 0 ? 'text-green-500' : 'text-red-500')}>
            {formatCurrencyAbbrev(summary.finalCash)}
          </div>
          <div className="text-xs text-muted-foreground">{summary.finalRunway > 900 ? 'Sustainable' : `${summary.finalRunway.toFixed(0)}mo runway`}</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4 pb-3">
          <div className="text-xs text-muted-foreground mb-1">Events</div>
          <div className="text-2xl font-bold font-mono">{summary.totalEvents}</div>
          <div className="text-xs text-muted-foreground">{summary.riskEvents} risk events</div>
        </CardContent>
      </Card>
    </div>
  );
}


function TimelineView({ timeline, events, selectedMonth, onSelectMonth }: {
  timeline: SimulationResult['timeline'];
  events: SimulationResult['events'];
  selectedMonth: number | null;
  onSelectMonth: (m: number | null) => void;
}) {
  const eventsByMonth: Record<number, typeof events> = {};
  events.forEach(e => {
    if (!eventsByMonth[e.month]) eventsByMonth[e.month] = [];
    eventsByMonth[e.month].push(e);
  });

  return (
    <div className="space-y-2" data-testid="timeline-view">
      {timeline.map((snap) => {
        const monthEvents = eventsByMonth[snap.month] || [];
        const hasRisk = monthEvents.some(e => e.severity === 'warning' || e.severity === 'danger');
        const isSelected = selectedMonth === snap.month;

        return (
          <div
            key={snap.month}
            className={cn(
              "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
              isSelected ? 'border-primary bg-primary/5' :
              !snap.survival ? 'border-red-500/30 bg-red-500/5' :
              hasRisk ? 'border-yellow-500/20 bg-yellow-500/5 hover:border-yellow-500/40' :
              'border-border hover:border-primary/30 hover:bg-muted/30'
            )}
            onClick={() => onSelectMonth(isSelected ? null : snap.month)}
            data-testid={`timeline-month-${snap.month}`}
          >
            <div className="shrink-0 w-12 text-center">
              <div className="text-xs text-muted-foreground">Month</div>
              <div className="text-lg font-bold font-mono">{snap.month}</div>
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 text-xs mb-1">
                <span className="font-mono">
                  <span className="text-muted-foreground">Cash </span>
                  <span className={snap.cash_balance > 0 ? 'text-green-500' : 'text-red-500'}>
                    {formatCurrencyAbbrev(snap.cash_balance)}
                  </span>
                </span>
                <span className="font-mono">
                  <span className="text-muted-foreground">Rev </span>
                  {formatCurrencyAbbrev(snap.monthly_revenue)}
                </span>
                <span className="font-mono">
                  <span className="text-muted-foreground">Burn </span>
                  {formatCurrencyAbbrev(snap.monthly_burn)}
                </span>
                <span className="font-mono">
                  <span className="text-muted-foreground">Runway </span>
                  {snap.runway_months > 900 ? '∞' : `${snap.runway_months.toFixed(0)}mo`}
                </span>
              </div>

              {monthEvents.length > 0 && (
                <div className="space-y-1 mt-1.5">
                  {monthEvents.slice(0, 3).map((e, i) => {
                    const agent = AGENT_CONFIG[e.agentType as keyof typeof AGENT_CONFIG];
                    const sev = SEVERITY_CONFIG[e.severity as keyof typeof SEVERITY_CONFIG] || SEVERITY_CONFIG.info;
                    return (
                      <div key={i} className="flex items-center gap-1.5 text-xs">
                        <span className={cn("font-medium", agent?.color || 'text-muted-foreground')}>
                          {agent?.label || e.agentType}:
                        </span>
                        <span className="text-muted-foreground truncate">{e.description}</span>
                      </div>
                    );
                  })}
                  {monthEvents.length > 3 && (
                    <div className="text-xs text-muted-foreground">+{monthEvents.length - 3} more events</div>
                  )}
                </div>
              )}
            </div>

            {!snap.survival && (
              <Badge variant="destructive" className="shrink-0 text-[10px]">Cash Out</Badge>
            )}
          </div>
        );
      })}
    </div>
  );
}


function EventFeed({ events, selectedMonth, onClearFilter }: {
  events: SimulationResult['events'];
  selectedMonth: number | null;
  onClearFilter: () => void;
}) {
  return (
    <div data-testid="event-feed">
      {selectedMonth && (
        <div className="flex items-center gap-2 mb-3 text-sm">
          <Badge variant="outline">Month {selectedMonth}</Badge>
          <Button variant="ghost" size="sm" onClick={onClearFilter} className="text-xs h-6">Clear filter</Button>
        </div>
      )}

      <div className="space-y-1.5">
        {events.map((event, i) => {
          const agent = AGENT_CONFIG[event.agentType as keyof typeof AGENT_CONFIG];
          const sev = SEVERITY_CONFIG[event.severity as keyof typeof SEVERITY_CONFIG] || SEVERITY_CONFIG.info;
          const SevIcon = sev.icon;

          return (
            <div key={i} className={cn("flex items-start gap-2.5 p-2.5 rounded-lg border", sev.bg, sev.border)}>
              <div className="shrink-0 mt-0.5">
                <SevIcon className={cn("h-3.5 w-3.5", sev.color)} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-mono text-muted-foreground">M{event.month}</span>
                  <Badge variant="outline" className={cn("text-[10px] py-0", agent?.color)}>
                    {agent?.label || event.agentType}
                  </Badge>
                  <span className="text-[10px] text-muted-foreground">{event.eventType.replace(/_/g, ' ')}</span>
                </div>
                <p className="text-xs">{event.description}</p>
              </div>
            </div>
          );
        })}
        {events.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-8">No events to display</p>
        )}
      </div>
    </div>
  );
}


function AgentStatesView({ agentStates, report }: {
  agentStates: SimulationResult['agentStates'];
  report: SimulationResult['report'];
}) {
  const agentSummary = report?.agentSummary || {};

  return (
    <div className="space-y-3" data-testid="agent-states">
      {Object.entries(AGENT_CONFIG).map(([key, config]) => {
        const Icon = config.icon;
        const summary = agentSummary[key];
        const sentimentEmoji = (s: string) => {
          switch (s) {
            case 'very_positive': return '🟢';
            case 'positive': return '🟢';
            case 'neutral': return '🟡';
            case 'negative': return '🔴';
            case 'very_negative': return '🔴';
            default: return '⚪';
          }
        };

        return (
          <Card key={key}>
            <CardContent className="pt-4 pb-3">
              <div className="flex items-center gap-2 mb-2">
                <div className={cn("p-1.5 rounded", config.bg)}>
                  <Icon className={cn("h-4 w-4", config.color)} />
                </div>
                <span className="font-medium text-sm">{config.label} Agent</span>
                {summary && (
                  <span className="ml-auto text-xs text-muted-foreground">
                    {sentimentEmoji(summary.finalSentiment)} {summary.finalSentiment.replace(/_/g, ' ')}
                  </span>
                )}
              </div>
              {summary && (
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span>Confidence: {(summary.averageConfidence * 100).toFixed(0)}%</span>
                  <span>Trend: {summary.trend}</span>
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}


function ChartsView({ timeline, trajectories }: {
  timeline: SimulationResult['timeline'];
  trajectories: SimulationResult['trajectories'];
}) {
  const chartData = timeline.map(s => ({
    month: `M${s.month}`,
    cash: Math.round(s.cash_balance),
    revenue: Math.round(s.monthly_revenue),
    burn: Math.round(s.monthly_burn),
    runway: Math.min(s.runway_months, 60),
    customers: s.customers,
    headcount: s.headcount,
  }));

  return (
    <div className="space-y-6" data-testid="charts-view">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Cash & Revenue</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="cashGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => formatCurrencyAbbrev(v)} />
                <RechartsTooltip
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '12px' }}
                  formatter={(value: number, name: string) => [formatCurrencyAbbrev(value), name === 'cash' ? 'Cash' : 'Revenue']}
                />
                <Area type="monotone" dataKey="cash" stroke="hsl(var(--primary))" fill="url(#cashGrad)" name="Cash" />
                <Area type="monotone" dataKey="revenue" stroke="#10b981" fill="url(#revGrad)" name="Revenue" />
                <Legend />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Runway & Growth</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <RechartsTooltip
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '12px' }}
                />
                <Line type="monotone" dataKey="runway" stroke="#f59e0b" dot={false} name="Runway (months)" />
                <Line type="monotone" dataKey="headcount" stroke="#8b5cf6" dot={false} name="Headcount" />
                <Legend />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


export function SharedSimulationPage() {
  const [, params] = useRoute('/simulate-v2/shared/:token');
  const token = params?.token;

  const { data, isLoading, error } = useQuery({
    queryKey: ['/api/simulation/shared', token],
    queryFn: async () => {
      const res = await fetch(`/api/simulation/shared/${token}`);
      if (!res.ok) throw new Error('Simulation not found');
      return res.json();
    },
    enabled: !!token,
  });

  if (isLoading) return <div className="flex items-center justify-center h-full"><Loader2 className="h-8 w-8 animate-spin" /></div>;
  if (error || !data) return <div className="flex items-center justify-center h-full"><p className="text-muted-foreground">Simulation not found</p></div>;

  const report = data.report || {};

  return (
    <div className="max-w-4xl mx-auto p-8" data-testid="shared-simulation">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-2">{data.companyName} — Flight Simulation</h1>
        <p className="text-muted-foreground">Generated on {data.createdAt ? new Date(data.createdAt).toLocaleDateString() : 'N/A'}</p>
      </div>

      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="text-center">
            <div className={cn(
              "text-6xl font-bold font-mono mb-2",
              data.summary?.survivalProbability >= 70 ? 'text-green-500' :
              data.summary?.survivalProbability >= 40 ? 'text-yellow-500' : 'text-red-500'
            )}>
              {data.summary?.survivalProbability?.toFixed(0) || 0}%
            </div>
            <p className="text-lg text-muted-foreground mb-4">Survival Probability</p>
            {report.headline && <p className="text-sm max-w-lg mx-auto">{report.headline}</p>}
          </div>
        </CardContent>
      </Card>

      {data.recommendations?.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {data.recommendations.map((rec: any, i: number) => (
                <div key={i} className="flex items-start gap-3">
                  <Badge variant="outline" className={PRIORITY_CONFIG[rec.priority]?.color}>{rec.priority}</Badge>
                  <div>
                    <p className="font-medium text-sm">{rec.title}</p>
                    <p className="text-xs text-muted-foreground">{rec.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="text-center mt-8">
        <p className="text-sm text-muted-foreground mb-3">Powered by FounderConsole Flight Simulator</p>
        <Button variant="outline" asChild>
          <a href="/" data-testid="link-try-founderconsole">Try FounderConsole</a>
        </Button>
      </div>
    </div>
  );
}
