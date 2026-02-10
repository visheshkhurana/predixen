import { useState, useMemo, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { MetricCard } from '@/components/MetricCard';
import { MetricDetailModal } from '@/components/MetricDetailModal';
import { ExportButton } from '@/components/ExportButton';
import { InfoTooltip } from '@/components/InfoTooltip';
import { UnitEconomicsPanel } from '@/components/UnitEconomicsPanel';
import { BurnBreakdownChart } from '@/components/BurnBreakdownChart';
import { ScenarioRunwayToggle } from '@/components/ScenarioRunwayToggle';
import { CashFlowForecast } from '@/components/CashFlowForecast';
import { HeadcountPanel } from '@/components/HeadcountPanel';
import { AlertTriangle, TrendingUp, RefreshCw, Info, HelpCircle, ChevronDown, ChevronUp, Lightbulb, CheckCircle, Pencil, Building2, X, Check, Globe, Loader2, ExternalLink } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useTruthScan, useRunTruthScan } from '@/api/hooks';
import { useFinancialMetrics } from '@/hooks/useFinancialMetrics';
import { METRIC_DEFINITIONS, getMetricDefinition, MetricDefinition } from '@/lib/metricDefinitions';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { formatTruthScanForExport } from '@/lib/exportUtils';
import { formatCurrencyAbbrev, formatPercent as formatPct } from '@/lib/utils';
import { generateMockTrendData } from '@/components/Sparkline';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import { useToast } from '@/hooks/use-toast';

const STATUS_EXPLANATIONS = {
  critical: {
    label: 'Critical',
    description: 'This metric requires immediate attention. Values in this range indicate a significant risk to business operations or survival.',
    color: 'text-red-500',
  },
  warning: {
    label: 'Caution',
    description: 'This metric is below optimal levels. Consider taking action to improve this area before it becomes critical.',
    color: 'text-amber-500',
  },
  healthy: {
    label: 'Healthy',
    description: 'This metric is within a healthy range. Continue monitoring to maintain performance.',
    color: 'text-emerald-500',
  },
};

const QUALITY_OF_GROWTH_EXPLANATION = {
  title: 'Quality of Growth Index',
  description: 'A composite score (0-100) that evaluates how sustainably your company is growing. It weighs factors like revenue growth efficiency, unit economics, capital efficiency, and risk exposure.',
  factors: [
    'Revenue growth rate and consistency',
    'Burn multiple and capital efficiency',
    'Gross margin health',
    'Customer concentration risk',
    'Net revenue retention',
  ],
  improvements: [
    { score: '0-40', actions: ['Focus on reducing burn rate immediately', 'Prioritize customer retention over acquisition', 'Review pricing strategy for margin improvement'] },
    { score: '41-60', actions: ['Optimize customer acquisition cost', 'Improve gross margins through pricing or cost reduction', 'Diversify customer base to reduce concentration'] },
    { score: '61-80', actions: ['Scale proven acquisition channels', 'Invest in product features that drive expansion revenue', 'Build operational efficiency'] },
    { score: '81-100', actions: ['Maintain current growth trajectory', 'Consider strategic investments for market expansion', 'Prepare for fundraising at favorable terms'] },
  ],
};

const DATA_CONFIDENCE_EXPLANATION = {
  title: 'Data Confidence Score',
  description: 'Measures how complete and reliable your uploaded financial data is. Higher scores indicate more accurate projections and benchmark comparisons.',
  factors: [
    'Number of months of historical data',
    'Consistency of data entries',
    'Presence of key financial metrics',
    'Data recency (how up-to-date)',
    'Completeness of expense categorization',
  ],
  improvements: [
    { score: '0-40', actions: ['Upload at least 6 months of financial data', 'Ensure all expense categories are properly labeled', 'Include both revenue and expense data'] },
    { score: '41-60', actions: ['Add 12+ months of historical data', 'Verify data accuracy by cross-referencing with bank statements', 'Fill in any missing monthly entries'] },
    { score: '61-80', actions: ['Upload customer-level revenue data for better retention analysis', 'Add cohort data for more accurate projections', 'Connect accounting integration for real-time updates'] },
    { score: '81-100', actions: ['Maintain regular data updates', 'Add forward-looking forecast inputs', 'Consider connecting additional data sources'] },
  ],
};

function getScoreActions(score: number, explanationData: typeof QUALITY_OF_GROWTH_EXPLANATION) {
  if (score <= 40) return explanationData.improvements[0];
  if (score <= 60) return explanationData.improvements[1];
  if (score <= 80) return explanationData.improvements[2];
  return explanationData.improvements[3];
}

