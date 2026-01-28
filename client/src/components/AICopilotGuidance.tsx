import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Sparkles, 
  AlertTriangle, 
  Lightbulb, 
  TrendingUp, 
  TrendingDown,
  Info
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiRequest } from '@/lib/queryClient';
import { useDebounce } from '@/hooks/use-debounce';

async function fetchWithJson<T>(method: string, url: string, data?: unknown): Promise<T> {
  const response = await apiRequest(method, url, data);
  return response.json() as Promise<T>;
}

interface AssumptionEffect {
  metric: string;
  effect: string;
  direction: 'positive' | 'negative';
}

interface GuidanceResponse {
  prompt: string;
  effects: AssumptionEffect[];
  recommendation: string | null;
  warning: string | null;
  delta: number;
  impact_level: 'high' | 'medium' | 'low';
}

interface AICopilotGuidanceProps {
  companyId: number;
  assumption: string;
  value: number;
  previousValue: number;
  onGuidanceUpdate?: (guidance: GuidanceResponse | null) => void;
  className?: string;
  testId?: string;
}

export function AICopilotGuidance({
  companyId,
  assumption,
  value,
  previousValue,
  onGuidanceUpdate,
  className,
  testId = 'ai-copilot-guidance'
}: AICopilotGuidanceProps) {
  const [guidance, setGuidance] = useState<GuidanceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const debouncedValue = useDebounce(value, 300);

  const fetchGuidance = useCallback(async () => {
    if (debouncedValue === previousValue) {
      setGuidance(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetchWithJson<GuidanceResponse>(
        'POST',
        `/simulation-copilot/prompt/${companyId}`,
        {
          assumption,
          old_value: previousValue,
          new_value: debouncedValue
        }
      );

      setGuidance(response);
      onGuidanceUpdate?.(response);
    } catch (err) {
      console.error('Failed to fetch AI guidance:', err);
      setError('Unable to get AI guidance');
      setGuidance(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, assumption, debouncedValue, previousValue, onGuidanceUpdate]);

  useEffect(() => {
    if (debouncedValue !== previousValue) {
      fetchGuidance();
    }
  }, [debouncedValue, previousValue, fetchGuidance]);

  if (!guidance && !isLoading && value === previousValue) {
    return null;
  }

  if (isLoading) {
    return (
      <Card className={cn("overflow-visible border-primary/20 bg-primary/5", className)} data-testid={testId}>
        <CardContent className="p-3">
          <div className="flex items-start gap-2">
            <Sparkles className="h-4 w-4 text-primary animate-pulse mt-0.5" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return null;
  }

  if (!guidance) {
    return null;
  }

  const impactColors = {
    high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    medium: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
    low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
  };

  return (
    <Card 
      className={cn(
        "overflow-visible animate-in slide-in-from-top-2 duration-300",
        guidance.warning ? "border-amber-300/50 bg-amber-50/50 dark:border-amber-700/30 dark:bg-amber-900/10" : "border-primary/20 bg-primary/5",
        className
      )} 
      data-testid={testId}
    >
      <CardContent className="p-3">
        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <Sparkles className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-medium text-primary">AI Insight</span>
                <Badge 
                  variant="secondary" 
                  className={cn("text-[10px] px-1.5 py-0", impactColors[guidance.impact_level])}
                >
                  {guidance.impact_level} impact
                </Badge>
              </div>
              <p className="text-sm text-foreground mt-1 leading-relaxed">
                {guidance.prompt}
              </p>
            </div>
          </div>

          {guidance.effects.length > 0 && (
            <div className="flex flex-wrap gap-1.5 ml-6">
              {guidance.effects.slice(0, 3).map((effect, idx) => (
                <div 
                  key={idx}
                  className={cn(
                    "flex items-center gap-1 text-xs px-2 py-0.5 rounded-full",
                    effect.direction === 'positive' 
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                      : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                  )}
                >
                  {effect.direction === 'positive' ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : (
                    <TrendingDown className="h-3 w-3" />
                  )}
                  <span className="capitalize">{effect.metric.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          )}

          {guidance.warning && (
            <div className="flex items-start gap-2 ml-6 p-2 bg-amber-100/50 dark:bg-amber-900/20 rounded-md">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-amber-800 dark:text-amber-300">
                {guidance.warning}
              </p>
            </div>
          )}

          {guidance.recommendation && (
            <div className="flex items-start gap-2 ml-6 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-md">
              <Lightbulb className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-blue-800 dark:text-blue-300">
                {guidance.recommendation}
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

interface InlineGuidanceTooltipProps {
  assumption: string;
  description: string;
  typicalRange?: string;
  testId?: string;
}

export function InlineGuidanceTooltip({
  assumption,
  description,
  typicalRange,
  testId = 'inline-guidance-tooltip'
}: InlineGuidanceTooltipProps) {
  return (
    <div className="flex items-start gap-2 p-2 bg-muted/50 rounded-md" data-testid={testId}>
      <Info className="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
      <div className="text-xs text-muted-foreground">
        <p>{description}</p>
        {typicalRange && (
          <p className="mt-1 font-medium">Typical range: {typicalRange}</p>
        )}
      </div>
    </div>
  );
}
