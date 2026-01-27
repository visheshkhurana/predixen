import { useEffect, useState, useMemo, useCallback } from 'react';
import { useLocation } from 'wouter';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { MetricCard } from '@/components/MetricCard';
import { DecisionCard, DecisionStatus } from '@/components/DecisionCard';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import {
  AlertTriangle,
  TrendingUp,
  ArrowRight,
  RefreshCw,
  Sparkles,
  Send,
  Info,
  HelpCircle,
  SlidersHorizontal,
  Save,
  Download,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Target,
  Users,
  DollarSign,
  Percent,
  Calendar,
  MessageSquare,
} from 'lucide-react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts';
import { useFounderStore } from '@/store/founderStore';
import { useTruthScan, useDecisions, useRunTruthScan } from '@/api/hooks';
import { formatCurrencyAbbrev, formatPercent as formatPct } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

const DECISION_STATUSES_KEY = 'decision_statuses_';
const SCENARIOS_STORAGE_KEY = 'overview_scenarios_';
const COMMENTS_STORAGE_KEY = 'overview_comments_';

interface ScenarioAssumptions {
  growthRate: number;
  pricingChange: number;
  hiringRate: number;
  churnRate: number;
  cacReduction: number;
}

interface SavedScenario {
  id: string;
  name: string;
  assumptions: ScenarioAssumptions;
  createdAt: string;
}

interface Comment {
  id: string;
  text: string;
  createdAt: string;
  scenarioName?: string;
}

const DEFAULT_ASSUMPTIONS: ScenarioAssumptions = {
  growthRate: 10,
  pricingChange: 0,
  hiringRate: 5,
  churnRate: 5,
  cacReduction: 0,
};

const DUMMY_BASE_DATA = {
  mrr: 10000,
  arr: 120000,
  cash: 500000,
  burnRate: 50000,
  cac: 500,
  ltv: 3000,
  grossMargin: 70,
  paybackPeriod: 10,
  totalCustomers: 200,
  churnRate: 5,
  conversionRate: 3.5,
  profitabilityDate: 'Dec 2026',
};

const METRIC_TOOLTIPS = {
  runway: {
    title: "Runway (P50)",
    calculation: "Cash Balance / Monthly Net Burn, simulated across 1000 scenarios",
    goodRange: "12+ months is healthy, 18+ months is ideal for fundraising",
    badRange: "Less than 6 months is critical, 6-12 months requires attention",
    dataSource: "Cash balance and expenses from Data Input",
  },
  netBurn: {
    title: "Net Burn",
    calculation: "Total Monthly Expenses - Monthly Revenue",
    goodRange: "Lower burn is better; negative burn means profitable",
    badRange: "High burn relative to cash reduces runway",
    dataSource: "Revenue and expense data from Data Input",
  },
  revenueGrowth: {
    title: "Revenue Growth",
    calculation: "(Current Month Revenue - Previous Month) / Previous Month",
    goodRange: "10%+ MoM for early-stage, 5-10% for growth stage",
    badRange: "Negative or flat growth may signal product-market fit issues",
    dataSource: "Monthly revenue from financial records",
  },
  grossMargin: {
    title: "Gross Margin",
    calculation: "(Revenue - COGS) / Revenue",
    goodRange: "70%+ for SaaS, 50%+ for most tech companies",
    badRange: "Below 50% may indicate pricing or cost issues",
    dataSource: "Revenue and COGS from Data Input",
  },
  burnMultiple: {
    title: "Burn Multiple",
    calculation: "Net Burn / Net New ARR",
    goodRange: "Below 1.5x is excellent, 1.5-2x is good",
    badRange: "Above 3x indicates inefficient growth",
    dataSource: "Burn rate and revenue growth from financial data",
  },
  concentration: {
    title: "Top 5 Customer Concentration",
    calculation: "Revenue from Top 5 Customers / Total Revenue",
    goodRange: "Below 25% is healthy diversification",
    badRange: "Above 50% creates significant revenue risk",
    dataSource: "Customer revenue data from CRM or manual entry",
  },
};

