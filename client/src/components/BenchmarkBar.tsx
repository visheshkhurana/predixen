import { cn } from '@/lib/utils';

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
  const range = max - min;
  
  const getPosition = (v: number) => ((v - min) / range) * 100;
  
  const p25Pos = getPosition(p25);
  const p50Pos = getPosition(p50);
  const p75Pos = getPosition(p75);
  const valuePos = Math.min(100, Math.max(0, getPosition(value)));
  
  const isGood =
    (direction === 'higher_is_better' && value >= p50) ||
    (direction === 'lower_is_better' && value <= p50);
  
  return (
    <div className="space-y-2" data-testid={testId}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{metric}</span>
        <span className="text-sm font-mono text-muted-foreground">
          {direction === 'higher_is_better' ? 'Higher is better' : 'Lower is better'}
        </span>
      </div>
      
      <div className="relative h-8 bg-secondary rounded-lg overflow-hidden">
        <div
          className="absolute top-0 bottom-0 bg-muted/50"
          style={{ left: `${p25Pos}%`, width: `${p75Pos - p25Pos}%` }}
        />
        
        <div
          className="absolute top-1 bottom-1 w-0.5 bg-muted-foreground/50"
          style={{ left: `${p25Pos}%` }}
        >
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-muted-foreground">
            P25
          </span>
        </div>
        
        <div
          className="absolute top-1 bottom-1 w-0.5 bg-muted-foreground"
          style={{ left: `${p50Pos}%` }}
        >
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-muted-foreground">
            P50
          </span>
        </div>
        
        <div
          className="absolute top-1 bottom-1 w-0.5 bg-muted-foreground/50"
          style={{ left: `${p75Pos}%` }}
        >
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-muted-foreground">
            P75
          </span>
        </div>
        
        <div
          className={cn(
            'absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 border-background',
            isGood ? 'bg-emerald-500' : 'bg-amber-500'
          )}
          style={{ left: `calc(${valuePos}% - 8px)` }}
        >
          <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs font-mono font-medium whitespace-nowrap">
            {format(value)}
          </span>
        </div>
      </div>
      
      <div className="flex justify-between text-xs text-muted-foreground mt-4">
        <span>{format(p25)}</span>
        <span>{format(p50)}</span>
        <span>{format(p75)}</span>
      </div>
    </div>
  );
}
