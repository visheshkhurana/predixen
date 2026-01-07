import { useEffect, useState } from 'react';
import { useLocation } from 'wouter';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { MetricCard } from '@/components/MetricCard';
import { DecisionCard } from '@/components/DecisionCard';
import { AlertTriangle, TrendingUp, ArrowRight, RefreshCw, Sparkles, Send } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useTruthScan, useDecisions, useRunTruthScan } from '@/api/hooks';

const COPILOT_PROMPTS = [
  "How do I extend runway by 6 months?",
  "What's the riskiest assumption?",
  "What if fundraise slips 3 months?",
];

export default function OverviewPage() {
  const [, setLocation] = useLocation();
  const { currentCompany, setTruthScan, setCurrentStep } = useFounderStore();
  const { data: truthScan, isLoading: truthLoading, error: truthError } = useTruthScan(currentCompany?.id || null);
  const { data: decisions, isLoading: decisionsLoading } = useDecisions(currentCompany?.id || null);
  const runTruthScanMutation = useRunTruthScan();
  
  useEffect(() => {
    if (truthScan) {
      setTruthScan(truthScan);
    }
  }, [truthScan, setTruthScan]);
  
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
    if (value == null) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currentCompany.currency || 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  };
  
  const formatPercent = (value: number | null | undefined) => {
    if (value == null || typeof value !== 'number' || isNaN(value)) return 'N/A';
    return `${value.toFixed(1)}%`;
  };
  
  const safeToFixed = (value: any, digits: number = 1): string => {
    if (value == null || typeof value !== 'number' || isNaN(value)) return 'N/A';
    return value.toFixed(digits);
  };
  
  const getConfidenceBadge = () => {
    if (confidence < 60) {
      return <Badge variant="destructive">Low Confidence ({confidence})</Badge>;
    } else if (confidence < 80) {
      return <Badge className="bg-amber-500/20 text-amber-400">Medium Confidence ({confidence})</Badge>;
    }
    return <Badge className="bg-emerald-500/20 text-emerald-400">High Confidence ({confidence})</Badge>;
  };
  
  const handleRefreshScan = async () => {
    if (!currentCompany) return;
    await runTruthScanMutation.mutateAsync(currentCompany.id);
  };
  
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold" data-testid="text-company-name">{currentCompany.name}</h1>
          <p className="text-muted-foreground">Financial Intelligence Overview</p>
        </div>
        <div className="flex items-center gap-2">
          {getConfidenceBadge()}
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
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="overflow-visible">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              Quality of Growth Index
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
            <CardTitle className="text-lg">Data Confidence Score</CardTitle>
          </CardHeader>
          <CardContent>
            {truthLoading ? (
              <Skeleton className="h-16 w-24" />
            ) : (
              <div className="text-4xl font-bold font-mono" data-testid="text-confidence-score">
                {confidence}
                <span className="text-lg text-muted-foreground">/100</span>
              </div>
            )}
            <p className="text-sm text-muted-foreground mt-1">
              Based on data completeness and consistency
            </p>
          </CardContent>
        </Card>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {truthLoading ? (
          Array(6).fill(0).map((_, i) => (
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
              title="Runway (P50)"
              value={`${safeToFixed(metrics.runway_p50)} mo`}
              subtitle={`P10: ${safeToFixed(metrics.runway_p10)}, P90: ${safeToFixed(metrics.runway_p90)}`}
              variant={typeof metrics.runway_p50 === 'number' && metrics.runway_p50 < 6 ? 'danger' : typeof metrics.runway_p50 === 'number' && metrics.runway_p50 < 12 ? 'warning' : 'success'}
              testId="metric-runway"
            />
            <MetricCard
              title="Net Burn"
              value={formatCurrency(metrics.net_burn)}
              trend={metrics.burn_change < 0 ? 'down' : metrics.burn_change > 0 ? 'up' : 'stable'}
              trendValue={`${metrics.burn_change >= 0 ? '+' : ''}${formatCurrency(metrics.burn_change)}`}
              testId="metric-burn"
            />
            <MetricCard
              title="Revenue Growth"
              value={formatPercent(metrics.revenue_growth_mom)}
              subtitle="MoM"
              trend={metrics.revenue_growth_mom > 0 ? 'up' : metrics.revenue_growth_mom < 0 ? 'down' : 'stable'}
              testId="metric-growth"
            />
            <MetricCard
              title="Gross Margin"
              value={formatPercent(metrics.gross_margin)}
              variant={metrics.gross_margin < 50 ? 'warning' : 'default'}
              testId="metric-margin"
            />
            <MetricCard
              title="Burn Multiple"
              value={safeToFixed(metrics.burn_multiple)}
              variant={typeof metrics.burn_multiple === 'number' && metrics.burn_multiple > 3 ? 'warning' : 'default'}
              testId="metric-burn-multiple"
            />
            <MetricCard
              title="Top 5 Concentration"
              value={formatPercent(metrics.concentration_top5)}
              variant={metrics.concentration_top5 > 50 ? 'warning' : 'default'}
              testId="metric-concentration"
            />
          </>
        )}
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
                rank={rec.rank}
                title={rec.title}
                rationale={rec.rationale}
                expectedImpact={rec.expected_impact}
                risks={rec.risks}
                keyAssumption={rec.key_assumption}
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