const getConfidenceExplanation = (score: number, metrics: any) => {
  const factors: { label: string; status: 'good' | 'warning' | 'missing' }[] = [];
  
  if (metrics.revenue_growth_mom != null) {
    factors.push({ label: "Revenue data", status: 'good' });
  } else {
    factors.push({ label: "Revenue data", status: 'missing' });
  }
  
  if (metrics.net_burn != null) {
    factors.push({ label: "Expense data", status: 'good' });
  } else {
    factors.push({ label: "Expense data", status: 'missing' });
  }
  
  if (metrics.gross_margin != null) {
    factors.push({ label: "COGS/Margin data", status: 'good' });
  } else {
    factors.push({ label: "COGS/Margin data", status: 'warning' });
  }
  
  if (metrics.concentration_top5 != null) {
    factors.push({ label: "Customer data", status: 'good' });
  } else {
    factors.push({ label: "Customer data", status: 'warning' });
  }
  
  return factors;
};

const getQoGExplanation = (score: number) => {
  const components = [
    { name: "Revenue Growth Efficiency", weight: "25%", description: "Growth rate relative to burn" },
    { name: "Gross Margin Health", weight: "20%", description: "Profitability of core business" },
    { name: "Burn Efficiency", weight: "20%", description: "Cash efficiency in acquiring growth" },
    { name: "Customer Concentration", weight: "15%", description: "Revenue diversification" },
    { name: "Runway Safety", weight: "20%", description: "Time to sustain operations" },
  ];
  return components;
};

const COPILOT_PROMPTS = [
  "How do I extend runway by 6 months?",
  "What's the riskiest assumption?",
  "What if fundraise slips 3 months?",
];

const getKpiStatus = (value: number | null, metric: string): 'green' | 'yellow' | 'red' => {
  if (value === null || value === undefined) return 'red';
  
  switch (metric) {
    case 'runway':
      if (value >= 18) return 'green';
      if (value >= 12) return 'yellow';
      return 'red';
    case 'grossMargin':
      if (value >= 70) return 'green';
      if (value >= 50) return 'yellow';
      return 'red';
    case 'churnRate':
      if (value <= 3) return 'green';
      if (value <= 7) return 'yellow';
      return 'red';
    case 'ltv_cac':
      if (value >= 3) return 'green';
      if (value >= 2) return 'yellow';
      return 'red';
    case 'growthRate':
      if (value >= 15) return 'green';
      if (value >= 5) return 'yellow';
      return 'red';
    case 'paybackPeriod':
      if (value <= 12) return 'green';
      if (value <= 18) return 'yellow';
      return 'red';
    default:
      return 'yellow';
  }
};

const KpiStatusIcon = ({ status }: { status: 'green' | 'yellow' | 'red' }) => {
  switch (status) {
    case 'green':
      return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
    case 'yellow':
      return <AlertCircle className="h-4 w-4 text-amber-500" />;
    case 'red':
      return <XCircle className="h-4 w-4 text-red-500" />;
  }
};