interface Recommendation {
  type: 'critical' | 'warning' | 'opportunity' | 'success';
  title: string;
  description: string;
  action?: string;
}

// Helper to extract numeric value from metrics that may be objects with {value, benchmark_percentile}
function getMetricValue(metric: any): number | null {
  if (metric === null || metric === undefined) return null;
  if (typeof metric === 'number') return metric;
  if (typeof metric === 'object' && 'value' in metric) return metric.value;
  return null;
}

function generateRecommendations(metrics: any, flags: any[]): Recommendation[] {
  const recommendations: Recommendation[] = [];
  
  // Extract numeric values (some metrics may be objects with value/benchmark_percentile)
  const runwayP50 = getMetricValue(metrics.runway_p50);
  const burnMultiple = getMetricValue(metrics.burn_multiple);
  const grossMargin = getMetricValue(metrics.gross_margin);
  const ltvCacRatio = getMetricValue(metrics.ltv_cac_ratio);
  const nrr = getMetricValue(metrics.net_revenue_retention);
  const runwaySustainable = metrics.runway_sustainable === true;
  
  // Critical: Low runway
  if (runwayP50 && runwayP50 < 6 && !runwaySustainable) {
    recommendations.push({
      type: 'critical',
      title: 'Runway Below 6 Months',
      description: `With only ${runwayP50.toFixed(1)} months of runway, immediate action is needed. Consider reducing burn rate by 20-30% or accelerating fundraising conversations.`,
      action: 'Focus on survival mode: pause non-essential hiring, negotiate extended payment terms with vendors, and explore bridge financing options.'
    });
  }
  
  // Warning: High burn multiple
  if (burnMultiple && burnMultiple > 3) {
    recommendations.push({
      type: 'warning',
      title: 'Burn Multiple is Elevated',
      description: `Your burn multiple of ${burnMultiple.toFixed(1)}x means you're spending $${burnMultiple.toFixed(1)} for every $1 of new ARR. Top-tier startups maintain this below 2x.`,
      action: 'Review customer acquisition costs and focus on higher-efficiency growth channels. Consider increasing pricing or reducing sales team overhead.'
    });
  }
  
  // Warning: Low gross margin
  if (grossMargin && grossMargin < 60) {
    recommendations.push({
      type: 'warning',
      title: 'Gross Margin Below Target',
      description: `At ${grossMargin.toFixed(0)}%, your gross margin is below the 70%+ target for SaaS. This limits profitability potential and fundraising attractiveness.`,
      action: 'Review infrastructure costs, vendor contracts, and pricing strategy. Consider usage-based pricing tiers or reducing support intensity for lower-tier customers.'
    });
  }
  
  // Opportunity: Strong unit economics
  if (ltvCacRatio && ltvCacRatio >= 3) {
    recommendations.push({
      type: 'opportunity',
      title: 'Strong Unit Economics',
      description: `Your LTV:CAC ratio of ${ltvCacRatio.toFixed(1)}x indicates healthy customer economics. This is a signal to potentially accelerate growth investment.`,
      action: 'Consider increasing marketing spend on proven channels. Your unit economics can support more aggressive customer acquisition.'
    });
  }
  
  // Opportunity: High NRR
  if (nrr && nrr > 110) {
    recommendations.push({
      type: 'opportunity',
      title: 'Excellent Net Revenue Retention',
      description: `At ${nrr.toFixed(0)}% NRR, your existing customers are growing significantly. This is a competitive advantage for fundraising.`,
      action: 'Document your expansion playbook and consider hiring dedicated customer success roles to amplify this strength.'
    });
  }
  
  // Success: Profitable/sustainable
  if (runwaySustainable) {
    recommendations.push({
      type: 'success',
      title: 'Cash Flow Positive',
      description: 'Your company is generating more cash than it spends. This gives you strategic flexibility to grow on your own terms.',
      action: 'Consider whether to reinvest profits for faster growth or maintain profitability for optionality in uncertain markets.'
    });
  }
  
  // Add any flags as warnings
  flags.filter((f: any) => f.severity === 'medium').forEach((flag: any) => {
    if (flag.title && flag.description) {
      recommendations.push({
        type: 'warning',
        title: String(flag.title),
        description: String(flag.description),
        action: flag.action ? String(flag.action) : undefined
      });
    }
  });
  
  // Default recommendation if no specific ones
  if (recommendations.length === 0) {
    recommendations.push({
      type: 'success',
      title: 'Financial Health is Looking Good',
      description: 'No critical issues detected. Your metrics are within healthy ranges. Continue monitoring key indicators regularly.',
    });
    recommendations.push({
      type: 'opportunity',
      title: 'Explore Scenario Planning',
      description: 'Use the Simulation page to model different growth scenarios and understand probabilistic outcomes for fundraising conversations.',
      action: 'Run a Monte Carlo simulation with optimistic and pessimistic assumptions to prepare for board discussions.'
    });
  }
  
  return recommendations.slice(0, 5); // Limit to 5 recommendations
}

