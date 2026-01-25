import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { 
  AlertTriangle, 
  CheckCircle2, 
  HelpCircle, 
  Loader2, 
  FileText,
  AlertCircle,
  TrendingUp,
  DollarSign,
  Percent
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface VerificationIssue {
  metric: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  suggestion?: string;
}

interface MetricVerification {
  name: string;
  value: number | null | undefined;
  displayValue: string;
  confidence: 'high' | 'medium' | 'low' | 'missing';
  source?: string;
  issue?: VerificationIssue;
}

interface DataVerificationCopilotProps {
  extractedData: {
    company_info?: {
      name?: string;
      stage?: string;
    };
    financials?: {
      monthly_revenue?: number;
      gross_margin_pct?: number;
      opex?: number;
      payroll?: number;
      other_costs?: number;
      cash_balance?: number;
      net_burn?: number;
    };
    computed_metrics?: {
      revenue_growth_mom?: number;
      burn_multiple?: number;
      concentration_top5?: number;
      ndr?: number;
      churn_rate?: number;
    };
    confidence?: { company_info: number; financials: number };
  } | null;
  baselineData: {
    monthly_revenue: number;
    gross_margin_pct: number;
    opex: number;
    payroll: number;
    other_costs: number;
    cash_balance: number;
  };
  onUpdateBaseline: (updates: Partial<typeof baselineData>) => void;
  companyStage?: string;
  currency?: string;
}

const formatCurrency = (value: number | null | undefined, currency = 'USD'): string => {
  if (value == null) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

const formatPercent = (value: number | null | undefined): string => {
  if (value == null) return 'N/A';
  return `${value.toFixed(1)}%`;
};

export function DataVerificationCopilot({
  extractedData,
  baselineData,
  onUpdateBaseline,
  companyStage,
  currency = 'USD'
}: DataVerificationCopilotProps) {
  const [issues, setIssues] = useState<VerificationIssue[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [simulationReady, setSimulationReady] = useState(false);

  const financials = extractedData?.financials || {};
  const computedMetrics = extractedData?.computed_metrics || {};
  const confidenceLevel = extractedData?.confidence?.financials || 0;

  const analyzeData = () => {
    setIsAnalyzing(true);
    const detectedIssues: VerificationIssue[] = [];

    const revenue = baselineData.monthly_revenue;
    const cash = baselineData.cash_balance;
    const grossMargin = baselineData.gross_margin_pct;
    const totalCosts = baselineData.opex + baselineData.payroll + baselineData.other_costs;
    const netBurn = totalCosts + (revenue * (1 - grossMargin / 100)) - revenue;

    if (revenue === 0) {
      detectedIssues.push({
        metric: 'monthly_revenue',
        severity: 'warning',
        message: 'Revenue is $0. Is this a pre-revenue company?',
        suggestion: 'If pre-revenue, confirm. Otherwise, enter actual monthly revenue.'
      });
    }

    if (revenue > 0 && computedMetrics.revenue_growth_mom === 0) {
      detectedIssues.push({
        metric: 'revenue_growth_mom',
        severity: 'info',
        message: 'Growth rate is 0%. This may flatten simulation variance.',
        suggestion: 'Add historical growth data for meaningful P10/P90 projections.'
      });
    }

    if (baselineData.payroll > 0 && baselineData.opex === 0 && baselineData.other_costs === 0) {
      detectedIssues.push({
        metric: 'opex',
        severity: 'warning',
        message: 'Only payroll is entered. Are other operating costs missing?',
        suggestion: 'Common costs: software, rent, marketing, legal.'
      });
    }

    if (baselineData.payroll === 0 && revenue > 10000) {
      detectedIssues.push({
        metric: 'payroll',
        severity: 'warning',
        message: 'Payroll is $0 but company has significant revenue.',
        suggestion: 'Include founder salaries or contractor costs if applicable.'
      });
    }

    if (grossMargin > 95) {
      detectedIssues.push({
        metric: 'gross_margin_pct',
        severity: 'info',
        message: `Gross margin of ${grossMargin}% is unusually high.`,
        suggestion: 'Typical SaaS: 70-85%. Ensure COGS includes hosting, support costs.'
      });
    }

    if (grossMargin < 40 && companyStage && ['seed', 'series_a'].includes(companyStage)) {
      detectedIssues.push({
        metric: 'gross_margin_pct',
        severity: 'warning',
        message: `Gross margin of ${grossMargin}% is low for ${companyStage} stage.`,
        suggestion: 'Consider if unit economics are sustainable for fundraising.'
      });
    }

    if (netBurn < 0 && revenue > 0) {
      detectedIssues.push({
        metric: 'net_burn',
        severity: 'info',
        message: 'Company appears profitable (negative burn).',
        suggestion: 'Runway will show as infinite. This is positive!'
      });
    }

    if (cash > 0 && netBurn > 0) {
      const runway = cash / netBurn;
      if (runway < 6) {
        detectedIssues.push({
          metric: 'runway',
          severity: 'error',
          message: `Runway is only ${runway.toFixed(1)} months.`,
          suggestion: 'Critical cash position. Consider fundraising or cost reduction.'
        });
      }
    }

    const burnMultiple = computedMetrics.burn_multiple;
    if (burnMultiple && burnMultiple > 3) {
      detectedIssues.push({
        metric: 'burn_multiple',
        severity: 'warning',
        message: `Burn multiple of ${burnMultiple.toFixed(1)}x is high.`,
        suggestion: 'Good: <1x, OK: 1-2x, Concerning: >2x'
      });
    }

    const concentration = computedMetrics.concentration_top5;
    if (concentration && concentration > 80) {
      detectedIssues.push({
        metric: 'concentration_top5',
        severity: 'warning',
        message: `Top 5 customers are ${concentration.toFixed(0)}% of revenue.`,
        suggestion: 'High concentration = high risk. Diversify customer base.'
      });
    }

    setIssues(detectedIssues);
    
    const hasBlockingIssues = detectedIssues.some(i => i.severity === 'error');
    setSimulationReady(!hasBlockingIssues);
    
    setTimeout(() => {
      setIsAnalyzing(false);
      setAnalysisComplete(true);
    }, 800);
  };

  useEffect(() => {
    if (extractedData) {
      analyzeData();
    }
  }, [baselineData, extractedData]);

  const getConfidenceBadge = (level: 'high' | 'medium' | 'low' | 'missing') => {
    switch (level) {
      case 'high':
        return <Badge className="bg-emerald-500/20 text-emerald-500 text-xs">High Confidence</Badge>;
      case 'medium':
        return <Badge className="bg-amber-500/20 text-amber-500 text-xs">Medium Confidence</Badge>;
      case 'low':
        return <Badge className="bg-orange-500/20 text-orange-500 text-xs">Low Confidence</Badge>;
      case 'missing':
        return <Badge variant="secondary" className="text-xs">Not Found</Badge>;
    }
  };

  const getMetricConfidence = (value: number | null | undefined, extractedValue: number | null | undefined): 'high' | 'medium' | 'low' | 'missing' => {
    if (extractedValue == null) return 'missing';
    if (value === extractedValue) return 'high';
    if (Math.abs((value || 0) - extractedValue) / extractedValue < 0.1) return 'medium';
    return 'low';
  };

  const getSeverityIcon = (severity: 'error' | 'warning' | 'info') => {
    switch (severity) {
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-amber-500" />;
      case 'info':
        return <HelpCircle className="h-4 w-4 text-blue-500" />;
    }
  };

  const metrics: MetricVerification[] = [
    {
      name: 'Monthly Revenue',
      value: baselineData.monthly_revenue,
      displayValue: formatCurrency(baselineData.monthly_revenue, currency),
      confidence: getMetricConfidence(baselineData.monthly_revenue, financials.monthly_revenue),
      source: financials.monthly_revenue != null ? 'Extracted from PDF' : undefined
    },
    {
      name: 'Gross Margin',
      value: baselineData.gross_margin_pct,
      displayValue: formatPercent(baselineData.gross_margin_pct),
      confidence: getMetricConfidence(baselineData.gross_margin_pct, financials.gross_margin_pct),
      source: financials.gross_margin_pct != null ? 'Extracted from PDF' : undefined
    },
    {
      name: 'Cash Balance',
      value: baselineData.cash_balance,
      displayValue: formatCurrency(baselineData.cash_balance, currency),
      confidence: getMetricConfidence(baselineData.cash_balance, financials.cash_balance),
      source: financials.cash_balance != null ? 'Extracted from PDF' : undefined
    },
    {
      name: 'Operating Expenses',
      value: baselineData.opex,
      displayValue: formatCurrency(baselineData.opex, currency),
      confidence: getMetricConfidence(baselineData.opex, financials.opex),
      source: financials.opex != null ? 'Extracted from PDF' : undefined
    },
    {
      name: 'Payroll',
      value: baselineData.payroll,
      displayValue: formatCurrency(baselineData.payroll, currency),
      confidence: getMetricConfidence(baselineData.payroll, financials.payroll),
      source: financials.payroll != null ? 'Extracted from PDF' : undefined
    }
  ];

  const errorCount = issues.filter(i => i.severity === 'error').length;
  const warningCount = issues.filter(i => i.severity === 'warning').length;

  return (
    <Card className="border-2 border-primary/30">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">Data Verification</CardTitle>
          </div>
          {analysisComplete && (
            <div className="flex items-center gap-2">
              {errorCount > 0 && (
                <Badge variant="destructive" className="text-xs">
                  {errorCount} Critical
                </Badge>
              )}
              {warningCount > 0 && (
                <Badge className="bg-amber-500/20 text-amber-500 text-xs">
                  {warningCount} Warning{warningCount > 1 ? 's' : ''}
                </Badge>
              )}
              {errorCount === 0 && warningCount === 0 && (
                <Badge className="bg-emerald-500/20 text-emerald-500 text-xs">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  All Clear
                </Badge>
              )}
            </div>
          )}
        </div>
        <CardDescription>
          Review extracted values and confirm accuracy before simulation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isAnalyzing && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Analyzing data for anomalies...
          </div>
        )}

        <div className="grid gap-3">
          {metrics.map((metric, idx) => (
            <div
              key={idx}
              className={cn(
                'flex items-center justify-between p-3 rounded-lg border',
                metric.confidence === 'high' && 'border-emerald-500/30 bg-emerald-500/5',
                metric.confidence === 'medium' && 'border-amber-500/30 bg-amber-500/5',
                metric.confidence === 'low' && 'border-orange-500/30 bg-orange-500/5',
                metric.confidence === 'missing' && 'border-muted'
              )}
              data-testid={`verification-metric-${metric.name.toLowerCase().replace(/\s/g, '-')}`}
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{metric.name}</span>
                  {metric.source && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <FileText className="h-3 w-3 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="text-xs">{metric.source}</p>
                      </TooltipContent>
                    </Tooltip>
                  )}
                </div>
                <div className="text-lg font-mono font-semibold">
                  {metric.displayValue}
                </div>
              </div>
              <div className="flex-shrink-0">
                {getConfidenceBadge(metric.confidence)}
              </div>
            </div>
          ))}
        </div>

        {issues.length > 0 && (
          <div className="space-y-3 pt-2">
            <div className="text-sm font-medium text-muted-foreground">Issues Detected</div>
            {issues.map((issue, idx) => (
              <div
                key={idx}
                className={cn(
                  'p-3 rounded-lg border',
                  issue.severity === 'error' && 'border-red-500/30 bg-red-500/5',
                  issue.severity === 'warning' && 'border-amber-500/30 bg-amber-500/5',
                  issue.severity === 'info' && 'border-blue-500/30 bg-blue-500/5'
                )}
                data-testid={`verification-issue-${idx}`}
              >
                <div className="flex items-start gap-2">
                  {getSeverityIcon(issue.severity)}
                  <div className="flex-1">
                    <p className="text-sm font-medium">{issue.message}</p>
                    {issue.suggestion && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {issue.suggestion}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className={cn(
          'p-3 rounded-lg border mt-4',
          simulationReady ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-amber-500/30 bg-amber-500/5'
        )}>
          <div className="flex items-center gap-2">
            {simulationReady ? (
              <>
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                <div>
                  <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
                    Ready for Simulation
                  </p>
                  <p className="text-xs text-muted-foreground">
                    All critical checks passed. You can proceed with confidence.
                  </p>
                </div>
              </>
            ) : (
              <>
                <AlertTriangle className="h-5 w-5 text-amber-500" />
                <div>
                  <p className="text-sm font-medium text-amber-600 dark:text-amber-400">
                    Review Required
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Address critical issues above before proceeding.
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
