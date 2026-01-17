import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { MetricCard } from '@/components/MetricCard';
import { BenchmarkBar } from '@/components/BenchmarkBar';
import { MetricDetailModal } from '@/components/MetricDetailModal';
import { ExportButton } from '@/components/ExportButton';
import { InfoTooltip } from '@/components/InfoTooltip';
import { AlertTriangle, TrendingUp, RefreshCw, Info, HelpCircle, ChevronDown, ChevronUp, Lightbulb, CheckCircle } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useTruthScan, useRunTruthScan } from '@/api/hooks';
import { METRIC_DEFINITIONS, getMetricDefinition, MetricDefinition } from '@/lib/metricDefinitions';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { formatTruthScanForExport } from '@/lib/exportUtils';
import { formatCurrencyAbbrev, formatPercent as formatPct } from '@/lib/utils';

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

export default function TruthScanPage() {
  const { currentCompany } = useFounderStore();
  const { data: truthScan, isLoading } = useTruthScan(currentCompany?.id || null);
  const runTruthScanMutation = useRunTruthScan();
  
  const [selectedMetric, setSelectedMetric] = useState<{
    definition: MetricDefinition | null;
    value?: number | string;
    benchmark?: { value: number; p25: number; p50: number; p75: number };
  }>({ definition: null });
  
  const [qualityExpanded, setQualityExpanded] = useState(false);
  const [confidenceExpanded, setConfidenceExpanded] = useState(false);
  
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
  
  const metrics = truthScan?.metrics || {};
  const flags = truthScan?.flags || [];
  const benchmarks = truthScan?.benchmark_comparisons || [];
  const confidence = truthScan?.data_confidence_score || 0;
  const qualityOfGrowth = truthScan?.quality_of_growth_index || 0;
  
  const formatCurrency = (value: number | null | undefined) => {
    return formatCurrencyAbbrev(value, currentCompany?.currency || 'USD');
  };
  
  const formatPercent = (value: number | null | undefined) => {
    return formatPct(value);
  };
  
  const handleRefresh = async () => {
    if (!currentCompany) return;
    await runTruthScanMutation.mutateAsync(currentCompany.id);
  };
  
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Truth Scan</h1>
          <p className="text-muted-foreground">24 metrics benchmarked against industry standards</p>
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
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('mrr') || null, 
                  value: formatCurrency(metrics.monthly_revenue) 
                })}
              />
              <MetricCard 
                title={metrics.is_profitable ? "Monthly Surplus" : "Net Burn"} 
                value={formatCurrency(metrics.is_profitable ? Math.abs(metrics.net_burn) : metrics.net_burn)} 
                testId="metric-burn"
                tooltip={metrics.is_profitable ? "Monthly surplus (revenue exceeds expenses)" : METRIC_DEFINITIONS.net_burn?.shortDescription}
                variant={metrics.is_profitable ? "success" : metrics.net_burn > 0 ? "danger" : "default"}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('net_burn') || null, 
                  value: formatCurrency(metrics.is_profitable ? Math.abs(metrics.net_burn) : metrics.net_burn) 
                })}
              />
              <MetricCard 
                title="Cash Balance" 
                value={formatCurrency(metrics.cash_balance)} 
                testId="metric-cash"
                tooltip={METRIC_DEFINITIONS.cash_balance?.shortDescription}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('cash_balance') || null, 
                  value: formatCurrency(metrics.cash_balance) 
                })}
              />
              <MetricCard 
                title="Runway (P50)" 
                value={metrics.runway_sustainable ? "Sustainable" : `${metrics.runway_p50?.toFixed(1) || 0} months`} 
                testId="metric-runway"
                tooltip={metrics.runway_sustainable ? "Company is cash-flow positive and self-sustaining" : METRIC_DEFINITIONS.runway_months?.shortDescription}
                variant={metrics.runway_sustainable ? "success" : (metrics.runway_p50 && metrics.runway_p50 < 12 ? "danger" : "default")}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('runway_months') || null, 
                  value: metrics.runway_sustainable ? "Sustainable" : `${metrics.runway_p50?.toFixed(1) || 0} months` 
                })}
              />
              <MetricCard 
                title="Gross Margin" 
                value={formatPercent(metrics.gross_margin)} 
                testId="metric-margin"
                tooltip={METRIC_DEFINITIONS.gross_margin?.shortDescription}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('gross_margin') || null, 
                  value: formatPercent(metrics.gross_margin) 
                })}
              />
              <MetricCard 
                title="Revenue Growth" 
                value={formatPercent(metrics.revenue_growth_mom)} 
                subtitle="MoM" 
                testId="metric-growth"
                tooltip={METRIC_DEFINITIONS.revenue_growth_mom?.shortDescription}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('revenue_growth_mom') || null, 
                  value: formatPercent(metrics.revenue_growth_mom) 
                })}
              />
              <MetricCard 
                title="Burn Multiple" 
                value={typeof metrics.burn_multiple === 'number' ? metrics.burn_multiple.toFixed(1) : 'N/A'} 
                testId="metric-burn-mult"
                tooltip={METRIC_DEFINITIONS.burn_multiple?.shortDescription}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('burn_multiple') || null, 
                  value: typeof metrics.burn_multiple === 'number' ? metrics.burn_multiple.toFixed(1) : 'N/A' 
                })}
              />
              <MetricCard 
                title="Operating Margin" 
                value={formatPercent(metrics.operating_margin)} 
                testId="metric-op-margin"
                tooltip={METRIC_DEFINITIONS.operating_margin?.shortDescription}
                onClick={() => setSelectedMetric({ 
                  definition: getMetricDefinition('operating_margin') || null, 
                  value: formatPercent(metrics.operating_margin) 
                })}
              />
            </>
          )}
        </div>
      </div>
      
      {benchmarks.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-semibold">Benchmark Comparisons</h2>
            <Tooltip>
              <TooltipTrigger asChild>
                <button type="button" className="p-0.5" data-testid="tooltip-benchmarks">
                  <HelpCircle className="h-4 w-4 text-muted-foreground" />
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p className="text-sm">
                  Compare your metrics against industry benchmarks. P25/P50/P75 represent the 25th, 50th (median), and 75th percentiles of comparable companies.
                </p>
              </TooltipContent>
            </Tooltip>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {benchmarks.map((bench: any) => (
              <Card key={bench.metric} className="overflow-visible">
                <CardContent className="p-4">
                  <BenchmarkBar
                    metric={bench.metric.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                    value={bench.value}
                    p25={bench.p25}
                    p50={bench.p50}
                    p75={bench.p75}
                    direction={bench.direction}
                    testId={`benchmark-${bench.metric}`}
                  />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
      
      {flags.filter((f: any) => f.severity !== 'high').length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Warnings & Insights</h2>
          <div className="space-y-2">
            {flags.filter((f: any) => f.severity !== 'high').map((flag: any, i: number) => (
              <Card key={i} className="overflow-visible">
                <CardContent className="p-4 flex items-start gap-3">
                  <AlertTriangle className={`h-5 w-5 mt-0.5 ${flag.severity === 'medium' ? 'text-amber-500' : 'text-muted-foreground'}`} />
                  <div>
                    <p className="font-medium">{flag.title}</p>
                    <p className="text-sm text-muted-foreground">{flag.description}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
      
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