export default function TruthScanPage() {
  const { currentCompany, setCurrentCompany, financialBaseline } = useFounderStore();
  const { data: truthScan, isLoading } = useTruthScan(currentCompany?.id || null);
  const { metrics: sharedMetrics } = useFinancialMetrics();
  const runTruthScanMutation = useRunTruthScan();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  
  const [selectedMetric, setSelectedMetric] = useState<{
    definition: MetricDefinition | null;
    value?: number | string;
    benchmark?: { value: number; p25: number; p50: number; p75: number };
  }>({ definition: null });
  
  const [qualityExpanded, setQualityExpanded] = useState(false);
  const [confidenceExpanded, setConfidenceExpanded] = useState(false);
  
  // Business summary editing state
  const [isEditingSummary, setIsEditingSummary] = useState(false);
  const [summaryText, setSummaryText] = useState(currentCompany?.description || '');
  
  // Sync summary text when company changes
  useEffect(() => {
    setSummaryText(currentCompany?.description || '');
  }, [currentCompany?.description]);
  
  // Mutation to update company description
  const updateDescriptionMutation = useMutation({
    mutationFn: async (description: string) => {
      const res = await apiRequest('PUT', `/api/companies/${currentCompany?.id}`, { description });
      const contentType = res.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return res.json();
      }
      return { description };
    },
    onSuccess: (data) => {
      toast({ title: 'Business summary saved' });
      // Update current company with new description
      if (currentCompany) {
        setCurrentCompany({ ...currentCompany, description: data?.description ?? summaryText });
      }
      queryClient.invalidateQueries({ queryKey: ['/api/companies'] });
      setIsEditingSummary(false);
    },
    onError: () => {
      toast({ title: 'Failed to save', variant: 'destructive' });
    }
  });

  // State for web search results
  const [webSearchCitations, setWebSearchCitations] = useState<string[]>([]);
  
  // Mutation to search web for company info
  const webSearchMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest('POST', `/api/companies/${currentCompany?.id}/web-search`, {});
      return res.json();
    },
    onSuccess: (data) => {
      if (data.description) {
        setSummaryText(data.description);
        setWebSearchCitations(data.citations || []);
        setIsEditingSummary(true);
        toast({ title: 'Company info found! Review and save the summary.' });
      } else {
        toast({ title: 'No information found', variant: 'destructive' });
      }
    },
    onError: (error: any) => {
      const message = error?.message || 'Web search failed';
      if (message.includes('not configured')) {
        toast({ title: 'Perplexity API key not configured', description: 'Please add PERPLEXITY_API_KEY to secrets', variant: 'destructive' });
      } else {
        toast({ title: 'Web search failed', description: message, variant: 'destructive' });
      }
    }
  });

  const rawMetrics = truthScan?.metrics || {};
  const enhancedMetrics = useMemo(() => {
    const m = { ...rawMetrics } as Record<string, any>;
    if (financialBaseline) {
      const revenue = Number(financialBaseline.monthlyRevenue) || 0;
      const expenses = Number(financialBaseline.totalMonthlyExpenses) || 0;
      const cogs = Number(financialBaseline.expenseBreakdown?.cogs) || 0;
      const cash = Number(financialBaseline.cashOnHand) || 0;
      if (revenue > 0 && !getMetricValue(m.arr)) {
        m.arr = revenue * 12;
      }
      if (revenue > 0 && !getMetricValue(m.gross_margin)) {
        m.gross_margin = ((revenue - cogs) / revenue) * 100;
      }
      if (revenue > 0 && !getMetricValue(m.mrr)) {
        m.mrr = revenue;
      }
      if (!getMetricValue(m.runway_p50) && cash > 0 && expenses > revenue) {
        m.runway_p50 = cash / (expenses - revenue);
      }
      if (!getMetricValue(m.revenue_growth_mom) && financialBaseline.monthlyGrowthRate) {
        m.revenue_growth_mom = Number(financialBaseline.monthlyGrowthRate);
      }
    }
    return m;
  }, [rawMetrics, financialBaseline]);
  const metrics = enhancedMetrics;
  const flags = truthScan?.flags || [];
  const confidence = truthScan?.data_confidence_score || 0;
  const qualityOfGrowth = truthScan?.quality_of_growth_index || 0;

  const trendData = useMemo(() => {
    if (!truthScan?.metrics) return {} as Record<string, number[]>;
    const m = truthScan.metrics;
    // Extract numeric values from potential object structures
    const getValue = (v: any): number => {
      if (v === null || v === undefined) return 0;
      if (typeof v === 'number') return v;
      if (typeof v === 'object' && 'value' in v) return getValue(v.value);
      return 0;
    };
    return {
      monthly_revenue: generateMockTrendData(getValue(m.monthly_revenue) || 100000, 6, 0.08),
      net_burn: generateMockTrendData(Math.abs(getValue(m.net_burn) || 50000), 6, 0.12),
      cash_balance: generateMockTrendData(getValue(m.cash_balance) || 500000, 6, 0.05),
      gross_margin: generateMockTrendData((getValue(m.gross_margin) || 0.65) * 100, 6, 0.03),
      revenue_growth: generateMockTrendData((getValue(m.revenue_growth_mom) || 0.1) * 100, 6, 0.15),
      burn_multiple: generateMockTrendData(getValue(m.burn_multiple) || 2, 6, 0.1),
      operating_margin: generateMockTrendData((getValue(m.operating_margin) || -0.2) * 100 + 50, 6, 0.08),
    };
  }, [truthScan?.metrics]);
  
  if (!currentCompany) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Select a company to view Truth Scan</p>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  // Extract numeric value from potential object structures
  const extractValue = (v: any): number | null => {
    if (v === null || v === undefined) return null;
    if (typeof v === 'number') return v;
    if (typeof v === 'object' && 'value' in v) return extractValue(v.value);
    return null;
  };
  
  const formatCurrency = (value: any) => {
    const numValue = extractValue(value);
    return formatCurrencyAbbrev(numValue, currentCompany?.currency || 'USD');
  };
  
  const formatPercent = (value: any) => {
    const numValue = extractValue(value);
    return formatPct(numValue);
  };
  
  const handleRefresh = async () => {
    if (!currentCompany) return;
    await runTruthScanMutation.mutateAsync(currentCompany.id);
  };
  
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Health Check</h1>
          <p className="text-muted-foreground">24 financial metrics for startup health assessment</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {truthScan && (
            <ExportButton
              data={truthScan}
              filename={`truth-scan-${currentCompany.name.toLowerCase().replace(/\s+/g, '-')}`}
              formatForCSV={formatTruthScanForExport}
              pdfTitle={`Truth Scan Report - ${currentCompany.name}`}
              showPDF={true}
              testId="export-truth-scan"
            />
          )}
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={runTruthScanMutation.isPending}
            data-testid="button-refresh-truth"
            aria-label="Refresh Truth Scan analysis"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${runTruthScanMutation.isPending ? 'animate-spin' : ''}`} aria-hidden="true" />
            Refresh Scan
          </Button>
        </div>
      </div>
      
      {flags.filter((f: any) => f.severity === 'high').length > 0 && (
        <Card className="border-destructive/50 bg-destructive/10">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-destructive mt-0.5" />
              <div className="space-y-2">
                <h3 className="font-medium text-destructive">Critical Flags</h3>
                {flags.filter((f: any) => f.severity === 'high').map((flag: any, i: number) => (
                  <div key={i} className="text-sm">
                    <span className="font-medium">{flag.title}:</span>{' '}
                    <span className="text-muted-foreground">{flag.description}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      
      <Card className="overflow-visible bg-secondary/30">
        <CardContent className="p-4">
          <div className="flex items-center gap-6 flex-wrap">
            <span className="text-sm font-medium text-muted-foreground">Status Legend:</span>
            <div className="flex items-center gap-4 flex-wrap">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-1.5 cursor-help" data-testid="legend-critical">
                    <Badge variant="destructive" className="text-xs">Critical</Badge>
                    <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="font-medium text-red-500 mb-1">{STATUS_EXPLANATIONS.critical.label}</p>
                  <p className="text-sm">{STATUS_EXPLANATIONS.critical.description}</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-1.5 cursor-help" data-testid="legend-warning">
                    <Badge variant="secondary" className="bg-amber-500/20 text-amber-400 text-xs">Caution</Badge>
                    <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="font-medium text-amber-500 mb-1">{STATUS_EXPLANATIONS.warning.label}</p>
                  <p className="text-sm">{STATUS_EXPLANATIONS.warning.description}</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-1.5 cursor-help" data-testid="legend-healthy">
                    <Badge variant="secondary" className="bg-emerald-500/20 text-emerald-400 text-xs">Healthy</Badge>
                    <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="font-medium text-emerald-500 mb-1">{STATUS_EXPLANATIONS.healthy.label}</p>
                  <p className="text-sm">{STATUS_EXPLANATIONS.healthy.description}</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Collapsible open={qualityExpanded} onOpenChange={setQualityExpanded}>
          <Card className="overflow-visible">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-primary" />
                  Quality of Growth Index
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button type="button" className="p-0.5" data-testid="tooltip-quality-index">
                        <HelpCircle className="h-4 w-4 text-muted-foreground" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p className="text-sm">{QUALITY_OF_GROWTH_EXPLANATION.description}</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="icon" data-testid="button-expand-quality">
                    {qualityExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                </CollapsibleTrigger>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-20 w-32" />
              ) : (
                <>
                  <div className="text-5xl font-bold font-mono" data-testid="text-quality-index">
                    {qualityOfGrowth}
                    <span className="text-xl text-muted-foreground">/100</span>
                  </div>
                  <div className="w-full h-2 bg-secondary rounded-full mt-3 overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all ${
                        qualityOfGrowth >= 80 ? 'bg-emerald-500' : 
                        qualityOfGrowth >= 60 ? 'bg-blue-500' : 
                        qualityOfGrowth >= 40 ? 'bg-amber-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${qualityOfGrowth}%` }}
                    />
                  </div>
                  <CollapsibleContent className="mt-4 space-y-4">
                    <div>
                      <p className="text-sm font-medium mb-2">How this score is calculated:</p>
                      <ul className="space-y-1">
                        {QUALITY_OF_GROWTH_EXPLANATION.factors.map((factor, i) => (
                          <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                            <CheckCircle className="h-3.5 w-3.5 text-primary mt-0.5 shrink-0" />
                            {factor}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="bg-secondary/50 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <Lightbulb className="h-4 w-4 text-amber-500" />
                        <p className="text-sm font-medium">Actions to improve (Score: {getScoreActions(qualityOfGrowth, QUALITY_OF_GROWTH_EXPLANATION).score})</p>
                      </div>
                      <ul className="space-y-1">
                        {getScoreActions(qualityOfGrowth, QUALITY_OF_GROWTH_EXPLANATION).actions.map((action, i) => (
                          <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                            <span className="text-primary font-mono">{i + 1}.</span>
                            {action}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </CollapsibleContent>
                </>
              )}
            </CardContent>
          </Card>
        </Collapsible>
        
        <Collapsible open={confidenceExpanded} onOpenChange={setConfidenceExpanded}>
          <Card className="overflow-visible">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  Data Confidence Score
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button type="button" className="p-0.5" data-testid="tooltip-confidence-score">
                        <HelpCircle className="h-4 w-4 text-muted-foreground" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p className="text-sm">{DATA_CONFIDENCE_EXPLANATION.description}</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="icon" data-testid="button-expand-confidence">
                    {confidenceExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                </CollapsibleTrigger>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-20 w-32" />
              ) : (
                <>
                  <div className="text-5xl font-bold font-mono" data-testid="text-confidence">
                    {confidence}
                    <span className="text-xl text-muted-foreground">/100</span>
                  </div>
                  <div className="w-full h-2 bg-secondary rounded-full mt-3 overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all ${
                        confidence >= 80 ? 'bg-emerald-500' : 
                        confidence >= 60 ? 'bg-amber-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${confidence}%` }}
                    />
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    {confidence < 60 && (
                      <Badge variant="destructive">Upload more data to improve</Badge>
                    )}
                    {confidence >= 60 && confidence < 80 && (
                      <Badge className="bg-amber-500/20 text-amber-400">Good - could be improved</Badge>
                    )}
                    {confidence >= 80 && (
                      <Badge className="bg-emerald-500/20 text-emerald-400">Excellent data quality</Badge>
                    )}
                  </div>
                  <CollapsibleContent className="mt-4 space-y-4">
                    <div>
                      <p className="text-sm font-medium mb-2">Factors affecting this score:</p>
                      <ul className="space-y-1">
                        {DATA_CONFIDENCE_EXPLANATION.factors.map((factor, i) => (
                          <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                            <CheckCircle className="h-3.5 w-3.5 text-primary mt-0.5 shrink-0" />
                            {factor}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="bg-secondary/50 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <Lightbulb className="h-4 w-4 text-amber-500" />
                        <p className="text-sm font-medium">Actions to improve (Score: {getScoreActions(confidence, DATA_CONFIDENCE_EXPLANATION).score})</p>
                      </div>
                      <ul className="space-y-1">
                        {getScoreActions(confidence, DATA_CONFIDENCE_EXPLANATION).actions.map((action, i) => (
                          <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                            <span className="text-primary font-mono">{i + 1}.</span>
                            {action}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </CollapsibleContent>
                </>
              )}
            </CardContent>
          </Card>
        </Collapsible>
      </div>
      
      {/* Business Summary Section */}
      <Card className="overflow-visible">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-primary" />
              Business Summary
            </div>
            <div className="flex items-center gap-2">
              {!isEditingSummary && (
                <>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => webSearchMutation.mutate()}
                        disabled={webSearchMutation.isPending}
                        data-testid="button-ai-web-search"
                      >
                        {webSearchMutation.isPending ? (
                          <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                        ) : (
                          <Globe className="h-4 w-4 mr-1" />
                        )}
                        AI Web Search
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-sm">Search the web for company information using AI</p>
                    </TooltipContent>
                  </Tooltip>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => setIsEditingSummary(true)}
                    data-testid="button-edit-summary"
                  >
                    <Pencil className="h-4 w-4 mr-1" />
                    Edit
                  </Button>
                </>
              )}
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isEditingSummary ? (
            <div className="space-y-3">
              <Textarea 
                value={summaryText}
                onChange={(e) => setSummaryText(e.target.value)}
                placeholder="Describe your company, product, market, and key value proposition..."
                className="min-h-[120px]"
                data-testid="textarea-summary"
              />
              {webSearchCitations.length > 0 && (
                <div className="p-3 bg-secondary/30 rounded-lg">
                  <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                    <Globe className="h-3 w-3" />
                    Sources from web search:
                  </p>
                  <div className="space-y-1">
                    {webSearchCitations.slice(0, 5).map((url, i) => (
                      <a 
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary hover:underline flex items-center gap-1 truncate"
                      >
                        <ExternalLink className="h-3 w-3 shrink-0" />
                        <span className="truncate">{url}</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex gap-2 justify-end">
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => {
                    setSummaryText(currentCompany?.description || '');
                    setWebSearchCitations([]);
                    setIsEditingSummary(false);
                  }}
                  data-testid="button-cancel-summary"
                >
                  <X className="h-4 w-4 mr-1" />
                  Cancel
                </Button>
                <Button 
                  size="sm" 
                  onClick={() => {
                    updateDescriptionMutation.mutate(summaryText);
                    setWebSearchCitations([]);
                  }}
                  disabled={updateDescriptionMutation.isPending}
                  data-testid="button-save-summary"
                >
                  <Check className="h-4 w-4 mr-1" />
                  {updateDescriptionMutation.isPending ? 'Saving...' : 'Save'}
                </Button>
              </div>
            </div>
          ) : (
            <div>
              {currentCompany?.description ? (
                <p className="text-sm text-muted-foreground leading-relaxed" data-testid="text-summary">
                  {currentCompany.description}
                </p>
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <Building2 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No business summary yet.</p>
                  <p className="text-xs">Add a description to help contextualize your metrics.</p>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="mt-3"
                    onClick={() => setIsEditingSummary(true)}
                    data-testid="button-add-summary"
                  >
                    <Pencil className="h-4 w-4 mr-1" />
                    Add Summary
                  </Button>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
      
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Key Metrics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {isLoading ? (
            Array(8).fill(0).map((_, i) => (
              <Card key={i} className="overflow-visible">
                <CardContent className="p-4">
                  <Skeleton className="h-4 w-20 mb-2" />
                  <Skeleton className="h-8 w-16" />
                </CardContent>
              </Card>
            ))
          ) : (
            <>
              <MetricCard 
                title="Monthly Revenue" 
                value={formatCurrency(metrics.monthly_revenue)} 
                testId="metric-revenue"
                tooltip={METRIC_DEFINITIONS.mrr?.shortDescription}
                trendData={trendData.monthly_revenue}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('mrr') || null, 
                  value: formatCurrency(metrics.monthly_revenue) 
                })}
              />
              <MetricCard 
                title={metrics.is_profitable ? "Monthly Surplus" : "Net Burn"} 
                value={formatCurrency(metrics.is_profitable ? Math.abs(extractValue(metrics.net_burn) || 0) : extractValue(metrics.net_burn))} 
                testId="metric-burn"
                tooltip={metrics.is_profitable ? "Monthly surplus (revenue exceeds expenses)" : METRIC_DEFINITIONS.net_burn?.shortDescription}
                variant={metrics.is_profitable ? "success" : (extractValue(metrics.net_burn) || 0) > 0 ? "danger" : "default"}
                trendData={trendData.net_burn}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('net_burn') || null, 
                  value: formatCurrency(metrics.is_profitable ? Math.abs(extractValue(metrics.net_burn) || 0) : extractValue(metrics.net_burn)) 
                })}
              />
              <MetricCard 
                title="Cash Balance" 
                value={formatCurrency(metrics.cash_balance)} 
                testId="metric-cash"
                tooltip={METRIC_DEFINITIONS.cash_balance?.shortDescription}
                trendData={trendData.cash_balance}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('cash_balance') || null, 
                  value: formatCurrency(metrics.cash_balance) 
                })}
              />
              <MetricCard 
                title="Runway (P50)" 
                value={(() => {
                  if (metrics.runway_sustainable) return "Sustainable";
                  const tsRunway = extractValue(metrics.runway_p50);
                  const runway = (tsRunway && tsRunway > 0) ? tsRunway : (sharedMetrics.runway !== Infinity ? sharedMetrics.runway : 0);
                  return `${runway.toFixed(1)} months`;
                })()} 
                testId="metric-runway"
                tooltip={metrics.runway_sustainable ? "Company is cash-flow positive and self-sustaining" : METRIC_DEFINITIONS.runway_months?.shortDescription}
                variant={(() => {
                  if (metrics.runway_sustainable) return "success" as const;
                  const tsRunway = extractValue(metrics.runway_p50);
                  const runway = (tsRunway && tsRunway > 0) ? tsRunway : (sharedMetrics.runway !== Infinity ? sharedMetrics.runway : 0);
                  return runway < 12 ? "danger" as const : "default" as const;
                })()}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('runway_months') || null, 
                  value: (() => {
                    if (metrics.runway_sustainable) return "Sustainable";
                    const tsRunway = extractValue(metrics.runway_p50);
                    const runway = (tsRunway && tsRunway > 0) ? tsRunway : (sharedMetrics.runway !== Infinity ? sharedMetrics.runway : 0);
                    return `${runway.toFixed(1)} months`;
                  })()
                })}
              />
              <MetricCard 
                title="Gross Margin" 
                value={formatPercent(metrics.gross_margin)} 
                testId="metric-margin"
                tooltip={METRIC_DEFINITIONS.gross_margin?.shortDescription}
                trendData={trendData.gross_margin}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('gross_margin') || null, 
                  value: formatPercent(metrics.gross_margin) 
                })}
              />
              <MetricCard 
                title="Revenue Growth" 
                value={(() => {
                  const val = extractValue(metrics.revenue_growth_mom);
                  return val !== null ? formatPercent(val) : 'N/A';
                })()} 
                subtitle={extractValue(metrics.revenue_growth_mom) === 0 ? "Need 2+ months data" : "MoM"} 
                testId="metric-growth"
                tooltip={
                  extractValue(metrics.revenue_growth_mom) === 0 || extractValue(metrics.revenue_growth_mom) === null
                    ? "Revenue growth requires at least 2 months of data to calculate month-over-month change."
                    : METRIC_DEFINITIONS.revenue_growth_mom?.shortDescription
                }
                variant={extractValue(metrics.revenue_growth_mom) === 0 ? "default" : undefined}
                trendData={trendData.revenue_growth}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('revenue_growth_mom') || null, 
                  value: formatPercent(metrics.revenue_growth_mom) 
                })}
              />
              <MetricCard 
                title="Burn Multiple" 
                value={(() => {
                  const val = extractValue(metrics.burn_multiple);
                  if (val !== null && typeof val === 'number') return `${val.toFixed(1)}x`;
                  return metrics.runway_sustainable ? 'Profitable' : 'N/A';
                })()} 
                testId="metric-burn-mult"
                tooltip={(() => {
                  const val = extractValue(metrics.burn_multiple);
                  if (val === null) {
                    return metrics.runway_sustainable
                      ? "Company is profitable - no burn multiple applicable."
                      : "Burn multiple = Net Burn ÷ Net New ARR. Requires positive ARR growth to calculate.";
                  }
                  return METRIC_DEFINITIONS.burn_multiple?.shortDescription;
                })()}
                variant={(() => {
                  const val = extractValue(metrics.burn_multiple);
                  if (metrics.runway_sustainable) return "success";
                  if (val !== null && val <= 2) return "success";
                  if (val !== null && val > 3) return "danger";
                  return undefined;
                })()}
                trendData={trendData.burn_multiple}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('burn_multiple') || null, 
                  value: (() => {
                    const val = extractValue(metrics.burn_multiple);
                    return typeof val === 'number' ? `${val.toFixed(1)}x` : 'N/A';
                  })()
                })}
              />
              <MetricCard 
                title="Operating Margin" 
                value={formatPercent(metrics.operating_margin)} 
                testId="metric-op-margin"
                tooltip={METRIC_DEFINITIONS.operating_margin?.shortDescription}
                trendData={trendData.operating_margin}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('operating_margin') || null, 
                  value: formatPercent(metrics.operating_margin) 
                })}
              />
            </>
          )}
        </div>
      </div>
      
      {/* Unit Economics Section */}
      <UnitEconomicsPanel 
        metrics={{
          cac: extractValue(metrics.cac),
          ltv: extractValue(metrics.ltv),
          ltv_cac_ratio: extractValue(metrics.ltv_cac_ratio),
          payback_months: extractValue(metrics.payback_months),
          mrr: extractValue(metrics.mrr),
          arr: extractValue(metrics.arr),
          arpu: extractValue(metrics.arpu),
          customer_count: extractValue(metrics.customer_count),
          churn_rate_customer: extractValue(metrics.churn_rate_customer),
          churn_rate_revenue: extractValue(metrics.churn_rate_revenue),
          net_revenue_retention: extractValue(metrics.net_revenue_retention),
        }}
        currency={currentCompany?.currency || 'USD'}
      />
      
      {/* Burn & Runway Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BurnBreakdownChart 
          breakdown={metrics.expense_breakdown}
          currency={currentCompany?.currency || 'USD'}
        />
        <ScenarioRunwayToggle
          currentRunway={(() => {
            const tsRunway = extractValue(metrics.runway_p50);
            return (tsRunway && tsRunway > 0) ? tsRunway : (sharedMetrics.runway !== Infinity ? sharedMetrics.runway : null);
          })()}
          currentBurn={extractValue(metrics.net_burn) || (sharedMetrics.netBurn > 0 ? sharedMetrics.netBurn : null)}
          cashBalance={extractValue(metrics.cash_balance) || (sharedMetrics.cashOnHand > 0 ? sharedMetrics.cashOnHand : null)}
          currency={currentCompany?.currency || 'USD'}
        />
      </div>
      
      {/* Cash Flow & Headcount Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CashFlowForecast 
          forecast={metrics.cash_flow_forecast}
          currency={currentCompany?.currency || 'USD'}
        />
        <HeadcountPanel
          headcount={extractValue(metrics.headcount)}
          plannedHires={extractValue(metrics.planned_hires)}
          revenuePerEmployee={extractValue(metrics.revenue_per_employee)}
          currency={currentCompany?.currency || 'USD'}
        />
      </div>
      
      {/* Insights & Recommendations Section - always shown */}
      <div className="space-y-4" data-testid="insights-section">
        <h2 className="text-xl font-semibold">Insights & Recommendations</h2>
        <div className="space-y-3">
          {generateRecommendations(metrics, flags).map((rec, i) => (
            <Card key={i} className="overflow-visible">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  {rec.type === 'critical' && <AlertTriangle className="h-5 w-5 mt-0.5 text-red-500 shrink-0" />}
                  {rec.type === 'warning' && <AlertTriangle className="h-5 w-5 mt-0.5 text-amber-500 shrink-0" />}
                  {rec.type === 'opportunity' && <Lightbulb className="h-5 w-5 mt-0.5 text-primary shrink-0" />}
                  {rec.type === 'success' && <CheckCircle className="h-5 w-5 mt-0.5 text-emerald-500 shrink-0" />}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{rec.title}</p>
                      {rec.type === 'critical' && (
                        <Badge variant="destructive" className="text-xs">Critical</Badge>
                      )}
                      {rec.type === 'warning' && (
                        <Badge className="bg-amber-500/20 text-amber-500 text-xs">Caution</Badge>
                      )}
                      {rec.type === 'opportunity' && (
                        <Badge className="bg-primary/20 text-primary text-xs">Opportunity</Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">{rec.description}</p>
                    {rec.action && (
                      <div className="mt-2 p-2 bg-secondary/50 rounded-md">
                        <p className="text-xs text-muted-foreground">
                          <span className="font-medium">Suggested action:</span> {rec.action}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
      
      <MetricDetailModal
        open={selectedMetric.definition !== null}
        onOpenChange={(open) => !open && setSelectedMetric({ definition: null })}
        metric={selectedMetric.definition}
        currentValue={selectedMetric.value}
        benchmarkData={selectedMetric.benchmark}
      />
    </div>
  );
}