export default function OverviewPage() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const { currentCompany, setTruthScan, setCurrentStep } = useFounderStore();
  const { data: truthScan, isLoading: truthLoading, error: truthError } = useTruthScan(currentCompany?.id || null);
  const { data: decisions, isLoading: decisionsLoading } = useDecisions(currentCompany?.id || null);
  const runTruthScanMutation = useRunTruthScan();
  const [decisionStatuses, setDecisionStatuses] = useState<Record<string, DecisionStatus>>({});
  
  const [assumptions, setAssumptions] = useState<ScenarioAssumptions>(DEFAULT_ASSUMPTIONS);
  const [savedScenarios, setSavedScenarios] = useState<SavedScenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('');
  const [newScenarioName, setNewScenarioName] = useState('');
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [assumptionsPanelOpen, setAssumptionsPanelOpen] = useState(false);

  useEffect(() => {
    if (currentCompany?.id) {
      try {
        const stored = localStorage.getItem(`${DECISION_STATUSES_KEY}${currentCompany.id}`);
        if (stored) {
          setDecisionStatuses(JSON.parse(stored));
        }
        const storedScenarios = localStorage.getItem(`${SCENARIOS_STORAGE_KEY}${currentCompany.id}`);
        if (storedScenarios) {
          setSavedScenarios(JSON.parse(storedScenarios));
        }
        const storedComments = localStorage.getItem(`${COMMENTS_STORAGE_KEY}${currentCompany.id}`);
        if (storedComments) {
          setComments(JSON.parse(storedComments));
        }
      } catch (e) {
        console.warn('Failed to load stored data');
      }
    }
  }, [currentCompany?.id]);
  
  useEffect(() => {
    if (truthScan) {
      setTruthScan(truthScan);
    }
  }, [truthScan, setTruthScan]);

  const projectedMetrics = useMemo(() => {
    const baseData = DUMMY_BASE_DATA;
    const months = 12;
    
    const growthMultiplier = 1 + assumptions.growthRate / 100;
    const pricingMultiplier = 1 + assumptions.pricingChange / 100;
    const adjustedChurn = baseData.churnRate * (1 - assumptions.cacReduction / 100) + assumptions.churnRate / 10;
    
    const projectedMrr = baseData.mrr * Math.pow(growthMultiplier, months) * pricingMultiplier;
    const projectedArr = projectedMrr * 12;
    
    const burnIncrease = 1 + (assumptions.hiringRate / 100) * 0.8;
    const projectedBurn = baseData.burnRate * burnIncrease;
    
    const projectedCash = baseData.cash - (projectedBurn * months * 0.5);
    const runway = projectedCash > 0 ? projectedCash / projectedBurn : 0;
    
    const adjustedCac = baseData.cac * (1 - assumptions.cacReduction / 100);
    const adjustedLtv = baseData.ltv * pricingMultiplier * (1 - adjustedChurn / 100);
    const ltvCacRatio = adjustedLtv / adjustedCac;
    const paybackPeriod = adjustedCac / (projectedMrr / baseData.totalCustomers);
    
    const projectedCustomers = Math.round(baseData.totalCustomers * growthMultiplier);
    
    return {
      mrr: projectedMrr,
      arr: projectedArr,
      cash: projectedCash,
      burnRate: projectedBurn,
      runway,
      cac: adjustedCac,
      ltv: adjustedLtv,
      ltvCacRatio,
      paybackPeriod,
      totalCustomers: projectedCustomers,
      churnRate: adjustedChurn,
      grossMargin: baseData.grossMargin + assumptions.pricingChange * 0.5,
    };
  }, [assumptions]);

  const chartData = useMemo(() => {
    const data = [];
    let currentMrr = DUMMY_BASE_DATA.mrr;
    const growthRate = assumptions.growthRate / 100;
    
    for (let month = 0; month <= 12; month++) {
      const monthName = new Date(2026, month, 1).toLocaleDateString('en-US', { month: 'short' });
      data.push({
        month: monthName,
        revenue: Math.round(currentMrr),
        projected: month > 0 ? Math.round(currentMrr) : null,
        baseline: DUMMY_BASE_DATA.mrr * Math.pow(1.05, month),
      });
      currentMrr *= (1 + growthRate / 12);
    }
    return data;
  }, [assumptions.growthRate]);

  const saveScenario = useCallback(() => {
    if (!newScenarioName.trim() || !currentCompany?.id) return;
    
    const scenario: SavedScenario = {
      id: Date.now().toString(),
      name: newScenarioName.trim(),
      assumptions: { ...assumptions },
      createdAt: new Date().toISOString(),
    };
    
    const updated = [...savedScenarios, scenario];
    setSavedScenarios(updated);
    setNewScenarioName('');
    setSelectedScenarioId(scenario.id);
    
    try {
      localStorage.setItem(`${SCENARIOS_STORAGE_KEY}${currentCompany.id}`, JSON.stringify(updated));
    } catch (e) {
      console.warn('Failed to save scenario');
    }
    
    toast({
      title: 'Scenario Saved',
      description: `"${scenario.name}" has been saved successfully.`,
    });
  }, [newScenarioName, assumptions, savedScenarios, currentCompany?.id, toast]);

  const loadScenario = useCallback((scenarioId: string) => {
    const scenario = savedScenarios.find(s => s.id === scenarioId);
    if (scenario) {
      setAssumptions(scenario.assumptions);
      setSelectedScenarioId(scenarioId);
      toast({
        title: 'Scenario Loaded',
        description: `Loaded "${scenario.name}"`,
      });
    }
  }, [savedScenarios, toast]);

  const addComment = useCallback(() => {
    if (!newComment.trim() || !currentCompany?.id) return;
    
    const currentScenario = savedScenarios.find(s => s.id === selectedScenarioId);
    const comment: Comment = {
      id: Date.now().toString(),
      text: newComment.trim(),
      createdAt: new Date().toISOString(),
      scenarioName: currentScenario?.name,
    };
    
    const updated = [comment, ...comments];
    setComments(updated);
    setNewComment('');
    
    try {
      localStorage.setItem(`${COMMENTS_STORAGE_KEY}${currentCompany.id}`, JSON.stringify(updated));
    } catch (e) {
      console.warn('Failed to save comment');
    }
  }, [newComment, currentCompany?.id, selectedScenarioId, savedScenarios, comments]);

  const handleAdoptPlan = (recId: string, recTitle: string) => {
    if (!currentCompany?.id) return;
    
    const updated = { ...decisionStatuses, [recId]: 'adopted' as DecisionStatus };
    setDecisionStatuses(updated);
    
    try {
      localStorage.setItem(`${DECISION_STATUSES_KEY}${currentCompany.id}`, JSON.stringify(updated));
    } catch (e) {
      console.warn('Failed to save decision status');
    }
    
    toast({
      title: 'Plan Adopted',
      description: `"${recTitle}" has been marked as adopted. View in Decisions page.`,
    });
  };

  const handleRunScenario = (recTitle: string) => {
    setCurrentStep('simulation');
    toast({
      title: 'Opening Scenario Builder',
      description: `Create a scenario based on "${recTitle}"`,
    });
    setLocation('/scenarios');
  };

  const handleStatusChange = (recId: string, status: DecisionStatus) => {
    if (!currentCompany?.id) return;
    
    const updated = { ...decisionStatuses, [recId]: status };
    setDecisionStatuses(updated);
    
    try {
      localStorage.setItem(`${DECISION_STATUSES_KEY}${currentCompany.id}`, JSON.stringify(updated));
    } catch (e) {
      console.warn('Failed to save decision status');
    }
    
    toast({
      title: 'Status Updated',
      description: `Decision marked as ${status}`,
    });
  };
  
  if (!currentCompany) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <Card>
          <CardContent className="py-12 text-center">
            <h2 className="text-xl font-semibold mb-2">No Company Selected</h2>
            <p className="text-muted-foreground mb-4">Create a company to get started</p>
            <Button onClick={() => setLocation('/onboarding')} data-testid="button-create-company">
              Get Started
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  const metrics = truthScan?.metrics || {};
  const flags = truthScan?.flags || [];
  const confidence = truthScan?.data_confidence_score || 0;
  const qualityOfGrowth = truthScan?.quality_of_growth_index || 0;
  
  const formatCurrency = (value: number | null | undefined) => {
    return formatCurrencyAbbrev(value, currentCompany?.currency || 'USD');
  };
  
  const formatPercent = (value: number | null | undefined) => {
    return formatPct(value);
  };
  
  const safeToFixed = (value: any, digits: number = 1): string => {
    if (value == null || typeof value !== 'number' || isNaN(value)) return 'N/A';
    return value.toFixed(digits);
  };
  
  const getConfidenceBadge = () => {
    if (confidence < 60) {
      return (
        <Badge variant="destructive" data-testid="badge-confidence">
          <XCircle className="h-3 w-3 mr-1" />
          Low Confidence ({confidence})
        </Badge>
      );
    } else if (confidence < 80) {
      return (
        <Badge variant="secondary" data-testid="badge-confidence">
          <AlertCircle className="h-3 w-3 mr-1 text-amber-500" />
          Medium Confidence ({confidence})
        </Badge>
      );
    }
    return (
      <Badge variant="secondary" data-testid="badge-confidence">
        <CheckCircle2 className="h-3 w-3 mr-1 text-emerald-500" />
        High Confidence ({confidence})
      </Badge>
    );
  };
  
  const handleRefreshScan = async () => {
    if (!currentCompany) return;
    await runTruthScanMutation.mutateAsync(currentCompany.id);
  };

  const kpiHealthData = [
    { name: 'Runway', value: projectedMetrics.runway, metric: 'runway' },
    { name: 'Gross Margin', value: projectedMetrics.grossMargin, metric: 'grossMargin' },
    { name: 'Churn Rate', value: projectedMetrics.churnRate, metric: 'churnRate' },
    { name: 'LTV/CAC', value: projectedMetrics.ltvCacRatio, metric: 'ltv_cac' },
    { name: 'Growth Rate', value: assumptions.growthRate, metric: 'growthRate' },
    { name: 'Payback', value: projectedMetrics.paybackPeriod, metric: 'paybackPeriod' },
  ];
  
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold" data-testid="text-company-name">{currentCompany.name}</h1>
          <p className="text-muted-foreground">Financial Intelligence Overview</p>
        </div>
        <div className="flex items-center gap-2">
          {getConfidenceBadge()}
          <Sheet open={assumptionsPanelOpen} onOpenChange={setAssumptionsPanelOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" size="sm" data-testid="button-open-assumptions">
                <SlidersHorizontal className="h-4 w-4 mr-1" />
                Assumptions
              </Button>
            </SheetTrigger>
            <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
              <SheetHeader>
                <SheetTitle>Scenario Assumptions</SheetTitle>
                <SheetDescription>
                  Adjust key parameters to see how they affect your projections in real-time.
                </SheetDescription>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="growth-rate">Monthly Growth Rate</Label>
                      <span className="text-sm font-mono text-muted-foreground">{assumptions.growthRate}%</span>
                    </div>
                    <Slider
                      id="growth-rate"
                      value={[assumptions.growthRate]}
                      onValueChange={(v) => setAssumptions(prev => ({ ...prev, growthRate: v[0] }))}
                      min={-10}
                      max={50}
                      step={1}
                      data-testid="slider-growth-rate"
                    />
                    <p className="text-xs text-muted-foreground">Expected MoM revenue growth percentage</p>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="pricing-change">Pricing Change</Label>
                      <span className="text-sm font-mono text-muted-foreground">{assumptions.pricingChange}%</span>
                    </div>
                    <Slider
                      id="pricing-change"
                      value={[assumptions.pricingChange]}
                      onValueChange={(v) => setAssumptions(prev => ({ ...prev, pricingChange: v[0] }))}
                      min={-30}
                      max={50}
                      step={1}
                      data-testid="slider-pricing-change"
                    />
                    <p className="text-xs text-muted-foreground">Percentage change to current pricing</p>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="hiring-rate">Hiring Rate</Label>
                      <span className="text-sm font-mono text-muted-foreground">{assumptions.hiringRate}%</span>
                    </div>
                    <Slider
                      id="hiring-rate"
                      value={[assumptions.hiringRate]}
                      onValueChange={(v) => setAssumptions(prev => ({ ...prev, hiringRate: v[0] }))}
                      min={0}
                      max={50}
                      step={1}
                      data-testid="slider-hiring-rate"
                    />
                    <p className="text-xs text-muted-foreground">Annual team growth rate (impacts burn)</p>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="churn-rate">Churn Adjustment</Label>
                      <span className="text-sm font-mono text-muted-foreground">{assumptions.churnRate}%</span>
                    </div>
                    <Slider
                      id="churn-rate"
                      value={[assumptions.churnRate]}
                      onValueChange={(v) => setAssumptions(prev => ({ ...prev, churnRate: v[0] }))}
                      min={0}
                      max={20}
                      step={0.5}
                      data-testid="slider-churn-rate"
                    />
                    <p className="text-xs text-muted-foreground">Expected monthly customer churn</p>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="cac-reduction">CAC Reduction</Label>
                      <span className="text-sm font-mono text-muted-foreground">{assumptions.cacReduction}%</span>
                    </div>
                    <Slider
                      id="cac-reduction"
                      value={[assumptions.cacReduction]}
                      onValueChange={(v) => setAssumptions(prev => ({ ...prev, cacReduction: v[0] }))}
                      min={0}
                      max={50}
                      step={1}
                      data-testid="slider-cac-reduction"
                    />
                    <p className="text-xs text-muted-foreground">Marketing efficiency improvement</p>
                  </div>
                </div>
                
                <Separator />
                
                <div className="space-y-4">
                  <h4 className="font-medium">Scenario Management</h4>
                  
                  <div className="flex gap-2">
                    <Input
                      placeholder="Scenario name..."
                      value={newScenarioName}
                      onChange={(e) => setNewScenarioName(e.target.value)}
                      className="flex-1"
                      data-testid="input-scenario-name"
                    />
                    <Button onClick={saveScenario} disabled={!newScenarioName.trim()} data-testid="button-save-scenario">
                      <Save className="h-4 w-4 mr-1" />
                      Save
                    </Button>
                  </div>
                  
                  {savedScenarios.length > 0 && (
                    <Select value={selectedScenarioId} onValueChange={loadScenario}>
                      <SelectTrigger data-testid="select-load-scenario">
                        <SelectValue placeholder="Load a saved scenario..." />
                      </SelectTrigger>
                      <SelectContent>
                        {savedScenarios.map((s, index) => (
                          <SelectItem key={s.id} value={s.id} data-testid={`select-item-scenario-${index}`}>
                            {s.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setAssumptions(DEFAULT_ASSUMPTIONS)}
                    className="w-full"
                    data-testid="button-reset-assumptions"
                  >
                    Reset to Defaults
                  </Button>
                </div>
              </div>
            </SheetContent>
          </Sheet>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefreshScan}
            disabled={runTruthScanMutation.isPending}
            data-testid="button-refresh-scan"
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${runTruthScanMutation.isPending ? 'animate-spin' : ''}`} />
            Refresh Scan
          </Button>
        </div>
      </div>
      
      {flags.filter((f: any) => f.severity === 'high').length > 0 && (
        <Card className="border-destructive/50 bg-destructive/10">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-destructive mt-0.5" />
              <div>
                <h3 className="font-medium text-destructive">Critical Issues Detected</h3>
                <ul className="mt-1 text-sm text-muted-foreground space-y-1">
                  {flags.filter((f: any) => f.severity === 'high').map((flag: any, i: number) => (
                    <li key={i}>{flag.title}: {flag.description}</li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <MetricCard
          title="MRR"
          value={formatCurrency(projectedMetrics.mrr)}
          subtitle="Monthly Recurring Revenue"
          trend="up"
          trendValue={`+${assumptions.growthRate}%`}
          testId="metric-mrr"
        />
        <MetricCard
          title="ARR"
          value={formatCurrency(projectedMetrics.arr)}
          subtitle="Annual Recurring Revenue"
          trend="up"
          testId="metric-arr"
        />
        <MetricCard
          title="Cash on Hand"
          value={formatCurrency(projectedMetrics.cash)}
          subtitle={`Runway: ${safeToFixed(projectedMetrics.runway)} mo`}
          variant={projectedMetrics.runway < 6 ? 'danger' : projectedMetrics.runway < 12 ? 'warning' : 'success'}
          testId="metric-cash"
        />
        <MetricCard
          title="Burn Rate"
          value={formatCurrency(projectedMetrics.burnRate)}
          subtitle="/month"
          testId="metric-burn-rate"
        />
        <MetricCard
          title="CAC"
          value={formatCurrency(projectedMetrics.cac)}
          subtitle="Cost to Acquire"
          testId="metric-cac"
        />
        <MetricCard
          title="LTV"
          value={formatCurrency(projectedMetrics.ltv)}
          subtitle={`LTV:CAC = ${safeToFixed(projectedMetrics.ltvCacRatio)}x`}
          variant={projectedMetrics.ltvCacRatio < 3 ? 'warning' : 'success'}
          testId="metric-ltv"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 overflow-visible">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Revenue Projection</CardTitle>
            <CardDescription>12-month forecast based on current assumptions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]" data-testid="chart-revenue-projection">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} className="text-muted-foreground" />
                  <YAxis
                    tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`}
                    tick={{ fontSize: 12 }}
                    className="text-muted-foreground"
                  />
                  <RechartsTooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--popover))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                    }}
                    formatter={(value: number) => [`$${value.toLocaleString()}`, 'Revenue']}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="hsl(var(--primary))"
                    fillOpacity={1}
                    fill="url(#colorRevenue)"
                    strokeWidth={2}
                    name="Projected Revenue"
                  />
                  <Line
                    type="monotone"
                    dataKey="baseline"
                    stroke="hsl(var(--muted-foreground))"
                    strokeDasharray="5 5"
                    dot={false}
                    name="Baseline (5% growth)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card className="overflow-visible">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              KPI Health
              <HoverCard>
                <HoverCardTrigger asChild>
                  <Button variant="ghost" size="icon" data-testid="button-kpi-health-info">
                    <HelpCircle className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </HoverCardTrigger>
                <HoverCardContent className="w-64" side="bottom">
                  <div className="space-y-2">
                    <h4 className="font-semibold">KPI Status Legend</h4>
                    <div className="space-y-1 text-sm">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                        <span>On Target</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-amber-500" />
                        <span>Needs Attention</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <XCircle className="h-4 w-4 text-red-500" />
                        <span>Critical</span>
                      </div>
                    </div>
                  </div>
                </HoverCardContent>
              </HoverCard>
            </CardTitle>
            <CardDescription>Real-time status of key metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3" data-testid="kpi-health-grid">
              {kpiHealthData.map((kpi) => {
                const status = getKpiStatus(kpi.value, kpi.metric);
                return (
                  <Card
                    key={kpi.metric}
                    className="overflow-visible"
                    data-testid={`kpi-${kpi.metric}`}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-xs font-medium text-muted-foreground truncate">{kpi.name}</span>
                        <Badge variant="secondary" data-testid={`kpi-${kpi.metric}-status`}>
                          <KpiStatusIcon status={status} />
                        </Badge>
                      </div>
                      <p className="text-sm font-semibold mt-1 font-mono" data-testid={`kpi-${kpi.metric}-value`}>
                        {kpi.metric === 'runway' || kpi.metric === 'paybackPeriod'
                          ? `${safeToFixed(kpi.value)} mo`
                          : kpi.metric === 'ltv_cac'
                          ? `${safeToFixed(kpi.value)}x`
                          : `${safeToFixed(kpi.value)}%`}
                      </p>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="overflow-visible">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              Quality of Growth Index
              <HoverCard>
                <HoverCardTrigger asChild>
                  <Button variant="ghost" size="icon" data-testid="button-qog-info">
                    <HelpCircle className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </HoverCardTrigger>
                <HoverCardContent className="w-80" side="bottom">
                  <div className="space-y-3">
                    <h4 className="font-semibold">How QoG is Calculated</h4>
                    <p className="text-sm text-muted-foreground">
                      A weighted composite score measuring growth quality:
                    </p>
                    <div className="space-y-2">
                      {getQoGExplanation(qualityOfGrowth).map((comp, i) => (
                        <div key={i} className="flex justify-between text-sm">
                          <span>{comp.name}</span>
                          <span className="text-muted-foreground">{comp.weight}</span>
                        </div>
                      ))}
                    </div>
                    <div className="pt-2 border-t text-sm">
                      <p><span className="text-emerald-500">80+:</span> Excellent growth quality</p>
                      <p><span className="text-amber-500">50-79:</span> Moderate, room for improvement</p>
                      <p><span className="text-red-500">&lt;50:</span> Needs attention</p>
                    </div>
                  </div>
                </HoverCardContent>
              </HoverCard>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {truthLoading ? (
              <Skeleton className="h-16 w-24" />
            ) : (
              <div className="text-4xl font-bold font-mono" data-testid="text-quality-index">
                {qualityOfGrowth}
                <span className="text-lg text-muted-foreground">/100</span>
              </div>
            )}
            <p className="text-sm text-muted-foreground mt-1">
              Composite score based on growth, efficiency, and risk factors
            </p>
          </CardContent>
        </Card>
        
        <Card className="overflow-visible">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              Milestones
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Projected Profitability</span>
              </div>
              <Badge variant="secondary">{DUMMY_BASE_DATA.profitabilityDate}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Total Customers</span>
              </div>
              <span className="font-mono font-medium">{projectedMetrics.totalCustomers}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Percent className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Conversion Rate</span>
              </div>
              <span className="font-mono font-medium">{DUMMY_BASE_DATA.conversionRate}%</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Gross Margin</span>
              </div>
              <span className="font-mono font-medium">{safeToFixed(projectedMetrics.grossMargin)}%</span>
            </div>
          </CardContent>
        </Card>
      </div>
      
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Top Recommendations</h2>
          <Button variant="ghost" size="sm" onClick={() => { setCurrentStep('decision'); setLocation('/decisions'); }} data-testid="button-view-all-decisions">
            View All <ArrowRight className="ml-1 h-4 w-4" />
          </Button>
        </div>
        
        {decisionsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Array(3).fill(0).map((_, i) => (
              <Card key={i} className="overflow-visible">
                <CardContent className="p-4">
                  <Skeleton className="h-6 w-32 mb-2" />
                  <Skeleton className="h-4 w-full mb-4" />
                  <Skeleton className="h-16 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : decisions?.recommendations?.length ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {decisions.recommendations.slice(0, 3).map((rec: any) => (
              <DecisionCard
                key={rec.id}
                id={rec.id}
                rank={rec.rank}
                title={rec.title}
                rationale={rec.rationale}
                expectedImpact={rec.expected_impact}
                risks={rec.risks}
                keyAssumption={rec.key_assumption}
                status={decisionStatuses[rec.id] || 'pending'}
                onAdoptPlan={() => handleAdoptPlan(rec.id, rec.title)}
                onRunScenario={() => handleRunScenario(rec.title)}
                onStatusChange={(status) => handleStatusChange(rec.id, status)}
                testId={`decision-card-${rec.rank}`}
              />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-8 text-center">
              <p className="text-muted-foreground">No recommendations yet. Run a simulation to generate decisions.</p>
              <Button className="mt-4" onClick={() => { setCurrentStep('simulation'); setLocation('/scenarios'); }} data-testid="button-run-simulation">
                Run Simulation
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      <Card className="overflow-visible">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-primary" />
            Notes & Annotations
          </CardTitle>
          <CardDescription>Add notes about the current scenario or assumptions</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Textarea
              placeholder="Add a note about this scenario..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              className="flex-1 min-h-[80px]"
              data-testid="textarea-comment"
            />
          </div>
          <Button onClick={addComment} disabled={!newComment.trim()} data-testid="button-add-comment">
            Add Note
          </Button>
          
          {comments.length > 0 && (
            <div className="space-y-2 mt-4" data-testid="comments-list">
              <h4 className="text-sm font-medium text-muted-foreground">Previous Notes</h4>
              <div className="space-y-2 max-h-[200px] overflow-y-auto">
                {comments.map((comment, index) => (
                  <Card key={comment.id} className="overflow-visible" data-testid={`comment-item-${index}`}>
                    <CardContent className="p-3 text-sm">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-xs text-muted-foreground" data-testid={`comment-date-${index}`}>
                          {new Date(comment.createdAt).toLocaleDateString()}
                        </span>
                        {comment.scenarioName && (
                          <Badge variant="secondary" className="text-xs" data-testid={`comment-scenario-${index}`}>{comment.scenarioName}</Badge>
                        )}
                      </div>
                      <p data-testid={`comment-text-${index}`}>{comment.text}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
      
      <Card className="overflow-visible">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Ask Copilot
          </CardTitle>
          <CardDescription>Get AI-powered insights grounded in your data</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Ask about your metrics, scenarios, or decisions..."
              className="flex-1"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setLocation('/copilot');
                }
              }}
              data-testid="input-copilot-quick"
            />
            <Button onClick={() => setLocation('/copilot')} data-testid="button-copilot-go">
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {COPILOT_PROMPTS.map((prompt, i) => (
              <Button
                key={i}
                variant="outline"
                size="sm"
                onClick={() => setLocation('/copilot')}
                data-testid={`button-copilot-prompt-${i}`}
              >
                {prompt}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
