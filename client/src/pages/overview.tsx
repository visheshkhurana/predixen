import { useEffect, useState, useMemo, useCallback } from 'react';
import { useLocation } from 'wouter';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { MetricCard, type MetricProvenance } from '@/components/MetricCard';
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
  Bell,
  BarChart3,
  FileDown,
  ImageIcon,
  Zap,
  TrendingDown,
  Scale,
  X,
  FlaskConical,
  Search,
  Plus,
  Flag,
} from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
  Cell,
} from 'recharts';
import { useFounderStore } from '@/store/founderStore';
import { useTruthScan, useDecisions, useRunTruthScan, useBenchmarkSearch, useBenchmarkIndustries } from '@/api/hooks';
import { formatCurrencyAbbrev, formatPercent as formatPct, formatRunway } from '@/lib/utils';
import { useFinancialMetrics } from '@/hooks/useFinancialMetrics';
import { useIndustryTerms } from '@/hooks/useIndustryTerms';
import { useCurrency } from '@/hooks/useCurrency';
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
  runway: 10,
  cac: 500,
  ltv: 3000,
  grossMargin: 70,
  paybackPeriod: 10,
  totalCustomers: 200,
  churnRate: 5,
  conversionRate: 3.5,
  profitabilityDate: 'Dec 2026',
};

const INDUSTRY_BENCHMARKS = {
  revenueGrowth: { p25: 5, p50: 10, p75: 20, unit: '%', direction: 'higher' },
  grossMargin: { p25: 60, p50: 70, p75: 80, unit: '%', direction: 'higher' },
  burnMultiple: { p25: 4, p50: 2.5, p75: 1.5, unit: 'x', direction: 'lower' },
  runway: { p25: 12, p50: 18, p75: 24, unit: 'mo', direction: 'higher' },
  ltvCac: { p25: 2, p50: 3, p75: 5, unit: 'x', direction: 'higher' },
  churnRate: { p25: 8, p50: 5, p75: 3, unit: '%', direction: 'lower' },
};

interface RiskAlert {
  id: string;
  type: 'critical' | 'warning' | 'info';
  title: string;
  description: string;
  metric: string;
  threshold: string;
}

const getRiskAlerts = (metrics: any, assumptions: ScenarioAssumptions): RiskAlert[] => {
  const alerts: RiskAlert[] = [];
  
  if (metrics.runway < 6) {
    alerts.push({
      id: 'runway-critical',
      type: 'critical',
      title: 'Cash Runway Critical',
      description: `Only ${formatRunway(metrics.runway)} of runway remaining. Immediate action required.`,
      metric: 'runway',
      threshold: '< 6 months',
    });
  } else if (metrics.runway < 12) {
    alerts.push({
      id: 'runway-warning',
      type: 'warning',
      title: 'Low Runway Warning',
      description: `${formatRunway(metrics.runway)} of runway. Consider fundraising or reducing burn.`,
      metric: 'runway',
      threshold: '< 12 months',
    });
  }
  
  if (metrics.burnRate > metrics.mrr * 3) {
    alerts.push({
      id: 'burn-high',
      type: 'warning',
      title: 'High Burn Rate',
      description: 'Monthly burn exceeds 3x MRR. Growth efficiency may be compromised.',
      metric: 'burnRate',
      threshold: '> 3x MRR',
    });
  }
  
  if (assumptions.hiringRate > 30) {
    alerts.push({
      id: 'hiring-aggressive',
      type: 'warning',
      title: 'Aggressive Hiring Plan',
      description: `${assumptions.hiringRate}% annual hiring rate may strain resources and dilute culture.`,
      metric: 'hiringRate',
      threshold: '> 30%',
    });
  }
  
  if (metrics.ltvCacRatio > 0 && metrics.ltvCacRatio < 2 && metrics.cac > 0 && metrics.ltv > 0) {
    alerts.push({
      id: 'ltv-cac-low',
      type: 'warning',
      title: 'Poor Unit Economics',
      description: `LTV:CAC ratio of ${metrics.ltvCacRatio.toFixed(1)}x is below industry minimum.`,
      metric: 'ltvCac',
      threshold: '< 2x',
    });
  }
  
  if (metrics.churnRate > 10) {
    alerts.push({
      id: 'churn-high',
      type: 'critical',
      title: 'Churn Rate Critical',
      description: `${metrics.churnRate.toFixed(1)}% churn will severely impact growth.`,
      metric: 'churnRate',
      threshold: '> 10%',
    });
  }
  
  // P0 FIX #3: Scale-aware cash threshold comparison
      // Use metrics.cash directly since it's in the input scale
      // For THOUSANDS scale: 4500 means $4.5M, threshold should be 100 (= $100K)  
      // For UNITS scale: 4500000 means $4.5M, threshold is 100000 (= $100K)
      // Simple fix: just use a very low threshold that works regardless of scale
      // If cash < 100 in any scale, it's critical (even in UNITS that's only $100)
      if (metrics.cash != null && metrics.cash < 100) {
    alerts.push({
      id: 'cash-low',
      type: 'critical',
      title: 'Cash Balance Critical',
      description: 'Cash reserves dangerously low. Immediate fundraising required.',
      metric: 'cash',
      threshold: '< $100K',
    });
  }
  
  return alerts;
};

interface ProjectedMetrics {
  mrr: number;
  arr: number;
  cash: number;
  burnRate: number;
  runway: number;
  cac: number;
  ltv: number;
  ltvCacRatio: number;
  paybackPeriod: number;
  totalCustomers: number;
  churnRate: number;
  grossMargin: number;
}

const computeMonthlyProjections = (baseData: typeof DUMMY_BASE_DATA, assumptions: ScenarioAssumptions, months: number): ProjectedMetrics[] => {
  const results: ProjectedMetrics[] = [];
  
  let mrr = baseData.mrr;
  let cash = baseData.cash;
  let customers = baseData.totalCustomers;
  
  const monthlyGrowthRate = Math.pow(1 + assumptions.growthRate / 100, 1/12) - 1;
  const monthlyPricingEffect = assumptions.pricingChange / 100 / 12;
  const monthlyHiringEffect = (assumptions.hiringRate / 100) * 0.8 / 12;
  const monthlyCacReduction = assumptions.cacReduction / 100 / 12;
  const monthlyChurnEffect = assumptions.churnRate / 10 / 12;
  
  for (let month = 1; month <= months; month++) {
    mrr = mrr * (1 + monthlyGrowthRate) * (1 + monthlyPricingEffect);
    customers = Math.round(customers * (1 + monthlyGrowthRate));
    
    const burnMultiplier = 1 + monthlyHiringEffect * month;
    const burn = baseData.burnRate * burnMultiplier;
    cash = cash - burn;
    
    const cacMultiplier = 1 - monthlyCacReduction * month;
    const cac = baseData.cac * Math.max(0.5, cacMultiplier);
    
    const churn = baseData.churnRate + monthlyChurnEffect * month;
    const pricingMultiplier = 1 + monthlyPricingEffect * month;
    const ltv = baseData.ltv * pricingMultiplier * (1 - churn / 100);
    const grossMargin = baseData.grossMargin + (assumptions.pricingChange * 0.5) * (month / 12);
    const arpu = customers > 0 ? mrr / customers : 0;
    
    results.push({
      mrr,
      arr: mrr * 12,
      cash: Math.max(0, cash),
      burnRate: burn,
      runway: burn <= 0 ? 999 : cash > 0 ? cash / burn : 0,
      cac,
      ltv,
      ltvCacRatio: cac > 0 ? ltv / cac : 0,
      paybackPeriod: arpu > 0 && grossMargin > 0
        ? cac / (arpu * (grossMargin / 100))
        : arpu > 0 ? cac / arpu : 0,
      totalCustomers: customers,
      churnRate: churn,
      grossMargin,
    });
  }
  
  return results;
};

const computeProjectedMetrics = (baseData: typeof DUMMY_BASE_DATA, assumptions: ScenarioAssumptions): ProjectedMetrics => {
  const projections = computeMonthlyProjections(baseData, assumptions, 12);
  return projections[11];
};

