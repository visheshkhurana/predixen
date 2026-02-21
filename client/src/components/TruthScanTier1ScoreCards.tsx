import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface Tier1ScoreCardsProps {
  dataConfidenceScore: number;
  qualityOfGrowthIndex: number;
  overallRiskLevel: 'critical' | 'warning' | 'healthy';
  isLoading: boolean;
}

export function Tier1ScoreCards({
  dataConfidenceScore,
  qualityOfGrowthIndex,
  overallRiskLevel,
  isLoading,
}: Tier1ScoreCardsProps) {
  const getConfidenceColor = (score: number) => {
    if (score >= 80) return 'bg-emerald-500/10 border-emerald-500/30';
    if (score >= 60) return 'bg-amber-500/10 border-amber-500/30';
    return 'bg-red-500/10 border-red-500/30';
  };

  const getConfidenceTextColor = (score: number) => {
    if (score >= 80) return 'text-emerald-600 dark:text-emerald-400';
    if (score >= 60) return 'text-amber-600 dark:text-amber-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getQualityColor = (score: number) => {
    if (score >= 80) return 'bg-emerald-500/10 border-emerald-500/30';
    if (score >= 60) return 'bg-blue-500/10 border-blue-500/30';
    if (score >= 40) return 'bg-amber-500/10 border-amber-500/30';
    return 'bg-red-500/10 border-red-500/30';
  };

  const getQualityTextColor = (score: number) => {
    if (score >= 80) return 'text-emerald-600 dark:text-emerald-400';
    if (score >= 60) return 'text-blue-600 dark:text-blue-400';
    if (score >= 40) return 'text-amber-600 dark:text-amber-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getRiskColor = (level: 'critical' | 'warning' | 'healthy') => {
    switch (level) {
      case 'critical':
        return 'bg-red-500/10 border-red-500/30';
      case 'warning':
        return 'bg-amber-500/10 border-amber-500/30';
      case 'healthy':
        return 'bg-emerald-500/10 border-emerald-500/30';
    }
  };

  const getRiskIcon = (level: 'critical' | 'warning' | 'healthy') => {
    switch (level) {
      case 'critical':
        return <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />;
      case 'warning':
        return <AlertTriangle className="h-6 w-6 text-amber-600 dark:text-amber-400" />;
      case 'healthy':
        return <CheckCircle className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />;
    }
  };

  const getRiskLabel = (level: 'critical' | 'warning' | 'healthy') => {
    switch (level) {
      case 'critical':
        return 'Critical';
      case 'warning':
        return 'Warning';
      case 'healthy':
        return 'Healthy';
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {/* Data Confidence Score Card */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Card className={`border-2 ${getConfidenceColor(dataConfidenceScore)} cursor-help`}>
            <CardContent className="p-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-muted-foreground">Data Confidence Score</h3>
                </div>
                {isLoading ? (
                  <>
                    <Skeleton className="h-12 w-20" />
                    <Skeleton className="h-2 w-full" />
                  </>
                ) : (
                  <>
                    <div className="flex items-baseline gap-2">
                      <span className={`text-4xl font-bold font-mono ${getConfidenceTextColor(dataConfidenceScore)}`}>
                        {dataConfidenceScore}
                      </span>
                      <span className="text-lg text-muted-foreground">/100</span>
                    </div>
                    <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          dataConfidenceScore >= 80
                            ? 'bg-emerald-500'
                            : dataConfidenceScore >= 60
                              ? 'bg-amber-500'
                              : 'bg-red-500'
                        }`}
                        style={{ width: `${dataConfidenceScore}%` }}
                      />
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <p className="text-sm font-semibold mb-1">Data Confidence Score</p>
          <p className="text-xs text-muted-foreground">
            Measures how complete and reliable your financial data is. Higher scores indicate more accurate projections.
          </p>
        </TooltipContent>
      </Tooltip>

      {/* Quality of Growth Index Card */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Card className={`border-2 ${getQualityColor(qualityOfGrowthIndex)} cursor-help`}>
            <CardContent className="p-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-muted-foreground">Quality of Growth Index</h3>
                </div>
                {isLoading ? (
                  <>
                    <Skeleton className="h-12 w-20" />
                    <Skeleton className="h-2 w-full" />
                  </>
                ) : (
                  <>
                    <div className="flex items-baseline gap-2">
                      <span className={`text-4xl font-bold font-mono ${getQualityTextColor(qualityOfGrowthIndex)}`}>
                        {qualityOfGrowthIndex}
                      </span>
                      <span className="text-lg text-muted-foreground">/100</span>
                    </div>
                    <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          qualityOfGrowthIndex >= 80
                            ? 'bg-emerald-500'
                            : qualityOfGrowthIndex >= 60
                              ? 'bg-blue-500'
                              : qualityOfGrowthIndex >= 40
                                ? 'bg-amber-500'
                                : 'bg-red-500'
                        }`}
                        style={{ width: `${qualityOfGrowthIndex}%` }}
                      />
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <p className="text-sm font-semibold mb-1">Quality of Growth Index</p>
          <p className="text-xs text-muted-foreground">
            Composite score evaluating sustainable growth through revenue efficiency, unit economics, capital efficiency, and risk exposure.
          </p>
        </TooltipContent>
      </Tooltip>

      {/* Overall Risk Level Card */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Card className={`border-2 ${getRiskColor(overallRiskLevel)} cursor-help`}>
            <CardContent className="p-6">
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground">Overall Risk Level</h3>
                {isLoading ? (
                  <Skeleton className="h-12 w-24" />
                ) : (
                  <div className="flex items-center gap-3">
                    {getRiskIcon(overallRiskLevel)}
                    <span className="text-2xl font-bold">{getRiskLabel(overallRiskLevel)}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <p className="text-sm font-semibold mb-1">Overall Risk Level</p>
          <p className="text-xs text-muted-foreground">
            Aggregated assessment of your company's financial health based on runway, burn rate, and key metrics.
          </p>
        </TooltipContent>
      </Tooltip>
    </div>
  );
}
