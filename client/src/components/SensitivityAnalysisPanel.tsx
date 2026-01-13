import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowUp, ArrowDown, Target, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';

interface SensitivityDriver {
  driver: string;
  impact_direction: string;
  impact_magnitude: number;
  threshold_value: number | null;
  explanation: string;
}

interface SensitivityResult {
  target_runway_months: number;
  target_probability: number;
  achievable: boolean;
  current_probability: number;
  key_drivers: SensitivityDriver[];
  recommendations: string[];
}

interface SensitivityAnalysisPanelProps {
  data: SensitivityResult | null;
  isLoading?: boolean;
  onRunAnalysis?: () => void;
}

function formatDriverName(driver: string): string {
  return driver
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase());
}

function DriverImpactBar({ driver }: { driver: SensitivityDriver }) {
  const isPositive = driver.impact_direction === 'positive';
  
  return (
    <div className="space-y-2 p-4 rounded-lg border hover-elevate">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          {isPositive ? (
            <ArrowUp className="h-4 w-4 text-emerald-500" />
          ) : (
            <ArrowDown className="h-4 w-4 text-red-500" />
          )}
          <span className="font-medium">{formatDriverName(driver.driver)}</span>
        </div>
        <Badge 
          variant="outline" 
          className={isPositive ? 'text-emerald-500' : 'text-red-500'}
        >
          {driver.impact_magnitude > 0 ? '+' : ''}{driver.impact_magnitude.toFixed(1)}% impact
        </Badge>
      </div>
      
      <Progress 
        value={Math.min(Math.abs(driver.impact_magnitude), 100)} 
        className="h-2"
      />
      
      <p className="text-sm text-muted-foreground">{driver.explanation}</p>
      
      {driver.threshold_value !== null && (
        <div className="flex items-center gap-2 text-sm">
          <Target className="h-3 w-3 text-primary" />
          <span className="text-muted-foreground">Target threshold:</span>
          <span className="font-mono font-medium">{driver.threshold_value.toFixed(2)}</span>
        </div>
      )}
    </div>
  );
}

export function SensitivityAnalysisPanel({ 
  data, 
  isLoading,
  onRunAnalysis 
}: SensitivityAnalysisPanelProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    );
  }
  
  if (!data) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Target className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground mb-2">
            Run sensitivity analysis to discover which drivers have the biggest impact on your runway
          </p>
          <p className="text-sm text-muted-foreground mb-4">
            Find out "what must be true" to achieve your target runway
          </p>
          {onRunAnalysis && (
            <Button onClick={onRunAnalysis} data-testid="button-run-sensitivity">
              Run Sensitivity Analysis
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }
  
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <CardTitle className="text-lg">What Must Be True</CardTitle>
              <CardDescription>
                Key drivers and thresholds to achieve {data.target_runway_months} months runway
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {data.achievable ? (
                <Badge className="bg-emerald-500/20 text-emerald-400">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Achievable
                </Badge>
              ) : (
                <Badge variant="destructive">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  Challenging
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-muted/50 rounded-lg text-center">
              <p className="text-xs text-muted-foreground">Target Runway</p>
              <p className="text-2xl font-mono font-bold text-primary">
                {data.target_runway_months}mo
              </p>
            </div>
            <div className="p-4 bg-muted/50 rounded-lg text-center">
              <p className="text-xs text-muted-foreground">Target Probability</p>
              <p className="text-2xl font-mono font-bold">
                {(data.target_probability * 100).toFixed(0)}%
              </p>
            </div>
            <div className="p-4 bg-muted/50 rounded-lg text-center">
              <p className="text-xs text-muted-foreground">Current Probability</p>
              <p className="text-2xl font-mono font-bold">
                {(data.current_probability * 100).toFixed(0)}%
              </p>
            </div>
            <div className="p-4 bg-muted/50 rounded-lg text-center">
              <p className="text-xs text-muted-foreground">Probability Gap</p>
              <p className={`text-2xl font-mono font-bold ${
                data.current_probability >= data.target_probability 
                  ? 'text-emerald-500' 
                  : 'text-amber-500'
              }`}>
                {((data.current_probability - data.target_probability) * 100).toFixed(0)}%
              </p>
            </div>
          </div>
          
          <h3 className="font-medium mb-4">Key Drivers (Ranked by Impact)</h3>
          <div className="space-y-3">
            {data.key_drivers.map((driver, index) => (
              <DriverImpactBar key={driver.driver} driver={driver} />
            ))}
          </div>
        </CardContent>
      </Card>
      
      {data.recommendations && data.recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recommendations</CardTitle>
            <CardDescription>
              Actions to improve your probability of achieving target runway
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.recommendations.map((rec, index) => (
                <li key={index} className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 mt-0.5 text-primary shrink-0" />
                  <span className="text-sm">{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