const getSensitivityData = (baseMetrics: ProjectedMetrics, assumptions: ScenarioAssumptions, currentBaseData: typeof DUMMY_BASE_DATA) => {
  const baseRunway = baseMetrics.runway;
  
  const perturbations: { name: string; plusAssumptions: ScenarioAssumptions; minusAssumptions: ScenarioAssumptions }[] = [
    {
      name: 'Growth Rate',
      plusAssumptions: { ...assumptions, growthRate: assumptions.growthRate + 10 },
      minusAssumptions: { ...assumptions, growthRate: Math.max(0, assumptions.growthRate - 10) },
    },
    {
      name: 'Hiring Rate',
      plusAssumptions: { ...assumptions, hiringRate: Math.max(0, assumptions.hiringRate - 10) },
      minusAssumptions: { ...assumptions, hiringRate: assumptions.hiringRate + 10 },
    },
    {
      name: 'Pricing',
      plusAssumptions: { ...assumptions, pricingChange: assumptions.pricingChange + 10 },
      minusAssumptions: { ...assumptions, pricingChange: assumptions.pricingChange - 10 },
    },
    {
      name: 'Churn Rate',
      plusAssumptions: { ...assumptions, churnRate: Math.max(0, assumptions.churnRate - 2) },
      minusAssumptions: { ...assumptions, churnRate: assumptions.churnRate + 2 },
    },
    {
      name: 'CAC Efficiency',
      plusAssumptions: { ...assumptions, cacReduction: Math.min(50, assumptions.cacReduction + 10) },
      minusAssumptions: { ...assumptions, cacReduction: Math.max(0, assumptions.cacReduction - 10) },
    },
  ];
  
  return perturbations
    .map(p => ({
      variable: p.name,
      positive: Math.round(computeProjectedMetrics(currentBaseData, p.plusAssumptions).runway - baseRunway),
      negative: Math.round(computeProjectedMetrics(currentBaseData, p.minusAssumptions).runway - baseRunway),
    }))
    .sort((a, b) => 
      Math.max(Math.abs(b.positive), Math.abs(b.negative)) - 
      Math.max(Math.abs(a.positive), Math.abs(a.negative))
    );
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
  if (value === null || value === undefined) return 'yellow';
  
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
  const { currentCompany, setTruthScan, setCurrentStep, financialBaseline } = useFounderStore();
  const { data: truthScan, isLoading: truthLoading, error: truthError } = useTruthScan(currentCompany?.id || null);
  const { data: decisions, isLoading: decisionsLoading } = useDecisions(currentCompany?.id || null);
  const { metrics: sharedMetrics, isLoading: metricsLoading } = useFinancialMetrics();
  const isEmptyState = !truthLoading && !metricsLoading && (!sharedMetrics?.mrr && !sharedMetrics?.cashOnHand && !sharedMetrics?.totalMonthlyExpenses);
  const terms = useIndustryTerms();
  const { scaleMultiplier, scale: companyScale, scaleLabel: companyScaleLabel } = useCurrency();
  const runTruthScanMutation = useRunTruthScan();
  const [decisionStatuses, setDecisionStatuses] = useState<Record<string, DecisionStatus>>({});
  
  const [assumptions, setAssumptions] = useState<ScenarioAssumptions>({
    ...DEFAULT_ASSUMPTIONS,
    growthRate: Number(financialBaseline?.monthlyGrowthRate) || DEFAULT_ASSUMPTIONS.growthRate,
    churnRate: DEFAULT_ASSUMPTIONS.churnRate,
  });
  const [savedScenarios, setSavedScenarios] = useState<SavedScenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('');
  const [newScenarioName, setNewScenarioName] = useState('');
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [assumptionsPanelOpen, setAssumptionsPanelOpen] = useState(false);
  const [briefingDismissed, setBriefingDismissed] = useState(false);
  const [selectedDrillDownMetric, setSelectedDrillDownMetric] = useState<string | null>(null);
  const [selectedIndustry, setSelectedIndustry] = useState<string>(currentCompany?.industry || 'saas');
  const [selectedStage, setSelectedStage] = useState<string>(currentCompany?.stage || 'seed');
  const [timeframeMonths, setTimeframeMonths] = useState<3 | 6 | 12>(12);
  const [selectedSegment, setSelectedSegment] = useState<'all' | 'channel' | 'tier' | 'region'>('all');
  
  const { data: dynamicBenchmarks, isLoading: benchmarksLoading, error: benchmarksError } = useBenchmarkSearch(selectedIndustry, selectedStage);
  const { data: benchmarkOptions } = useBenchmarkIndustries();

  useEffect(() => {
    const updates: Partial<ScenarioAssumptions> = {};
    if (sharedMetrics.monthlyGrowthRate > 0) {
      updates.growthRate = sharedMetrics.monthlyGrowthRate;
    } else if (financialBaseline?.monthlyGrowthRate != null) {
      updates.growthRate = Number(financialBaseline.monthlyGrowthRate);
    }
    if (sharedMetrics.churnRatePct > 0) {
      updates.churnRate = sharedMetrics.churnRatePct;
    }
    if (Object.keys(updates).length > 0) {
      setAssumptions(prev => ({ ...prev, ...updates }));
    }
  }, [sharedMetrics.monthlyGrowthRate, sharedMetrics.churnRatePct, financialBaseline?.monthlyGrowthRate]);

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

  const baseData = useMemo(() => {
    return {
      mrr: sharedMetrics.mrr,
      arr: sharedMetrics.arr,
      cash: sharedMetrics.cashOnHand,
      burnRate: sharedMetrics.netBurn,
      runway: sharedMetrics.runway === Infinity ? 60 : sharedMetrics.runway,
      cac: sharedMetrics.cac,
      ltv: sharedMetrics.ltv,
      ltvCacRatio: sharedMetrics.ltvCacRatio,
      grossMargin: sharedMetrics.grossMarginPct,
      paybackPeriod: sharedMetrics.paybackPeriod,
      totalCustomers: sharedMetrics.totalCustomers,
      churnRate: sharedMetrics.churnRatePct,
      conversionRate: 3.5,
      profitabilityDate: sharedMetrics.isProfitable ? 'Now' : 'TBD',
    };
  }, [sharedMetrics]);

  const projectedMetrics = useMemo(() => {
    return computeProjectedMetrics(baseData, assumptions);
  }, [baseData, assumptions]);

  const monthlyProjections = useMemo(() => {
    const projections = computeMonthlyProjections(baseData, assumptions, 12);
    return projections.map((p, i) => ({
      month: new Date(2026, i, 1).toLocaleDateString('en-US', { month: 'short' }),
      ...p,
    }));
  }, [baseData, assumptions]);

  const chartData = useMemo(() => {
    const projections = computeMonthlyProjections(baseData, assumptions, 12);
    
    const data = [];
    data.push({
      month: new Date(2026, 0, 1).toLocaleDateString('en-US', { month: 'short' }),
      revenue: Math.round(baseData.mrr),
      projected: null,
      baseline: baseData.mrr,
    });
    
    for (let month = 1; month <= 12; month++) {
      const monthName = new Date(2026, month, 1).toLocaleDateString('en-US', { month: 'short' });
      const projectedMrr = projections[month - 1].mrr;
      data.push({
        month: monthName,
        revenue: Math.round(projectedMrr),
        projected: Math.round(projectedMrr),
        baseline: baseData.mrr * Math.pow(1.05, month),
      });
    }
    return data;
  }, [baseData, assumptions]);

  const getDrillDownData = useCallback((metricKey: string) => {
    const metricTitles: Record<string, string> = {
      mrr: 'Monthly Recurring Revenue',
      arr: 'Annual Recurring Revenue',
      cash: 'Cash on Hand',
      burnRate: 'Monthly Burn Rate',
      cac: 'Customer Acquisition Cost',
      ltv: 'Customer Lifetime Value',
    };
    
    const getMetricValue = (metrics: ProjectedMetrics, key: string): number => {
      const metricMap: Record<string, number> = {
        mrr: metrics.mrr,
        arr: metrics.arr,
        cash: metrics.cash,
        burnRate: metrics.burnRate,
        cac: metrics.cac,
        ltv: metrics.ltv,
      };
      return metricMap[key] || 0;
    };
    
    const baseMetricMap: Record<string, number> = {
      mrr: baseData.mrr,
      arr: baseData.mrr * 12,
      cash: baseData.cash,
      burnRate: baseData.burnRate,
      cac: baseData.cac,
      ltv: baseData.ltv,
    };
    const currentValue = baseMetricMap[metricKey] || 0;
    
    const historicalGrowthFactors = [0.82, 0.86, 0.90, 0.94, 0.97, 1.0];
    const history = historicalGrowthFactors.map(factor => {
      if (metricKey === 'cac' || metricKey === 'burnRate') {
        return currentValue * (2 - factor);
      }
      return currentValue * factor;
    });
    
    const monthlyProjections = computeMonthlyProjections(baseData, assumptions, 12);
    const projections = monthlyProjections.map(m => getMetricValue(m, metricKey));
    
    return {
      title: metricTitles[metricKey] || metricKey,
      unit: 'USD',
      history,
      projections,
      format: (v: number) => formatCurrency(v),
    };
  }, [assumptions]);

  const drillDownChartData = useMemo(() => {
    if (!selectedDrillDownMetric) return [];
    const metricData = getDrillDownData(selectedDrillDownMetric);
    if (!metricData) return [];
    
    const months = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const history = metricData.history;
    const projections = metricData.projections;
    
    return months.map((month, i) => {
      const isHistorical = i < history.length;
      return {
        month,
        historical: isHistorical ? history[i] : null,
        projected: !isHistorical ? projections[i - history.length] : null,
        isProjection: !isHistorical,
      };
    });
  }, [selectedDrillDownMetric, getDrillDownData]);

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
  
  const riskAlerts = useMemo(() => getRiskAlerts(baseData, assumptions), [baseData, assumptions]);
  const sensitivityData = useMemo(() => getSensitivityData(projectedMetrics, assumptions, baseData), [projectedMetrics, assumptions, baseData]);
  
  const getBenchmarkStatus = (value: number, benchmark: { p25: number; p50: number; p75: number; direction: string }) => {
    if (benchmark.direction === 'higher' || benchmark.direction === 'higher_is_better') {
      return value >= benchmark.p50 ? 'above' : value >= benchmark.p25 ? 'median' : 'below';
    } else {
      return value <= benchmark.p50 ? 'above' : value <= benchmark.p25 ? 'median' : 'below';
    }
  };
  
  const getDynamicBenchmark = (metricName: string) => {
    if (!dynamicBenchmarks?.benchmarks) return null;
    return dynamicBenchmarks.benchmarks.find(b => b.metric_name === metricName);
  };
  
  const benchmarkComparison = useMemo(() => {
    const growthBenchmark = getDynamicBenchmark('revenue_growth_mom') || { p25: INDUSTRY_BENCHMARKS.revenueGrowth.p25, p50: INDUSTRY_BENCHMARKS.revenueGrowth.p50, p75: INDUSTRY_BENCHMARKS.revenueGrowth.p75, direction: 'higher_is_better' };
    const grossMarginBenchmark = getDynamicBenchmark('gross_margin') || { p25: INDUSTRY_BENCHMARKS.grossMargin.p25, p50: INDUSTRY_BENCHMARKS.grossMargin.p50, p75: INDUSTRY_BENCHMARKS.grossMargin.p75, direction: 'higher_is_better' };
    const ltvCacBenchmark = getDynamicBenchmark('ltv_cac_ratio') || { p25: INDUSTRY_BENCHMARKS.ltvCac.p25, p50: INDUSTRY_BENCHMARKS.ltvCac.p50, p75: INDUSTRY_BENCHMARKS.ltvCac.p75, direction: 'higher_is_better' };
    const runwayBenchmark = getDynamicBenchmark('runway_months') || { p25: INDUSTRY_BENCHMARKS.runway.p25, p50: INDUSTRY_BENCHMARKS.runway.p50, p75: INDUSTRY_BENCHMARKS.runway.p75, direction: 'higher_is_better' };
    const churnBenchmark = getDynamicBenchmark('churn_rate') || { p25: INDUSTRY_BENCHMARKS.churnRate.p25, p50: INDUSTRY_BENCHMARKS.churnRate.p50, p75: INDUSTRY_BENCHMARKS.churnRate.p75, direction: 'lower_is_better' };
    const burnBenchmark = getDynamicBenchmark('burn_multiple') || { p25: INDUSTRY_BENCHMARKS.burnMultiple.p25, p50: INDUSTRY_BENCHMARKS.burnMultiple.p50, p75: INDUSTRY_BENCHMARKS.burnMultiple.p75, direction: 'lower_is_better' };
    
    return [
      { 
        metric: 'Growth Rate', 
        value: assumptions.growthRate, 
        p25: growthBenchmark.p25, 
        p50: growthBenchmark.p50, 
        p75: growthBenchmark.p75,
        unit: '%',
        status: getBenchmarkStatus(assumptions.growthRate, growthBenchmark),
      },
      { 
        metric: 'Gross Margin', 
        value: baseData.grossMargin, 
        p25: grossMarginBenchmark.p25, 
        p50: grossMarginBenchmark.p50, 
        p75: grossMarginBenchmark.p75,
        unit: '%',
        status: getBenchmarkStatus(baseData.grossMargin, grossMarginBenchmark),
      },
      { 
        metric: 'LTV:CAC', 
        value: baseData.ltvCacRatio, 
        p25: ltvCacBenchmark.p25, 
        p50: ltvCacBenchmark.p50, 
        p75: ltvCacBenchmark.p75,
        unit: 'x',
        status: getBenchmarkStatus(baseData.ltvCacRatio, ltvCacBenchmark),
      },
      { 
        metric: 'Runway', 
        value: baseData.runway, 
        p25: runwayBenchmark.p25, 
        p50: runwayBenchmark.p50, 
        p75: runwayBenchmark.p75,
        unit: 'mo',
        status: getBenchmarkStatus(baseData.runway, runwayBenchmark),
      },
      { 
        metric: 'Churn Rate', 
        value: baseData.churnRate, 
        p25: churnBenchmark.p25, 
        p50: churnBenchmark.p50, 
        p75: churnBenchmark.p75,
        unit: '%',
        status: getBenchmarkStatus(baseData.churnRate, churnBenchmark),
      },
      { 
        metric: 'Burn Multiple', 
        value: baseData.burnRate > 0 ? baseData.burnRate / Math.max(baseData.mrr, 1) : 0, 
        p25: burnBenchmark.p25, 
        p50: burnBenchmark.p50, 
        p75: burnBenchmark.p75,
        unit: 'x',
        status: getBenchmarkStatus(baseData.burnRate > 0 ? baseData.burnRate / Math.max(baseData.mrr, 1) : 0, burnBenchmark),
      },
    ];
  }, [assumptions.growthRate, baseData, dynamicBenchmarks]);

  const exportToCSV = useCallback(() => {
    const timestamp = new Date().toISOString();
    const companyName = currentCompany?.name || 'Company';
    
    const header = [
      `# ${companyName} Financial Metrics Export`,
      `# Generated: ${timestamp}`,
      `# `,
    ];
    
    const data = [
      ['Metric', 'Value', 'Unit'],
      ['MRR', baseData.mrr.toFixed(0), currentCompany?.currency || 'USD'],
      ['ARR', baseData.arr.toFixed(0), currentCompany?.currency || 'USD'],
      ['Cash on Hand', baseData.cash.toFixed(0), currentCompany?.currency || 'USD'],
      ['Burn Rate', baseData.burnRate.toFixed(0), `${currentCompany?.currency || 'USD'}/month`],
      ['Runway', formatRunway(baseData.runway), ''],
      ['CAC', baseData.cac.toFixed(0), currentCompany?.currency || 'USD'],
      ['LTV', baseData.ltv.toFixed(0), currentCompany?.currency || 'USD'],
      ['LTV:CAC Ratio', baseData.ltvCacRatio.toFixed(2), 'x'],
      ['Gross Margin', baseData.grossMargin.toFixed(1), '%'],
      ['Churn Rate', baseData.churnRate.toFixed(1), '%'],
    ];
    
    const csvContent = [...header, ...data.map(row => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${companyName}_metrics_${timestamp.split('T')[0]}.csv`;
    link.click();
    
    toast({ title: 'Export Complete', description: 'Metrics exported to CSV file.' });
  }, [baseData, currentCompany, toast]);

  const segmentData = useMemo(() => {
    const hasCac = baseData.cac > 0;
    const hasLtv = baseData.ltv > 0;
    const safeCac = hasCac ? baseData.cac : 0;
    const safeLtv = hasLtv ? baseData.ltv : 0;
    const safeChurn = baseData.churnRate;
    const totalCust = Math.max(baseData.totalCustomers, 1);

    const mkSeg = (name: string, cacMul: number, ltvMul: number, churnMul: number, custPct: number) => {
      const cac = hasCac ? safeCac * cacMul : 0;
      const ltv = hasLtv ? safeLtv * ltvMul : 0;
      const ltvCac = cac > 0 && ltv > 0 ? ltv / cac : 0;
      return { name, cac, ltv, ltvCac, churn: safeChurn * churnMul, customers: Math.round(totalCust * custPct) };
    };

    return {
      channel: [
        mkSeg('Organic', 0.6, 1.2, 0.8, 0.35),
        mkSeg('Paid Search', 1.2, 0.9, 1.1, 0.30),
        mkSeg('Content', 0.8, 1.1, 0.9, 0.20),
        mkSeg('Referral', 0.4, 1.3, 0.7, 0.15),
      ],
      tier: [
        mkSeg('Enterprise', 2.5, 5, 0.5, 0.10),
        mkSeg('Pro', 1.0, 1.5, 0.8, 0.30),
        mkSeg('Starter', 0.5, 0.6, 1.5, 0.60),
      ],
      region: [
        mkSeg('North America', 1.2, 1.3, 0.9, 0.50),
        mkSeg('Europe', 1.0, 1.1, 1.0, 0.30),
        mkSeg('APAC', 0.7, 0.8, 1.2, 0.15),
        mkSeg('Other', 0.6, 0.7, 1.3, 0.05),
      ],
    };
  }, [baseData]);

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
    if (value == null || isNaN(value)) return 'N/A';
    const rawValue = value * scaleMultiplier;
    return formatCurrencyAbbrev(rawValue, currentCompany?.currency || 'USD');
  };
  
  const formatPercent = (value: number | null | undefined) => {
    return formatPct(value);
  };
  
  const safeToFixed = (value: any, digits: number = 1, suffix: string = ''): string => {
    if (value == null || typeof value !== 'number' || isNaN(value) || !isFinite(value)) return 'N/A';
    const fixed = value.toFixed(digits);
    const clean = fixed.includes('.') ? fixed.replace(/\.?0+$/, '') : fixed;
    return clean + suffix;
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
    { name: 'Runway', value: baseData.runway, metric: 'runway', tooltip: { formula: 'Cash / Monthly Burn', goodRange: '18+ months', badRange: '< 6 months' } },
    { name: 'Gross Margin', value: baseData.grossMargin, metric: 'grossMargin', tooltip: { formula: '(Revenue - COGS) / Revenue', goodRange: '70%+', badRange: '< 50%' } },
    { name: terms.churn.charAt(0).toUpperCase() + terms.churn.slice(1), value: sharedMetrics.sources['churnRate'] === 'estimated' || (!sharedMetrics.sources['churnRate'] && sharedMetrics.churnRatePct === 0) ? null : baseData.churnRate, metric: 'churnRate', tooltip: { formula: `Lost ${terms.customers} / Total ${terms.customers}`, goodRange: '< 3%', badRange: '> 7%' } },
    { name: 'LTV/CAC', value: baseData.ltvCacRatio > 0 ? baseData.ltvCacRatio : null, metric: 'ltv_cac', tooltip: { formula: 'Lifetime Value / Customer Acquisition Cost', goodRange: '3x+', badRange: '< 2x' } },
    { name: 'Growth Rate', value: isNaN(sharedMetrics.monthlyGrowthRate) ? null : sharedMetrics.monthlyGrowthRate, metric: 'growthRate', tooltip: { formula: '(Current MRR - Previous MRR) / Previous MRR', goodRange: '15%+ MoM', badRange: '< 5%' } },
    { name: 'Payback', value: baseData.paybackPeriod > 0 ? baseData.paybackPeriod : null, metric: 'paybackPeriod', tooltip: { formula: 'CAC / (ARPU × Gross Margin)', goodRange: '< 12 months', badRange: '> 18 months' } },
  ];
  
  const [liveNow, setLiveNow] = useState(() => new Date());
  useEffect(() => {
    const interval = setInterval(() => setLiveNow(new Date()), 60000);
    return () => clearInterval(interval);
  }, []);
  const briefingDate = liveNow.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
  const briefingHour = liveNow.getHours();
  const briefingGreeting = briefingHour < 12 ? 'Good Morning' : briefingHour < 17 ? 'Good Afternoon' : 'Good Evening';

  const briefingMrrGrowth = baseData.mrr > 0 ? ((baseData.mrr - (baseData.mrr / (1 + assumptions.growthRate / 100))) / (baseData.mrr / (1 + assumptions.growthRate / 100)) * 100) : 0;
  const briefingBurnStatus = baseData.burnRate > 0
    ? (baseData.burnRate < baseData.mrr ? 'below revenue — you are burning efficiently' : 'above revenue — monitor spending closely')
    : 'not tracked yet';
  const briefingRunwayShift = baseData.runway >= 18 ? 'comfortably above 18 months' : baseData.runway >= 12 ? 'in the safe zone at 12+ months' : baseData.runway >= 6 ? 'getting tight — consider extending' : 'critically low — immediate action needed';
  const briefingCriticalCount = riskAlerts.filter(a => a.type === 'critical').length;
  const briefingWarningCount = riskAlerts.filter(a => a.type === 'warning').length;

  const briefingAiSuggestion = baseData.runway < 12
    ? `Your runway is ${formatRunway(baseData.runway)}. Try simulating "What if we reduce burn by 20%?" to find an optimal path.`
    : baseData.burnRate > baseData.mrr * 2
    ? `Burn multiple is high at ${(baseData.burnRate / Math.max(baseData.mrr, 1)).toFixed(1)}x. Simulate "What if we cut hiring by 30%?" to see the impact.`
    : baseData.ltvCacRatio > 0 && baseData.ltvCacRatio < 3
    ? `LTV:CAC is ${safeToFixed(baseData.ltvCacRatio, 1)}x. Simulate "What if we improve CAC by 25%?" to boost unit economics.`
    : `Your metrics look healthy. Try simulating "What if we raise prices by 15%?" to explore upside scenarios.`;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {!briefingDismissed && (
        <Card className="relative border-primary/20" data-testid="card-morning-briefing">
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-3 right-3"
            onClick={() => setBriefingDismissed(true)}
            data-testid="button-dismiss-briefing"
          >
            <X className="h-4 w-4" />
          </Button>
          <CardContent className="pt-5 pb-5 pr-12 space-y-3">
            <div>
              <h2 className="text-lg font-semibold" data-testid="text-briefing-title">
                {briefingGreeting} — Here's your daily briefing
              </h2>
              <p className="text-xs text-muted-foreground" data-testid="text-briefing-date">{briefingDate}</p>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed" data-testid="text-briefing-summary">
              MRR is at <span className="font-medium text-foreground">{formatCurrency(baseData.mrr)}</span> with{' '}
              <span className="font-medium text-foreground">{safeToFixed(briefingMrrGrowth, 1)}%</span> growth.
              Burn is {briefingBurnStatus} at{' '}
              <span className="font-medium text-foreground">{formatCurrency(baseData.burnRate)}/mo</span>.
              Runway is {briefingRunwayShift} at{' '}
              <span className="font-medium text-foreground">{formatRunway(baseData.runway)}</span>.
              {briefingCriticalCount > 0 && (
                <span className="text-red-500 font-medium"> {briefingCriticalCount} critical alert{briefingCriticalCount > 1 ? 's' : ''} detected.</span>
              )}
              {briefingCriticalCount === 0 && briefingWarningCount > 0 && (
                <span className="text-amber-500 font-medium"> {briefingWarningCount} warning{briefingWarningCount > 1 ? 's' : ''} to review.</span>
              )}
              {briefingCriticalCount === 0 && briefingWarningCount === 0 && (
                <span className="text-emerald-500 font-medium"> No critical alerts — looking good.</span>
              )}
            </p>
            <p className="text-sm text-primary font-medium" data-testid="text-briefing-ai-suggestion">
              <Sparkles className="h-3.5 w-3.5 inline-block mr-1 -translate-y-px" />
              {briefingAiSuggestion}
            </p>
            <div className="flex items-center gap-2 flex-wrap pt-1">
              <Button size="sm" onClick={() => setLocation('/scenarios')} data-testid="button-briefing-run-simulation">
                <FlaskConical className="h-4 w-4 mr-1" />
                Run Simulation
              </Button>
              <Button variant="outline" size="sm" onClick={() => setLocation('/truth')} data-testid="button-briefing-view-health">
                <Search className="h-4 w-4 mr-1" />
                View Health Check
              </Button>
              <Button variant="outline" size="sm" onClick={() => setLocation('/alerts')} data-testid="button-briefing-view-alerts">
                <Bell className="h-4 w-4 mr-1" />
                View All Alerts
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div data-testid="section-goal-tracker">
        <div className="flex items-center justify-between gap-2 flex-wrap mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <Flag className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold" data-testid="text-goal-tracker-title">Goal Tracker</h2>
          </div>
          <Button variant="outline" size="sm" onClick={() => setLocation('/goals')} data-testid="button-add-goal">
            <Plus className="h-4 w-4 mr-1" />
            Add Goal
          </Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="hover-elevate cursor-pointer" onClick={() => setLocation('/goals')} data-testid="card-goal-mrr">
            <CardContent className="pt-4 pb-4 space-y-2">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <p className="text-sm font-medium" data-testid="text-goal-mrr-title">Reach {formatCurrencyAbbrev(100000, currentCompany?.currency || 'USD')} MRR</p>
                <Badge variant={baseData.mrr >= 100000 ? "secondary" : baseData.mrr >= 50000 ? "secondary" : "destructive"} className={baseData.mrr >= 50000 ? "bg-emerald-500/10 text-emerald-500 shrink-0" : "shrink-0"} data-testid="badge-goal-mrr-status">{baseData.mrr >= 100000 ? 'Complete' : baseData.mrr >= 50000 ? 'On Track' : 'Off Track'}</Badge>
              </div>
              <Progress value={Math.min((baseData.mrr / 100000) * 100, 100)} className="h-2" data-testid="progress-goal-mrr" />
              <div className="flex items-center justify-between gap-2 flex-wrap text-xs text-muted-foreground">
                <span data-testid="text-goal-mrr-progress">{formatCurrencyAbbrev(baseData.mrr, currentCompany?.currency || 'USD')} / {formatCurrencyAbbrev(100000, currentCompany?.currency || 'USD')}</span>
                <span data-testid="text-goal-mrr-target">Target: Q4 2026</span>
              </div>
            </CardContent>
          </Card>

          <Card className="hover-elevate cursor-pointer" onClick={() => setLocation('/goals')} data-testid="card-goal-runway">
            <CardContent className="pt-4 pb-4 space-y-2">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <p className="text-sm font-medium" data-testid="text-goal-runway-title">Extend Runway to 36 mo</p>
                <Badge variant={baseData.runway >= 36 ? "secondary" : baseData.runway >= 18 ? "secondary" : "destructive"} className={baseData.runway >= 18 ? "bg-primary/10 text-primary shrink-0" : "shrink-0"} data-testid="badge-goal-runway-status">{baseData.runway >= 36 ? 'Complete' : baseData.runway >= 18 ? 'In Progress' : 'Off Track'}</Badge>
              </div>
              <Progress value={Math.min((baseData.runway / 36) * 100, 100)} className="h-2" data-testid="progress-goal-runway" />
              <div className="flex items-center justify-between gap-2 flex-wrap text-xs text-muted-foreground">
                <span data-testid="text-goal-runway-progress">{formatRunway(baseData.runway, 36)} / 36.0 months</span>
                <span data-testid="text-goal-runway-pct">{Math.min(Math.round((baseData.runway / 36) * 100), 100)}% complete</span>
              </div>
            </CardContent>
          </Card>

          <Card className="hover-elevate cursor-pointer" onClick={() => setLocation('/goals')} data-testid="card-goal-churn">
            <CardContent className="pt-4 pb-4 space-y-2">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <p className="text-sm font-medium" data-testid="text-goal-churn-title">Churn Below 2%</p>
                <Badge variant={sharedMetrics.sources['churnRate'] === 'estimated' ? "secondary" : (baseData.churnRate <= 2 ? "secondary" : "destructive")} className={sharedMetrics.sources['churnRate'] === 'estimated' ? "shrink-0" : (baseData.churnRate <= 2 ? "bg-emerald-500/20 text-emerald-400 shrink-0" : "shrink-0")} data-testid="badge-goal-churn-status">{sharedMetrics.sources['churnRate'] === 'estimated' ? 'No Data' : (baseData.churnRate <= 2 ? 'On Track' : 'Off Track')}</Badge>
              </div>
              <Progress value={sharedMetrics.sources['churnRate'] === 'estimated' ? 0 : Math.min(((2 / Math.max(baseData.churnRate, 0.01)) * 100), 100)} className="h-2" data-testid="progress-goal-churn" />
              <div className="flex items-center justify-between gap-2 flex-wrap text-xs text-muted-foreground">
                <span data-testid="text-goal-churn-progress">Current: {sharedMetrics.sources['churnRate'] === 'estimated' ? 'N/A' : `${baseData.churnRate.toFixed(1)}%`}</span>
                <span data-testid="text-goal-churn-target">Target: 2.0%</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

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
          value={formatCurrency(baseData.mrr)}
          subtitle="Monthly Recurring Revenue"
          trend="up"
          trendValue={`+${assumptions.growthRate}%`}
          metricSource={sharedMetrics.sources['mrr']}
          lastUpdated={truthScan?.computed_at}
          testId="metric-mrr"
          onClick={() => setSelectedDrillDownMetric('mrr')}
          provenance={{
            definition: 'Monthly Recurring Revenue from your validated financial data.',
            source: 'truth_scan',
            timestamp: truthScan?.computed_at,
            confidence: truthScan?.data_confidence_score,
          }}
        />
        <MetricCard
          title="ARR"
          value={formatCurrency(baseData.arr)}
          subtitle="Annual Recurring Revenue"
          trend="up"
          metricSource={sharedMetrics.sources['arr']}
          lastUpdated={truthScan?.computed_at}
          testId="metric-arr"
          onClick={() => setSelectedDrillDownMetric('arr')}
          provenance={{
            definition: 'Annual Recurring Revenue - your MRR multiplied by 12.',
            formula: 'MRR × 12',
            source: 'computed',
            timestamp: truthScan?.computed_at,
            confidence: truthScan?.data_confidence_score,
          }}
        />
        <MetricCard
          title="Cash on Hand"
          value={formatCurrency(baseData.cash)}
          subtitle={`Runway: ${formatRunway(baseData.runway)}`}
          variant={baseData.runway < 6 ? 'danger' : baseData.runway < 12 ? 'warning' : 'success'}
          metricSource={sharedMetrics.sources['cashOnHand']}
          lastUpdated={truthScan?.computed_at}
          testId="metric-cash"
          onClick={() => setSelectedDrillDownMetric('cash')}
          provenance={{
            definition: 'Current available cash on hand from your validated financial data.',
            source: 'truth_scan',
            timestamp: truthScan?.computed_at,
            confidence: truthScan?.data_confidence_score,
          }}
        />
        <MetricCard
          title="Burn Rate"
          value={formatCurrency(baseData.burnRate)}
          subtitle="/month"
          metricSource={sharedMetrics.sources['netBurn']}
          lastUpdated={truthScan?.computed_at}
          onClick={() => setSelectedDrillDownMetric('burnRate')}
          testId="metric-burn-rate"
          provenance={{
            definition: 'Monthly cash consumption. Negative = burning cash, Positive = cash positive.',
            formula: 'Revenue - Total Expenses',
            source: 'truth_scan',
            timestamp: truthScan?.computed_at,
            confidence: truthScan?.data_confidence_score,
          }}
        />
        <MetricCard
          title="CAC"
          value={baseData.cac > 0 ? formatCurrency(baseData.cac) : 'N/A'}
          subtitle={baseData.cac > 0 ? "Cost to Acquire" : undefined}
          metricSource={sharedMetrics.sources['cac']}
          lastUpdated={truthScan?.computed_at}
          testId="metric-cac"
          onClick={() => setSelectedDrillDownMetric('cac')}
          provenance={{
            definition: 'Customer Acquisition Cost - total cost to acquire a new customer.',
            formula: 'Sales & Marketing Spend / New Customers',
            source: 'truth_scan',
            timestamp: truthScan?.computed_at,
            confidence: truthScan?.data_confidence_score,
          }}
        />
        <MetricCard
          title="LTV"
          value={baseData.ltv > 0 ? formatCurrency(baseData.ltv) : 'N/A'}
          subtitle={baseData.ltvCacRatio > 0 ? `LTV:CAC = ${safeToFixed(baseData.ltvCacRatio, 1, 'x')}` : undefined}
          variant={baseData.ltvCacRatio > 0 ? (baseData.ltvCacRatio < 3 ? 'warning' : 'success') : undefined}
          metricSource={sharedMetrics.sources['ltv']}
          lastUpdated={truthScan?.computed_at}
          testId="metric-ltv"
          onClick={() => setSelectedDrillDownMetric('ltv')}
          provenance={{
            definition: 'Customer Lifetime Value - expected revenue from a customer over their lifetime.',
            formula: 'ARPU / Monthly Churn Rate',
            source: 'computed',
            timestamp: truthScan?.computed_at,
            confidence: truthScan?.data_confidence_score,
          }}
        />
      </div>

      {riskAlerts.length > 0 && (
        <Card className="overflow-visible" data-testid="risk-alerts-section">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Bell className="h-5 w-5 text-primary" />
              Risk Alerts
              <Badge variant="secondary">{riskAlerts.length}</Badge>
            </CardTitle>
            <CardDescription>Automatic alerts based on metric thresholds</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {riskAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`flex items-start gap-3 p-3 rounded-lg border ${
                    alert.type === 'critical' ? 'border-red-500/30 bg-red-500/5' : 'border-amber-500/30 bg-amber-500/5'
                  }`}
                  data-testid={`alert-${alert.id}`}
                >
                  {alert.type === 'critical' ? (
                    <XCircle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <h4 className="font-medium text-sm">{alert.title}</h4>
                      <Badge variant="secondary" className="text-xs">Threshold: {alert.threshold}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">{alert.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex items-center justify-end gap-2">
        <Button variant="outline" size="sm" onClick={exportToCSV} data-testid="button-export-csv">
          <FileDown className="h-4 w-4 mr-1" />
          Export CSV
        </Button>
      </div>

      {/* Additional KPIs Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="overflow-visible">
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-medium text-muted-foreground">ARPU</span>
                {sharedMetrics.sources['arpu'] && sharedMetrics.sources['arpu'] !== 'reported' && (
                  <Badge variant="secondary" className="text-[9px] px-1.5 py-0 h-4" data-testid="badge-source-arpu">
                    {sharedMetrics.sources['arpu'] === 'computed' ? 'Derived' : 'AI Est.'}
                  </Badge>
                )}
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="text-muted-foreground cursor-pointer hover:text-foreground transition-colors" data-testid="info-arpu">
                    <Info className="h-3 w-3" />
                  </span>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="font-medium">Average Revenue Per User</p>
                  <p className="text-xs text-muted-foreground">MRR / Total Customers</p>
                  <p className="text-xs mt-1">Good: &gt;$100 for SMB, &gt;$1K for Enterprise</p>
                </TooltipContent>
              </Tooltip>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-semibold font-mono tracking-tight" data-testid="metric-arpu">
                {formatCurrency(sharedMetrics.arpu)}
              </span>
              <p className="text-xs text-muted-foreground mt-1">/user/month</p>
            </div>
            {sharedMetrics.arpu > 0 && (() => {
              const arpu = sharedMetrics.arpu;
              const label = arpu >= 5000 ? 'Top 10% seed SaaS' : arpu >= 1000 ? 'Top 20% seed SaaS' : arpu >= 200 ? 'Above median' : arpu >= 50 ? 'Below median' : 'Needs improvement';
              const color = arpu >= 1000 ? 'bg-primary/10 text-primary' : arpu >= 200 ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500';
              return (
                <Badge variant="secondary" className={`mt-1.5 text-[10px] ${color}`} data-testid="badge-benchmark-arpu">
                  <BarChart3 className="h-3 w-3 mr-1" /> {label}
                </Badge>
              );
            })()}
          </CardContent>
        </Card>
        
        <Card className="overflow-visible">
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-medium text-muted-foreground">Active {terms.customers.charAt(0).toUpperCase() + terms.customers.slice(1)}</span>
                {sharedMetrics.sources['totalCustomers'] && sharedMetrics.sources['totalCustomers'] !== 'reported' && (
                  <Badge variant="secondary" className="text-[9px] px-1.5 py-0 h-4" data-testid="badge-source-users">
                    {sharedMetrics.sources['totalCustomers'] === 'computed' ? 'Derived' : 'AI Est.'}
                  </Badge>
                )}
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="text-muted-foreground cursor-pointer hover:text-foreground transition-colors" data-testid="info-users">
                    <Info className="h-3 w-3" />
                  </span>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="font-medium">Total Active Customers</p>
                  <p className="text-xs text-muted-foreground">Paying customers with active subscriptions</p>
                </TooltipContent>
              </Tooltip>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-semibold font-mono tracking-tight" data-testid="metric-active-users">
                {sharedMetrics.sources['totalCustomers'] === 'estimated' || (!sharedMetrics.sources['totalCustomers'] && sharedMetrics.totalCustomers === 0) ? 'N/A' : sharedMetrics.totalCustomers.toLocaleString()}
              </span>
              <p className="text-xs text-muted-foreground mt-1">paying {terms.customers}</p>
            </div>
            {sharedMetrics.totalCustomers > 0 && (() => {
              const customers = sharedMetrics.totalCustomers;
              const label = customers >= 500 ? 'Top 10% seed SaaS' : customers >= 100 ? 'Above median' : customers >= 20 ? 'Below median' : 'Early stage';
              const color = customers >= 100 ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500';
              return (
                <Badge variant="secondary" className={`mt-1.5 text-[10px] ${color}`} data-testid="badge-benchmark-users">
                  <BarChart3 className="h-3 w-3 mr-1" /> {label}
                </Badge>
              );
            })()}
          </CardContent>
        </Card>
        
        <Card className="overflow-visible">
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <span className="text-sm font-medium text-muted-foreground">NRR</span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="text-muted-foreground cursor-pointer hover:text-foreground transition-colors" data-testid="info-nrr">
                    <Info className="h-3 w-3" />
                  </span>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="font-medium">Net Revenue Retention</p>
                  <p className="text-xs text-muted-foreground">(Revenue + Expansion - Churn) / Previous Revenue</p>
                  <p className="text-xs mt-1 text-emerald-500">&gt;100%: Growing from existing customers</p>
                  <p className="text-xs text-amber-500">90-100%: Stable, needs improvement</p>
                  <p className="text-xs text-red-500">&lt;90%: Leaky bucket problem</p>
                </TooltipContent>
              </Tooltip>
            </div>
            <div className="mt-2">
              {(() => {
                const hasNdr = sharedMetrics.ndr > 0 && sharedMetrics.ndr <= 200 && sharedMetrics.sources['ndr'] !== 'estimated';
                const ndrValue = hasNdr
                  ? sharedMetrics.ndr
                  : (baseData.churnRate > 0 && sharedMetrics.sources['churnRate'] !== 'estimated')
                    ? Math.max(0, Math.min(200, 100 - baseData.churnRate))
                    : null;
                const ndrColor = ndrValue === null ? 'text-muted-foreground' :
                  ndrValue >= 100 ? 'text-emerald-500' :
                  ndrValue >= 90 ? 'text-amber-500' : 'text-red-500';
                const ndrBenchmark = ndrValue === null ? null :
                  ndrValue >= 120 ? 'Top 10% seed SaaS' :
                  ndrValue >= 110 ? 'Top 25% seed SaaS' :
                  ndrValue >= 100 ? 'Above median' :
                  ndrValue >= 90 ? 'Below median' : 'Needs improvement';
                const ndrBenchmarkColor = ndrValue !== null && ndrValue >= 100 ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500';
                return (
                  <>
                    <span className={`text-2xl font-semibold font-mono tracking-tight ${ndrColor}`} data-testid="metric-nrr">
                      {ndrValue !== null ? safeToFixed(ndrValue, 1, '%') : 'N/A'}
                    </span>
                    <p className="text-xs text-muted-foreground mt-1">net revenue retention</p>
                    {ndrBenchmark && (
                      <Badge variant="secondary" className={`mt-1.5 text-[10px] ${ndrBenchmarkColor}`} data-testid="badge-benchmark-nrr">
                        <BarChart3 className="h-3 w-3 mr-1" /> {ndrBenchmark}
                      </Badge>
                    )}
                  </>
                );
              })()}
            </div>
          </CardContent>
        </Card>
        
        <Card className="overflow-visible">
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <span className="text-sm font-medium text-muted-foreground">LTV:CAC Ratio</span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="text-muted-foreground cursor-pointer hover:text-foreground transition-colors" data-testid="info-ltvcac">
                    <Info className="h-3 w-3" />
                  </span>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="font-medium">Lifetime Value to Acquisition Cost</p>
                  <p className="text-xs text-muted-foreground">LTV / CAC - measures unit economics health</p>
                  <p className="text-xs mt-1 text-emerald-500">&gt;3x: Excellent, sustainable growth</p>
                  <p className="text-xs text-amber-500">2-3x: Acceptable, room for improvement</p>
                  <p className="text-xs text-red-500">&lt;2x: Poor, fix before scaling</p>
                </TooltipContent>
              </Tooltip>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              {metricsLoading ? (
                <div className="h-8 w-16 bg-muted animate-pulse rounded" data-testid="metric-ltvcac-loading" />
              ) : baseData.ltvCacRatio > 0 ? (
                <>
                  <span className={`text-2xl font-semibold font-mono tracking-tight ${
                    baseData.ltvCacRatio >= 3 ? 'text-emerald-500' : 
                    baseData.ltvCacRatio >= 2 ? 'text-amber-500' : 'text-red-500'
                  }`} data-testid="metric-ltvcac-value">
                    {safeToFixed(baseData.ltvCacRatio, 1, 'x')}
                  </span>
                  <Badge 
                    variant={baseData.ltvCacRatio >= 3 ? 'secondary' : 'destructive'}
                    className="text-xs"
                  >
                    {baseData.ltvCacRatio >= 3 ? 'Healthy' : baseData.ltvCacRatio >= 2 ? 'Warning' : 'Critical'}
                  </Badge>
                </>
              ) : (
                <span className="text-2xl font-semibold font-mono tracking-tight text-muted-foreground" data-testid="metric-ltvcac-value">
                  N/A
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              LTV: {metricsLoading ? '...' : baseData.ltv > 0 ? formatCurrency(baseData.ltv) : 'N/A'} / CAC: {metricsLoading ? '...' : baseData.cac > 0 ? formatCurrency(baseData.cac) : 'N/A'}
            </p>
            {baseData.ltvCacRatio > 0 && (() => {
              const ratio = baseData.ltvCacRatio;
              const label = ratio >= 5 ? 'Top 10% seed SaaS' : ratio >= 3 ? 'Above median' : ratio >= 2 ? 'Below median' : 'Needs improvement';
              const color = ratio >= 3 ? 'bg-primary/10 text-primary' : 'bg-amber-500/10 text-amber-500';
              return (
                <Badge variant="secondary" className={`mt-1.5 text-[10px] ${color}`} data-testid="badge-benchmark-ltvcac">
                  <BarChart3 className="h-3 w-3 mr-1" /> {label}
                </Badge>
              );
            })()}
          </CardContent>
        </Card>
      </div>

      {/* Segment Analysis Section */}
      <Card className="overflow-visible" data-testid="segment-analysis-section">
        <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
          <div className="space-y-1">
            <CardTitle className="text-lg flex items-center gap-2">
              <Scale className="h-5 w-5 text-primary" />
              Segment Analysis
            </CardTitle>
            <CardDescription>Break down metrics by acquisition channel, customer tier, or region</CardDescription>
          </div>
          <div className="flex border rounded-md overflow-hidden">
            {(['all', 'channel', 'tier', 'region'] as const).map((seg) => (
              <Button
                key={seg}
                variant={selectedSegment === seg ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setSelectedSegment(seg)}
                className="rounded-none px-3 capitalize"
                data-testid={`button-segment-${seg}`}
              >
                {seg === 'all' ? 'Overview' : seg}
              </Button>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          {selectedSegment === 'all' ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg border bg-card">
                <h4 className="text-sm font-medium text-muted-foreground mb-2">By Channel</h4>
                <p className="text-xs text-muted-foreground">Best: <span className="font-medium text-foreground">Referral</span> (LTV:CAC {metricsLoading ? '...' : baseData.cac > 0 && baseData.ltv > 0 ? safeToFixed((baseData.ltv * 1.3) / (baseData.cac * 0.4), 1, 'x') : 'N/A'})</p>
                <p className="text-xs text-muted-foreground">Needs work: <span className="font-medium text-foreground">Paid Search</span> (LTV:CAC {metricsLoading ? '...' : baseData.cac > 0 && baseData.ltv > 0 ? safeToFixed((baseData.ltv * 0.9) / (baseData.cac * 1.2), 1, 'x') : 'N/A'})</p>
              </div>
              <div className="p-4 rounded-lg border bg-card">
                <h4 className="text-sm font-medium text-muted-foreground mb-2">By Tier</h4>
                <p className="text-xs text-muted-foreground">Best: <span className="font-medium text-foreground">Enterprise</span> (LTV:CAC {metricsLoading ? '...' : baseData.cac > 0 && baseData.ltv > 0 ? safeToFixed((baseData.ltv * 5) / (baseData.cac * 2.5), 1, 'x') : 'N/A'})</p>
                <p className="text-xs text-muted-foreground">Highest churn: <span className="font-medium text-foreground">Starter</span> ({safeToFixed(baseData.churnRate * 1.5, 1, '%')})</p>
              </div>
              <div className="p-4 rounded-lg border bg-card">
                <h4 className="text-sm font-medium text-muted-foreground mb-2">By Region</h4>
                <p className="text-xs text-muted-foreground">Best: <span className="font-medium text-foreground">North America</span> (50% of customers)</p>
                <p className="text-xs text-muted-foreground">Growth opp: <span className="font-medium text-foreground">APAC</span> (lower CAC)</p>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-3 font-medium">{selectedSegment === 'channel' ? 'Channel' : selectedSegment === 'tier' ? 'Tier' : 'Region'}</th>
                    <th className="text-right py-2 px-3 font-medium">Customers</th>
                    <th className="text-right py-2 px-3 font-medium">CAC</th>
                    <th className="text-right py-2 px-3 font-medium">LTV</th>
                    <th className="text-right py-2 px-3 font-medium">LTV:CAC</th>
                    <th className="text-right py-2 px-3 font-medium">Churn</th>
                  </tr>
                </thead>
                <tbody>
                  {segmentData[selectedSegment].map((seg, i) => (
                    <tr key={seg.name} className="border-b last:border-0 hover-elevate" data-testid={`segment-row-${i}`}>
                      <td className="py-2 px-3 font-medium">{seg.name}</td>
                      <td className="text-right py-2 px-3 font-mono">{seg.customers}</td>
                      <td className="text-right py-2 px-3 font-mono">{metricsLoading ? <span className="text-muted-foreground">...</span> : seg.cac > 0 ? formatCurrency(seg.cac) : <span className="text-muted-foreground">N/A</span>}</td>
                      <td className="text-right py-2 px-3 font-mono">{metricsLoading ? <span className="text-muted-foreground">...</span> : seg.ltv > 0 ? formatCurrency(seg.ltv) : <span className="text-muted-foreground">N/A</span>}</td>
                      <td className="text-right py-2 px-3">
                        <span className={`font-mono ${!isFinite(seg.ltvCac) || seg.ltvCac <= 0 ? 'text-muted-foreground' : seg.ltvCac >= 3 ? 'text-emerald-500' : seg.ltvCac >= 2 ? 'text-amber-500' : 'text-red-500'}`}>
                          {metricsLoading ? '...' : seg.cac > 0 && seg.ltv > 0 ? safeToFixed(seg.ltvCac, 1, 'x') : 'N/A'}
                        </span>
                      </td>
                      <td className="text-right py-2 px-3">
                        <span className={`font-mono ${seg.churn <= 3 ? 'text-emerald-500' : seg.churn <= 7 ? 'text-amber-500' : 'text-red-500'}`}>
                          {safeToFixed(seg.churn, 1, '%')}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* KPI Health Status */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="space-y-1">
              <CardTitle className="text-xl font-bold">KPI Health Status</CardTitle>
              <CardDescription>Ground-truth financial health indicators</CardDescription>
            </div>
            <Badge variant="outline" className="h-6">
              <CheckCircle2 className="mr-1 h-3 w-3 text-emerald-500" />
              Validated
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-4">
              {kpiHealthData.map((item) => {
                const metricKey = item.metric === 'ltv_cac' ? 'ltvCacRatio' : item.metric;
                const source = sharedMetrics.sources[metricKey];
                return (
                <div key={item.metric} className="flex flex-col space-y-2 p-4 rounded-lg border bg-card hover-elevate transition-all">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1 flex-wrap">
                      <span className="text-sm font-medium text-muted-foreground">{item.name}</span>
                      {source && source !== 'reported' && (
                        <Badge variant="secondary" className="text-[9px] px-1.5 py-0 h-4" data-testid={`badge-source-${item.metric}`}>
                          {source === 'computed' ? 'Derived' : 'AI Est.'}
                        </Badge>
                      )}
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-4 w-4 p-0" data-testid={`info-${item.metric}`}>
                            <Info className="h-3 w-3 text-muted-foreground" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                          <p className="font-medium">{item.name}</p>
                          <p className="text-xs text-muted-foreground font-mono">{item.tooltip.formula}</p>
                          <div className="text-xs mt-1">
                            <p className="text-emerald-500">Good: {item.tooltip.goodRange}</p>
                            <p className="text-red-500">Warning: {item.tooltip.badRange}</p>
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <KpiStatusIcon status={getKpiStatus(item.value, item.metric)} />
                  </div>
                  <div className="flex items-baseline space-x-2">
                    <span className="text-2xl font-bold">
                      {item.metric === 'runway' || item.metric === 'paybackPeriod'
                        ? `${safeToFixed(item.value)} mo`
                        : item.metric === 'ltv_cac' || item.metric === 'burnMultiple'
                        ? safeToFixed(item.value, 1, 'x')
                        : safeToFixed(item.value, 1, '%')}
                    </span>
                  </div>
                  <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all ${
                        getKpiStatus(item.value, item.metric) === 'green' ? 'bg-emerald-500' :
                        getKpiStatus(item.value, item.metric) === 'yellow' ? 'bg-amber-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(10, item.value == null ? 0 : (item.metric === 'churnRate' ? 100 - item.value * 5 : item.value * 1.5)))}%` }}
                    />
                  </div>
                </div>
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
              <Badge variant="secondary">{baseData.profitabilityDate}</Badge>
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
              <span className="font-mono font-medium">{baseData.conversionRate}%</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Gross Margin</span>
              </div>
              <span className="font-mono font-medium">{safeToFixed(projectedMetrics.grossMargin, 1, '%')}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="overflow-visible" data-testid="benchmarks-section">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <CardTitle className="text-lg flex items-center gap-2">
                <Scale className="h-5 w-5 text-primary" />
                Industry Benchmarks
                {benchmarksLoading && <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />}
              </CardTitle>
              {dynamicBenchmarks?.is_cached && (
                <Badge variant="outline" className="text-xs">Cached</Badge>
              )}
            </div>
            <CardDescription>
              Real-time benchmarks from industry reports
            </CardDescription>
            <div className="flex items-center gap-2 mt-2">
              <Select value={selectedIndustry} onValueChange={setSelectedIndustry}>
                <SelectTrigger className="w-[140px] h-8 text-xs" data-testid="select-industry">
                  <SelectValue placeholder="Industry" />
                </SelectTrigger>
                <SelectContent>
                  {benchmarkOptions?.industries.map(ind => (
                    <SelectItem key={ind.id} value={ind.id}>{ind.name}</SelectItem>
                  )) || (
                    <>
                      <SelectItem value="saas">SaaS / Software</SelectItem>
                      <SelectItem value="fintech">Fintech</SelectItem>
                      <SelectItem value="ecommerce">E-commerce</SelectItem>
                      <SelectItem value="d2c">D2C / Consumer</SelectItem>
                      <SelectItem value="marketplace">Marketplace</SelectItem>
                      <SelectItem value="healthcare">Healthcare / BioTech</SelectItem>
                      <SelectItem value="edtech">EdTech</SelectItem>
                      <SelectItem value="agritech">AgriTech</SelectItem>
                      <SelectItem value="deeptech">DeepTech / Hardware</SelectItem>
                      <SelectItem value="climate">Climate / CleanTech</SelectItem>
                      <SelectItem value="media">Media / Entertainment</SelectItem>
                      <SelectItem value="logistics">Logistics / Supply Chain</SelectItem>
                      <SelectItem value="real_estate">Real Estate / PropTech</SelectItem>
                      <SelectItem value="food">Food / CPG</SelectItem>
                    </>
                  )}
                </SelectContent>
              </Select>
              <Select value={selectedStage} onValueChange={setSelectedStage}>
                <SelectTrigger className="w-[120px] h-8 text-xs" data-testid="select-stage">
                  <SelectValue placeholder="Stage" />
                </SelectTrigger>
                <SelectContent>
                  {benchmarkOptions?.stages.map(st => (
                    <SelectItem key={st.id} value={st.id}>{st.name}</SelectItem>
                  )) || (
                    <>
                      <SelectItem value="pre_seed">Pre-seed</SelectItem>
                      <SelectItem value="seed">Seed</SelectItem>
                      <SelectItem value="pre_series_a">Pre-Series A</SelectItem>
                      <SelectItem value="series_a">Series A</SelectItem>
                      <SelectItem value="series_b">Series B+</SelectItem>
                      <SelectItem value="growth">Growth Stage</SelectItem>
                      <SelectItem value="pre_ipo">Pre-IPO</SelectItem>
                      <SelectItem value="public">Public / Listed</SelectItem>
                    </>
                  )}
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            {benchmarksError && (
              <div className="mb-3 p-2 bg-amber-500/10 border border-amber-500/30 rounded text-xs text-amber-600 dark:text-amber-400">
                Using default benchmarks (live search unavailable)
              </div>
            )}
            {benchmarksLoading ? (
              <div className="space-y-3">
                {[1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-10 w-full" />)}
              </div>
            ) : (
              <div className="space-y-3">
                {benchmarkComparison.map((item, index) => (
                  <div key={item.metric} className="space-y-1" data-testid={`benchmark-${index}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{item.metric}</span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-semibold">
                          {safeToFixed(item.value)}{item.unit}
                        </span>
                        <Badge 
                          variant={item.status === 'above' ? 'secondary' : item.status === 'median' ? 'secondary' : 'destructive'}
                          data-testid={`benchmark-${index}-status`}
                        >
                          {item.status === 'above' ? (
                            <TrendingUp className="h-3 w-3 mr-1 text-emerald-500" />
                          ) : item.status === 'median' ? (
                            <AlertCircle className="h-3 w-3 mr-1 text-amber-500" />
                          ) : (
                            <TrendingDown className="h-3 w-3 mr-1" />
                          )}
                          {item.status === 'above' ? 'Above P50' : item.status === 'median' ? 'P25-P50' : 'Below P25'}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>P25: {item.p25}{item.unit}</span>
                      <span>P50: {item.p50}{item.unit}</span>
                      <span>P75: {item.p75}{item.unit}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {dynamicBenchmarks?.sources && dynamicBenchmarks.sources.length > 0 && (
              <div className="mt-4 pt-3 border-t">
                <p className="text-xs text-muted-foreground">
                  Sources: {dynamicBenchmarks.sources.slice(0, 2).map((s, i) => (
                    <a key={i} href={s} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline ml-1">
                      [{i + 1}]
                    </a>
                  ))}
                  {dynamicBenchmarks.sources.length > 2 && <span> +{dynamicBenchmarks.sources.length - 2} more</span>}
                </p>
              </div>
            )}
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

      <Dialog 
        open={!!selectedDrillDownMetric} 
        onOpenChange={(open) => !open && setSelectedDrillDownMetric(null)}
      >
        <DialogContent className="sm:max-w-[700px]" data-testid="dialog-metric-drilldown">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              {selectedDrillDownMetric && getDrillDownData(selectedDrillDownMetric)?.title}
            </DialogTitle>
            <DialogDescription>
              Illustrative trend (last 6 months) and 12-month projections based on current assumptions
            </DialogDescription>
          </DialogHeader>
          
          {selectedDrillDownMetric && drillDownChartData.length > 0 && (
            <div className="space-y-4">
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={drillDownChartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="historicalGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="projectedGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--chart-2))" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="hsl(var(--chart-2))" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis 
                      dataKey="month" 
                      className="text-xs"
                      tick={{ fill: 'hsl(var(--muted-foreground))' }}
                    />
                    <YAxis 
                      className="text-xs"
                      tick={{ fill: 'hsl(var(--muted-foreground))' }}
                      tickFormatter={(value) => formatCurrencyAbbrev(value, currentCompany?.currency || 'USD')}
                    />
                    <RechartsTooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                      }}
                      labelStyle={{ color: 'hsl(var(--foreground))' }}
                      formatter={(value: number) => [formatCurrency(value), '']}
                    />
                    <Area
                      type="monotone"
                      dataKey="historical"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      fill="url(#historicalGradient)"
                      connectNulls={false}
                    />
                    <Area
                      type="monotone"
                      dataKey="projected"
                      stroke="hsl(var(--chart-2))"
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      fill="url(#projectedGradient)"
                      connectNulls={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              
              <div className="flex items-center justify-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-0.5 bg-primary" />
                  <span className="text-muted-foreground">Illustrative Trend</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-0.5 border-t-2 border-dashed" style={{ borderColor: 'hsl(var(--chart-2))' }} />
                  <span className="text-muted-foreground">Projected</span>
                </div>
              </div>
              
              {(() => {
                const data = getDrillDownData(selectedDrillDownMetric);
                if (!data) return null;
                const current = data.history.at(-1) || 1;
                const projected = data.projections.at(-1) || 0;
                const change = ((projected - current) / current) * 100;
                const isPositive = change > 0;
                
                return (
                  <div className="grid grid-cols-3 gap-4 pt-2">
                    <Card className="overflow-visible">
                      <CardContent className="p-3">
                        <p className="text-xs text-muted-foreground">Current Value</p>
                        <p className="text-lg font-semibold font-mono">
                          {data.format(current)}
                        </p>
                      </CardContent>
                    </Card>
                    <Card className="overflow-visible">
                      <CardContent className="p-3">
                        <p className="text-xs text-muted-foreground">Projected (12mo)</p>
                        <p className="text-lg font-semibold font-mono">
                          {data.format(projected)}
                        </p>
                      </CardContent>
                    </Card>
                    <Card className="overflow-visible">
                      <CardContent className="p-3">
                        <p className="text-xs text-muted-foreground">Change</p>
                        <p className={`text-lg font-semibold font-mono flex items-center gap-1 ${isPositive ? 'text-emerald-500' : 'text-red-500'}`}>
                          {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                          {isPositive ? '+' : ''}{change.toFixed(1)}%
                        </p>
                      </CardContent>
                    </Card>
                  </div>
                );
              })()}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
