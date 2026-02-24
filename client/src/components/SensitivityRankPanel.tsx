import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { AlertCircle, ChevronRight, TrendingUp } from 'lucide-react';

export interface SensitivityRank {
  rank: number;
  variable: string;
  displayName: string;
  impact: number;
  impactUnit: string;
  percentageChange: number;
  description: string;
  recommendation?: string;
}

interface SensitivityRankPanelProps {
  ranks: SensitivityRank[];
  isLoading?: boolean;
  onAdjustVariable?: (variable: string) => void;
}

export function SensitivityRankPanel({
  ranks,
  isLoading = false,
  onAdjustVariable,
}: SensitivityRankPanelProps) {
  if (!ranks || ranks.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Sensitivity Ranking
          </CardTitle>
          <CardDescription>
            Variables with the greatest impact on your runway
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-sm">
              Run a scenario to see which variables have the most impact on your outcomes
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Calculate max impact for scaling progress bars
  const maxImpact = Math.max(...ranks.map((r) => Math.abs(r.impact)));

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Sensitivity Ranking
            </CardTitle>
            <CardDescription>
              Variables with the greatest impact on your runway (sorted by magnitude)
            </CardDescription>
          </div>
          <AlertCircle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-1" />
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          {ranks.map((rank, idx) => {
            const isPositiveImpact = rank.impact >= 0;
            const normalizedPercentage = (Math.abs(rank.impact) / maxImpact) * 100;

            return (
              <div key={rank.variable} className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs font-bold shrink-0">
                        #{rank.rank}
                      </Badge>
                      <h4 className="font-medium text-sm truncate">{rank.displayName}</h4>
                    </div>

                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {rank.description}
                    </p>
                  </div>

                  <div className="text-right shrink-0">
                    <div
                      className={`text-sm font-bold font-mono ${
                        isPositiveImpact
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      {isPositiveImpact ? '+' : ''}
                      {rank.impact} {rank.impactUnit}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {Math.abs(rank.percentageChange).toFixed(1)}% change
                    </p>
                  </div>
                </div>

                {/* Visual impact indicator */}
                <div className="flex items-center gap-2">
                  <Progress value={normalizedPercentage} className="h-2 flex-1" />
                  <span className="text-xs font-medium text-muted-foreground w-10 text-right">
                    {Math.round(normalizedPercentage)}%
                  </span>
                </div>

                {/* Recommendation */}
                {rank.recommendation && (
                  <div className="pl-0 pt-1 border-l-2 border-amber-300 dark:border-amber-600">
                    <p className="text-xs text-amber-900 dark:text-amber-300 italic ml-3">
                      💡 {rank.recommendation}
                    </p>
                  </div>
                )}

                {/* Action button */}
                {onAdjustVariable && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onAdjustVariable(rank.variable)}
                    className="h-7 text-xs -ml-2 mt-2"
                  >
                    Adjust {rank.displayName}
                    <ChevronRight className="h-3 w-3 ml-1" />
                  </Button>
                )}

                {idx < ranks.length - 1 && <div className="pt-2 border-b border-border/30" />}
              </div>
            );
          })}
        </div>

        {/* Summary insight */}
        {ranks.length >= 1 && (
          <div className="mt-6 pt-6 border-t space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Key Insight</p>
            <p className="text-sm text-foreground">
              Focusing on <span className="font-semibold">{ranks[0].displayName}</span> will have
              the highest impact on your runway. A {Math.abs(ranks[0].percentageChange).toFixed(1)}%
              improvement in this variable could add {Math.abs(ranks[0].impact)} months to your
              current runway.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
