import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

interface SimulationSummaryBannerProps {
  runwayP50: number;
  survival18m: number;
  survival12m: number;
  endCash?: number;
  scenarioName: string;
  testId?: string;
}

export function SimulationSummaryBanner({
  runwayP50,
  survival18m,
  survival12m,
  endCash,
  scenarioName,
  testId = 'summary-banner',
}: SimulationSummaryBannerProps) {
  const isHealthy = survival18m >= 80;
  const isWarning = survival18m >= 50 && survival18m < 80;
  const isCritical = survival18m < 50;

  const getStatusIcon = () => {
    if (isHealthy) return <CheckCircle className="h-5 w-5 text-emerald-500" />;
    if (isWarning) return <AlertTriangle className="h-5 w-5 text-amber-500" />;
    return <AlertTriangle className="h-5 w-5 text-red-500" />;
  };

  const getStatusColor = () => {
    if (isHealthy) return 'border-emerald-500/30 bg-emerald-500/10';
    if (isWarning) return 'border-amber-500/30 bg-amber-500/10';
    return 'border-red-500/30 bg-red-500/10';
  };

  const formatCurrency = (value: number | undefined) => {
    if (value === undefined || value === null) return 'N/A';
    if (Math.abs(value) >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    }
    return `$${(value / 1000).toFixed(0)}K`;
  };

  return (
    <Card className={`${getStatusColor()}`} data-testid={testId}>
      <CardContent className="p-4">
        <div className="flex items-start gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            {getStatusIcon()}
            <div>
              <p className="font-semibold">{scenarioName} Results</p>
              <p className="text-sm text-muted-foreground">Monte Carlo simulation complete</p>
            </div>
          </div>
          
          <div className="flex-1 flex items-center gap-4 flex-wrap justify-end">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">
                Runway extends to <strong className="font-mono">{runwayP50.toFixed(1)} months</strong> (P50)
              </span>
            </div>
            
            <Badge 
              variant={isHealthy ? 'default' : isWarning ? 'secondary' : 'destructive'}
              className="font-mono"
            >
              {survival18m.toFixed(0)}% survival at 18 months
            </Badge>
            
            {endCash !== undefined && (
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">
                  End cash: <strong className="font-mono">{formatCurrency(endCash)}</strong>
                </span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
