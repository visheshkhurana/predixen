import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  AlertTriangle, Clock, TrendingDown, Flame
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface InactionData {
  months_to_crisis: number;
  crisis_description: string;
  probability: number;
  cash_at_crisis: number;
  key_trigger: string;
}

interface InactionProjectionProps {
  data: InactionData | null;
}

export function InactionProjection({ data }: InactionProjectionProps) {
  if (!data) return null;

  const isUrgent = data.months_to_crisis <= 6;
  const isCritical = data.months_to_crisis <= 3;
  const probabilityHigh = data.probability >= 60;

  const borderColor = isCritical
    ? 'border-red-500/40'
    : isUrgent
    ? 'border-amber-500/30'
    : 'border-amber-500/20';

  const bgGradient = isCritical
    ? 'from-red-500/10 to-transparent'
    : isUrgent
    ? 'from-amber-500/8 to-transparent'
    : 'from-amber-500/5 to-transparent';

  return (
    <Card 
      className={cn("bg-gradient-to-br", bgGradient, borderColor)}
      data-testid="card-inaction-projection"
    >
      <CardContent className="py-4 px-5">
        <div className="flex items-start gap-4 flex-wrap">
          <div className={cn(
            "w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0",
            isCritical ? "bg-red-500" : "bg-amber-500"
          )}>
            {isCritical ? (
              <Flame className="h-5 w-5 text-white" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-white" />
            )}
          </div>

          <div className="flex-1 min-w-0 space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold">If You Do Nothing</span>
              <Badge 
                className={cn(
                  "text-xs text-white",
                  isCritical ? "bg-red-500" : "bg-amber-500"
                )}
              >
                {data.months_to_crisis} months to crisis
              </Badge>
              {probabilityHigh && (
                <Badge variant="outline" className="text-xs border-red-500/30 text-red-400">
                  {data.probability}% probability
                </Badge>
              )}
            </div>

            <p className="text-sm text-muted-foreground leading-relaxed">
              {data.crisis_description}
            </p>

            <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Trigger: {data.key_trigger}
              </span>
              {data.cash_at_crisis !== undefined && (
                <span className="flex items-center gap-1">
                  <TrendingDown className="h-3 w-3 text-red-400" />
                  Cash at crisis: ${data.cash_at_crisis.toLocaleString()}
                </span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
