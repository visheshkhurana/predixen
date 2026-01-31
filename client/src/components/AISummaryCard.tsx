import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { 
  Sparkles, 
  ChevronDown,
  ChevronUp,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Lightbulb,
  Target,
  BarChart3
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiRequest } from '@/lib/queryClient';

async function fetchWithJson<T>(method: string, url: string, data?: unknown): Promise<T> {
  const response = await apiRequest(method, url, data);
  return response.json() as Promise<T>;
}

interface Driver {
  name: string;
  value: number;
  impact_area: string;
  impact_score: number;
  description: string;
}

interface NarrativeResponse {
  summary: string;
  health_status: 'healthy' | 'warning' | 'critical';
  key_metrics: {
    runway_p50: number;
    runway_range: string;
    survival_18m: number;
    survival_24m: number;
    end_cash: number;
    monthly_burn: number;
  };
  drivers: Driver[];
  insights: string[];
  recommendations: string[];
}

interface AISummaryCardProps {
  companyId: number;
  simulationResults: {
    runway?: { p10?: number; p50?: number; p90?: number };
    survival?: { '12m'?: number; '18m'?: number; '24m'?: number };
    summary?: { end_cash?: number; monthly_burn?: number; monthly_burn_p50?: number };
  };
  scenarioParams?: {
    name?: string;
    pricing_change_pct?: number;
    growth_uplift_pct?: number;
    burn_reduction_pct?: number;
    gross_margin_delta_pct?: number;
    churn_change_pct?: number;
    cac_change_pct?: number;
    fundraise_month?: number | null;
    fundraise_amount?: number;
  };
  scenarioName?: string;
  className?: string;
  testId?: string;
}

