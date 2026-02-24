import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Lightbulb, ArrowRight } from 'lucide-react';
import { useLocation } from 'wouter';

interface SuggestedAction {
  id: string;
  title: string;
  description: string;
  metricIssue: string; // e.g., "Churn is 40% above benchmark"
  actionType: 'retention' | 'runway' | 'burn' | 'margin' | 'growth' | 'acquisition';
  scenarioName?: string;
  scenarioParams?: Record<string, any>;
  priority: 'high' | 'medium' | 'low';
}

interface TruthScanSuggestedActionsProps {
  actions: SuggestedAction[];
  companyId?: string | number;
  isLoading?: boolean;
}

export function TruthScanSuggestedActions({
  actions,
  companyId,
  isLoading = false,
}: TruthScanSuggestedActionsProps) {
  const [, navigate] = useLocation();

  if (!actions || actions.length === 0) {
    return null;
  }

  const getActionColor = (actionType: string) => {
    switch (actionType) {
      case 'retention':
        return 'bg-blue-500/10 border-blue-500/30 hover:bg-blue-500/20';
      case 'runway':
        return 'bg-red-500/10 border-red-500/30 hover:bg-red-500/20';
      case 'burn':
        return 'bg-orange-500/10 border-orange-500/30 hover:bg-orange-500/20';
      case 'margin':
        return 'bg-purple-500/10 border-purple-500/30 hover:bg-purple-500/20';
      case 'growth':
        return 'bg-emerald-500/10 border-emerald-500/30 hover:bg-emerald-500/20';
      case 'acquisition':
        return 'bg-cyan-500/10 border-cyan-500/30 hover:bg-cyan-500/20';
      default:
        return 'bg-secondary/50';
    }
  };

  const getActionLabel = (actionType: string) => {
    switch (actionType) {
      case 'retention':
        return 'Retention';
      case 'runway':
        return 'Fundraising';
      case 'burn':
        return 'Cost Control';
      case 'margin':
        return 'Margin';
      case 'growth':
        return 'Growth';
      case 'acquisition':
        return 'Acquisition';
      default:
        return actionType;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-500/20 text-red-700 dark:text-red-300';
      case 'medium':
        return 'bg-amber-500/20 text-amber-700 dark:text-amber-300';
      case 'low':
        return 'bg-blue-500/20 text-blue-700 dark:text-blue-300';
      default:
        return 'bg-secondary text-muted-foreground';
    }
  };

  const handleActionClick = (action: SuggestedAction) => {
    // Build scenario URL with pre-populated parameters
    const params = new URLSearchParams();

    if (companyId) {
      params.append('company', String(companyId));
    }

    // Add scenario-specific parameters
    if (action.scenarioParams) {
      Object.entries(action.scenarioParams).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
          params.append(key, String(value));
        }
      });
    }

    // Add scenario name/type to guide the user
    if (action.scenarioName) {
      params.append('scenario', action.scenarioName);
    }

    const url = `/scenarios${params.toString() ? `?${params.toString()}` : ''}`;
    navigate(url);
  };

  return (
    <Card className="border-blue-500/20 bg-blue-500/5">
      <CardContent className="p-6">
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            Suggested Actions
          </h3>

          <div className="space-y-3">
            {actions.slice(0, 4).map((action) => (
              <div
                key={action.id}
                className={`border rounded-lg p-4 transition-all ${getActionColor(action.actionType)}`}
              >
                <div className="space-y-3">
                  {/* Header: Title + Priority + Type */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-sm">{action.title}</h4>
                      <p className="text-xs text-muted-foreground mt-1">{action.metricIssue}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant="secondary" className={`text-xs ${getPriorityColor(action.priority)}`}>
                        {action.priority === 'high' ? 'High' : action.priority === 'medium' ? 'Medium' : 'Low'}
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {getActionLabel(action.actionType)}
                      </Badge>
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-sm text-muted-foreground">{action.description}</p>

                  {/* CTA Button */}
                  <div className="pt-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleActionClick(action)}
                      disabled={isLoading}
                      className="w-full"
                    >
                      Run Scenario
                      <ArrowRight className="h-3.5 w-3.5 ml-2" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {actions.length > 4 && (
            <p className="text-xs text-muted-foreground text-center pt-2">
              Showing {Math.min(4, actions.length)} of {actions.length} suggested actions
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
