import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { FlaskConical, TrendingDown, AlertCircle, Snowflake, Users, Swords, Pause, ArrowRight } from 'lucide-react';
import { stressTestTemplates, StressTestTemplate, applyStressTest } from '@/lib/simulation/stressTestTemplates';
import { calculateRunway, type FinancialState } from '@/lib/simulation/sensitivityAnalysis';
import { cn } from '@/lib/utils';

interface StressTestPanelProps {
  currentState: FinancialState;
  currentRunway: number;
  onApplyStressTest: (stressedState: any, template: StressTestTemplate) => void;
  testId?: string;
}

const iconMap: Record<string, typeof TrendingDown> = {
  TrendingDown,
  AlertCircle,
  Snowflake,
  Users,
  Swords,
  Pause,
};

const severityStyles = {
  low: { 
    badge: 'bg-muted text-muted-foreground border-border',
    card: 'border-border hover:border-muted-foreground/50'
  },
  moderate: { 
    badge: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/30',
    card: 'border-yellow-500/30 hover:border-yellow-500/50'
  },
  severe: { 
    badge: 'bg-red-500/10 text-red-500 border-red-500/30',
    card: 'border-red-500/30 hover:border-red-500/50'
  },
};

export function StressTestPanel({ 
  currentState, 
  currentRunway, 
  onApplyStressTest,
  testId = 'stress-test-panel'
}: StressTestPanelProps) {
  const [selectedTest, setSelectedTest] = useState<string | null>(null);

  const previewResults = useMemo(() => {
    const results: Record<string, number> = {};
    stressTestTemplates.forEach(template => {
      const stressedState = applyStressTest(currentState, template);
      results[template.id] = calculateRunway(stressedState);
    });
    return results;
  }, [currentState]);

  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5" />
          Stress Test Scenarios
        </CardTitle>
        <CardDescription>
          Test your business resilience under adverse conditions
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {stressTestTemplates.map((template) => {
            const previewRunway = previewResults[template.id] || 0;
            const runwayChange = previewRunway - currentRunway;
            const styles = severityStyles[template.severity];
            const Icon = iconMap[template.icon] || FlaskConical;
            const isSelected = selectedTest === template.id;
            
            return (
              <div
                key={template.id}
                className={cn(
                  "border rounded-lg p-4 cursor-pointer transition-all",
                  styles.card,
                  isSelected && 'ring-2 ring-primary'
                )}
                onClick={() => setSelectedTest(isSelected ? null : template.id)}
                data-testid={`stress-test-${template.id}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <Icon className="h-5 w-5 text-muted-foreground" />
                  <Badge variant="outline" className={cn("text-xs", styles.badge)}>
                    {template.severity}
                  </Badge>
                </div>
                
                <h4 className="font-medium mb-1">{template.name}</h4>
                <p className="text-muted-foreground text-xs mb-3 line-clamp-2">{template.description}</p>
                
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Runway Impact:</span>
                  <span className={cn(
                    "font-mono",
                    runwayChange < 0 ? 'text-red-500' : 'text-green-500'
                  )}>
                    {currentRunway >= 900 ? '∞' : `${currentRunway.toFixed(0)}mo`} <ArrowRight className="inline h-3 w-3" /> {previewRunway >= 900 ? '∞' : `${previewRunway.toFixed(0)}mo`}
                  </span>
                </div>
                
                <div className="flex items-center justify-between text-xs text-muted-foreground mt-1">
                  <span>Duration: {template.duration}mo</span>
                  <span>~{(template.historicalProbability * 100).toFixed(0)}% probability</span>
                </div>
                
                {isSelected && (
                  <Button
                    className="w-full mt-3"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      const stressedState = applyStressTest(currentState, template);
                      onApplyStressTest(stressedState, template);
                    }}
                    data-testid={`apply-stress-test-${template.id}`}
                  >
                    Apply Stress Test
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export default StressTestPanel;