export function AISummaryCard({
  companyId,
  simulationResults,
  scenarioParams = {},
  scenarioName = 'Custom Scenario',
  className,
  testId = 'ai-summary-card'
}: AISummaryCardProps) {
  const [narrative, setNarrative] = useState<NarrativeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);
  const [showDrivers, setShowDrivers] = useState(false);
  const [showRecommendations, setShowRecommendations] = useState(true);
  
  const lastFetchKey = useRef<string>('');
  const fetchInProgress = useRef<boolean>(false);

  useEffect(() => {
    const fetchNarrative = async () => {
      if (!simulationResults?.runway?.p50) {
        return;
      }

      const fetchKey = JSON.stringify({
        companyId,
        runway: simulationResults.runway,
        survival: simulationResults.survival,
        scenarioName
      });
      
      if (fetchKey === lastFetchKey.current || fetchInProgress.current) {
        return;
      }
      
      lastFetchKey.current = fetchKey;
      fetchInProgress.current = true;
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetchWithJson<NarrativeResponse>(
          'POST',
          `/simulation-copilot/narrative/${companyId}`,
          {
            simulation_results: simulationResults,
            scenario_params: scenarioParams,
            scenario_name: scenarioName
          }
        );

        setNarrative(response);
      } catch (err) {
        console.error('Failed to fetch AI narrative:', err);
        setError('Unable to generate AI summary');
      } finally {
        setIsLoading(false);
        fetchInProgress.current = false;
      }
    };

    const timeoutId = setTimeout(fetchNarrative, 500);
    return () => clearTimeout(timeoutId);
  }, [companyId, simulationResults, scenarioParams, scenarioName]);

  if (!simulationResults?.runway?.p50) {
    return null;
  }

  const healthColors = {
    healthy: 'border-green-300/50 bg-green-50/50 dark:border-green-700/30 dark:bg-green-900/10',
    warning: 'border-amber-300/50 bg-amber-50/50 dark:border-amber-700/30 dark:bg-amber-900/10',
    critical: 'border-red-300/50 bg-red-50/50 dark:border-red-700/30 dark:bg-red-900/10'
  };

  const healthIcons = {
    healthy: <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />,
    warning: <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" />,
    critical: <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
  };

  const healthLabels = {
    healthy: 'Healthy Outlook',
    warning: 'Moderate Risk',
    critical: 'High Risk'
  };

  if (isLoading) {
    return (
      <Card className={cn("overflow-visible", className)} data-testid={testId}>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary animate-pulse" />
            <Skeleton className="h-5 w-32" />
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-4 w-3/5" />
        </CardContent>
      </Card>
    );
  }

  if (error || !narrative) {
    return null;
  }

  return (
    <Card 
      className={cn(
        "overflow-visible",
        healthColors[narrative.health_status],
        className
      )} 
      data-testid={testId}
    >
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <CardTitle className="text-base">AI Analysis</CardTitle>
              <Badge variant="outline" className="ml-2 gap-1">
                {healthIcons[narrative.health_status]}
                <span className="text-xs">{healthLabels[narrative.health_status]}</span>
              </Badge>
            </div>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8" data-testid="toggle-summary">
                {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </CollapsibleTrigger>
          </div>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="space-y-4 pt-0">
            <p className="text-sm leading-relaxed text-foreground">
              {narrative.summary}
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="text-center p-2 bg-background/50 rounded-lg">
                <p className="text-lg font-bold">{narrative.key_metrics.runway_p50.toFixed(1)}</p>
                <p className="text-xs text-muted-foreground">Runway (months)</p>
              </div>
              <div className="text-center p-2 bg-background/50 rounded-lg">
                <p className="text-lg font-bold">{narrative.key_metrics.survival_18m.toFixed(0)}%</p>
                <p className="text-xs text-muted-foreground">18m Survival</p>
              </div>
              <div className="text-center p-2 bg-background/50 rounded-lg">
                <p className="text-lg font-bold">${(narrative.key_metrics.monthly_burn / 1000).toFixed(0)}k</p>
                <p className="text-xs text-muted-foreground">Monthly Burn</p>
              </div>
              <div className="text-center p-2 bg-background/50 rounded-lg">
                <p className="text-lg font-bold">${(narrative.key_metrics.end_cash / 1000000).toFixed(1)}M</p>
                <p className="text-xs text-muted-foreground">End Cash</p>
              </div>
            </div>

            {narrative.drivers.length > 0 && (
              <Collapsible open={showDrivers} onOpenChange={setShowDrivers}>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="sm" className="w-full justify-between" data-testid="toggle-drivers">
                    <span className="flex items-center gap-2">
                      <BarChart3 className="h-4 w-4" />
                      Key Drivers
                    </span>
                    {showDrivers ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="space-y-2 mt-2">
                    {narrative.drivers.map((driver, idx) => (
                      <div 
                        key={idx} 
                        className="flex items-center justify-between p-2 bg-background/50 rounded-md"
                      >
                        <div className="flex items-center gap-2">
                          <Target className="h-3.5 w-3.5 text-muted-foreground" />
                          <span className="text-sm font-medium">{driver.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-xs">
                            {driver.value > 0 ? '+' : ''}{driver.value}%
                          </Badge>
                          <span className="text-xs text-muted-foreground capitalize">
                            {driver.impact_area}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CollapsibleContent>
              </Collapsible>
            )}

            {narrative.insights.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  Insights
                </div>
                <ul className="space-y-1">
                  {narrative.insights.map((insight, idx) => (
                    <li key={idx} className="text-sm text-muted-foreground pl-6 relative">
                      <span className="absolute left-2 top-2 w-1.5 h-1.5 rounded-full bg-primary/50" />
                      {insight}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {narrative.recommendations.length > 0 && (
              <Collapsible open={showRecommendations} onOpenChange={setShowRecommendations}>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="sm" className="w-full justify-between" data-testid="toggle-recommendations">
                    <span className="flex items-center gap-2">
                      <Lightbulb className="h-4 w-4 text-amber-500" />
                      Recommendations
                    </span>
                    {showRecommendations ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="space-y-2 mt-2">
                    {narrative.recommendations.map((rec, idx) => (
                      <div 
                        key={idx} 
                        className="flex items-start gap-2 p-2 bg-amber-50/50 dark:bg-amber-900/10 rounded-md"
                      >
                        <span className="text-amber-600 dark:text-amber-400 font-medium text-sm">{idx + 1}.</span>
                        <p className="text-sm text-amber-800 dark:text-amber-300">{rec}</p>
                      </div>
                    ))}
                  </div>
                </CollapsibleContent>
              </Collapsible>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
