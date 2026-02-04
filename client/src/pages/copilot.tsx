import { useState, useRef, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Slider } from '@/components/ui/slider';
import { Textarea } from '@/components/ui/textarea';
import { FeedbackButton } from '@/components/FeedbackButton';
import { 
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  BarChart, Bar, Cell, ReferenceLine
} from 'recharts';
import { 
  Send, 
  Sparkles, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Play, 
  Database, 
  BarChart3, 
  Target,
  Bot,
  User,
  ChevronDown,
  AlertTriangle,
  Lightbulb,
  Users,
  Building2,
  HelpCircle,
  Zap,
  Eye,
  FileText,
  Shield,
  Link2,
  Activity,
  GitCompare,
  Terminal,
  Plus,
  X,
  StickyNote,
  Cpu,
  Sliders,
  PanelRightClose,
  PanelRight,
  Menu,
  ChevronRight,
  MessageSquare
} from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useTruthScan, useSimulation, useScenarios } from '@/api/hooks';
import { apiRequest } from '@/lib/queryClient';
import { useToast } from '@/hooks/use-toast';

type DataSource = 'truth_scan' | 'simulation' | 'scenario' | 'benchmark' | 'cfo_agent' | 'market_agent' | 'strategy_agent';

interface CopilotApiResponse {
  executive_summary: string[];
  company_snapshot: string[];
  financials?: {
    metrics?: Record<string, any>;
    extracted?: Record<string, any>;
    health_score?: number;
  };
  market_and_customers?: {
    icp?: any;
    competitors?: any[];
    benchmarks?: Record<string, any>;
    this_month_targets?: Array<{
      company_name: string;
      industry: string;
      why_now: string;
      outreach_channel: string;
      talking_points: string[];
      priority: string;
    }>;
  };
  strategy_options?: Array<{
    title: string;
    description: string;
    impact: string;
    risk_level: string;
    timeline: string;
  }>;
  recommendations?: Array<{
    action: string;
    priority: string;
    rationale: string;
    expected_impact: string;
  }>;
  assumptions: string[];
  risks: string[];
  next_questions: string[];
  confidence: string;
  ckb_updated: boolean;
  decision_created?: {
    id: string;
    title: string;
    status: string;
  };
  challenge?: {
    mode: string;
    challenges: Array<{
      recommendation: string;
      counterarguments: string[];
      stress_test: Record<string, string>;
      alternative_perspectives: string[];
    }>;
    summary: string;
  };
  investor_analysis?: {
    investor_type: string;
    evaluation_criteria: Record<string, any>;
    company_fit_analysis: {
      strengths: string[];
      gaps: string[];
      score: string;
    };
    recommendation_alignment: Array<{
      action: string;
      investor_perspective: string;
      concerns: string;
    }>;
  };
  citations?: Array<{
    source_id: string;
    label: string;
    kind?: string;
    page?: number;
    url?: string;
    snippet?: string;
  }>;
  highlighted_claims?: Array<{
    text: string;
    source_ids: string[];
    confidence: string;
  }>;
  data_health?: {
    score: number;
    grade: string;
    issues: Array<{
      severity: string;
      code: string;
      message: string;
      suggested_fix: string;
    }>;
  };
  pii_findings?: Array<{
    type: string;
    count: number;
    examples: string[];
    confidence: string;
  }>;
  pii_mode?: string;
  simulation_result?: {
    success: boolean;
    intent: string;
    action: string;
    summary: string;
    scenario_id?: number;
    scenario_name?: string;
    simulation_id?: number;
    results?: {
      runway_months: number;
      survival_rate: number;
      final_cash: number;
      confidence_intervals?: Record<string, number>;
    };
    parameters?: {
      burn_reduction_pct?: number | null;
      price_change_pct?: number | null;
      revenue_growth_pct?: number | null;
      hiring_freeze_months?: number | null;
      fundraise_amount?: number | null;
      horizon_months?: number;
    };
    comparison?: {
      scenario_1: { name: string; runway: number; survival: number };
      scenario_2: { name: string; runway: number; survival: number };
      differences: { runway_months: number; survival_rate: number };
    };
    chart_data?: {
      runway?: {
        type: string;
        scenario_name: string;
        metrics: { p10: number; p25: number; p50: number; p75: number; p90: number };
      };
      cash_trajectory?: Array<{ month: number; mean: number; p10?: number; p90?: number }>;
      survival_trajectory?: Array<{ month: number; survival_rate: number }>;
    };
    recommendations?: Array<{
      type: string;
      priority: number;
      text: string;
      action_prompt: string;
    }>;
  };
  intent_detected?: string;
  clarifications?: Array<{
    field: string;
    question: string;
    options?: string[];
    example?: string;
  }>;
  follow_up_actions?: Array<{
    label: string;
    action: string;
  }>;
  decision_advisor?: {
    decision_context: {
      type: string;
      core_decision: string;
      timeframe_months: number;
      target?: string;
      constraints: string[];
    };
    levers: Array<{
      name: string;
      change_percent: number;
      impact: string;
      feasibility: string;
      time_to_implement: number;
    }>;
    simulations: Array<{
      scenario: string;
      runway: { p10: number; p50: number; p90: number };
      survival: { '12m': number; '18m': number; '24m': number };
      risks: string[];
    }>;
    risk_analysis: {
      riskiest_assumptions: Array<{
        assumption: string;
        risk_level: string;
        impact: string;
        mitigation: string;
      }>;
      sensitivity: Array<{
        variable: string;
        current: number;
        sensitivity: string;
        runway_impact: string;
        survival_impact: string;
      }>;
      failure_cascade: string;
    };
    recommendation: {
      primary_action: string;
      details: string;
      expected_impact: string;
      confidence: string;
      confidence_reasoning: string;
      alternatives: string[];
      what_changes: string;
    };
  };
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  metrics?: string[];
  dataSources?: DataSource[];
  suggestion?: { label: string; action: string };
  timestamp?: Date;
  structuredResponse?: CopilotApiResponse;
}

const DATA_SOURCE_CONFIG: Record<DataSource, { label: string; icon: typeof Database; className: string }> = {
  truth_scan: { 
    label: 'Truth Scan', 
    icon: Database, 
    className: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' 
  },
  simulation: { 
    label: 'Simulation', 
    icon: BarChart3, 
    className: 'bg-blue-500/20 text-blue-400 border-blue-500/30' 
  },
  scenario: { 
    label: 'Scenario', 
    icon: Target, 
    className: 'bg-purple-500/20 text-purple-400 border-purple-500/30' 
  },
  benchmark: { 
    label: 'Benchmark', 
    icon: TrendingUp, 
    className: 'bg-amber-500/20 text-amber-400 border-amber-500/30' 
  },
  cfo_agent: { 
    label: 'CFO Agent', 
    icon: DollarSign, 
    className: 'bg-green-500/20 text-green-400 border-green-500/30' 
  },
  market_agent: { 
    label: 'Market Agent', 
    icon: Users, 
    className: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' 
  },
  strategy_agent: { 
    label: 'Strategy Agent', 
    icon: Building2, 
    className: 'bg-orange-500/20 text-orange-400 border-orange-500/30' 
  },
};

const SIMULATION_COMMANDS = [
  { label: 'Run a simulation cutting burn by 20%', icon: Play, category: 'simulation' },
  { label: 'Compare current vs aggressive growth scenario', icon: GitCompare, category: 'simulation' },
  { label: 'What happens if revenue grows 15% next quarter?', icon: TrendingUp, category: 'simulation' },
  { label: 'Show me 18-month runway with a $500K fundraise', icon: DollarSign, category: 'simulation' },
  { label: 'Model a hiring freeze for 6 months', icon: Users, category: 'simulation' },
];

const SUGGESTED_PROMPTS = [
  { label: 'How can I extend my runway by 6 months?', icon: TrendingUp, category: 'strategy' },
  { label: "What's the riskiest assumption in my financials?", icon: TrendingDown, category: 'analysis' },
  { label: 'What if my fundraise slips by 3 months?', icon: DollarSign, category: 'scenario' },
  { label: 'Who are my top competitors and how do I differentiate?', icon: Users, category: 'market' },
  { label: 'What strategic options should I consider for growth?', icon: Lightbulb, category: 'strategy' },
  { label: 'How much dilution will I face in the next round?', icon: DollarSign, category: 'fundraising' },
  { label: 'What valuation should I target for my Series A?', icon: TrendingUp, category: 'fundraising' },
  { label: 'Help me prepare my investor data room checklist', icon: FileText, category: 'fundraising' },
];

