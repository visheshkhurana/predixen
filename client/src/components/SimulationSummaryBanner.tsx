import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, AlertTriangle, CheckCircle, Clock, DollarSign } from 'lucide-react';

interface SimulationSummaryBannerProps {
  runwayP50: number;
  survival18m: number;
  survival12m: number;
  endCash?: number;
  netProfit?: number;
  monthlyBurn?: number;
  monthlyRevenue?: number;
  scenarioName: string;
  testId?: string;
}

export function SimulationSummaryBanner({
  runwayP50,
  survival18m,
  survival12m,
  endCash,
  netProfit,
  monthlyBurn,
  monthlyRevenue,
  scenarioName,
  testId = 'summary-banner',
}: SimulationSummaryBannerProps) {
  const isSustainable = runwayP50 >= 36 || (monthlyRevenue !== undefined && monthlyBurn !== undefined && monthlyRevenue > monthlyBurn);
  const cappedRunway = Math.min(runwayP50, 60);
  
  const effectiveSurvival = isSustainable ? 100 : survival18m;
  
  const isHealthy = effectiveSurvival >= 80 || isSustainable;
  const isWarning = effectiveSurvival >= 50 && effectiveSurvival < 80 && !isSustainable;
  const isCritical = effectiveSurvival < 50 && !isSustainable;

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

  const calculateNetProfit = () => {
    if (netProfit !== undefined) return netProfit;
    if (monthlyRevenue !== undefined && monthlyBurn !== undefined) {
      return monthlyRevenue - monthlyBurn;
    }
    return undefined;
  };

  const profit = calculateNetProfit();

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
            {isSustainable ? (
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-emerald-500" />
                <span className="text-sm">
                  <strong className="font-mono text-emerald-500">Sustainable</strong>
                  {profit !== undefined && profit > 0 && (
                    <span className="ml-2 text-muted-foreground">
                      (Net profit: <strong className="font-mono text-emerald-500">{formatCurrency(profit)}/mo</strong>)
                    </span>
                  )}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">
                  Runway extends to <strong className="font-mono">{cappedRunway.toFixed(1)} months</strong> (P50)
                </span>
              </div>
            )}
            
            <Badge 
              variant={isHealthy ? 'default' : isWarning ? 'secondary' : 'destructive'}
              className="font-mono"
            >
              {isSustainable ? '100% survival at 18 months' : `${survival18m.toFixed(0)}% survival at 18 months`}
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
