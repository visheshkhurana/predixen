import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { HelpCircle, TrendingUp, TrendingDown } from 'lucide-react';

interface BenchmarkBarProps {
  metric: string;
  value: number;
  p25: number;
  p50: number;
  p75: number;
  direction: 'higher_is_better' | 'lower_is_better';
  format?: (value: number) => string;
  testId?: string;
}

export function BenchmarkBar({
  metric,
  value,
  p25,
  p50,
  p75,
  direction,
  format = (v) => v.toFixed(1),
  testId = 'benchmark-bar',
}: BenchmarkBarProps) {
  const min = Math.min(p25 * 0.5, value * 0.8);
  const max = Math.max(p75 * 1.5, value * 1.2);
  const range = max - min || 1;
  
  const getPosition = (v: number) => Math.min(100, Math.max(0, ((v - min) / range) * 100));
  
  const p25Pos = getPosition(p25);
  const p50Pos = getPosition(p50);
  const p75Pos = getPosition(p75);
  const valuePos = getPosition(value);
  
  const getQuartileStatus = () => {
    if (direction === 'higher_is_better') {
      if (value >= p75) return { label: 'Top Quartile', color: 'bg-emerald-500/20 text-emerald-400', status: 'excellent' };
      if (value >= p50) return { label: 'Above Median', color: 'bg-blue-500/20 text-blue-400', status: 'good' };
      if (value >= p25) return { label: 'Below Median', color: 'bg-amber-500/20 text-amber-400', status: 'warning' };
      return { label: 'Bottom Quartile', color: 'bg-red-500/20 text-red-400', status: 'critical' };
    } else {
      if (value <= p25) return { label: 'Top Quartile', color: 'bg-emerald-500/20 text-emerald-400', status: 'excellent' };
      if (value <= p50) return { label: 'Above Median', color: 'bg-blue-500/20 text-blue-400', status: 'good' };
      if (value <= p75) return { label: 'Below Median', color: 'bg-amber-500/20 text-amber-400', status: 'warning' };
      return { label: 'Bottom Quartile', color: 'bg-red-500/20 text-red-400', status: 'critical' };
    }
  };
  
  const quartile = getQuartileStatus();
  const isGood = quartile.status === 'excellent' || quartile.status === 'good';
  
  return (
    <div className="space-y-2" data-testid={testId}>
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{metric}</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="p-0.5" data-testid={`${testId}-tooltip`}>
                <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-sm">
                <strong>P25:</strong> 25th percentile (bottom quarter)<br/>
                <strong>P50:</strong> Median (middle)<br/>
                <strong>P75:</strong> 75th percentile (top quarter)
              </p>
            </TooltipContent>
          </Tooltip>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className={cn('text-xs', quartile.color)}>
            {quartile.label}
          </Badge>
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            {direction === 'higher_is_better' ? (
              <><TrendingUp className="h-3 w-3" /> Higher is better</>
            ) : (
              <><TrendingDown className="h-3 w-3" /> Lower is better</>
            )}
          </span>
        </div>
      </div>
      
      <div className="relative h-10 bg-secondary rounded-lg overflow-hidden">
        <div
          className="absolute top-0 bottom-0 bg-gradient-to-r from-red-500/10 via-amber-500/10 to-red-500/10"
          style={{ left: '0%', width: `${p25Pos}%` }}
        />
        <div
          className={cn(
            "absolute top-0 bottom-0",
            direction === 'higher_is_better' 
              ? "bg-gradient-to-r from-amber-500/15 to-emerald-500/15" 
              : "bg-gradient-to-r from-emerald-500/15 to-amber-500/15"
          )}
          style={{ left: `${p25Pos}%`, width: `${p75Pos - p25Pos}%` }}
        />
        <div
          className="absolute top-0 bottom-0 bg-gradient-to-r from-emerald-500/10 to-emerald-500/5"
          style={{ left: `${p75Pos}%`, width: `${100 - p75Pos}%` }}
        />
        
        <div
          className="absolute top-1 bottom-1 w-0.5 bg-muted-foreground/40"
          style={{ left: `${p25Pos}%` }}
        >
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-muted-foreground font-medium">
            P25
          </span>
        </div>
        
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-muted-foreground"
          style={{ left: `${p50Pos}%` }}
        >
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-muted-foreground font-semibold">
            P50
          </span>
        </div>
        
        <div
          className="absolute top-1 bottom-1 w-0.5 bg-muted-foreground/40"
          style={{ left: `${p75Pos}%` }}
        >
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-muted-foreground font-medium">
            P75
          </span>
        </div>
        
        <div
          className={cn(
            'absolute top-1/2 -translate-y-1/2 w-5 h-5 rounded-full border-2 border-background shadow-lg transition-all',
            isGood ? 'bg-emerald-500' : 'bg-amber-500'
          )}
          style={{ left: `calc(${valuePos}% - 10px)` }}
        >
          <span className={cn(
            "absolute -top-7 left-1/2 -translate-x-1/2 text-xs font-mono font-bold whitespace-nowrap px-1.5 py-0.5 rounded",
            isGood ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
          )}>
            {format(value)}
          </span>
        </div>
      </div>
      
      <div className="flex justify-between text-xs text-muted-foreground mt-5">
        <span className="font-mono">{format(p25)}</span>
        <span className="font-mono font-medium">{format(p50)}</span>
        <span className="font-mono">{format(p75)}</span>
      </div>
    </div>
  );
}