const SLASH_COMMANDS = [
  { command: '/run-scenario', description: 'Run a scenario simulation with assumptions', icon: Sliders },
  { command: '/metrics', description: 'View your key business metrics', icon: BarChart3 },
  { command: '/notes', description: 'View your pinned notes', icon: StickyNote },
  { command: '/fetch-metric', description: 'Fetch a specific metric value', icon: Database },
  { command: '/compare', description: 'Compare two scenarios', icon: GitCompare },
  { command: '/extend-runway', description: 'Analyze ways to extend runway', icon: TrendingUp },
  { command: '/help', description: 'Show available commands', icon: HelpCircle },
];

interface PinnedNote {
  id: string;
  content: string;
  timestamp: Date;
}

interface ScenarioAssumptions {
  growthRate: number;
  priceChange: number;
  hiringRate: number;
  burnReduction: number;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

const CONVERSATIONS_STORAGE_KEY = 'copilot_conversations_';

const generateConversationTitle = (messages: Message[]): string => {
  const firstUserMessage = messages.find(m => m.role === 'user');
  if (firstUserMessage) {
    const title = firstUserMessage.content.slice(0, 40);
    return title.length < firstUserMessage.content.length ? `${title}...` : title;
  }
  return 'New Conversation';
};

function RunwayBandChart({ chartData }: { chartData: NonNullable<CopilotApiResponse['simulation_result']>['chart_data'] }) {
  if (!chartData?.runway?.metrics) return null;
  
  const { metrics } = chartData.runway;
  const data = [
    { name: 'P10', value: metrics.p10, fill: '#ef4444' },
    { name: 'P25', value: metrics.p25, fill: '#f97316' },
    { name: 'P50', value: metrics.p50, fill: '#22c55e' },
    { name: 'P75', value: metrics.p75, fill: '#3b82f6' },
    { name: 'P90', value: metrics.p90, fill: '#8b5cf6' },
  ];
  
  return (
    <div className="h-24 w-full" data-testid="runway-band-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 30 }}>
          <XAxis type="number" tick={{ fontSize: 10, fill: '#888' }} domain={[0, 'auto']} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#888' }} />
          <Tooltip 
            contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
            formatter={(value: number) => [`${value.toFixed(1)} months`, 'Runway']}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Bar>
          <ReferenceLine x={12} stroke="#fbbf24" strokeDasharray="3 3" label={{ value: '12mo', position: 'top', fontSize: 10, fill: '#fbbf24' }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function CashTrajectoryChart({ chartData }: { chartData: NonNullable<CopilotApiResponse['simulation_result']>['chart_data'] }) {
  if (!chartData?.cash_trajectory || chartData.cash_trajectory.length === 0) return null;
  
  const data = chartData.cash_trajectory.map(d => ({
    ...d,
    meanK: d.mean / 1000,
    p10K: d.p10 ? d.p10 / 1000 : undefined,
    p90K: d.p90 ? d.p90 / 1000 : undefined,
  }));
  
  return (
    <div className="h-32 w-full" data-testid="cash-trajectory-chart">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <XAxis dataKey="month" tick={{ fontSize: 9, fill: '#888' }} tickFormatter={(v) => `M${v}`} />
          <YAxis tick={{ fontSize: 9, fill: '#888' }} tickFormatter={(v) => `$${v}K`} />
          <Tooltip 
            contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
            formatter={(value: number) => [`$${value.toFixed(0)}K`, 'Cash']}
          />
          {data[0]?.p10K !== undefined && (
            <Area type="monotone" dataKey="p10K" stroke="transparent" fill="#ef444433" />
          )}
          {data[0]?.p90K !== undefined && (
            <Area type="monotone" dataKey="p90K" stroke="transparent" fill="#22c55533" />
          )}
          <Area type="monotone" dataKey="meanK" stroke="#3b82f6" fill="#3b82f666" strokeWidth={2} />
          <ReferenceLine y={0} stroke="#ef4444" strokeDasharray="3 3" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function RecommendationsPanel({ recommendations, onTryPrompt }: { recommendations?: NonNullable<CopilotApiResponse['simulation_result']>['recommendations']; onTryPrompt?: (prompt: string) => void }) {
  if (!recommendations || recommendations.length === 0) return null;
  
  return (
    <div className="mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20" data-testid="recommendations-panel">
      <div className="flex items-center gap-2 mb-2">
        <Lightbulb className="h-4 w-4 text-amber-400" />
        <span className="text-xs font-semibold">Suggested Next Steps</span>
      </div>
      <div className="space-y-2">
        {recommendations.slice(0, 3).map((rec, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className="text-xs text-muted-foreground mt-0.5">{i + 1}.</span>
            <div className="flex-1">
              <p className="text-xs">{rec.text}</p>
              {rec.action_prompt && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-auto p-0 text-xs text-blue-400 hover:text-blue-300 hover:bg-transparent"
                  onClick={() => onTryPrompt?.(rec.action_prompt.replace(/^Try: '|'$/g, '').replace(/^"|"$/g, ''))}
                  data-testid={`button-rec-${i}`}
                >
                  {rec.action_prompt}
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SimulationResultCard({ response, onAction, onTryPrompt }: { response: CopilotApiResponse; onAction?: (action: string) => void; onTryPrompt?: (prompt: string) => void }) {
  const simResult = response.simulation_result;
  const [showCharts, setShowCharts] = useState(true);
  if (!simResult) return null;

  const results = simResult.results;
  const params = simResult.parameters;
  const chartData = simResult.chart_data;
  const recommendations = simResult.recommendations;

  return (
    <div className="mt-4 p-4 rounded-lg bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20" data-testid="simulation-result-card">
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-blue-400" />
          <span className="font-semibold text-sm">Simulation Results</span>
          {simResult.scenario_name && (
            <Badge variant="outline" className="text-xs">{simResult.scenario_name}</Badge>
          )}
        </div>
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={() => setShowCharts(!showCharts)}
          className="h-6 px-2 text-xs"
        >
          {showCharts ? 'Hide' : 'Show'} Charts
        </Button>
      </div>
      
      {results && (
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="p-3 rounded-lg bg-card/50 border border-border/30 text-center">
            <div className="text-2xl font-bold text-blue-400">{results.runway_months?.toFixed(1) || '0'}</div>
            <div className="text-xs text-muted-foreground">Runway (months)</div>
          </div>
          <div className="p-3 rounded-lg bg-card/50 border border-border/30 text-center">
            <div className="text-2xl font-bold text-emerald-400">{((results.survival_rate || 0) * 100).toFixed(0)}%</div>
            <div className="text-xs text-muted-foreground">Survival Rate</div>
          </div>
          <div className="p-3 rounded-lg bg-card/50 border border-border/30 text-center">
            <div className="text-2xl font-bold text-purple-400">${((results.final_cash || 0) / 1000).toFixed(0)}K</div>
            <div className="text-xs text-muted-foreground">Final Cash</div>
          </div>
        </div>
      )}

      {showCharts && chartData && (
        <div className="mb-4 space-y-3">
          {chartData.runway && (
            <div className="p-2 rounded-lg bg-card/30 border border-border/20">
              <p className="text-xs text-muted-foreground mb-1">Runway Distribution (P10-P90)</p>
              <RunwayBandChart chartData={chartData} />
            </div>
          )}
          {chartData.cash_trajectory && chartData.cash_trajectory.length > 0 && (
            <div className="p-2 rounded-lg bg-card/30 border border-border/20">
              <p className="text-xs text-muted-foreground mb-1">Cash Trajectory</p>
              <CashTrajectoryChart chartData={chartData} />
            </div>
          )}
        </div>
      )}

      {params && Object.entries(params).some(([k, v]) => v !== null && k !== 'horizon_months') && (
        <div className="mb-4">
          <p className="text-xs text-muted-foreground mb-2">Parameters Used:</p>
          <div className="flex flex-wrap gap-1.5">
            {params.burn_reduction_pct && (
              <Badge variant="outline" className="text-xs">Burn -{params.burn_reduction_pct}%</Badge>
            )}
            {params.price_change_pct && (
              <Badge variant="outline" className="text-xs">Price {params.price_change_pct > 0 ? '+' : ''}{params.price_change_pct}%</Badge>
            )}
            {params.revenue_growth_pct && (
              <Badge variant="outline" className="text-xs">Growth +{params.revenue_growth_pct}%</Badge>
            )}
            {params.hiring_freeze_months && (
              <Badge variant="outline" className="text-xs">Hiring Freeze {params.hiring_freeze_months}mo</Badge>
            )}
            {params.fundraise_amount && (
              <Badge variant="outline" className="text-xs">Raise ${(params.fundraise_amount / 1000000).toFixed(1)}M</Badge>
            )}
            {params.horizon_months && (
              <Badge variant="outline" className="text-xs text-muted-foreground">{params.horizon_months}mo horizon</Badge>
            )}
          </div>
        </div>
      )}

      {simResult.comparison && (
        <div className="mb-4 p-3 rounded-lg bg-card/50 border border-border/30">
          <p className="text-xs text-muted-foreground mb-2">Comparison</p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="font-medium">{simResult.comparison.scenario_1.name}:</span>
              <span className="ml-2">{simResult.comparison.scenario_1.runway.toFixed(1)}mo</span>
            </div>
            <div>
              <span className="font-medium">{simResult.comparison.scenario_2.name}:</span>
              <span className="ml-2">{simResult.comparison.scenario_2.runway.toFixed(1)}mo</span>
            </div>
          </div>
          <div className="mt-2 text-xs">
            Difference: <span className={simResult.comparison.differences.runway_months > 0 ? 'text-green-400' : 'text-red-400'}>
              {simResult.comparison.differences.runway_months > 0 ? '+' : ''}{simResult.comparison.differences.runway_months.toFixed(1)} months
            </span>
          </div>
        </div>
      )}

      <RecommendationsPanel recommendations={recommendations} onTryPrompt={onTryPrompt} />

      {response.follow_up_actions && response.follow_up_actions.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {response.follow_up_actions.map((action, i) => (
            <Button
              key={i}
              variant="outline"
              size="sm"
              onClick={() => onAction?.(action.action)}
              data-testid={`button-followup-${action.action}`}
            >
              {action.label}
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}

function ClarificationPanel({ response, onSelect }: { response: CopilotApiResponse; onSelect?: (option: string) => void }) {
  const clarifications = response.clarifications;
  if (!clarifications || clarifications.length === 0) return null;

  return (
    <div className="mt-4 p-4 rounded-lg bg-amber-500/10 border border-amber-500/20" data-testid="clarification-panel">
      <div className="flex items-center gap-2 mb-3">
        <HelpCircle className="h-5 w-5 text-amber-400" />
        <span className="font-semibold text-sm">Need More Details</span>
      </div>
      {clarifications.map((c, i) => (
        <div key={i} className="mb-3">
          <p className="text-sm">{c.question}</p>
          {c.options && c.options.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {c.options.map((opt, j) => (
                <Button
                  key={j}
                  variant="outline"
                  size="sm"
                  onClick={() => onSelect?.(opt)}
                  data-testid={`button-clarification-option-${j}`}
                >
                  {opt}
                </Button>
              ))}
            </div>
          )}
          {c.example && (
            <p className="text-xs text-muted-foreground mt-2">Example: "{c.example}"</p>
          )}
        </div>
      ))}
    </div>
  );
}

function DecisionAdvisorPanel({ advisor }: { advisor: CopilotApiResponse['decision_advisor'] }) {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    decision: true,
    simulations: true,
    recommendation: true
  });

  if (!advisor) return null;

  const toggleSection = (section: string) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const { decision_context, levers, simulations, risk_analysis, recommendation } = advisor;

  return (
    <div className="space-y-4 mt-4" data-testid="decision-advisor-panel">
      <Card className="overflow-visible border-primary/30 bg-primary/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Target className="h-4 w-4 text-primary" />
            Decision Analysis
          </CardTitle>
          <CardDescription className="text-xs">
            {decision_context.core_decision}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="text-xs">
              {decision_context.type.replace(/_/g, ' ')}
            </Badge>
            <Badge variant="outline" className="text-xs">
              {decision_context.timeframe_months} month horizon
            </Badge>
            {decision_context.constraints.map((c, i) => (
              <Badge key={i} variant="outline" className="text-xs text-amber-400 border-amber-500/30">
                {c}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {recommendation && (
        <Card className="overflow-visible border-emerald-500/30 bg-emerald-500/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Zap className="h-4 w-4 text-emerald-400" />
              Recommendation
              <Badge 
                variant="outline" 
                className={`ml-auto text-xs ${
                  recommendation.confidence === 'high' ? 'text-emerald-400 border-emerald-500/30' :
                  recommendation.confidence === 'medium' ? 'text-amber-400 border-amber-500/30' :
                  'text-red-400 border-red-500/30'
                }`}
              >
                {recommendation.confidence.toUpperCase()} Confidence
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <p className="font-medium text-sm">{recommendation.primary_action}</p>
              <p className="text-xs text-muted-foreground mt-1">{recommendation.details}</p>
            </div>
            <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/20">
              <p className="text-xs font-medium text-emerald-400">Expected Impact</p>
              <p className="text-sm">{recommendation.expected_impact}</p>
            </div>
            {recommendation.alternatives.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Alternatives:</p>
                <div className="flex flex-wrap gap-1">
                  {recommendation.alternatives.map((alt, i) => (
                    <Badge key={i} variant="outline" className="text-xs">{alt}</Badge>
                  ))}
                </div>
              </div>
            )}
            <p className="text-xs text-muted-foreground italic">{recommendation.what_changes}</p>
          </CardContent>
        </Card>
      )}

      {simulations && simulations.length > 0 && (
        <Collapsible open={openSections['simulations']} onOpenChange={() => toggleSection('simulations')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors">
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['simulations'] ? 'rotate-180' : ''}`} />
            <BarChart3 className="h-4 w-4 text-blue-400" />
            Simulation Results ({simulations.length} scenarios)
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 space-y-2">
            {simulations.map((sim, i) => (
              <div key={i} className="p-3 rounded-lg bg-card border border-border/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">{sim.scenario}</span>
                  <Badge 
                    variant="outline" 
                    className={`text-xs ${
                      sim.survival['18m'] >= 80 ? 'text-emerald-400' :
                      sim.survival['18m'] >= 60 ? 'text-amber-400' : 'text-red-400'
                    }`}
                  >
                    {sim.survival['18m']}% @ 18m
                  </Badge>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="p-2 rounded bg-secondary/50">
                    <p className="text-xs text-muted-foreground">P10</p>
                    <p className="text-sm font-mono">{sim.runway.p10.toFixed(1)}mo</p>
                  </div>
                  <div className="p-2 rounded bg-secondary/50">
                    <p className="text-xs text-muted-foreground">P50</p>
                    <p className="text-sm font-mono font-medium">{sim.runway.p50.toFixed(1)}mo</p>
                  </div>
                  <div className="p-2 rounded bg-secondary/50">
                    <p className="text-xs text-muted-foreground">P90</p>
                    <p className="text-sm font-mono">{sim.runway.p90.toFixed(1)}mo</p>
                  </div>
                </div>
                <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                  <span>12m: {sim.survival['12m']}%</span>
                  <span>18m: {sim.survival['18m']}%</span>
                  <span>24m: {sim.survival['24m']}%</span>
                </div>
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}

      {levers && levers.length > 0 && (
        <Collapsible open={openSections['levers']} onOpenChange={() => toggleSection('levers')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors">
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['levers'] ? 'rotate-180' : ''}`} />
            <Sliders className="h-4 w-4 text-cyan-400" />
            Available Levers ({levers.length})
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 space-y-2">
            {levers.map((lever, i) => (
              <div key={i} className="p-2 rounded bg-card/50 border border-border/30">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{lever.name}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={`text-xs ${
                      lever.feasibility === 'easy' ? 'text-emerald-400' :
                      lever.feasibility === 'moderate' ? 'text-amber-400' : 'text-red-400'
                    }`}>
                      {lever.feasibility}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {lever.change_percent > 0 ? '+' : ''}{lever.change_percent}%
                    </Badge>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-1">{lever.impact}</p>
                <p className="text-xs text-muted-foreground">Implementation: {lever.time_to_implement} month(s)</p>
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}

      {risk_analysis && (
        <Collapsible open={openSections['risks']} onOpenChange={() => toggleSection('risks')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors">
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['risks'] ? 'rotate-180' : ''}`} />
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            Risk Analysis
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 space-y-3">
            {risk_analysis.riskiest_assumptions.length > 0 && (
              <div>
                <p className="text-xs font-medium mb-2">Riskiest Assumptions</p>
                {risk_analysis.riskiest_assumptions.map((risk, i) => (
                  <div key={i} className="p-2 rounded bg-amber-500/5 border border-amber-500/20 mb-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">{risk.assumption}</span>
                      <Badge variant="outline" className={`text-xs ${
                        risk.risk_level === 'High' ? 'text-red-400' : 'text-amber-400'
                      }`}>
                        {risk.risk_level}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{risk.impact}</p>
                    <p className="text-xs text-emerald-400 mt-1">Mitigation: {risk.mitigation}</p>
                  </div>
                ))}
              </div>
            )}
            
            {risk_analysis.sensitivity.length > 0 && (
              <div>
                <p className="text-xs font-medium mb-2">Sensitivity Analysis</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border/50">
                        <th className="text-left py-1">Variable</th>
                        <th className="text-right py-1">Change</th>
                        <th className="text-right py-1">Runway</th>
                        <th className="text-right py-1">Survival</th>
                      </tr>
                    </thead>
                    <tbody>
                      {risk_analysis.sensitivity.map((s, i) => (
                        <tr key={i} className="border-b border-border/30">
                          <td className="py-1">{s.variable}</td>
                          <td className="text-right py-1">{s.sensitivity}</td>
                          <td className="text-right py-1 text-red-400">{s.runway_impact}</td>
                          <td className="text-right py-1 text-red-400">{s.survival_impact}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            
            {risk_analysis.failure_cascade && (
              <div className="p-2 rounded bg-red-500/5 border border-red-500/20">
                <p className="text-xs font-medium text-red-400 mb-1">Failure Cascade</p>
                <p className="text-xs text-muted-foreground">{risk_analysis.failure_cascade}</p>
              </div>
            )}
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  );
}

function StructuredResponseDisplay({ response, messageIndex, showSources, onTryPrompt }: { response: CopilotApiResponse; messageIndex: number; showSources?: boolean; onTryPrompt?: (prompt: string) => void }) {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});
  
  const toggleSection = (section: string) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  };
  
  return (
    <div className="mt-4 space-y-3">
      {response.decision_advisor && <DecisionAdvisorPanel advisor={response.decision_advisor} />}
      {response.simulation_result && <SimulationResultCard response={response} onTryPrompt={onTryPrompt} />}
      {response.clarifications && response.clarifications.length > 0 && <ClarificationPanel response={response} />}
      
      {showSources && response.citations && response.citations.length > 0 && (
        <Collapsible open={openSections['citations']} onOpenChange={() => toggleSection('citations')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors" data-testid={`trigger-citations-${messageIndex}`}>
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['citations'] ? 'rotate-180' : ''}`} />
            <Link2 className="h-4 w-4 text-blue-400" />
            Sources ({response.citations.length})
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 pl-6 space-y-2">
            {response.citations.map((citation, i) => (
              <div key={i} className="p-2 rounded bg-blue-500/5 border border-blue-500/20">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    {citation.kind === 'pdf' ? 'PDF' : citation.kind === 'web' ? 'Web' : 'Analysis'}
                  </Badge>
                  <span className="text-sm font-medium">{citation.label}</span>
                </div>
                {citation.snippet && (
                  <p className="text-xs text-muted-foreground mt-1 italic">"{citation.snippet}"</p>
                )}
                {citation.page && (
                  <p className="text-xs text-muted-foreground mt-1">Page {citation.page}</p>
                )}
                {citation.url && (
                  <a href={citation.url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-400 hover:underline mt-1 block">
                    View source
                  </a>
                )}
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}
      {response.company_snapshot && response.company_snapshot.length > 0 && (
        <Collapsible open={openSections['snapshot']} onOpenChange={() => toggleSection('snapshot')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors" data-testid={`trigger-snapshot-${messageIndex}`}>
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['snapshot'] ? 'rotate-180' : ''}`} />
            <Building2 className="h-4 w-4" />
            Company Snapshot
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 pl-6 space-y-1">
            {response.company_snapshot.map((item, i) => (
              <p key={i} className="text-xs text-muted-foreground">{item}</p>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}
      
      {response.strategy_options && response.strategy_options.length > 0 && (
        <Collapsible open={openSections['strategy']} onOpenChange={() => toggleSection('strategy')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors" data-testid={`trigger-strategy-${messageIndex}`}>
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['strategy'] ? 'rotate-180' : ''}`} />
            <Lightbulb className="h-4 w-4" />
            Strategic Options ({response.strategy_options.length})
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 pl-6 space-y-2">
            {response.strategy_options.map((option, i) => (
              <div key={i} className="p-2 rounded bg-card/50 border border-border/30">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{option.title}</span>
                  <Badge variant="outline" className={option.risk_level === 'Low' ? 'text-green-400' : option.risk_level === 'High' ? 'text-red-400' : 'text-yellow-400'}>
                    {option.risk_level} Risk
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-1">{option.description}</p>
                <div className="flex gap-4 mt-2 text-xs">
                  <span>Impact: {option.impact}</span>
                  <span>Timeline: {option.timeline}</span>
                </div>
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}
      
      {response.recommendations && response.recommendations.length > 0 && (
        <Collapsible open={openSections['recommendations']} onOpenChange={() => toggleSection('recommendations')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors" data-testid={`trigger-recommendations-${messageIndex}`}>
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['recommendations'] ? 'rotate-180' : ''}`} />
            <Target className="h-4 w-4" />
            Recommendations ({response.recommendations.length})
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 pl-6 space-y-2">
            {response.recommendations.map((rec, i) => (
              <div key={i} className="p-2 rounded bg-card/50 border border-border/30">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{rec.action}</span>
                  <Badge variant="outline" className={rec.priority === 'High' ? 'text-red-400' : rec.priority === 'Low' ? 'text-green-400' : 'text-yellow-400'}>
                    {rec.priority} Priority
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-1">{rec.rationale}</p>
                <p className="text-xs text-primary mt-1">Expected: {rec.expected_impact}</p>
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}
      
      {response.risks && response.risks.length > 0 && (
        <Collapsible open={openSections['risks']} onOpenChange={() => toggleSection('risks')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors" data-testid={`trigger-risks-${messageIndex}`}>
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['risks'] ? 'rotate-180' : ''}`} />
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            Risks & Considerations ({response.risks.length})
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 pl-6">
            <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
              {response.risks.map((risk, i) => (
                <li key={i}>{risk}</li>
              ))}
            </ul>
          </CollapsibleContent>
        </Collapsible>
      )}
      
      {response.next_questions && response.next_questions.length > 0 && (
        <div className="pt-2 border-t border-border/30">
          <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
            <HelpCircle className="h-3 w-3" />
            Suggested follow-ups:
          </p>
          <div className="flex flex-wrap gap-1">
            {response.next_questions.slice(0, 3).map((q, i) => (
              <Badge key={i} variant="outline" className="text-xs cursor-pointer hover:bg-primary/10">
                {q}
              </Badge>
            ))}
          </div>
        </div>
      )}
      
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline" className={response.confidence === 'High' ? 'text-green-400 border-green-500/30' : response.confidence === 'Low' ? 'text-red-400 border-red-500/30' : 'text-yellow-400 border-yellow-500/30'}>
          {response.confidence} Confidence
        </Badge>
        {response.ckb_updated && (
          <Badge variant="outline" className="text-blue-400 border-blue-500/30">
            Knowledge Base Updated
          </Badge>
        )}
      </div>
    </div>
  );
}

export default function CopilotPage() {
  const { currentCompany, token } = useFounderStore();
  const { toast } = useToast();
  const { data: truthScan, isLoading: truthLoading } = useTruthScan(currentCompany?.id || null);
  const { data: scenarios } = useScenarios(currentCompany?.id || null);
  const latestScenario = scenarios?.[0];
  const { data: simulation } = useSimulation(latestScenario?.id || null);
  
  const createDefaultMessage = (): Message => ({
    role: 'assistant',
    content: "I'm your AI financial advisor powered by a multi-agent system. I can analyze your financials (CFO Agent), research your market (Market Agent), and develop strategy (Strategy Agent). What would you like to explore?",
    timestamp: new Date(),
  });
  
  const createNewConversation = (): Conversation => ({
    id: crypto.randomUUID(),
    title: 'New Conversation',
    messages: [createDefaultMessage()],
    createdAt: new Date(),
    updatedAt: new Date(),
  });
  
  const loadConversationsFromStorage = (companyId: number): Conversation[] => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(CONVERSATIONS_STORAGE_KEY + companyId);
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          return parsed.map((c: any) => ({
            ...c,
            createdAt: new Date(c.createdAt),
            updatedAt: new Date(c.updatedAt),
            messages: c.messages.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) })),
          }));
        } catch (e) {
          console.error('Failed to parse conversations', e);
        }
      }
    }
    return [];
  };
  
  const [conversations, setConversations] = useState<Conversation[]>([createNewConversation()]);
  const [activeConversationId, setActiveConversationId] = useState<string>(conversations[0]?.id || '');
  const [showConversationSidebar, setShowConversationSidebar] = useState(true);
  
  useEffect(() => {
    if (currentCompany?.id) {
      const loaded = loadConversationsFromStorage(currentCompany.id);
      if (loaded.length > 0) {
        setConversations(loaded);
        setActiveConversationId(loaded[0].id);
      } else {
        const newConv = createNewConversation();
        setConversations([newConv]);
        setActiveConversationId(newConv.id);
      }
    }
  }, [currentCompany?.id]);
  
  const activeConversation = useMemo(() => {
    const found = conversations.find(c => c.id === activeConversationId);
    if (found) return found;
    if (conversations.length > 0) {
      setActiveConversationId(conversations[0].id);
      return conversations[0];
    }
    return null;
  }, [conversations, activeConversationId]);
  
  const messages = activeConversation?.messages || [createDefaultMessage()];
  
  const setMessages = (updater: Message[] | ((prev: Message[]) => Message[])) => {
    setConversations(prevConversations => {
      const targetId = activeConversationId || prevConversations[0]?.id;
      if (!targetId) return prevConversations;
      
      return prevConversations.map(conv => {
        if (conv.id === targetId) {
          const newMessages = typeof updater === 'function' ? updater(conv.messages) : updater;
          return {
            ...conv,
            messages: newMessages,
            title: generateConversationTitle(newMessages),
            updatedAt: new Date(),
          };
        }
        return conv;
      });
    });
  };
  
  useEffect(() => {
    if (currentCompany?.id && conversations.length > 0) {
      localStorage.setItem(
        CONVERSATIONS_STORAGE_KEY + currentCompany.id,
        JSON.stringify(conversations)
      );
    }
  }, [conversations, currentCompany?.id]);
  
  const handleNewConversation = () => {
    const newConv = createNewConversation();
    setConversations(prev => [newConv, ...prev]);
    setActiveConversationId(newConv.id);
  };
  
  const handleDeleteConversation = (id: string) => {
    setConversations(prev => {
      const filtered = prev.filter(c => c.id !== id);
      if (filtered.length === 0) {
        const newConv = createNewConversation();
        setActiveConversationId(newConv.id);
        return [newConv];
      }
      if (id === activeConversationId) {
        setActiveConversationId(filtered[0].id);
      }
      return filtered;
    });
  };
  
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [useApiMode, setUseApiMode] = useState(true);
  
  const [mode, setMode] = useState<'advisor' | 'analyst' | 'pitch'>('advisor');
  const [challengeMode, setChallengeMode] = useState(false);
  const [investorLens, setInvestorLens] = useState<string | null>(null);
  const [createDecision, setCreateDecision] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [piiMode, setPiiMode] = useState<'off' | 'standard' | 'strict'>('standard');
  const [latestDataHealth, setLatestDataHealth] = useState<CopilotApiResponse['data_health'] | null>(null);
  const [latestPiiFindings, setLatestPiiFindings] = useState<any[] | null>(null);
  
  // Scenario Runner state
  const [scenarioAssumptions, setScenarioAssumptions] = useState<ScenarioAssumptions>({
    growthRate: 15,
    priceChange: 0,
    hiringRate: 10,
    burnReduction: 0,
  });
  const [scenarioMetrics, setScenarioMetrics] = useState({
    projectedRevenue: 120000,
    projectedCash: 450000,
    projectedRunway: 16.5,
  });
  
  // Pinned Notes state
  const [pinnedNotes, setPinnedNotes] = useState<PinnedNote[]>([]);
  const [newNoteContent, setNewNoteContent] = useState('');
  
  // Slash command autocomplete state
  const [showSlashCommands, setShowSlashCommands] = useState(false);
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0);
  
  // Collapsible panel state (ChatGPT-like design)
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [activePanelTab, setActivePanelTab] = useState<'metrics' | 'scenario' | 'notes'>('metrics');
  const [isFabOpen, setIsFabOpen] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const confidence = truthScan?.data_confidence_score || 0;
  const qualityOfGrowth = truthScan?.quality_of_growth_index || 0;
  const metrics = truthScan?.metrics || {};

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);
  
  // Scenario Runner function
  const runScenario = () => {
    const baseRevenue = metrics.mrr?.value || 100000;
    const baseCash = metrics.cash_balance?.value || 500000;
    const baseRunway = metrics.runway_months?.value || 16.5;
    
    const projectedRevenue = baseRevenue * (1 + scenarioAssumptions.growthRate / 100) * (1 + scenarioAssumptions.priceChange / 100);
    const burnSavings = (metrics.net_burn?.value || 80000) * (scenarioAssumptions.burnReduction / 100);
    const hiringCost = (scenarioAssumptions.hiringRate / 100) * 10000; // Simplified
    const projectedCash = baseCash + burnSavings * 12 - hiringCost * 12;
    const projectedRunway = baseRunway * (1 + scenarioAssumptions.burnReduction / 100 * 0.8);
    
    setScenarioMetrics({
      projectedRevenue: Math.round(projectedRevenue),
      projectedCash: Math.round(projectedCash),
      projectedRunway: Math.round(projectedRunway * 10) / 10,
    });
    
    // Send scenario to chat
    const scenarioMessage = `Run scenario with: ${scenarioAssumptions.growthRate}% growth, ${scenarioAssumptions.priceChange}% price change, ${scenarioAssumptions.hiringRate}% hiring rate, ${scenarioAssumptions.burnReduction}% burn reduction`;
    sendMessage(scenarioMessage);
  };
  
  // Pinned Notes functions
  const addNote = () => {
    if (!newNoteContent.trim()) return;
    const note: PinnedNote = {
      id: Date.now().toString(),
      content: newNoteContent.trim(),
      timestamp: new Date(),
    };
    setPinnedNotes(prev => [note, ...prev]);
    setNewNoteContent('');
  };
  
  const deleteNote = (id: string) => {
    setPinnedNotes(prev => prev.filter(note => note.id !== id));
  };
  
  // Slash command handling
  const handleInputChange = (value: string) => {
    setInput(value);
    const shouldShow = value.startsWith('/') && value.length <= 15;
    setShowSlashCommands(shouldShow);
    if (shouldShow) {
      setSelectedCommandIndex(0);
    }
  };
  
  const handleSlashCommand = (command: string) => {
    if (command === '/help') {
      setInput('');
      setShowSlashCommands(false);
      const helpMessage: Message = {
        role: 'assistant',
        content: 'Available commands:\n\n• **/run-scenario** - Run a scenario with your current assumptions\n• **/fetch-metric {name}** - Get a specific metric (mrr, arr, runway, cac, ltv)\n• **/compare** - Compare current scenario vs baseline\n• **/extend-runway** - Get strategies to extend runway\n• **/metrics** - View your key metrics\n• **/notes** - View your pinned notes\n• **/help** - Show this help message',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, helpMessage]);
    } else if (command === '/run-scenario') {
      setInput('');
      setShowSlashCommands(false);
      setActivePanelTab('scenario');
      setIsPanelOpen(true);
    } else if (command === '/metrics') {
      setInput('');
      setShowSlashCommands(false);
      setActivePanelTab('metrics');
      setIsPanelOpen(true);
    } else if (command === '/notes') {
      setInput('');
      setShowSlashCommands(false);
      setActivePanelTab('notes');
      setIsPanelOpen(true);
    } else if (command.startsWith('/fetch-metric')) {
      setInput('/fetch-metric ');
      setShowSlashCommands(false);
    } else if (command === '/compare') {
      setInput('');
      setShowSlashCommands(false);
      sendMessage('Compare current scenario vs baseline');
    } else if (command === '/extend-runway') {
      setInput('');
      setShowSlashCommands(false);
      sendMessage('How can I extend my runway by 6 months?');
    }
  };
  
  // FAB action handler
  const handleFabAction = (action: 'metrics' | 'scenario' | 'notes') => {
    setActivePanelTab(action);
    setIsPanelOpen(true);
    setIsFabOpen(false);
  };
  
  // Filter slash commands based on input
  const filteredSlashCommands = useMemo(() => {
    if (!input.startsWith('/')) return [];
    const searchTerm = input.toLowerCase();
    return SLASH_COMMANDS.filter(cmd => 
      cmd.command.toLowerCase().startsWith(searchTerm)
    );
  }, [input]);
  
  const sendMessage = async (messageText: string) => {
    if (!messageText.trim() || isTyping || !currentCompany) return;
    
    const userMessage: Message = { 
      role: 'user', 
      content: messageText,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);
    
    if (useApiMode && token) {
      try {
        const res = await apiRequest(
          'POST',
          `/api/companies/${currentCompany.id}/chat`,
          { 
            message: messageText,
            mode,
            challenge_mode: challengeMode,
            investor_lens: investorLens,
            create_decision: createDecision,
            show_sources: showSources,
            privacy: { pii_mode: piiMode }
          }
        );
        
        // Parse JSON response
        const response = await res.json() as CopilotApiResponse;
        
        const dataSources: DataSource[] = [];
        if (response.financials) dataSources.push('cfo_agent');
        if (response.market_and_customers) dataSources.push('market_agent');
        if (response.strategy_options) dataSources.push('strategy_agent');
        
        // More robust parsing with fallback handling
        let summary = 'No summary available.';
        if (response && response.executive_summary) {
          if (Array.isArray(response.executive_summary)) {
            summary = response.executive_summary.filter(s => s && typeof s === 'string').join('\n\n');
          } else if (typeof response.executive_summary === 'string') {
            summary = response.executive_summary;
          }
        }
        if (!summary || summary.trim() === '') {
          // Fallback to recommendations if available
          if (response.recommendations && Array.isArray(response.recommendations) && response.recommendations.length > 0) {
            summary = response.recommendations.map((r: any) => r.name || r.description || JSON.stringify(r)).join('\n\n');
          } else {
            summary = 'Analysis complete. See details in the structured response below.';
          }
        }
        
        const assistantMessage: Message = {
          role: 'assistant',
          content: summary || 'No summary available.',
          dataSources,
          timestamp: new Date(),
          structuredResponse: response,
        };
        setMessages((prev) => [...prev, assistantMessage]);
        
        if (response.data_health) {
          setLatestDataHealth(response.data_health);
        }
        
        if (response.pii_findings) {
          setLatestPiiFindings(response.pii_findings);
        }
      } catch (error: any) {
        console.error('Copilot API error:', error);
        // Provide more specific error message based on error type
        let errorMessage = 'Failed to get response from Copilot.';
        if (error.message) {
          if (error.message.includes('500')) {
            errorMessage = 'Server error occurred. Please try again.';
          } else if (error.message.includes('401') || error.message.includes('403')) {
            errorMessage = 'Authentication error. Please try logging in again.';
          } else if (error.message.includes('404')) {
            errorMessage = 'Service temporarily unavailable. Using fallback mode.';
          } else if (error.message.includes('Failed to fetch')) {
            errorMessage = 'Network error. Please check your connection.';
          }
        }
        toast({
          title: 'Warning',
          description: errorMessage + ' Using intelligent fallback.',
          variant: 'default',
        });
        const fallbackResponse = generateResponse(messageText, metrics, confidence);
        setMessages((prev) => [...prev, fallbackResponse]);
      }
    } else {
      setTimeout(() => {
        const response = generateResponse(messageText, metrics, confidence);
        setMessages((prev) => [...prev, response]);
      }, 1500);
    }
    setIsTyping(false);
  };

  const handleSend = () => {
    sendMessage(input);
  };
  
  const generateResponse = (query: string, metrics: any, confidence: number): Message => {
    const lowerQuery = query.toLowerCase();
    
    if (lowerQuery.includes('runway') || lowerQuery.includes('extend')) {
      return {
        role: 'assistant',
        content: `Based on your current metrics, your runway is ${metrics.runway_months?.value?.toFixed(1) || 16.5} months (P50). To extend by 6 months, I recommend:\n\n1. **Reduce burn by 15%** - This alone could add 3-4 months\n2. **Implement 10% price increase** - With your strong NRR of ${metrics.net_revenue_retention?.value || 108}%, churn risk is minimal\n3. **Defer non-critical hires** - Push Q2 hires to Q3\n\nWould you like me to run a simulation with these changes?`,
        metrics: ['runway_months', 'net_burn', 'net_revenue_retention'],
        dataSources: ['truth_scan', 'simulation'],
        suggestion: { label: 'Run burn cut scenario', action: 'burn_cut_15' },
        timestamp: new Date(),
      };
    }
    
    if (lowerQuery.includes('risk') || lowerQuery.includes('assumption')) {
      return {
        role: 'assistant',
        content: `Your riskiest assumption is **revenue concentration**. Your top 5 customers represent ${metrics.concentration_top5?.value || 32}% of revenue.\n\nIf you lose your largest customer, runway drops from ${metrics.runway_months?.value?.toFixed(1) || 16.5} to approximately 11 months.\n\nRecommendation: Prioritize customer diversification and increase logo count before your next fundraise.`,
        metrics: ['concentration_top5', 'customer_count', 'runway_months'],
        dataSources: ['truth_scan', 'benchmark'],
        timestamp: new Date(),
      };
    }
    
    if (lowerQuery.includes('fundraise') || lowerQuery.includes('slip')) {
      return {
        role: 'assistant',
        content: `If your fundraise slips 3 months:\n\n• Current runway: ${metrics.runway_months?.value?.toFixed(1) || 16.5} months\n• Survival probability at 18m: ${simulation?.survival?.['18m'] || 65}%\n• Post-slip survival: ~52%\n\nMitigation options:\n1. Secure a bridge round now ($500K-750K)\n2. Implement immediate burn reduction (15-20%)\n3. Accelerate revenue with pricing optimization\n\nThe confidence in these projections is ${confidence >= 80 ? 'high' : confidence >= 60 ? 'moderate' : 'low'} based on your data quality.`,
        metrics: ['runway_months', 'survival_18m', 'cash_balance'],
        dataSources: ['truth_scan', 'simulation', 'scenario'],
        suggestion: { label: 'Run bridge scenario', action: 'bridge_round' },
        timestamp: new Date(),
      };
    }
    
    if (lowerQuery.includes('competitor') || lowerQuery.includes('differentiate') || lowerQuery.includes('compete')) {
      return {
        role: 'assistant',
        content: `**Competitive Positioning Analysis**\n\nBased on your SaaS profile, here's how to differentiate:\n\n**Key Differentiators:**\n1. **Superior UX** - Focus on intuitive interface and faster time-to-value\n2. **Integration Ecosystem** - Build stronger API and partner integrations\n3. **Customer Success** - Invest in proactive support and onboarding\n\n**Competitive Advantages Framework:**\n• Technology: What technical capabilities set you apart?\n• Team: What unique expertise does your team bring?\n• Timing: Why is now the right time for your solution?\n\n**Recommended Actions:**\n1. Document your unique value proposition clearly\n2. Identify 3-5 direct competitors and their positioning\n3. Survey customers on why they chose you over alternatives\n\nWould you like me to help create a detailed competitive analysis?`,
        metrics: ['market_position', 'competitive_advantage'],
        dataSources: ['market_agent', 'strategy_agent'],
        timestamp: new Date(),
      };
    }
    
    return {
      role: 'assistant',
      content: `Based on your current data (confidence: ${confidence}/100):\n\n• Monthly Revenue: $${(metrics.mrr?.value || 45000).toLocaleString()}\n• Gross Margin: ${metrics.gross_margin?.value || 75}%\n• Net Burn: $${(metrics.net_burn?.value || 15000).toLocaleString()}/month\n• Runway: ${metrics.runway_months?.value?.toFixed(1) || 16.5} months\n\nWhat specific aspect would you like to explore? I can run simulations, compare scenarios, or explain any metric.`,
      metrics: ['mrr', 'gross_margin', 'net_burn', 'runway_months'],
      dataSources: ['truth_scan'],
      timestamp: new Date(),
    };
  };
  
  const handlePromptClick = (prompt: string) => {
    sendMessage(prompt);
  };
  
  if (!currentCompany) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Select a company to use Copilot</p>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  return (
    <div className="h-[calc(100vh-4rem)] flex relative overflow-hidden">
      {/* Conversation History Sidebar */}
      {showConversationSidebar && (
        <div className="w-64 border-r border-border/50 flex flex-col bg-muted/30">
          <div className="p-3 border-b border-border/50 flex items-center justify-between gap-2">
            <span className="text-sm font-medium">Conversations</span>
            <Button 
              size="sm" 
              variant="outline" 
              onClick={handleNewConversation}
              className="h-7 px-2 text-xs"
              data-testid="button-new-conversation"
            >
              <Plus className="h-3 w-3 mr-1" />
              New
            </Button>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`group flex items-center gap-2 p-2 rounded-md cursor-pointer text-sm hover-elevate ${
                    conv.id === activeConversationId 
                      ? 'bg-primary/10 text-primary' 
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                  onClick={() => setActiveConversationId(conv.id)}
                  data-testid={`conversation-${conv.id}`}
                >
                  <MessageSquare className="h-4 w-4 shrink-0" />
                  <div className="flex-1 truncate">
                    <p className="truncate text-xs font-medium">{conv.title}</p>
                    <p className="text-[10px] text-muted-foreground">
                      {new Date(conv.updatedAt).toLocaleDateString()}
                    </p>
                  </div>
                  {conversations.length > 1 && (
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteConversation(conv.id);
                      }}
                      data-testid={`delete-conversation-${conv.id}`}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}
      
      {/* Main Chat Container - Centered */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ease-in-out ${isPanelOpen ? 'lg:mr-80' : ''}`}>
        {/* Minimal Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/50">
          <div className="flex items-center gap-2">
            <Button 
              size="icon" 
              variant="ghost" 
              onClick={() => setShowConversationSidebar(!showConversationSidebar)}
              data-testid="button-toggle-sidebar"
            >
              <Menu className="h-4 w-4" />
            </Button>
            <Sparkles className="h-5 w-5 text-primary" />
            <span className="font-medium">Copilot</span>
            <Badge variant="outline" className="text-xs bg-primary/10 text-primary border-primary/30" data-testid="model-indicator">
              Multi-LLM
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              size="icon" 
              variant="ghost" 
              onClick={() => setIsPanelOpen(!isPanelOpen)}
              data-testid="button-toggle-panel"
            >
              {isPanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRight className="h-4 w-4" />}
            </Button>
          </div>
        </div>
        
        {/* Chat Messages - Centered with max width */}
        <ScrollArea className="flex-1" ref={scrollAreaRef}>
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            {messages.map((message, i) => (
              <div
                key={i}
                className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'assistant' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl p-4 ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary'
                  }`}
                  data-testid={`message-${message.role}-${i}`}
                >
                  <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                  
                  {message.dataSources && message.dataSources.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-border/30">
                      <p className="text-xs text-muted-foreground mb-2">Data sources used:</p>
                      <div className="flex flex-wrap gap-1.5">
                        {message.dataSources.map((source) => {
                          const config = DATA_SOURCE_CONFIG[source];
                          const Icon = config.icon;
                          return (
                            <Badge 
                              key={source} 
                              variant="outline" 
                              className={`text-xs ${config.className}`}
                            >
                              <Icon className="h-3 w-3 mr-1" />
                              {config.label}
                            </Badge>
                          );
                        })}
                      </div>
                    </div>
                  )}
                  
                  {message.metrics && message.metrics.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-muted-foreground mb-1.5">Referenced metrics:</p>
                      <div className="flex flex-wrap gap-1">
                        {message.metrics.map((metric) => (
                          <Badge 
                            key={metric} 
                            variant="outline" 
                            className="text-xs font-mono"
                          >
                            {metric.replace(/_/g, ' ')}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {message.structuredResponse && (
                    <StructuredResponseDisplay 
                      response={message.structuredResponse} 
                      messageIndex={i} 
                      showSources={showSources}
                      onTryPrompt={(prompt) => {
                        setInput(prompt);
                        setTimeout(() => sendMessage(prompt), 100);
                      }}
                    />
                  )}
                  
                  {message.suggestion && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="mt-3"
                      data-testid={`button-suggestion-${i}`}
                    >
                      <Play className="h-3 w-3 mr-1" />
                      {message.suggestion.label}
                    </Button>
                  )}
                  
                  {message.role === 'assistant' && i > 0 && (
                    <div className="mt-3 pt-2 border-t border-border/50">
                      <FeedbackButton testId={`feedback-${i}`} />
                    </div>
                  )}
                </div>
                {message.role === 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                    <User className="h-4 w-4 text-primary-foreground" />
                  </div>
                )}
              </div>
            ))}
            {isTyping && (
              <div className="flex gap-3 justify-start">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
                <div className="bg-secondary rounded-2xl p-4">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
        
        {/* Clean Input Area at Bottom */}
        <div className="border-t border-border/50 p-4">
          <div className="max-w-3xl mx-auto">
            {/* Quick prompts - collapsed by default, expandable */}
            {messages.length === 1 && (
              <div className="mb-4">
                <p className="text-xs text-muted-foreground mb-2">Try asking:</p>
                <div className="flex flex-wrap gap-2">
                  {SUGGESTED_PROMPTS.slice(0, 3).map((prompt, i) => (
                    <Button
                      key={i}
                      variant="outline"
                      size="sm"
                      onClick={() => handlePromptClick(prompt.label)}
                      disabled={isTyping}
                      className="text-xs"
                      data-testid={`button-prompt-${i}`}
                    >
                      <prompt.icon className="h-3 w-3 mr-1.5" />
                      <span className="truncate max-w-[180px]">{prompt.label}</span>
                    </Button>
                  ))}
                </div>
              </div>
            )}
            
            <div className="relative">
              {showSlashCommands && filteredSlashCommands.length > 0 && (
                <div className="absolute bottom-full mb-2 left-0 right-0 bg-card border border-border rounded-lg shadow-lg p-2 z-10" data-testid="slash-command-dropdown">
                  <p className="text-xs text-muted-foreground mb-2 px-2" data-testid="text-commands-header">Commands</p>
                  {filteredSlashCommands.map((cmd, idx) => (
                    <button
                      key={cmd.command}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-left transition-colors hover-elevate ${
                        idx === selectedCommandIndex ? 'bg-secondary' : ''
                      }`}
                      onClick={() => handleSlashCommand(cmd.command)}
                      onMouseEnter={() => setSelectedCommandIndex(idx)}
                      data-testid={`slash-cmd-${cmd.command.slice(1)}`}
                    >
                      <cmd.icon className="h-4 w-4 text-primary" />
                      <div>
                        <p className="text-sm font-medium" data-testid={`text-cmd-name-${cmd.command.slice(1)}`}>{cmd.command}</p>
                        <p className="text-xs text-muted-foreground" data-testid={`text-cmd-desc-${cmd.command.slice(1)}`}>{cmd.description}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <Input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => handleInputChange(e.target.value)}
                  onKeyDown={(e) => {
                    if (showSlashCommands && filteredSlashCommands.length > 0) {
                      if (e.key === 'ArrowDown') {
                        e.preventDefault();
                        setSelectedCommandIndex(prev => 
                          prev < filteredSlashCommands.length - 1 ? prev + 1 : 0
                        );
                      } else if (e.key === 'ArrowUp') {
                        e.preventDefault();
                        setSelectedCommandIndex(prev => 
                          prev > 0 ? prev - 1 : filteredSlashCommands.length - 1
                        );
                      } else if (e.key === 'Enter') {
                        e.preventDefault();
                        handleSlashCommand(filteredSlashCommands[selectedCommandIndex].command);
                      } else if (e.key === 'Escape') {
                        setShowSlashCommands(false);
                      }
                    } else if (e.key === 'Enter') {
                      handleSend();
                    }
                  }}
                  placeholder="Type / for commands or ask a question..."
                  disabled={isTyping}
                  data-testid="input-copilot"
                />
                <Button onClick={handleSend} disabled={!input.trim() || isTyping} data-testid="button-send">
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Sliding Panel - Hidden by default */}
      <div className={`fixed right-0 top-0 h-full w-80 bg-background border-l border-border shadow-xl transform transition-transform duration-300 ease-in-out z-40 ${isPanelOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex gap-2">
            <Button 
              size="sm" 
              variant={activePanelTab === 'metrics' ? 'secondary' : 'ghost'}
              onClick={() => setActivePanelTab('metrics')}
              data-testid="button-tab-metrics"
            >
              <BarChart3 className="h-4 w-4" />
            </Button>
            <Button 
              size="sm" 
              variant={activePanelTab === 'scenario' ? 'secondary' : 'ghost'}
              onClick={() => setActivePanelTab('scenario')}
              data-testid="button-tab-scenario"
            >
              <Sliders className="h-4 w-4" />
            </Button>
            <Button 
              size="sm" 
              variant={activePanelTab === 'notes' ? 'secondary' : 'ghost'}
              onClick={() => setActivePanelTab('notes')}
              data-testid="button-tab-notes"
            >
              <StickyNote className="h-4 w-4" />
            </Button>
          </div>
          <Button size="icon" variant="ghost" onClick={() => setIsPanelOpen(false)} data-testid="button-close-panel">
            <X className="h-4 w-4" />
          </Button>
        </div>
        
        <ScrollArea className="h-[calc(100%-4rem)] p-4">
          {/* Metrics Tab */}
          {activePanelTab === 'metrics' && (
            truthLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : (
              <div className="space-y-4">
                <Card className="overflow-visible">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Database className="h-4 w-4 text-emerald-400" />
                      Data Confidence
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold font-mono" data-testid="text-context-confidence">
                      {confidence}/100
                    </div>
                    <Badge
                      variant={confidence < 60 ? 'destructive' : 'secondary'}
                      className={confidence >= 80 ? 'bg-emerald-500/20 text-emerald-400' : confidence >= 60 ? 'bg-amber-500/20 text-amber-400' : ''}
                    >
                      {confidence < 60 ? 'Low' : confidence < 80 ? 'Medium' : 'High'}
                    </Badge>
                  </CardContent>
                </Card>
                
                <Card className="overflow-visible">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-amber-400" />
                      Quality of Growth
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold font-mono" data-testid="text-context-qog">
                      {qualityOfGrowth}/100
                    </div>
                  </CardContent>
                </Card>
                
                <Card className="overflow-visible">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Target className="h-4 w-4 text-purple-400" />
                      Current Scenario
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">
                    {latestScenario ? (
                      <>
                        <p className="font-medium text-foreground">{latestScenario.name}</p>
                        <p>Pricing: {latestScenario.pricing_change_pct > 0 ? '+' : ''}{latestScenario.pricing_change_pct}%</p>
                        <p>Burn cut: {latestScenario.burn_reduction_pct}%</p>
                      </>
                    ) : (
                      <p>No scenario selected</p>
                    )}
                  </CardContent>
                </Card>
                
                <Card className="overflow-visible">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-blue-400" />
                      Latest Simulation
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm">
                    {simulation ? (
                      <>
                        <p>Runway P50: <span className="font-mono font-medium">{simulation.runway?.p50?.toFixed(1)} mo</span></p>
                        <p>Survival 18m: <span className="font-mono font-medium">{simulation.survival?.['18m']}%</span></p>
                      </>
                    ) : (
                      <p className="text-muted-foreground">No simulation run yet</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            )
          )}
          
          {/* Scenario Tab */}
          {activePanelTab === 'scenario' && (
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span>Growth Rate</span>
                  <span className="font-mono">{scenarioAssumptions.growthRate}%</span>
                </div>
                <Slider
                  value={[scenarioAssumptions.growthRate]}
                  onValueChange={([v]) => setScenarioAssumptions(prev => ({ ...prev, growthRate: v }))}
                  min={-20}
                  max={50}
                  step={1}
                  data-testid="slider-growth-rate"
                />
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span>Price Change</span>
                  <span className="font-mono">{scenarioAssumptions.priceChange}%</span>
                </div>
                <Slider
                  value={[scenarioAssumptions.priceChange]}
                  onValueChange={([v]) => setScenarioAssumptions(prev => ({ ...prev, priceChange: v }))}
                  min={-20}
                  max={30}
                  step={1}
                  data-testid="slider-price-change"
                />
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span>Hiring Rate</span>
                  <span className="font-mono">{scenarioAssumptions.hiringRate}%</span>
                </div>
                <Slider
                  value={[scenarioAssumptions.hiringRate]}
                  onValueChange={([v]) => setScenarioAssumptions(prev => ({ ...prev, hiringRate: v }))}
                  min={0}
                  max={30}
                  step={1}
                  data-testid="slider-hiring-rate"
                />
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span>Burn Reduction</span>
                  <span className="font-mono">{scenarioAssumptions.burnReduction}%</span>
                </div>
                <Slider
                  value={[scenarioAssumptions.burnReduction]}
                  onValueChange={([v]) => setScenarioAssumptions(prev => ({ ...prev, burnReduction: v }))}
                  min={0}
                  max={40}
                  step={1}
                  data-testid="slider-burn-reduction"
                />
              </div>
              
              <Separator />
              
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2 rounded bg-secondary">
                  <p className="text-xs text-muted-foreground">Revenue</p>
                  <p className="text-sm font-mono font-medium">${(scenarioMetrics.projectedRevenue / 1000).toFixed(0)}K</p>
                </div>
                <div className="p-2 rounded bg-secondary">
                  <p className="text-xs text-muted-foreground">Cash</p>
                  <p className="text-sm font-mono font-medium">${(scenarioMetrics.projectedCash / 1000).toFixed(0)}K</p>
                </div>
                <div className="p-2 rounded bg-secondary">
                  <p className="text-xs text-muted-foreground">Runway</p>
                  <p className="text-sm font-mono font-medium">{scenarioMetrics.projectedRunway}mo</p>
                </div>
              </div>
              
              <Button 
                className="w-full" 
                onClick={runScenario}
                disabled={isTyping}
                data-testid="button-run-scenario"
              >
                <Play className="h-4 w-4 mr-2" />
                Run Scenario
              </Button>
            </div>
          )}
          
          {/* Notes Tab */}
          {activePanelTab === 'notes' && (
            <div className="space-y-4">
              <div className="flex gap-2">
                <Input
                  value={newNoteContent}
                  onChange={(e) => setNewNoteContent(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addNote()}
                  placeholder="Add a note..."
                  data-testid="input-new-note"
                />
                <Button 
                  size="icon" 
                  variant="outline" 
                  onClick={addNote}
                  disabled={!newNoteContent.trim()}
                  data-testid="button-add-note"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              
              {pinnedNotes.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No notes yet. Add one above.</p>
              ) : (
                <div className="space-y-2">
                  {pinnedNotes.map((note) => (
                    <div 
                      key={note.id} 
                      className="p-3 rounded-lg bg-secondary/50 border border-border/30 group"
                      data-testid={`note-${note.id}`}
                    >
                      <div className="flex justify-between items-start gap-2">
                        <p className="text-sm flex-1">{note.content}</p>
                        <button
                          onClick={() => deleteNote(note.id)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity"
                          data-testid={`button-delete-note-${note.id}`}
                        >
                          <X className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                        </button>
                      </div>
                      <p className="text-xs text-muted-foreground mt-2">
                        {note.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </ScrollArea>
      </div>
      
      {/* Floating Action Button */}
      <div className={`fixed bottom-6 right-6 z-30 transition-all duration-300 ${isPanelOpen ? 'lg:right-[22rem]' : ''}`}>
        <div className="relative">
          {isFabOpen && (
            <div className="absolute bottom-16 right-0 bg-card border border-border rounded-lg shadow-xl p-2 w-48" data-testid="fab-menu">
              <button
                className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover-elevate text-left"
                onClick={() => handleFabAction('metrics')}
                data-testid="fab-action-metrics"
              >
                <BarChart3 className="h-4 w-4 text-emerald-400" />
                <span className="text-sm">View Metrics</span>
              </button>
              <button
                className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover-elevate text-left"
                onClick={() => handleFabAction('scenario')}
                data-testid="fab-action-scenario"
              >
                <Sliders className="h-4 w-4 text-cyan-400" />
                <span className="text-sm">Run Scenario</span>
              </button>
              <button
                className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover-elevate text-left"
                onClick={() => handleFabAction('notes')}
                data-testid="fab-action-notes"
              >
                <StickyNote className="h-4 w-4 text-amber-400" />
                <span className="text-sm">Add Note</span>
              </button>
            </div>
          )}
          <Button
            size="icon"
            className="h-14 w-14 rounded-full shadow-lg"
            onClick={() => setIsFabOpen(!isFabOpen)}
            data-testid="button-fab"
          >
            {isFabOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
