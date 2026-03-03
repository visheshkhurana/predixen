import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ArrowRight, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { Link } from 'wouter';

interface Recommendation {
  issue: string;
  action: string;
  currentValue: string | number;
  targetValue: string | number;
  impact: string;
}

function getImpactBadgeClass(impact: string): string {
  switch (impact) {
    case 'high': return 'bg-red-500/15 text-red-600 border-transparent';
    case 'medium': return 'bg-yellow-500/15 text-yellow-600 border-transparent';
    case 'low': return 'bg-blue-500/15 text-blue-600 border-transparent';
    default: return '';
  }
}

function ImpactIcon({ impact }: { impact: string }) {
  switch (impact) {
    case 'high': return <AlertTriangle className="h-4 w-4 text-red-500" />;
    case 'medium': return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    default: return <Info className="h-4 w-4 text-blue-500" />;
  }
}

const impactOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };

export function RecommendationsList({ recommendations }: { recommendations: Recommendation[] }) {
  const sorted = [...recommendations].sort(
    (a, b) => (impactOrder[a.impact] ?? 3) - (impactOrder[b.impact] ?? 3)
  );

  if (sorted.length === 0) {
    return (
      <Card data-testid="card-recommendations-empty">
        <CardContent className="pt-6 text-center text-muted-foreground">
          No recommendations at this time. Your metrics look great!
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3" data-testid="display-recommendations-list">
      <h3 className="text-lg font-semibold">Recommendations</h3>
      {sorted.map((rec, idx) => (
        <Card key={idx} data-testid={`card-recommendation-${idx}`}>
          <CardContent className="pt-4 pb-4 space-y-3">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-2">
                <ImpactIcon impact={rec.impact} />
                <span className="font-medium text-sm" data-testid={`text-recommendation-issue-${idx}`}>{rec.issue}</span>
              </div>
              <Badge className={getImpactBadgeClass(rec.impact)} data-testid={`badge-impact-${idx}`}>
                {rec.impact}
              </Badge>
            </div>

            <p className="text-sm text-muted-foreground" data-testid={`text-recommendation-action-${idx}`}>
              {rec.action}
            </p>

            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Current:</span>
              <span className="font-medium" data-testid={`text-current-value-${idx}`}>{rec.currentValue}</span>
              <ArrowRight className="h-3 w-3 text-muted-foreground" />
              <span className="text-muted-foreground">Target:</span>
              <span className="font-medium" data-testid={`text-target-value-${idx}`}>{rec.targetValue}</span>
            </div>

            <Link href="/scenarios">
              <Button variant="outline" size="sm" data-testid={`button-run-scenario-${idx}`}>
                Run Scenario
              </Button>
            </Link>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
