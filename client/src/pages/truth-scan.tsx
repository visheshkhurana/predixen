import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { MetricCard } from '@/components/MetricCard';
import { BenchmarkBar } from '@/components/BenchmarkBar';
import { MetricDetailModal } from '@/components/MetricDetailModal';
import { ExportButton } from '@/components/ExportButton';
import { AlertTriangle, TrendingUp, RefreshCw, Info } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useTruthScan, useRunTruthScan } from '@/api/hooks';
import { METRIC_DEFINITIONS, getMetricDefinition, MetricDefinition } from '@/lib/metricDefinitions';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { formatTruthScanForExport } from '@/lib/exportUtils';
import { formatCurrencyAbbrev, formatPercent as formatPct } from '@/lib/utils';

export default function TruthScanPage() {
  const { currentCompany } = useFounderStore();
  const { data: truthScan, isLoading } = useTruthScan(currentCompany?.id || null);
  const runTruthScanMutation = useRunTruthScan();
  
  const [selectedMetric, setSelectedMetric] = useState<{
    definition: MetricDefinition | null;
    value?: number | string;
    benchmark?: { value: number; p25: number; p50: number; p75: number };
  }>({ definition: null });
  
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
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="overflow-visible">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              Quality of Growth Index
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
                <p className="text-sm text-muted-foreground mt-2">
                  Composite score based on growth trajectory, unit economics, and risk factors
                </p>
              </>
            )}
          </CardContent>
        </Card>
        
        <Card className="overflow-visible">
          <CardHeader>
            <CardTitle>Data Confidence Score</CardTitle>
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
              </>
            )}
          </CardContent>
        </Card>
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
          <h2 className="text-xl font-semibold">Benchmark Comparisons</h2>
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
