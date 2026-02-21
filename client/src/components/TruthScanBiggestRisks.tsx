import { Card, CardContent } from '@/components/ui/card';
import { AlertCircle, AlertTriangle, TrendingDown, DollarSign, Users } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

interface Risk {
  id: string;
  icon: 'critical' | 'warning' | 'metric';
  title: string;
  description: string;
  priority: 1 | 2 | 3; // 1 = highest
}

interface TruthScanBiggestRisksProps {
  risks: Risk[];
  isLoading: boolean;
}

export function TruthScanBiggestRisks({ risks, isLoading }: TruthScanBiggestRisksProps) {
  if (!risks || risks.length === 0) {
    return null;
  }

  const getRiskIcon = (type: Risk['icon']) => {
    switch (type) {
      case 'critical':
        return <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0" />;
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0" />;
      case 'metric':
        return <TrendingDown className="h-5 w-5 text-blue-600 dark:text-blue-400 shrink-0" />;
    }
  };

  const getRiskColor = (type: Risk['icon']) => {
    switch (type) {
      case 'critical':
        return 'bg-red-500/10 border-red-500/30';
      case 'warning':
        return 'bg-amber-500/10 border-amber-500/30';
      case 'metric':
        return 'bg-blue-500/10 border-blue-500/30';
    }
  };

  const getPriorityLabel = (priority: number) => {
    switch (priority) {
      case 1:
        return 'P0';
      case 2:
        return 'P1';
      case 3:
        return 'P2';
      default:
        return '';
    }
  };

  const getPriorityColor = (priority: number) => {
    switch (priority) {
      case 1:
        return 'bg-red-500/20 text-red-700 dark:text-red-300';
      case 2:
        return 'bg-amber-500/20 text-amber-700 dark:text-amber-300';
      case 3:
        return 'bg-blue-500/20 text-blue-700 dark:text-blue-300';
      default:
        return 'bg-secondary text-muted-foreground';
    }
  };

  // Show only top 3 risks
  const topRisks = risks.slice(0, 3);

  return (
    <Card className="border-amber-500/20 bg-amber-500/5">
      <CardContent className="p-6">
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            Biggest Risks
          </h3>

          <div className="space-y-3">
            {isLoading ? (
              Array(3)
                .fill(0)
                .map((_, i) => (
                  <div key={i} className="space-y-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-3 w-3/4" />
                  </div>
                ))
            ) : (
              topRisks.map((risk) => (
                <div key={risk.id} className={`border border-current rounded-lg p-3 ${getRiskColor(risk.icon)}`}>
                  <div className="flex items-start gap-3">
                    {getRiskIcon(risk.icon)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="font-medium text-sm">{risk.title}</h4>
                        <span className={`text-xs font-semibold px-2 py-1 rounded ${getPriorityColor(risk.priority)}`}>
                          {getPriorityLabel(risk.priority)}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">{risk.description}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
