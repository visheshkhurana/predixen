import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface ImpactBarProps {
  baselineRunway: number;
  projectedRunway: number;
  maxRunway?: number;
  showLabel?: boolean;
  className?: string;
}

export function ImpactBar({
  baselineRunway,
  projectedRunway,
  maxRunway = 36,
  showLabel = true,
  className,
}: ImpactBarProps) {
  const change = projectedRunway - baselineRunway;
  const isPositive = change > 0.5;
  const isNegative = change < -0.5;
  const isNeutral = !isPositive && !isNegative;
  
  const baselinePercent = Math.min((baselineRunway / maxRunway) * 100, 100);
  const projectedPercent = Math.min((projectedRunway / maxRunway) * 100, 100);
  
  const barColor = isPositive 
    ? "bg-emerald-500" 
    : isNegative 
      ? "bg-red-500" 
      : "bg-amber-500";
  
  const textColor = isPositive 
    ? "text-emerald-500" 
    : isNegative 
      ? "text-red-500" 
      : "text-amber-500";
  
  return (
    <div className={cn("space-y-2", className)} data-testid="impact-bar">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Runway Impact</span>
        <div className={cn("flex items-center gap-1 font-medium", textColor)}>
          {isNeutral ? (
            <Minus className="w-4 h-4" />
          ) : isPositive ? (
            <TrendingUp className="w-4 h-4" />
          ) : (
            <TrendingDown className="w-4 h-4" />
          )}
          <span>
            {isNeutral 
              ? 'No significant change' 
              : `${isPositive ? '+' : ''}${change.toFixed(1)} months`
            }
          </span>
        </div>
      </div>
      
      <div className="relative h-6 bg-muted rounded-md overflow-hidden">
        <div
          className="absolute top-0 left-0 h-full bg-muted-foreground/20 transition-all duration-300"
          style={{ width: `${baselinePercent}%` }}
        />
        <div
          className={cn("absolute top-0 left-0 h-full transition-all duration-300", barColor)}
          style={{ width: `${projectedPercent}%` }}
        />
        
        <div 
          className="absolute top-0 h-full w-0.5 bg-foreground/50"
          style={{ left: `${baselinePercent}%` }}
        />
        
        <div className="absolute inset-0 flex items-center justify-between px-3 text-xs font-medium">
          <span className="text-foreground/80">0</span>
          <span className="text-foreground/80">{maxRunway}mo</span>
        </div>
      </div>
      
      {showLabel && (
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Current: {baselineRunway >= 900 ? 'Sustainable' : `${baselineRunway.toFixed(1)} months`}</span>
          <span>Projected: {projectedRunway >= 900 ? 'Sustainable' : `${projectedRunway.toFixed(1)} months`}</span>
        </div>
      )}
    </div>
  );
}
